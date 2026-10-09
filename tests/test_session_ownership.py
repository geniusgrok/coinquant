"""Session ownership and protection under unavailable or delayed responses."""
import tempfile
from dataclasses import replace
from decimal import Decimal as D
from unittest import TestCase
from unittest.mock import patch
from urllib.parse import parse_qsl, urlsplit

from coinquant.binance import Binance
from coinquant.campaign import Campaign
from coinquant.config import Config
from coinquant.lifecycle import Lifecycle
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


class SessionOwnershipTests(TestCase):
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

    def test_manual_equal_reopen_after_exit_decision_is_not_reduced(self):
        self.session(seconds=1)
        with State(self.directory,'binance:BTCUSDT:live:123') as state:
            model=Campaign.restore(state.get('linear_campaign'))
            model.model.active=None
            state.set('linear_campaign',model.checkpoint())
        original=self.venue.get;writes=len(self.venue.sent);fired=[]
        def get(path,p=None):
            if path.endswith('/exchangeInfo') and not fired:
                fired.append(True)
                wallet,entry=self.venue.wallet,self.venue.entry
                self.manual_close_and_reopen(entry)
                # Preserve size, entry and wallet: the new fill cursor must still
                # stop the write, even if other sampled values happen to match.
                self.venue.wallet=wallet
            return original(path,p)
        self.venue.get=get
        result=self.session(seconds=1)
        self.assertTrue(fired)
        self.assertGreater(self.venue.q,0)
        self.assertEqual(len(self.venue.sent),writes)
        self.assertEqual(self.reductions(),[])
        self.assertEqual(result['cleanup'],'unresolved')

    def test_manual_reverse_after_exit_decision_does_not_change_reduction_side(self):
        self.session(seconds=1)
        with State(self.directory,'binance:BTCUSDT:live:123') as state:
            model=Campaign.restore(state.get('linear_campaign'))
            model.model.active=None
            state.set('linear_campaign',model.checkpoint())
        original=self.venue.get;writes=len(self.venue.sent);fired=[]
        def get(path,p=None):
            if path.endswith('/exchangeInfo') and not fired:
                fired.append(True);q=self.venue.q
                for identity,reduce in ((900,True),(901,False)):
                    self.venue.fill(dict(side='SELL',reduceOnly=reduce,price=str(self.venue.mark),
                                         orderId=identity,executedQty='0'),q)
            return original(path,p)
        self.venue.get=get
        result=self.session(seconds=1)
        self.assertTrue(fired)
        self.assertLess(self.venue.q,0)
        self.assertEqual(len(self.venue.sent),writes)
        self.assertEqual(self.reductions(),[])
        self.assertEqual(result['cleanup'],'unresolved')

    def test_native_creation_age_renews_unchanged_protection_with_fresh_ids(self):
        self.session(seconds=1)
        for order in self.venue.algos.values():
            order['createTime']=self.venue.now-75*86400000
        original=self.venue.send
        def send(method,path,p):
            result=original(method,path,p)
            if method=='POST' and path.endswith('/algoOrder'):
                self.venue.algos[p['clientAlgoId']]['createTime']=self.venue.now
            return result
        self.venue.send=send
        old_ids=set(self.venue.algos)
        with State(self.directory,'binance:BTCUSDT:live:123') as state:
            model=Campaign.restore(state.get('linear_campaign'))
            before=state.get('position_protection')
            self.venue.begin_cycle(120)
            engine=Lifecycle(self.venue,state,'123',authorized=True)
            result=engine.maintain(model,self.venue.snapshot('123'))
            after=state.get('position_protection')
            self.assertNotEqual(before['epoch'],after['epoch'])
            self.assertEqual((before['stop'],before['take']),(after['stop'],after['take']))
            new_ids={a['clientAlgoId'] for a in result['open_algos']}
            self.assertEqual(len(new_ids),2)
            self.assertFalse(old_ids & new_ids)
            self.assertTrue(all(self.venue.algos[i]['algoStatus']=='CANCELED' for i in old_ids))
            writes=len(self.venue.sent)
            engine.maintain(model,result)
            self.assertEqual(len(self.venue.sent),writes)

    def test_acceptance_observation_is_not_used_as_native_creation_age(self):
        self.session(seconds=1)
        writes=len(self.venue.sent)
        with State(self.directory,'binance:BTCUSDT:live:123') as state:
            protection=state.get('position_protection')
            protection['accepted_at_ms']=self.venue.now-80*86400000
            state.set('position_protection',protection)
            self.venue.begin_cycle(120)
            Lifecycle(self.venue,state,'123',authorized=True).maintain(
                Campaign.restore(state.get('linear_campaign')),self.venue.snapshot('123'))
        self.assertEqual(len(self.venue.sent),writes)

    def test_over_history_limit_geometry_change_does_not_cancel_old_protection(self):
        self.session(seconds=1)
        active_ids={identity for identity,a in self.venue.algos.items() if a['algoStatus']=='NEW'}
        for order in self.venue.algos.values():
            order['createTime']=self.venue.now-90*86400000
        writes=len(self.venue.sent)
        with State(self.directory,'binance:BTCUSDT:live:123') as state:
            model=Campaign.restore(state.get('linear_campaign'))
            model.model.active=replace(model.model.active,stop=model.model.active.stop+D(100))
            self.venue.begin_cycle(120)
            with self.assertRaisesRegex(Unknown,'outside algo history'):
                Lifecycle(self.venue,state,'123',authorized=True).maintain(model,self.venue.snapshot('123'))
        self.assertEqual(len(self.venue.sent),writes)
        self.assertTrue(all(self.venue.algos[i]['algoStatus']=='NEW' for i in active_ids))

    def test_exit_progress_requires_owned_fills_even_when_protection_wins_readback(self):
        for owned in (True,False):
            with self.subTest(owned=owned):
                self.tmp.cleanup();self.tmp=tempfile.TemporaryDirectory();self.directory=self.tmp.name
                self.venue=Venue();self.venue.seed(self.directory);self.session(seconds=1)
                original=self.venue.send
                def race(method,path,p):
                    if method!='POST' or p.get('reduceOnly')!='true':
                        return original(method,path,p)
                    self.venue.now+=1;self.venue.sent.append((method,path,dict(p)))
                    order=dict(p,orderId=len(self.venue.orders)+1,clientOrderId=p['newClientOrderId'],
                               reduceOnly=True,origQty=p['quantity'],executedQty='0',status='EXPIRED')
                    self.venue.orders[p['newClientOrderId']]=order
                    self.venue.fill(order,D(p['quantity'])//D('.002')*D('.001'))
                    child=dict(symbol='BTCUSDT',positionSide='BOTH',side='SELL',type='MARKET',
                               orderId=900001,clientOrderId='native-child',reduceOnly=True,
                               origQty=str(self.venue.q),executedQty='0',status='EXPIRED')
                    self.venue.orders['native-child']=child
                    self.venue.fill(child,D('.001'))
                    if owned:
                        stop=next(a for a in self.venue.algos.values() if a['orderType']=='STOP_MARKET' and a['algoStatus']=='NEW')
                        stop.update(algoStatus='FINISHED',actualOrderId=900001)
                    return dict(order)
                self.venue.send=race
                with State(self.directory,'binance:BTCUSDT:live:123') as state:
                    self.venue.begin_cycle(120)
                    engine=Lifecycle(self.venue,state,'123',authorized=True)
                    reason='partial exit remains' if owned else 'external or unowned fill'
                    with self.assertRaisesRegex(Unknown,reason):
                        engine.close(self.venue.snapshot('123'))
                    self.assertEqual(engine.exit_progress,1 if owned else 0)
                self.assertEqual(len(self.reductions()),1)
                self.assertGreater(self.venue.q,0)


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


    def test_owned_fill_is_protected_or_reduced_within_the_reserved_budget_under_latency(self):
        # Cover fast responses, delayed protection, and the request-timeout boundary.
        for latency in (0,2,7.9):
            with self.subTest(latency=latency):
                self.tmp.cleanup();self.tmp=tempfile.TemporaryDirectory();self.directory=self.tmp.name
                self.venue=Latent(latency);self.venue.seed(self.directory)
                self.session(seconds=2)
                log=self.venue.log
                entry=next(i for i,(_,m,path,p) in enumerate(log) if p.get('timeInForce')=='IOC')
                stop=next(i for i,(_,m,path,p) in enumerate(log) if m=='POST' and p.get('type')=='STOP_MARKET')
                protected={a['orderType'] for a in self.venue.algos.values() if a['algoStatus']=='NEW'}
                # Full native protection, or a reduce-only exit removed the exposure.
                self.assertTrue(self.venue.q==0 or protected=={'STOP_MARKET','TAKE_PROFIT_MARKET'},
                                (self.venue.q,protected))
                self.assertLessEqual(len(self.reductions()),1)
                self.venue.latency=self.venue.after_entry=0
                later=self.session(seconds=2)
                self.assertEqual((later['cleanup'],later['pending_intents']),('verified',0))
                self.assertEqual(len([p for _,_,path,p in log if p.get('timeInForce')=='IOC']),1)
