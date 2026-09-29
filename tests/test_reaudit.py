"""Offline reproductions of the 7c9b2b7 re-audit findings on the real session path."""
import tempfile
from decimal import Decimal as D
from unittest import TestCase
from unittest.mock import patch
from urllib.parse import parse_qsl, urlsplit

from coinquant.binance import Binance
from coinquant.config import Config
from coinquant.session import run
from coinquant.state import State
from coinquant.types import Unknown
from tests.session_venue import Venue

INTEGER = ('startTime','endTime','fromId','limit','orderId','type')


class Latent(Venue):
    """Every request passes the real adapter's signing, deadline and timeout path.

    After the entry POST each response arrives `latency` virtual seconds later;
    a response later than the request timeout is lost (a write still executes).
    """
    def __init__(self,latency):
        super().__init__();self.key,self.secret='k','s';self.latency=0;self.after_entry=latency
        self.log=[]
    def get(self,path,parameters=None):
        return Binance.get(self,path,parameters)
    def send(self,method,path,parameters):
        return Binance.send(self,method,path,parameters)
    def _transport(self,request,timeout):
        split=urlsplit(request.full_url);method=request.get_method()
        query=split.query if method=='GET' else request.data.decode()
        p={k:(int(v) if k in INTEGER and v.lstrip('-').isdigit() else v) for k,v in parse_qsl(query)
           if k not in ('timestamp','recvWindow','signature')}
        delay=self.latency;lost=delay>=timeout
        if lost and method=='GET':
            self.now+=int(timeout*1000);raise TimeoutError()
        self.log.append((self.now,method,split.path,p))
        answer=(Venue.get(self,split.path,p) if method=='GET' else Venue.send(self,method,split.path,p))
        if method=='POST' and split.path.endswith('/order') and p.get('timeInForce')=='IOC':
            self.latency=self.after_entry
        self.now+=int(min(delay,timeout)*1000)
        if lost:raise TimeoutError()
        return answer


