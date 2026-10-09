import tempfile
import unittest
from decimal import Decimal as D
from coinquant.state import State
from coinquant.binance import Binance
from coinquant.binance_safety import protect_existing,cancel_entry,reduce_existing,add_margin
from coinquant.types import Blocked,Unknown
from tests.test_binance_quantity import instrument

def rules():
    r=instrument();r['filters'].append(dict(filterType='PRICE_FILTER',tickSize='.1',minPrice='1',maxPrice='1000000'))
    r.update(marginAsset='USDT',quotePrecision=8);return r

class Native(Binance):
    def __init__(self):
        super().__init__(clock=lambda:1770004800.0)
        self.orders={};self.sent=[];self.q='.003';self.margin='30';self.remainders=0;self.cursor=7
    def snapshot(self,uid):
        return dict(account_uid=str(uid),quantity_btc=self.q,mark_price='100000',
            native_liquidation_price='91000',isolated_wallet_usdt=self.margin,wallet_usdt='100',entry='100000',last_fill_id=self.cursor,
            possible_entry_remainders=self.remainders,
            native_full_position_protected=len(self.orders)>=2,stop_before_liquidation=True)
    def get(self,path,parameters=None):
        if path=='/fapi/v1/userTrades':return [dict(symbol='BTCUSDT',id=self.cursor)]
        raise Unknown('fixture read unavailable')
    def query_intent(self,identity,conditional=False):
        if identity not in self.orders:raise Unknown('missing')
        return dict(parent=self.orders[identity],child=None)
    def send(self,method,path,p):
        self.sent.append((method,path,p))
        if path=='/fapi/v1/algoOrder':
            self.orders[p['clientAlgoId']]=dict(p,algoId=len(self.orders)+1,orderType=p['type'],
                closePosition=True,priceProtect=False,algoStatus='NEW')
        elif method=='DELETE':
            self.orders[p['origClientOrderId']].update(status='FILLED',executedQty='.01')
            self.q='.01';self.remainders=0
        elif path=='/fapi/v1/positionMargin':
            self.margin=str(D(self.margin)+D(p['amount']))
            return dict(code=200,type=1,amount=p['amount'])
        else:
            self.orders[p['newClientOrderId']]=dict(p,reduceOnly=True,origQty=p['quantity'],
                executedQty=p['quantity'],status='FILLED');self.q='0'

