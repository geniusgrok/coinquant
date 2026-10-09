"""Native recovery regressions for the issue 76 / PR 77 execution boundary."""
import json
import tempfile
import unittest
from copy import deepcopy
from decimal import Decimal as D

from coinquant.binance import Binance
from coinquant.binance_safety import add_margin, protect_existing, settled_protection
from coinquant.ownership import owned_observation
from coinquant.state import State
from coinquant.types import Blocked, Missing, Unknown
from tests.test_binance_safety import Native, rules


class TriggeredProtectionTests(unittest.TestCase):
    def fixture(self, state, child_status='FILLED', filled='.003', parent_status='TRIGGERED'):
        payload=dict(symbol='BTCUSDT',side='SELL',positionSide='BOTH',type='STOP_MARKET',
                     closePosition='true',priceProtect='false',workingType='MARK_PRICE',
                     triggerPrice='95000',clientAlgoId='cq-stop')
        state.prepare('cq-stop','binance_algo',payload)
        parent=dict(payload,orderType=payload['type'],closePosition=True,priceProtect=False,
                    algoStatus=parent_status,algoId=1,actualOrderId='42')
        child=dict(symbol='BTCUSDT',positionSide='BOTH',side='SELL',orderId=42,
                   origQty='.003',executedQty=filled,status=child_status)
        reader=Binance()
        reader.query_intent=lambda *a,**k:deepcopy(dict(parent=parent,child=child))
        return reader,parent,child

    def test_triggered_terminal_child_archives_in_every_recovery_path(self):
        for status,filled in (('FILLED','.003'),('CANCELED','.001'),('EXPIRED','0')):
            for path in ('ownership','cleanup','pending'):
                with self.subTest(status=status,path=path),tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
                    reader,_,_=self.fixture(state,status,filled)
                    if path=='ownership':
                        owned_observation(state,reader,'cq-stop',conditional=True)
                        archive=state.get('terminal_native_orders')
                    elif path=='cleanup':
                        self.assertTrue(settled_protection(reader,state,'cq-stop'))
                        archive=state.get('settled_protection')
                    else:
                        self.assertEqual(reader.recover_pending(state),dict(resolved=1,pending=0))
                        archive=state.get('terminal_native_orders')
                    self.assertEqual(archive['cq-stop']['child']['executedQty'],filled)
                    self.assertEqual(archive['cq-stop']['parent']['algoStatus'],'TRIGGERED')

    def test_working_or_missing_triggered_child_never_becomes_terminal(self):
        for child in (None,dict(status='NEW',origQty='.003',executedQty='0'),
                      dict(status='PARTIALLY_FILLED',origQty='.003',executedQty='.001')):
            with self.subTest(child=child),tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
                reader,parent,_=self.fixture(state)
                if child is not None:child=dict(child,symbol='BTCUSDT',positionSide='BOTH',side='SELL',orderId=42)
                reader.query_intent=lambda *a,**k:deepcopy(dict(parent=parent,child=child))
                self.assertFalse(settled_protection(reader,state,'cq-stop'))
                owned_observation(state,reader,'cq-stop',conditional=True)
                self.assertIsNone(state.get('terminal_native_orders'))
                self.assertEqual(reader.recover_pending(state),dict(resolved=0,pending=1))

    def test_child_status_change_between_terminal_reads_stays_unknown(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
            reader,parent,child=self.fixture(state)
            observations=iter((dict(parent=parent,child=child),
                               dict(parent=parent,child=dict(child,status='PARTIALLY_FILLED',executedQty='.001'))))
            reader.query_intent=lambda *a,**k:next(observations)
            with self.assertRaises(Unknown):settled_protection(reader,state,'cq-stop')
            self.assertIsNone(state.get('settled_protection'))


class FillCursorTests(unittest.TestCase):
    def test_full_page_continues_by_id_until_latest_cursor_is_proven(self):
        reader=Binance();calls=[]
        rows=[dict(symbol='BTCUSDT',id=i) for i in range(1,2008)]
        def get(path,params):
            self.assertEqual(path,'/fapi/v1/userTrades');calls.append(params)
            return rows[params.get('fromId',1)-1:params.get('fromId',1)-1+1000]
        reader.get=get
        fills,complete=reader._recent_fills()
        self.assertTrue(complete);self.assertEqual(fills,rows)
        self.assertEqual([p.get('fromId') for p in calls],[None,1001,2001])
        self.assertTrue(all('startTime' not in p and 'endTime' not in p for p in calls))

    def test_malformed_or_nonadvancing_pages_are_unknown(self):
        reader=Binance()
        for page in ([None],[dict(symbol='BTCUSDT',id=True)],
                     [dict(symbol='BTCUSDT',id=i) for i in range(1000)]):
            with self.subTest(page_size=len(page)):
                reader.get=lambda *a:page
                with self.assertRaises(Unknown):reader._recent_fills()

    def test_incomplete_snapshot_cannot_authorize_a_safety_write(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
            reader=Native();owner=reader.snapshot('123');owner['recent_fill_window_complete']=False
            with self.assertRaises(Unknown):
                protect_existing(reader,state,reader.send,'123',100,'95000','110000',
                                 instrument=rules(),authorized=True,snapshot=owner,expected_owner=owner)
            self.assertEqual(reader.sent,[]);self.assertEqual(state.pending(),[])


class AbsenceEvidenceTests(unittest.TestCase):
    def fixture(self,state,kind='binance_order'):
        identity='cq-missing'
        payload=dict(symbol='BTCUSDT',side='SELL',positionSide='BOTH',type='MARKET',
                     quantity='.003',reduceOnly='true',newClientOrderId=identity)
        if kind=='binance_algo':
            payload=dict(symbol='BTCUSDT',side='SELL',positionSide='BOTH',type='STOP_MARKET',
                         closePosition='true',priceProtect='false',workingType='MARK_PRICE',
                         triggerPrice='95000',clientAlgoId=identity)
        state.prepare(identity,kind,payload,result={'prepared_at_ms':600000})
        reader=Binance(clock=lambda:1000)
        observations={'open':[],'trades':[],'error':Missing('native -2013')}
        def get(path,params):
            if path in ('/fapi/v1/order','/fapi/v1/algoOrder'):raise observations['error']
            if path in ('/fapi/v1/openOrders','/fapi/v1/openAlgoOrders'):return deepcopy(observations['open'])
            if path=='/fapi/v1/userTrades':return deepcopy(observations['trades'])
            raise AssertionError(path)
        reader.get=get
        return reader,state.pending()[0],observations

    def test_only_native_absence_with_complete_matching_history_can_retire(self):
        for kind in ('binance_order','binance_algo'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
                reader,intent,observations=self.fixture(state,kind)
                self.assertTrue(reader.proven_absent(state,intent))
                observations['error']=Unknown('unresolved query')
                self.assertFalse(reader.proven_absent(state,intent))
                observations['error']=Missing('native -2013')
                for opened in ([None],[{}],[dict(symbol='ETHUSDT',clientOrderId='foreign')],
                               [dict(symbol='BTCUSDT',clientOrderId=intent['id'],clientAlgoId=intent['id'])]):
                    observations['open']=opened
                    self.assertFalse(reader.proven_absent(state,intent))
                observations['open']=[]
                trade=dict(symbol='BTCUSDT',id=9,time=700000,qty='.001')
                observations['trades']=[trade]
                self.assertFalse(reader.proven_absent(state,intent))
                state.db.execute('INSERT INTO native_fills VALUES (?,?,?)',(9,'cq-entry',json.dumps(trade)))
                state.db.commit()
                self.assertTrue(reader.proven_absent(state,intent))
                observations['trades']=[dict(trade,qty='.002')]
                self.assertFalse(reader.proven_absent(state,intent))
                observations['trades']=[dict(trade,time=1000001)]
                self.assertFalse(reader.proven_absent(state,intent))

    def test_recover_pending_cannot_bypass_missing_order_evidence(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
            reader,intent,observations=self.fixture(state)
            observations['trades']=[dict(symbol='BTCUSDT',id=9,time=700000)]
            self.assertEqual(reader.recover_pending(state),dict(resolved=0,pending=1))
            observations['trades']=[]
            self.assertEqual(reader.recover_pending(state),dict(resolved=1,pending=0))
            self.assertEqual(state.db.execute('SELECT status FROM intents WHERE id=?',(intent['id'],)).fetchone()[0],'rejected')

    def test_saturated_trade_page_or_expired_retention_is_not_absence(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
            reader,intent,observations=self.fixture(state)
            observations['trades']=[dict(symbol='BTCUSDT',id=i,time=700000) for i in range(1000)]
            self.assertFalse(reader.proven_absent(state,intent))
            observations['trades']=[];reader.clock=lambda:100000
            self.assertFalse(reader.proven_absent(state,intent))


class MarginFundingTests(unittest.TestCase):
    def test_margin_amount_uses_fresh_native_margin_not_supplied_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
            reader=Native();stale=reader.snapshot('123');reader.margin='35'
            after=add_margin(reader,state,reader.send,'123',100,'40',instrument=rules(),
                             authorized=True,snapshot=stale,expected_owner=stale)
            self.assertEqual(D(reader.sent[0][2]['amount']),D(5))
            self.assertEqual(D(after['isolated_wallet_usdt']),D(40))

    def test_missing_or_insufficient_available_funds_prevent_margin_write(self):
        for available in (None,'4'):
            with self.subTest(available=available),tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
                reader=Native();original=reader.snapshot
                reader.snapshot=lambda uid:dict(original(uid),available_usdt=available)
                with self.assertRaises((Blocked,Unknown)):
                    add_margin(reader,state,reader.send,'123',100,'40',instrument=rules(),authorized=True)
                self.assertEqual(reader.sent,[]);self.assertEqual(state.pending(),[])

    def test_funding_change_since_owner_observation_prevents_margin_write(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
            reader=Native();owner=reader.snapshot('123');original=reader.snapshot
            reader.snapshot=lambda uid:dict(original(uid),wallet_usdt='99')
            with self.assertRaises(Unknown):
                add_margin(reader,state,reader.send,'123',100,'40',instrument=rules(),authorized=True,
                           snapshot=owner,expected_owner=owner)
            self.assertEqual(reader.sent,[]);self.assertEqual(state.pending(),[])


class OwnedPriceExitTests(unittest.TestCase):
    def test_confirmed_flat_price_exit_retires_only_its_own_signal(self):
        from coinquant.opportunities import Opportunity
        from coinquant.ownership import reconcile
        from tests import test_ownership as fixture
        for same_signal in (True,False):
            with self.subTest(same_signal=same_signal),tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
                model,reader,snapshot,trade=fixture.OwnershipTests().fixture(state)
                signal=Opportunity(model.last if same_signal else model.last-14400000,1,D('95'),D('110'),model.last+14400000)
                model.model.active=signal;model.position_campaign=model.exit_campaign=model.last
                model.exit_cause='price';model.exit_stop='95'
                entry=reader.query_intent.return_value['parent'];entry['status']='CANCELED'
                payload=dict(symbol='BTCUSDT',side='SELL',positionSide='BOTH',type='MARKET',quantity='.003',reduceOnly='true')
                state.prepare('cq-exit','binance_order',payload)
                exited=dict(payload,orderId=2,reduceOnly=True,status='FILLED',origQty='.003',executedQty='.003')
                reader.query_intent.side_effect=lambda identity,**kw:dict(parent=entry if identity=='cq-entry' else exited,child=None)
                reader.get.return_value=[trade,dict(trade,id=12,orderId=2,side='SELL')]
                snapshot.update(quantity_btc='0',entry='0',possible_entry_remainders=0,last_fill_id=12)
                reconcile(state,reader,model,snapshot)
                self.assertIsNone(model.exit_cause);self.assertIsNone(model.position_campaign)
                self.assertEqual(model.model.active,None if same_signal else signal)
