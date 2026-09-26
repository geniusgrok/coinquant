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
        snapshot=dict(flat,quantity_btc='.003',entry='100',wallet_usdt='999',possible_entry_remainders=1,native_full_position_protected=False)
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
            s.update(quantity_btc='0',entry='0',possible_entry_remainders=0)
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
