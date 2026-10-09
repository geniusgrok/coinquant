"""Historical matching behind the production Binance adapter.

Market rows and fills are the replacement boundary. Order checks, weight, and
the session coordinator stay on the production path. This is not a live venue
and it does not know the future session schedule.
"""
from datetime import datetime, timezone
from decimal import Decimal as D, ROUND_CEILING
import hashlib
import io
import json
from pathlib import Path
from math import ceil
from urllib.error import HTTPError

from coinquant.binance import Binance
from coinquant.types import Unknown


def _refuse(code, message):
    """A native HTTP 400 refusal, so the production classifier sees what it sees live."""
    raise HTTPError('https://fapi.binance.com', 400, 'Bad Request', {},
                    io.BytesIO(json.dumps({'code': code, 'msg': message}).encode()))


FEE = D('0.00075')          # research proxy, not an account commission schedule
MAINTENANCE = D('0.005')    # single 20x tier proxy, not dated brackets
LIQUIDATION_FEE = D('0.0125')  # field on the 2026-09-26 public rules snapshot
RULES_PATH = Path(__file__).resolve().parents[1] / 'evidence' / 'bounded-session-20260926' / 'public' / 'rules.json'
RULES_SHA256 = 'a730dabf5b6710dafb1bc70db1ab579083ad0699e07b5f59e1f20a5617445c7f'
MINUTE = 60_000
DAY = 86_400_000
# Worst 1m mark low/high relative to trade low/high, 2020-01-01..2026-09-20.
MARK_BELOW_TRADE = D('-0.0237')
MARK_ABOVE_TRADE = D('0.0412')


