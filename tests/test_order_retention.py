"""Order retention, ambiguous outcomes, exit slices and account locks."""
import json
import tempfile
import unittest
from decimal import Decimal as D

from coinquant.binance import REJECT_CODES, market_quantity
from coinquant.binance_safety import send_once
from coinquant.lifecycle import Lifecycle
from coinquant.state import State
from coinquant.types import Blocked, Unknown
from tests.session_venue import Venue
from tests.test_binance_quantity import instrument
from tests import test_margin_intents as margin_fixture


class RejectCodeTests(unittest.TestCase):
    def setUp(self):
        self.inner = margin_fixture.WriteClassificationTests('test_expired_deadline_is_recorded_as_never_sent')
        self.inner.setUp()

    def tearDown(self):
        self.inner.tearDown()

    def test_duplicate_client_id_and_triggering_stop_stay_unknown(self):
        for code in (-4116, -4117, -4115, -4111):
            self.assertNotIn(code, REJECT_CODES)
            self.inner.state.db.execute('DELETE FROM intents')
            self.inner.state.db.commit()
            reader, _http_calls = self.inner.reader(margin_fixture.rejection(400, code))
            self.assertEqual(self.inner.attempt(reader)[0], 'unknown', code)


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


class AbsentOrderTests(unittest.TestCase):
    def test_explicit_missing_inside_retention_is_terminal_and_stays_terminal(self):
        tmp = tempfile.TemporaryDirectory()
        now = [1770004800.0]
        venue = Venue()
        venue.now = int(now[0] * 1000)
        venue.clock = lambda: now[0]
        with State(tmp.name, 'binance:BTCUSDT:live:123') as state:
            payload = dict(symbol='BTCUSDT', side='BUY', positionSide='BOTH', type='LIMIT', quantity='0.001')
            state.prepare('cq-x', 'binance_order', payload, result={'prepared_at_ms': int(now[0] * 1000)})
            now[0] += 301
            venue.now += 301000
            venue.clock = lambda: now[0]
            self.assertTrue(venue.absent_within_retention(state, {'id': 'cq-x', 'status': 'unknown'}))
            self.assertEqual(state.db.execute("SELECT status FROM intents WHERE id='cq-x'").fetchone()[0], 'rejected')
            venue.recover_pending(state)
            self.assertEqual(state.db.execute("SELECT status FROM intents WHERE id='cq-x'").fetchone()[0], 'rejected')
        tmp.cleanup()

    def test_missing_before_expiry_or_after_retention_stays_unknown(self):
        tmp = tempfile.TemporaryDirectory()
        now = [1770004800.0]
        venue = Venue()
        venue.now = int(now[0] * 1000)
        venue.clock = lambda: now[0]
        with State(tmp.name, 'binance:BTCUSDT:live:123') as state:
            payload = dict(symbol='BTCUSDT', side='BUY', positionSide='BOTH', type='LIMIT', quantity='0.001')
            state.prepare('cq-x', 'binance_order', payload, result={'prepared_at_ms': int(now[0] * 1000)})
            now[0] += 299
            venue.clock = lambda: now[0]
            self.assertFalse(venue.absent_within_retention(state, {'id': 'cq-x', 'status': 'unknown'}))
            now[0] += 2 * 86400
            venue.clock = lambda: now[0]
            self.assertFalse(venue.absent_within_retention(state, {'id': 'cq-x', 'status': 'unknown'}))
            self.assertEqual(state.pending()[0]['status'], 'unknown')
        tmp.cleanup()


class WriterHostTests(unittest.TestCase):
    def test_a_live_writer_on_another_machine_blocks_the_next_open(self):
        tmp = tempfile.TemporaryDirectory()
        with State(tmp.name, 'binance:BTCUSDT:live:host') as state:
            state.set('writer_host', {'host': 'other-host', 'pid': 1, 'at': __import__('time').time()})
        with self.assertRaises(Blocked):
            State(tmp.name, 'binance:BTCUSDT:live:host').__enter__()
        import sqlite3
        connection = sqlite3.connect(tmp.name + '/intents.sqlite')
        connection.execute("UPDATE meta SET value=? WHERE key='writer_host'",
                           (json.dumps({'host': 'other-host', 'pid': 1, 'at': 1.0}),))
        connection.commit()
        connection.close()
        with State(tmp.name, 'binance:BTCUSDT:live:host') as state:
            self.assertEqual(state.get('writer_host')['host'], __import__('socket').gethostname())
        tmp.cleanup()


if __name__ == '__main__':
    unittest.main()
