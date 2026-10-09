import json
import tempfile
import unittest
from copy import deepcopy
from io import BytesIO
from urllib.error import HTTPError
from urllib.parse import urlsplit
from unittest.mock import patch
from coinquant.campaign import Campaign
from coinquant.ownership import owned_observation, reconcile
from coinquant.state import State
from coinquant.binance import Binance
from coinquant.types import Blocked, Missing, Unknown
from tests.session_venue import Venue

class RecoveryTests(unittest.TestCase):
    def test_stop_after_terminal_commit_preserves_zero_fill_recovery_past_retention(self):
        class Stop(BaseException):pass
        with tempfile.TemporaryDirectory() as tmp:
            venue=Venue();venue.seed(tmp);venue.fraction=0
            identity='cq-zero'
            payload=dict(symbol='BTCUSDT',side='BUY',positionSide='BOTH',type='LIMIT',
                         quantity='.001',price=str(venue.mark),timeInForce='IOC',newClientOrderId=identity)
            with State(tmp,'binance:BTCUSDT:live:123') as state:
                model=Campaign.restore(state.get('linear_campaign'))
                state.prepare(identity,'binance_order',payload,campaign=model.last,
                              flat_snapshot=venue.snapshot('123'))
                venue.send('POST','/fapi/v1/order',payload)
                finish=state.finish
                def stop(*args,**kwargs):
                    finish(*args,**kwargs)
                    raise Stop()
                with patch.object(state,'finish',side_effect=stop),self.assertRaises(Stop):
                    venue.recover_pending(state)
            venue.wait(4*86400)
            with State(tmp,'binance:BTCUSDT:live:123') as state:
                self.assertEqual(state.pending(),[])
                self.assertIn(identity,state.get('terminal_native_orders'))
                with patch.object(venue,'query_intent',side_effect=Missing('expired query')) as query:
                    result=reconcile(state,venue,Campaign.restore(state.get('linear_campaign')),
                                     venue.snapshot('123'))
                self.assertEqual(result['status'],'no_campaign_fill')
                self.assertEqual(state.get('entry_campaigns'),{})
                query.assert_not_called()

    def test_late_missing_order_stays_unknown_then_original_fill_recovers(self):
        with tempfile.TemporaryDirectory() as tmp, State(tmp,'binance:BTCUSDT:live:123') as state:
            payload=dict(symbol='BTCUSDT',side='BUY',positionSide='BOTH',type='LIMIT',quantity='.001')
            state.prepare('cq-add','binance_order',payload,result={'prepared_at_ms':100000})
            reader=Binance(clock=lambda:100301)
            reader.query_intent=lambda *a,**k:(_ for _ in ()).throw(Missing('late -2013'))
            self.assertEqual(reader.recover_pending(state),dict(resolved=0,pending=1))
            self.assertEqual(state.pending()[0]['id'],'cq-add')
            reader.query_intent=lambda *a,**k:dict(parent=dict(payload,origQty='.001',executedQty='.001',status='FILLED'),child=None)
            self.assertEqual(reader.recover_pending(state),dict(resolved=1,pending=0))
            self.assertEqual(state.db.execute("SELECT status FROM intents WHERE id='cq-add'").fetchone()[0],'confirmed')


    def test_terminal_partial_fill_and_unknown_are_independent(self):
        with tempfile.TemporaryDirectory() as tmp, State(tmp,'binance:BTCUSDT:live:123') as state:
            payload=dict(symbol='BTCUSDT',side='BUY',positionSide='BOTH',type='LIMIT',quantity='.01')
            for identity in ('cq-good','cq-unknown'):state.prepare(identity,'binance_order',payload)
            reader=Binance()
            def lookup(identity,conditional=False):
                if identity=='cq-unknown':raise Unknown('missing history')
                return dict(parent=dict(payload,origQty='.01',executedQty='.003',status='CANCELED'),child=None)
            reader.query_intent=lookup
            self.assertEqual(reader.recover_pending(state),dict(resolved=1,pending=1))
            self.assertEqual(state.pending()[0]['id'],'cq-unknown')
            self.assertEqual(reader.recover_pending(state),dict(resolved=0,pending=1))

    def test_canceled_parent_cannot_hide_working_child(self):
        with tempfile.TemporaryDirectory() as tmp, State(tmp,'binance:BTCUSDT:live:123') as state:
            payload=dict(symbol='BTCUSDT',side='SELL',positionSide='BOTH',type='STOP_MARKET',closePosition='true',triggerPrice='90000',workingType='MARK_PRICE')
            state.prepare('cq-stop','binance_algo',payload)
            parent=dict(payload,orderType='STOP_MARKET',closePosition=True,algoStatus='CANCELED')
            child=dict(status='PARTIALLY_FILLED',origQty='.01',executedQty='.003')
            reader=Binance();reader.query_intent=lambda *a,**k:dict(parent=parent,child=child)
            self.assertEqual(reader.recover_pending(state),dict(resolved=0,pending=1))
            child['status']='FILLED'
            self.assertEqual(reader.recover_pending(state),dict(resolved=0,pending=1))
            child['executedQty']='.01'
            self.assertEqual(reader.recover_pending(state),dict(resolved=1,pending=0))

    def test_payload_mismatch_and_unknown_intent_kind_stay_unknown(self):
        with tempfile.TemporaryDirectory() as tmp, State(tmp,'binance:BTCUSDT:live:123') as state:
            payload=dict(symbol='BTCUSDT',side='BUY',positionSide='BOTH',type='MARKET',quantity='.01')
            state.prepare('cq-mismatch','binance_order',payload);state.prepare('old','entry',{})
            reader=Binance();reader.query_intent=lambda *a,**k:dict(parent=dict(payload,side='SELL',origQty='.01',executedQty='.01',status='FILLED'),child=None)
            self.assertEqual(reader.recover_pending(state),dict(resolved=0,pending=2))
    def test_readonly_recovers_algo_cancel_only_after_child_terminal(self):
        with tempfile.TemporaryDirectory() as tmp, State(tmp,'binance:BTCUSDT:live:123') as state:
            state.prepare('cq-old','binance_algo',dict(symbol='BTCUSDT',closePosition='true'))
            state.finish('cq-old','confirmed',{})
            state.prepare('cq-cancel','binance_algo_cancel',dict(clientAlgoId='cq-old'))
            child=dict(status='PARTIALLY_FILLED',origQty='.01',executedQty='.003')
            reader=Binance();reader.query_intent=lambda *a,**k:dict(parent=dict(algoStatus='CANCELED'),child=child)
            self.assertEqual(reader.recover_pending(state),dict(resolved=0,pending=1))
            child['status']='CANCELED'
            self.assertEqual(reader.recover_pending(state),dict(resolved=1,pending=0))


