"""Manual restart schedules use current native execution, never historical fills."""
from datetime import datetime, timezone
from decimal import Decimal as D
from tempfile import TemporaryDirectory
from unittest import TestCase

from coinquant.campaign import Campaign
from coinquant.config import Config
from coinquant.linear_preview import advance
from coinquant.opportunities import FOUR_HOURS, Opportunity
from coinquant.session import run
from coinquant.state import State
from coinquant.types import Unknown
from tests.session_venue import Venue

SCOPE='binance:BTCUSDT:live:123'


class ManualRestartSchedule(TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.directory=self.tmp.name
        self.venue=Venue();self.venue.seed(self.directory)
        with State(self.directory,SCOPE) as state:
            model=Campaign.restore(state.get('linear_campaign'))
            self.start=model.last
            model.model.active=Opportunity(self.start,1,D(95000),D(600000),
                                           self.start+42*FOUR_HOURS)
            state.set('linear_campaign',model.checkpoint())

    def session(self, *, execute=True):
        return run(Config('123',self.directory,1,1),self.venue,execute=execute,
                   monotonic=self.venue.monotonic,wait=self.venue.wait)

    def offline(self, count, *, interrupted=False, take_touch=False, mark='100000'):
        bars=[dict(time=self.start+i*FOUR_HOURS,high='101000',low='99000',close='100000')
              for i in range(count)]
        if take_touch:bars[1]['high']='111000'
        end=self.start+count*FOUR_HOURS
        self.venue.now=end+1000;self.venue.mark=D(mark)
        reads=[]
        def completed(start=None,on_page=None):
            reads.append(start)
            remaining=[bar for bar in bars if bar['time']+FOUR_HOURS>start]
            if on_page and remaining:
                on_page(remaining[:1])
                if interrupted:raise Unknown('interrupted market catch-up')
                if len(remaining)>1:on_page(remaining[1:])
            return dict(interval_ms=FOUR_HOURS,complete_through=end,candles=remaining)
        self.venue.completed_market=completed
        return reads

    def open_with_near_take(self):
        with State(self.directory,SCOPE) as state:
            model=Campaign.restore(state.get('linear_campaign'))
            model.model.active=Opportunity(self.start,1,D(95000),D(110000),
                                           self.start+42*FOUR_HOURS)
            state.set('linear_campaign',model.checkpoint())
        self.assertEqual(self.session()['cleanup'],'verified')
        with State(self.directory,SCOPE) as state:
            return state.get('position_protection')

    def test_missed_seven_day_expiry_exits_at_next_execution_after_readonly_catchup(self):
        self.assertEqual(self.session()['cleanup'],'verified')
        original_quantity=self.venue.q;writes=len(self.venue.sent);fills=len(self.venue.trades)
        self.offline(45)
        result=self.session(execute=False)
        self.assertEqual(result['model_preview']['action'],'exit',result)
        self.assertEqual(len(self.venue.sent),writes)
        self.assertEqual(len(self.venue.trades),fills)
        self.assertEqual(self.venue.q,original_quantity)
        with State(self.directory,SCOPE) as state:
            model=Campaign.restore(state.get('linear_campaign'))
            self.assertEqual(model.last,self.start+45*FOUR_HOURS)
            self.assertEqual(model.exit_cause,'time')
        restarted=self.venue.now
        result=self.session()
        self.assertEqual(result['cleanup'],'verified',result)
        self.assertEqual(self.venue.q,0)
        self.assertTrue(all(t['time']>=restarted for t in self.venue.trades[fills:]))
        self.assertEqual(len([p for _,_,p in self.venue.sent[writes:] if p.get('reduceOnly')=='true']),1)

    def test_macro_state_after_manual_gap_exits_now_without_replaying_macro_orders(self):
        with State(self.directory,SCOPE) as state:
            model=Campaign.restore(state.get('linear_campaign'));model.model.active=None
            model.daily_lows.extend([D(90000)]*10)
            state.set('linear_campaign',model.checkpoint())
        row=dict(missing_reason=None,latest_value='1',prior20_value='1.3',
                 latest_observation_date=datetime.fromtimestamp(self.venue.now/1000,timezone.utc).date().isoformat(),
                 latest_value_available_ms=self.venue.now-1000,
                 prior20_value_available_ms=self.venue.now-1000)
        self.venue.dfii10_snapshot=lambda:row
        self.assertEqual(self.session()['cleanup'],'verified')
        self.assertGreater(self.venue.q,0)
        fills=len(self.venue.trades);writes=len(self.venue.sent)
        self.offline(18)
        self.venue.dfii10_snapshot=lambda:dict(row,missing_reason='stale')
        readonly=self.session(execute=False)
        self.assertEqual(readonly['model_preview']['action'],'exit',readonly)
        self.assertEqual(len(self.venue.sent),writes)
        self.assertEqual(len(self.venue.trades),fills)
        restarted=self.venue.now
        result=self.session()
        self.assertEqual(result['cleanup'],'verified',result)
        self.assertEqual(self.venue.q,0)
        self.assertTrue(all(t['time']>=restarted for t in self.venue.trades[fills:]))

    def test_interrupted_catchup_resumes_saved_bar_without_changing_exchange_protection(self):
        self.assertEqual(self.session()['cleanup'],'verified')
        writes=len(self.venue.sent);fills=len(self.venue.trades)
        with State(self.directory,SCOPE) as state:
            protection=state.get('position_protection')
        self.offline(6,interrupted=True)
        failed=self.session(execute=False)
        self.assertEqual(failed['status'],'unknown')
        with State(self.directory,SCOPE) as state:
            self.assertEqual(Campaign.restore(state.get('linear_campaign')).last,self.start+FOUR_HOURS)
            self.assertEqual(state.get('position_protection'),protection)
        reads=self.offline(6)
        finished=self.session(execute=False)
        self.assertEqual(finished['status'],'read_only',finished)
        self.assertEqual(reads[0],self.start+FOUR_HOURS)
        self.assertEqual(len(self.venue.sent),writes)
        self.assertEqual(len(self.venue.trades),fills)
        with State(self.directory,SCOPE) as state:
            self.assertEqual(Campaign.restore(state.get('linear_campaign')).last,self.start+6*FOUR_HOURS)
            self.assertEqual(state.get('position_protection'),protection)

    def test_protection_accepted_inside_a_bar_is_not_backdated_to_that_bar_start(self):
        with State(self.directory,SCOPE) as state:
            model=Campaign.restore(state.get('linear_campaign'))
        model.model.active=Opportunity(self.start,1,D(100000),D(600000),None,
                                       D(110000),D(10000),D(130000),True)
        model.model.close=D(125000);model.entry_fill=D(110000);model.filled(self.start)
        protection=dict(campaign=self.start,stop='120000',take='600000',accepted_at_ms=self.start+1)
        model.update(self.start+FOUR_HOURS,D(130000),D(115000),D(125000),
                     effective_protection=protection)
        self.assertIsNone(model.exit_cause)
        self.assertEqual(model.action(D(1)),'hold')
        # Only the following complete bar was covered by the accepted geometry
        # for its full interval; its stop condition still awaits a current mark.
        model.update(self.start+2*FOUR_HOURS,D(130000),D(119000),D(125000),
                     effective_protection=protection)
        self.assertEqual(model.exit_cause,'price')
        self.assertEqual(model.exit_stop,'120000')
        self.assertEqual(model.model.active.identity,self.start)

    def test_current_risk_tightening_preserves_the_previous_offline_take_condition(self):
        previous=self.open_with_near_take()
        fills=len(self.venue.trades);writes=len(self.venue.sent)
        self.offline(3,take_touch=True,mark='108000')
        restarted=self.venue.now
        result=self.session()
        self.assertEqual(result['cleanup'],'verified',result)
        self.assertEqual(result['model_preview']['action'],'exit',result)
        self.assertEqual(self.venue.q,0)
        replacements=[p for method,path,p in self.venue.sent[writes:]
                      if method=='POST' and path.endswith('/algoOrder') and p['type']=='STOP_MARKET']
        self.assertTrue(any(D(p['triggerPrice'])>D(previous['stop']) for p in replacements))
        self.assertTrue(all(t['time']>=restarted for t in self.venue.trades[fills:]))

    def test_offline_take_survives_multiple_risk_replacements_and_interrupted_restarts(self):
        previous=self.open_with_near_take();fills=len(self.venue.trades)
        self.offline(3,interrupted=True,take_touch=True,mark='108000')
        first=self.session()
        self.assertEqual(first['status'],'unknown',first)
        self.assertGreater(self.venue.q,0)
        with State(self.directory,SCOPE) as state:
            self.assertEqual(Campaign.restore(state.get('linear_campaign')).last,self.start+FOUR_HOURS)
            first_stop=D(state.get('position_protection')['stop'])
            self.assertGreater(first_stop,D(previous['stop']))
            self.assertTrue(any(p['accepted_at_ms']==previous['accepted_at_ms']
                                for p in state.get('protection_catchup')))
        self.offline(4,take_touch=True,mark='109000')
        def unavailable(**kwargs):raise Unknown('market still unavailable after risk maintenance')
        self.venue.completed_market=unavailable
        second=self.session()
        self.assertEqual(second['status'],'unknown',second)
        self.assertEqual(len(self.venue.trades),fills)
        with State(self.directory,SCOPE) as state:
            self.assertGreater(D(state.get('position_protection')['stop']),first_stop)
            self.assertGreaterEqual(len(state.get('protection_catchup')),2)
        self.offline(5,take_touch=True,mark='109000')
        restarted=self.venue.now
        result=self.session()
        self.assertEqual(result['cleanup'],'verified',result)
        self.assertEqual(result['model_preview']['action'],'exit',result)
        self.assertEqual(self.venue.q,0)
        self.assertTrue(all(t['time']>=restarted for t in self.venue.trades[fills:]))
        with State(self.directory,SCOPE) as state:
            self.assertEqual(state.get('protection_catchup'),[])

    def test_explicit_no_previous_protection_does_not_use_a_newly_recovered_pair(self):
        with State(self.directory,SCOPE) as state:
            model=Campaign.restore(state.get('linear_campaign'))
            model.entry_fill=D(100000);model.filled(self.start)
            before=model.checkpoint();state.set('linear_campaign',before)
            state.set('position_protection',dict(campaign=self.start,stop='100500',
                                                 take='600000',accepted_at_ms=self.start-1))
            self.offline(1)
            skipped,_,_=advance(state,self.venue,effective_protection=None)
            self.assertIsNone(skipped.exit_cause)
            state.set('linear_campaign',before)
            current,_,_=advance(state,self.venue)
            self.assertEqual(current.exit_cause,'price')

    def test_only_same_geometry_renewal_covers_a_candle_spanning_replacement(self):
        for stop,expected in [('95000','take'),('103000',None)]:
            with self.subTest(stop=stop),State(self.directory,SCOPE) as state:
                model=Campaign.restore(state.get('linear_campaign'))
                model.last=model.model.last=self.start
                model.model.active=Opportunity(self.start,1,D(95000),D(110000),
                                               self.start+42*FOUR_HOURS)
                model.entry_fill=D(100000);model.filled(self.start)
                model.exit_cause=model.exit_stop=model.exit_campaign=None
                previous=dict(campaign=self.start,stop='95000',take='110000',accepted_at_ms=self.start+1)
                state.set_many({'linear_campaign':model.checkpoint(),
                    'position_protection':dict(campaign=self.start,stop=stop,take='110000',
                                              accepted_at_ms=self.start+FOUR_HOURS+1000),
                    'protection_catchup':[{**previous,'ended_at_ms':self.start+FOUR_HOURS+500}]})
                self.offline(2,take_touch=True)
                caught,_,_=advance(state,self.venue,effective_protection=previous)
                self.assertEqual(caught.exit_cause,expected)
                self.assertEqual(state.get('protection_catchup'),[])

