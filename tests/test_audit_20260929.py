"""Offline checks for the 2026-09-29 review: exit slices, reject codes, locks, trial paths."""
import json
import tempfile
import unittest
from decimal import Decimal as D
from email.message import Message
from io import BytesIO
from urllib.error import HTTPError

from coinquant.binance import REJECT_CODES, market_quantity
from coinquant.binance_safety import send_once
from coinquant.lifecycle import Lifecycle
from coinquant.state import State
from coinquant.types import Blocked, Unknown
from research.rebuild import _allowed_output, scratch_dir
from tests.session_venue import Venue
from tests.test_binance_quantity import instrument
from tests.test_margin_intents import WriteClassificationTests


def _http(status, code):
    body = json.dumps(dict(code=code, msg='fixture')).encode()
    return HTTPError('https://fapi.binance.com/fapi/v1/order', status, 'fixture', Message(), BytesIO(body))


class RejectCodeTests(unittest.TestCase):
    def setUp(self):
        self.inner = WriteClassificationTests('test_documented_native_rejection_is_terminal')
        self.inner.setUp()

    def tearDown(self):
        self.inner.tearDown()

    def test_duplicate_client_id_and_triggering_stop_stay_unknown(self):
        for code in (-4116, -4117, -4115, -4111):
            self.assertNotIn(code, REJECT_CODES)
            self.inner.state.db.execute('DELETE FROM intents')
            self.inner.state.db.commit()
            reader, _http_calls = self.inner.reader(_http(400, code))
            self.assertEqual(self.inner.attempt(reader)[0], 'unknown', code)

    def test_plain_parameter_rejection_is_still_terminal(self):
        self.assertIn(-4164, REJECT_CODES)
        reader, _http_calls = self.inner.reader(_http(400, -4164))
        self.assertEqual(self.inner.attempt(reader)[0], 'rejected')

    def test_lost_send_records_only_the_error_type(self):
        payload = dict(self.inner.payload)
        self.inner.state.prepare('cq-x', 'binance_order', payload, result={'prepared_at_ms': 1})
        send_once(self.inner.state, 'cq-x', lambda *args: (_ for _ in ()).throw(TimeoutError('secret')),
                  'POST', '/fapi/v1/order', payload)
        status, result = self.inner.state.db.execute("SELECT status,result FROM intents WHERE id='cq-x'").fetchone()
        self.assertEqual(status, 'unknown')
        saved = json.loads(result)
        self.assertEqual(saved['unresolved']['error_type'], 'TimeoutError')
        self.assertNotIn('secret', result)


class QuantityRuleTests(unittest.TestCase):
    def test_limit_entry_does_not_use_the_market_lot_cap(self):
        rules = instrument()
        self.assertEqual(market_quantity('150', '10000', rules, order='LIMIT'), D('150'))
        self.assertEqual(market_quantity('150', '10000', rules), D('120'))


class ExitSliceTests(unittest.TestCase):
    def test_close_sends_the_market_cap_then_the_remainder(self):
        tmp = tempfile.TemporaryDirectory()
        venue = Venue()
        venue.q = D('150')
        venue.entry = D('100000')
        venue.margin = D('1000')
        venue.wallet = D('5000')
        venue.rules = instrument()
        venue.rules['filters'].append(dict(filterType='PRICE_FILTER', tickSize='.1', minPrice='1', maxPrice='1000000'))
        venue.rules.update(status='TRADING', contractType='PERPETUAL', marginAsset='USDT', quotePrecision=8)
        with State(tmp.name, 'binance:BTCUSDT:live:123') as state:
            life = Lifecycle(venue, state, '123', authorized=True)
            with self.assertRaises(Unknown):
                life.close(venue.snapshot('123'))
            first = [p['quantity'] for _, path, p in venue.sent if p.get('reduceOnly') == 'true']
            self.assertEqual([D(q) for q in first], [D('120')])
            life.close(venue.snapshot('123'))
            sent = [p['quantity'] for _, path, p in venue.sent if p.get('reduceOnly') == 'true']
            self.assertEqual([D(q) for q in sent], [D('120'), D('30')])
            self.assertEqual(venue.q, 0)
        tmp.cleanup()


class AccountLockTests(unittest.TestCase):
    def test_same_account_in_two_directories_cannot_both_write(self):
        one, two = tempfile.TemporaryDirectory(), tempfile.TemporaryDirectory()
        held = State(one.name, 'binance:BTCUSDT:live:lock').__enter__()
        try:
            with self.assertRaises(Blocked):
                State(two.name, 'binance:BTCUSDT:live:lock').__enter__()
        finally:
            held.__exit__(None, None, None)
            one.cleanup()
            two.cleanup()


class TrialPathTests(unittest.TestCase):
    def test_names_and_output_roots_are_bounded(self):
        self.assertEqual(scratch_dir('P7').name, 'cq-P7')
        with self.assertRaises(ValueError):
            scratch_dir('../P7')
        with self.assertRaises(ValueError):
            scratch_dir('a/b')
        self.assertTrue(_allowed_output('/tmp/coinquant-partial'))
        self.assertFalse(_allowed_output('/'))


if __name__ == '__main__':
    unittest.main()
