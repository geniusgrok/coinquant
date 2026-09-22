from decimal import Decimal as D
import unittest
from research.edge_allocation import target_fraction

class EdgeAllocationTests(unittest.TestCase):
    def test_cold_start_no_edge_and_exposure_ceiling(self):
        self.assertEqual(target_fraction([D('.01')]*59),0)
        self.assertEqual(target_fraction([D('-.01')]*252),0)
        self.assertEqual(target_fraction([D(0)]*252),0)
        self.assertEqual(target_fraction([D('.01')]*252),2)

    def test_net_edge_and_variance_determine_target(self):
        observations=[D('.12'),D('-.10')]*126
        self.assertEqual(target_fraction(observations),D('.25')*D('.01')/D('.0122'))
        self.assertLess(target_fraction(observations[:60]),target_fraction(observations))
