"""Single production adapter: Bybit BTCUSD inverse, no sockets or mode writes."""
import time

from . import decode
from .config import Config
from .rest import Rest
from .types import (Bar, Blocked, CATEGORY, D, INTERVAL_MS, SYMBOL, Unknown,
                    number, serial)

SCOPE = {'category': CATEGORY, 'symbol': SYMBOL}
TERMINAL = {'Filled', 'Cancelled', 'Rejected', 'Deactivated', 'PartiallyFilledCanceled'}
ACTIVE = {'New', 'PartiallyFilled', 'Untriggered', 'Triggered', 'Created'}


class Bybit:
    def __init__(self, config: Config, *, execute=False, rest=None):
        self.config = config
        self.execute = execute
        self.rest = rest or Rest(config.environment, execute=execute)
        self.uid = None
        self.read_only_key = True
        self.instrument = None
        self.tiers = None
        self.fee = None

    def identity(self) -> str:
        # query-api includes the API key in its raw response. Retain ONLY the
        # UID and permission bit, never serialize or log that response.
        data = self.rest.get('/v5/user/query-api', private=True)
        uid = str(data.get('userID', ''))
        if not uid.isdigit() or int(uid) <= 0 or data.get('readOnly') not in (0, 1):
            raise Unknown('account UID or key access mode is unknown')
        self.uid, self.read_only_key = uid, data['readOnly'] == 1
        return uid

    def _position(self):
        return decode.one(self.rest.pages('/v5/position/list', SCOPE, private=True), 'BTCUSD position')

    def _orders(self):
        # No orderFilter: current endpoint returns ordinary AND conditional.
        rows = self.rest.pages('/v5/order/realtime', dict(SCOPE, openOnly=0, limit=50), private=True)
        if any(o.get('symbol') != SYMBOL or o.get('orderStatus') not in ACTIVE for o in rows):
            raise Unknown('unexpected order scope/status in active snapshot')
        return rows

    def snapshot(self):
        if self.uid is None:
            self.identity()
        if self.instrument is None:
            self.instrument = decode.one(self.rest.pages('/v5/market/instruments-info', SCOPE), 'instrument')
            self.tiers = self.rest.pages('/v5/market/risk-limit', SCOPE)
            self.fee = decode.one(self.rest.pages('/v5/account/fee-rate', SCOPE, private=True), 'fee rate')
        # Compare the sequence and native order records across observations so
        # a fill during reconciliation cannot be silently sized from stale state.
        for _ in range(2):
            account = self.rest.get('/v5/account/info', private=True)
            first = self._position()
            orders = self._orders()
            wallet = decode.one(self.rest.get('/v5/account/wallet-balance', {'accountType': 'UNIFIED'}, private=True)['list'], 'wallet')
            fills = self.rest.pages('/v5/execution/list', dict(SCOPE, limit=100), private=True)
            ticker = decode.one(self.rest.pages('/v5/market/tickers', SCOPE), 'ticker')
            book = self.rest.get('/v5/market/orderbook', dict(SCOPE, limit=50))
            second, last_orders = self._position(), self._orders()
            keys = ('seq', 'size', 'side', 'avgPrice', 'positionIM', 'takeProfit', 'stopLoss', 'leverage', 'positionIdx')
            if any(k not in first or k not in second for k in keys):
                raise Unknown('position sequence or required fields are missing')
            order_key = lambda o: (o['orderId'], o['orderStatus'], o['qty'], o['cumExecQty'], o['updatedTime'])
            if all(first[k] == second[k] for k in keys) and sorted(map(order_key, orders)) == sorted(map(order_key, last_orders)):
                return decode.snapshot(self.uid, int(time.time() * 1000), account, wallet, second,
                                       self.instrument, self.tiers, self.fee, ticker, book,
                                       last_orders, fills, self.config.model.slippage_fraction)
        raise Unknown('account changed during bounded reconciliation')

    def candles(self, now: int):
        result = self.rest.get('/v5/market/kline', dict(SCOPE, interval='240', limit=501))
        if result.get('symbol') != SYMBOL or result.get('category') != CATEGORY:
            raise Unknown('wrong candle instrument')
        bars = [Bar(int(r[0]), *(number(v) for v in r[1:6])) for r in result['list'] if int(r[0]) + INTERVAL_MS <= now]
        return sorted(bars, key=lambda bar: bar.time)

    def lookup(self, link: str):
        args = dict(SCOPE, orderLinkId=link, limit=50)
        for path in ('/v5/order/realtime', '/v5/order/history'):
            rows = self.rest.pages(path, args, private=True)
            if rows:
                row = decode.one(rows, 'client order identifier')
                if row.get('symbol') != SYMBOL or row.get('orderLinkId') != link:
                    raise Unknown('order identifier returned another order')
                return row
        return None  # Absence is NOT proof an uncertain send failed.

    def write(self, path: str, payload: dict):
        self.config.authorize(self.uid or '', self.execute)
        if self.read_only_key:
            raise Blocked('configured API key is read-only')
        allowed = {'/v5/order/create', '/v5/order/cancel', '/v5/order/amend',
                   '/v5/position/trading-stop', '/v5/position/add-margin'}
        if path not in allowed or payload.get('symbol') != SYMBOL or payload.get('category') != CATEGORY:
            raise Blocked('write outside authorized adapter scope')
        if payload.get('positionIdx', 0) != 0:
            raise Blocked('hedged position write refused')
        return self.rest.call('POST', path, serial(payload), private=True)['result']

    def place(self, link: str, delta: D, target, *, reduce_only=False):
        if not delta or (not reduce_only and abs(delta) > self.config.max_position_usd):
            raise Blocked('order size outside authorized scope')
        payload = dict(SCOPE, orderLinkId=link, positionIdx=0,
                       side='Buy' if delta > 0 else 'Sell', qty=str(abs(delta)),
                       orderType='Limit', price=str(target.entry), timeInForce='IOC', reduceOnly=reduce_only)
        if not reduce_only:
            if min(target.take_profit, target.stop_loss) <= 0:
                raise Blocked('entry requires full native TP and SL')
            payload.update(takeProfit=str(target.take_profit), stopLoss=str(target.stop_loss),
                           tpslMode='Full', tpOrderType='Market', slOrderType='Market',
                           tpTriggerBy='MarkPrice', slTriggerBy='MarkPrice')
        return self.write('/v5/order/create', payload)

    def cancel(self, link: str):
        if not link.startswith('pq-'):
            raise Blocked('unowned order cannot be cancelled')
        return self.write('/v5/order/cancel', dict(SCOPE, orderLinkId=link))

    def amend(self, link: str, target):
        if not link.startswith('pq-'):
            raise Blocked('unowned order cannot be amended')
        order = self.lookup(link)
        if not order or order.get('stopOrderType') not in ('', None) or order.get('reduceOnly') is not False:
            raise Blocked('ordinary entry amendment only; native TP/SL use trading-stop')
        if number(order['cumExecQty']) != 0:
            raise Blocked('partial fill raced amendment; reconcile position first')
        return self.write('/v5/order/amend', dict(SCOPE, orderLinkId=link,
                         qty=str(abs(target.quantity)), price=str(target.entry),
                         takeProfit=str(target.take_profit), stopLoss=str(target.stop_loss),
                         tpslMode='Full', tpTriggerBy='MarkPrice', slTriggerBy='MarkPrice'))

    def protect(self, target):
        if not target.quantity or min(target.take_profit, target.stop_loss) <= 0:
            raise Blocked('do not install opening protection on a flat position')
        return self.write('/v5/position/trading-stop', dict(SCOPE, positionIdx=0,
                          tpslMode='Full', takeProfit=str(target.take_profit), stopLoss=str(target.stop_loss),
                          tpTriggerBy='MarkPrice', slTriggerBy='MarkPrice', tpOrderType='Market', slOrderType='Market'))

    def margin(self, amount: D):
        if amount == 0 or amount % D('0.0001'):
            raise Blocked('margin must use the documented nonzero 4-decimal increment')
        return self.write('/v5/position/add-margin', dict(SCOPE, positionIdx=0, margin=str(amount)))
