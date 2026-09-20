"""Native FOK contract fixtures are not receipts from a real exchange."""
from dataclasses import replace
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from pancakequant.bybit import Bybit
from pancakequant.config import Config
from pancakequant.execution import run_once, coverage
from pancakequant.model import decide
from pancakequant.pending import record, valid
from pancakequant.state import State, client_id
from pancakequant.types import D, ModelConfig, Position, Target, Unknown
from test_execution import FakeVenue, protectors
from test_model import history, sample


def target(candle=None, quantity=D(100)):
    candle = history()[-1].time if candle is None else candle
    return Target(candle, quantity, D(31032), D(31600), D(30800),
                  abs(quantity) / D(31032) / 20, abs(quantity) / D(31032) / 20,
                  D('.0001'), 'synthetic conditional fixture', D(31000))


class ConditionalVenue(FakeVenue):
    def __init__(self):
        super().__init__()
        self.target = None
        self.amend_race = False

    def place(self, link, delta, t, *, reduce_only=False):
        if not t.trigger_price or reduce_only:
            return super().place(link, delta, t, reduce_only=reduce_only)
        self.writes.append(('place_entry', link))
        self.target = t
        if self.failure == 'missing':
            raise Unknown('send possibly reached exchange')
        row = record(link, t)
        self.records[link] = row
        self.s = replace(self.s, orders=(row,))
        if self.failure == 'ack':
            raise Unknown('ack lost after hosted parent creation')
        return {}

    def trigger(self, link, *, partial=False):
        t = self.target
        # Parent activation is an exchange event, not a call to decide().
        self.s = replace(self.s, mark=t.trigger_price, bid=t.entry - 1, ask=t.entry)
        qty = t.quantity / 2 if partial else t.quantity
        self._fill(qty, t, False)
        self.records[link] = dict(self.records[link], orderStatus='Cancelled' if partial else 'Filled',
                                  cumExecQty=str(abs(qty)))
        self.s = replace(self.s, orders=protectors(self.s.position))

    def amend(self, link, t):
        self.writes.append(('amend_entry', link))
        if self.amend_race:
            self.trigger(link, partial=self.failure == 'partial_fok')
            raise Unknown('old parent filled before amendment acknowledgment')
        self.target = t
        self.records[link] = record(link, t)
        self.s = replace(self.s, orders=(self.records[link],))
        if self.failure == 'ack':
            raise Unknown('amend acknowledgment lost')
        return {}


