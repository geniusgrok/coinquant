"""Money/causality boundaries for the new offline consumer, without replay."""
from decimal import Decimal as D
import importlib
from pathlib import Path
from types import SimpleNamespace

import tempfile
import unittest

from research.lifecycle import DAY, DebtMemory, configured, giveback_proposal, update_debt

PACKAGE = Path(__file__).resolve().parents[1].name
session = importlib.import_module(PACKAGE+'.session')
State = importlib.import_module(PACKAGE+'.state').State
Blocked = importlib.import_module(PACKAGE+'.types').Blocked
guard = '_guard_strategy' if PACKAGE == 'coinquant' else '_guard_state'


class LifecycleBoundaries(unittest.TestCase):
    def test_canonical_and_other_lifecycle_consumer_reject_foreign_state_before_recovery(self):
        with tempfile.TemporaryDirectory() as temporary:
            self._foreign(Path(temporary))

    def _foreign(self, tmp_path):
        with State(str(tmp_path/'account'), 'lifecycle-test') as state:
            foreign = dict(policy='different', spec_sha256='f'*64)
            state.set('lifecycle_identity', foreign)
            with self.assertRaisesRegex(Blocked, 'lifecycle'):
                getattr(session, guard)(state)
            with configured('debt-half', bars=[], binding=dict(packet='a'*64)):
                with self.assertRaisesRegex(Blocked, 'identity mismatch before recovery'):
                    getattr(session, guard)(state)
            self.assertEqual(state.get('lifecycle_identity'), foreign)
        self.assertIsNone(session._LIFECYCLE_IDENTITY)


    def test_configured_refuses_adapter_before_clock_or_recovery(self):
        def no_clock():
            self.fail('adapter clock must not be read')
        venue = SimpleNamespace(offline=False, clock=no_clock)
        with configured('debt-half', bars=[], binding=dict(packet='a'*64)) as selected:
            with self.assertRaisesRegex(ValueError, 'before recovery'):
                selected.run(None, venue, execute=True)


    def test_delayed_confirmed_loss_respects_completed_recovery_after_original_exit(self):
        memory = DebtMemory()
        memory.close(2*DAY+60000, D(90))
        loss = dict(id='actual-1', fully_closed=True, gain=D(-20),
                    end_ms=DAY+20000, owned_close_peak=D(100))
        rows = [(DAY+60000,D(95)), (2*DAY+60000,D(110))]
        recovered = update_debt(memory.checkpoint(), [loss], rows, 3*DAY)
        self.assertEqual(recovered.factor('debt-half'), 1)
        self.assertEqual(recovered.settled, {'actual-1'})
        with self.assertRaisesRegex(ValueError, 'fully settled'):
            recovered.settle(dict(loss, id='residual', fully_closed=False), 3*DAY)


    def test_earned_r_requires_actual_installed_receipt_and_completed_owned_days(self):
        values = dict(offline=True, now_ms=4*DAY, fill_ms=DAY//2, entry='100',
                      initial_stop=None, stop_received_ms=None,
                      completed_closes=[(2*DAY,'120'),(3*DAY,'105')], owned_btc='1')
        self.assertEqual(giveback_proposal('giveback-half', **values)['status'], 'BLOCKED_INPUT')
        values.update(initial_stop='90', stop_received_ms=DAY//2+1000)
        result = giveback_proposal('giveback-half', **values)
        self.assertEqual(result['reduce_btc'], '0.5')
        self.assertEqual(result['orders'], 0)
        values['completed_closes'].append((5*DAY,'125'))
        with self.assertRaisesRegex(ValueError, 'causal owned completed closes'):
            giveback_proposal('giveback-half', **values)
