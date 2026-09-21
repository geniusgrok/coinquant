from decimal import Decimal as D
import unittest
from research.funding_crowding import direction, funding_cash
from research.persistent_hold_replay import HOUR

class FundingCrowdingTests(unittest.TestCase):
    def test_entry_excluded_exit_included_and_exact_boundary_uses_open(self):
        times=[0,HOUR,2*HOUR,3*HOUR]
        rates=[D('.01')]*4
        marks={t:[t,'100','200','50','150'] for t in times}
        self.assertEqual(funding_cash(times,rates,marks,0,2*HOUR,1,D(100)),D('.02'))
        self.assertEqual(funding_cash(times,rates,marks,0,2*HOUR,-1,D(100)),D('-.02'))
        self.assertEqual(funding_cash([1],[D('.01')],marks,0,HOUR,1,D(100)),D('.02'))
        self.assertEqual(funding_cash([1],[D('.01')],marks,0,HOUR,-1,D(100)),D('-.005'))

    def test_crowding_requires_past_baseline_and_prespecified_sign(self):
        self.assertEqual(direction([D('.0001')]*90),0)
        self.assertEqual(direction([D('.0001')]*90+[D('.0002')]),-1)
        self.assertEqual(direction([D('.0001')]*90+[D(0)]),1)
        self.assertEqual(direction([D('.0001')]*91),0)
