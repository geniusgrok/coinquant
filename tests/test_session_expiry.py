"""Owned expiry replay and native amendment boundaries, without exchange access."""
import tempfile
from decimal import Decimal as D
from unittest import TestCase
from unittest.mock import Mock, patch

from coinquant.campaign import Campaign
from coinquant.config import Config
from coinquant.lifecycle import Lifecycle
from coinquant.opportunities import Opportunity
from coinquant.session import cycle, run
from coinquant.state import State
from coinquant.types import Unknown
from tests.session_venue import Venue

SCOPE='binance:BTCUSDT:live:123'
INTERVAL=14400000


class SessionExpiryTests(TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.directory=self.tmp.name
        self.risk=patch('coinquant.campaign.PRIMARY_RISK','6');self.risk.start()
        self.venue=Venue();self.venue.seed(self.directory)

    def tearDown(self):
        self.risk.stop();self.tmp.cleanup()

    def session(self, *, execute=True, seconds=1):
        return run(Config('123',self.directory,seconds,1),self.venue,execute=execute,
                   monotonic=self.venue.monotonic,wait=self.venue.wait)

    def expiry_replay(self, *, offline_bars=1):
        """The stop was installed, but ownership checkpointing was interrupted."""
        with State(self.directory,SCOPE) as state:
            model=Campaign.restore(state.get('linear_campaign'))
            start=model.last
            model.model.active=Opportunity(start,1,D(95000),D(600000),start+INTERVAL,
                                           D(100000),D(5000),D(100000))
            model.model.close=D(100000)
            model.model.lows.extend([D(125000)]*84)
            before=model.checkpoint()
            state.set('linear_campaign',before)
        self.assertEqual(self.session()['cleanup'],'verified')
        with State(self.directory,SCOPE) as state:
            state.set('linear_campaign',before)
        bars=[dict(time=start,high='140000',low='115000',close='135000')]
        if offline_bars>1:
            bars.append(dict(time=start+INTERVAL,high='140000',low='120000',close='136000'))
        end=start+offline_bars*INTERVAL
        self.venue.now=end+1000;self.venue.mark=D(bars[-1]['close'])
        def completed(start=None,on_page=None):
            remaining=[bar for bar in bars if bar['time']+INTERVAL>start]
            if on_page:
                for bar in remaining:on_page([bar])
            return dict(interval_ms=INTERVAL,complete_through=end,candles=remaining)
        self.venue.completed_market=completed
        return before

    def candidate(self, stop, *, fill=None):
        self.assertEqual(self.session()['cleanup'],'verified')
        with State(self.directory,SCOPE) as state:
            model=Campaign.restore(state.get('linear_campaign'))
            active=model.model.active
            model.model.active=Opportunity(active.identity,1,D(stop),D(600000),None,
                                           active.anchor,active.risk,D(140000),True)
            model.entry_fill=D(fill) if fill is not None else self.venue.entry
            state.set('linear_campaign',model.checkpoint())

    def reductions(self):
        return [p for _,path,p in self.venue.sent
                if path.endswith('/order') and p.get('reduceOnly')=='true']

    def mark_at_ownership_readback(self, mark):
        snapshot=self.venue.snapshot
        reads=0
        def read(uid):
            nonlocal reads
            reads+=1
            if reads==2:
                self.venue.mark=D(mark)
                self.venue.wait(.001)
            return snapshot(uid)
        self.venue.snapshot=read

    def test_read_only_restores_owner_before_checkpointing_expiry(self):
        self.expiry_replay()
        writes=len(self.venue.sent)
        readonly=self.session(execute=False)
        self.assertEqual(readonly['status'],'read_only',readonly)
        self.assertEqual(readonly['model_preview']['action'],'hold')
        with State(self.directory,SCOPE) as state:
            model=Campaign.restore(state.get('linear_campaign'))
            self.assertTrue(model.model.active.extended)
            self.assertEqual(model.entry_fill,self.venue.entry)
            self.assertEqual(model.position_campaign,model.model.active.identity)
        self.assertEqual(len(self.venue.sent),writes)
        executed=self.session()
        self.assertEqual(executed['cleanup'],'verified',executed)
        self.assertGreater(self.venue.q,0)
        self.assertEqual(self.reductions(),[])

    def test_offline_candidate_stop_is_not_applied_to_later_offline_candles(self):
        self.expiry_replay(offline_bars=2)
        readonly=self.session(execute=False)
        self.assertEqual(readonly['model_preview']['action'],'hold',readonly)
        with State(self.directory,SCOPE) as state:
            model=Campaign.restore(state.get('linear_campaign'))
            self.assertTrue(model.model.active.extended)
            self.assertEqual(model.model.active.stop,D(125000))
            self.assertEqual(D(state.get('position_protection')['stop']),D(95000))
        executed=self.session()
        self.assertEqual(executed['cleanup'],'verified',executed)
        with State(self.directory,SCOPE) as state:
            protection=state.get('position_protection')
            # The historical trail remains 125000. Current observed-profit risk
            # can require a tighter native stop, which strategy maintenance must
            # retain rather than loosen back to that historical proposal.
            self.assertEqual(Campaign.restore(state.get('linear_campaign')).model.active.stop,D(125000))
            risk=state.get('holding_risk')
            self.assertEqual(risk['status'],'observed')
            self.assertEqual(D(protection['stop']),D(risk['native_stop']))
            # Observed profit does not replace the strategy trail with a tighter stop.
            self.assertEqual(D(protection['stop']),D(125000))
            self.assertGreater(D(risk['loss_ceiling_usdt']),0)

    def test_unknown_ownership_does_not_advance_read_only_checkpoint(self):
        before=self.expiry_replay()
        self.venue.fill(dict(side='BUY',reduceOnly=False,price=str(self.venue.mark),
                             orderId=900,executedQty='0'),D('.001'))
        self.venue.completed_market=Mock(side_effect=AssertionError('unknown ownership must stop replay'))
        writes=len(self.venue.sent)
        with State(self.directory,SCOPE) as state:
            with self.assertRaises(Unknown):cycle(self.venue,state,'123')
            self.assertEqual(state.get('linear_campaign'),before)
        self.venue.completed_market.assert_not_called()
        self.assertEqual(len(self.venue.sent),writes)

    def test_crossed_candidate_stop_closes_verified_position(self):
        self.candidate('100001')
        before=len(self.venue.algos)
        result=self.session()
        self.assertEqual(result['cleanup'],'verified',result)
        self.assertEqual(result['model_preview']['action'],'exit')
        self.assertEqual(self.venue.q,0)
        self.assertEqual(len(self.reductions()),1)
        self.assertEqual(len(self.venue.algos),before)
        with State(self.directory,SCOPE) as state:
            self.assertIsNone(state.get('session_replacement'))

    def test_mark_crossing_at_replacement_gate_still_closes(self):
        self.candidate('99000')
        original=self.venue.get
        def crossed(path,p=None):
            if path.endswith('/exchangeInfo'):self.venue.mark=D(98500)
            return original(path,p)
        self.venue.get=crossed
        result=self.session()
        self.assertEqual(result['cleanup'],'verified',result)
        self.assertEqual(self.venue.q,0)
        self.assertEqual(len(self.reductions()),1)

    def test_recovered_mark_can_install_candidate_after_fresh_reconciliation(self):
        self.candidate('100001')
        with State(self.directory,SCOPE) as state:
            snapshot=self.venue.snapshot('123')
            self.venue.mark=D(102000)
            engine=Lifecycle(self.venue,state,'123',authorized=True)
            result=engine.maintain(Campaign.restore(state.get('linear_campaign')),snapshot)
            self.assertGreater(D(result['quantity_btc']),0)
            self.assertEqual(D(state.get('position_protection')['stop']),self.venue.entry)
        self.assertEqual(self.reductions(),[])

    def test_mark_rebounding_during_ownership_readback_installs_stop_without_exit(self):
        self.candidate('100001')
        with State(self.directory,SCOPE) as state:
            snapshot=self.venue.snapshot('123')
            self.mark_at_ownership_readback('102000')
            engine=Lifecycle(self.venue,state,'123',authorized=True)
            result=engine.maintain(Campaign.restore(state.get('linear_campaign')),snapshot)
            self.assertGreater(D(result['quantity_btc']),0)
            self.assertEqual(D(result['mark_price']),D(102000))
            self.assertEqual(D(state.get('position_protection')['stop']),self.venue.entry)
            self.assertIsNone(state.get('position_exit'))
            self.assertIsNone(state.get('session_replacement'))
        self.assertEqual(self.reductions(),[])

    def test_mark_still_crossed_at_ownership_readback_closes(self):
        self.candidate('100001')
        with State(self.directory,SCOPE) as state:
            snapshot=self.venue.snapshot('123')
            self.mark_at_ownership_readback('99000')
            engine=Lifecycle(self.venue,state,'123',authorized=True)
            result=engine.maintain(Campaign.restore(state.get('linear_campaign')),snapshot)
            self.assertEqual(D(result['quantity_btc']),0)
        self.assertEqual(len(self.reductions()),1)

    def test_unconditional_owned_exit_still_closes_after_mark_rebounds(self):
        self.candidate('100001')
        self.mark_at_ownership_readback('102000')
        with State(self.directory,SCOPE) as state:
            result=Lifecycle(self.venue,state,'123',authorized=True).close_owned()
            self.assertEqual(D(result['quantity_btc']),0)
        self.assertEqual(len(self.reductions()),1)

    def test_crossed_stop_does_not_reduce_an_external_fill_after_decision(self):
        self.candidate('100001')
        with State(self.directory,SCOPE) as state:
            snapshot=self.venue.snapshot('123')
            model=Campaign.restore(state.get('linear_campaign'))
            self.venue.fill(dict(side='BUY',reduceOnly=False,price=str(self.venue.mark),
                                 orderId=900,executedQty='0'),D('.001'))
            engine=Lifecycle(self.venue,state,'123',authorized=True)
            with self.assertRaises(Unknown):engine.maintain(model,snapshot)
        self.assertEqual(self.reductions(),[])

    def test_unknown_crossed_stop_reduction_is_not_resent(self):
        self.candidate('100001')
        original=self.venue.send
        def lost(method,path,p):
            if p.get('reduceOnly')=='true':
                self.venue.sent.append((method,path,p))
                raise TimeoutError()
            return original(method,path,p)
        self.venue.send=lost
        first=self.session(seconds=2)
        second=self.session(seconds=2)
        self.assertEqual(first['cleanup'],'unresolved',first)
        self.assertEqual(second['cleanup'],'unresolved',second)
        self.assertGreater(self.venue.q,0)
        self.assertEqual(len(self.reductions()),1)

    def test_extended_native_stop_rounds_up_to_actual_fill(self):
        self.candidate('100100.05',fill='100100.05')
        self.venue.mark=D(102000)
        with State(self.directory,SCOPE) as state:
            engine=Lifecycle(self.venue,state,'123',authorized=True)
            engine.maintain(Campaign.restore(state.get('linear_campaign')),self.venue.snapshot('123'))
            protection=state.get('position_protection')
            self.assertEqual(D(protection['stop']),D('100100.1'))
            accepted=protection['accepted_at_ms']
            self.venue.wait(1)
            engine.maintain(Campaign.restore(state.get('linear_campaign')),self.venue.snapshot('123'))
            self.assertEqual(state.get('position_protection')['accepted_at_ms'],accepted)

    def test_terminal_partial_crossed_stop_reduction_resumes_owned_residual(self):
        self.candidate('100001')
        self.venue.partial_exit=True
        original=self.venue.wait
        def wait(seconds):
            original(seconds);self.venue.partial_exit=False
        self.venue.wait=wait
        result=self.session(seconds=2)
        self.assertEqual(result['cleanup'],'verified',result)
        self.assertEqual(self.venue.q,0)
        reductions=self.reductions()
        self.assertEqual(len(reductions),2)
        self.assertEqual(D(reductions[1]['quantity']),D(reductions[0]['quantity'])/2)
        self.assertNotEqual(reductions[0]['newClientOrderId'],reductions[1]['newClientOrderId'])