class ReauditTests(TestCase):
    def setUp(self):
        self.risk=patch('coinquant.campaign.PRIMARY_RISK','6');self.risk.start()
        self.tmp=tempfile.TemporaryDirectory();self.directory=self.tmp.name
        self.venue=Venue();self.venue.seed(self.directory)
    def tearDown(self):self.tmp.cleanup();self.risk.stop()
    def session(self,seconds=3):
        return run(Config('123',self.directory,seconds,1),self.venue,execute=True,
                   monotonic=self.venue.monotonic,wait=self.venue.wait)
    def posts(self,kind=None):
        return [p for m,path,p in self.venue.sent if m=='POST' and path.endswith('/algoOrder') and kind in (None,p['type'])]
    def reductions(self):
        return [p for m,path,p in self.venue.sent if path.endswith('/order') and p.get('reduceOnly')=='true']
    def margins(self):
        return [p for m,path,p in self.venue.sent if path.endswith('/positionMargin')]
    def intents(self):
        with State(self.directory,'binance:BTCUSDT:live:123') as state:
            return state.db.execute('SELECT kind,status FROM intents ORDER BY updated').fetchall()
    def manual_close_and_reopen(self,price):
        """Another client closes the owned position, then opens the same size."""
        q=abs(self.venue.q);self.venue.manual=getattr(self.venue,'manual',900)
        for side,reduce in (('SELL',True),('BUY',False)):
            self.venue.manual+=1
            order=dict(side=side,reduceOnly=reduce,price=str(price),orderId=self.venue.manual,executedQty='0')
            self.venue.fill(order,q)

    def test_unknown_protection_does_not_block_a_later_safe_reduction(self):
        original=self.venue.send
        def lost_stop(method,path,p):
            if method=='POST' and path.endswith('/algoOrder') and p['type']=='STOP_MARKET' and not self.posts():
                self.venue.sent.append((method,path,p))
                self.venue.fail_reads=True  # transient outage right after the lost request
                raise TimeoutError()
            return original(method,path,p)
        self.venue.send=lost_stop
        first=self.session()
        self.assertGreater(self.venue.q,0)
        self.assertEqual(first['cleanup'],'unresolved')
        self.assertEqual(self.reductions(),[])
        self.venue.fail_reads=False
        second=self.session()
        self.assertEqual(self.venue.q,0)
        self.assertEqual(len(self.reductions()),1)
        self.assertEqual(len(self.posts('STOP_MARKET')),1)
        self.assertEqual(self.posts('TAKE_PROFIT_MARKET'),[])
        # The never-observed stop still blocks new risk until it can be retired.
        self.assertEqual(second['pending_intents'],1)
        self.venue.wait(301)
        third=self.session()
        self.assertEqual(third['pending_intents'],0)
        self.assertEqual(third['cleanup'],'verified')
        self.assertIn(('binance_algo','void'),self.intents())
        self.assertEqual(len(self.posts('STOP_MARKET')),1)

    def test_external_close_and_equal_manual_reopen_is_never_touched(self):
        original=self.venue.send
        def external(method,path,p):
            answer=original(method,path,p)
            if path.endswith('/order') and p.get('timeInForce')=='IOC':
                self.manual_close_and_reopen(self.venue.mark)
            return answer
        self.venue.send=external
        self.venue.reject_protection=True  # an attempted write would also try a reduction
        result=self.session()
        self.assertGreater(self.venue.q,0)
        self.assertEqual((self.margins(),self.posts(),self.reductions()),([],[],[]))
        self.assertEqual(result['cleanup'],'unresolved')
        self.assertTrue(any('external or unowned fill' in e['reason'] for e in result['errors']),result['errors'])

    def test_external_reopen_is_not_adopted_on_the_trade_id_proof(self):
        # A fill a day before the flat snapshot gives the entry a trade-ID cursor.
        self.venue.trades.append(dict(symbol='BTCUSDT',positionSide='BOTH',side='SELL',orderId=900,id=1,
                                      time=self.venue.now-86400000,qty='.01'))
        self.test_external_close_and_equal_manual_reopen_is_never_touched()

    def test_failed_protection_never_reduces_a_manual_fill_that_arrived_between_legs(self):
        original=self.venue.send
        def manual_after_stop(method,path,p):
            answer=original(method,path,p)
            if method=='POST' and path.endswith('/algoOrder') and p['type']=='STOP_MARKET':
                self.venue.manual=901
                self.venue.fill(dict(side='BUY',reduceOnly=False,price=str(self.venue.mark),orderId=901,
                                     executedQty='0'),D('0.005'))
            return answer
        self.venue.send=manual_after_stop
        result=self.session()
        owned=[p for m,path,p in self.venue.sent if p.get('timeInForce')=='IOC']
        self.assertEqual(len(owned),1)
        self.assertEqual(self.reductions(),[])
        self.assertGreater(self.venue.q,0)
        self.assertEqual(result['cleanup'],'unresolved')

    def test_manual_position_after_restart_is_not_adopted_during_a_history_outage(self):
        original=self.venue.send
        def crash(method,path,p):
            answer=original(method,path,p)
            if path.endswith('/order') and p.get('timeInForce')=='IOC':self.venue.fail_reads=True
            return answer
        self.venue.send=crash
        self.session()
        self.assertEqual(len(self.venue.sent),1)
        self.venue.send=original;self.venue.fail_reads=False
        self.venue.wait(600)
        self.manual_close_and_reopen(99000)
        get=self.venue.get
        def history_down(path,p=None):
            if path.endswith('/userTrades') and 'startTime' in (p or {}):raise Unknown('fixture history outage')
            return get(path,p)
        self.venue.get=history_down
        result=self.session()
        self.assertEqual(len(self.venue.sent),1)
        self.assertEqual(result['cleanup'],'unresolved')

    def test_fill_proof_after_a_week_without_trades_uses_the_flat_time_boundary(self):
        self.venue=Latent(0);self.venue.seed(self.directory)
        self.venue.trades.append(dict(symbol='BTCUSDT',positionSide='BOTH',side='SELL',orderId=900,id=1,
                                      time=self.venue.now-30*86400000,qty='.01'))
        self.assertEqual(self.session()['cleanup'],'verified')
        log=self.venue.log
        entry=next(i for i,(_,m,path,p) in enumerate(log) if p.get('timeInForce')=='IOC')
        stop=next(i for i,(_,m,path,p) in enumerate(log) if m=='POST' and p.get('type')=='STOP_MARKET')
        self.assertEqual(len([x for x in log[entry+1:stop] if x[1]=='GET']),12)
        self.assertTrue(any('startTime' in p for _,m,path,p in log[entry+1:stop] if path.endswith('/userTrades')))

    def test_owned_fill_is_protected_or_reduced_within_the_reserved_budget_under_latency(self):
        # Up to the 8 s request timeout; the old path needed 54 reads before its first stop.
        for latency in (0,1,2,3,4,5,6,7.9):
            with self.subTest(latency=latency):
                self.tmp.cleanup();self.tmp=tempfile.TemporaryDirectory();self.directory=self.tmp.name
                self.venue=Latent(latency);self.venue.seed(self.directory)
                self.session(seconds=2)
                log=self.venue.log
                entry=next(i for i,(_,m,path,p) in enumerate(log) if p.get('timeInForce')=='IOC')
                stop=next(i for i,(_,m,path,p) in enumerate(log) if m=='POST' and p.get('type')=='STOP_MARKET')
                self.assertEqual(len([x for x in log[entry+1:stop] if x[1]=='GET']),12)
                if latency==1:
                    # Twelve one-second reads plus the fixture's 1 ms write acceptance.
                    self.assertEqual(log[stop][0]-log[entry][0],12001)
                    with State(self.directory,'binance:BTCUSDT:live:123') as state:
                        times=state.get('entry_timing')
                    self.assertEqual(times['entry_send_attempt_at_ms'],log[entry][0])
                    self.assertEqual(times['stop_send_attempt_at_ms'],log[stop][0])
                    self.assertLessEqual(times['fill_confirmed_at_ms'],times['stop_send_attempt_at_ms'])
                    self.assertLessEqual(times['stop_send_attempt_at_ms'],times['stop_accepted_at_ms'])
                protected={a['orderType'] for a in self.venue.algos.values() if a['algoStatus']=='NEW'}
                # Full native protection, or a reduce-only exit removed the exposure.
                self.assertTrue(self.venue.q==0 or protected=={'STOP_MARKET','TAKE_PROFIT_MARKET'},
                                (self.venue.q,protected))
                self.assertLessEqual(len(self.reductions()),1)
                self.venue.latency=self.venue.after_entry=0
                later=self.session(seconds=2)
                self.assertEqual((later['cleanup'],later['pending_intents']),('verified',0))
                self.assertEqual(len([p for _,_,path,p in log if p.get('timeInForce')=='IOC']),1)
