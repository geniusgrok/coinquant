import unittest
from decimal import Decimal as D
from research.linear_replay import Account, FEE
from pancakequant.types import Blocked


class LinearAccountTests(unittest.TestCase):
    def test_long_and_short_pnl_and_fees(self):
        for side,price in ((1,110),(-1,90)):
            a=Account(D(1000));a.open(D(side),D(100),D(97 if side>0 else 103),D(124 if side>0 else 76))
            a.close(D(1),D(price))
            self.assertEqual(a.wallet,D(1010)-D(100+price)*FEE)
            self.assertEqual((a.q,a.margin),(0,0))

    def test_partial_close_preserves_remaining_protection_and_margin(self):
        a=Account(D(1000));a.open(D(2),D(100),D(97),D(124));a.close(D('.5'),D(102))
        self.assertEqual((a.q,a.margin,a.sl,a.tp),(D('1.5'),D('7.5'),D(97),D(124)))

    def test_bankruptcy_consumes_only_isolated_margin_after_entry_fee(self):
        for q,sl,tp in ((1,97,124),(-1,103,76)):
            a=Account(D(1000));a.open(D(q),D(100),D(sl),D(tp));before=a.wallet; margin=a.margin
            a.close(D(1),a.liquidation(D(0)))
            self.assertLess(abs(a.wallet-(before-margin)),D('1e-20'))

    def test_funding_direction_and_margin_shortfall(self):
        a=Account(D(1000));a.open(D(-1),D(100),D(103),D(76));before=a.wallet
        a.pay_funding(D(100),D('.001'));self.assertEqual(a.wallet,before+D('.1'))
        a.wallet=D('4');a.pay_funding(D(100),D('-.001'));self.assertEqual(a.margin,D('3.9'))

    def test_reversal_invalid_geometry_and_insufficient_margin_rejected(self):
        a=Account(D(1000))
        with self.assertRaises(Blocked):a.open(D(1),D(100),D(103),D(124))
        a.open(D(1),D(100),D(97),D(124))
        with self.assertRaises(Blocked):a.open(D(-1),D(100),D(103),D(76))
        with self.assertRaises(Blocked):a.close(D(2),D(100))
        with self.assertRaises(Blocked):Account(D(1)).open(D(1),D(100),D(97),D(124))
