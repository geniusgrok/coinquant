import unittest
from research.binance_readonly import BinanceReadOnly
from pancakequant.types import Unknown


class IntentRead(unittest.TestCase):
    def test_canceled_parent_still_queries_partially_filled_child(self):
        parent = dict(symbol='BTCUSDT',clientAlgoId='pq-1',actualOrderId='42',
                      algoStatus='CANCELED',side='BUY',positionSide='BOTH')
        child = dict(symbol='BTCUSDT',orderId=42,status='PARTIALLY_FILLED',
                     executedQty='0.001',side='BUY',positionSide='BOTH')
        reader=BinanceReadOnly();calls=[]
        def get(path, params):
            calls.append((path,params))
            return parent if path.endswith('algoOrder') else child
        reader.get=get
        observed=reader.query_intent('pq-1',conditional=True)
        self.assertEqual(observed['child']['executedQty'],'0.001')
        self.assertFalse(observed['resubmit_authorized'])
        self.assertEqual(calls[1][1],{'symbol':'BTCUSDT','orderId':42})
        child['orderId']=43
        with self.assertRaises(Unknown):reader.query_intent('pq-1',conditional=True)

    def test_missing_history_never_becomes_retry_permission(self):
        reader=BinanceReadOnly()
        def get(*args):raise Unknown('history unavailable')
        reader.get=get
        with self.assertRaises(Unknown):reader.query_intent('pq-1')
        reader.get=lambda *args:dict(symbol='BTCUSDT',clientOrderId='foreign')
        with self.assertRaises(Unknown):reader.query_intent('pq-1')
