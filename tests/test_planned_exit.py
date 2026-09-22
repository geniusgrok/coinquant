from dataclasses import replace
from decimal import Decimal as D
import unittest

from coinquant.linear_account import Account, FEE
from coinquant.capital import CapitalBudget, HOUR
from research.planned_exit import PlannedExit, MINUTE


class PlannedExitTests(unittest.TestCase):
    def fixture(self, sliced=True, stress=False):
        now=9*HOUR
        a=Account(D(10000),D(10),D(100),D(350),D(80),D(160))
        b=CapitalBudget.from_history(now,{0:D('.0001'),8*HOUR:D('.0001')},D(600000),D('.001'),D('.0002'))
        p=PlannedExit.freeze(a,now,7,D(100),D(100),'confirmed-entry-child',b,sliced=sliced,stress=stress)
        quotes={t:D(5000) for t in range(now-MINUTE,p.deadline+MINUTE,MINUTE)}
        return a,p,quotes

    def test_distinct_capacities_deadline_and_cash(self):
        a,p,quotes=self.fixture();original=replace(a);children=[]
        for i in range(6):
            t=p.start+i*MINUTE
            c=p.attempt(t,a,D(100+i),D(100+i),quotes,None);children.append(c)
        self.assertEqual(a.q,0);self.assertEqual(p.filled,p.maximum)
        self.assertEqual(children[-1]['event'],'regime_exit_deadline')
        self.assertEqual(len({c['volume_minute'] for c in children[:-1]}),5)
        expected=original.wallet
        for c in children:
            q,price=D(c['accepted']),D(c['fill_price'])
            expected+=q*(price-original.entry)-q*price*FEE
        self.assertEqual(a.wallet,expected)
        self.assertTrue(all(c['original_anchor']==p.anchor_child for c in children))

    def test_preparation_equal_stress_does_not_extend_window(self):
        a,control,q=self.fixture(False,True);b,sliced,_=self.fixture(True,True)
        self.assertEqual(control.start,sliced.start)
        self.assertEqual(control.deadline-control.start,300000)
        self.assertEqual(control.start-control.call_time,120000)
        self.assertEqual(control.attempt(control.call_time,a,D(100),D(100),q,None)['accepted'],'0')
        c=control.attempt(control.start,a,D(100),D(100),q,None)
        self.assertEqual(D(c['accepted']),10);self.assertEqual(a.q,0)

    def test_stop_competition_and_restart_cannot_reopen(self):
        a,p,q=self.fixture()
        c=p.attempt(p.start,a,D(100),D(100),q,None)
        restored=PlannedExit.restore(p.record());before=replace(a)
        self.assertEqual(restored.attempt(p.start,a,D(100),D(100),q,None)['reason'],'duplicate_step')
        self.assertEqual(before,a)
        a.close(a.q,D(79))
        self.assertEqual(restored.attempt(p.start+MINUTE,a,D(79),D(79),q,None)['reason'],'protection_closed')
        self.assertEqual(a.q,0)
        self.assertEqual(c['original_anchor'],'confirmed-entry-child')

    def test_unknown_and_missing_protection_do_not_mutate_account(self):
        for kwargs in ({'outcome_known':False},{'pending_child':True},{'protection_confirmed':False}):
            a,p,q=self.fixture();before=replace(a)
            c=p.attempt(p.start,a,D(100),D(100),q,None,**kwargs)
            self.assertTrue(p.unresolved);self.assertEqual(a,before);self.assertEqual(c['accepted'],'0')
            restored=PlannedExit.restore(p.record())
            restored.attempt(p.start+MINUTE,a,D(100),D(100),q,None)
            self.assertEqual(a,before)

    def test_safety_bypasses_prepare_and_participation(self):
        a,p,q=self.fixture();a.wallet=D(350)
        c=p.attempt(p.call_time,a,D(100),D(100),q,None)
        self.assertEqual(c['event'],'planned_exit_safety');self.assertEqual(a.q,0)

    def test_future_volume_price_not_used(self):
        a,p,q=self.fixture();b,r,_=self.fixture();changed=dict(q)
        changed[p.start-MINUTE]=D('999999999')
        c=p.attempt(p.start,a,D(100),D(100),q,None)
        d=r.attempt(r.start,b,D(100),D(100),changed,None)
        self.assertEqual(c,d);self.assertEqual(a,b)

    def test_control_and_deadline_use_same_known_minute_capacity(self):
        from research.bounded_execution import exit_fill
        a,p,q=self.fixture(False)
        c=p.attempt(p.start,a,D(100),D(100),q,None)
        price,_=exit_fill(D(100),D(10),D(5000)*60,D('.001'),D('.0002'))
        self.assertEqual(D(c['fill_price']),price)
        a,p,q=self.fixture(True)
        c=p.attempt(p.deadline,a,D(100),D(100),q,None)
        self.assertEqual(D(c['fill_price']),price)

    def test_missing_deadline_is_unknown_not_success(self):
        a,p,q=self.fixture();before=replace(a)
        p.attempt(p.deadline+MINUTE,a,D(100),D(100),q,None)
        self.assertTrue(p.unresolved);self.assertEqual(a,before)


if __name__=='__main__':unittest.main()
