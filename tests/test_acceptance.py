import unittest
from pancakequant.research import economic_limits, spec

class AcceptanceTests(unittest.TestCase):
    def test_authorized_exact_boundaries(self):
        frozen = spec()
        self.assertTrue(economic_limits('1.5', '0.499999999999999999', frozen))
        self.assertFalse(economic_limits('1.499999999999999999', '0.1', frozen))
        self.assertFalse(economic_limits('2', '0.5', frozen))