class CurrentProtectionRecoveryTests(unittest.TestCase):
    def parent(self,actual='0'):
        return dict(symbol='BTCUSDT',clientAlgoId='cq-old',algoId=1,
                    algoType='CONDITIONAL',
                    side='SELL',positionSide='BOTH',orderType='STOP_MARKET',
                    closePosition=True,priceProtect=False,workingType='MARK_PRICE',
                    triggerPrice='90000',algoStatus='NEW',actualOrderId=actual)

    def reader(self,rows,history_error=None):
        reader=Binance();calls=[]
        def get(path,params):
            calls.append((path,params))
            if path=='/fapi/v1/algoOrder':raise history_error or Missing('history retention')
            self.assertEqual(path,'/fapi/v1/openAlgoOrders')
            self.assertEqual(params,{'symbol':'BTCUSDT'})
            return deepcopy(rows)
        reader.get=get
        return reader,calls

    def test_missing_history_uses_only_current_untriggered_protection(self):
        for actual in ('','0',0):
            with self.subTest(actual=actual):
                reader,calls=self.reader([self.parent(actual)])
                observed=reader.query_intent('cq-old',conditional=True)
                self.assertIsNone(observed['child'])
                self.assertFalse(observed['resubmit_authorized'])
                self.assertFalse(reader.conditional_terminal('cq-old'))
                self.assertEqual(len(calls),4)
        reader,calls=self.reader([self.parent()],Unknown('timeout'))
        with self.assertRaises(Unknown):reader.query_intent('cq-old',conditional=True)
        self.assertEqual(len(calls),1)

    def test_native_missing_history_reaches_current_open_lookup(self):
        calls=[]
        parent=self.parent()
        class HTTP:
            def open(self,request,timeout):
                path=urlsplit(request.full_url).path
                calls.append((request.method,path))
                if path=='/fapi/v1/algoOrder':
                    body=BytesIO(b'{"code":-2013,"msg":"Order does not exist."}')
                    raise HTTPError(request.full_url,400,'fixture',{},body)
                return BytesIO(json.dumps([parent]).encode())
        reader=Binance(key='fixture',secret='fixture',opener=HTTP())
        observed=reader.query_intent('cq-old',conditional=True)
        self.assertEqual(observed['parent'],parent)
        self.assertIsNone(observed['child'])
        self.assertFalse(observed['resubmit_authorized'])
        self.assertEqual(calls,[('GET','/fapi/v1/algoOrder'),('GET','/fapi/v1/openAlgoOrders')])

    def test_other_native_errors_cannot_authorize_current_open_fallback(self):
        for status,code in ((400,-1102),(500,-2013)):
            with self.subTest(status=status,code=code):
                calls=[]
                class HTTP:
                    def open(self,request,timeout):
                        calls.append(urlsplit(request.full_url).path)
                        body=BytesIO(json.dumps(dict(code=code,msg='fixture')).encode())
                        raise HTTPError(request.full_url,status,'fixture',{},body)
                reader=Binance(key='fixture',secret='fixture',opener=HTTP())
                with self.assertRaises(Unknown) as caught:
                    reader.query_intent('cq-old',conditional=True)
                self.assertEqual(type(caught.exception),Unknown)
                self.assertEqual(calls,['/fapi/v1/algoOrder'])

    def test_absent_triggered_malformed_or_foreign_current_parent_stays_unknown(self):
        changes=(dict(algoType='UNKNOWN'),dict(algoStatus='TRIGGERED'),dict(actualOrderId='42'),dict(actualOrderId=None),
                 dict(actualOrderId=False),dict(closePosition=False),dict(priceProtect=True),
                 dict(workingType='CONTRACT_PRICE'),dict(orderType='LIMIT'),dict(algoId=0),
                 dict(symbol='ETHUSDT'),dict(positionSide='LONG'),dict(triggerPrice='0'))
        rows=[[],[self.parent(),self.parent()],{},[None]]
        rows.extend([[dict(self.parent(),**change)] for change in changes])
        for current in rows:
            with self.subTest(current=current):
                reader,_=self.reader(current)
                with self.assertRaises((Blocked,Unknown)):reader.query_intent('cq-old',conditional=True)

    def test_current_parent_must_match_durable_trigger_and_never_become_terminal_archive(self):
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'binance:BTCUSDT:live:123') as state:
            payload=dict(symbol='BTCUSDT',side='SELL',positionSide='BOTH',type='STOP_MARKET',
                         closePosition='true',priceProtect='false',workingType='MARK_PRICE',triggerPrice='90000')
            state.prepare('cq-old','binance_algo',payload)
            state.finish('cq-old','confirmed',{})
            reader,_=self.reader([dict(self.parent(),triggerPrice='89000')])
            with self.assertRaises(Unknown):owned_observation(state,reader,'cq-old',conditional=True)
            reader,_=self.reader([self.parent()])
            self.assertIsNone(owned_observation(state,reader,'cq-old',conditional=True)['child'])
            self.assertIsNone(state.get('terminal_native_orders'))
