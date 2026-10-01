"""Starquant's production runner on Coinquant's historical venue; no network.

Import the peer explicitly in the research command. Production has no peer dependency.
"""
from decimal import Decimal as D
from urllib.error import HTTPError

from coinquant.types import Unknown
from research.session_exchange import SessionExchange, _text, MINUTE


class StarExchange(SessionExchange):
    def _accept_order(self, params):
        if params.get('type') != 'MARKET' or params.get('reduceOnly') == 'true':
            return super()._accept_order(params)
        if self.unknown_from is not None:
            return self._reject_new_exposure(params)
        side, wanted = params['side'], D(params['quantity'])
        if self.q and ((self.q > 0) != (side == 'BUY')):
            raise Unknown('opposite market entry requires a confirmed prior close')
        order_id = self._id()
        row = dict(symbol='BTCUSDT', orderId=order_id, clientOrderId=params['newClientOrderId'],
                   side=side, type='MARKET', positionSide='BOTH', origQty=_text(wanted),
                   executedQty='0', reduceOnly=False, price='0', status='NEW')
        self.orders[row['clientOrderId']] = row
        self.by_order_id[order_id] = row
        rows = self.prints.timed(self.now_ms, self.now_ms + self.print_window_ms)
        if rows is None:
            self.known_path = False
            self.unknown_from = self.now_ms
            row['status'] = 'EXPIRED'
            return dict(row)
        filled, value = D(0), D(0)
        prior_closes = self.funnel['triggers'] + self.funnel['liquidations']
        for stamp, price, available in rows:
            self._advance(stamp)
            if self.funnel['triggers'] + self.funnel['liquidations'] != prior_closes:
                break
            price *= 1 + self.market_slippage if side == 'BUY' else 1 - self.market_slippage
            part = min(wanted - filled, available)
            if part <= 0 or part * price * (D('.05') + self.fee) > self.wallet - self.margin:
                break
            self._settle_change()
            if self.funnel['triggers'] + self.funnel['liquidations'] != prior_closes:
                break
            self._apply_open(side, part, price)
            self._trade(side, order_id, part, price)
            self.held_from = self.now_ms
            filled += part
            value += part * price
            if filled == wanted:
                break
        row.update(status='FILLED' if filled == wanted else 'EXPIRED', executedQty=_text(filled),
                   price=_text(value / filled) if filled else '0')
        return dict(row)

    def _answer(self, method, path, params):
        if method == 'POST' and path.endswith('/algoOrder'):
            _, last = self._last_print()
            trigger = D(params['triggerPrice'])
            stop = params['type'] == 'STOP_MARKET'
            closing_long = params['side'] == 'SELL'
            if params.get('workingType') != 'CONTRACT_PRICE':
                raise Unknown('peer research expects the actual CONTRACT_PRICE protection')
            if (trigger >= last) if stop == closing_long else (trigger <= last):
                from research.session_exchange import _refuse
                _refuse(-2021, 'Order would immediately trigger.')
            row = dict(symbol='BTCUSDT', algoId=self._id(), clientAlgoId=params['clientAlgoId'],
                       side=params['side'], positionSide='BOTH', orderType=params['type'],
                       algoStatus='NEW', closePosition=True, workingType='CONTRACT_PRICE',
                       priceProtect=False, triggerPrice=params['triggerPrice'], actualOrderId='0')
            self.algos[row['clientAlgoId']] = row
            self.funnel['protections'] += 1
            return dict(row)
        return super()._answer(method, path, params)

    def _scan(self, start, end):
        if not self.q:
            return None
        previous = start // MINUTE * MINUTE - MINUTE
        mark, trade = self.market.minute('mark', previous), self.market.minute('trade', previous)
        if mark is None or trade is None:
            return None
        ratio = mark[3] / trade[3]
        stop, take = self._triggers()
        liq, long = self._liquidation(), self.q > 0
        for stamp, price, _qty in self.prints.timed(start, end) or []:
            self._note_at(stamp, price * ratio, 'envelope')
            if (price * ratio <= liq) if long else (price * ratio >= liq):
                return stamp, 'liq', liq
            if stop is not None and ((price <= stop) if long else (price >= stop)):
                return stamp, 'stop', price
            if take is not None and ((price >= take) if long else (price <= take)):
                return stamp, 'take', price
        return None

    def _on_minute(self, open_ms):
        if not self.q:
            return
        mark, trade = self.market.minute('mark', open_ms), self.market.minute('trade', open_ms)
        if mark is None or trade is None:
            # Preserve the accepted missing-mark policy; native peer protection is not
            # asserted to have fired when its required input is absent.
            return super()._on_minute(open_ms)
        long = self.q > 0
        stop, take = self._triggers()
        liq = self._liquidation()
        self._note(mark[1] if long else mark[2], 'favorable')
        self._note(mark[2] if long else mark[1], 'envelope')
        self._note(mark[3], 'close')
        hits = []
        if stop is not None and ((trade[2] <= stop) if long else (trade[1] >= stop)):
            hits.append('stop')
        if take is not None and ((trade[1] >= take) if long else (trade[2] <= take)):
            hits.append('take')
        if (mark[2] <= liq) if long else (mark[1] >= liq):
            hits.append('liq')
        if len(hits) > 1:
            self.known_path = False
            self.unknown_from = self.unknown_from or open_ms
        elif hits == ['liq']:
            self._liquidate(liq)
        elif hits:
            kind, level = ('STOP_MARKET', stop) if hits[0] == 'stop' else ('TAKE_PROFIT_MARKET', take)
            price = min(trade[0], level) if long == (hits[0] == 'stop') else max(trade[0], level)
            self._trigger(kind, price)

    def _partial(self, open_ms, at_boundary):
        self._on_minute(open_ms)


