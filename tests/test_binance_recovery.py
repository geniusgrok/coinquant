import tempfile
import unittest
from coinquant.state import State
from coinquant.binance import Binance
from coinquant.types import Unknown

class RecoveryTests(unittest.TestCase):
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

    def test_payload_mismatch_and_legacy_intent_stay_unknown(self):
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
