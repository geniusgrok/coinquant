import unittest
from decimal import Decimal as D
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
            r=query(identity,conditional);child=self.native.children.get(identity)
            if child is not None:
                parent=r['parent']
                r['child']=dict(symbol=parent['symbol'],side=parent['side'],positionSide=parent['positionSide'],
                                type='MARKET',orderId=1000+parent['algoId'],**child)
                r['parent']=dict(parent,actualOrderId=str(r['child']['orderId']))
            return r
        self.native.query_intent=observe
    def tearDown(self):
        self.state.__exit__();self.tmp.cleanup()
    def replace(self,send=None,**kwargs):
        return replace_protection(self.native,self.state,send or self.native.send,'123',100,200,'97000','111000',instrument=rules(),authorized=True,**kwargs)
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
    def test_canceled_parent_working_child_blocks(self):
        identity=client_id(self.state.identity,100,'STOP_MARKET')
        self.native.orders[identity]['algoStatus']='CANCELED'
        self.native.children[identity]=dict(status='PARTIALLY_FILLED',origQty='.003',executedQty='.001')
        with self.assertRaises(Unknown):self.replace()
        self.assertFalse(any(m=='DELETE' for m,_,_ in self.native.sent))
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

    def test_manual_same_size_reopen_before_retirement_keeps_old_stop(self):
        owner=self.native.snapshot('123');query=self.native.query_intent
        old_stop=client_id(self.state.identity,100,'STOP_MARKET')
        def observe(identity,conditional=False):
            if identity==old_stop:self.native.cursor+=2
            return query(identity,conditional)
        self.native.query_intent=observe
        with self.assertRaises(Unknown):self.replace(expected_owner=owner)
        self.assertFalse(any(method=='DELETE' for method,_,_ in self.native.sent))
        self.assertEqual(self.native.orders[old_stop]['algoStatus'],'NEW')