class StarVenue:
    """Map native venue records to the peer runner's existing Snapshot contract."""
    def __init__(self, exchange):
        self.exchange = exchange

    def snapshot(self):
        from btc_perp.model import Snapshot, Filters, RestingOrder, AlgoOrder, Trade, Income
        e = self.exchange
        try:
            first = e.get('/fapi/v3/account')
            positions = e.get('/fapi/v3/positionRisk', {'symbol': 'BTCUSDT'})
            orders = e.get('/fapi/v1/openOrders', {'symbol': 'BTCUSDT'})
            algos = e.get('/fapi/v1/openAlgoOrders', {'symbol': 'BTCUSDT'})
            second = e.get('/fapi/v3/account')
            def stable(account):
                return account['totalWalletBalance'], [(p['positionAmt'], p['entryPrice'], p['isolatedWallet'])
                                                       for p in account['positions']]
            if stable(first) != stable(second):
                raise Unknown('account changed during bounded snapshot')
            observed, last = e._last_print()
            p = positions[0]
            filters = {row['filterType']: row for row in e.rules['filters']}
            lot, tick = filters['LOT_SIZE'], filters['PRICE_FILTER']
            since = e.now_ms - 7 * 86_400_000
            return Snapshot(known=True, reason='', position_qty=float(p['positionAmt']),
                entry_price=float(p['entryPrice']), wallet_usdt=float(second['totalWalletBalance']),
                available_usdt=float(second['availableBalance']), mark_price=float(p['markPrice']),
                last_price=float(last), liquidation_price=float(p['liquidationPrice']), one_way=True,
                isolated=True, leverage=20, symbol_status='TRADING', server_time_ms=e.now_ms,
                orders=tuple(RestingOrder(row['clientOrderId'], row['side'], row['type'],
                    float(row['origQty']), float(row['executedQty']), row['reduceOnly'], row['status'],
                    float(row.get('price', 0)), str(row['orderId'])) for row in orders),
                algos=tuple(AlgoOrder(row['clientAlgoId'], row['orderType'], row['side'],
                    float(row['triggerPrice']), row['closePosition'], False, 0., row['algoStatus'],
                    row['workingType']) for row in algos),
                can_trade=True, fee_taker=float(e.fee),
                filters=Filters(float(tick['tickSize']), float(lot['stepSize']), float(lot['minQty']),
                    float(filters['MIN_NOTIONAL']['notional']), float(tick['minPrice']), float(tick['maxPrice'])),
                brackets_ok=True, recent_trades_ok=True, funding_ok=True, auto_add_margin_off=True,
                trades=tuple(Trade(row['id'], str(row['orderId']), row['side'], float(row['qty']), row['time'])
                    for row in e.trades if row['time'] >= since)[-1000:],
                income=tuple(Income(row['incomeType'], float(row['income']), row['time'])
                    for row in e.income if row['time'] >= since)[-1000:],
                clock_offset_ms=0, clock_rtt_ms=0, read_ms=e.now_ms)
        except (Unknown, HTTPError) as exc:
            return Snapshot(False, str(exc), 0., 0., 0., 0., 0., 0., 0., True, True, 20, 'TRADING', e.now_ms)

    def _send(self, method, path, params):
        try:
            return self.exchange.send(method, path, params)
        except HTTPError as exc:
            import json
            return json.loads(exc.read())

    def place_market(self, *, client_id, side, qty, reduce_only):
        return self._send('POST', '/fapi/v1/order', dict(symbol='BTCUSDT', newClientOrderId=client_id,
            side=side, quantity=qty, type='MARKET', reduceOnly='true' if reduce_only else 'false'))

    def place_algo(self, *, client_id, side, order_type, trigger_price, close_position,
                   reduce_only, qty, working_type):
        if not close_position or reduce_only or qty:
            raise Unknown('peer protection must be the actual full-position shape')
        return self._send('POST', '/fapi/v1/algoOrder', dict(symbol='BTCUSDT', clientAlgoId=client_id,
            side=side, type=order_type, triggerPrice=trigger_price, closePosition='true', workingType=working_type))

    def cancel_order(self, client_id):
        return self._send('DELETE', '/fapi/v1/order', {'symbol': 'BTCUSDT', 'origClientOrderId': client_id})

    def cancel_algo(self, client_id):
        self._send('DELETE', '/fapi/v1/algoOrder', {'symbol': 'BTCUSDT', 'clientAlgoId': client_id})
        return self.query_algo(client_id)

    def query_order(self, client_id):
        return self.exchange.get('/fapi/v1/order', {'symbol': 'BTCUSDT', 'origClientOrderId': client_id})

    def query_order_id(self, order_id):
        return self.exchange.get('/fapi/v1/order', {'symbol': 'BTCUSDT', 'orderId': order_id})

    def query_algo(self, client_id):
        return self.exchange.get('/fapi/v1/algoOrder', {'symbol': 'BTCUSDT', 'clientAlgoId': client_id})
