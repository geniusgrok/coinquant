from decimal import Decimal as D
import unittest

from research.persistent_hold_replay import recoverable_budget


class RecoverableBudgetTests(unittest.TestCase):
    def test_leaves_space_for_later_decisions(self):
        self.assertEqual(recoverable_budget(D('100'), D('100')), D('10'))
        self.assertEqual(recoverable_budget(D('55'), D('100')), D('2.5'))
        self.assertEqual(recoverable_budget(D('50'), D('100')), 0)
        self.assertEqual(recoverable_budget(D('49'), D('100')), 0)