def _text(value):
    text = format(D(value), 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text or '0'


class _Offline:
    def open(self, *args, **kwargs):
        raise AssertionError('session exchange must not open a network request')


class SessionExchange(Binance):
    def __init__(self, market, now_ms, wallet, *, matcher='unresolved', uid=1, prints=None):
        self.market = market
        self.now_ms = int(now_ms)
        self.wallet = D(wallet)
        self.q = D(0)
        self.entry = D(0)
        self.margin = D(0)
        self._changed = None
        self._changed_ms = int(now_ms)
        self.fees = D(0)
        self.funding_paid = D(0)
        self.matcher = matcher
        self.prints = prints
        self.uid = int(uid)
        self.orders = {}
        self.by_order_id = {}
        self.algos = {}
        self.trades = []
        self.income = []
        self._seq = 1
        self._tran = 1
        self.sent = []
        self.funnel = {'ioc_submitted': 0, 'ioc_zero': 0, 'ioc_filled': 0,
                       'protections': 0, 'triggers': 0, 'liquidations': 0, 'funding': 0,
                       'gap_forfeits': 0, 'print_triggers': 0, 'partial_adverse': 0}
        # Start of the current position/protection configuration, and the last
        # minute whose prints were scanned for triggers.
        self.held_from = 0
        self._scanned = None
        self.hindsight_bounded = False
        self.print_miss_days = set()
        self.bounded_minutes = []
        self.unknown_from = None
        self.peak_cny = D(10000)
        self.peak_envelope_cny = D(10000)
        self.mdd_close = D(0)
        self.mdd_envelope = D(0)
        self.mdd_close_at = None
        self.mdd_envelope_at = None
        self.daily_cny = {}
        self.known_path = True
        raw = RULES_PATH.read_bytes()
        if hashlib.sha256(raw).hexdigest() != RULES_SHA256:
            raise ValueError('contract rules snapshot changed')
        self.rules_sha256 = RULES_SHA256
        self.rules = json.loads(raw.decode('utf-8'))['instrument']
        super().__init__(key='historical-proxy', secret='historical-proxy',
                         opener=_Offline(), authorize_writes=True,
                         clock=lambda: self.now_ms / 1000,
                         monotonic=lambda: self.now_ms / 1000.0)
        self._note_cash()

    _dfii10_history = None
    fx = staticmethod(lambda _now: D('6.9762'))
    exit_conversion = D(0)
    fee = FEE
    trigger_slippage = D(0)
    market_slippage = D(0)

    def _slipped(self, price, rate):
        return price * (1 - rate) if self.q > 0 else price * (1 + rate)

    def _cny(self):
        return self.fx(self.now_ms) * (1 - self.exit_conversion)
    print_window_ms = 1000
    latency_ms = 1000
    # Zero reproduces the earlier meters, where a read took no simulated time and the local
    # request-weight reserve, not the clock, decided how many top-ups fit in a session.
    read_latency_ms = 0
    # 'forfeit': a missing official mark minute costs the whole isolated wallet.
    # 'bound': trade range widened by the window's worst mark/trade gap (hindsight;
    # the owner-accepted basis that research.rebuild passes by default).
    mark_gap = 'forfeit'

    def dfii10_snapshot(self):
        if SessionExchange._dfii10_history is None:
            from research.dfii10_history import History
            SessionExchange._dfii10_history = History()
        history = SessionExchange._dfii10_history
        if history.last_now is not None and self.now_ms < history.last_now:
            SessionExchange._dfii10_history = history = type(history)()
        return history.snapshot(self.now_ms)

    def _request(self, method, path, parameters=None):
        # Private transport observation only; every production gate executes.
        previous = getattr(self, '_inflight', None)
        self._inflight = (method, path, dict(parameters or {}))
        try:
            return super()._request(method, path, parameters)
        finally:
            # A signed request may align its clock through a nested GET.
            # Restore its transport identity instead of dispatching that GET twice.
            self._inflight = previous

    def _transport(self, request, timeout):
        method, path, params = self._inflight
        if method != 'GET':
            self.sent.append((method, path, dict(params)))
            # A write takes effect when it reaches the venue; resting protection,
            # funding and liquidation keep running meanwhile.
            self._advance(self.now_ms + self.latency_ms)
        elif self.read_latency_ms:
            self._advance(self.now_ms + self.read_latency_ms)
        return self._reply(method, path, params)

    def _id(self):
        self._seq += 1
        return self._seq

    def _income(self, kind, stamp, amount, trade_id=''):
        self._tran += 1
        self.income.append({'incomeType': kind, 'tranId': self._tran, 'time': int(stamp),
                            'asset': 'USDT', 'income': _text(amount), 'symbol': 'BTCUSDT',
                            'tradeId': str(trade_id)})

    def _mark_state(self):
        """(observation time, mark). With prints, the mark is the last print at
        or before now scaled by the last completed minute's official
        mark/trade ratio, stamped with that print's time. Without prints it is
        the completed minute's official close, stamped at that minute's end."""
        open_ms, _observed = self._completed_minute()
        if open_ms is None:
            raise Unknown('completed minute unavailable')
        row = self.market.minute('mark', open_ms)
        if row is None:
            raise Unknown('completed mark minute unavailable')
        if self.prints is None:
            return open_ms + MINUTE, row[3]
        stamp, price = self._last_print()
        trade = self.market.minute('trade', open_ms)
        if trade is None or trade[3] <= 0:
            raise Unknown('completed trade minute unavailable for the mark basis')
        return stamp, (price * row[3] / trade[3]).quantize(D('0.00000001'))

    def _last_print(self):
        last = self.prints.last(self.now_ms)
        if last is None:
            raise Unknown('no trade print at or before the request')
        return int(last[0]), last[1]

    def _completed_minute(self):
        boundary = self.now_ms // MINUTE * MINUTE
        open_ms = boundary - MINUTE
        if open_ms < 0:
            return None, None
        return open_ms, self.now_ms

    def _book(self):
        """One-level proxy: ask at the last print rounded up to the tick, bid one
        tick below, both stamped with the print time. The quantity proxy is
        the last completed minute's volume."""
        open_ms, _observed = self._completed_minute()
        if open_ms is None:
            raise Unknown('completed trade minute unavailable')
        row = self.market.minute('trade', open_ms)
        if row is None:
            raise Unknown('completed trade minute unavailable')
        close, volume = row[3], row[4]
        tick = D(self._price_filter()['tickSize'])
        if self.prints is None:
            observed, ask = open_ms + MINUTE, close
        else:
            observed, price = self._last_print()
            ask = (price / tick).to_integral_value(rounding=ROUND_CEILING) * tick
        bid = ask - tick
        if bid <= 0 or volume <= 0:
            raise Unknown('completed minute has no positive book proxy')
        return observed, bid, ask, volume

    def _price_filter(self):
        rows = [item for item in self.rules['filters'] if item.get('filterType') == 'PRICE_FILTER']
        if len(rows) != 1:
            raise Unknown('price filter unavailable')
        return rows[0]

    def _liquidation(self):
        if not self.q:
            return D(0)
        # Same shape as the linear proxy. Dated brackets are not claimed.
        return (self.q * self.entry - self.margin) / (self.q - abs(self.q) * (MAINTENANCE + self.fee))

    def _update_time(self):
        """Binance `updateTime` is the last account change, not the read time; it is
        stamped when a read first sees a new wallet/position/margin state."""
        state = (self.wallet, self.q, self.entry, self.margin)
        if state != self._changed:
            self._changed, self._changed_ms = state, self.now_ms
        return self._changed_ms

    def _position(self, mark):
        pnl = self.q * (mark - self.entry) if self.q else D(0)
        liq = max(D(0), self._liquidation()) if self.q > 0 else self._liquidation()
        return dict(symbol='BTCUSDT', positionSide='BOTH', positionAmt=_text(self.q),
                    entryPrice=_text(self.entry if self.q else 0), isolatedWallet=_text(self.margin if self.q else 0),
                    updateTime=self._update_time(), marginAsset='USDT', markPrice=_text(mark),
                    unRealizedProfit=_text(pnl), liquidationPrice=_text(liq if self.q else 0))

    def _note(self, price, kind):
        """`favorable` only raises the envelope peak; `envelope` is the adverse
        extreme; `close` is a point of both series. Within a minute the
        favorable extreme is taken before the adverse one."""
        equity = self.wallet + (self.q * (D(price) - self.entry) if self.q else D(0))
        self._record(equity * self._cny(), kind)

    def _record(self, cny, kind):
        if cny > self.peak_envelope_cny:
            self.peak_envelope_cny = cny
        if kind == 'favorable':
            return
        drawdown = 1 - cny / self.peak_envelope_cny
        if drawdown > self.mdd_envelope:
            self.mdd_envelope = drawdown
            self.mdd_envelope_at = self.now_ms
        if kind != 'close':
            return
        self.daily_cny[self.now_ms // DAY] = cny
        if cny > self.peak_cny:
            self.peak_cny = cny
        drawdown = 1 - cny / self.peak_cny
        if self.known_path and drawdown > self.mdd_close:
            self.mdd_close = drawdown
            self.mdd_close_at = self.now_ms

    def advance_unattended(self, until_ms):
        """Exchange time only: mark, resting protection, funding, liquidation."""
        until_ms = int(until_ms)
        if until_ms < self.now_ms:
            raise ValueError('exchange clock cannot move backwards')
        sends = len(self.sent)
        self._advance(until_ms)
        if len(self.sent) != sends:
            raise AssertionError('unattended time sent a client order')

    def wait(self, seconds):
        # The coordinator may hand us a positive submillisecond deadline tail.
        # Rounding it down to zero would repeat the same virtual poll forever.
        if seconds > 0:
            self._advance(self.now_ms + max(1, ceil(D(seconds) * 1000)))

    def _advance(self, until_ms):
        """Whole held minutes use the official mark OHLC. Attended or partly held
        minutes also walk the trade prints, so a trigger takes effect at its
        print time, before later funding or client actions."""
        while self.now_ms < until_ms:
            if not self.q:
                # Flat cash only moves in CNY when the dated rate changes.
                changes = getattr(self.fx, 'changes', None)
                for stamp in (changes(self.now_ms, until_ms) if changes else ()):
                    self.now_ms = stamp
                    self._note_cash()
                self.now_ms = until_ms
                self._note_cash()
                return
            open_ms = self.now_ms // MINUTE * MINUTE
            boundary = open_ms + MINUTE
            step = min(until_ms, boundary)
            if step < boundary or self.held_from > open_ms or self._scanned == open_ms:
                self._scanned = open_ms
                hit = self._scan(self.now_ms, step)
                if hit is not None:
                    stamp, kind, price = hit
                    self._pay_funding(self.now_ms, stamp)
                    self.now_ms = max(self.now_ms, stamp)
                    if self.q:
                        self._fire(kind, price)
                    continue
            if self.q and step == boundary:
                # A settlement stamped exactly at the boundary follows this
                # minute's range, so a stop inside the minute is not charged.
                self._pay_funding(self.now_ms, step - 1)
                if self.held_from > open_ms:
                    self._partial(open_ms, True)
                else:
                    self._on_minute(open_ms)
                self._pay_funding(max(self.now_ms, step - 1), step)
            else:
                self._pay_funding(self.now_ms, step)
            self.now_ms = step
        self._note_cash()

    def _scan(self, start_ms, end_ms):
        """First print in [start, end) whose proxy mark reaches a trigger.

        The proxy mark is the print scaled by the previous completed minute's
        official mark/trade ratio, as served to the client. None if unavailable."""
        if self.prints is None or not self.q or end_ms <= start_ms:
            return None
        open_ms = start_ms // MINUTE * MINUTE
        mark = self.market.minute('mark', open_ms - MINUTE)
        trade = self.market.minute('trade', open_ms - MINUTE)
        if mark is None or trade is None or trade[3] <= 0:
            return None
        rows = self.prints.raw(start_ms, end_ms)
        if not rows:
            return None
        ratio = mark[3] / trade[3]
        scale = D(10) ** 8
        long = self.q > 0
        stop, take = self._triggers()
        liq = self._liquidation()
        level = lambda price: int(price / ratio * scale)
        adverse = [(kind, value, level(value)) for kind, value in (('stop', stop), ('liq', liq))
                   if value is not None and value > 0]
        good = level(take) if take is not None else None
        # Prints are an ordered path, so every point both raises the peak and is
        # measured against it. Points that are neither a new high nor a new low
        # since the last high cannot change either, whatever the segmentation.
        best = worst = None
        for stamp, price, _qty in rows:
            extreme = True
            if best is None or ((price > best) if long else (price < best)):
                best = worst = price
            elif (price < worst) if long else (price > worst):
                worst = price
            else:
                extreme = False
            if extreme:
                mark = D(price) / scale * ratio
                if take is not None:
                    mark = min(mark, take) if long else max(mark, take)
                self._note_at(stamp, mark, 'envelope')
            for kind, value, bound in adverse:
                if (price <= bound) if long else (price >= bound):
                    trade_price = D(price) / scale
                    return stamp, kind, (min(value, trade_price) if long else max(value, trade_price))
            if good is not None and ((price >= good) if long else (price <= good)):
                return stamp, 'take', take
        return None

    def _note_at(self, stamp, price, kind):
        """Record a path point stamped at its print without moving the clock."""
        now, self.now_ms = self.now_ms, max(self.now_ms, stamp)
        try:
            self._note(price, kind)
        finally:
            self.now_ms = now

    def _fire(self, kind, price):
        self.funnel['print_triggers'] += 1
        self._note(price, 'envelope')
        if kind == 'stop':
            self._trigger('STOP_MARKET', price)
        elif kind == 'take':
            self._trigger('TAKE_PROFIT_MARKET', price)
        else:
            self._liquidate(price)
        if kind == 'stop' and self.q:
            # Without an owned stop the adverse print may still reach liquidation later.
            return
        self.held_from = self.now_ms

    def _partial(self, open_ms, at_boundary):
        """Held only part of this minute. The official minute range also covers
        time outside the holding, so its order is unknown: the adverse
        extreme counts for drawdown and a reachable stop or liquidation
        applies; a take is not assumed."""
        row = self.market.minute('mark', open_ms)
        if row is None:
            self._on_minute(open_ms)
            return
        _open, high, low, close, _volume = row
        long = self.q > 0
        stop, take = self._triggers()
        liq = self._liquidation()
        favorable = high if long else low
        if take is not None:
            favorable = min(favorable, take) if long else max(favorable, take)
        self._note(favorable, 'favorable')
        self._note(low if long else high, 'envelope')
        if at_boundary:
            self._note(close, 'close')
        if (low <= liq) if long else (high >= liq):
            self.funnel['partial_adverse'] += 1
            self._liquidate(liq)
        elif stop is not None and ((low <= stop) if long else (high >= stop)):
            self.funnel['partial_adverse'] += 1
            self._trigger('STOP_MARKET', stop)

    def _settle_change(self):
        """Close the held segment of this minute before its configuration changes."""
        if self.q and self.now_ms % MINUTE and self.now_ms > self.held_from:
            self._partial(self.now_ms // MINUTE * MINUTE, False)
        self.held_from = self.now_ms

    def _note_cash(self):
        if not self.q:
            self._record(self.wallet * self._cny(), 'close')

    def _pay_funding(self, start_ms, end_ms):
        if not self.q:
            return
        events, gap = self.market.funding_between(start_ms, end_ms)
        for stamp, rate in events:
            mark_row = self.market.minute('mark', (stamp // MINUTE) * MINUTE - MINUTE)
            if mark_row is None:
                raise Unknown('official mark price missing at a funding settlement')
            mark = mark_row[3]
            payment = -(self.q * mark * rate)
            self.wallet += payment
            self.funding_paid -= payment
            self.funnel['funding'] += 1
            self._income('FUNDING_FEE', stamp, payment)
            if self.q and self.wallet < self.margin:
                self.margin = max(D(0), self.wallet)
            self.now_ms = stamp
            self._note(mark, 'close')
        if gap:
            self.known_path = False
            self.unknown_from = self.unknown_from or end_ms

    def _on_minute(self, open_ms):
        if not self.q:
            return
        row = self.market.minute('mark', open_ms)
        bounded = row is None
        if bounded and self.mark_gap == 'forfeit':
            # No official mark exists. The isolated position can lose at most its
            # isolated wallet; that bound is taken at the first missing minute.
            self.bounded_minutes.append(open_ms)
            self._forfeit_isolated()
            return
        if bounded:
            trade = self.market.minute('trade', open_ms)
            if trade is None:
                self.known_path = False
                self.unknown_from = self.unknown_from or open_ms
                return
            self.hindsight_bounded = True
            # Missing mark minute: the trade range widened by the worst mark/trade
            # divergence observed in the window. The adverse bound is applied.
            row = (trade[0], trade[1] * (1 + MARK_ABOVE_TRADE), trade[2] * (1 + MARK_BELOW_TRADE),
                   trade[3], trade[4])
            self.bounded_minutes.append(open_ms)
        open_, high, low, close, _volume = row
        long = self.q > 0
        stop, take = self._triggers()
        liq = self._liquidation()
        adverse = low if long else high
        favorable = high if long else low
        if take is not None:
            favorable = min(favorable, take) if long else max(favorable, take)
        self._note(favorable, 'favorable')
        self._note(adverse, 'envelope')
        self._note(close, 'close')
        hits = []
        if stop is not None and (low <= stop if long else high >= stop):
            hits.append('stop')
        if take is not None and (high >= take if long else low <= take):
            hits.append('take')
        if (low <= liq if long else high >= liq):
            hits.append('liq')
        if bounded and hits:
            # Pessimistic: a reachable liquidation wins, then the stop; a take is not assumed.
            if 'liq' in hits:
                self._liquidate(liq)
            elif 'stop' in hits:
                self._trigger('STOP_MARKET', min(stop, open_) if long else max(stop, open_))
            return
        if len(hits) > 1:
            self.known_path = False
            self.unknown_from = self.unknown_from or open_ms
            worst = liq if 'liq' in hits else adverse
            self._note(worst, 'envelope')
            return
        if hits == ['stop']:
            price = open_ if (open_ <= stop if long else open_ >= stop) else stop
            self._trigger('STOP_MARKET', price)
        elif hits == ['take']:
            price = open_ if (open_ >= take if long else open_ <= take) else take
            self._trigger('TAKE_PROFIT_MARKET', price)
        elif hits == ['liq']:
            price = open_ if (open_ <= liq if long else open_ >= liq) else liq
            self._liquidate(price)

    def _forfeit_isolated(self):
        margin, wallet = self.margin, self.wallet
        live = self._live('STOP_MARKET')
        if live is None:
            self._liquidate(self.entry)
        else:
            self._close_all(live[0], live[1])
            self.funnel['triggers'] += 1
        # Whatever the recorded close, the total loss is exactly the isolated wallet.
        shortfall = margin - (wallet - self.wallet)
        if shortfall > 0:
            self.wallet -= shortfall
            self.fees += shortfall
            self._income('INSURANCE_CLEAR', self.now_ms, -shortfall)
        self.funnel['gap_forfeits'] += 1
        self._note_cash()

    def _live(self, kind):
        """The live conditional of `kind` that Binance would fire first: the highest
        long stop or lowest long take (mirrored for a short). During a protection
        replacement the old and new legs overlap."""
        rows = [(D(item['triggerPrice']), item) for item in self.algos.values()
                if item.get('algoStatus') == 'NEW' and item['orderType'] == kind]
        if not rows:
            return None
        first_high = (kind == 'STOP_MARKET') == (self.q > 0)
        return (max if first_high else min)(rows, key=lambda row: row[0])

    def _triggers(self):
        stop, take = self._live('STOP_MARKET'), self._live('TAKE_PROFIT_MARKET')
        return (stop[0] if stop else None), (take[0] if take else None)

    def _trigger(self, kind, price):
        live = self._live(kind)
        if live is None or not self.q:
            return
        self._close_all(self._slipped(price, self.trigger_slippage), live[1])
        self.funnel['triggers'] += 1

    def _liquidate(self, price):
        if not self.q:
            return
        quantity = abs(self.q)
        notional_fee = quantity * price * LIQUIDATION_FEE
        self._apply_close(quantity, price)
        self.wallet -= notional_fee
        self.fees += notional_fee
        self._income('INSURANCE_CLEAR', self.now_ms, -notional_fee)
        self.funnel['liquidations'] += 1
        for algo in self.algos.values():
            if algo['algoStatus'] == 'NEW':
                algo['algoStatus'] = 'CANCELED'

    def _close_all(self, price, algo):
        quantity = abs(self.q)
        side = 'SELL' if self.q > 0 else 'BUY'
        child_id = self._id()
        child = dict(symbol='BTCUSDT', orderId=child_id, clientOrderId='ex-' + str(child_id),
                     side=side, positionSide='BOTH', type='MARKET', status='FILLED',
                     origQty=_text(quantity), executedQty=_text(quantity), price=_text(price),
                     reduceOnly=True)
        self.orders[child['clientOrderId']] = child
        self.by_order_id[child_id] = child
        realized = self._apply_close(quantity, price)
        self._trade(side, child_id, quantity, price, realized)
        algo['algoStatus'] = 'FINISHED'
        algo['actualOrderId'] = str(child_id)
        for other in self.algos.values():
            if other is not algo and other['algoStatus'] == 'NEW':
                other['algoStatus'] = 'CANCELED'

    def _apply_open(self, side, quantity, price):
        fee = quantity * price * self.fee
        self.wallet -= fee
        self.fees += fee
        signed = quantity if side == 'BUY' else -quantity
        if self.q and (self.q > 0) != (signed > 0):
            raise Unknown('historical venue does not net an opposite entry')
        total = abs(self.q) + quantity
        self.entry = (abs(self.q) * self.entry + quantity * price) / total
        self.q += signed
        self.margin += quantity * price / 20
        self._income('COMMISSION', self.now_ms, -fee)
        return D(0)

    def _apply_close(self, quantity, price):
        original = abs(self.q)
        if quantity <= 0 or quantity > original:
            raise Unknown('close exceeds the historical position')
        if self.q > 0:
            realized = quantity * (price - self.entry)
            self.q -= quantity
        else:
            realized = quantity * (self.entry - price)
            self.q += quantity
        fee = quantity * price * self.fee
        self.wallet += realized - fee
        self.fees += fee
        if not self.q:
            self.entry = self.margin = D(0)
        else:
            self.margin *= (original - quantity) / original
        self._income('REALIZED_PNL', self.now_ms, realized)
        self._income('COMMISSION', self.now_ms, -fee)
        return realized

    def _trade(self, side, order_id, quantity, price, realized_pnl):
        # Mirror the commission and PnL just booked at this actual simulated fill.
        # Capture realized PnL before a full close resets the position basis.
        self.trades.append(dict(symbol='BTCUSDT', positionSide='BOTH', side=side, orderId=order_id,
                                id=len(self.trades) + 1, time=self.now_ms, qty=_text(quantity),
                                price=_text(price), commissionAsset='USDT',
                                commission=_text(quantity * price * self.fee),
                                realizedPnl=_text(realized_pnl)))

    def _working_orders(self):
        return [dict(order) for order in self.orders.values() if order['status'] in ('NEW', 'PARTIALLY_FILLED')]

    def _working_algos(self):
        return [dict(algo) for algo in self.algos.values() if algo['algoStatus'] == 'NEW']

    def _fill_ioc(self, side, limit, quantity):
        """[(time, quantity)] fill segments. Unresolved matching never fills."""
        if self.matcher == 'unresolved':
            self.funnel['ioc_zero'] += 1
            return []
        if self.matcher == 'trade_print':
            return self._fill_from_prints(side, limit, quantity)
        if self.matcher != 'bar_through':
            raise ValueError('unknown matcher')
        # Non-causal sensitivity: the minute that contains the latency instant.
        # A whole-bar print is still not a book. Callers must not treat it as a pass.
        instant = self.now_ms
        open_ms = instant // MINUTE * MINUTE
        row = self.market.minute('trade', open_ms)
        if row is None:
            self.funnel['ioc_zero'] += 1
            return []
        _open, high, low, _close, _volume = row
        through = high <= limit if side == 'BUY' else low >= limit
        if not through:
            self.funnel['ioc_zero'] += 1
            return []
        self.funnel['ioc_filled'] += 1
        return [(instant, quantity)]

    def _fill_from_prints(self, side, limit, quantity):
        """Quantity is an upper bound: the whole matching print can be taken.

        The fill price stays at the limit. A missing official file is unknown,
        which is different from a present file that contains no matching print.
        """
        if self.prints is None:
            raise Unknown('trade prints were not loaded')
        start = self.now_ms
        end = start + self.print_window_ms
        rows = self.prints.timed(start, end)
        if rows is None:
            day = datetime.fromtimestamp(self.now_ms / 1000, timezone.utc).strftime('%Y-%m-%d')
            self.print_miss_days.add(day)
            self.known_path = False
            self.unknown_from = self.unknown_from or self.now_ms
            self.funnel['ioc_zero'] += 1
            return []
        remain = quantity
        segments = []
        for stamp, price, qty in rows:
            if side == 'BUY' and price > limit:
                continue
            if side == 'SELL' and price < limit:
                continue
            take = min(remain, qty)
            segments.append((stamp, take))
            remain -= take
            if remain <= 0:
                break
        if not segments:
            self.funnel['ioc_zero'] += 1
            return []
        self.funnel['ioc_filled'] += 1
        return segments

    def _reply(self, method, path, params):
        changes = method != 'GET' and (path.endswith('/algoOrder') or path.endswith('/positionMargin') or (
            path.endswith('/order') and method == 'POST'
            and (params.get('reduceOnly') == 'true' or params.get('type') == 'MARKET')))
        if changes:
            self._settle_change()
        answer = self._answer(method, path, params)
        if changes:
            self.held_from = self.now_ms
        return answer

    def _answer(self, method, path, params):
        if self.unknown_from is not None and method == 'POST' and path.endswith('/order') and params.get('reduceOnly') != 'true':
            # The coordinator already journaled this identity. A raised send is
            # indistinguishable from a lost response, so return a terminal reject
            # that a later query can settle. The fill itself is still refused.
            return self._reject_new_exposure(params)
        if path.endswith('/klines'):
            step = {'4h': 14_400_000, '1m': MINUTE}.get(params.get('interval'))
            if step is None:
                raise Unknown('unsupported historical interval')
            start, end = int(params['startTime']), int(params['endTime'])
            rows = []
            cursor = start
            while cursor <= end:
                if cursor + step - 1 > self.now_ms:
                    break
                values = self.market.bar4(cursor) if step != MINUTE else self.market.minute('trade', cursor)
                if values is None:
                    break
                open_, high, low, close, volume = values
                rows.append([cursor, _text(open_), _text(high), _text(low), _text(close), _text(volume),
                             cursor + step - 1, '0', '0', '0', '0', '0'])
                cursor += step
            return rows
        if path.endswith('/time'):
            return {'serverTime': self.now_ms}
        if path == '/api/v3/account':
            return {'uid': self.uid}
        if path.endswith('/accountConfig'):
            return dict(dualSidePosition=False, multiAssetsMargin=False)
        if path.endswith('/symbolConfig'):
            return [dict(symbol='BTCUSDT', marginType='ISOLATED', leverage=20, isAutoAddMargin=False)]
        if path.endswith('/exchangeInfo'):
            return {'symbols': [self.rules]}
        if path.endswith('/commissionRate'):
            return dict(symbol='BTCUSDT', takerCommissionRate=_text(self.fee), makerCommissionRate=_text(self.fee))
        if path.endswith('/leverageBracket'):
            return dict(symbol='BTCUSDT', brackets=[dict(
                notionalFloor='0', notionalCap='100000000', maintMarginRatio=_text(MAINTENANCE),
                cum='0', initialLeverage=20)])
        if path.endswith('/premiumIndex'):
            observed, mark = self._mark_state()
            self._last_mark = mark
            return dict(symbol='BTCUSDT', time=observed, markPrice=_text(mark))
        if path.endswith('/depth'):
            observed, bid, ask, volume = self._book()
            return dict(E=observed, bids=[[_text(bid), _text(volume)]], asks=[[_text(ask), _text(volume)]])
        if path.endswith('/income'):
            start, end = int(params.get('startTime', 0)), int(params.get('endTime', self.now_ms))
            rows = [dict(row) for row in self.income if start <= row['time'] <= end]
            page = int(params.get('page', 1))
            limit = int(params.get('limit', 1000))
            return rows[(page - 1) * limit:page * limit]
        if path.endswith('/userTrades') and method == 'GET':
            rows = self.trades
            if 'fromId' in params:
                rows = [row for row in rows if row['id'] >= int(params['fromId'])]
            if 'startTime' in params:
                rows = [row for row in rows if int(params['startTime']) <= row['time'] <= int(params.get('endTime', self.now_ms))]
            limit = int(params.get('limit', 1000))
            if 'fromId' in params or 'startTime' in params:
                return [dict(row) for row in rows[:limit]]
            return [dict(row) for row in rows[-limit:]]
        if path.endswith('/positionRisk'):
            _observed, mark = self._mark_state()
            return [self._position(mark)]
        if path == '/fapi/v3/account':
            _observed, mark = self._mark_state()
            position = self._position(mark)
            pnl = D(position['unRealizedProfit'])
            available = self.wallet - (self.margin if self.q else D(0))
            return dict(assets=[dict(asset='USDT', walletBalance=_text(self.wallet), updateTime=self._update_time())],
                        positions=[position], totalWalletBalance=_text(self.wallet),
                        totalUnrealizedProfit=_text(pnl), totalMarginBalance=_text(self.wallet + pnl),
                        availableBalance=_text(available))
        if path.endswith('/openOrders'):
            return self._working_orders()
        if path.endswith('/openAlgoOrders'):
            return self._working_algos()
        if path.endswith('/order') and method == 'GET':
            if 'origClientOrderId' in params:
                order = self.orders.get(params['origClientOrderId'])
            else:
                order = self.by_order_id.get(int(params['orderId']))
            if order is None:
                raise Unknown('historical order unknown')
            return dict(order)
        if path.endswith('/algoOrder') and method == 'GET':
            algo = self.algos.get(params['clientAlgoId'])
            if algo is None:
                raise Unknown('historical protection unknown')
            return dict(algo)
        if path.endswith('/positionMargin') and method == 'POST':
            if not self.q:
                raise Unknown('isolated margin change without a position')
            amount = D(params['amount'])
            if params.get('type') != 1 or amount <= 0:
                _refuse(-4004, 'only adding isolated margin is modelled')
            if amount > self.wallet - self.margin:
                _refuse(-2019, 'Margin is insufficient.')
            self.margin += amount
            return dict(code=200, type=1, amount=_text(amount))
        if path.endswith('/algoOrder') and method == 'DELETE':
            algo = self.algos.get(params['clientAlgoId'])
            if algo is None:
                raise Unknown('historical protection unknown')
            algo['algoStatus'] = 'CANCELED'
            return {}
        if path.endswith('/order') and method == 'DELETE':
            order = self.orders.get(params['origClientOrderId'])
            if order is None:
                raise Unknown('historical order unknown')
            if order['status'] not in ('FILLED', 'CANCELED', 'EXPIRED', 'EXPIRED_IN_MATCH', 'REJECTED'):
                order['status'] = 'CANCELED'
            return {}
        if path.endswith('/algoOrder') and method == 'POST':
            _observed, mark = self._mark_state()
            trigger = D(params['triggerPrice'])
            through = (trigger >= mark) if (params['type'] == 'STOP_MARKET') == (params['side'] == 'SELL') else (trigger <= mark)
            if through:
                _refuse(-2021, 'Order would immediately trigger.')
            algo_id = self._id()
            algo = dict(symbol='BTCUSDT', algoId=algo_id, clientAlgoId=params['clientAlgoId'],
                        side=params['side'], positionSide='BOTH', orderType=params['type'],
                        algoType='CONDITIONAL', createTime=self.now_ms,
                        algoStatus='NEW', closePosition=True, workingType='MARK_PRICE',
                        priceProtect=False, triggerPrice=params['triggerPrice'], actualOrderId='0')
            self.algos[params['clientAlgoId']] = algo
            self.funnel['protections'] += 1
            return dict(algo)
        if path.endswith('/order') and method == 'POST':
            return self._accept_order(params)
        raise Unknown('historical venue has no response for ' + path)

    def _reject_new_exposure(self, params):
        order_id = self._id()
        order = dict(symbol='BTCUSDT', orderId=order_id, clientOrderId=params['newClientOrderId'],
                     side=params['side'], positionSide='BOTH', type=params['type'],
                     origQty=_text(params['quantity']), executedQty='0', price=params.get('price', '0'),
                     reduceOnly=False, status='REJECTED')
        self.orders[order['clientOrderId']] = order
        self.by_order_id[order_id] = order
        self.funnel['ioc_zero'] += 1
        return dict(order)

    def _accept_order(self, params):
        if self.unknown_from is not None and params.get('reduceOnly') != 'true':
            return self._reject_new_exposure(params)
        order_id = self._id()
        reduce = params.get('reduceOnly') == 'true'
        quantity = D(params['quantity'])
        order = dict(symbol='BTCUSDT', orderId=order_id, clientOrderId=params['newClientOrderId'],
                     side=params['side'], positionSide='BOTH', type=params['type'],
                     origQty=_text(quantity), executedQty='0', price=params.get('price', '0'),
                     reduceOnly=reduce, status='NEW')
        if reduce or params.get('type') == 'MARKET':
            closing = 'SELL' if self.q > 0 else 'BUY'
            if reduce and (not self.q or params['side'] != closing):
                # Protection may have closed the position while the order travelled.
                _refuse(-2022, 'ReduceOnly Order is rejected.')
            if not self.q or params['side'] != closing:
                order['status'] = 'EXPIRED'
            else:
                quantity = min(quantity, abs(self.q))
                if self.prints is None:
                    _observed, price = self._mark_state()
                else:
                    _observed, price = self._last_print()
                price = self._slipped(price, self.market_slippage)
                realized = self._apply_close(quantity, price)
                order['status'] = 'FILLED' if quantity == D(params['quantity']) else 'EXPIRED'
                order['executedQty'] = _text(quantity)
                order['price'] = _text(price)
                self._trade(params['side'], order_id, quantity, price, realized)
        elif quantity * D(params['price']) * (D(1) / 20 + self.fee) > self.wallet - self.margin:
            order['status'] = 'REJECTED'
            self.funnel['ioc_zero'] += 1
        else:
            self.funnel['ioc_submitted'] += 1
            arrival = self.now_ms
            self.orders[order['clientOrderId']] = order
            self.by_order_id[order_id] = order
            filled = D(0)
            adding = bool(self.q)
            closes = self.funnel['triggers'] + self.funnel['liquidations']
            for stamp, part in self._fill_ioc(params['side'], D(params['price']), quantity):
                # Each matched print books at its own time, after earlier funding
                # and protection events.
                closed = lambda: (adding or filled) and (
                    not self.q or self.funnel['triggers'] + self.funnel['liquidations'] != closes)
                self._advance(stamp)
                if closed():
                    break  # the rest of an add must not reopen a stopped position
                self._settle_change()
                if closed():
                    break
                realized = self._apply_open(params['side'], part, D(params['price']))
                self._trade(params['side'], order_id, part, D(params['price']), realized)
                self.held_from = self.now_ms
                filled += part
            order['executedQty'] = _text(filled)
            order['status'] = 'FILLED' if filled == quantity else 'EXPIRED'
            if params.get('timeInForce') == 'IOC':
                # The response follows the print window the fill was measured on.
                self._advance(max(self.now_ms, arrival + self.print_window_ms))
            return dict(order)
        self.orders[order['clientOrderId']] = order
        self.by_order_id[order_id] = order
        return dict(order)
