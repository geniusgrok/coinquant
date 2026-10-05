"""Necessary funded target, ownership, causality and durable-source boundaries."""
from datetime import datetime, timezone
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import tempfile
from time import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from coinquant import session
from coinquant.campaign import Campaign, DAY, ORIGIN
from coinquant.lifecycle import Lifecycle
from coinquant.opportunities import Opportunity
from coinquant.state import State
from coinquant.types import Blocked, Unknown
from research.information_runtime import admitted, configured, primary_class, reconcile_information
import test_incremental_information as information_fixtures


def admission(book, kind):
    folder = Path(__file__).parents[1]/'research'
    result = dict(input_sha256=book.input_sha256, spec_sha256='b'*64,
        assessments={kind:dict(status='ELIGIBLE_FINITE_ACCOUNT_PROPOSAL', account_entrant=True, gates={'fixture':True})},
        source_sha256={str(folder/name):hashlib.sha256((folder/name).read_bytes()).hexdigest()
            for name in ('incremental_information.py', 'edge_features.py', 'continuous_routes.py', 'tradeoff_routes.py', 'replacement_routes.py')})
    binding = dict(information_result_sha256=hashlib.sha256((json.dumps(result, indent=2)+'\n').encode()).hexdigest(),
                   information_spec_sha256=result['spec_sha256'])
    return result, binding


