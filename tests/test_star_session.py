from decimal import Decimal as D
from unittest import TestCase

from research.session_market import Market
from research.star_session import StarExchange, StarVenue


class Prints:
    loaded = {}
    def timed(self, start, end):
        return [(start + 10, D('100'), D('.5'))] if end > start + 10 else []
    def last(self, now):
        return now, D('100')


class SharedPeerTests(TestCase):
    def venue(self):
        start = 1577836860000
        rows = {stamp: (D(100), D('100.1'), D('99.9'), D(100), D(1000))
                for stamp in range(start - 60000, start + 240000, 60000)}
        market = Market({}, (), identity={'trade': dict(rows), 'mark': dict(rows)})
        exchange = StarExchange(market, start, D(1000), matcher='trade_print', prints=Prints())
        return exchange

    def test_peer_transport_preserves_market_and_contract_price_shapes(self):
        e = self.venue()
        venue = StarVenue(e)
        order = venue.place_market(client_id='en-test', side='BUY', qty='1', reduce_only=False)
        self.assertEqual(D(order['executedQty']), D('.5'))
        self.assertEqual(e.q, D('.5'))
        stop = venue.place_algo(client_id='sl-test', side='SELL', order_type='STOP_MARKET',
                                trigger_price='72', close_position=True, reduce_only=False,
                                qty='', working_type='CONTRACT_PRICE')
        self.assertEqual(stop['algoStatus'], 'NEW')
        self.assertEqual(stop['workingType'], 'CONTRACT_PRICE')
        self.assertEqual(venue.cancel_algo('sl-test')['algoStatus'], 'CANCELED')
        self.assertEqual(len(e.sent), 3)

    def test_short_partial_market_fill_and_add_keep_cash_identity(self):
        e = self.venue()
        initial = e.wallet
        order = e._accept_order({'newClientOrderId': 'short', 'type': 'MARKET', 'side': 'SELL',
                                 'quantity': '1', 'reduceOnly': 'false'})
        self.assertEqual(order['status'], 'EXPIRED')
        self.assertEqual(e.q, D('-.5'))
        e._accept_order({'newClientOrderId': 'add', 'type': 'MARKET', 'side': 'SELL',
                         'quantity': '.5', 'reduceOnly': 'false'})
        self.assertEqual(e.q, D('-1'))
        self.assertEqual(initial - e.wallet, e.fees)
        self.assertEqual(e.wallet - initial, sum(D(row['income']) for row in e.income))
        self.assertEqual(len(e.trades), 2)

    def test_contract_stop_does_not_use_mark_trigger_and_survives_stopped_process(self):
        e = self.venue()
        e._accept_order({'newClientOrderId': 'short', 'type': 'MARKET', 'side': 'SELL',
                         'quantity': '.5', 'reduceOnly': 'false'})
        e.margin = D(20)
        row = e._answer('POST', '/fapi/v1/algoOrder', {'clientAlgoId': 'stop', 'side': 'BUY',
             'type': 'STOP_MARKET', 'triggerPrice': '105', 'workingType': 'CONTRACT_PRICE'})
        self.assertEqual(row['workingType'], 'CONTRACT_PRICE')
        start = e.now_ms // 60000 * 60000
        e.market.identity['mark'][start] = (D(106), D(107), D(106), D(106), D(1))
        e.market.identity['trade'][start] = (D(100), D(101), D(99), D(100), D(1))
        e._on_minute(start)
        self.assertEqual(e.q, D('-.5'))
        e.market.identity['trade'][start + 60000] = (D(106), D(107), D(106), D(106), D(1))
        sent = len(e.sent)
        e._on_minute(start + 60000)
        self.assertEqual(e.q, 0)
        self.assertEqual(len(e.sent), sent)
        self.assertEqual(e.algos['stop']['algoStatus'], 'FINISHED')


# These saved scenarios seed legacy SX60/DFII10 checkpoints explicitly.
from tests.legacy_policy import legacy_policy
setUpModule, tearDownModule = legacy_policy()
