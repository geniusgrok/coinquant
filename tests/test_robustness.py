"""Research knobs and blocks for the overfitting audit; defaults must not change."""
import math
import tempfile
from decimal import Decimal as D
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from coinquant import dfii10, opportunities
from coinquant.opportunities import FOUR_HOURS, Opportunities
from research import rebuild, risk_select, robustness
from research.session_exchange import SessionExchange

FLAT = [(101, 99, 100)] * 20


def feed(rows, model=None):
    model = model or Opportunities()
    return [model.update((i + 1) * FOUR_HOURS, *map(D, row)) for i, row in enumerate(rows)]


class KnobTests(TestCase):
    def test_defaults_are_the_frozen_model(self):
        self.assertEqual((opportunities.IMPULSE_ATR, opportunities.ATR_BARS, opportunities.TAKE_POWER,
                          opportunities.LIFE_BARS, opportunities.RETRACE, dfii10.DROP),
                         (3, 14, 20, 42, D('0.5'), D('.25')))

    def test_retrace_moves_the_stop(self):
        with patch.object(opportunities, 'RETRACE', D('0.4')):
            a = feed(FLAT + [(120, 99, 115)])[-1]
        self.assertEqual(a.stop, D(115) - D('0.4') * 15)

    def test_atr_window_and_impulse_threshold(self):
        with patch.object(opportunities, 'ATR_BARS', 10):
            self.assertIsNotNone(feed([(101, 99, 100)] * 10 + [(120, 99, 115)])[-1])
        self.assertIsNone(feed([(101, 99, 100)] * 10 + [(120, 99, 115)])[-1])
        with patch.object(opportunities, 'IMPULSE_ATR', D('9')):
            self.assertIsNone(feed(FLAT + [(120, 99, 115)])[-1])

    def test_life_bars(self):
        with patch.object(opportunities, 'LIFE_BARS', 28):
            a = feed(FLAT + [(120, 99, 115)])[-1]
        self.assertEqual(a.expires - a.identity, 28 * FOUR_HOURS)


