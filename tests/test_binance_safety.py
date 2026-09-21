import tempfile
import unittest
from decimal import Decimal as D
from pancakequant.state import State
from pancakequant.binance import BinanceReadOnly
from pancakequant.binance_safety import protect_existing,cancel_entry,reduce_existing,add_margin
from pancakequant.types import Blocked,Unknown
from tests.test_binance_quantity import instrument

def rules():
    r=instrument();r['filters'].append(dict(filterType='PRICE_FILTER',tickSize='.1',minPrice='1',maxPrice='1000000'));return r

class Native(BinanceReadOnly):
    def __init__(self):
        self.orders={};self.sent=[];self.q='.003';self.margin='30';self.remainders=0
    def snapshot(self,uid):
        return dict(account_uid=str(uid),quantity_btc=self.q,mark_price='100000',
            native_liquidation_price='91000',isolated_wallet_usdt=self.margin,wallet_usdt='100',
            possible_entry_remainders=self.remainders,
            native_full_position_protected=len(self.orders)>=2,stop_before_liquidation=True)
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
        self.state.prepare('pq-entry','binance_order',p)
        self.native.orders['pq-entry']=dict(p,reduceOnly=False,status='PARTIALLY_FILLED',origQty='.01',executedQty='.003')
        self.native.remainders=1
        r=cancel_entry(self.native,self.state,self.native.send,'123',100,'pq-entry',authorized=True)
        self.assertEqual(r['quantity_btc'],'.01');self.assertEqual(self.state.pending(),[])
    def test_reduce_only_never_reverses(self):
        reduce_existing(self.native,self.state,self.native.send,'123',100,'.003',instrument=rules(),authorized=True)
        self.assertEqual(self.native.sent[0][2]['reduceOnly'],'true')
        self.assertEqual(self.native.q,'0')
    def test_unknown_margin_blocks_different_epoch(self):
        calls=[]
        def send(*a):calls.append(a);raise TimeoutError()
        for epoch in (100,200):
            with self.assertRaises(Unknown):add_margin(self.native,self.state,send,'123',epoch,'40',authorized=True)
        self.assertEqual(len(calls),1)
    def test_model_margin_target_readback(self):
        result=add_margin(self.native,self.state,self.native.send,'123',100,'40',authorized=True)
        self.assertEqual(result['isolated_wallet_usdt'],'40')
        self.assertEqual(self.state.pending(),[])
