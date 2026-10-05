"""Native adapter limits, cleanup budgets and absent-order retirement."""
import io
import tempfile
from http.client import IncompleteRead
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from coinquant import binance_safety as safety
from coinquant.binance import Binance, MAX_CLOCK_ROUND_TRIP
from coinquant.config import Config
from coinquant.lifecycle import FINISH_SECONDS, REDUCE_SECONDS, Lifecycle
from coinquant.session import run
from coinquant.state import State
from coinquant.types import Blocked, NotSent, ObservationDeadline, Unknown
from tests.session_venue import Venue

SCOPE = 'binance:BTCUSDT:live:123'
ORDER = dict(symbol='BTCUSDT', positionSide='BOTH', side='BUY', type='LIMIT', timeInForce='IOC',
             quantity='.001', price='100000', newClientOrderId='cq-test')


def adapter(opener, **kwargs):
    return Binance(key='k', secret='s', opener=opener, clock=lambda: 1_770_004_800.0, authorize_writes=True, **kwargs)


class AdapterEdges(TestCase):
    def test_truncated_or_malformed_http_is_unknown_never_a_raw_exception(self):
        for error in (IncompleteRead(b'x'), __import__('http.client').client.BadStatusLine('x')):
            opener = Mock()
            opener.open.side_effect = error
            with self.assertRaises(Unknown):
                adapter(opener).get('/fapi/v1/time')
            with self.assertRaises(Unknown):
                adapter(opener).send('POST', '/fapi/v1/order', ORDER)
            reader = adapter(opener)
            with self.assertRaises(Unknown):
                reader.align_clock()

    def test_order_cancel_and_reduction_shapes_are_restricted_to_owned_market_reductions(self):
        opener = Mock()
        reader = adapter(opener)
        for bad in ({'symbol': 'BTCUSDT', 'orderId': 1}, {'symbol': 'BTCUSDT', 'origClientOrderId': 'x-1'},
                    {'symbol': 'BTCUSDT', 'origClientOrderId': 'cq-1', 'orderId': 1}):
            with self.assertRaises(Blocked):
                reader.send('DELETE', '/fapi/v1/order', bad)
        resting = {**ORDER, 'reduceOnly': 'true', 'side': 'SELL', 'timeInForce': 'GTC'}
        with self.assertRaises(Blocked):
            reader.send('POST', '/fapi/v1/order', resting)
        opener.open.assert_not_called()


    def test_a_write_without_time_to_read_the_answer_is_never_sent(self):
        opener = Mock()
        reader = adapter(opener)
        reader.set_deadline(1.0)
        with self.assertRaises(ObservationDeadline):
            reader.send('POST', '/fapi/v1/order', ORDER)
        opener.open.assert_not_called()

    def test_slow_time_sample_does_not_set_the_offset_and_rate_limit_cools_down(self):
        ticks = iter([0.0, 0.0, 0.0, MAX_CLOCK_ROUND_TRIP + 1, MAX_CLOCK_ROUND_TRIP + 1])
        opener = Mock()
        opener.open.return_value = io.BytesIO(b'{"serverTime":1770004800000}')
        reader = adapter(opener, monotonic=lambda: next(ticks, 100.0))
        reader.time_offset_ms = 123
        with self.assertRaises(Unknown):
            reader.align_clock()
        self.assertEqual(reader.time_offset_ms, 123)

        now = [0.0]
        limited = Mock()
        limited.open.side_effect = lambda *a, **k: (_ for _ in ()).throw(
            HTTPError('u', 429, 'x', {'Retry-After': '90'}, io.BytesIO(b'{}')))
        reader = adapter(limited, monotonic=lambda: now[0])
        with self.assertRaises(Unknown):
            reader.align_clock()
        with self.assertRaises(NotSent):
            reader.align_clock()
        self.assertEqual(limited.open.call_count, 1)


