"""Native adapter loss boundaries; deterministic responses, no account calls."""
import json
import tempfile
from copy import deepcopy
from decimal import Decimal as D
from unittest import TestCase

from coinquant.binance import conditional_is_terminal
from coinquant.binance_safety import add_margin, protect_existing, settled_protection
from coinquant.state import State, client_id
from coinquant.types import Blocked, Unknown
from tests.session_venue import Venue
from tests.test_binance_safety import Native, rules
from tests.test_margin_intents import History


class ParentEvidenceTests(TestCase):
    def test_childless_cancellation_with_fill_metadata_is_not_terminal(self):
        for status in ('CANCELED','EXPIRED','REJECTED','TRIGGERED','FINISHED'):
            for field,value in (('actualQty','.001'),('actualPrice','100000')):
                with self.subTest(status=status,field=field):
                    parent=dict(algoStatus=status,actualOrderId='',**{field:value})
                    with self.assertRaisesRegex(Unknown,'lacks its native child'):
                        conditional_is_terminal(dict(parent=parent,child=None))

    def test_unfilled_cancellation_and_trigger_rejection_can_still_settle(self):
        for status in ('CANCELED','EXPIRED','REJECTED'):
            for fields in ({},{'actualQty':'0','actualPrice':'0.00000','triggerTime':1}):
                with self.subTest(status=status,fields=fields):
                    self.assertTrue(conditional_is_terminal(dict(
                        parent=dict(algoStatus=status,actualOrderId='',**fields),child=None)))
        for status in ('TRIGGERED','FINISHED'):
            self.assertFalse(conditional_is_terminal(dict(parent=dict(algoStatus=status),child=None)))

    def test_published_terminal_child_settles_the_execution(self):
        parent=dict(algoStatus='CANCELED',actualOrderId='41',actualQty='.001',actualPrice='100000')
        child=dict(status='FILLED',origQty='.001',executedQty='.001')
        self.assertTrue(conditional_is_terminal(dict(parent=parent,child=child)))


