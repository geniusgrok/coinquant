import json
import tempfile
from decimal import Decimal as D
from pathlib import Path
from unittest import TestCase

from coinquant.config import Config,load
from coinquant.session import run,cycle
from coinquant.lifecycle import Lifecycle
from coinquant.state import State
from coinquant.campaign import Campaign
from coinquant.types import Blocked,Unknown
from tests.session_venue import Venue


class SessionTests(TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.directory=self.tmp.name
        self.venue=Venue();self.venue.seed(self.directory)
    def tearDown(self):self.tmp.cleanup()
    def run_session(self,execute=True,seconds=11,wait=None):
        return run(Config('123',self.directory,seconds,1),self.venue,execute=execute,
                   monotonic=self.venue.monotonic,wait=wait or self.venue.wait)
    def test_finite_long_entry_hold_and_offline_protection(self):
        result=self.run_session(seconds=3)
        self.assertEqual(result['cycles'],3);self.assertEqual(result['cleanup'],'verified')
        self.assertGreater(self.venue.q,0)
        self.assertTrue(result['actual']['native_full_position_protected'])
        self.assertEqual(len([p for m,path,p in self.venue.sent if path.endswith('/order') and p.get('reduceOnly')!='true']),1)
        self.assertEqual(result['pending_intents'],0)
    def test_short_uses_same_engine_and_buy_close_all(self):
        self.venue=Venue(-1);self.venue.seed(self.directory)
        r=self.run_session(seconds=2)
        self.assertLess(self.venue.q,0);self.assertEqual(r['cleanup'],'verified')
        self.assertTrue(all(p['side']=='BUY' for m,path,p in self.venue.sent if path.endswith('/algoOrder') and m=='POST'))
    def test_read_only_runs_repeatedly_without_orders(self):
        r=self.run_session(False,seconds=3)
        self.assertEqual(r['cycles'],3);self.assertEqual(r['status'],'read_only');self.assertEqual(self.venue.sent,[])
    def test_timeout_after_fill_recovers_without_duplicate(self):
        self.venue.timeout_after_entry=True
        r=self.run_session(seconds=3)
        self.assertEqual(r['cleanup'],'verified');self.assertEqual(len(self.venue.orders),1)
    def test_unknown_entry_never_resends_even_after_restart(self):
        self.venue.timeout_before_entry=True
        a=self.run_session(seconds=2);b=self.run_session(seconds=2)
        self.assertEqual(a['cleanup'],'unresolved');self.assertEqual(b['status'],'unknown')
        self.assertEqual(len([x for x in self.venue.sent if x[1].endswith('/order')]),1)
    def test_partial_fill_protects_actual_size_and_never_adds(self):
        self.venue.fraction=D('.5');r=self.run_session(seconds=3)
        self.assertEqual(r['cleanup'],'verified');self.assertEqual(len(self.venue.orders),1)
        with State(self.directory,'binance:BTCUSDT:live:123') as s:
            self.assertIsNone(s.get('entry_plan'))
            self.assertIsNotNone(s.get('position_protection'))
    def test_failed_protection_attempts_reduce_only_and_reports_unknown(self):
        self.venue.reject_protection=True;r=self.run_session(seconds=1)
        self.assertEqual(self.venue.q,0);self.assertEqual(r['status'],'unknown')
        self.assertTrue(any(p.get('reduceOnly')=='true' for _,_,p in self.venue.sent))
    def test_restart_retains_position_and_does_not_reenter(self):
        self.run_session(seconds=1);n=len(self.venue.sent)
        r=self.run_session(seconds=2)
        self.assertEqual(r['cleanup'],'verified');self.assertEqual(len(self.venue.sent),n)
    def test_signal_expiry_closes_without_same_cycle_reversal(self):
        self.run_session(seconds=1)
        with State(self.directory,'binance:BTCUSDT:live:123') as s:
            m=Campaign.restore(s.get('linear_campaign'));m.model.active=None;s.set('linear_campaign',m.checkpoint())
        r=self.run_session(seconds=2)
        self.assertEqual(r['cleanup'],'verified');self.assertEqual(self.venue.q,0)
        self.assertTrue(all(x['algoStatus']=='CANCELED' for x in self.venue.algos.values()))
    def test_keyboard_interrupt_finishes_owned_protection(self):
        def interrupt(_):raise KeyboardInterrupt()
        r=self.run_session(seconds=10,wait=interrupt)
        self.assertEqual(r['stop_reason'],'interrupted');self.assertEqual(r['cleanup'],'verified')
    def test_disconnection_never_infers_flat_or_successful_cleanup(self):
        def disconnect(seconds):self.venue.wait(seconds);self.venue.fail_reads=True
        r=self.run_session(seconds=2,wait=disconnect)
        self.assertEqual(r['status'],'unknown');self.assertEqual(r['cleanup'],'unresolved')
        self.assertGreater(self.venue.q,0)
    def test_config_has_one_schema_and_bounded_time(self):
        for data in (dict(account_uid='0',state_dir=self.directory),dict(account_uid='123',state_dir=self.directory,poll_seconds=0),dict(account_uid='123',state_dir=self.directory,session_seconds=True)):
            with self.assertRaises(Blocked):Config(**data)
        p=Path(self.directory)/'config.json';p.write_text('{"account_uid":"123","state_dir":"x","model":"other"}')
        with self.assertRaises(Blocked):load(p)

    def test_terminal_partial_exit_reduces_only_remaining_on_next_cycle(self):
        self.run_session(seconds=1)
        self.venue.partial_exit=True
        with State(self.directory,'binance:BTCUSDT:live:123') as s:
            m=Campaign.restore(s.get('linear_campaign'));m.model.active=None;s.set('linear_campaign',m.checkpoint())
        # First partial is terminal; the next operation is sized from observed q.
        def wait(seconds):self.venue.wait(seconds);self.venue.partial_exit=False
        r=self.run_session(seconds=2,wait=wait)
        self.assertEqual(r['cleanup'],'verified');self.assertEqual(self.venue.q,0)
        exits=[p for _,_,p in self.venue.sent if p.get('reduceOnly')=='true']
        self.assertEqual(D(exits[1]['quantity']),D(exits[0]['quantity'])/2)
        self.assertNotEqual(exits[0]['newClientOrderId'],exits[1]['newClientOrderId'])

    def test_cancel_timeout_does_not_get_new_identity_on_each_poll(self):
        self.venue.fraction=D(0)
        original=self.venue.send
        def working(method,path,p):
            r=original(method,path,p)
            if method=='POST' and path.endswith('/order'):
                self.venue.orders[p['newClientOrderId']]['status']='NEW'
            if method=='DELETE':
                self.venue.orders[p['origClientOrderId']]['status']='NEW'
                raise TimeoutError()
            return r
        self.venue.send=working
        r=self.run_session(seconds=3)
        self.assertEqual(r['cleanup'],'unresolved')
        self.assertEqual(len([x for x in self.venue.sent if x[0]=='DELETE']),1)
        self.assertTrue(r['write_attempted'])

    def test_complete_native_tape_replays_identical_requests_and_decisions(self):
        from copy import deepcopy
        from research.session_replay import replay
        with State(self.directory,'binance:BTCUSDT:live:123') as s:checkpoint=s.get('linear_campaign')
        tape=dict(start_ms=self.venue.now,records=[])
        for method in ('get','send'):
            original=getattr(self.venue,method)
            def capture(*args,_original=original,_method=method):
                verb,path,p=('GET',args[0],args[1] if len(args)>1 else {}) if _method=='get' else args
                rec=dict(method=verb,path=path,parameters=deepcopy(p or {}),time_ms=self.venue.now)
                try:r=_original(*args);rec['response']=deepcopy(r);return r
                except Unknown:rec['unknown']=True;raise
                finally:tape['records'].append(rec)
            setattr(self.venue,method,capture)
        first=self.run_session(seconds=2)
        with tempfile.TemporaryDirectory() as other:
            with State(other,'binance:BTCUSDT:live:123') as s:s.set('linear_campaign',checkpoint)
            second=replay(tape,Config('123',other,2,1),execute=True)
        self.assertTrue(second['tape_complete'],second)
        self.assertEqual(first['actual'],second['actual'])
        self.assertEqual(first['model_preview'],second['model_preview'])
        self.assertEqual(first['cleanup'],second['cleanup'])
        self.assertEqual(second['status'],'no_action')
        import subprocess,sys
        with tempfile.TemporaryDirectory() as temporary:
            payload={**tape,'checkpoint':checkpoint,'execute':True,
                     'config':dict(account_uid='123',session_seconds=2,poll_seconds=1)}
            path=Path(temporary)/'tape.json';path.write_text(json.dumps(payload))
            completed=subprocess.run([sys.executable,'-m','research.session_replay',str(path),
                '--state-dir',str(Path(temporary)/'state')],capture_output=True,text=True,timeout=10)
            self.assertEqual(completed.returncode,0,completed.stderr)
            self.assertTrue(json.loads(completed.stdout)['tape_complete'])

    def test_protection_amendment_keeps_old_until_new_pair_confirmed(self):
        self.run_session(seconds=1);before=len(self.venue.sent)
        from dataclasses import replace
        with State(self.directory,'binance:BTCUSDT:live:123') as s:
            m=Campaign.restore(s.get('linear_campaign'));m.model.active=replace(m.model.active,stop=D(97000));s.set('linear_campaign',m.checkpoint())
        r=self.run_session(seconds=1)
        self.assertEqual(r['cleanup'],'verified')
        changes=[(verb,p.get('type')) for verb,path,p in self.venue.sent[before:] if path.endswith('/algoOrder')]
        self.assertEqual(changes,[('POST','STOP_MARKET'),('POST','TAKE_PROFIT_MARKET'),('DELETE',None),('DELETE',None)])
    def test_external_fill_prevents_strategy_or_cleanup_position_changes(self):
        self.run_session(seconds=1);before=len(self.venue.sent)
        self.venue.trades.append(dict(symbol='BTCUSDT',positionSide='BOTH',side='BUY',orderId=999,id=999,time=self.venue.now,qty='.001'))
        self.venue.q+=D('.001')
        r=self.run_session(seconds=1)
        self.assertEqual(r['status'],'unknown');self.assertEqual(r['cleanup'],'unresolved')
        self.assertEqual(len(self.venue.sent),before)

    def test_lost_active_stop_readback_resumes_missing_take_after_restart(self):
        original=self.venue.send
        def disconnect_after_stop(method,path,p):
            r=original(method,path,p)
            if p.get('type')=='STOP_MARKET':self.venue.fail_reads=True
            return r
        self.venue.send=disconnect_after_stop
        first=self.run_session(seconds=1)
        self.assertEqual(first['cleanup'],'unresolved');self.assertGreater(self.venue.q,0)
        self.venue.fail_reads=False;self.venue.send=original
        second=self.run_session(seconds=2)
        self.assertEqual(second['cleanup'],'verified');self.assertEqual(second['pending_intents'],0)
        self.assertEqual(len([p for _,_,p in self.venue.sent if p.get('type')=='STOP_MARKET']),1)
        self.assertEqual(len([p for _,_,p in self.venue.sent if p.get('type')=='TAKE_PROFIT_MARKET']),1)

    def test_zero_fill_retries_archive_terminal_entries(self):
        self.venue.fraction=D(0)
        r=self.run_session(seconds=3)
        self.assertEqual(r['cleanup'],'verified')
        with State(self.directory,'binance:BTCUSDT:live:123') as s:
            self.assertEqual(s.get('entry_campaigns'),{})
            self.assertEqual(len(s.get('settled_entry_campaigns')),3)
        self.venue.orders={}  # old zero-fill history can expire at the venue
        self.venue.fraction=D(1)
        r=self.run_session(seconds=1)
        self.assertEqual(r['cleanup'],'verified');self.assertGreater(self.venue.q,0)

    def test_unsent_exit_can_shrink_after_native_protection_reduction(self):
        self.run_session(seconds=1)
        with State(self.directory,'binance:BTCUSDT:live:123') as s:
            engine=Lifecycle(self.venue,s,'123',authorized=True)
            snapshot=engine.snapshot();original=self.venue.q
            # A native protective reduction won the race after the first read.
            self.venue.q=original/2;self.venue.margin/=2
            with self.assertRaises(Blocked):engine.close(snapshot)
            self.assertFalse(any(p.get('reduceOnly')=='true' for _,_,p in self.venue.sent))
            result=engine.close(engine.snapshot())
            self.assertEqual(D(result['quantity_btc']),0)
            reduction=[p for _,_,p in self.venue.sent if p.get('reduceOnly')=='true'][-1]
            self.assertEqual(D(reduction['quantity']),original/2)

    def test_stale_mark_time_cannot_mix_previous_exit_with_new_entry(self):
        from coinquant.opportunities import Opportunity
        self.run_session(seconds=1)
        self.venue.now+=14400000
        with State(self.directory,'binance:BTCUSDT:live:123') as s:
            m=Campaign.restore(s.get('linear_campaign'));m.last=self.venue.now//14400000*14400000;m.model.last=m.last;m.model.active=None;s.set('linear_campaign',m.checkpoint())
        self.run_session(seconds=1);self.assertEqual(self.venue.q,0)
        with State(self.directory,'binance:BTCUSDT:live:123') as s:
            m=Campaign.restore(s.get('linear_campaign'));m.model.active=Opportunity(m.last,1,D(95000),D(110000),m.last+14400000);s.set('linear_campaign',m.checkpoint())
        get=self.venue.get
        def stale(path,p=None):
            result=get(path,p)
            if path.endswith('/premiumIndex'):result['time']-=2000
            return result
        self.venue.get=stale
        result=self.run_session(seconds=1)
        self.assertGreater(self.venue.q,0)
        self.assertEqual(result['cleanup'],'verified',result)
        self.assertTrue(result['actual']['native_full_position_protected'])

    def test_retired_protection_history_can_expire_without_blocking_position(self):
        self.run_session(seconds=1)
        old=list(self.venue.algos)
        from dataclasses import replace
        with State(self.directory,'binance:BTCUSDT:live:123') as s:
            m=Campaign.restore(s.get('linear_campaign'));m.model.active=replace(m.model.active,stop=D(97000));s.set('linear_campaign',m.checkpoint())
        self.assertEqual(self.run_session(seconds=1)['cleanup'],'verified')
        for identity in old:del self.venue.algos[identity]
        result=self.run_session(seconds=2)
        self.assertEqual(result['cleanup'],'verified',result)
        self.assertTrue(result['actual']['native_full_position_protected'])

    def test_verified_flat_finalizes_abandoned_replacement_journal(self):
        self.run_session(seconds=1)
        old=list(self.venue.algos)
        with State(self.directory,'binance:BTCUSDT:live:123') as s:
            s.set('binance_protection_replacement',dict(done=False,request={'old_ids':old,'new_ids':['cq-never-prepared']}))
            m=Campaign.restore(s.get('linear_campaign'));m.model.active=None;s.set('linear_campaign',m.checkpoint())
        result=self.run_session(seconds=2)
        self.assertEqual(result['cleanup'],'verified')
        with State(self.directory,'binance:BTCUSDT:live:123') as s:self.assertTrue(s.get('binance_protection_replacement')['done'])

    def test_real_transport_and_budget_complete_entry_protection_and_cleanup(self):
        from io import BytesIO
        from urllib.parse import urlsplit,parse_qs
        from coinquant.binance import Binance
        backend=self.venue
        class HTTP:
            def open(self,request,timeout):
                url=urlsplit(request.full_url)
                p={k:v[0] for k,v in parse_qs(url.query if request.method=='GET' else request.data.decode()).items()}
                for k in ('timestamp','signature','recvWindow'):p.pop(k,None)
                for k in ('startTime','endTime','limit','orderId'):
                    if k in p:p[k]=int(p[k])
                if url.path.endswith('/positionMargin'):p['type']=int(p['type'])
                response=backend.get(url.path,p) if request.method=='GET' else backend.send(request.method,url.path,p)
                return BytesIO(json.dumps(response).encode())
        reader=Binance(key='fixture',secret='fixture',clock=backend.clock,opener=HTTP(),authorize_writes=True)
        result=run(Config('123',self.directory,1,1),reader,execute=True,monotonic=backend.monotonic,wait=backend.wait)
        self.assertEqual(result['cleanup'],'verified',result)
        self.assertTrue(result['actual']['native_full_position_protected'])
        self.assertLessEqual(sum(cost for _,cost in reader.request_weights),2200)

    def test_deadline_during_preflight_prevents_new_entry(self):
        original=self.venue.get
        def slow(path,p=None):
            result=original(path,p)
            if path.endswith('/depth'):self.venue.wait(2)
            return result
        self.venue.get=slow
        result=self.run_session(seconds=1)
        self.assertEqual(self.venue.q,0)
        self.assertEqual(self.venue.sent,[])
        self.assertEqual(result['cleanup'],'verified')
