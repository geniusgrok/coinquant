import unittest
from coinquant.binance_safety import replace_protection
from coinquant.state import client_id
from coinquant.types import Unknown,Blocked
from tests.test_binance_safety import Native,rules
from coinquant.state import State
from coinquant.binance_safety import protect_existing
import tempfile

class ReplacementTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.state=State(self.tmp.name,'binance:BTCUSDT:live:123').__enter__();self.native=Native()
        protect_existing(self.native,self.state,self.native.send,'123',100,'95000','110000',instrument=rules(),authorized=True)
        original=self.native.send
        self.native.children={}
        def send(method,path,p):
            if method=='DELETE' and path=='/fapi/v1/algoOrder':
                self.assertEqual(set(p),{'clientAlgoId'})  # native schema: no symbol on single algo cancel
                self.native.sent.append((method,path,p));self.native.orders[p['clientAlgoId']]['algoStatus']='CANCELED'
            else:original(method,path,p)
        self.native.send=send
        query=self.native.query_intent
        def observe(identity,conditional=False):
            r=query(identity,conditional);r['child']=self.native.children.get(identity);return r
        self.native.query_intent=observe
    def tearDown(self):
        self.state.__exit__();self.tmp.cleanup()
    def replace(self,send=None):
        return replace_protection(self.native,self.state,send or self.native.send,'123',100,200,'97000','111000',instrument=rules(),authorized=True)
    def test_new_pair_before_old_cancel_and_restart_no_writes(self):
        self.replace();sent=list(self.native.sent);self.replace()
        self.assertEqual(self.native.sent,sent)
        self.assertEqual([m for m,_,_ in sent],['POST','POST','POST','POST','DELETE','DELETE'])
    def test_new_rejection_retains_old_and_never_retries(self):
        calls=[]
        def reject(*a):calls.append(a);raise RuntimeError('duplicate close-all rejected')
        for _ in range(2):
            with self.assertRaises(Unknown):self.replace(reject)
        self.assertEqual(len(calls),1)
        self.assertTrue(all(o['algoStatus']=='NEW' for o in self.native.orders.values()))
    def test_cancel_timeout_after_acceptance_settles_by_query(self):
        def send(*a):
            self.native.send(*a)
            if a[0]=='DELETE':raise TimeoutError()
        self.replace(send)
        self.assertEqual(len(self.native.sent),6)
    def test_unknown_cancel_is_not_repeated(self):
        calls=[]
        def send(*a):
            if a[0]=='DELETE':calls.append(a);raise TimeoutError()
            self.native.send(*a)
        for _ in range(2):
            with self.assertRaises(Unknown):self.replace(send)
        self.assertEqual(len(calls),1)
        self.native.orders[calls[0][2]['clientAlgoId']]['algoStatus']='CANCELED'
        self.replace()
    def test_canceled_parent_working_child_blocks(self):
        identity=client_id(self.state.identity,100,'STOP_MARKET')
        self.native.orders[identity]['algoStatus']='CANCELED'
        self.native.children[identity]=dict(status='PARTIALLY_FILLED',origQty='.003',executedQty='.001')
        with self.assertRaises(Unknown):self.replace()
        self.assertFalse(any(m=='DELETE' for m,_,_ in self.native.sent))
    def test_partial_exposure_restart_keeps_existing_protections(self):
        def send(*a):
            self.native.send(*a)
            if a[0]=='DELETE':self.native.q='.002'
        with self.assertRaises(Unknown):self.replace(send)
        count=len(self.native.sent)
        with self.assertRaises(Unknown):self.replace()
        self.assertEqual(len(self.native.sent),count)
    def test_flat_after_cancel_cleanup_does_not_reopen(self):
        def send(*a):
            self.native.send(*a)
            if a[0]=='DELETE':self.native.q='0'
        with self.assertRaises(Unknown):self.replace(send)
        self.replace()
        self.assertTrue(all(o['algoStatus']=='CANCELED' for o in self.native.orders.values()))
    def test_lost_ownership_blocks_without_writes(self):
        self.state.db.execute('DELETE FROM intents');self.state.db.commit();count=len(self.native.sent)
        with self.assertRaises(Blocked):self.replace()
        self.assertEqual(len(self.native.sent),count)
    def test_restart_resumes_accepted_cancel_without_resend(self):
        calls=[]
        def send(*a):
            if a[0]=='DELETE':calls.append(a);raise TimeoutError()
            self.native.send(*a)
        with self.assertRaises(Unknown):self.replace(send)
        self.state.__exit__()
        self.state=State(self.tmp.name,'binance:BTCUSDT:live:123').__enter__()
        target=calls[0][2]['clientAlgoId'];self.native.orders[target]['algoStatus']='CANCELED'
        self.replace()
        self.assertEqual(len(calls),1)
        self.assertTrue(self.state.get('binance_protection_replacement')['done'])
    def test_changed_replacement_request_cannot_bypass_pending_operation(self):
        with self.assertRaises(Unknown):self.replace(lambda *a: (_ for _ in ()).throw(TimeoutError()))
        n=len(self.native.sent)
        with self.assertRaises(Unknown):
            replace_protection(self.native,self.state,self.native.send,'123',100,201,'98000','112000',instrument=rules(),authorized=True)
        self.assertEqual(n,len(self.native.sent))
    def test_replacement_default_read_only(self):
        n=len(self.native.sent)
        with self.assertRaises(Blocked):
            replace_protection(self.native,self.state,self.native.send,'123',100,200,'97000','111000',instrument=rules())
        self.assertEqual(n,len(self.native.sent))

    def test_authorized_reduce_remains_available_with_unknown_owned_cancel(self):
        from coinquant.binance_safety import reduce_existing
        def send(*a):
            if a[0]=='DELETE':raise TimeoutError()
            return self.native.send(*a)
        with self.assertRaises(Unknown):self.replace(send)
        result=reduce_existing(self.native,self.state,self.native.send,'123',300,'.003',instrument=rules(),authorized=True)
        self.assertEqual(result['quantity_btc'],'0')
        self.assertTrue(any(x['kind']=='binance_algo_cancel' for x in self.state.pending()))
    def test_short_replacement_uses_buy_close_all_without_quantity(self):
        self.state.db.execute('DELETE FROM intents');self.state.db.commit();self.native.orders={};self.native.sent=[]
        self.native.q='-.003';snapshot=self.native.snapshot
        self.native.snapshot=lambda uid:dict(snapshot(uid),native_liquidation_price='110000')
        protect_existing(self.native,self.state,self.native.send,'123',100,'105000','90000',instrument=rules(),authorized=True)
        replace_protection(self.native,self.state,self.native.send,'123',100,200,'103000','89000',instrument=rules(),authorized=True)
        for method,_,p in self.native.sent:
            if method=='POST':
                self.assertEqual(p['side'],'BUY');self.assertEqual(p['closePosition'],'true');self.assertNotIn('quantity',p)
    def test_price_already_through_new_stop_keeps_old_protection(self):
        n=len(self.native.sent)
        with self.assertRaises(Blocked):
            replace_protection(self.native,self.state,self.native.send,'123',100,200,'101000','111000',instrument=rules(),authorized=True)
        self.assertEqual(len(self.native.sent),n)
        self.assertTrue(all(o['algoStatus']=='NEW' for o in self.native.orders.values()))