class ParentRecoveryTests(TestCase):
    def poisoned_cache(self,state):
        venue=Venue();identity='cq-loss-poisoned-stop'
        payload=dict(symbol='BTCUSDT',side='SELL',positionSide='BOTH',algoType='CONDITIONAL',
                     type='STOP_MARKET',triggerPrice='95000',closePosition='true',
                     workingType='MARK_PRICE',priceProtect='false',clientAlgoId=identity)
        state.prepare(identity,'binance_algo',payload)
        venue.send('POST','/fapi/v1/algoOrder',payload)
        venue.algos[identity].update(algoStatus='CANCELED',actualOrderId='',actualQty='.001')
        observed=deepcopy(dict(parent=venue.algos[identity],child=None))
        for key in ('terminal_native_orders','settled_protection'):state.set(key,{identity:observed})
        return venue,identity,observed

    def publish_child(self,venue,identity,*,status='FILLED'):
        venue.orders['native-child']=dict(symbol='BTCUSDT',side='SELL',positionSide='BOTH',
            type='MARKET',clientOrderId='native-child',orderId=41,status=status,
            reduceOnly=True,origQty='.001',executedQty='.001' if status=='FILLED' else '.0005')
        venue.algos[identity]['actualOrderId']='41'

    def test_incomplete_legacy_cache_refreshes_both_archives_after_a_terminal_child(self):
        with tempfile.TemporaryDirectory() as directory, State(directory,'binance:BTCUSDT:live:123') as state:
            venue,identity,_=self.poisoned_cache(state)
            self.publish_child(venue,identity)
            self.assertTrue(settled_protection(venue,state,identity))
            for key in ('terminal_native_orders','settled_protection'):
                self.assertEqual(state.get(key)[identity]['child']['orderId'],41)

    def test_incomplete_legacy_cache_stays_intact_until_its_child_is_terminal(self):
        for case in ('still_missing','working_child','fill_field_disappeared'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as directory, State(directory,'binance:BTCUSDT:live:123') as state:
                venue,identity,original=self.poisoned_cache(state)
                if case=='working_child':self.publish_child(venue,identity,status='PARTIALLY_FILLED')
                elif case=='fill_field_disappeared':venue.algos[identity].pop('actualQty')
                with self.assertRaises(Unknown):settled_protection(venue,state,identity)
                for key in ('terminal_native_orders','settled_protection'):
                    self.assertEqual(state.get(key)[identity],original)

    def test_incomplete_legacy_cache_cannot_change_its_native_identity(self):
        with tempfile.TemporaryDirectory() as directory, State(directory,'binance:BTCUSDT:live:123') as state:
            venue,identity,original=self.poisoned_cache(state)
            self.publish_child(venue,identity)
            venue.algos[identity]['algoId']+=1
            with self.assertRaisesRegex(Unknown,'changed its native identity'):
                settled_protection(venue,state,identity)
            for key in ('terminal_native_orders','settled_protection'):
                self.assertEqual(state.get(key)[identity],original)

    def test_cached_terminal_protection_must_still_match_its_durable_scope(self):
        with tempfile.TemporaryDirectory() as directory, State(directory,'binance:BTCUSDT:live:123') as state:
            venue=Venue();identity='cq-loss-cached-stop'
            payload=dict(symbol='BTCUSDT',side='SELL',positionSide='BOTH',algoType='CONDITIONAL',
                         type='STOP_MARKET',triggerPrice='95000',closePosition='true',
                         workingType='MARK_PRICE',priceProtect='false',clientAlgoId=identity)
            state.prepare(identity,'binance_algo',payload)
            venue.send('POST','/fapi/v1/algoOrder',payload)
            observed=dict(parent=dict(venue.algos[identity],algoStatus='CANCELED',side='BUY'),child=None)
            for key in ('terminal_native_orders','settled_protection'):
                with self.subTest(cache=key):
                    state.set('terminal_native_orders',{});state.set('settled_protection',{})
                    state.set(key,{identity:observed})
                    with self.assertRaisesRegex(Unknown,'owned order scope changed'):
                        settled_protection(venue,state,identity)

    def test_incomplete_parent_is_not_frozen_before_the_child_is_published(self):
        with tempfile.TemporaryDirectory() as directory, State(directory,'binance:BTCUSDT:live:123') as state:
            venue=Venue();identity='cq-loss-stop'
            payload=dict(symbol='BTCUSDT',side='SELL',positionSide='BOTH',algoType='CONDITIONAL',
                         type='STOP_MARKET',triggerPrice='95000',closePosition='true',
                         workingType='MARK_PRICE',priceProtect='false',clientAlgoId=identity)
            state.prepare(identity,'binance_algo',payload)
            venue.send('POST','/fapi/v1/algoOrder',payload)
            venue.algos[identity].update(algoStatus='CANCELED',actualOrderId='',actualQty='.001')
            self.assertEqual(venue.recover_pending(state),dict(resolved=0,pending=1))
            self.assertNotIn(identity,state.get('terminal_native_orders') or {})

            venue.orders['native-child']=dict(symbol='BTCUSDT',side='SELL',positionSide='BOTH',
                type='MARKET',clientOrderId='native-child',orderId=41,status='FILLED',
                reduceOnly=True,origQty='.001',executedQty='.001')
            venue.algos[identity]['actualOrderId']='41'
            self.assertEqual(venue.recover_pending(state),dict(resolved=1,pending=0))
            self.assertEqual(state.get('terminal_native_orders')[identity]['child']['orderId'],41)


class ProtectionConfirmationTests(TestCase):
    def test_pending_native_new_preserves_first_aligned_readback_and_identity(self):
        with tempfile.TemporaryDirectory() as directory, State(directory,'binance:BTCUSDT:live:123') as state:
            reader=Venue();reader.time_offset_ms=250
            now=[reader.clock()];reader.clock=lambda:now[0]
            identity='cq-loss-pending-stop'
            payload=dict(symbol='BTCUSDT',side='SELL',positionSide='BOTH',algoType='CONDITIONAL',
                         type='STOP_MARKET',triggerPrice='95000',closePosition='true',
                         workingType='MARK_PRICE',priceProtect='false',clientAlgoId=identity)
            state.prepare(identity,'binance_algo',payload)
            reader.send('POST','/fapi/v1/algoOrder',payload)
            self.assertEqual(reader.recover_pending(state),dict(resolved=1,pending=0))
            result=json.loads(state.db.execute('SELECT result FROM intents WHERE id=?',(identity,)).fetchone()[0])
            self.assertEqual(result['first_confirmed_at_ms'],int(now[0]*1000)+250)
            state.finish(identity,'unknown',result);now[0]+=60
            self.assertEqual(reader.recover_pending(state),dict(resolved=1,pending=0))
            self.assertEqual(json.loads(state.db.execute('SELECT result FROM intents WHERE id=?',(identity,)).fetchone()[0]),result)
            state.finish(identity,'unknown',result);reader.algos[identity]['algoId']+=100
            self.assertEqual(reader.recover_pending(state),dict(resolved=0,pending=1))
            self.assertEqual(json.loads(state.db.execute('SELECT result FROM intents WHERE id=?',(identity,)).fetchone()[0]),result)
            self.assertEqual(len(reader.sent),1)

    def test_native_confirmation_time_survives_restart_and_identity_cannot_change(self):
        with tempfile.TemporaryDirectory() as directory:
            reader=Native();now=[reader.clock()];reader.clock=lambda:now[0];reader.time_offset_ms=250
            expected=int(now[0]*1000)+250
            with State(directory,'binance:BTCUSDT:live:123') as state:
                protect_existing(reader,state,reader.send,'123',100,'95000','110000',instrument=rules(),authorized=True)
                identities=[client_id(state.identity,100,kind) for kind in ('STOP_MARKET','TAKE_PROFIT_MARKET')]
                for identity in identities:
                    result=json.loads(state.db.execute('SELECT result FROM intents WHERE id=?',(identity,)).fetchone()[0])
                    self.assertEqual(result['first_confirmed_at_ms'],expected)
            now[0]+=60
            with State(directory,'binance:BTCUSDT:live:123') as state:
                protect_existing(reader,state,reader.send,'123',100,'95000','110000',instrument=rules(),authorized=True)
                self.assertEqual(len(reader.sent),2)
                for identity in identities:
                    result=json.loads(state.db.execute('SELECT result FROM intents WHERE id=?',(identity,)).fetchone()[0])
                    self.assertEqual(result['first_confirmed_at_ms'],expected)
                reader.orders[identities[0]]['algoId']+=100
                with self.assertRaisesRegex(Unknown,'changed its native identity'):
                    protect_existing(reader,state,reader.send,'123',100,'95000','110000',instrument=rules(),authorized=True)
                self.assertEqual(len(reader.sent),2)


class MarginRecoveryTests(TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.state=State(self.tmp.name,'binance:BTCUSDT:live:123').__enter__()
        self.addCleanup(self.state.__exit__)
        self.reader=History();self.now=self.reader.clock();self.reader.clock=lambda:self.now
        self.attempts=[]

    def add(self,target,*,epoch=100,send=None):
        return add_margin(self.reader,self.state,send or self.reader.send,'123',epoch,target,
                          instrument=rules(),authorized=True)

    def lose_answer(self,target):
        def lost(*args):self.attempts.append(args);raise TimeoutError()
        with self.assertRaises(Unknown):self.add(target,send=lost)
        return self.state.pending()[0]

    def manual_add(self):
        self.reader.send('POST','/fapi/v1/positionMargin',
                         dict(symbol='BTCUSDT',positionSide='BOTH',type=1,amount='10'))

    def assert_unresolved_without_another_transfer(self):
        self.assertEqual(self.reader.recover_pending(self.state),dict(resolved=0,pending=1))
        writes=len(self.reader.sent)
        with self.assertRaises(Unknown):self.add(str(D(self.reader.margin)+10),epoch=200)
        self.assertEqual(len(self.reader.sent),writes)
        self.assertEqual(len(self.attempts),1)

    def test_a_presend_manual_equal_amount_cannot_confirm_the_lost_request(self):
        self.manual_add();self.now+=10
        intent=self.lose_answer('50')
        result=json.loads(self.state.db.execute('SELECT result FROM intents WHERE id=?',(intent['id'],)).fetchone()[0])
        self.assertEqual(self.reader.history[0]['amount'],intent['payload']['amount'])
        self.assertLess(self.reader.history[0]['time'],result['prepared_at_ms'])
        self.assert_unresolved_without_another_transfer()

    def test_a_postsend_manual_equal_amount_cannot_confirm_the_lost_request(self):
        intent=self.lose_answer('40');self.now+=1;self.manual_add()
        result=json.loads(self.state.db.execute('SELECT result FROM intents WHERE id=?',(intent['id'],)).fetchone()[0])
        self.assertEqual(self.reader.history[0]['amount'],intent['payload']['amount'])
        self.assertGreater(self.reader.history[0]['time'],result['prepared_at_ms'])
        self.assert_unresolved_without_another_transfer()

    def test_legacy_history_only_confirmation_reopens_without_erasing_evidence(self):
        intent=self.lose_answer('40');self.now+=1;self.manual_add()
        original=json.loads(self.state.db.execute('SELECT result FROM intents WHERE id=?',(intent['id'],)).fetchone()[0])
        original.update(amount='10',history_time=self.reader.history[0]['time'])
        self.state.finish(intent['id'],'confirmed',original)
        self.assertEqual(self.state.pending(),[])
        self.assert_unresolved_without_another_transfer()
        status,raw=self.state.db.execute('SELECT status,result FROM intents WHERE id=?',(intent['id'],)).fetchone()
        self.assertEqual(status,'unknown')
        self.assertEqual(json.loads(raw),{**original,'legacy_margin_history_reopened':True})

    def test_a_real_ack_is_not_reopened_by_legacy_history_metadata(self):
        self.add('40')
        identity,raw=self.state.db.execute("SELECT id,result FROM intents WHERE kind='binance_margin'").fetchone()
        original=json.loads(raw);original['history_time']=self.reader.history[0]['time']
        self.assertIs(original['acknowledged'],True)
        self.state.finish(identity,'confirmed',original)
        self.assertEqual(self.reader.recover_pending(self.state),dict(resolved=0,pending=0))
        self.assertEqual(json.loads(self.state.db.execute('SELECT result FROM intents WHERE id=?',(identity,)).fetchone()[0]),original)
        self.add('50',epoch=200)
        self.assertEqual(len(self.reader.sent),2)
        self.assertEqual(self.state.pending(),[])


class MarginCapitalTests(TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state=State(self.tmp.name,'binance:BTCUSDT:live:123').__enter__()
        self.addCleanup(self.state.__exit__)
        self.venue=Venue()
        self.venue.q=D('.01');self.venue.entry=D('100000')
        self.venue.wallet=D('999.5');self.venue.margin=D('50')

    def add(self,target,**kwargs):
        return add_margin(self.venue,self.state,self.venue.send,'123',100,target,
                          instrument=self.venue.rules,authorized=True,**kwargs)

    def assert_no_transfer(self):
        self.assertEqual(self.venue.sent,[])
        self.assertEqual(self.state.db.execute('SELECT count(*) FROM intents').fetchone()[0],0)

    def test_current_mark_limits_a_stale_but_still_owned_margin_plan(self):
        old=self.venue.snapshot('123')
        self.assertEqual(D(old['equity_usdt']),D('999.5'))
        self.venue.mark=D('99700')
        # A lower mark does not by itself forbid funding the strategy stop.
        # The transfer is still limited by current capital, not by a 25% slice.
        after=self.add('249.393',snapshot=old,expected_owner=old)
        self.assertEqual(D(after['isolated_wallet_usdt']),D('249.393'))

    def test_exact_current_cap_can_be_funded_and_read_back(self):
        self.venue.mark=D('99700')
        after=self.add('249.125')
        self.assertEqual(D(after['isolated_wallet_usdt']),D('249.125'))
        self.assertEqual(self.venue.sent[0][2]['amount'],'199.125')
        self.assertEqual(self.state.pending(),[])

    def test_unrealized_gains_do_not_enlarge_the_wallet_cap(self):
        self.venue.mark=D('120000')
        with self.assertRaisesRegex(Blocked,'funded from existing wallet'):self.add('1000')
        self.assert_no_transfer()
        after=self.add('260')
        self.assertEqual(D(after['isolated_wallet_usdt']),D('260'))

    def test_the_configured_capital_ceiling_applies_to_actual_margin(self):
        self.venue.capital_limit=D('100');self.venue.margin=D('10')
        with self.assertRaisesRegex(Blocked,'current capital'):self.add('100.00000001')
        self.assert_no_transfer()
        after=self.add('100')
        self.assertEqual(D(after['isolated_wallet_usdt']),D('100'))

    def test_rounding_cannot_push_a_target_below_the_raw_cap_over_it(self):
        self.venue.wallet=D('1000.00000001')
        with self.assertRaisesRegex(Blocked,'funded from existing wallet'):self.add('1000.00000002')
        self.assert_no_transfer()
        after=self.add('250')
        self.assertEqual(D(after['isolated_wallet_usdt']),D('250'))

    def test_nonpositive_marked_capital_cannot_fund_a_transfer(self):
        self.venue.wallet=D('5');self.venue.margin=D('1');self.venue.mark=D('99400')
        with self.assertRaisesRegex(Blocked,'positive current capital'):self.add('2')
        self.assert_no_transfer()
