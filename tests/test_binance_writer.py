import hashlib
import hmac
import json
from io import BytesIO
from urllib.error import HTTPError
from unittest import TestCase
from urllib.parse import parse_qs
from unittest.mock import Mock

from coinquant.binance import Binance
from coinquant.types import Blocked,Unknown


class WriterTests(TestCase):
    def payload(self):
        return dict(symbol='BTCUSDT',positionSide='BOTH',side='BUY',type='LIMIT',timeInForce='IOC',quantity='.001',price='100000',newClientOrderId='cq-test')
    def test_signed_order_is_sent_once_without_account_setting_capability(self):
        opener=Mock();opener.open.return_value=BytesIO(b'{"orderId":1}')
        venue=Binance(key='fixture-key',secret='fixture-secret',opener=opener,clock=lambda:1000,authorize_writes=True)
        venue.send('POST','/fapi/v1/order',self.payload())
        request=opener.open.call_args.args[0];body=request.data.decode()
        signed,signature=body.rsplit('&signature=',1)
        self.assertEqual(signature,hmac.new(b'fixture-secret',signed.encode(),hashlib.sha256).hexdigest())
        self.assertEqual(request.method,'POST');self.assertEqual(request.full_url,'https://fapi.binance.com/fapi/v1/order')
        self.assertEqual(parse_qs(signed)['timestamp'],['1000000'])
        self.assertEqual(opener.open.call_count,1)
        with self.assertRaises(Blocked):venue.send('POST','/fapi/v1/leverage',{'symbol':'BTCUSDT','leverage':20})
        self.assertEqual(opener.open.call_count,1)
    def test_default_read_only_and_unbounded_entries_rejected_before_network(self):
        opener=Mock();venue=Binance(opener=opener)
        with self.assertRaises(Blocked):venue.send('POST','/fapi/v1/order',self.payload())
        venue.authorize_writes=True
        for change in ({'type':'MARKET'},{'timeInForce':'GTC'},{'symbol':'ETHUSDT'}):
            with self.assertRaises(Blocked):venue.send('POST','/fapi/v1/order',{**self.payload(),**change})
        opener.open.assert_not_called()
    def test_transport_timeout_is_unknown_and_never_retried(self):
        opener=Mock();opener.open.side_effect=TimeoutError()
        venue=Binance(key='x',secret='x',opener=opener,authorize_writes=True)
        with self.assertRaises(Unknown):venue.send('POST','/fapi/v1/order',self.payload())
        self.assertEqual(opener.open.call_count,1)
    def test_rate_limit_cooldown_prevents_poll_storm(self):
        opener=Mock();opener.open.side_effect=HTTPError('https://fapi.binance.com',429,'rate limit',{'Retry-After':'120'},None)
        venue=Binance(opener=opener)
        for _ in range(3):
            with self.assertRaises(Unknown):venue.get('/fapi/v1/time')
        self.assertEqual(opener.open.call_count,1)

    def test_candle_weight_tracks_page_size_and_reserves_before_request(self):
        import time
        opener=Mock();opener.open.side_effect=lambda *a,**k:BytesIO(b'[]')
        venue=Binance(opener=opener)
        for limit,cost in ((1,1),(99,1),(100,2),(499,2),(500,5),(1000,5),(1500,10)):
            venue.get('/fapi/v1/klines',{'symbol':'BTCUSDT','limit':limit})
            self.assertEqual(venue.request_weights[-1][1],cost)
        count=opener.open.call_count
        for limit in (True,0,1501,'1000'):
            with self.assertRaises(Blocked):venue.get('/fapi/v1/klines',{'limit':limit})
        venue.request_weights.clear();venue.request_weights.append((time.monotonic(),2196))
        with self.assertRaises(Unknown):venue.get('/fapi/v1/klines',{'limit':1000})
        self.assertEqual(opener.open.call_count,count)
