import json
import tempfile
from unittest import TestCase
from unittest.mock import Mock
from decimal import Decimal as D
from time import time
from coinquant.state import State
from coinquant.campaign import Campaign
from coinquant.ownership import reconcile
from coinquant.types import Unknown


class OwnershipTests(TestCase):
    def fixture(self,state):
        now=int(time()*1000);epoch=now//14400000*14400000
        m=Campaign();m.last=epoch;m.model.last=epoch
        flat=dict(account_uid='123',quantity_btc='0.00000000',possible_entry_remainders=0)
        p=dict(symbol='BTCUSDT',side='BUY',positionSide='BOTH',type='LIMIT',quantity='.01')
        state.prepare('cq-entry','binance_order',p,campaign=epoch,flat_snapshot=flat)
        start=state.get('entry_campaigns')['cq-entry']['prepared_at'];now=start+1000
        order=dict(p,orderId=1,origQty='.01',executedQty='.003',status='PARTIALLY_FILLED')
        snapshot=dict(flat,quantity_btc='.003',entry='100',wallet_usdt='999',possible_entry_remainders=1,native_full_position_protected=False,last_fill_id=11)
        trade=dict(symbol='BTCUSDT',positionSide='BOTH',side='BUY',orderId=1,id=11,time=start,qty='.003')
        reader=Mock();reader.clock.return_value=now/1000;reader.query_intent.return_value={'parent':order,'child':None}
        reader.get.return_value=[trade];reader.snapshot.return_value=snapshot
        return m,reader,snapshot,trade

    def test_late_partial_fill_binds_once_and_exposes_unprotected_remainder(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
            m,r,s,t=self.fixture(state)
            a=reconcile(state,r,m,s);checkpoint=m.checkpoint()
            self.assertEqual(a['quantity'],'0.003')
            self.assertEqual(a['entry_remainder'],1);self.assertFalse(a['protection_confirmed'])
            self.assertEqual(m.action(D('.003')),'exit')  # opportunity has expired
            reconcile(state,r,m,s);self.assertEqual(m.checkpoint(),checkpoint)

    def test_external_fill_or_position_mismatch_never_guesses_owner(self):
        for kind in ('external','quantity'):
            with tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
                m,r,s,t=self.fixture(state)
                if kind=='external':t['orderId']=999
                else:s['quantity_btc']='.004'
                before=m.checkpoint()
                with self.assertRaises(Unknown):reconcile(state,r,m,s)
                self.assertEqual(before,m.checkpoint())

    def test_successful_reconciliation_reuses_final_account_observation(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
            m,r,s,_=self.fixture(state)
            s.update(mark_price='99',observed_at_ms=1,wallet_observed_from_ms=1,wallet_observed_until_ms=1)
            fresh=dict(s,mark_price='101',native_full_position_protected=True,
                       observed_at_ms=3,wallet_observed_from_ms=2,wallet_observed_until_ms=3)
            r.snapshot.return_value=fresh
            result=reconcile(state,r,m,s)
            self.assertEqual(s,fresh)
            self.assertTrue(result['protection_confirmed'])
            r.snapshot.assert_called_once_with('123')

    def test_changed_exposure_at_final_readback_never_refreshes_or_commits(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
            m,r,s,_=self.fixture(state)
            before=m.checkpoint();original=dict(s)
            r.snapshot.return_value=dict(s,quantity_btc='.004',mark_price='101')
            with self.assertRaises(Unknown):reconcile(state,r,m,s)
            self.assertEqual(s,original)
            self.assertEqual(m.checkpoint(),before)
            self.assertIsNone(state.get('ownership_coverage'))

    def test_rejected_reduction_has_no_native_order_to_query(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
            m,r,s,t=self.fixture(state)
            payload=dict(symbol='BTCUSDT',side='SELL',positionSide='BOTH',type='MARKET',quantity='.003',reduceOnly='true')
            state.prepare('cq-exit','binance_order',payload)
            state.finish('cq-exit','rejected',{'not_sent':'deadline'})
            entry=r.query_intent.return_value
            r.query_intent.side_effect=lambda identity,**kw:entry if identity=='cq-entry' else (_ for _ in ()).throw(Unknown('missing'))
            self.assertEqual(reconcile(state,r,m,s)['quantity'],'0.003')

    def test_new_fill_cursor_after_history_never_refreshes_or_commits(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
            m,r,s,_=self.fixture(state)
            before=m.checkpoint();original=dict(s)
            r.snapshot.return_value=dict(s,last_fill_id=13)
            with self.assertRaises(Unknown):reconcile(state,r,m,s)
            self.assertEqual(s,original)
            self.assertEqual(m.checkpoint(),before)
            self.assertIsNone(state.get('ownership_coverage'))

    def test_initial_recent_cursor_requires_matching_verified_history(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
            m,r,s,_=self.fixture(state)
            s['last_fill_id']=13
            with self.assertRaises(Unknown):reconcile(state,r,m,s)
            self.assertIsNone(state.get('ownership_coverage'))

    def test_zero_fill_entry_keeps_journal_when_recent_cursor_changes(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
            m,r,s,_=self.fixture(state)
            r.query_intent.return_value['parent'].update(status='CANCELED',executedQty='0')
            state.finish('cq-entry','confirmed',{'executed_quantity':'0'})
            s.update(quantity_btc='0',entry='0',possible_entry_remainders=0)
            r.snapshot.return_value=dict(s,last_fill_id=13)
            with self.assertRaises(Unknown):reconcile(state,r,m,s)
            self.assertIn('cq-entry',state.get('entry_campaigns'))
            self.assertIsNone(state.get('settled_entry_campaigns'))

    def test_older_than_default_recent_window_keeps_verified_ownership(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
            m,r,s,_=self.fixture(state)
            reconcile(state,r,m,s)
            r.clock.return_value+=8*86400
            r.get.return_value=[]
            s['last_fill_id']=-1
            result=reconcile(state,r,m,s)
            self.assertEqual(D(result['quantity']),D('.003'))
            self.assertEqual(s['last_fill_id'],-1)
            self.assertEqual(state.db.execute('SELECT COUNT(*) FROM native_fills').fetchone()[0],1)

    def test_lost_journal_cannot_assign_an_existing_position(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
            with self.assertRaises(Unknown):reconcile(state,Mock(),Campaign(),{'quantity_btc':'.1'})

    def test_protective_fill_preserves_consumption_after_flat_recovery(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
            m,r,s,t=self.fixture(state)
            entry=r.query_intent.return_value['parent']
            entry['status']='CANCELED'
            payload=dict(symbol='BTCUSDT',side='SELL',positionSide='BOTH',type='MARKET',quantity='.003',reduceOnly='true')
            state.prepare('cq-exit','binance_order',payload)
            exit_order=dict(payload,orderId=2,reduceOnly=True,status='FILLED',origQty='.003',executedQty='.003')
            r.query_intent.side_effect=lambda identity,**kw:dict(parent=entry if identity=='cq-entry' else exit_order,child=None)
            r.get.return_value=[t,dict(t,id=12,orderId=2,side='SELL')]
            s.update(quantity_btc='0',entry='0',possible_entry_remainders=0,last_fill_id=12)
            reconcile(state,r,m,s)
            self.assertEqual(m.consumed,m.last);self.assertIsNone(m.position_campaign)
            self.assertEqual(state.get('entry_campaigns'),{})
            self.assertIn('cq-entry',state.get('settled_entry_campaigns'))
            r.query_intent.reset_mock()
            self.assertEqual(reconcile(state,r,m,s)['status'],'flat_without_entry_journal')
            r.query_intent.assert_not_called()
            # A still-visible original opportunity cannot reopen after its stop.
            from coinquant.campaign import disposition
            self.assertEqual(disposition(type('Opportunity',(),dict(direction=1,identity=m.last))(),D(0),m.consumed),'consumed')

    def test_history_older_than_three_months_is_not_inferred(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
            m,r,s,t=self.fixture(state)
            r.clock.return_value+=100*86400
            with self.assertRaises(Unknown):reconcile(state,r,m,s)
            r.get.assert_not_called()

    def test_cumulative_fill_cannot_regress(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
            self.fixture(state)
            state.finish('cq-entry','partial',{'executed_quantity':'.003'})
            for result in ({'executed_quantity':'.002'},{}):
                with self.assertRaises(Unknown):state.finish('cq-entry','confirmed',result)
            self.assertEqual(state.pending()[0]['status'],'partial')

    def test_campaign_costs_keep_entry_add_and_partial_reduction_after_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            with State(tmp,'binance:BTCUSDT:live:123') as state:
                m,r,s,t=self.fixture(state)
                t.update(commission='.125',commissionAsset='USDT',realizedPnl='0')
                entry=r.query_intent.return_value['parent'];entry['status']='CANCELED'
                s['possible_entry_remainders']=0
                reconcile(state,r,m,s)
                state.finish('cq-entry','confirmed',{'executed_quantity':'.003'})
                add=dict(symbol='BTCUSDT',side='BUY',positionSide='BOTH',type='LIMIT',quantity='.002')
                state.prepare('cq-add','binance_order',add,campaign=m.last,position_snapshot=s)
                add_order=dict(add,orderId=2,origQty='.002',executedQty='.002',status='FILLED')
                reduce=dict(symbol='BTCUSDT',side='SELL',positionSide='BOTH',type='MARKET',quantity='.001',reduceOnly='true')
                state.prepare('cq-reduce','binance_order',reduce)
                reduce_order=dict(reduce,orderId=3,reduceOnly=True,origQty='.001',executedQty='.001',status='FILLED')
                orders={'cq-entry':entry,'cq-add':add_order,'cq-reduce':reduce_order}
                r.query_intent.side_effect=lambda identity,**kw:dict(parent=orders[identity],child=None)
                added=dict(t,id=12,orderId=2,qty='.002',commission='.2',time=t['time']+1)
                removed=dict(t,id=13,orderId=3,side='SELL',qty='.001',commission='.063',realizedPnl='-.25',time=t['time']+2)
                r.get.return_value=[t,added,removed]
                s.update(quantity_btc='.004',last_fill_id=13)
                result=reconcile(state,r,m,s)
                self.assertEqual(D(result['campaign_fee_usdt']),D('.388'))
                self.assertEqual(D(result['campaign_realized_pnl_usdt']),D('-.25'))
                self.assertEqual(result['last_fill_id'],13)
                self.assertEqual(state.db.execute('SELECT DISTINCT entry_id FROM native_fills').fetchall(),[('cq-entry',)])
                saved=[json.loads(row[0]) for row in state.db.execute('SELECT payload FROM native_fills ORDER BY trade_id')]
                self.assertEqual(saved,[t,added,removed])
            with State(tmp,'binance:BTCUSDT:live:123') as state:
                r.get.return_value=[]
                again=reconcile(state,r,m,s)
                self.assertEqual(again['campaign_fee_usdt'],result['campaign_fee_usdt'])
                self.assertEqual(again['campaign_realized_pnl_usdt'],result['campaign_realized_pnl_usdt'])
                self.assertEqual(again['last_fill_id'],13)

    def test_missing_or_unsupported_costs_do_not_block_position_reconciliation(self):
        variants=({'commission':None},{'commission':'NaN'},{'commission':'-.001'},
                  {'commissionAsset':'BNB'},{'commissionAsset':'BTC'},
                  {'realizedPnl':None},{'realizedPnl':'Infinity'},{'marginAsset':'BTC'})
        for changed in variants:
            with self.subTest(changed=changed),tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
                m,r,s,t=self.fixture(state)
                t.update(commission='.125',commissionAsset='USDT',realizedPnl='0')
                t.update(changed)
                result=reconcile(state,r,m,s)
                self.assertEqual(result['status'],'reconciled')
                self.assertEqual(result['quantity'],'0.003')
                missing='campaign_fee_usdt' if any(k.startswith('commission') for k in changed) else 'campaign_realized_pnl_usdt'
                self.assertIsNone(result[missing])
                self.assertEqual(state.db.execute('SELECT COUNT(*) FROM native_fills').fetchone()[0],1)


class AbsentEntryOwnership(TestCase):
    def rejected(self,result):
        flat=dict(account_uid='123',quantity_btc='0.00000000',possible_entry_remainders=0,last_fill_id=-1)
        p=dict(symbol='BTCUSDT',side='BUY',positionSide='BOTH',type='LIMIT',quantity='.01')
        m=Campaign();reader=Mock();reader.snapshot.return_value=flat;reader.query_intent.side_effect=Unknown('missing')
        return m,reader,flat,p,result

    def test_definitive_absence_reconciles_flat_but_legacy_absence_does_not(self):
        for marker,ok in ((True,True),(False,False)):
            with tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
                m,r,flat,p,_=self.rejected(None)
                state.prepare('cq-entry','binance_order',p,campaign=int(time()*1000)//14400000*14400000,flat_snapshot=flat)
                state.finish('cq-entry','rejected',{'prepared_at_ms':1,'absent_at_ms':400000,
                                                    **({'query_absent_within_retention':True} if marker else {})})
                fresh=dict(flat,mark_price='101',observed_at_ms=2)
                r.snapshot.return_value=fresh
                if ok:
                    self.assertEqual(reconcile(state,r,m,flat)['status'],'no_campaign_fill')
                    self.assertEqual(flat,fresh)
                else:
                    with self.assertRaises(Unknown):reconcile(state,r,m,flat)

    def test_late_fill_after_definitive_absence_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
            m,r,flat,p,_=self.rejected(None)
            state.prepare('cq-entry','binance_order',p,campaign=int(time()*1000)//14400000*14400000,flat_snapshot=flat)
            state.finish('cq-entry','rejected',{'prepared_at_ms':1,'absent_at_ms':400000,'query_absent_within_retention':True})
            with self.assertRaises(Unknown):reconcile(state,r,m,dict(flat,quantity_btc='.01'))
