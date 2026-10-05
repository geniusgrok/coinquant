"""Necessary sizing, causal clock and recovery boundaries; no account replay."""
from decimal import Decimal as D
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from coinquant import session
from coinquant.campaign import Campaign, DAY, ORIGIN
from coinquant.lifecycle import Lifecycle
from coinquant.linear_sizing import target_fraction as symmetric_fraction
from coinquant.opportunities import Opportunity
from coinquant.state import State
from coinquant.types import Blocked
from research.downside_budget import NORMAL_ES20, POLICIES, configured, estimate, measure, target_fraction


class DownsideBudgetBoundaries(unittest.TestCase):
    def test_balanced_semivariance_preserves_original_budget_and_units(self):
        returns = [D('.01'), D('-.01')]*10
        self.assertEqual(estimate(returns, POLICIES[0])['sigma'], D('.01'))
        for risk in (D('7.5'), D('3.6')):
            self.assertEqual(target_fraction(returns, '.0011', POLICIES[0], risk=risk),
                             risk*symmetric_fraction(returns, D('.0011')))

    def test_fixed_shrinkage_bounds_positive_only_history_and_detects_downside(self):
        positive = estimate([D('.04')]*20, POLICIES[0])
        negative = estimate([D('-.04')]*20, POLICIES[0])
        self.assertLess(abs(positive['sigma']**2-D('.0008')), D('1e-25'))
        self.assertLess(abs(negative['sigma']**2-D('.0024')), D('1e-25'))
        for policy in POLICIES:
            row = measure([D('.04')]*20, policy=policy, risk='7.5')
            self.assertLessEqual(row['multiplier'], D(2).sqrt())
            self.assertGreater(row['candidate_fraction'], 0)

    def test_tail_is_worst_four_nonnegative_losses_on_same_daily_scale(self):
        returns = [D('-.08'), D('-.04'), D('-.02'), D('-.01')]+[D('.01')]*16
        stats = estimate(returns, POLICIES[1])
        loss = D('.15')/4
        self.assertLess(abs(stats['raw_downside_sigma']-loss/NORMAL_ES20), D('1e-25'))
        rms2 = sum((r*r for r in returns), D(0))/20
        # Squaring the rounded Decimal square root can differ in its last digit.
        self.assertLess(abs(stats['sigma']**2-(rms2+(loss/NORMAL_ES20)**2)/2), D('1e-25'))

    def test_short_history_not_zero_padded_and_reserves_bound_zero_volatility(self):
        for policy in POLICIES:
            self.assertEqual(target_fraction([D('.02')]*19, '.0011', policy, risk='7.5'), 0)
            value = target_fraction([D(0)]*20, '.0011', policy, risk='7.5')
            self.assertTrue(value.is_finite())
            self.assertEqual(value, D('1.5')/(D('.10')+D('.01')+2*(D('.00075')+D('.0011'))))

    def test_future_history_invalid_return_and_invalid_budget_are_refused(self):
        with self.assertRaisesRegex(Blocked, 'causally completed'):
            measure([D('.01')]*20, policy=POLICIES[0], risk='7.5',
                    completed_through_ms=2000, decision_ms=1999)
        for returns in ([D('NaN')]*20, [D(-1)]*20):
            with self.assertRaises(ValueError):
                estimate(returns, POLICIES[0])
        for values in (dict(risk='Infinity'), dict(friction='-.01'), dict(absence_days=5)):
            parameters = dict(risk='7.5', friction='.0011', absence_days=7)
            parameters.update(values)
            with self.assertRaises(ValueError):
                target_fraction([D('.01')]*20, policy=POLICIES[0], **parameters)

    def test_adapter_refused_before_clock_or_recovery(self):
        def forbidden():
            self.fail('private adapter clock must not be read')
        with configured(POLICIES[0], binding={'input_sha256': 'a'*64}) as selected:
            with self.assertRaisesRegex(ValueError, 'before clock or recovery'):
                selected.run(None, SimpleNamespace(offline=False, clock=forbidden), execute=True)

    def test_default_and_different_expression_reject_saved_research_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            with State(Path(directory)/'wallet', 'downside-boundary-test') as state:
                with configured(POLICIES[0], binding={'input_sha256': 'a'*64}) as selected:
                    session._guard_strategy(state)
                    saved = state.get('lifecycle_identity')
                    self.assertEqual(saved, selected.identity)
                with self.assertRaisesRegex(Blocked, 'matching offline consumer'):
                    session._guard_strategy(state)
                with configured(POLICIES[1], binding={'input_sha256': 'a'*64}):
                    with self.assertRaisesRegex(Blocked, 'identity mismatch before recovery'):
                        session._guard_strategy(state)
                self.assertEqual(state.get('lifecycle_identity'), saved)
        self.assertIsNone(session._LIFECYCLE_IDENTITY)

    def test_real_initial_entry_seam_bypasses_subclass_fraction_and_restores_topup(self):
        class HistoricalVariant(Campaign):
            @property
            def active(self):
                return Opportunity(ORIGIN+DAY, 1, D(90), D(200), None)
            def fraction(self, risk, friction):
                raise AssertionError('historical subclass symmetric override was used')
        model = HistoricalVariant()
        model.returns.extend([D('-.01')]*20)
        model.last = ORIGIN+DAY
        observed = []
        topup = Lifecycle.top_up
        def actual_enter(engine, selected_model, snapshot):
            observed.append(selected_model.entry_fraction('.0011'))
            # The real lifecycle persists this quantity before submit. This seam
            # checks the candidate reaches it rather than a symmetric override.
            return snapshot
        journal = []
        fixed_clock = (model.last+1000)/1000
        reader = SimpleNamespace(offline=True, clock=lambda: fixed_clock)
        with patch.object(Lifecycle, 'enter', actual_enter):
            with configured(POLICIES[0], binding={'input_sha256': 'a'*64}, journal=journal):
                Lifecycle.enter(SimpleNamespace(reader=reader), model, {'quantity_btc': '0'})
                self.assertIs(Lifecycle.top_up, topup)
                model.last += DAY
                with self.assertRaisesRegex(Blocked, 'causally completed'):
                    Lifecycle.enter(SimpleNamespace(reader=reader), model, {'quantity_btc': '0'})
        self.assertEqual(observed, [target_fraction([D('-.01')]*20, '.0011', POLICIES[0], risk='7.5')])
        self.assertEqual(journal[0]['campaign'], ORIGIN+DAY)
        self.assertNotIn('entry_fraction', vars(HistoricalVariant))
