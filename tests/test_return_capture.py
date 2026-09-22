from decimal import Decimal as D
import unittest
from research.persistent_hold_replay import anchored_state

class AnchoredStateTests(unittest.TestCase):
    def test_fixed_anchor_failure_and_fresh_rearm(self):
        prior=[(D(110),D(90),D(100))]*20
        bar=(D(120),D(101),D(115))
        state,anchor=anchored_state(prior+[bar],0,None)
        self.assertEqual((state,anchor),(1,D(101)))
        # A surviving close does not trail the original failure boundary.
        self.assertEqual(anchored_state(prior+[bar,(D(119),D(105),D(108))],state,anchor),(1,D(101)))
        failed=prior+[bar,(D(109),D(99),D(100))]
        self.assertEqual(anchored_state(failed,state,anchor),(0,None))
        self.assertEqual(anchored_state(failed,0,None),(0,None))
        self.assertEqual(anchored_state(failed+[(D(130),D(108),D(125))],0,None),(1,D(108)))

    def test_opposite_breakout_takes_precedence_and_short_is_symmetric(self):
        prior=[(D(110),D(90),D(100))]*20
        self.assertEqual(anchored_state(prior+[(D(105),D(80),D(85))],1,D(95)),(-1,D(105)))
        self.assertEqual(anchored_state(prior+[(D(108),D(95),D(106))],-1,D(105)),(0,None))
        self.assertEqual(anchored_state(prior+[(D(108),D(95),D(105))],-1,D(105)),(-1,D(105)))
