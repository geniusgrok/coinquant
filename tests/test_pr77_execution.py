"""Native lifecycle regressions at the final write and crash boundaries."""
from copy import deepcopy
from decimal import Decimal as D
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from coinquant import binance_safety as safety
from coinquant.campaign import Campaign
from coinquant.config import Config
from coinquant.lifecycle import Lifecycle
from coinquant.opportunities import Opportunity
from coinquant.ownership import reconcile
from coinquant.session import run
from coinquant.state import State
from coinquant.types import Unknown
from tests.session_venue import Venue

SCOPE='binance:BTCUSDT:live:123'


class ExecutionBoundaries(TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.directory=self.tmp.name
        self.venue=Venue();self.venue.seed(self.directory)

    def session(self, seconds=1):
        return run(Config('123',self.directory,seconds,1),self.venue,execute=True,
                   monotonic=self.venue.monotonic,wait=self.venue.wait)

    def reductions(self):
        return [p for _,_,p in self.venue.sent if p.get('reduceOnly')=='true']

    def zero_reduction(self, method, path, payload):
        if payload.get('reduceOnly')!='true':
            return Venue.send(self.venue,method,path,payload)
        self.venue.now+=1
        self.venue.sent.append((method,path,deepcopy(payload)))
        order=dict(payload,orderId=len(self.venue.orders)+1,clientOrderId=payload['newClientOrderId'],
                   reduceOnly=True,origQty=payload['quantity'],executedQty='0',status='EXPIRED')
        self.venue.orders[payload['newClientOrderId']]=order
        return deepcopy(order)

    def test_final_entry_book_read_cannot_extend_entry_deadline(self):
        original=self.venue.get;books=[]
        def delayed(path,parameters=None):
            result=original(path,parameters)
            if path.endswith('/depth'):
                books.append(result)
                if len(books)==2:self.venue.wait(2)
            return result
        self.venue.get=delayed
        result=self.session()
        self.assertEqual(len(books),2)
        self.assertEqual(self.venue.sent,[])
        self.assertEqual(result['cleanup'],'verified')
        self.assertEqual(result['risk_limits'],dict(max_stop_loss_fraction='.10',stop_slippage_fraction='.01'))

    def test_entry_and_topup_keep_funded_limit_when_fresh_band_changes(self):
        self.venue.fraction=D('.5')
        original=self.venue.get;books=[]
        def changing(path,parameters=None):
            result=original(path,parameters)
            if path.endswith('/depth'):
                result['asks'][0][1]=str(101+len(books))
                if len(books)%2:
                    result['bids'][0][0]=str(self.venue.mark+D(9))
                    result['asks'][0][0]=str(self.venue.mark+D(10))
                books.append(result)
            return result
        self.venue.get=changing
        report=self.session()
        self.assertEqual(report['cleanup'],'verified')
        self.assertGreater(self.venue.q,0)
        self.assertEqual(report['entry_timing']['quote_observation']['visible_limit_depth_btc'],'101')
        before=len(self.venue.orders);quantity=self.venue.q
        with State(self.directory,SCOPE) as state:
            model=Campaign.restore(state.get('linear_campaign'));snapshot=self.venue.snapshot('123')
            ownership=reconcile(state,self.venue,model,snapshot)
            engine=Lifecycle(self.venue,state,'123',authorized=True,session=state.get('entry_fill')['session'])
            engine.risk_audit_ok=True;engine.reconciled=(snapshot,0,ownership)
            result=engine.top_up(model,snapshot)
        self.assertEqual(len(self.venue.orders),before+1)
        self.assertGreater(self.venue.q,quantity)
        self.assertTrue(result['native_full_position_protected'])
        self.assertEqual(len(books),4)
        self.assertTrue(all(D(order['price'])==D('100100') for order in self.venue.orders.values()))

    def test_entry_rejects_changed_depth_below_fresh_participation_limit(self):
        original=self.venue.get;books=[]
        def depleted(path,parameters=None):
            result=original(path,parameters)
            if path.endswith('/depth'):
                books.append(result)
                if len(books)==2:result['asks'][0][1]='.001'
            return result
        self.venue.get=depleted
        result=self.session()
        self.assertEqual(len(books),2)
        self.assertEqual(self.venue.sent,[])
        self.assertEqual(self.venue.q,0)
        self.assertEqual(result['cleanup'],'verified')

    def test_final_topup_book_read_cannot_extend_entry_deadline(self):
        self.venue.fraction=D('.5')
        self.assertEqual(self.session()['cleanup'],'verified')
        original=self.venue.get;books=[];before=len(self.venue.orders)
        def delayed(path,parameters=None):
            result=original(path,parameters)
            if path.endswith('/depth'):
                books.append(result)
                if len(books)==2:self.venue.wait(2)
            return result
        self.venue.get=delayed
        with State(self.directory,SCOPE) as state:
            model=Campaign.restore(state.get('linear_campaign'))
            snapshot=self.venue.snapshot('123')
            ownership=reconcile(state,self.venue,model,snapshot)
            deadline=self.venue.monotonic()+1
            engine=Lifecycle(self.venue,state,'123',authorized=True,
                             session=state.get('entry_fill')['session'],may_enter=lambda:self.venue.monotonic()<deadline)
            engine.risk_audit_ok=True;engine.reconciled=(snapshot,0,ownership)
            result=engine.top_up(model,snapshot)
        self.assertEqual(len(books),2)
        self.assertEqual(len(self.venue.orders),before)
        self.assertTrue(result['native_full_position_protected'])

    def test_checkpoint_string_stop_rechecks_live_mark(self):
        self.assertEqual(self.session()['cleanup'],'verified')
        self.venue.mark=D(101000);quantity=self.venue.q
        with State(self.directory,SCOPE) as state:
            result=Lifecycle(self.venue,state,'123',authorized=True).close_owned(stop='100000')
            self.assertIsNone(result)
        self.assertEqual(self.venue.q,quantity)
        self.assertEqual(self.reductions(),[])

    def test_native_stop_fill_during_final_book_read_blocks_topup(self):
        self.venue.fraction=D('.5')
        self.assertEqual(self.session()['cleanup'],'verified')
        entries=len(self.venue.orders);original=self.venue.get;books=[]
        def stopped(path,parameters=None):
            result=original(path,parameters)
            if path.endswith('/depth'):
                books.append(result)
                if len(books)==2:
                    stop=next(a for a in self.venue.algos.values()
                              if a['orderType']=='STOP_MARKET' and a['algoStatus']=='NEW')
                    child=dict(symbol='BTCUSDT',positionSide='BOTH',side='SELL',type='MARKET',
                               orderId=900001,clientOrderId='native-child',reduceOnly=True,
                               origQty=str(self.venue.q),executedQty='0',status='FILLED')
                    self.venue.orders['native-child']=child
                    self.venue.fill(child,self.venue.q)
                    stop.update(algoStatus='FINISHED',actualOrderId=900001)
            return result
        self.venue.get=stopped
        with State(self.directory,SCOPE) as state:
            model=Campaign.restore(state.get('linear_campaign'));snapshot=self.venue.snapshot('123')
            ownership=reconcile(state,self.venue,model,snapshot)
            engine=Lifecycle(self.venue,state,'123',authorized=True,session=state.get('entry_fill')['session'])
            engine.risk_audit_ok=True;engine.reconciled=(snapshot,0,ownership)
            with self.assertRaisesRegex(Unknown,'fill ownership changed'):
                engine.top_up(model,snapshot)
        self.assertEqual(len(books),2)
        self.assertEqual(len(self.venue.orders),entries+1)
        self.assertEqual(self.venue.q,0)

    def test_terminal_zero_fill_retry_keeps_stop_at_final_account_gate(self):
        self.assertEqual(self.session()['cleanup'],'verified')
        self.venue.mark=D(99000);quantity=self.venue.q
        self.venue.send=self.zero_reduction
        with State(self.directory,SCOPE) as state:
            engine=Lifecycle(self.venue,state,'123',authorized=True)
            with self.assertRaisesRegex(Unknown,'no terminal fill progress'):
                engine.close_owned(stop='100000')
            self.venue.send=lambda *args:Venue.send(self.venue,*args)
            original=safety.reduce_existing
            def rebound(*args,**kwargs):
                self.venue.mark=D(101000)
                return original(*args,**kwargs)
            with patch('coinquant.lifecycle.safety.reduce_existing',side_effect=rebound):
                self.assertIsNone(engine.close_owned(stop='100000'))
            self.assertIsNone(state.get('position_exit'))
        self.assertEqual(self.venue.q,quantity)
        self.assertEqual(len(self.reductions()),1)

    def test_zero_fill_retry_budget_is_shared_with_cleanup_and_resets_next_session(self):
        self.assertEqual(self.session()['cleanup'],'verified')
        with State(self.directory,SCOPE) as state:
            model=Campaign.restore(state.get('linear_campaign'));model.model.active=None
            state.set('linear_campaign',model.checkpoint())
        self.venue.send=self.zero_reduction
        result=self.session(seconds=3)
        self.assertEqual(len(self.reductions()),2)
        self.assertEqual(result['cleanup'],'unresolved')
        next_result=self.session(seconds=2)
        self.assertEqual(len(self.reductions()),3)
        self.assertEqual(next_result['cleanup'],'unresolved')
        self.assertTrue(all(p['newClientOrderId']!=q['newClientOrderId']
                            for i,p in enumerate(self.reductions()) for q in self.reductions()[i+1:]))

    def test_restarted_owned_fill_is_protected_before_full_history_audit(self):
        with State(self.directory,SCOPE) as state:
            model=Campaign.restore(state.get('linear_campaign'))
            engine=Lifecycle(self.venue,state,'123',authorized=True)
            engine.risk_audit_ok=True
            with patch.object(engine,'protect_entry',side_effect=SystemExit('process stopped before protection')):
                with self.assertRaises(SystemExit):engine.enter(model,self.venue.snapshot('123'))
            entry=state.get('entry_plan')['id']
            self.assertGreater(self.venue.q,0)
            self.assertEqual(self.venue.algos,{})
        events=[];original_send=self.venue.send
        def send(method,path,payload):
            if payload.get('type')=='STOP_MARKET':events.append('stop')
            return original_send(method,path,payload)
        def audit(*args,**kwargs):
            events.append('audit')
            return reconcile(*args,**kwargs)
        self.venue.send=send
        with State(self.directory,SCOPE) as state,patch('coinquant.ownership.reconcile',side_effect=audit):
            engine=Lifecycle(self.venue,state,'123',authorized=True)
            result=engine.recover_exposure(engine.settle())
            self.assertTrue(result['native_full_position_protected'])
            self.assertIsNone(state.get('entry_plan'))
        self.assertLess(events.index('stop'),events.index('audit'))
        self.assertEqual(list(self.venue.orders),[entry])

    def test_protection_amendment_preserves_original_buffer(self):
        self.assertEqual(self.session()['cleanup'],'verified')
        self.venue.mark=D(102000)
        with State(self.directory,SCOPE) as state:
            original=state.get('position_protection')['buffer_distance']
            model=Campaign.restore(state.get('linear_campaign'));active=model.active
            model.model.active=Opportunity(active.identity,1,D(99000),active.take,active.expires,
                                           active.anchor,active.risk,active.peak,active.extended)
            engine=Lifecycle(self.venue,state,'123',authorized=True)
            engine.maintain(model,self.venue.snapshot('123'))
            self.assertEqual(state.get('position_protection')['buffer_distance'],original)

    def test_topup_after_mark_decline_keeps_buffer_without_recovery_transfer(self):
        self.venue.fraction=D('.5')
        self.assertEqual(self.session()['cleanup'],'verified')
        quantity=self.venue.q;transfers=len(self.venue.margin_history)
        self.venue.fraction=D(1);self.venue.mark-=100
        with State(self.directory,SCOPE) as state:
            protection=state.get('position_protection');original=protection['buffer_distance']
            model=Campaign.restore(state.get('linear_campaign'));snapshot=self.venue.snapshot('123')
            ownership=reconcile(state,self.venue,model,snapshot)
            engine=Lifecycle(self.venue,state,'123',authorized=True,session=state.get('entry_fill')['session'])
            engine.risk_audit_ok=True;engine.reconciled=(snapshot,0,ownership)
            result=engine.top_up(model,snapshot)
            self.assertGreater(self.venue.q,quantity)
            self.assertTrue(result['native_full_position_protected'])
            self.assertEqual(state.get('position_protection')['buffer_distance'],original)
            self.assertGreaterEqual(engine._gap(result,protection['stop']),D(original))
        # Fund the add once before entry; do not fill the current cap afterward.
        self.assertEqual(len(self.venue.margin_history),transfers+1)
        self.assertEqual(self.reductions(),[])

    def test_triggered_terminal_protective_partial_can_close_entry_residual(self):
        with State(self.directory,SCOPE) as state:
            model=Campaign.restore(state.get('linear_campaign'))
            engine=Lifecycle(self.venue,state,'123',authorized=True);engine.risk_audit_ok=True
            # Lose power before the new atomic protection/entry-plan commit;
            # native protection already exists but the entry plan remains live.
            with patch.object(engine,'_save_protection',side_effect=SystemExit('stopped before protected entry commit')):
                with self.assertRaises(SystemExit):engine.enter(model,self.venue.snapshot('123'))
            self.assertIsNotNone(state.get('entry_plan'))
        stop=next(a for a in self.venue.algos.values()
                  if a['orderType']=='STOP_MARKET' and a['algoStatus']=='NEW')
        child=dict(symbol='BTCUSDT',positionSide='BOTH',side='SELL',type='MARKET',
                   orderId=900001,clientOrderId='native-child',reduceOnly=True,
                   origQty=str(self.venue.q),executedQty='0',status='EXPIRED')
        self.venue.orders['native-child']=child
        self.venue.fill(child,D('.001'))
        stop.update(algoStatus='TRIGGERED',actualOrderId=900001)
        with State(self.directory,SCOPE) as state:
            engine=Lifecycle(self.venue,state,'123',authorized=True)
            result=engine.recover_exposure(engine.settle())
        self.assertEqual(D(result['quantity_btc']),0)
        self.assertEqual(len(self.reductions()),1)

    def test_margin_recovery_does_not_ratchet_buffer_and_force_next_exit(self):
        self.venue.fraction=D('.5')
        self.assertEqual(self.session()['cleanup'],'verified')
        with State(self.directory,SCOPE) as state:
            original=state.get('position_protection')['buffer_distance']
            self.venue.margin-=D(5);self.venue.wallet-=D(5)
            engine=Lifecycle(self.venue,state,'123',authorized=True)
            engine.ensure_liquidation_buffer(self.venue.snapshot('123'))
            self.assertEqual(state.get('position_protection')['buffer_distance'],original)
            self.venue.margin-=D(2);self.venue.wallet-=D(2)
            result=engine.ensure_liquidation_buffer(self.venue.snapshot('123'))
        self.assertGreater(D(result['quantity_btc']),0)
        self.assertEqual(self.reductions(),[])

    def test_margin_recovery_rounding_stays_inside_collateral_limit(self):
        self.venue.fraction=D('.5')
        self.venue.wallet=D('1000.00000003')
        self.assertEqual(self.session()['cleanup'],'verified')
        self.venue.margin-=D(5);self.venue.wallet-=D(5)
        with State(self.directory,SCOPE) as state:
            engine=Lifecycle(self.venue,state,'123',authorized=True)
            result=engine.ensure_liquidation_buffer(self.venue.snapshot('123'))
        cap=min(D(result['wallet_usdt']),D(result['equity_usdt']))*D('.25')
        self.assertGreater(D(result['quantity_btc']),0)
        self.assertLessEqual(D(result['isolated_wallet_usdt']),cap)

    def test_small_buffer_erosion_is_not_ignored_as_mark_rises(self):
        self.assertEqual(self.session()['cleanup'],'verified')
        self.venue.mark=D(105000);self.venue.margin-=D('.01');self.venue.wallet-=D('.01')
        before=len(self.venue.margin_history)
        with State(self.directory,SCOPE) as state:
            engine=Lifecycle(self.venue,state,'123',authorized=True)
            original=D(state.get('position_protection')['buffer_distance'])
            result=engine.ensure_liquidation_buffer(self.venue.snapshot('123'))
            self.assertGreaterEqual(engine._gap(result,state.get('position_protection')['stop']),original)
        self.assertEqual(len(self.venue.margin_history),before+1)

    def test_reduction_action_records_verified_position_for_full_slice_fill(self):
        self.assertEqual(self.session()['cleanup'],'verified')
        with State(self.directory,SCOPE) as state:
            engine=Lifecycle(self.venue,state,'123',authorized=True)
            quantity=self.venue.q
            rules=deepcopy(self.venue.rules)
            next(f for f in rules['filters'] if f['filterType']=='MARKET_LOT_SIZE')['maxQty']='.001'
            with self.assertRaisesRegex(Unknown,'partial exit remains'):
                engine.close_owned(rules)
            action=next(a for a in engine.actions if a['path']=='/fapi/v1/order')
        self.assertEqual(D(action['position_before_btc']),quantity)
        order=self.venue.orders[action['id']]
        self.assertEqual(order['status'],'FILLED')
        self.assertLess(D(order['executedQty']),D(action['position_before_btc']))

