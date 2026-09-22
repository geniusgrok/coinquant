import contextlib
from dataclasses import replace
from decimal import Decimal as D
import gzip
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from coinquant.linear_account import Account, LOT
from coinquant.linear_sizing import funded_target
from coinquant.opportunities import Opportunity
from coinquant.research import spec, timestamp
from coinquant.state import State
from research.bounded_execution import BoundedEntry, ExecutionStudy, MINUTE, exit_fill
from research.bounded_execution_data import validate_hour
from research.persistent_hold_replay import run
from research.verify_account_ledger import verify

T = timestamp('2020-01-01T00:00:00Z')
HOUR = 3600000


class BoundedTests(unittest.TestCase):
    def parent(self):
        account = Account(D(10000))
        parent = BoundedEntry.freeze(account,T,T-4*HOUR,D('3.6'),D(10000),D(10000),
                    D(9500),D(20000),D(6000000),None,D('.001'),D('.0002'))
        return account,parent,{t:D(100000) for t in range(T-MINUTE,T+8*MINUTE,MINUTE)}

    def test_fixed_target_does_not_expand_with_equity(self):
        a,p,v = self.parent()
        a.wallet *= 2
        for t in range(p.start,p.deadline,MINUTE):
            p.attempt(t,a,D(10000),D(10000),v,None)
            self.assertLessEqual(a.q,p.maximum)
            self.assertLessEqual(p.loss_at_stop(a),p.risk_budget)
            self.assertLessEqual(a.margin,a.wallet)
        self.assertGreater(a.q,0)
        self.assertFalse(p.available(p.deadline))

    def test_published_volume_only_and_unique_child(self):
        a,p,v = self.parent();b=replace(a);q=BoundedEntry.restore(p.record())
        future={t:(value if t<T else value*10000) for t,value in v.items()}
        first=p.attempt(T+MINUTE,a,D(10000),D(10000),v,None)
        other=q.attempt(T+MINUTE,b,D(10000),D(10000),future,None)
        self.assertEqual(first,other)
        before=replace(a)
        self.assertEqual(p.attempt(T+MINUTE,a,D(10000),D(10000),v,None)['reason'],'duplicate_step')
        self.assertEqual(a,before)
        self.assertEqual(first['volume_available_at'],T+MINUTE)

    def test_unknown_and_unprotected_do_not_increase_risk(self):
        for option in ('balance_known','outcome_known','pending_child','protection_confirmed'):
            with self.subTest(option=option):
                a,p,v=self.parent()
                p.attempt(T+MINUTE,a,D(10000),D(10000),v,None)
                before=replace(a)
                args={option: option=='pending_child'}
                p.attempt(T+2*MINUTE,a,D(10000),D(10000),v,None,**args)
                self.assertEqual(a,before);self.assertTrue(p.unresolved)
                self.assertFalse(p.available(T+3*MINUTE))

    def test_state_restart_and_stop_preserve_terminal_intent(self):
        a,p,v=self.parent()
        p.attempt(T+MINUTE,a,D(10000),D(10000),v,None)
        with tempfile.TemporaryDirectory() as directory:
            with State(directory,'offline-research') as state:state.set('bounded-parent',p.record())
            with State(directory,'offline-research') as state:q=BoundedEntry.restore(state.get('bounded-parent'))
        before=replace(a)
        self.assertEqual(q.deadline,p.deadline)
        q.attempt(q.deadline+MINUTE,a,D(10000),D(10000),v,None)
        self.assertEqual(a,before);self.assertEqual(q.terminal_reason,'deadline')
        p.finish('protection_stop',T+2*MINUTE)
        a.close(abs(a.q),D(9400));before=replace(a)
        p.attempt(T+3*MINUTE,a,D(10000),D(10000),v,None)
        self.assertEqual(a,before)

    def test_slice_prices_and_exit_cost_scale(self):
        a,p,v=self.parent()
        one=p.attempt(T+MINUTE,a,D(10000),D(10000),v,None)
        two=p.attempt(T+2*MINUTE,a,D(10005),D(10005),v,None)
        self.assertNotEqual(one['price'],two['price'])
        small,x=exit_fill(D(10000),D('.1'),D(6000000),D('.001'),D('.0002'))
        large,y=exit_fill(D(10000),D(1),D(6000000),D('.001'),D('.0002'))
        self.assertLess(large,small)
        self.assertGreater(D(y['extra_impact_usdt']),D(x['extra_impact_usdt']))

    def test_missing_and_invalid_inputs_fail_closed(self):
        a,p,v=self.parent();v.pop(T-MINUTE)
        before=replace(a)
        with self.assertRaises(ValueError):p.attempt(T+MINUTE,a,D(10000),D(10000),v,None)
        self.assertEqual(a,before)
        saved=p.record();saved['deadline']+=MINUTE
        with self.assertRaises(ValueError):BoundedEntry.restore(saved)
        for bad in (D('-1'),D('NaN'),D('Infinity')):
            with self.assertRaises(ValueError):funded_target(a,1,D(1),D(10000),D(10000),D(9500),D(20000),D(1),None,target_quantity=bad)

    def test_start_and_quantity_rounding(self):
        a,p,v=self.parent();before=replace(a)
        p.attempt(T,a,D(10000),D(10000),v,None)
        self.assertEqual(a,before)
        change=funded_target(a,1,D(999),D(10000),D(10000),D(9500),D(20000),D(999),None,target_quantity=D('.1234'),intended_add=True)
        self.assertEqual(D(change['accepted']),D('.1234')//LOT*LOT)

    def test_native_hour_reconstruction_rejects_missing_or_changed_rows(self):
        rows=[[T+i*MINUTE,'100','101','99','100','1',T+(i+1)*MINUTE-1,'100',1] for i in range(60)]
        hour=[T,'100','101','99','100','60',T+HOUR-1,'6000',60]
        self.assertTrue(validate_hour(rows,hour,trade=True)['ohlc_exact'])
        with self.assertRaises(ValueError):validate_hour(rows[:-1],hour,trade=True)
        rows[5][7]='101'
        with self.assertRaises(ValueError):validate_hour(rows,hour,trade=True)


class TimelineTests(unittest.TestCase):
    def fixture(self,stop=False):
        def row(t):return [t,'100','101','99','100','6000',t+HOUR-1,'600000','6000']
        warm={t:row(t) for t in range(timestamp('2019-12-01T00:00:00Z'),T,HOUR)}
        bars={t:row(t) for t in range(T,T+4*HOUR,HOUR)}
        series={k:bars.copy() for k in ('klines','markPriceKlines')}
        minutes={k:{t:(D(100),D(101),D(99),D(100)) for t in range(T,T+HOUR,MINUTE)} for k in series}
        if stop:
            minutes['markPriceKlines'][T+2*MINUTE]=(D(100),D(101),D(94),D(100))
        frozen=spec();frozen['development_end']='2020-01-01T04:00:00Z'
        class Model:
            def __init__(self,*args):pass
            def update(self,*args):return Opportunity(T-4*HOUR,1,D(95),D(200),None)
            def fraction(self,*args):return D('.5')
        return frozen,Model,(series,{T+2*MINUTE:D('.0001')},warm,[]),minutes

    def test_partial_stop_and_funding_share_one_timeline(self):
        frozen,model,cached,minutes=self.fixture(stop=True)
        execution=ExecutionStudy(True,False,frozenset([T]),{t:D(10000) for t in range(T-MINUTE,T+HOUR,MINUTE)})
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'out'
            with patch('research.persistent_hold_replay.spec',return_value=frozen),patch('research.persistent_hold_replay.decision_times',return_value=[T]),patch('coinquant.campaign.Campaign',model),contextlib.redirect_stdout(io.StringIO()):
                run(Path('.'),Path('.'),Path('.'),output,allocation='volatility',reference='impulse_hold',lifecycle='one_campaign',entry_side='long',risk_scale=D('3.6'),cached_inputs=cached,cached_minutes=(minutes,[]),execution=execution)
            summary=json.loads((output/'execution_summary.json').read_text())
            parent=summary['parents'][0]
            self.assertEqual(parent['terminal_reason'],'protection_or_exit:stop')
            self.assertEqual(parent['last_fill'],T+2*MINUTE)
            children=[json.loads(line) for line in (output/'execution.jsonl').read_text().splitlines() if json.loads(line)['kind']=='child']
            self.assertEqual(len(children),2)
            self.assertEqual(verify(output)['close_points'],4)
            import csv
            with gzip.open(output/'orders.csv.gz','rt') as f:orders=list(csv.DictReader(f))
            funding=[r for r in orders if r['event']=='funding_adverse_bound']
            self.assertEqual(len(funding),1)
            self.assertEqual(D(funding[0]['quantity_btc']),D(children[0]['accepted']))

    def test_default_path_matches_prechange_measured_engine(self):
        # These decompressed trace hashes were independently matched to the
        # remotely restored prechange engine on this deterministic four-hour case.
        import hashlib
        expected = {'orders': '95cf7514f3ed0663a29b2f42688101999d2e3b0cf22ef9c607f36faae1da5d1f', 'equity': '4f12a0fecf90c21c46e0f10503364c2d38b7e9d6b2ea17e10c18c72b7a3474ee', 'decisions': '0de50f4cda8d5cbf2f9d604958b2233b84981656db54ddf0ba587168c2fdbed6'}
        frozen,model,cached,minutes=self.fixture()
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'out'
            with patch('research.persistent_hold_replay.spec',return_value=frozen),patch('research.persistent_hold_replay.decision_times',return_value=[T]),patch('coinquant.campaign.Campaign',model),contextlib.redirect_stdout(io.StringIO()):
                run(Path('.'),Path('.'),Path('.'),output,allocation='volatility',reference='impulse_hold',lifecycle='one_campaign',entry_side='long',risk_scale=D('3.6'),cached_inputs=cached,cached_minutes=(minutes,[]))
            for name,digest in expected.items():
                with gzip.open(output/(name+'.csv.gz'),'rb') as stream:self.assertEqual(hashlib.sha256(stream.read()).hexdigest(),digest,name)

    def test_zero_parent_needs_no_minute_data(self):
        frozen,model,cached,minutes=self.fixture()
        model.update=lambda *args: Opportunity(T-4*HOUR,1,D(101),D(200),None)
        execution=ExecutionStudy(True,False,frozenset(),{})
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'out'
            with patch('research.persistent_hold_replay.spec',return_value=frozen),patch('research.persistent_hold_replay.decision_times',return_value=[T]),patch('coinquant.campaign.Campaign',model),contextlib.redirect_stdout(io.StringIO()):
                result=run(Path('.'),Path('.'),Path('.'),output,allocation='volatility',reference='impulse_hold',lifecycle='one_campaign',entry_side='long',risk_scale=D('3.6'),cached_inputs=cached,cached_minutes=({k:{} for k in minutes},[]),execution=execution)
            self.assertEqual(result['counts']['unfunded_parent:protection'],1)
            self.assertNotIn('entry',result['counts'])
            self.assertEqual(verify(output)['close_points'],4)

    def test_exact_boundary_funding_precedes_new_entry(self):
        frozen,model,cached,minutes=self.fixture()
        cached=(cached[0],{T:D('.001')},cached[2],cached[3])
        execution=ExecutionStudy(True,False,frozenset([T]),{t:D(10000) for t in range(T-MINUTE,T+HOUR,MINUTE)})
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'out'
            with patch('research.persistent_hold_replay.spec',return_value=frozen),patch('research.persistent_hold_replay.decision_times',return_value=[T]),patch('coinquant.campaign.Campaign',model),contextlib.redirect_stdout(io.StringIO()):
                result=run(Path('.'),Path('.'),Path('.'),output,allocation='volatility',reference='impulse_hold',lifecycle='one_campaign',entry_side='long',risk_scale=D('3.6'),cached_inputs=cached,cached_minutes=(minutes,[]),execution=execution)
            self.assertEqual(D(result['funding_bound_paid_usdt']),D(0))
            self.assertEqual(verify(output)['close_points'],4)
