"""Offline documented-schema checks; these are NOT native exchange receipts."""
from dataclasses import replace
from decimal import Decimal as D
from io import BytesIO
import json
import time
import unittest

from coinquant import decode
from coinquant.bybit import Bybit
from coinquant.config import Config
from coinquant.execution import coverage, run_once
from coinquant.model import decide
from coinquant.rest import Rest
from coinquant.types import Blocked, Unknown
from test_execution import FakeVenue
from test_model import sample, history


class Opener:
    def __init__(self, code=0):
        self.calls = []
        self.code = code

    def open(self, request, timeout):
        self.calls.append(request)
        return BytesIO(json.dumps({'retCode': self.code, 'time': int(time.time() * 1000), 'result': {}}).encode())


class Capture:
    def __init__(self):
        self.calls = []

    def call(self, method, path, payload, **kwargs):
        self.calls.append((method, path, payload))
        return {'result': {'orderLinkId': payload.get('orderLinkId')}}


class AdapterTests(unittest.TestCase):
    def test_transport_never_retries_unknown_writes(self):
        opener = Opener(10000)
        rest = Rest('testnet', execute=True, opener=opener)
        with self.assertRaises(Unknown):
            rest.call('POST', '/v5/order/create', {'symbol': 'BTCUSD'})
        self.assertEqual(len(opener.calls), 1)
        with self.assertRaises(Blocked):
            Rest('testnet', opener=opener).call('POST', '/v5/order/create')
        self.assertEqual(len(opener.calls), 1)

    def test_transport_host_is_explicit_and_restricted_to_official_environment_hosts(self):
        self.assertEqual(Rest('live', opener=Opener()).base, 'https://api.bybit.com')
        self.assertEqual(Rest('live', api_host='api.manepa.jp', opener=Opener()).base,
                         'https://api.manepa.jp')
        self.assertEqual(Rest('testnet', api_host='api-testnet.manepa.jp', opener=Opener()).base,
                         'https://api-testnet.manepa.jp')
        with self.assertRaises(Blocked):
            Rest('live', api_host='example.com', opener=Opener())
        with self.assertRaises(Blocked):
            Rest('testnet', api_host='api.manepa.jp', opener=Opener())

    def test_missing_or_looping_pages_are_not_empty_account(self):
        rest = Rest('testnet', opener=Opener())
        rest.get = lambda *a, **k: {}
        with self.assertRaises(Unknown):
            rest.pages('/v5/order/realtime', {})
        rest.get = lambda *a, **k: {'list': [], 'nextPageCursor': 'repeated'}
        with self.assertRaises(Unknown):
            rest.pages('/v5/order/realtime', {})

    def test_native_parent_has_both_full_mark_market_protectors(self):
        capture = Capture()
        cfg = Config(account_uid='12345', max_position_usd=D(100000))
        venue = Bybit(cfg, execute=True, rest=capture)
        venue.uid, venue.read_only_key = '12345', False
        target = decide(history(), sample(), cfg.model)
        venue.place('cq-test', target.quantity, target)
        payload = capture.calls[-1][2]
        self.assertEqual(payload['symbol'], 'BTCUSD')
        self.assertEqual(payload['category'], 'inverse')
        self.assertEqual(payload['timeInForce'], 'IOC')
        self.assertEqual(payload['tpslMode'], 'Full')
        self.assertEqual(payload['tpTriggerBy'], 'MarkPrice')
        self.assertEqual(payload['slTriggerBy'], 'MarkPrice')
        self.assertEqual(payload['tpOrderType'], 'Market')
        self.assertEqual(payload['slOrderType'], 'Market')
        self.assertGreater(D(payload['takeProfit']), 0)
        self.assertGreater(D(payload['stopLoss']), 0)
        self.assertIs(payload['reduceOnly'], False)
        venue.place('cq-reduce', -target.quantity, target, reduce_only=True)
        payload = capture.calls[-1][2]
        self.assertIs(payload['reduceOnly'], True)
        self.assertNotIn('stopLoss', payload)
        self.assertNotIn('takeProfit', payload)

    def test_protection_amends_both_sides_without_a_cancel(self):
        capture = Capture()
        cfg = Config(account_uid='12345', max_position_usd=D(100000))
        venue = Bybit(cfg, execute=True, rest=capture)
        venue.uid, venue.read_only_key = '12345', False
        target = decide(history(), sample(), cfg.model)
        venue.protect(target)
        self.assertEqual(len(capture.calls), 1)
        self.assertEqual(capture.calls[0][1], '/v5/position/trading-stop')
        self.assertIn('takeProfit', capture.calls[0][2])
        self.assertIn('stopLoss', capture.calls[0][2])
        with self.assertRaises(Blocked):
            venue.protect(replace(target, quantity=D(0)))
        with self.assertRaises(Blocked):
            venue.write('/v5/position/set-leverage', {'symbol': 'BTCUSD', 'category': 'inverse'})

    def test_inverse_risk_units_and_market_close_capacity(self):
        instrument = dict(symbol='BTCUSD', contractType='InversePerpetual', settleCoin='BTC',
                          leverageFilter={'minLeverage': '1', 'maxLeverage': '100'},
                          lotSizeFilter=dict(qtyStep='1', minOrderQty='1', maxOrderQty='10000', maxMktOrderQty='5000'),
                          priceFilter={'tickSize': '.5'}, launchTime='1514764800000', status='Trading')
        tiers = [dict(symbol='BTCUSD', isLowestRisk=1, initialMargin='1', maxLeverage='100',
                      riskLimitValue='150', maintenanceMargin='.5')]
        r = decode.rules(instrument, tiers, {'takerFeeRate': '.00075'}, D(20000))
        self.assertEqual(r.maintenance_rate, D('.005'))
        self.assertEqual(r.risk_limit_usd, D(3000000))
        self.assertEqual(r.maximum, 5000)
        tiers[0]['initialMargin'] = '.01'
        with self.assertRaises(Blocked):
            decode.rules(instrument, tiers, {'takerFeeRate': '.00075'}, D(20000))
        with self.assertRaises(Unknown):
            decode.position({})

    def test_cancel_race_extra_fill_is_reconciled_not_ignored(self):
        import tempfile

        class RacingVenue(FakeVenue):
            def place(self, link, delta, target, *, reduce_only=False):
                self.last_target = target
                return super().place(link, delta, target, reduce_only=reduce_only)

            def cancel(self, link):
                self._fill(D(1), self.last_target, False)
                self.records[link]['cumExecQty'] = '3'
                return super().cancel(link)

        venue = RacingVenue(); venue.fill_limit = D(2); venue.cancel_race = True
        with tempfile.TemporaryDirectory() as directory:
            cfg = Config(account_uid='12345', max_position_usd=D(100000), state_dir=directory)
            report = run_once(venue, cfg, execute=True)
        self.assertEqual(report['status'], 'partial')
        self.assertEqual(venue.s.position.quantity, 3)
        self.assertTrue(coverage(venue.s))
        self.assertEqual(sum(w[0] == 'place' for w in venue.writes), 1)
        self.assertEqual([a['filled'] for a in report['actions'] if a['operation'] == 'increase'], ['3'])