class InformationRuntimeTests(unittest.TestCase):
    def test_other_input_or_unbound_admission_cannot_enable_account(self):
        book = information_fixtures.IncrementalInformationTests().book()
        result, binding = admission(book, 'coin')
        admitted(book, binding, result, 'coin')
        with self.assertRaises(ValueError):
            admitted(book, dict(binding, information_result_sha256='0'*64), result, 'coin')
        result['input_sha256'] = '0'*64
        with self.assertRaises(ValueError):
            admitted(book, binding, result, 'coin')

    def test_fresh_fraction_once_preserves_committed_topup_and_restores_hook(self):
        book = information_fixtures.IncrementalInformationTests().book()
        book.at = lambda now:dict(status='FEATURE_READY', release=False, day_ms=now//DAY*DAY-DAY,
                                 latest_input_available_ms=now)
        result, binding = admission(book, 'coin')
        class Candidate(Campaign):
            @property
            def active(self):
                return Opportunity(ORIGIN+DAY, 1, D(90), D(200), None)
            def entry_fraction(self, friction):
                return D(4)
        model = Candidate()
        clock = model.last+1000
        venue = SimpleNamespace(offline=True, clock=lambda:clock/1000)
        observed, journal = [], []
        def enter(engine, selected, snapshot):
            observed.append(selected.entry_fraction('.0011'))
            return snapshot
        topup = Lifecycle.top_up
        with patch.object(Lifecycle, 'enter', enter):
            with configured('release-full-otherwise-half', book=book, binding=binding,
                            venue=venue, admission=result, journal=journal):
                Lifecycle.enter(SimpleNamespace(reader=venue), model, {'quantity_btc':'0'})
                self.assertIs(Lifecycle.top_up, topup)
                model.position_campaign = model.active.identity
                with self.assertRaises(Blocked):
                    Lifecycle.enter(SimpleNamespace(reader=venue), model, {'quantity_btc':'1'})
        self.assertEqual(observed, [D(2)])
        self.assertEqual(model.entry_fraction('.0011'), D(4))
        self.assertEqual(journal[0]['factor'], '.5')

    def test_foreign_identity_and_adapter_reject_before_recovery_or_clock(self):
        book = information_fixtures.IncrementalInformationTests().book()
        result, binding = admission(book, 'coin')
        with self.assertRaises(ValueError):
            with configured('release-full-otherwise-half', book=book, binding=binding,
                    venue=SimpleNamespace(offline=False, clock=lambda:self.fail('private clock')),
                    admission=result):
                self.fail('private adapter opened')
        with tempfile.TemporaryDirectory() as directory, State(directory, 'info-test') as state:
            state.set('lifecycle_identity', {'foreign':True})
            with configured('release-full-otherwise-half', book=book, binding=binding,
                    venue=SimpleNamespace(offline=True), admission=result):
                with self.assertRaises(Blocked):
                    session._guard_strategy(state)
            self.assertEqual(state.get('lifecycle_identity'), {'foreign':True})

    def model(self):
        book = SimpleNamespace(input_sha256='a'*64, at=lambda now:dict(
            status='FEATURE_READY', release=True, day_ms=now//DAY*DAY-DAY))
        cls = primary_class(book)
        model = cls()
        for i in range(1, 91):
            model.update(ORIGIN+i*14400000, D(100), D(100), D(100))
        call = model.last+1000
        row = dict(missing_reason=None, latest_observation_date=datetime.fromtimestamp(call/1000, timezone.utc).date().isoformat(),
                   latest_value_available_ms=call-1, prior20_value_available_ms=call-1,
                   latest_value='2', prior20_value='2')
        return cls, model, call, row

    def test_primary_keeps_dfii_unknown_and_original_entry_priority(self):
        _, model, call, row = self.model()
        with self.assertRaises(Unknown):
            model.select_macro(None, D(100), call)
        model.select_macro(dict(row, missing_reason='fixture_no_causal_value'), D(100), call)
        self.assertIsNone(model.information_active)
        original = Opportunity(model.last, 1, D(90), D(200), None)
        model.model.active = original
        model.select_macro(None, D(100), call)
        self.assertIs(model.active, original)
        self.assertIsNone(model.information_active)

    def test_real_native_reconcile_consumes_once_preserves_primary_and_restores(self):
        from coinquant.ownership import reconcile
        book = SimpleNamespace(input_sha256='a'*64, at=lambda now:dict(
            status='FEATURE_READY', release=True, day_ms=now//DAY*DAY-DAY))
        cls = primary_class(book)
        with tempfile.TemporaryDirectory() as directory, State(directory, 'binance:BTCUSDT:live:123') as state:
            epoch = int(time()*1000)//14400000*14400000
            model = cls(); model.last = epoch; model.model.last = epoch
            model.primary_consumed = epoch-14400000
            prior_primary = model.primary_consumed
            now = int(time()*1000)
            row = dict(missing_reason=None, latest_observation_date=datetime.fromtimestamp(now/1000, timezone.utc).date().isoformat(),
                       latest_value_available_ms=now-1, prior20_value_available_ms=now-1,
                       latest_value='2', prior20_value='2')
            model.select_macro(row, D(100), now)
            selected = model.active.identity
            self.assertEqual(selected, epoch-1)
            self.assertEqual(model.entry_fraction('.0011'), D(1))
            flat = dict(account_uid='123', quantity_btc='0', possible_entry_remainders=0)
            entry_payload = dict(symbol='BTCUSDT', side='BUY', positionSide='BOTH', type='LIMIT', quantity='.01')
            state.prepare('cq-info', 'binance_order', entry_payload, campaign=selected, flat_snapshot=flat)
            start = state.get('entry_campaigns')['cq-info']['prepared_at']
            now = start+1000
            entry = dict(entry_payload, orderId=1, origQty='.01', executedQty='.003', status='CANCELED')
            snapshot = dict(flat, quantity_btc='.003', entry='100', wallet_usdt='999', native_full_position_protected=False)
            trade = dict(symbol='BTCUSDT', positionSide='BOTH', side='BUY', orderId=1, id=11, time=start, qty='.003')
            reader = Mock(); reader.clock.return_value=now/1000
            reader.query_intent.return_value={'parent':entry,'child':None}
            reader.get.return_value=[trade]; reader.snapshot.return_value=snapshot
            result = reconcile_information(reconcile, state, reader, model, snapshot)
            self.assertEqual(result['status'], 'reconciled')
            self.assertTrue(model.information_owned())
            self.assertEqual(model.information_consumed, selected)
            self.assertEqual(model.primary_consumed, prior_primary)
            # The actual original reconcile write already contains the corrected
            # fields, not a later in-memory repair after durable persistence.
            restored = cls.restore(state.get('linear_campaign'))
            self.assertTrue(restored.information_owned())
            self.assertEqual(restored.primary_consumed, prior_primary)
            exit_payload = dict(symbol='BTCUSDT', side='SELL', positionSide='BOTH', type='MARKET', quantity='.003', reduceOnly='true')
            state.prepare('cq-exit', 'binance_order', exit_payload)
            closed = dict(exit_payload, orderId=2, origQty='.003', executedQty='.003', status='FILLED', reduceOnly=True)
            reader.query_intent.side_effect=lambda identity, **kw:dict(parent=entry if identity=='cq-info' else closed, child=None)
            reader.get.return_value=[trade, dict(trade, id=12, orderId=2, side='SELL')]
            snapshot.update(quantity_btc='0', entry='0')
            reconcile_information(reconcile, state, reader, model, snapshot)
            self.assertIsNone(model.position_campaign)
            self.assertEqual(model.primary_consumed, prior_primary)
            model.select_macro(row, D(100), now)
            self.assertNotEqual(model.action(D(0)), 'enter')
            self.assertEqual(cls.restore(model.checkpoint()).checkpoint(), model.checkpoint())
            with self.assertRaises(Blocked):
                Campaign.restore(model.checkpoint())


if __name__ == '__main__':
    unittest.main()
