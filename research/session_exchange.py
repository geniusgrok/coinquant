"""Historical matching behind the production Binance adapter.

Market rows and fills are the replacement boundary. Order checks, weight, and
the session coordinator stay on the production path. This is not a live venue
and it does not know the future session schedule.
"""
from decimal import Decimal as D
import json
from pathlib import Path

from coinquant.binance import Binance
from coinquant.types import Unknown


FEE = D('0.00075')          # research proxy, not an account commission schedule
MAINTENANCE = D('0.005')    # single 20x tier proxy, not dated brackets
LIQUIDATION_FEE = D('0.0125')  # field on the 2026-09-26 public rules snapshot
RULES_PATH = Path(__file__).resolve().parents[1] / 'evidence' / 'bounded-session-20260926' / 'public' / 'rules.json'
MINUTE = 60_000


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
                       'protections': 0, 'triggers': 0, 'liquidations': 0, 'funding': 0}
        self.unknown_from = None
        self.peak_cny = D(10000)
        self.mdd_close = D(0)
        self.mdd_envelope = D(0)
        self.mdd_close_at = None
        self.mdd_envelope_at = None
        self.known_path = True
        self.rules = json.loads(RULES_PATH.read_text(encoding='utf-8'))['instrument']
        super().__init__(key='historical-proxy', secret='historical-proxy',
                         opener=_Offline(), authorize_writes=True,
                         clock=lambda: self.now_ms / 1000,
                         monotonic=lambda: self.now_ms / 1000.0)
        self._note_cash()

    def _transport(self, request, timeout):
        method, path, params = self._inflight
        if method != 'GET':
            self.sent.append((method, path, dict(params)))
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
        open_ms, observed = self._completed_minute()
        if open_ms is None:
            raise Unknown('completed minute unavailable')
        row = self.market.minute('mark', open_ms)
        if row is None:
            raise Unknown('completed mark minute unavailable')
        return observed, row[3]

    def _completed_minute(self):
        boundary = self.now_ms // MINUTE * MINUTE
        open_ms = boundary - MINUTE
        if open_ms < 0:
            return None, None
        return open_ms, boundary

    def _book(self):
        open_ms, observed = self._completed_minute()
        if open_ms is None:
            raise Unknown('completed trade minute unavailable')
        row = self.market.minute('trade', open_ms)
        if row is None:
            raise Unknown('completed trade minute unavailable')
        close, volume = row[3], row[4]
        tick = D(self._price_filter()['tickSize'])
        bid = close - tick
        if bid <= 0 or volume <= 0:
            raise Unknown('completed minute has no positive book proxy')
        return observed, bid, close, volume

    def _price_filter(self):
        rows = [item for item in self.rules['filters'] if item.get('filterType') == 'PRICE_FILTER']
        if len(rows) != 1:
            raise Unknown('price filter unavailable')
        return rows[0]

    def _liquidation(self):
        if not self.q:
            return D(0)
        # Same shape as the linear proxy. Dated brackets are not claimed.
        return (self.q * self.entry - self.margin) / (self.q - abs(self.q) * (MAINTENANCE + FEE))

    def _position(self, mark):
        pnl = self.q * (mark - self.entry) if self.q else D(0)
        liq = self._liquidation()
        return dict(symbol='BTCUSDT', positionSide='BOTH', positionAmt=_text(self.q),
                    entryPrice=_text(self.entry if self.q else 0), isolatedWallet=_text(self.margin if self.q else 0),
                    updateTime=self.now_ms, marginAsset='USDT', markPrice=_text(mark),
                    unRealizedProfit=_text(pnl), liquidationPrice=_text(liq if self.q else 0))

    def _note(self, price, kind):
        equity = self.wallet + (self.q * (D(price) - self.entry) if self.q else D(0))
        cny = equity * D('6.9762')
        if cny > self.peak_cny:
            self.peak_cny = cny
        if self.peak_cny > 0:
            drawdown = 1 - cny / self.peak_cny
            if kind == 'envelope':
                if drawdown > self.mdd_envelope:
                    self.mdd_envelope = drawdown
                    self.mdd_envelope_at = self.now_ms
            elif self.known_path and drawdown > self.mdd_close:
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
        self._advance(self.now_ms + int(D(seconds) * 1000))

    def _advance(self, until_ms):
        while self.now_ms < until_ms:
            if not self.q:
                self.now_ms = until_ms
                self._note_cash()
                return
            boundary = (self.now_ms // MINUTE + 1) * MINUTE
            step = min(until_ms, boundary)
            self._pay_funding(self.now_ms, step)
            if self.q and step == boundary:
                self._on_minute(boundary - MINUTE)
            self.now_ms = step
        self._note_cash()

    def _note_cash(self):
        if not self.q:
            equity = self.wallet * D('6.9762')
            if equity > self.peak_cny:
                self.peak_cny = equity
            if self.peak_cny > 0 and self.known_path:
                drawdown = 1 - equity / self.peak_cny
                if drawdown > self.mdd_close:
                    self.mdd_close = drawdown
                    self.mdd_close_at = self.now_ms
                if drawdown > self.mdd_envelope:
                    self.mdd_envelope = drawdown
                    self.mdd_envelope_at = self.now_ms

    def _pay_funding(self, start_ms, end_ms):
        if not self.q:
            return
        events, gap = self.market.funding_between(start_ms, end_ms)
        for stamp, rate in events:
            mark_row = self.market.minute('mark', (stamp // MINUTE) * MINUTE - MINUTE)
            mark = mark_row[3] if mark_row is not None else self.entry
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
        row = self.market.minute('mark', open_ms)
        if row is None or not self.q:
            if self.q and row is None:
                self.known_path = False
                self.unknown_from = self.unknown_from or open_ms
            return
        open_, high, low, close, _volume = row
        long = self.q > 0
        stop, take = self._triggers()
        liq = self._liquidation()
        adverse = low if long else high
        self._note(adverse, 'envelope')
        self._note(close, 'close')
        hits = []
        if stop is not None and (low <= stop if long else high >= stop):
            hits.append('stop')
        if take is not None and (high >= take if long else low <= take):
            hits.append('take')
        if (low <= liq if long else high >= liq):
            hits.append('liq')
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

    def _triggers(self):
        stop = take = None
        for algo in self.algos.values():
            if algo.get('algoStatus') != 'NEW':
                continue
            price = D(algo['triggerPrice'])
            if algo['orderType'] == 'STOP_MARKET':
                stop = price
            elif algo['orderType'] == 'TAKE_PROFIT_MARKET':
                take = price
        return stop, take

    def _trigger(self, kind, price):
        algo = next((item for item in self.algos.values()
                     if item['algoStatus'] == 'NEW' and item['orderType'] == kind), None)
        if algo is None or not self.q:
            return
        self._close_all(price, algo)
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
        self._apply_close(quantity, price)
        self._trade(side, child_id, quantity, price)
        algo['algoStatus'] = 'FINISHED'
        algo['actualOrderId'] = str(child_id)
        for other in self.algos.values():
            if other is not algo and other['algoStatus'] == 'NEW':
                other['algoStatus'] = 'CANCELED'

    def _apply_open(self, side, quantity, price):
        fee = quantity * price * FEE
        self.wallet -= fee
        self.fees += fee
        self.q = quantity if side == 'BUY' else -quantity
        self.entry = price
        self.margin = quantity * price / 20
        self._income('COMMISSION', self.now_ms, -fee)

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
        fee = quantity * price * FEE
        self.wallet += realized - fee
        self.fees += fee
        if not self.q:
            self.entry = self.margin = D(0)
        else:
            self.margin *= (original - quantity) / original
        self._income('REALIZED_PNL', self.now_ms, realized)
        self._income('COMMISSION', self.now_ms, -fee)

    def _trade(self, side, order_id, quantity, price):
        self.trades.append(dict(symbol='BTCUSDT', positionSide='BOTH', side=side, orderId=order_id,
                                id=len(self.trades) + 1, time=self.now_ms, qty=_text(quantity),
                                price=_text(price)))

    def _working_orders(self):
        return [dict(order) for order in self.orders.values() if order['status'] in ('NEW', 'PARTIALLY_FILLED')]

    def _working_algos(self):
        return [dict(algo) for algo in self.algos.values() if algo['algoStatus'] == 'NEW']

    def _fill_ioc(self, side, limit, quantity):
        """Primary rule needs a trade print after the request. None are loaded here."""
        if self.matcher == 'unresolved':
            self.funnel['ioc_zero'] += 1
            return D(0)
        if self.matcher == 'trade_print':
            return self._fill_from_prints(side, limit, quantity)
        if self.matcher != 'bar_through':
            raise ValueError('unknown matcher')
        # Non-causal sensitivity: the minute that contains the latency instant.
        # A whole-bar print is still not a book. Callers must not treat it as a pass.
        instant = self.now_ms + 1000
        open_ms = instant // MINUTE * MINUTE
        row = self.market.minute('trade', open_ms)
        if row is None:
            self.funnel['ioc_zero'] += 1
            return D(0)
        _open, high, low, _close, _volume = row
        through = high <= limit if side == 'BUY' else low >= limit
        if not through:
            self.funnel['ioc_zero'] += 1
            return D(0)
        self.funnel['ioc_filled'] += 1
        return quantity

    def _fill_from_prints(self, side, limit, quantity):
        """Quantity is an upper bound: the whole matching print can be taken.

        The fill price stays at the limit. A missing official file is unknown,
        which is different from a present file that contains no matching print.
        """
        if self.prints is None:
            raise Unknown('trade prints were not loaded')
        start, end = self.now_ms + 1000, self.now_ms + 2000
        rows = self.prints.window(start, end)
        if rows is None:
            self.known_path = False
            self.unknown_from = self.unknown_from or self.now_ms
            self.funnel['ioc_zero'] += 1
            return D(0)
        remain = quantity
        for price, qty in rows:
            if side == 'BUY' and price > limit:
                continue
            if side == 'SELL' and price < limit:
                continue
            remain -= min(remain, qty)
            if remain <= 0:
                break
        filled = quantity - remain
        if filled <= 0:
            self.funnel['ioc_zero'] += 1
            return D(0)
        self.funnel['ioc_filled'] += 1
        return filled

    def _reply(self, method, path, params):
        if self.unknown_from is not None and method == 'POST' and path.endswith('/order') and params.get('reduceOnly') != 'true':
            raise Unknown('trigger sequence unknown; no new exposure')
        if path.endswith('/klines'):
            step = {'4h': 14_400_000, '1m': MINUTE}.get(params.get('interval'))
            if step is None:
                raise Unknown('unsupported historical interval')
            start, end = int(params['startTime']), int(params['endTime'])
            rows = []
            cursor = start
            while cursor <= end:
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
            return dict(symbol='BTCUSDT', takerCommissionRate=_text(FEE), makerCommissionRate=_text(FEE))
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
            return dict(assets=[dict(asset='USDT', walletBalance=_text(self.wallet), updateTime=self.now_ms)],
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
            amount = D(params['amount'])
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
            algo_id = self._id()
            algo = dict(symbol='BTCUSDT', algoId=algo_id, clientAlgoId=params['clientAlgoId'],
                        side=params['side'], positionSide='BOTH', orderType=params['type'],
                        algoStatus='NEW', closePosition=True, workingType='MARK_PRICE',
                        priceProtect=False, triggerPrice=params['triggerPrice'], actualOrderId='0')
            self.algos[params['clientAlgoId']] = algo
            self.funnel['protections'] += 1
            return dict(algo)
        if path.endswith('/order') and method == 'POST':
            return self._accept_order(params)
        raise Unknown('historical venue has no response for ' + path)

    def _accept_order(self, params):
        if self.unknown_from is not None and params.get('reduceOnly') != 'true':
            raise Unknown('trigger sequence unknown; no new exposure')
        order_id = self._id()
        reduce = params.get('reduceOnly') == 'true'
        quantity = D(params['quantity'])
        order = dict(symbol='BTCUSDT', orderId=order_id, clientOrderId=params['newClientOrderId'],
                     side=params['side'], positionSide='BOTH', type=params['type'],
                     origQty=_text(quantity), executedQty='0', price=params.get('price', '0'),
                     reduceOnly=reduce, status='NEW')
        if reduce or params.get('type') == 'MARKET':
            _observed, mark = self._mark_state()
            self._apply_close(quantity, mark)
            order['status'] = 'FILLED'
            order['executedQty'] = _text(quantity)
            order['price'] = _text(mark)
            self._trade(params['side'], order_id, quantity, mark)
        else:
            self.funnel['ioc_submitted'] += 1
            filled = self._fill_ioc(params['side'], D(params['price']), quantity)
            if filled <= 0:
                order['status'] = 'EXPIRED'
                order['executedQty'] = '0'
            elif filled < quantity:
                order['status'] = 'EXPIRED'
                order['executedQty'] = _text(filled)
                self._apply_open(params['side'], filled, D(params['price']))
                self._trade(params['side'], order_id, filled, D(params['price']))
            else:
                order['status'] = 'FILLED'
                order['executedQty'] = _text(filled)
                self._apply_open(params['side'], filled, D(params['price']))
                self._trade(params['side'], order_id, filled, D(params['price']))
        self.orders[order['clientOrderId']] = order
        self.by_order_id[order_id] = order
        return dict(order)