class AbsentOrderRetirement(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.risk = patch('coinquant.campaign.PRIMARY_RISK', '6')
        self.risk.start()
        self.venue = Venue()
        self.venue.seed(self.tmp.name)
        run(Config('123', self.tmp.name, 3, 1), self.venue, execute=True,
            monotonic=self.venue.monotonic, wait=self.venue.wait)
        self.assertGreater(self.venue.q, 0)
        self.state = State(self.tmp.name, SCOPE).__enter__()
        self.now = int(self.venue.clock() * 1000)

    def tearDown(self):
        self.state.__exit__(None, None, None)
        self.tmp.cleanup()
        self.risk.stop()

    def intent(self, identity, payload, **result):
        self.state.prepare(identity, 'binance_order', payload,
                           result={'prepared_at_ms': self.now - 400_000, **result})
        return {'id': identity, 'status': 'unknown'}

    def status(self, identity):
        return self.state.db.execute('SELECT status FROM intents WHERE id=?', (identity,)).fetchone()[0]

    def test_an_absent_reduction_is_retired_even_with_a_position_and_never_reduces_more(self):
        pending = self.intent('cq-r', dict(symbol='BTCUSDT', side='SELL', positionSide='BOTH', type='MARKET',
                                           quantity='0.001', reduceOnly='true'))
        self.assertTrue(self.venue.absent_within_retention(self.state, pending))
        self.assertEqual(self.status('cq-r'), 'rejected')

    def test_an_absent_add_is_retired_only_while_the_position_is_unchanged(self):
        payload = dict(symbol='BTCUSDT', side='BUY', positionSide='BOTH', type='LIMIT', quantity='0.001')
        before = str(self.venue.snapshot('123')['quantity_btc'])
        unchanged = self.intent('cq-a', payload, position_before_btc=before)
        self.assertTrue(self.venue.absent_within_retention(self.state, unchanged))
        self.venue.q += 1
        moved = self.intent('cq-b', {**payload, 'quantity': '0.002'}, position_before_btc=before)
        self.assertFalse(self.venue.absent_within_retention(self.state, moved))
        self.assertEqual(self.status('cq-b'), 'unknown')

    def test_an_absent_entry_needs_a_flat_account(self):
        payload = dict(symbol='BTCUSDT', side='BUY', positionSide='BOTH', type='LIMIT', quantity='0.001')
        entry = self.intent('cq-e', payload)
        self.assertFalse(self.venue.absent_within_retention(self.state, entry))
        self.assertEqual(self.status('cq-e'), 'unknown')


class CleanupBudgets(TestCase):
    def setUp(self):
        self.risk = patch('coinquant.campaign.PRIMARY_RISK', '6')
        self.risk.start()
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = self.tmp.name
        self.venue = Venue()
        self.venue.seed(self.directory)

    def tearDown(self):
        self.tmp.cleanup()
        self.risk.stop()

    def session(self, seconds=3):
        return run(Config('123', self.directory, seconds, 1), self.venue, execute=True,
                   monotonic=self.venue.monotonic, wait=self.venue.wait)

    def test_failed_clock_sample_at_cleanup_does_not_skip_verification(self):
        original = self.venue.begin_cycle

        def begin(seconds=120):
            original(seconds)
            if seconds == FINISH_SECONDS:
                raise Unknown('fixture clock sample failed')

        self.venue.begin_cycle = begin
        report = self.session()
        self.assertEqual(report['cleanup'], 'verified')
        self.assertTrue(any(e['phase'] == 'cleanup_clock' for e in report['errors']))

    def test_signal_landing_inside_the_final_cleanup_is_retried_once(self):
        real = Lifecycle.finish
        calls = []

        def finish(engine):
            calls.append(1)
            if len(calls) == 1:
                raise KeyboardInterrupt
            return real(engine)

        with patch.object(Lifecycle, 'finish', finish):
            report = self.session()
        self.assertEqual(len(calls), 2)
        self.assertEqual(report['cleanup'], 'verified')

    def test_recovery_fallback_reductions_reserve_their_own_observation_budget(self):
        self.session()
        with State(self.directory, SCOPE) as state:
            engine = Lifecycle(self.venue, state, '123', authorized=True)
            order = []
            snapshot = engine.snapshot()
            self.assertTrue(snapshot['quantity_btc'] != 0)
            with patch.object(Lifecycle, 'planned_protection', return_value=False), \
                    patch.object(safety, 'protect_existing', side_effect=Unknown('fixture')), \
                    patch.object(Lifecycle, 'reserve', lambda self, seconds: order.append(('reserve', seconds))), \
                    patch.object(Lifecycle, 'close', lambda self, snap, *a, **k: order.append(('close',))), \
                    patch.object(Lifecycle, 'entry_fill_proven', return_value=False):
                state.set('entry_plan', None)
                state.set('session_replacement', None)
                with self.assertRaises(Unknown):
                    engine.recover_exposure(snapshot)
            self.assertEqual(order, [('reserve', REDUCE_SECONDS), ('close',)])


class ConfigPath(TestCase):
    def test_relative_state_directory_is_refused(self):
        with self.assertRaises(Blocked):
            Config('123', 'state')
        Config('123', '~/.coinquant/x')
        Config('123', str(Path('/tmp/x')))
