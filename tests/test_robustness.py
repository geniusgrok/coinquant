"""Research knobs and blocks for the overfitting audit; defaults must not change."""
import json
import math
import tempfile
from decimal import Decimal as D
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from coinquant import dfii10, opportunities
from coinquant.opportunities import FOUR_HOURS, Opportunities
from research import rebuild, robustness

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
