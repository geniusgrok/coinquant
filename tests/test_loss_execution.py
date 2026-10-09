"""Native-shape crash/restart cases that must not create avoidable exits."""
import json
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal as D
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from coinquant import binance_safety as safety
from coinquant.campaign import Campaign
from coinquant.config import Config
from coinquant.lifecycle import Lifecycle
from coinquant.opportunities import FOUR_HOURS
from coinquant.ownership import reconcile
from coinquant.session import cycle, run
from coinquant.state import State, client_id
from coinquant.types import Blocked, Unknown
from tests.session_venue import Venue

SCOPE='binance:BTCUSDT:live:123'


class PowerLoss(BaseException):
    """A process loss, without run() performing graceful cleanup."""


class LossExecutionTests(TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.directory=self.tmp.name
        self.venue=Venue();self.venue.seed(self.directory)
        with State(self.directory,SCOPE) as state:
            model=Campaign.restore(state.get('linear_campaign'))
            self.start=model.last
            model.model.active=replace(model.model.active,expires=self.start+42*FOUR_HOURS)
            state.set('linear_campaign',model.checkpoint())

    def session(self, *, execute=True, seconds=1):
        return run(Config('123',self.directory,seconds,1),self.venue,execute=execute,
                   monotonic=self.venue.monotonic,wait=self.venue.wait)

    def entry_cycle(self,state):
        self.venue.begin_cycle(120)
        return cycle(self.venue,state,'123',execute=True,session=int(self.venue.clock()*1000))

    def reductions(self):
        return [p for _,path,p in self.venue.sent
                if path.endswith('/order') and p.get('reduceOnly')=='true']

    def guard_crash(self, *, after_journal):
        send=self.venue.send
        with State(self.directory,SCOPE) as state:
            save=state.set
            def interrupted_send(method,path,payload):
                result=send(method,path,payload)
                if not after_journal and method=='DELETE' and path.endswith('/algoOrder'):
                    raise PowerLoss('old guard retired before the cancellation was checkpointed')
                return result
            def interrupted_save(key,value):
                save(key,value)
                if after_journal and key=='binance_protection_replacement' and value.get('done'):
                    raise PowerLoss('replacement committed before the entry protection record')
            with patch.object(self.venue,'send',new=interrupted_send),patch.object(state,'set',new=interrupted_save):
                with self.assertRaises(PowerLoss):self.entry_cycle(state)
            plan=state.get('entry_plan')
            self.assertIsNotNone(plan.get('guard_epoch'))
            self.assertIsNone(state.get('position_protection'))
            self.assertEqual(state.get('binance_protection_replacement')['done'],after_journal)
            expected={client_id(SCOPE,plan['epoch'],kind) for kind in ('STOP_MARKET','TAKE_PROFIT_MARKET')}
            self.assertTrue(all(self.venue.algos[identity]['algoStatus']=='NEW' for identity in expected))
        quantity=self.venue.q
        self.assertGreater(quantity,0)
        posts=len([1 for method,path,_ in self.venue.sent if method=='POST' and path.endswith('/algoOrder')])
        margins=len(self.venue.margin_history)
        resumed=self.session()
        self.assertEqual(resumed['cleanup'],'verified',resumed)
        self.assertEqual(self.venue.q,quantity)
        self.assertEqual(self.reductions(),[])
        self.assertEqual(len(self.venue.margin_history),margins)
        self.assertEqual(len([1 for method,path,_ in self.venue.sent if method=='POST' and path.endswith('/algoOrder')]),posts)
        self.assertEqual({identity for identity,order in self.venue.algos.items() if order['algoStatus']=='NEW'},expected)
        with State(self.directory,SCOPE) as state:
            self.assertIsNone(state.get('entry_plan'))
            self.assertTrue(state.get('binance_protection_replacement')['done'])

    def test_restart_after_first_guard_retirement_resumes_original_replacement(self):
        self.guard_crash(after_journal=False)

    def test_restart_after_guard_replacement_commit_preserves_live_successor(self):
        self.guard_crash(after_journal=True)

    def delayed_guard_recovery(self, *, readonly_first):
        with State(self.directory,SCOPE) as state:
            save=state.set
            def interrupted(key,value):
                save(key,value)
                if key=='binance_protection_replacement' and value.get('done'):
                    raise PowerLoss('formal pair confirmed before its position record')
            with patch.object(state,'set',new=interrupted):
                with self.assertRaises(PowerLoss):self.entry_cycle(state)
            plan=state.get('entry_plan')
            self.assertIsNone(state.get('position_protection'))
            self.assertTrue(state.get('binance_protection_replacement')['done'])
            formal={client_id(SCOPE,plan['epoch'],kind)
                    for kind in ('STOP_MARKET','TAKE_PROFIT_MARKET')}
            self.assertTrue(all(self.venue.algos[identity]['algoStatus']=='NEW' for identity in formal))
        bars=[dict(time=self.start+i*FOUR_HOURS,high='101000',low='99000',close='100000')
              for i in range(3)]
        bars[1]['high']='111000'  # A whole later bar touches the already-live formal take.
        end=self.start+3*FOUR_HOURS
        self.venue.now=end+1000
        def completed(start=None,on_page=None):
            remaining=[bar for bar in bars if bar['time']+FOUR_HOURS>start]
            if on_page:on_page(remaining)
            return dict(interval_ms=FOUR_HOURS,complete_through=end,candles=remaining)
        self.venue.completed_market=completed
        quantity=self.venue.q;writes=len(self.venue.sent);fills=len(self.venue.trades)
        if readonly_first:
            result=self.session(execute=False)
            self.assertEqual(result['model_preview']['action'],'exit',result)
            self.assertEqual(self.venue.q,quantity)
            self.assertEqual(len(self.venue.sent),writes)
            self.assertEqual(len(self.venue.trades),fills)
            with State(self.directory,SCOPE) as state:
                model=Campaign.restore(state.get('linear_campaign'))
                self.assertEqual(model.last,end)
                self.assertEqual(model.exit_cause,'take')
        restarted=self.venue.now
        result=self.session()
        self.assertEqual(result['cleanup'],'verified',result)
        self.assertEqual(result['model_preview']['action'],'exit',result)
        self.assertEqual(self.venue.q,0)
        self.assertEqual(len(self.reductions()),1)
        self.assertTrue(all(trade['time']>=restarted for trade in self.venue.trades[fills:]))

    def test_delayed_restart_replays_formal_pair_confirmed_before_position_commit(self):
        self.delayed_guard_recovery(readonly_first=False)

    def test_readonly_first_preserves_formal_pair_history_after_entry_crash(self):
        self.delayed_guard_recovery(readonly_first=True)

    def test_entry_protection_commit_also_clears_its_completed_entry_plan(self):
        save=Lifecycle._save_protection
        def interrupted(engine,payload,snapshot,**kwargs):
            save(engine,payload,snapshot,**kwargs)
            if kwargs.get('clear_entry_plan'):
                raise PowerLoss('immediately after entry protection commit')
        with State(self.directory,SCOPE) as state,patch.object(Lifecycle,'_save_protection',new=interrupted):
            with self.assertRaises(PowerLoss):self.entry_cycle(state)
            self.assertIsNotNone(state.get('position_protection'))
            self.assertIsNone(state.get('entry_plan'))
        quantity=self.venue.q
        resumed=self.session()
        self.assertEqual(resumed['cleanup'],'verified',resumed)
        self.assertEqual(self.venue.q,quantity)
        self.assertEqual(self.reductions(),[])

    def test_legacy_stranded_entry_plan_cannot_retimestamp_the_same_live_pair(self):
        with State(self.directory,SCOPE) as state:
            model=Campaign.restore(state.get('linear_campaign'))
            model.model.active=replace(model.model.active,stop=D(97000))
            state.set('linear_campaign',model.checkpoint())
        save=Lifecycle._save_protection
        def legacy_commit(engine,payload,snapshot,**kwargs):
            # Reproduce the previous released sequence: save the pair, then lose
            # power before the separate clearing of the entry plan.
            save(engine,payload,snapshot)
            raise PowerLoss('legacy pair commit without entry-plan clearing')
        with State(self.directory,SCOPE) as state,patch.object(Lifecycle,'_save_protection',new=legacy_commit):
            with self.assertRaises(PowerLoss):self.entry_cycle(state)
            previous=state.get('position_protection')
            self.assertIsNone(state.get('entry_plan').get('guard_epoch'))
        quantity=self.venue.q
        self.venue.wait(3*FOUR_HOURS/1000)
        def unavailable(**kwargs):raise Unknown('history unavailable after native recovery')
        self.venue.completed_market=unavailable
        resumed=self.session()
        self.assertEqual(resumed['status'],'unknown',resumed)
        self.assertEqual(resumed['cleanup'],'verified',resumed)
        self.assertEqual(self.venue.q,quantity)
        self.assertEqual(self.reductions(),[])
        with State(self.directory,SCOPE) as state:
            current=state.get('position_protection')
            self.assertEqual(current['epoch'],previous['epoch'])
            self.assertEqual(current['accepted_at_ms'],previous['accepted_at_ms'])
            self.assertIsNone(state.get('entry_plan'))

    def test_rejected_amendment_does_not_end_the_old_pairs_offline_history(self):
        self.assertEqual(self.session()['cleanup'],'verified')
        for rule in self.venue.rules['filters']:
            if rule['filterType']=='PRICE_FILTER':rule['tickSize']='0.01'
        self.venue.mark=D('110000.08')
        refused=self.session()
        self.assertTrue(refused['protection_replacement_pending'],refused)
        self.assertGreater(self.venue.q,0)
        with State(self.directory,SCOPE) as state:
            current=state.get('position_protection')
            self.assertEqual(D(current['take']),D('110000.1'))
            request=state.get('session_replacement')
            self.assertEqual(D(request['take']),D('110000.01'))
        bars=[dict(time=self.start+i*FOUR_HOURS,high='109500',low='108000',close='109000')
              for i in range(3)]
        bars[1]['high']='111000'  # Old take is active; this is trade price, not mark.
        end=self.start+3*FOUR_HOURS
        self.venue.now=end+1000;self.venue.mark=D('109000')
        def completed(start=None,on_page=None):
            remaining=[bar for bar in bars if bar['time']+FOUR_HOURS>start]
            if on_page:on_page(remaining)
            return dict(interval_ms=FOUR_HOURS,complete_through=end,candles=remaining)
        self.venue.completed_market=completed
        restarted=self.venue.now;fills=len(self.venue.trades)
        result=self.session()
        self.assertEqual(result['cleanup'],'verified',result)
        self.assertEqual(result['model_preview']['action'],'exit',result)
        self.assertEqual(self.venue.q,0)
        self.assertEqual(len(self.reductions()),1)
        self.assertTrue(all(trade['time']>=restarted for trade in self.venue.trades[fills:]))

    def close_without_cleanup(self,state):
        self.venue.begin_cycle(120)
        engine=Lifecycle(self.venue,state,'123',authorized=True)
        owned=engine.recover_exposure(engine.settle())
        flat=safety.reduce_existing(self.venue,state,engine.send,'123',engine.epoch(),
            str(abs(D(owned['quantity_btc']))),instrument=self.venue.rules,authorized=True,
            expected_owner=dict(owned),expected_direction=1)
        self.assertEqual(D(flat['quantity_btc']),0)
        self.assertTrue(flat['open_algos'])
        return engine,flat

    def test_external_reopen_after_owned_flat_readback_keeps_existing_protection(self):
        self.assertEqual(self.session()['cleanup'],'verified')
        with State(self.directory,SCOPE) as state:
            engine,flat=self.close_without_cleanup(state)
            protected={order['clientAlgoId'] for order in flat['open_algos']}
            # The position was truly flat when the owner's reduction returned.
            # Another client opens before cleanup can retire the old close-all pair.
            self.venue.fill(dict(side='BUY',reduceOnly=False,price=str(self.venue.mark),
                                 orderId=900,executedQty='0'),D('.001'))
            before=len(self.venue.sent)
            with self.assertRaises(Unknown):engine.cleanup_flat(flat)
            self.assertEqual(self.venue.q,D('.001'))
            self.assertFalse(any(method=='DELETE' for method,_,_ in self.venue.sent[before:]))
            self.assertTrue(all(self.venue.algos[identity]['algoStatus']=='NEW' for identity in protected))

    def test_freshly_verified_flat_cleanup_retires_only_the_owned_pair(self):
        self.assertEqual(self.session()['cleanup'],'verified')
        with State(self.directory,SCOPE) as state:
            engine,flat=self.close_without_cleanup(state)
            expected={order['clientAlgoId'] for order in flat['open_algos']}
            before=len(self.venue.sent)
            result=engine.cleanup_flat(flat)
            self.assertEqual(D(result['quantity_btc']),0)
            self.assertEqual(result['open_algos'],[])
            retired={payload['clientAlgoId'] for method,path,payload in self.venue.sent[before:]
                     if method=='DELETE' and path.endswith('/algoOrder')}
            self.assertEqual(retired,expected)

    def open_macro(self):
        with State(self.directory,SCOPE) as state:
            model=Campaign.restore(state.get('linear_campaign'))
            model.model.active=None
            model.daily_lows.extend([D(90000)]*10)
            state.set('linear_campaign',model.checkpoint())
        row=dict(missing_reason=None,latest_value='1',prior20_value='1.3',
                 latest_observation_date=datetime.fromtimestamp(self.venue.now/1000,timezone.utc).date().isoformat(),
                 latest_value_available_ms=self.venue.now-1000,
                 prior20_value_available_ms=self.venue.now-1000)
        self.venue.dfii10_snapshot=lambda:row
        opened=self.session()
        self.assertEqual(opened['cleanup'],'verified',opened)
        self.assertGreater(self.venue.q,0)
        with State(self.directory,SCOPE) as state:
            model=Campaign.restore(state.get('linear_campaign'))
            self.assertLess(model.position_campaign,0)
            return row,model.macro_opportunity

    def test_readonly_macro_false_then_true_preserves_the_owned_campaign(self):
        row,original=self.open_macro()
        quantity=self.venue.q;writes=len(self.venue.sent);fills=len(self.venue.trades)
        self.venue.dfii10_snapshot=lambda:dict(row,missing_reason='stale')
        preview=self.session(execute=False)
        self.assertEqual(preview['status'],'read_only',preview)
        self.assertEqual(preview['model_preview']['action'],'exit')
        self.assertEqual(len(self.venue.sent),writes)
        self.assertEqual(self.venue.q,quantity)
        with State(self.directory,SCOPE) as state:
            waiting=Campaign.restore(state.get('linear_campaign'))
            self.assertEqual(waiting.macro_opportunity,original)
            self.assertEqual(waiting.position_campaign,original.identity)
        self.venue.dfii10_snapshot=lambda:row
        resumed=self.session()
        self.assertEqual(resumed['cleanup'],'verified',resumed)
        self.assertEqual(resumed['model_preview']['action'],'hold',resumed)
        self.assertEqual(self.venue.q,quantity)
        self.assertEqual(len(self.venue.sent),writes)
        self.assertEqual(len(self.venue.trades),fills)
        with State(self.directory,SCOPE) as state:
            current=Campaign.restore(state.get('linear_campaign'))
            self.assertEqual(current.macro_opportunity,original)
            self.assertEqual(current.position_campaign,original.identity)

    def test_readonly_macro_false_still_exits_when_execution_remains_false(self):
        row,original=self.open_macro()
        self.venue.dfii10_snapshot=lambda:dict(row,missing_reason='stale')
        readonly=self.session(execute=False)
        self.assertEqual(readonly['model_preview']['action'],'exit',readonly)
        self.assertGreater(self.venue.q,0)
        result=self.session()
        self.assertEqual(result['cleanup'],'verified',result)
        self.assertEqual(result['model_preview']['action'],'exit',result)
        self.assertEqual(self.venue.q,0)
        self.assertEqual(len(self.reductions()),1)
        with State(self.directory,SCOPE) as state:
            model=Campaign.restore(state.get('linear_campaign'))
            self.assertIsNone(model.position_campaign)
            self.assertIsNone(model.exit_cause)

    def test_partial_native_take_during_replacement_finishes_exit_without_buyback(self):
        with State(self.directory,SCOPE) as state:
            model=Campaign.restore(state.get('linear_campaign'))
            model.model.active=replace(model.model.active,stop=D(97000))
            state.set('linear_campaign',model.checkpoint())
        maintain=Lifecycle.maintain;send=self.venue.send
        change={}
        def update_take(engine,model,snapshot):
            if not change:
                protection=engine.state.get('position_protection')
                change['old_take']=client_id(SCOPE,protection['epoch'],'TAKE_PROFIT_MARKET')
                model.model.active=replace(model.model.active,take=D(111000))
                engine.state.set('linear_campaign',model.checkpoint())
            return maintain(engine,model,snapshot)
        def fill_old_take(method,path,payload):
            result=send(method,path,payload)
            if change and not change.get('filled') and method=='DELETE' and path.endswith('/algoOrder'):
                change['filled']=True
                parent=self.venue.algos[change['old_take']]
                child=dict(symbol='BTCUSDT',positionSide='BOTH',side='SELL',type='MARKET',
                           orderId=900001,clientOrderId='native-take-child',reduceOnly=True,
                           origQty=str(self.venue.q),executedQty='0',status='EXPIRED')
                self.venue.orders['native-take-child']=child
                self.venue.mark=D('110001')
                self.venue.fill(child,D('.001'))
                parent.update(algoStatus='TRIGGERED',actualOrderId=900001)
                # Both prices occurred after the fresh entry observation. The
                # native take has started a close-all exit despite the rebound.
                self.venue.mark=D(100000)
            return result
        with patch.object(Lifecycle,'maintain',new=update_take),patch.object(self.venue,'send',new=fill_old_take):
            result=self.session(seconds=4)
        self.assertTrue(change.get('filled'))
        self.assertEqual(result['cleanup'],'verified',result)
        self.assertEqual(self.venue.q,0)
        self.assertEqual(len(self.reductions()),1)
        entries=[p for _,path,p in self.venue.sent if path.endswith('/order') and p.get('timeInForce')=='IOC']
        self.assertEqual(len(entries),1,'a started close-all exit must not buy back its executed slice')
        self.assertEqual(self.venue.algos[change['old_take']]['algoStatus'],'TRIGGERED')
        self.assertEqual(self.venue.orders['native-take-child']['executedQty'],'0.001')

    def test_partial_opening_ioc_still_adds_in_its_own_session(self):
        self.venue.fraction=D('.5')
        result=self.session(seconds=3)
        self.assertEqual(result['cleanup'],'verified',result)
        entries=[p for _,path,p in self.venue.sent if path.endswith('/order') and p.get('timeInForce')=='IOC']
        self.assertGreaterEqual(len(entries),2)
        first=self.venue.orders[entries[0]['newClientOrderId']]
        self.assertEqual(first['status'],'EXPIRED')
        self.assertGreater(self.venue.q,D(first['executedQty']))
        self.assertEqual(self.reductions(),[])
        self.assertTrue(result['actual']['native_full_position_protected'])

    def test_final_entry_book_after_next_close_blocks_the_old_model(self):
        boundary=self.start+FOUR_HOURS
        self.venue.now=boundary-1000
        original=self.venue.get;books=[]
        def next_bar(path,parameters=None):
            result=original(path,parameters)
            if path.endswith('/depth'):
                if len(books)==1:
                    # The exchange event is just ahead of the local clock and
                    # well inside the 15-second freshness allowance.
                    result['E']=boundary+1
                books.append(result)
            return result
        self.venue.get=next_bar
        result=self.session()
        self.assertEqual(len(books),2)
        self.assertEqual(books[0]['bids'],books[1]['bids'])
        self.assertEqual(books[0]['asks'],books[1]['asks'])
        self.assertGreaterEqual(books[1]['E'],boundary)
        self.assertEqual(self.venue.sent,[])
        self.assertEqual(self.venue.q,0)
        self.assertEqual(result['cleanup'],'verified',result)

    def test_final_topup_cursor_crossing_next_close_keeps_protection_and_allows_exit(self):
        boundary=self.start+FOUR_HOURS
        self.venue.now=boundary-5000
        self.venue.fraction=D('.5')
        self.assertEqual(self.session()['cleanup'],'verified')
        quantity=self.venue.q;entries=len(self.venue.orders)
        self.venue.now=boundary-1000
        original=self.venue.get;books=[];crossed=[]
        def next_bar(path,parameters=None):
            if path.endswith('/userTrades') and len(books)==2 and not crossed:
                # The final quote is still in the old candle; only its following
                # native fill-cursor read carries the local clock over the close.
                self.venue.now=boundary+1
                crossed.append(self.venue.now)
            result=original(path,parameters)
            if path.endswith('/depth'):books.append(result)
            return result
        self.venue.get=next_bar
        with State(self.directory,SCOPE) as state:
            self.venue.begin_cycle(120)
            model=Campaign.restore(state.get('linear_campaign'))
            snapshot=self.venue.snapshot('123')
            ownership=reconcile(state,self.venue,model,snapshot)
            engine=Lifecycle(self.venue,state,'123',authorized=True,
                             session=state.get('entry_fill')['session'])
            engine.risk_audit_ok=True;engine.reconciled=(snapshot,0,ownership)
            with self.assertRaisesRegex(Blocked,'completed model candle changed'):
                engine.top_up(model,snapshot)
            result=self.venue.snapshot('123')
            self.assertEqual(len(books),2)
            self.assertTrue(crossed)
            self.assertTrue(all(book['E']<boundary for book in books))
            self.assertEqual(books[0]['bids'],books[1]['bids'])
            self.assertEqual(books[0]['asks'],books[1]['asks'])
            self.assertEqual(len(self.venue.orders),entries)
            self.assertEqual(self.venue.q,quantity)
            self.assertTrue(result['native_full_position_protected'])
            # Candle catch-up gates only new risk. Existing native protection
            # can still be verified and an owned reduction can still execute.
            protection=state.get('position_protection')
            protected=safety.protect_existing(self.venue,state,engine.send,'123',
                protection['epoch'],protection['stop'],protection['take'],
                instrument=self.venue.rules,authorized=True,expected_owner=dict(result))
            self.assertTrue(protected['native_full_position_protected'])
            closed=engine.close_owned()
            self.assertEqual(D(closed['quantity_btc']),0)
        self.assertEqual(len(self.reductions()),1)

    def unknown_buffer_transfer(self, *, applied, external_fill=False):
        self.assertEqual(self.session()['cleanup'],'verified')
        quantity=self.venue.q
        self.assertGreater(quantity,0)
        histories=len(self.venue.margin_history);writes=len(self.venue.sent)
        with State(self.directory,SCOPE) as state:
            protection=state.get('position_protection')
        # An isolated-wallet removal does not change total wallet balance or
        # position ownership. It does reduce the frozen liquidation buffer.
        self.venue.margin-=D(1);self.venue.updated=self.venue.now
        original=self.venue.send;attempts=[]
        def lost_answer(method,path,payload):
            if path.endswith('/positionMargin'):
                attempts.append(dict(payload))
                if applied:
                    original(method,path,payload)
                else:
                    self.venue.now+=1
                    self.venue.sent.append((method,path,dict(payload)))
                    self.venue.calls.append((method,path,dict(payload)))
                if external_fill:
                    self.venue.fill(dict(side='BUY',reduceOnly=False,price=str(self.venue.mark),
                                         orderId=900001,executedQty='0'),D('.001'))
                raise TimeoutError('margin response lost')
            return original(method,path,payload)
        self.venue.send=lost_answer
        return quantity,histories,writes,protection,attempts

    def test_unknown_applied_buffer_transfer_holds_from_fresh_native_proof(self):
        quantity,histories,_,protection,attempts=self.unknown_buffer_transfer(applied=True)
        result=self.session(seconds=3)
        resumed=self.session(seconds=2)
        self.assertEqual(len(attempts),1)
        self.assertEqual(len(self.venue.margin_history),histories+1)
        self.assertEqual(self.venue.q,quantity)
        self.assertEqual(self.reductions(),[])
        for report in (result,resumed):
            self.assertEqual(report['status'],'unknown',report)
            self.assertEqual(report['cleanup'],'verified',report)
            self.assertEqual(report['pending_intents'],1)
            self.assertTrue(report['actual']['native_full_position_protected'])
        with State(self.directory,SCOPE) as state:
            pending=state.pending()
            self.assertEqual(len(pending),1)
            self.assertEqual((pending[0]['kind'],pending[0]['status']),('binance_margin','unknown'))
            current=state.get('position_protection')
            self.assertEqual(current['buffer_distance'],protection['buffer_distance'])
            engine=Lifecycle(self.venue,state,'123')
            self.assertGreaterEqual(engine._gap(resumed['actual'],current['stop']),
                                    D(current['buffer_distance']))

    def test_unknown_unapplied_buffer_transfer_exits_without_resend(self):
        _,histories,_,_,attempts=self.unknown_buffer_transfer(applied=False)
        result=self.session(seconds=3)
        resumed=self.session(seconds=2)
        self.assertEqual(len(attempts),1)
        self.assertEqual(len(self.venue.margin_history),histories)
        self.assertEqual(self.venue.q,0)
        self.assertEqual(len(self.reductions()),1)
        self.assertFalse(any(order['algoStatus']=='NEW' for order in self.venue.algos.values()))
        for report in (result,resumed):
            self.assertEqual(report['cleanup'],'verified',report)
            self.assertEqual(D(report['actual']['quantity_btc']),0)
            # A flat position does not identify which transfer ran. Within the
            # signed-request expiry bound, the lost request is still unknown.
            self.assertEqual(report['pending_intents'],1)

    def test_unknown_buffer_transfer_with_external_fill_cannot_authorize_owned_exit(self):
        quantity,histories,writes,protection,attempts=self.unknown_buffer_transfer(
            applied=False,external_fill=True)
        result=self.session(seconds=3)
        self.assertEqual(len(attempts),1)
        self.assertEqual(len(self.venue.margin_history),histories)
        self.assertEqual(self.venue.q,quantity+D('.001'))
        self.assertEqual(self.reductions(),[])
        self.assertFalse(any(method=='DELETE' for method,_,_ in self.venue.sent[writes:]))
        self.assertEqual(result['status'],'unknown',result)
        self.assertEqual(result['cleanup'],'unresolved',result)
        self.assertTrue(any('external or unowned fill' in error['reason'] for error in result['errors']),result)
        live={identity for identity,order in self.venue.algos.items() if order['algoStatus']=='NEW'}
        self.assertEqual(live,{client_id(SCOPE,protection['epoch'],kind)
                              for kind in ('STOP_MARKET','TAKE_PROFIT_MARKET')})

    def test_entry_prepare_pause_expires_quote_before_transport(self):
        with State(self.directory,SCOPE) as state:
            original=state.prepare;paused=[]
            def durable_pause(identity,kind,payload,**kwargs):
                original(identity,kind,payload,**kwargs)
                if kind=='binance_order' and payload.get('timeInForce')=='IOC':
                    paused.append(identity)
                    # The durable IOC already exists; its same-bar quote ages
                    # while fsync stalls, with manual entry still authorized.
                    self.venue.wait(16)
            with patch.object(state,'prepare',new=durable_pause):
                result=self.entry_cycle(state)
            self.assertEqual(len(paused),1)
            self.assertEqual(self.venue.now//FOUR_HOURS*FOUR_HOURS,self.start)
            self.assertEqual(self.venue.q,0)
            self.assertEqual(self.venue.sent,[])
            self.assertEqual(D(result['actual']['quantity_btc']),0)
            row=state.db.execute('SELECT status,result FROM intents WHERE id=?',(paused[0],)).fetchone()
            self.assertEqual(row[0],'rejected')
            self.assertIn('entry quote/model expired',json.loads(row[1])['not_sent'])
            self.assertEqual(state.pending(),[])
