import hashlib
import hmac
import io
import unittest
from urllib.error import URLError

from research.binance_readonly import BinanceReadOnly, NoRedirect, validate_account_mode
from pancakequant.types import Blocked, Unknown


class Opener:
    def __init__(self, body=b'{"uid":123}'):
        self.body=body; self.requests=[]
    def open(self, request, timeout):
        self.requests.append(request)
        return io.BytesIO(self.body)


class BinanceReadTests(unittest.TestCase):
    def test_signs_exact_query_and_returns_only_uid(self):
        o=Opener();v=BinanceReadOnly(key='test-key',secret='test-secret',opener=o,clock=lambda:1)
        self.assertEqual(v.account_identity(),'123')
        request=o.requests[0];query,signature=request.full_url.split('?',1)[1].split('&signature=')
        self.assertEqual(signature,hmac.new(b'test-secret',query.encode(),hashlib.sha256).hexdigest())
        self.assertEqual(request.get_method(),'GET')
        self.assertTrue(request.full_url.startswith('https://api.binance.com/api/v3/account?'))

    def test_public_get_never_sends_key_or_signature(self):
        o=Opener(b'{"serverTime":1000}');v=BinanceReadOnly(key='test-key',secret='test-secret',opener=o)
        v.get('/fapi/v1/time');r=o.requests[0]
        self.assertNotIn('signature',r.full_url)
        self.assertNotIn('X-mbx-apikey',r.headers)

    def test_out_of_scope_request_and_redirect_blocked(self):
        v=BinanceReadOnly(opener=Opener())
        for path in ['/fapi/v1/order','/sapi/v1/capital/withdraw/apply','https://example.com']:
            with self.assertRaises(Blocked):v.get(path)
        with self.assertRaises(Blocked):NoRedirect().redirect_request()
        with self.assertRaises(Blocked):v.get('/fapi/v1/klines',{'symbol':'ETHUSDT'})

    def test_unavailable_is_unknown_and_error_does_not_leak_secrets(self):
        class Broken:
            def open(self,*args,**kwargs):raise URLError('secret-url-and-key')
        with self.assertRaises(Unknown) as e:BinanceReadOnly(opener=Broken()).get('/fapi/v1/time')
        self.assertNotIn('secret-url',str(e.exception))
        with self.assertRaises(Unknown):BinanceReadOnly(opener=Opener(b'{}'),key='k',secret='s').account_identity()

    def test_missing_or_wrong_account_mode_blocks(self):
        account={'dualSidePosition':False,'multiAssetsMargin':False}
        symbol={'symbol':'BTCUSDT','marginType':'ISOLATED','leverage':20,'isAutoAddMargin':False}
        validate_account_mode(account,symbol)
        with self.assertRaises(Blocked):validate_account_mode({},symbol)
        with self.assertRaises(Blocked):validate_account_mode(account,dict(symbol,leverage=21))
        with self.assertRaises(Blocked):validate_account_mode(account,dict(symbol,marginType='CROSSED'))
