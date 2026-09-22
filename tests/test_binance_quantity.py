from decimal import Decimal as D
import unittest
from pancakequant.binance import market_quantity
from pancakequant.types import Unknown,Blocked

def instrument():
    return {'symbol':'BTCUSDT','filters':[
        {'filterType':'LOT_SIZE','stepSize':'.001','minQty':'.001','maxQty':'1000'},
        {'filterType':'MARKET_LOT_SIZE','stepSize':'.001','minQty':'.001','maxQty':'120'},
        {'filterType':'MIN_NOTIONAL','notional':'50'}]}

class QuantityTests(unittest.TestCase):
    def test_preserves_risk_budget_and_applies_minimum_and_market_cap(self):
        self.assertEqual(market_quantity('.0094','8000',instrument()),D('.009'))
        self.assertEqual(market_quantity('.0049','10000',instrument()),0)
        self.assertEqual(market_quantity('121','10000',instrument()),120)
        self.assertEqual(market_quantity('.0009','100000',instrument()),0)
    def test_common_increment_and_incomplete_filters(self):
        i=instrument();i['filters'][0]['stepSize']='.002';i['filters'][1]['stepSize']='.003'
        self.assertEqual(market_quantity('.019','10000',i),D('.018'))
        i['filters'].pop()
        with self.assertRaises(Unknown):market_quantity('.01','10000',i)
        with self.assertRaises(Blocked):market_quantity('-.01','10000',instrument())
