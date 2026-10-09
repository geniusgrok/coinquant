"""The first IOC's native fills can shorten protection, never replace ownership."""
from copy import deepcopy
from decimal import Decimal as D
import tempfile
from unittest import TestCase

from coinquant.binance_safety import protect_existing
from coinquant.lifecycle import Lifecycle
from coinquant.state import State, client_id
from coinquant.types import Unknown
from tests.session_venue import Venue
from tests.test_session_ownership import Latent


class FastEntryTests(TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state=State(self.tmp.name,'binance:BTCUSDT:live:123')
        self.state.__enter__()
        self.addCleanup(self.state.__exit__,None,None,None)
        self.reader=Venue()
        self.identity=client_id(self.state.identity,1,'entry')

    def enter(self, *, fraction='1', side='BUY', quantity='.004', price='100000'):
        self.reader.fraction=D(fraction)
        self.flat=self.reader.snapshot('123')
        payload=dict(symbol='BTCUSDT',positionSide='BOTH',side=side,type='LIMIT',timeInForce='IOC',
                     quantity=quantity,price=price,newClientOrderId=self.identity,newOrderRespType='RESULT')
        self.state.prepare(self.identity,'binance_order',payload,campaign=1,flat_snapshot=self.flat)
        self.reader.send('POST','/fapi/v1/order',payload)
        self.reader.recover_pending(self.state)

    def observe(self):
        return self.reader.entry_snapshot(self.state,'123',self.identity,flat_snapshot=self.flat)

    def test_one_native_round_proves_full_and_terminal_partial_fills(self):
        self.enter()
        before=len(self.reader.calls)
        snapshot,parent=self.observe()
        calls=self.reader.calls[before:]
        self.assertEqual([path for _,path,_ in calls],['/fapi/v3/account','/fapi/v3/positionRisk',
                         '/fapi/v1/openOrders','/fapi/v1/openAlgoOrders','/fapi/v1/premiumIndex','/fapi/v1/userTrades'])
        self.assertEqual(calls[-1][2],dict(symbol='BTCUSDT',startTime=self.flat['observed_at_ms']-15000,
                                         endTime=self.reader.now,limit=1000))
        self.assertEqual(D(snapshot['quantity_btc']),D('.004'))
        self.assertEqual(parent['status'],'FILLED')
        self.assertEqual(snapshot['last_fill_id'],1)
        self.assertTrue(snapshot['recent_fill_window_complete'])
        self.assertFalse(snapshot['recovery_history_complete'])
        self.assertFalse(snapshot['native_full_position_protected'])

    def test_terminal_partial_short_is_not_confused_with_working_remainder(self):
        self.enter(fraction='.5',side='SELL')
        snapshot,parent=self.observe()
        self.assertEqual(parent['status'],'EXPIRED')
        self.assertEqual(D(snapshot['quantity_btc']),D('-.002'))
        self.assertEqual(snapshot['possible_entry_remainders'],0)

    def test_existing_flat_cursor_excludes_preceding_closed_trades(self):
        for oid,side,reduce in ((70,'BUY',False),(71,'SELL',True)):
            self.reader.fill(dict(orderId=oid,side=side,reduceOnly=reduce,price='100000',executedQty='0'),D('.001'))
        self.enter()
        before=len(self.reader.calls)
        snapshot,_=self.observe()
        self.assertEqual(self.flat['last_fill_id'],2)
        self.assertEqual(snapshot['last_fill_id'],3)
        self.assertEqual(self.reader.calls[before:][-1][2],dict(symbol='BTCUSDT',fromId=3,limit=1000))

    def test_post_ack_and_local_confirmation_are_not_terminal_native_evidence(self):
        self.enter()
        self.state.set('terminal_native_orders',{})
        before=len(self.reader.calls)
        with self.assertRaises(Unknown):self.observe()
        self.assertEqual(len(self.reader.calls),before)

    def test_working_or_changed_native_order_cannot_use_fast_protection(self):
        self.enter()
        archived=self.state.get('terminal_native_orders')
        for change in ({'status':'PARTIALLY_FILLED'},{'status':'NEW'},{'status':'REJECTED'},
                       {'origQty':'.005'},{'executedQty':'.003'},{'price':'99999'},
                       {'clientOrderId':'manual'},{'side':'SELL'},{'positionSide':'LONG'},
                       {'reduceOnly':True},{'timeInForce':'GTC'}):
            with self.subTest(change=change):
                changed=deepcopy(archived);changed[self.identity]['parent'].update(change)
                self.state.set('terminal_native_orders',changed)
                with self.assertRaises(Unknown):self.observe()
        self.state.set('terminal_native_orders',archived)

    def test_flat_and_journal_boundaries_are_required(self):
        self.enter()
        flat=deepcopy(self.flat)
        for change in ({'account_uid':'456'},{'quantity_btc':'.001'},{'entry':'100000'},
                       {'open_orders':[{}]},{'open_algos':[{}]},{'possible_entry_remainders':1},
                       {'recent_fill_window_complete':False},{'last_fill_id':None},
                       {'last_fill_id':True},{'observed_at_ms':flat['observed_at_ms']-16000}):
            with self.subTest(change=change):
                self.flat={**flat,**change}
                with self.assertRaises(Unknown):self.observe()
        self.flat=flat
        links=self.state.get('entry_campaigns')
        for change in ({'add':True},{'prepared_at':links[self.identity]['prepared_at']+1},
                       {'after_trade_id':999},{'campaign':None}):
            with self.subTest(change=change):
                self.state.set('entry_campaigns',{self.identity:{**links[self.identity],**change}})
                with self.assertRaises(Unknown):self.observe()
        self.state.set('entry_campaigns',{**links,'other':links[self.identity]})
        with self.assertRaises(Unknown):self.observe()

    def test_incomplete_or_unowned_trade_page_never_proves_the_fill(self):
        self.enter()
        get=self.reader.get;original=deepcopy(self.reader.trades)
        bad_pages=[[],original*1000,original*2,[None]]
        for change in ({'symbol':'ETHUSDT'},{'positionSide':'LONG'},{'orderId':999},{'side':'SELL'},
                       {'id':-1},{'id':True},{'qty':'.003'},{'qty':'0'},{'price':'NaN'},
                       {'price':'100001'},{'commissionAsset':'BNB'},{'commission':'-.1'},
                       {'realizedPnl':'1'},{'time':self.flat['observed_at_ms']-15001},
                       {'time':self.reader.now+1}):
            bad_pages.append([{**original[0],**change}])
        for page in bad_pages:
            with self.subTest(page=page[:2]):
                self.reader.get=lambda path,p=None:deepcopy(page) if path.endswith('/userTrades') else get(path,p)
                with self.assertRaises(Unknown):self.observe()
        self.reader.get=get

    def test_manual_round_trip_is_rejected_even_when_position_and_wallet_match(self):
        self.enter()
        wallet=self.reader.wallet
        for oid,side,reduce in ((90,'SELL',True),(91,'BUY',False)):
            self.reader.fill(dict(orderId=oid,side=side,reduceOnly=reduce,price='100000',executedQty='0'),abs(self.reader.q) or D('.004'))
        self.reader.wallet=wallet
        with self.assertRaisesRegex(Unknown,'external or invalid fill'):self.observe()
        self.assertEqual(D(self.reader.q),D('.004'))

    def test_final_safety_cursor_still_stops_a_manual_round_trip_after_fast_proof(self):
        self.enter()
        snapshot,_=self.observe();wallet=self.reader.wallet
        for oid,side,reduce in ((90,'SELL',True),(91,'BUY',False)):
            self.reader.fill(dict(orderId=oid,side=side,reduceOnly=reduce,price='100000',executedQty='0'),D('.004'))
        self.reader.wallet=wallet
        before=len(self.reader.sent)
        with self.assertRaisesRegex(Unknown,'fill ownership changed'):
            protect_existing(self.reader,self.state,self.reader.send,'123',2,'98000','110000',
                             instrument=self.reader.rules,authorized=True,snapshot=snapshot,expected_owner=snapshot)
        self.assertEqual(len(self.reader.sent),before)

    def test_position_margin_wallet_or_pending_order_changes_require_full_reconciliation(self):
        self.enter()
        get=self.reader.get
        for path,change in (('/fapi/v3/positionRisk',{'positionAmt':'.005'}),
                            ('/fapi/v3/positionRisk',{'isolatedWallet':'21'}),
                            ('/fapi/v1/openOrders',{'symbol':'ETHUSDT'}),
                            ('/fapi/v1/openAlgoOrders',{'symbol':'BTCUSDT'})):
            with self.subTest(path=path,change=change):
                def changed(key,p=None):
                    value=get(key,p)
                    if key==path:
                        if not value:value=[{}]
                        value[0].update(change)
                    return value
                self.reader.get=changed
                with self.assertRaises(Unknown):self.observe()
                self.reader.get=get
        self.reader.wallet-=D('.1')  # Funding or a transfer is not an entry commission.
        with self.assertRaisesRegex(Unknown,'do not close native'):self.observe()

    def test_price_rounding_uses_native_quote_precision_and_rejects_a_different_entry(self):
        self.enter(quantity='.003',price='100000.1')
        first=deepcopy(self.reader.trades[0]);second=deepcopy(first)
        first.update(qty='.001',price='100000',commission='.05')
        second.update(id=2,qty='.002',price='100000.1',commission='.1000001')
        self.reader.trades=[first,second]
        notional=D('.001')*D('100000')+D('.002')*D('100000.1')
        self.reader.entry=(notional/D('.003')).quantize(D('.00000001'))
        self.reader.margin=notional/20
        self.reader.wallet=D(self.flat['wallet_usdt'])-D('.1500001')
        snapshot,_=self.observe()
        self.assertEqual(D(snapshot['entry']),D('100000.06666667'))
        self.reader.entry+=D('.001')
        with self.assertRaisesRegex(Unknown,'do not close native'):self.observe()

    def test_unknown_or_expired_configuration_does_not_expand_the_fast_path(self):
        self.enter()
        config=self.reader._cycle_config
        self.reader._cycle_config=None
        with self.assertRaises(Unknown):self.observe()
        self.reader._cycle_config=config
        self.reader._config_at-=61
        with self.assertRaises(Unknown):self.observe()

    def test_ordinary_snapshot_still_uses_two_account_rounds(self):
        self.enter()
        before=len(self.reader.calls)
        self.reader.snapshot('123')
        paths=[path for _,path,_ in self.reader.calls[before:]]
        for path in ('/fapi/v3/account','/fapi/v3/positionRisk','/fapi/v1/openOrders','/fapi/v1/openAlgoOrders'):
            self.assertEqual(paths.count(path),2)

    def test_late_fill_response_cannot_return_an_expired_mark(self):
        # Both reads finish inside the real adapter's 8-second request timeout,
        # but the mark is older than 15 seconds after the fill response arrives.
        self.reader=Latent(7.9)
        self.enter()
        with self.assertRaisesRegex(Unknown,'mark expired'):self.observe()

    def guard_plan(self):
        self.state.set('entry_plan',dict(id=self.identity,epoch=3,guard_epoch=2))
        self.guard_id=client_id(self.state.identity,2,'STOP_MARKET')
        self.state.set('entry_timing',dict(entry_id=self.identity,first_stop_id=self.guard_id))
        return Lifecycle(self.reader,self.state,'123',authorized=True)

    def test_first_guard_acceptance_and_readback_are_not_overwritten_by_plan_stop(self):
        self.enter()
        snapshot,_=self.observe();engine=self.guard_plan()
        snapshot=protect_existing(self.reader,self.state,engine.send,'123',2,'98000','110000',
                                  instrument=self.reader.rules,authorized=True,snapshot=snapshot,expected_owner=snapshot)
        first=self.state.get('entry_timing')
        self.assertEqual(first['first_stop_id'],self.guard_id)
        self.assertLess(first['stop_send_attempt_at_ms'],first['stop_accepted_at_ms'])
        self.assertLessEqual(first['stop_accepted_at_ms'],first['stop_account_readback_at_ms'])
        self.reader.wait(2)
        protect_existing(self.reader,self.state,engine.send,'123',3,'99000','111000',
                         instrument=self.reader.rules,authorized=True,snapshot=snapshot,expected_owner=snapshot)
        self.assertEqual(self.state.get('entry_timing'),first)

    def test_recovered_guard_records_the_actual_readback_time_without_resending(self):
        self.enter();engine=self.guard_plan()
        payload=dict(symbol='BTCUSDT',positionSide='BOTH',side='SELL',algoType='CONDITIONAL',
                     type='STOP_MARKET',triggerPrice='98000',closePosition='true',
                     workingType='MARK_PRICE',priceProtect='false',clientAlgoId=self.guard_id)
        self.state.prepare(self.guard_id,'binance_algo',payload)
        engine.send('POST','/fapi/v1/algoOrder',payload)
        sent_at=self.state.get('entry_timing')['stop_send_attempt_at_ms']
        self.reader.wait(20)
        snapshot=self.reader.snapshot('123');resumed_at=self.reader.now
        protect_existing(self.reader,self.state,engine.send,'123',2,'98000','110000',
                         instrument=self.reader.rules,authorized=True,snapshot=snapshot,expected_owner=snapshot)
        timing=self.state.get('entry_timing')
        self.assertEqual(timing['stop_send_attempt_at_ms'],sent_at)
        self.assertEqual(timing['stop_accepted_at_ms'],resumed_at)
        self.assertGreaterEqual(timing['stop_account_readback_at_ms'],resumed_at)
        self.assertEqual(sum(p.get('clientAlgoId')==self.guard_id for _,_,p in self.reader.sent),1)

    def test_another_entrys_timing_is_not_attached_to_this_stop(self):
        self.enter();snapshot,_=self.observe();self.guard_plan()
        self.state.set('entry_timing',dict(entry_id='other-entry',first_stop_id=self.guard_id))
        protect_existing(self.reader,self.state,self.reader.send,'123',2,'98000','110000',
                         instrument=self.reader.rules,authorized=True,snapshot=snapshot,expected_owner=snapshot)
        self.assertEqual(self.state.get('entry_timing'),dict(entry_id='other-entry',first_stop_id=self.guard_id))
