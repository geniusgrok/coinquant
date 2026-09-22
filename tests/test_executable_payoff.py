import copy
import csv
import gzip
import tempfile
import unittest
from pathlib import Path
from decimal import Decimal as D
import numpy as np
from coinquant.research import spec,invocations,timestamp
from coinquant.linear_account import Account,FEE
from research.executable_payoff import account,fit_targets,predict,orders,HOUR,DAY

class ExecutablePayoffTests(unittest.TestCase):
    def fixture(self):
        start=timestamp(spec()['start']);t=next(invocations(spec()));u=next(x for x in invocations(spec()) if x>=t+7*DAY)
        rows={s:[s,'100','101','99','100','10000',s+HOUR-1,'1000000','5','5000','500000','0'] for s in range(start-31*DAY,u+HOUR,HOUR)}
        warm={s:r for s,r in rows.items() if s<start};trade={s:r for s,r in rows.items() if s>=start}
        for r in trade.values():r[3]='99.5'
        return t,u,({'klines':trade,'markPriceKlines':copy.deepcopy(trade)}, {},warm,[])
    def test_label_costs_match_shared_account_and_expiry(self):
        t,u,b=self.fixture()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'case';r=account(Path('.'),p,b,({},[]),{t:1},'test',start=t,end=u+HOUR,scenario=True)
            o=orders(p);entry=next(x for x in o if x['event']=='entry');exit=next(x for x in o if x['event']=='payoff_expiry')
            self.assertEqual(int(exit['time']),u)
            initial=D(spec()['initial_cny'])/D(spec()['cny_per_usd'])*(1-D(spec()['initial_conversion_cost']))
            q=D(entry['quantity_btc']);a=Account(initial);a.open(q,D(entry['price_or_mark']),D(99),D(200));a.close(q,D(exit['price_or_mark']))
            self.assertEqual(a.wallet,D(r['final_equity_usdt']))
            self.assertEqual(a.fees,D(r['fees_usdt']))
    def test_gap_and_liquidation_are_not_clipped_to_stop(self):
        for price,event in (('95','stop_gap'),('50','liquidation')):
            t,u,b=self.fixture();b[0]['klines'][t+HOUR][1:5]=[price]*4;b[0]['markPriceKlines'][t+HOUR][1:5]=[price]*4
            with tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp)/'case';r=account(Path('.'),p,b,({},[]),{t:1},'test',start=t,end=u+HOUR,scenario=True)
                exits=[x for x in orders(p) if x['event']!='entry'];self.assertEqual(exits[0]['event'],event)
                self.assertLess(D(exits[0]['price_or_mark']),D(99));self.assertLess(D(r['final_equity_usdt']),D(spec()['initial_cny'])/D(spec()['cny_per_usd'])*(1-D(spec()['initial_conversion_cost'])))
    def test_target_fit_uses_only_matured_training(self):
        rng=np.random.default_rng(9);boundary=timestamp('2022-01-01T00:00:00Z')
        rows=[dict(status='eligible',primary=True,t=boundary-(50-i)*10*DAY,u=boundary-(50-i)*10*DAY+7*DAY,x=rng.normal(size=5).tolist(),terminal={'net':float(rng.normal())},protected={'net':float(rng.normal())}) for i in range(40)]
        late=copy.deepcopy(rows[0]);late['u']=boundary+DAY;rows.append(late)
        xs={boundary+HOUR:[.1]*5};first=predict(rows,xs)
        late['terminal']['net']=1e12;late['protected']['net']=-1e12
        self.assertEqual(first,predict(rows,xs))
        self.assertLess(first[1][0]['max_training_maturity'],boundary-7*DAY)
    def test_future_paths_do_not_change_entry(self):
        t,u,b=self.fixture();changed=copy.deepcopy(b)
        for s,r in changed[0]['klines'].items():
            if s>t:r[1:5]=['150','155','145','150']
        for s,r in changed[0]['markPriceKlines'].items():
            if s>t:r[1:5]=['150','155','145','150']
        with tempfile.TemporaryDirectory() as tmp:
            entries=[]
            for i,data in enumerate((b,changed)):
                p=Path(tmp)/str(i);account(Path('.'),p,data,({},[]),{t:1},'test',start=t,end=u+HOUR,scenario=True)
                entries.append(next(r for r in orders(p) if r['event']=='entry'))
            self.assertEqual(*entries)
