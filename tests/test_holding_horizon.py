import math
import unittest
from research.holding_horizon_screen import score

class HoldingHorizonTests(unittest.TestCase):
    def test_requires_completed_window_and_symmetric_known_trend(self):
        self.assertEqual(score([100]*19),0)
        self.assertEqual(score([100]*20),0)
        rising=[math.exp(i*.01) for i in range(20)]
        falling=[math.exp(-i*.01) for i in range(20)]
        self.assertAlmostEqual(score(rising),1)
        self.assertAlmostEqual(score(falling),-1)