class BlockTests(TestCase):
    def _run(self, **kwargs):
        base = SimpleNamespace(identity={'market': 'fake'}, loaded={})
        exchange = SimpleNamespace(prints=SimpleNamespace(loaded={}))
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(rebuild, 'OUT', Path(tmp) / 'official'), \
                patch.object(rebuild, 'PARTIAL', Path(tmp) / 'partial'), \
                patch.object(rebuild, 'load_base', return_value=base), \
                patch.object(rebuild, 'run_account', return_value=({}, exchange)) as account:
            result = rebuild.trial('T', state=Path(tmp) / 'state', **kwargs)
            written = sorted(str(path.relative_to(tmp)) for path in Path(tmp).rglob('T.json'))
            return result, written, account

    def test_a_block_uses_only_its_frozen_sessions_and_never_the_official_name(self):
        result, written, account = self._run(window_start='2023-01-01T00:00:00Z', window_end='2024-01-01T00:00:00Z')
        starts = account.call_args.args[1]
        self.assertTrue(starts and all(rebuild.timestamp('2023-01-01T00:00:00Z') <= s < rebuild.timestamp('2024-01-01T00:00:00Z')
                                       for s in starts))
        self.assertEqual(written, ['partial/T.json'])
        self.assertTrue(result['complete'])
        self.assertEqual(account.call_args.args[5:], ('2023-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 1))

    def test_a_window_outside_the_frozen_range_is_refused(self):
        with self.assertRaises(ValueError):
            self._run(window_start='2019-06-01T00:00:00Z', window_end='2020-06-01T00:00:00Z')

    def test_knobs_apply_and_are_restored(self):
        before = opportunities.LIFE_BARS, dfii10.DROP
        result, _written, _account = self._run(limit=1, knobs={'life_bars': '28', 'dfii_drop': '0.35'})
        self.assertEqual((result['life_bars'], result['dfii_drop']), ('28', '0.35'))
        self.assertEqual((opportunities.LIFE_BARS, dfii10.DROP), before)
        with self.assertRaises(ValueError):
            self._run(knobs={'nonsense': '1'})


class AnalysisTests(TestCase):
    def test_growth_is_the_geometric_mean_of_block_growth(self):
        row = {'a': {'final_cny': 20000.0}, 'b': {'final_cny': 5000.0}}
        self.assertAlmostEqual(robustness.growth(row, ('a', 'b')), 1.0)

    def test_deflated_sharpe_falls_with_more_trials(self):
        weekly = [0.02, -0.01, 0.03, 0.0, 0.015, -0.005] * 60
        few = robustness.deflated_sharpe(weekly, [0.1, 0.2, 0.3], 3)['probability']
        many = robustness.deflated_sharpe(weekly, [0.1, 0.2, 0.3], 300)['probability']
        self.assertGreater(few, many)
        self.assertTrue(0 <= many <= 1 and not math.isnan(few))

    def test_adoption_needs_both_splits_and_a_real_margin(self):
        blocks = list(robustness.BLOCKS)

        def row(final, mdd=0.3):
            return {b: {'final_cny': final, 'mdd_envelope': mdd} for b in blocks}
        table = {name: row(15000.0) for name in robustness.CANDIDATES}
        table['base'] = row(15000.0)
        table['life28'] = row(15000.0 * 1.2)
        table['life56'] = row(15000.0 * 1.05)
        verdict = robustness.analyse(table)
        self.assertEqual([item[1] for item in verdict['adopted_changes']], ['life28'])


class FinalMarkTests(TestCase):
    def test_missing_prints_fall_back_to_the_official_mark_minute(self):
        from coinquant.types import Unknown

        class Exchange:
            market = SimpleNamespace(minute=lambda kind, open_ms: (0, 0, 0, D('123.5'), 0))

            def _mark_state(self):
                raise Unknown('no trade print at or before the request')

            def _completed_minute(self):
                return 60_000, 120_000
        self.assertEqual(rebuild._final_mark(Exchange()), D('123.5'))

        class Printed(Exchange):
            def _mark_state(self):
                return 1, D('99')
        self.assertEqual(rebuild._final_mark(Printed()), D('99'))


class RiskSelectionTests(TestCase):
    @staticmethod
    def table(spec):
        def row(growth, mdd, full_mdd):
            blocks = {b: {'final_cny': 10000 * growth, 'mdd_envelope': mdd} for b in robustness.BLOCKS}
            blocks['full'] = {'final_cny': 1e6, 'cagr': 1.0, 'mdd_envelope': full_mdd}
            return blocks
        return {risk_select.name_of(risk): row(*values) for risk, values in spec.items()}

    def test_plateau_and_buffer_decide(self):
        table = self.table({'6': (1.5, 0.30, 0.40), '6.5': (1.6, 0.40, 0.45),
                            '7': (1.9, 0.44, 0.49), '7.5': (2.5, 0.46, 0.51)})
        result = risk_select.select(table)
        self.assertEqual(result['ranked'], ['6.5', '6'])
        self.assertEqual(result['chosen'], '6.5')

    def test_a_failing_stress_vetoes_the_chosen_value_but_missing_stress_does_not(self):
        table = self.table({'6': (1.5, 0.30, 0.40), '6.5': (1.6, 0.40, 0.45),
                            '7': (1.9, 0.44, 0.49), '7.5': (2.5, 0.46, 0.51)})
        self.assertEqual(risk_select.select(table, stress_ok=lambda risk: None)['chosen'], '6.5')
        self.assertEqual(risk_select.select(table, stress_ok=lambda risk: risk != '6.5')['chosen'], '6')
        self.assertEqual(risk_select.select(table, stress_ok=lambda risk: False)['chosen'], '6')
        self.assertEqual(risk_select.select(table, stress_ok=lambda risk: False)['ranked'], [])

    def test_isolated_point_is_a_spike_and_nothing_qualifying_keeps_six(self):
        table = self.table({'6': (1.5, 0.50, 0.40), '6.5': (1.6, 0.30, 0.40),
                            '7': (1.9, 0.50, 0.40), '7.5': (2.5, 0.30, 0.40)})
        self.assertEqual(risk_select.select(table)['ranked'], [])
        self.assertEqual(risk_select.select(table)['chosen'], '6')


class UpdateTimeTests(TestCase):
    def test_update_time_moves_only_when_the_account_changes(self):
        account = SimpleNamespace(now_ms=1000, wallet=D(10), q=D(0), entry=D(0), margin=D(0),
                                  _changed=None, _changed_ms=1000)
        stamp = lambda: SessionExchange._update_time(account)
        self.assertEqual(stamp(), 1000)
        account.now_ms = 1200
        self.assertEqual(stamp(), 1000)
        account.wallet = D(11)
        account.now_ms = 1400
        self.assertEqual(stamp(), 1400)
        account.now_ms = 1600
        self.assertEqual(stamp(), 1400)