class PartialFillReplacementTests(unittest.TestCase):
    setUp=ReplacementTests.setUp;tearDown=ReplacementTests.tearDown;replace=ReplacementTests.replace
    def spend(self,identity,filled='.001'):
        self.native.orders[identity]['algoStatus']='FINISHED'
        self.native.children[identity]=dict(status='FILLED',origQty=filled,executedQty=filled)
        self.native.q=str(D('.003')-D(filled))

    def interrupted(self,spent):
        state={'done':False}
        def send(method,path,p):
            if method=='DELETE' and not state['done']:
                state['done']=True;self.native.send(method,path,p);self.spend(spent)
            else:self.native.send(method,path,p)
        with self.assertRaises(Unknown):self.replace(send)

    def test_old_leg_filled_keeps_healthy_new_pair_and_finishes(self):
        old_stop=client_id(self.state.identity,100,'STOP_MARKET')
        new_ids=[client_id(self.state.identity,200,k) for k in ('STOP_MARKET','TAKE_PROFIT_MARKET')]
        self.interrupted(old_stop)
        self.replace()
        journal=self.state.get('binance_protection_replacement')
        self.assertTrue(journal['done']);self.assertEqual(journal['epoch'],200)
        self.assertEqual([self.native.orders[i]['algoStatus'] for i in new_ids],['NEW','NEW'])
        old_take=client_id(self.state.identity,100,'TAKE_PROFIT_MARKET')
        self.assertEqual(self.native.orders[old_take]['algoStatus'],'CANCELED')
        self.assertEqual(sum(1 for o in self.native.orders.values() if o['algoStatus']=='NEW'),2)

    def test_spent_new_leg_rotates_to_fresh_generation_without_reusing_spent_id(self):
        new_stop=client_id(self.state.identity,200,'STOP_MARKET')
        self.interrupted(new_stop)
        before=set(self.native.orders)
        self.replace()
        journal=self.state.get('binance_protection_replacement')
        self.assertTrue(journal['done']);self.assertNotEqual(journal['epoch'],200)
        fresh=[i for i in self.native.orders if i not in before]
        self.assertEqual(len(fresh),2)
        self.assertTrue(all(self.native.orders[i]['algoStatus']=='NEW' for i in fresh))
        self.assertEqual(self.native.orders[new_stop]['algoStatus'],'FINISHED')
        self.assertEqual(sum(1 for o in self.native.orders.values() if o['algoStatus']=='NEW'),2)
        sent=len(self.native.sent);self.replace()
        self.assertEqual(len(self.native.sent),sent)

    def test_unexplained_or_oversized_change_stays_unknown(self):
        old_stop=client_id(self.state.identity,100,'STOP_MARKET')
        self.interrupted(old_stop)
        self.native.q='.001'
        n=len(self.native.sent)
        with self.assertRaises(Unknown):self.replace()
        self.native.q='.004'
        with self.assertRaises(Unknown):self.replace()
        self.assertEqual(len(self.native.sent),n)

    def test_child_still_working_stays_unknown(self):
        old_stop=client_id(self.state.identity,100,'STOP_MARKET')
        self.interrupted(old_stop)
        self.native.children[old_stop]=dict(status='PARTIALLY_FILLED',origQty='.001',executedQty='.0005')
        with self.assertRaises(Unknown):self.replace()

    def test_flat_after_partial_fill_cleans_up_without_reopening(self):
        old_stop=client_id(self.state.identity,100,'STOP_MARKET')
        self.interrupted(old_stop)
        self.native.q='0'
        self.replace()
        self.assertTrue(self.state.get('binance_protection_replacement')['done'])
        self.assertFalse(any(o['algoStatus']=='NEW' for o in self.native.orders.values()))

    def zero_fill_replacement(self,parent_status,child):
        new_stop=client_id(self.state.identity,200,'STOP_MARKET');fired=False
        def send(method,path,p):
            nonlocal fired
            self.native.send(method,path,p)
            if method=='DELETE' and not fired:
                fired=True
                self.native.orders[new_stop]['algoStatus']=parent_status
                if child is not None:self.native.children[new_stop]=child
        with self.assertRaises(Unknown):self.replace(send)
        before=set(self.native.orders);self.replace()
        journal=self.state.get('binance_protection_replacement')
        self.assertTrue(journal['done']);self.assertNotEqual(journal['epoch'],200)
        fresh=[identity for identity in self.native.orders if identity not in before]
        self.assertEqual(len(fresh),2)
        self.assertTrue(all(self.native.orders[identity]['algoStatus']=='NEW' for identity in fresh))
        self.assertEqual(self.native.q,'.003')
        self.assertEqual(sum(o['algoStatus']=='NEW' for o in self.native.orders.values()),2)
        writes=len(self.native.sent);self.replace();self.assertEqual(len(self.native.sent),writes)

    def test_zero_fill_expired_new_stop_rotates_its_generation(self):
        self.zero_fill_replacement('FINISHED',dict(status='EXPIRED',origQty='.003',executedQty='0'))

    def test_rejected_new_stop_without_child_rotates_its_generation(self):
        self.zero_fill_replacement('REJECTED',None)

    def test_unfilled_working_new_child_never_rotates_or_resends(self):
        new_stop=client_id(self.state.identity,200,'STOP_MARKET');fired=False
        def send(method,path,p):
            nonlocal fired
            self.native.send(method,path,p)
            if method=='DELETE' and not fired:
                fired=True
                self.native.orders[new_stop]['algoStatus']='TRIGGERED'
                self.native.children[new_stop]=dict(status='NEW',origQty='.003',executedQty='0')
        with self.assertRaises(Unknown):self.replace(send)
        writes=len(self.native.sent);identities=set(self.native.orders)
        with self.assertRaises(Unknown):self.replace()
        self.assertEqual(len(self.native.sent),writes)
        self.assertEqual(set(self.native.orders),identities)
