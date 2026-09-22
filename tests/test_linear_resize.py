from decimal import Decimal as D
import unittest
from research.linear_replay import Account
from research.native_channel_replay import resize


class LinearResize(unittest.TestCase):
    def test_add_and_reduce_conserve_equity_except_fees(self):
        a=Account(D(1000));a.open(D(1),D(100),D(90),D(200));a.margin=D(20)
        before=a.equity(D(110));fees=a.fees
        event,amount=resize(a,D(2),D(110),D(110))
        self.assertEqual(event,'rebalance_add');self.assertEqual(amount,D(1))
        self.assertEqual(a.entry,D(105));self.assertEqual(a.equity(D(110)),before-(a.fees-fees))
        self.assertLess(a.liquidation(),a.sl)
        before=a.equity(D(120));fees=a.fees
        event,amount=resize(a,D('.5'),D(120),D(120))
        self.assertEqual(event,'rebalance_reduce');self.assertEqual(a.q,D('.5'))
        self.assertEqual(a.equity(D(120)),before-(a.fees-fees))

    def test_unfunded_or_outside_protection_add_does_not_mutate(self):
        a=Account(D(100));a.open(D(1),D(100),D(90),D(120));before=vars(a).copy()
        self.assertEqual(resize(a,D(100),D(110),D(110)),(None,D(0)))
        self.assertEqual(vars(a),before)
        self.assertEqual(resize(a,D(2),D(121),D(110)),(None,D(0)))
        self.assertEqual(vars(a),before)
