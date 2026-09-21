import math
import unittest
from research.change_point_screen import ChangePoint, PRIOR, updated


class ChangePointTest(unittest.TestCase):
    def test_first_update_and_symmetric_history(self):
        a=ChangePoint();b=ChangePoint()
        a.add(.01)
        self.assertAlmostEqual(a.expected(),updated(PRIOR,.01)[0])
        a=ChangePoint()
        for x in [.01,.02,-.005,.03,-.08,.01]:
            a.add(x);b.add(-x)
            self.assertAlmostEqual(sum(a.weights),1)
            self.assertAlmostEqual(a.expected(),-b.expected())
            self.assertTrue(all(math.isfinite(w) and w>=0 for w in a.weights))