class PendingTests(unittest.TestCase):
    def config(self, path):
        return Config(account_uid='12345', max_position_usd=D(10000), state_dir=path)

    def invoke(self, venue, config, t):
        with patch('pancakequant.execution.decide', return_value=t):
            return run_once(venue, config, execute=True)

    def test_hosted_entry_survives_exit_and_same_candle_does_not_duplicate(self):
        v = ConditionalVenue()
        with TemporaryDirectory() as path:
            config = self.config(path)
            first = self.invoke(v, config, target())
            second = self.invoke(v, config, target())
        self.assertEqual(first['status'], 'executed')
        self.assertEqual(second['status'], 'no_action')
        self.assertEqual(len(v.writes), 1)
        self.assertTrue(first['hosted_entry_contract_verified_at_observation'])
        self.assertFalse(first['pending_intents'])
        self.assertEqual(v.s.position.quantity, 0)

    def test_lost_ack_is_readback_not_second_submission(self):
        v = ConditionalVenue(); v.failure = 'ack'
        with TemporaryDirectory() as path:
            result = self.invoke(v, self.config(path), target())
        self.assertEqual(result['status'], 'executed')
        self.assertEqual(v.writes, [('place_entry', next(iter(v.records)))])

    def test_amend_preserves_parent_id_and_lost_ack_recovers(self):
        v = ConditionalVenue()
        with TemporaryDirectory() as path:
            config = self.config(path)
            self.invoke(v, config, target())
            v.failure = 'ack'
            result = self.invoke(v, config, target(candle=target().candle + 14_400_000, quantity=D(80)))
        self.assertEqual(result['status'], 'executed')
        self.assertEqual(v.writes[0][1], v.writes[1][1])
        self.assertEqual(v.writes[1][0], 'amend_entry')
        self.assertEqual(v.records[v.writes[0][1]]['qty'], '80')
        self.assertFalse(result['pending_intents'])

    def test_fill_during_amend_does_not_submit_new_target(self):
        v = ConditionalVenue()
        with TemporaryDirectory() as path:
            config = self.config(path)
            self.invoke(v, config, target())
            v.amend_race = True
            result = self.invoke(v, config, target(candle=target().candle + 14_400_000, quantity=D(80)))
        self.assertEqual(result['status'], 'executed')
        self.assertEqual(v.s.position.quantity, 100)
        self.assertTrue(coverage(v.s))
        self.assertFalse(result['pending_intents'])
        self.assertEqual([w[0] for w in v.writes], ['place_entry', 'amend_entry'])

    def test_partial_fok_is_recorded_safety_fault_not_approved_contract(self):
        v = ConditionalVenue()
        with TemporaryDirectory() as path:
            config = self.config(path)
            self.invoke(v, config, target())
            v.amend_race, v.failure = True, 'partial_fok'
            result = self.invoke(v, config, target(candle=target().candle + 14_400_000, quantity=D(80)))
            with State(path, 'testnet:12345') as state:
                self.assertIsNotNone(state.get('native_fok_violation'))
        self.assertEqual(result['status'], 'unknown')
        self.assertFalse(result['offline_safe_at_observation'])
        self.assertTrue(coverage(v.s))

    def test_offline_fill_then_stop_cannot_leave_entry_remainder_or_reenter_same_candle(self):
        v = ConditionalVenue()
        with TemporaryDirectory() as first, TemporaryDirectory() as lost:
            self.invoke(v, self.config(first), target())
            v.trigger(next(iter(v.records)))
            self.assertTrue(coverage(v.s))
            # Hosted stop completes while no program is running.
            v.s = replace(v.s, position=Position(), orders=())
            v.s = replace(v.s, mark=D(30745))
            result = self.invoke(v, self.config(lost), target())
        self.assertEqual(v.s.position.quantity, 0)
        self.assertEqual(v.s.orders, ())
        self.assertEqual(len(v.writes), 1)
        self.assertEqual(result['status'], 'no_action')

    def test_unknown_creation_is_not_resent(self):
        v = ConditionalVenue(); v.failure = 'missing'
        with TemporaryDirectory() as path:
            config = self.config(path)
            first = self.invoke(v, config, target())
            second = self.invoke(v, config, target())
        self.assertEqual(first['status'], 'unknown')
        self.assertEqual(second['status'], 'unknown')
        self.assertEqual(len(v.writes), 1)
        self.assertTrue(second['pending_intents'])

    def test_unsafe_gtc_and_existing_position_never_qualify_as_hosted_entry(self):
        t, s = target(), sample()
        row = record('pq-fixture', t)
        self.assertTrue(valid(row, s, D(1000)))
        self.assertFalse(valid(dict(row, timeInForce='GTC'), s, D(1000)))
        self.assertFalse(valid(dict(row, stopLoss='1'), s, D(1000)))
        self.assertFalse(valid(row, replace(s, position=Position(D(1), D(30000))), D(1000)))

    def test_model_generates_pending_from_complete_past_channel_only(self):
        bars = history()
        bars[-10] = replace(bars[-10], high=D(31000))
        t = decide(bars, sample(), ModelConfig(), notional_limit=D(100))
        self.assertGreater(t.trigger_price, sample().mark)
        self.assertLessEqual(t.quantity, 100)
        self.assertTrue(valid(record('pq-model', t), sample(), D(100)))

    def test_adapter_serializes_fok_trigger_and_native_full_protectors(self):
        venue = Bybit(Config(max_position_usd=D(1000)))
        requests = []
        venue.write = lambda path, data: requests.append((path, data))
        venue.place('pq-test', D(100), target())
        payload = requests[-1][1]
        self.assertEqual(payload['timeInForce'], 'FOK')
        self.assertEqual(payload['triggerPrice'], '31000')
        self.assertEqual(payload['tpslMode'], 'Full')
        self.assertEqual(payload['slOrderType'], 'Market')
        venue.lookup = lambda link: record(link, target())
        venue.amend('pq-test', target(quantity=D(80)))
        self.assertEqual(requests[-1][0], '/v5/order/amend')
        self.assertEqual(requests[-1][1]['qty'], '80')