class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.state=State(self.tmp.name,'binance:BTCUSDT:live:123').__enter__();self.native=Native()
    def tearDown(self):self.state.__exit__();self.tmp.cleanup()
    def protect(self,send=None,**kw):
        return protect_existing(self.native,self.state,send or self.native.send,'123',100,'95000','110000',instrument=rules(),**kw)
    def test_default_does_not_write(self):
        with self.assertRaises(Blocked):self.protect()
        self.assertEqual(self.native.sent,[])
    def test_partial_exposure_close_all_and_idempotent_recovery(self):
        self.protect(authorized=True);self.protect(authorized=True)
        self.assertEqual(len(self.native.sent),2)
        for _,_,p in self.native.sent:
            self.assertNotIn('quantity',p);self.assertNotIn('reduceOnly',p)
            self.assertEqual(p['closePosition'],'true')
    def test_timeout_after_acceptance_is_queried(self):
        def send(*a):self.native.send(*a);raise TimeoutError()
        self.protect(send,authorized=True)
        self.assertEqual(len(self.native.sent),2)
    def test_unknown_missing_never_retries(self):
        calls=[]
        def send(*a):calls.append(a);raise TimeoutError()
        for _ in range(2):
            with self.assertRaises(Unknown):self.protect(send,authorized=True)
        self.assertEqual(len(calls),1)
    def test_remainder_blocks_protection(self):
        self.native.remainders=1
        with self.assertRaises(Blocked):self.protect(authorized=True)
        self.assertEqual(self.native.sent,[])
    def test_cancel_fill_race_returns_real_exposure(self):
        p=dict(symbol='BTCUSDT',side='BUY',positionSide='BOTH',type='LIMIT',quantity='.01')
        self.state.prepare('cq-entry','binance_order',p)
        self.native.orders['cq-entry']=dict(p,reduceOnly=False,status='PARTIALLY_FILLED',origQty='.01',executedQty='.003')
        self.native.remainders=1
        r=cancel_entry(self.native,self.state,self.native.send,'123',100,'cq-entry',authorized=True)
        self.assertEqual(r['quantity_btc'],'.01');self.assertEqual(self.state.pending(),[])
    def test_unknown_margin_blocks_different_epoch(self):
        calls=[]
        def send(*a):calls.append(a);raise TimeoutError()
        for epoch in (100,200):
            with self.assertRaises(Unknown):add_margin(self.native,self.state,send,'123',epoch,'40',instrument=rules(),authorized=True)
        self.assertEqual(len(calls),1)

    def test_no_open_order_is_not_proof_unknown_entry_cannot_arrive(self):
        payload=dict(symbol='BTCUSDT',side='BUY',positionSide='BOTH',type='MARKET',quantity='.003')
        self.state.prepare('cq-unknown-entry','binance_order',payload)
        with self.assertRaises(Unknown):self.protect(authorized=True)
        with self.assertRaises(Unknown):reduce_existing(self.native,self.state,self.native.send,'123',100,'.003',instrument=rules(),authorized=True)
        self.assertEqual(self.native.sent,[])

    def test_stop_fill_between_legs_prevents_stale_take_write(self):
        def send(*args):
            self.native.send(*args)
            self.native.q='0'
        with self.assertRaises(Unknown):self.protect(send,authorized=True)
        self.assertEqual(len(self.native.sent),1)
        self.assertEqual(self.native.sent[0][2]['type'],'STOP_MARKET')

    def test_new_entry_remainder_between_legs_stops_writes(self):
        def send(*args):
            self.native.send(*args)
            self.native.remainders=1
        with self.assertRaises(Unknown):self.protect(send,authorized=True)
        self.assertEqual(len(self.native.sent),1)

    def test_reduce_only_below_entry_min_notional_can_close(self):
        instrument=rules()
        for f in instrument['filters']:
            if f['filterType']=='MIN_NOTIONAL':f['notional']='1000'
        result=reduce_existing(self.native,self.state,self.native.send,'123',100,'.003',instrument=instrument,authorized=True)
        self.assertEqual(result['quantity_btc'],'0')

    def test_same_direction_equal_size_reopen_blocks_all_safety_writes(self):
        owner=self.native.snapshot('123');self.native.cursor+=2
        operations=(
            lambda:self.protect(authorized=True,snapshot=owner,expected_owner=owner),
            lambda:reduce_existing(self.native,self.state,self.native.send,'123',100,'.003',
                instrument=rules(),authorized=True,expected_owner=owner,expected_direction=1),
            lambda:add_margin(self.native,self.state,self.native.send,'123',100,'40',
                instrument=rules(),authorized=True,snapshot=owner,expected_owner=owner))
        for operation in operations:
            with self.assertRaises(Unknown):operation()
        self.assertEqual(self.native.sent,[])
        self.assertEqual(self.state.pending(),[])

    def test_invalid_final_fill_cursor_blocks_before_protection(self):
        owner=self.native.snapshot('123')
        for fills in (None,[dict(symbol='ETHUSDT',id=7)],[dict(symbol='BTCUSDT',id=True)],
                      [dict(symbol='BTCUSDT',id=7)]*2,[]):
            with self.subTest(fills=fills):
                self.native.get=lambda *a: fills
                with self.assertRaises(Unknown):self.protect(authorized=True,snapshot=owner,expected_owner=owner)
        self.assertEqual(self.native.sent,[])

    def test_reduction_keeps_its_durable_direction(self):
        self.native.q='-.003'
        with self.assertRaises(Unknown):
            reduce_existing(self.native,self.state,self.native.send,'123',100,'.003',
                instrument=rules(),authorized=True,expected_direction=1)
        self.assertEqual(self.native.sent,[])

    def test_conditional_reduction_uses_final_mark_for_both_directions(self):
        for q,mark in (('.003','101000'),('-.003','99000')):
            with self.subTest(quantity=q):
                self.native.q=q
                snapshot=self.native.snapshot
                self.native.snapshot=lambda uid:dict(snapshot(uid),mark_price=mark)
                owner=self.native.snapshot('123')
                result=reduce_existing(self.native,self.state,self.native.send,'123',100,'.003',
                    instrument=rules(),authorized=True,expected_owner=owner,stop=D(100000))
                self.assertIsNone(result)
                self.assertEqual(self.native.q,q)
                self.assertEqual(self.native.sent,[])
                self.assertEqual(self.state.pending(),[])
                self.native.snapshot=snapshot

    def test_same_size_manual_fill_between_protection_legs_stops_take(self):
        owner=self.native.snapshot('123')
        def send(*args):
            self.native.send(*args);self.native.cursor+=2
        with self.assertRaises(Unknown):self.protect(send,authorized=True,expected_owner=owner)
        self.assertEqual(len(self.native.sent),1)
        self.assertEqual(self.native.sent[0][2]['type'],'STOP_MARKET')

    def test_terminal_partial_reduction_returns_its_proven_remainder(self):
        def send(method,path,p):
            self.native.send(method,path,p)
            self.native.orders[p['newClientOrderId']].update(status='EXPIRED',executedQty='.001')
            self.native.q='.002'
        result=reduce_existing(self.native,self.state,send,'123',100,'.003',
            instrument=rules(),authorized=True)
        self.assertEqual(result['quantity_btc'],'.002')
        self.assertEqual(self.state.pending(),[])

    def test_terminal_zero_fill_returns_unchanged_position_for_no_progress_check(self):
        def send(method,path,p):
            self.native.send(method,path,p)
            self.native.orders[p['newClientOrderId']].update(status='EXPIRED',executedQty='0')
            self.native.q='.003'
        result=reduce_existing(self.native,self.state,send,'123',100,'.003',
            instrument=rules(),authorized=True)
        self.assertEqual(result['quantity_btc'],'.003')
