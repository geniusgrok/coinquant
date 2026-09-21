import unittest
from decimal import Decimal as D
from pancakequant.types import Bar, Blocked, INTERVAL_MS
from research.sparse_trend import signal


def series(ratio):
    prices = [D('100') * D(ratio) ** i for i in range(121)]
    return [Bar(i * INTERVAL_MS, p, p, p, p) for i, p in enumerate(prices)]


class SparseTrendTests(unittest.TestCase):
    def test_long_short_symmetry_and_bounded_conviction(self):
        up = signal(series('1.001'), 121 * INTERVAL_MS)
        down = signal(series(D(1) / D('1.001')), 121 * INTERVAL_MS)
        self.assertEqual((up.direction, down.direction), (1, -1))
        self.assertLess(abs(up.score + down.score), D('1e-20'))
        self.assertTrue(0 < up.conviction < 1)
        self.assertGreater(up.daily_rms, 0)

    def test_flat_prices_have_no_signal_or_nan(self):
        value = signal(series('1'), 121 * INTERVAL_MS)
        self.assertEqual((value.score, value.conviction, value.direction, value.daily_rms), (0, 0, 0, 0))

    def test_future_stale_missing_and_short_history_fail_closed(self):
        bars = series('1.001')
        for data, now in ((bars, 120 * INTERVAL_MS),
                          (bars, 122 * INTERVAL_MS),
                          (bars[:60] + bars[61:], 121 * INTERVAL_MS),
                          (bars[1:], 121 * INTERVAL_MS)):
            with self.assertRaises(Blocked):
                signal(data, now)

    def test_scale_invariance(self):
        bars = series('1.001')
        scaled = [Bar(b.time, b.open * 10, b.high * 10, b.low * 10, b.close * 10) for b in bars]
        self.assertEqual(signal(bars, 121 * INTERVAL_MS), signal(scaled, 121 * INTERVAL_MS))

    def test_same_complete_candle_produces_same_decision(self):
        bars = series('1.001')
        self.assertEqual(signal(bars, 121 * INTERVAL_MS), signal(bars, 121 * INTERVAL_MS + 3_600_000))
