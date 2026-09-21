import unittest
from decimal import Decimal as D
from pancakequant.opportunities import Opportunities, FOUR_HOURS

class OpportunityTests(unittest.TestCase):
    def feed(self, model, rows):
        return [model.update((i+1)*FOUR_HOURS,*map(D,row)) for i,row in enumerate(rows)]

    def test_sweep_waits_for_right_bars_and_next_sweep(self):
        rows=[(101,90,100),(103,91,100),(105,92,100),(110,93,100),
              (106,94,100),(104,95,100),(102,96,100),(112,97,105)]
        out=self.feed(Opportunities('sweep'),rows)
        self.assertTrue(all(x is None for x in out[:7]))
        self.assertEqual((out[-1].identity,out[-1].direction,out[-1].stop,out[-1].take),
                         (8*FOUR_HOURS,-1,D(112),D(91)))

    def test_squeeze_boundary_precedes_breakout_and_is_consumed(self):
        m=Opportunities('squeeze')
        out=self.feed(m,[(101,99,100)]*24+[(111,100,110)])
        self.assertTrue(all(x is None for x in out[:-1]))
        a=out[-1];self.assertEqual((a.direction,a.stop,a.take),(1,D(99),D(132)))
        self.assertEqual(m.update(26*FOUR_HOURS,D(112),D(109),D(111)),a)
        self.assertIsNone(m.update(27*FOUR_HOURS,D(112),D(98),D(100)))
        self.assertIsNone(m.update(28*FOUR_HOURS,D(115),D(100),D(114)))

    def test_prefix_cannot_depend_on_future_or_rewrite_objects(self):
        rows=[(101,99,100)]*24+[(111,100,110)]+[(112,109,111)]*10
        for mechanism in ('squeeze','sweep','shock','impulse','impulse_hold','persistent_impulse'):
            original=self.feed(Opportunities(mechanism),rows)
            prefix=self.feed(Opportunities(mechanism),rows[:26])
            changed=self.feed(Opportunities(mechanism),rows[:26]+[(1000,1,5)]*9)
            self.assertEqual(original[:26],prefix)
            self.assertEqual(changed[:26],prefix)

    def test_missing_bar_fails_closed(self):
        m=Opportunities('sweep');m.update(FOUR_HOURS,D(101),D(99),D(100))
        with self.assertRaises(ValueError):m.update(3*FOUR_HOURS,D(101),D(99),D(100))

    def test_impulse_uses_prior_volatility_and_persistent_has_no_timer(self):
        rows=[(101,99,100)]*20+[(120,99,115)]
        m=Opportunities('persistent_impulse');a=self.feed(m,rows)[-1]
        self.assertEqual((a.direction,a.stop,a.expires),(1,D('107.5'),None))
        for i in range(22,80):self.assertEqual(m.update(i*FOUR_HOURS,D(116),D(114),D(115)),a)
        b=m.update(80*FOUR_HOURS,D(116),D(90),D(95))
        self.assertEqual(b.direction,-1)
        self.assertEqual(b.identity,80*FOUR_HOURS)
