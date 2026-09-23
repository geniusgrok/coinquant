import unittest
from decimal import Decimal as D
from coinquant.opportunities import Opportunities, FOUR_HOURS

class OpportunityTests(unittest.TestCase):
    def feed(self, model, rows):
        return [model.update((i+1)*model.interval,*map(D,row)) for i,row in enumerate(rows)]

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
        for mechanism in ('squeeze','sweep','shock','impulse','impulse_hold','impulse_validity','impulse_confirmation','persistent_impulse'):
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
        self.assertEqual((a.direction,a.stop,a.expires),(1,D('113'),None))
        for i in range(22,80):self.assertEqual(m.update(i*FOUR_HOURS,D(116),D(114),D(115)),a)
        b=m.update(80*FOUR_HOURS,D(116),D(90),D(95))
        self.assertEqual(b.direction,-1)
        self.assertEqual(b.identity,80*FOUR_HOURS)

    def test_hourly_resolution_keeps_seven_calendar_days(self):
        m=Opportunities('impulse_hold',3600000)
        for i in range(20):m.update((i+1)*3600000,D(101),D(99),D(100))
        a=m.update(21*3600000,D(120),D(99),D(115))
        self.assertEqual((a.direction,a.stop),(1,D('107.5')))
        self.assertEqual(a.expires-a.identity,7*24*3600000)
        with self.assertRaises(ValueError):m.update(25*3600000,D(120),D(99),D(115))

    def test_hourly_future_deletion_and_perturbation(self):
        rows=[(101,99,100)]*20+[(120,99,115)]+[(116,114,115)]*10
        prefix=self.feed(Opportunities('impulse_hold',3600000),rows[:23])
        full=self.feed(Opportunities('impulse_hold',3600000),rows)
        changed=self.feed(Opportunities('impulse_hold',3600000),rows[:23]+[(1000,1,5)]*8)
        self.assertEqual(prefix,full[:23]);self.assertEqual(prefix,changed[:23])

    def test_realization_retires_entry_without_rewriting_prior_state(self):
        m=Opportunities('impulse_validity')
        a=self.feed(m,[(101,99,100)]*20+[(116,100,115)])[-1]
        b=m.update(22*FOUR_HOURS,D(131),D(114),D(130))
        c=m.update(23*FOUR_HOURS,D(131),D(119),D(120))
        self.assertTrue(a.entry_open)
        self.assertFalse(b.entry_open);self.assertFalse(c.entry_open)
        self.assertEqual((a.identity,a.stop,a.expires),(c.identity,c.stop,c.expires))

    def test_confirmation_is_symmetric_one_time_completed_close_transition(self):
        for side in (1,-1):
            m=Opportunities('impulse_confirmation')
            def bar(close):return (close+1,close-1,close)
            signal=100+15*side
            a=self.feed(m,[bar(100)]*20+[bar(signal)])[-1]
            target=100+30*side
            b=m.update(22*FOUR_HOURS,*map(D,bar(target)))
            c=m.update(23*FOUR_HOURS,*map(D,bar(target+side)))
            self.assertEqual(a.stop,D(100)+D('7.5')*side)
            self.assertEqual(b.stop,D(signal));self.assertEqual(c.stop,b.stop)
            self.assertIsNone(b.confirm_at)
            self.assertEqual(a.expires-a.identity,7*86400000)
            self.assertEqual((a.identity,a.take,a.expires),(b.identity,b.take,b.expires))
