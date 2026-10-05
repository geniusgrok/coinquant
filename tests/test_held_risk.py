"""Necessary causal, durable reduce-only and no-rebuy boundaries; no replay."""
from contextlib import ExitStack
from decimal import Decimal as D
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from coinquant import session
from coinquant.config import scope
from coinquant.lifecycle import Lifecycle
from coinquant.state import State
from coinquant.types import Blocked, Unknown
from research.held_risk import DAY, POLICIES, STATE_KEY, configured, measure


RULES = dict(symbol='BTCUSDT', filters=[
    dict(filterType='LOT_SIZE', minQty='.001', maxQty='100', stepSize='.001'),
    dict(filterType='MARKET_LOT_SIZE', minQty='.001', maxQty='100', stepSize='.001'),
    dict(filterType='MIN_NOTIONAL', notional='5')])


def memory_state():
    # Exercise the original durable SQL/intent methods without account locks,
    # native balances, network or a historical venue producer.
    state = State('', scope('live', '12345'))
    state.db = sqlite3.connect(':memory:')
    state.db.execute('CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
    state.db.execute('CREATE TABLE intents (id TEXT PRIMARY KEY, kind TEXT NOT NULL, '
                     'payload TEXT NOT NULL, status TEXT NOT NULL, result TEXT NOT NULL, updated REAL NOT NULL)')
    return state


class Reader:
    offline, environment = True, 'live'

    def __init__(self, state, *, uncertain=False):
        self.state, self.uncertain = state, uncertain
        self.q = D(1)
        self.orders, self.writes = {}, []

    def clock(self):
        return (30*DAY+1000)/1000

    def snapshot(self, uid):
        return dict(account_uid=str(uid), quantity_btc=str(self.q), mark_price='100',
                    possible_entry_remainders=0, native_full_position_protected=bool(self.q),
                    stop_before_liquidation=bool(self.q))

    def send(self, method, path, payload):
        self.writes.append((method, path, dict(payload)))
        if self.uncertain:
            raise OSError('lost response')
        qty = D(payload['quantity'])
        self.q -= qty
        self.orders[payload['newClientOrderId']] = dict(payload, reduceOnly=True,
            orderId=len(self.orders)+1, status='FILLED', origQty=str(qty), executedQty=str(qty))

    def recover_pending(self, state):
        for item in state.pending():
            if item['id'] in self.orders:
                state.finish(item['id'], 'confirmed', self.orders[item['id']])

    def query_intent(self, identity, *, conditional=False):
        return dict(parent=self.orders[identity], child=None)


class HeldDownsideBoundaries(unittest.TestCase):
    def test_overlap_bound_and_fixed_threshold_can_trigger(self):
        values = [D('.01')]*15 + [D('-.02')]*5
        result = measure(values, completed_through_ms=30*DAY, decision_ms=30*DAY+1000)
        self.assertEqual(result['ratio'], 2)
        self.assertTrue(result['triggered'])
        even = measure([D('-.02')]*20, completed_through_ms=30*DAY, decision_ms=30*DAY)
        self.assertEqual(even['ratio'], 1)
        self.assertFalse(even['triggered'])
        positive = measure([D('.02')]*20, completed_through_ms=30*DAY, decision_ms=30*DAY)
        self.assertIsNone(positive['ratio'])
        self.assertFalse(positive['triggered'])

    def test_short_invalid_or_future_history_is_not_imputed(self):
        self.assertFalse(measure([0]*19, completed_through_ms=30*DAY, decision_ms=30*DAY)['ready'])
        for values in ([D('NaN')]*20, [D(-1)]*20):
            with self.assertRaises(ValueError):
                measure(values, completed_through_ms=30*DAY, decision_ms=30*DAY)
        for completed, now in ((30*DAY, 30*DAY-1), (30*DAY+1, 31*DAY)):
            with self.assertRaisesRegex(Blocked, 'causally completed'):
                measure([0]*20, completed_through_ms=completed, decision_ms=now)

    def test_adapter_refused_before_clock_or_recovery(self):
        def forbidden():
            self.fail('adapter clock must not be accessed')
        with configured(POLICIES[0], binding={'input': 'a'*64}) as selected:
            with self.assertRaisesRegex(ValueError, 'before clock or recovery'):
                selected.run(None, SimpleNamespace(offline=False, clock=forbidden), execute=True)

    def test_research_identity_and_cap_guard_precede_recovery(self):
        state = memory_state()
        self.addCleanup(state.db.close)
        with configured(POLICIES[0], binding={'input': 'a'*64}) as selected:
            session._guard_strategy(state)
            self.assertEqual(state.get('lifecycle_identity'), selected.identity)
        with self.assertRaisesRegex(Blocked, 'matching offline consumer'):
            session._guard_strategy(state)
        with configured(POLICIES[1], binding={'input': 'a'*64}):
            with self.assertRaisesRegex(Blocked, 'identity mismatch before recovery'):
                session._guard_strategy(state)
        with configured(POLICIES[0], binding={'input': 'a'*64}):
            state.set(STATE_KEY, {'7': {'cap_btc': 'NaN'}})
            with self.assertRaisesRegex(Blocked, 'invalid held downside checkpoint'):
                session._guard_strategy(state)
        self.assertIsNone(session._LIFECYCLE_IDENTITY)

    def fixture(self, policy, *, uncertain=False):
        stack = ExitStack()
        self.addCleanup(stack.close)
        state = memory_state()
        self.addCleanup(state.db.close)
        model = SimpleNamespace(active=SimpleNamespace(identity=7), position_campaign=7,
            last=30*DAY, returns=[D('.01')]*15+[D('-.02')]*5, consumed=7,
            primary_consumed=7, macro_consumed=None)
        model.action = lambda q: 'hold' if q else 'consumed'
        state.set_many({'entry_fill': dict(campaign=7, requested='1', session=123),
                        'position_protection': dict(campaign=7, stop='90', take='200')})
        reader = Reader(state, uncertain=uncertain)
        engine = Lifecycle(reader, state, '12345', authorized=True, session=123)
        # Original ownership/protection is an explicitly mocked prerequisite;
        # the actual native reduce helper, SQL intents and send-once are used.
        stack.enter_context(patch.object(Lifecycle, 'recover_exposure', lambda _e, snap: snap))
        stack.enter_context(patch.object(Lifecycle, 'planned_protection', lambda _e, _s: True))
        stack.enter_context(patch.object(Lifecycle, 'instrument', lambda _e: RULES))
        stack.enter_context(patch.object(Lifecycle, 'top_up', side_effect=AssertionError('buyback')))
        stack.enter_context(patch.object(Lifecycle, 'rebalance', side_effect=AssertionError('rebalance buyback')))
        def ordinary_decide(e, m, snapshot):
            snapshot = e.rebalance(m, snapshot)
            return 'hold', e.top_up(m, snapshot)
        stack.enter_context(patch.object(Lifecycle, 'decide', ordinary_decide))
        journal = []
        stack.enter_context(configured(policy, binding={'input': 'a'*64}, journal=journal))
        return engine, model, reader, state, journal

    def test_actual_reduce_only_half_is_once_per_campaign_and_target_never_bought_back(self):
        engine, model, reader, state, journal = self.fixture(POLICIES[0])
        action, snapshot = engine.decide(model, reader.snapshot(engine.uid))
        self.assertEqual((action, reader.q), ('hold', D('.5')))
        self.assertEqual(state.get('entry_fill')['requested'], '0.5')
        request = reader.writes[0][2]
        self.assertEqual((request['type'], request['side'], request['reduceOnly']), ('MARKET', 'SELL', 'true'))
        self.assertEqual(request['quantity'], '0.500')
        engine.decide(model, snapshot)
        engine.recover_exposure(snapshot)
        self.assertEqual(len(reader.writes), 1)
        cap = state.get(STATE_KEY)['7']
        self.assertEqual((cap['phase'], cap['confirmed_orders'], cap['attempt']), ('CAP_SATISFIED', 1, None))
        self.assertEqual(model.consumed, 7)
        self.assertEqual(sum(e['event'] == 'held-downside-cap' for e in journal), 1)
        self.assertEqual(sum(e['event'] == 'held-downside-reduction-confirmed' for e in journal), 1)

    def test_lost_response_keeps_stable_attempt_and_is_never_counted_or_resent(self):
        engine, model, reader, state, journal = self.fixture(POLICIES[0], uncertain=True)
        with self.assertRaisesRegex(Unknown, 'unresolved'):
            engine.decide(model, reader.snapshot(engine.uid))
        attempt = state.get(STATE_KEY)['7']['attempt']
        self.assertIsNotNone(attempt)
        self.assertEqual(state.get(STATE_KEY)['7']['confirmed_orders'], 0)
        self.assertEqual(state.get('entry_fill')['requested'], '0.5')
        for _ in range(2):
            with self.assertRaisesRegex(Unknown, 'unresolved'):
                engine.recover_exposure(reader.snapshot(engine.uid))
        self.assertEqual(len(reader.writes), 1)
        self.assertEqual(state.get(STATE_KEY)['7']['attempt'], attempt)
        self.assertFalse(any(e['event'] == 'held-downside-reduction-confirmed' for e in journal))
        reader.q = D(0)
        state.set('position_protection', None)
        with self.assertRaisesRegex(Unknown, 'unresolved'):
            engine.recover_exposure(reader.snapshot(engine.uid))

    def test_exit_keeps_consumption_and_new_campaign_has_fresh_eligibility(self):
        engine, model, reader, state, journal = self.fixture(POLICIES[1])
        action, snapshot = engine.decide(model, reader.snapshot(engine.uid))
        self.assertEqual((action, reader.q), ('exit', D(0)))
        self.assertEqual(state.get(STATE_KEY)['7']['phase'], 'FLAT')
        self.assertEqual((model.consumed, model.primary_consumed, model.action(D(0))), (7, 7, 'consumed'))
        self.assertEqual(len(reader.writes), 1)
        self.assertEqual(state.get('entry_fill')['requested'], '0')
        # A genuinely different confirmed campaign is not inhibited by an old
        # cap; eligibility uses ownership identity, not a cleared consumed flag.
        model.active = SimpleNamespace(identity=8)
        model.position_campaign = 8
        model.returns = [D('-.01')]*20
        state.set('entry_fill', dict(campaign=8, requested='1'))
        state.set('position_protection', dict(campaign=8))
        with self.assertRaisesRegex(AssertionError, 'rebalance buyback'):
            engine.decide(model, dict(snapshot, quantity_btc='1'))
        self.assertNotIn('8', state.get(STATE_KEY))

    def test_pending_or_unprotected_campaign_cannot_become_a_trigger(self):
        engine, model, reader, state, journal = self.fixture(POLICIES[0])
        state.set('position_protection', None)
        with self.assertRaisesRegex(Unknown, 'confirmed owned protected'):
            engine.decide(model, reader.snapshot(engine.uid))
        self.assertIsNone(state.get(STATE_KEY))
        self.assertEqual(reader.writes, [])
