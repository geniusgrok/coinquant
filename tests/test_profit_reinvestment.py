from decimal import Decimal as D
import unittest
from research.linear_replay import Account
from research.profit_reinvestment_replay import reinvest,protected_exit_equity,floor_stop

class ProfitReinvestment(unittest.TestCase):
    def test_adds_only_locked_profit_and_preserves_funded_floor(self):
        for side,entry,stop,price,tp in [(1,100,110,120,200),(-1,100,90,80,40)]:
            a=Account(D(1000),q=D(side),entry=D(entry),margin=D(50),sl=D(stop),tp=D(tp))
            floor=D(1000);before=a.wallet
            event,qty=reinvest(a,floor,D(price),D(price),D('.0011'),D(10))
            self.assertEqual(event,'rebalance_add')
            self.assertGreater(qty,0)
            self.assertGreaterEqual(protected_exit_equity(a,D('.0011')),floor-D('1e-20'))
            self.assertLess(a.wallet,before)
            self.assertLessEqual(a.margin,a.wallet)
    def test_no_add_without_locked_profit(self):
        a=Account(D(1000),q=D(1),entry=D(100),margin=D(50),sl=D(95),tp=D(200))
        before=(a.wallet,a.q,a.margin)
        self.assertEqual(reinvest(a,D(1000),D(110),D(110),D('.0011'),D(10)),(None,D(0)))
        self.assertEqual((a.wallet,a.q,a.margin),before)

    def test_stop_floor_rounding_protects_both_directions(self):
        for side,sl,tp in [(1,90,150),(-1,110,50)]:
            a=Account(D(1000),q=D(side),entry=D(100),margin=D(50),sl=D(sl),tp=D(tp))
            a.sl=floor_stop(a,D(1005),D('.0011'))
            self.assertGreaterEqual(protected_exit_equity(a,D('.0011')),D(1005))
