import hashlib
import hmac
import io
import unittest
from decimal import Decimal
from urllib.error import URLError

from pancakequant.binance import BinanceReadOnly, NoRedirect, validate_account_mode, account_report
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

    def test_usdt_equity_full_protection_and_remainder_are_distinct(self):
        config={'dualSidePosition':False,'multiAssetsMargin':False}
        symbol={'symbol':'BTCUSDT','marginType':'ISOLATED','leverage':20,'isAutoAddMargin':False}
        p={'symbol':'BTCUSDT','positionSide':'BOTH','marginAsset':'USDT','positionAmt':'.02',
           'entryPrice':'100000','markPrice':'110000','unRealizedProfit':'200',
           'liquidationPrice':'95000','isolatedWallet':'100'}
        a={'assets':[{'asset':'USDT','walletBalance':'1000'}],'positions':[p],
           'totalWalletBalance':'1000','totalUnrealizedProfit':'200','totalMarginBalance':'1200'}
        common={'symbol':'BTCUSDT','side':'SELL','positionSide':'BOTH','closePosition':True,
                'workingType':'MARK_PRICE','priceProtect':False,'algoStatus':'NEW'}
        algos=[dict(common,algoId=1,orderType='STOP_MARKET',triggerPrice='105000'),
               dict(common,algoId=2,orderType='TAKE_PROFIT_MARKET',triggerPrice='120000')]
        r=account_report(123,config,symbol,a,[p],[{'symbol':'BTCUSDT','reduceOnly':False}],algos,'110000')
        self.assertEqual(Decimal(r['equity_usdt']),1200);self.assertEqual(r['quantity_btc'],'0.02')
        self.assertTrue(r['native_full_position_protected']);self.assertEqual(r['possible_entry_remainders'],1)
        self.assertTrue(r['stop_before_liquidation'])
        algos[0]['triggerPrice']='94000'
        self.assertFalse(account_report(123,config,symbol,a,[p],[],algos,'110000')['stop_before_liquidation'])
        algos[0]['workingType']='CONTRACT_PRICE'
        self.assertFalse(account_report(123,config,symbol,a,[p],[],algos,'110000')['native_full_position_protected'])
        with self.assertRaises(Unknown):account_report(123,config,symbol,a,[],[],algos,'110000')
        a['totalWalletBalance']='999'
        with self.assertRaises(Unknown):account_report(123,config,symbol,a,[p],[],algos,'110000')

    def test_bounded_snapshot_does_not_turn_racing_wallet_into_stable_state(self):
        class Fixture(BinanceReadOnly):
            def __init__(self,racing=False):
                super().__init__(clock=lambda:1000);self.racing=racing;self.observations=0
            def account_identity(self):return '123'
            def get(self,path,parameters=None):
                if path.endswith('accountConfig'):return {'dualSidePosition':False,'multiAssetsMargin':False}
                if path.endswith('symbolConfig'):
                    return [{'symbol':'BTCUSDT','marginType':'ISOLATED','leverage':20,'isAutoAddMargin':False}]
                if path=='/fapi/v3/account':
                    self.observations+=1;wallet=str(1000+self.observations if self.racing else 1000)
                    return {'assets':[{'asset':'USDT','walletBalance':wallet,'updateTime':1}],
                            'positions':[],'totalWalletBalance':wallet,'totalUnrealizedProfit':'0',
                            'totalMarginBalance':wallet}
                if path.endswith('premiumIndex'):return {'symbol':'BTCUSDT','markPrice':'100000','time':1000000}
                return []
        good=Fixture();self.assertEqual(good.snapshot('123')['equity_usdt'],'1000')
        with self.assertRaises(Blocked):Fixture().snapshot('456')
        racing=Fixture(True)
        with self.assertRaises(Unknown):racing.snapshot('123')
        self.assertEqual(racing.observations,4)
