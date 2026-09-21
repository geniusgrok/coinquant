"""Binance bounded observation adapter; no order or account-setting writes.

Private reads require explicitly supplied credentials; raw identity/balance
responses must never be printed or persisted.
"""
import hashlib
import hmac
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from pancakequant.types import Blocked, Unknown, number

PUBLIC = {'/fapi/v1/time', '/fapi/v1/exchangeInfo', '/fapi/v1/klines',
          '/fapi/v1/premiumIndex', '/fapi/v1/depth'}
PRIVATE = {'/api/v3/account', '/fapi/v3/account', '/fapi/v1/accountConfig',
           '/fapi/v1/symbolConfig', '/fapi/v3/positionRisk', '/fapi/v1/openOrders',
           '/fapi/v1/openAlgoOrders', '/fapi/v1/userTrades',
           '/fapi/v1/commissionRate', '/fapi/v1/leverageBracket',
           '/fapi/v1/order', '/fapi/v1/algoOrder'}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise Blocked('Binance API redirects are refused')


class BinanceReadOnly:
    def __init__(self, *, key='', secret='', opener=None, clock=time.time):
        self.key, self.secret = key, secret
        self.opener = opener or build_opener(NoRedirect())
        self.clock = clock
        self.deadline = time.monotonic() + 120

    def get(self, path, parameters=None):
        if path not in PUBLIC | PRIVATE:
            raise Blocked('operation outside Binance read-only allowlist')
        private = path in PRIVATE
        params = dict(parameters or {})
        if any(k in params for k in ('signature', 'timestamp', 'recvWindow')):
            raise Blocked('caller cannot override request signing fields')
        if 'symbol' in params and params['symbol'] != 'BTCUSDT':
            raise Blocked('only BTCUSDT is supported')
        headers = {'User-Agent':'pancakequant'}
        if private:
            if not self.key or not self.secret:
                raise Blocked('explicit Binance credentials required for private reads')
            params.update(timestamp=int(self.clock()*1000), recvWindow=5000)
            headers['X-MBX-APIKEY'] = self.key
        query = urlencode(sorted(params.items()))
        if private:
            query += '&signature=' + hmac.new(self.secret.encode(),query.encode(),hashlib.sha256).hexdigest()
        host = 'api.binance.com' if path == '/api/v3/account' else 'fapi.binance.com'
        request = Request('https://'+host+path+('?' + query if query else ''),headers=headers,method='GET')
        remaining = self.deadline-time.monotonic()
        if remaining <= 0: raise Unknown('bounded Binance observation deadline exceeded')
        try:
            with self.opener.open(request, timeout=min(8,remaining)) as response:
                raw = response.read(2000001)
            if len(raw)>2000000: raise Unknown('oversized Binance response')
            result = json.loads(raw)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError):
            raise Unknown('Binance observation unavailable; no empty-account inference') from None
        if not isinstance(result,(dict,list)) or (isinstance(result,dict) and 'code' in result):
            raise Unknown('unexpected Binance read response')
        return result

    def completed_market(self):
        """Exactly 120 completed native four-hour trade bars, no forming candle."""
        response = self.get('/fapi/v1/time')
        now = response.get('serverTime') if isinstance(response, dict) else None
        if type(now) is not int or abs(int(self.clock()*1000)-now) > 15000:
            raise Unknown('Binance server time is missing or local clock is stale')
        interval = 4*60*60*1000
        end = now//interval*interval
        rows = self.get('/fapi/v1/klines', {'symbol':'BTCUSDT','interval':'4h',
                                         'startTime':end-120*interval,'endTime':end-1,'limit':120})
        if not isinstance(rows, list) or len(rows) != 120:
            raise Unknown('complete Binance market history unavailable')
        candles=[]
        for offset, row in enumerate(rows):
            if (not isinstance(row, list) or len(row) < 11
                    or type(row[0]) is not int or row[0] != end-(120-offset)*interval
                    or type(row[6]) is not int or row[6] != row[0]+interval-1
                    or row[6] >= now):
                raise Unknown('Binance candle sequence is incomplete or still forming')
            o,h,l,c,v = [number(x) for x in row[1:6]]
            if not 0 < l <= min(o,c) <= max(o,c) <= h or v < 0:
                raise Unknown('invalid native Binance candle values')
            candles.append({'time':row[0],'open':str(o),'high':str(h),'low':str(l),
                            'close':str(c),'volume':str(v)})
        return {'server_time':now,'complete_through':end,'interval_ms':interval,'candles':candles}

    def account_identity(self):
        raw = self.get('/api/v3/account', {'omitZeroBalances':'true'})
        uid = raw.get('uid') if isinstance(raw,dict) else None
        if type(uid) is not int or uid <= 0:
            raise Unknown('Binance account UID is unavailable')
        return str(uid)  # do not retain or log the raw spot account response

    def query_intent(self, client_identity, *, conditional=False):
        """Observe a stable identity, including the conditional order's child.

        Missing/expired history remains Unknown. Never authorizes resubmission;
        a parent trigger/cancel status is not evidence of its child's fill state.
        """
        if (not isinstance(client_identity, str) or not 1 <= len(client_identity) <= 36
                or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.:/'
                       for c in client_identity)):
            raise Blocked('invalid stable Binance order identity')
        if conditional:
            parent = self.get('/fapi/v1/algoOrder', {'clientAlgoId':client_identity})
            identity_field = 'clientAlgoId'
        else:
            parent = self.get('/fapi/v1/order', {'symbol':'BTCUSDT',
                                               'origClientOrderId':client_identity})
            identity_field = 'clientOrderId'
        if (not isinstance(parent, dict) or parent.get('symbol') != 'BTCUSDT'
                or parent.get(identity_field) != client_identity):
            raise Unknown('Binance order identity does not match durable intent')
        child = None
        if conditional:
            actual = parent.get('actualOrderId')
            if actual is None:
                raise Unknown('conditional child identity is missing')
            if actual not in ('', '0', 0):
                if not str(actual).isdigit() or int(actual) <= 0:
                    raise Unknown('invalid conditional child identity')
                child = self.get('/fapi/v1/order', {'symbol':'BTCUSDT','orderId':int(actual)})
                if (not isinstance(child, dict) or child.get('symbol') != 'BTCUSDT'
                        or str(child.get('orderId')) != str(actual)
                        or child.get('side') != parent.get('side')
                        or child.get('positionSide') != parent.get('positionSide')):
                    raise Unknown('conditional child observation conflicts with parent')
        return {'parent':parent, 'child':child, 'resubmit_authorized':False}

    def snapshot(self, expected_uid):
        uid=self.account_identity()
        if uid!=str(expected_uid):raise Blocked('Binance account UID does not match the configured account')
        for _ in range(2):
            def observe():
                return {'config':self.get('/fapi/v1/accountConfig'),
                        'symbol':self.get('/fapi/v1/symbolConfig',{'symbol':'BTCUSDT'}),
                        'account':self.get('/fapi/v3/account'),
                        'positions':self.get('/fapi/v3/positionRisk',{'symbol':'BTCUSDT'}),
                        'orders':self.get('/fapi/v1/openOrders'),
                        'algos':self.get('/fapi/v1/openAlgoOrders')}
            first=observe()
            fills=self.get('/fapi/v1/userTrades',{'symbol':'BTCUSDT','limit':1000})
            second=observe()
            if not isinstance(fills,list) or len(fills)>=1000:
                raise Unknown('recent trade response is missing or may be truncated')
            if any(f.get('symbol')!='BTCUSDT' for f in fills):
                raise Unknown('unexpected recent trade scope')
            if observation_key(first)!=observation_key(second):continue
            symbols=second['symbol']
            if not isinstance(symbols,list) or len(symbols)!=1:
                raise Unknown('missing or ambiguous BTCUSDT configuration')
            ticker=self.get('/fapi/v1/premiumIndex',{'symbol':'BTCUSDT'})
            if (not isinstance(ticker,dict) or ticker.get('symbol')!='BTCUSDT'
                    or type(ticker.get('time')) is not int
                    or abs(int(self.clock()*1000)-ticker['time'])>15000):
                raise Unknown('stale or invalid Binance mark observation')
            report=account_report(uid,second['config'],symbols[0],second['account'],
                                  second['positions'],second['orders'],second['algos'],ticker['markPrice'])
            report.update(mark_time=ticker['time'],mark_price=ticker['markPrice'],
                          recent_fill_count=len(fills),recovery_history_complete=False)
            return report
        raise Unknown('Binance account changed during bounded reconciliation')


def observation_key(value):
    """Ignore continuously repriced PnL; compare state that fills/margin writes change."""
    try:
        account=value['account']
        assets=sorted((a['asset'],a['walletBalance'],a['updateTime']) for a in account['assets'])
        account_positions=sorted((p['symbol'],p['positionSide'],p['positionAmt'],
                                  p['isolatedWallet'],p['updateTime']) for p in account['positions'])
        positions=sorted((p['symbol'],p['positionSide'],p['positionAmt'],p['entryPrice'],
                          p['isolatedWallet'],p['updateTime']) for p in value['positions'])
        stable={'assets':assets,'account_positions':account_positions,'positions':positions,
                'config':value['config'],'symbol':value['symbol'],
                'orders':sorted(value['orders'],key=lambda o:o['orderId']),
                'algos':sorted(value['algos'],key=lambda o:o['algoId'])}
        return json.dumps(stable,sort_keys=True,separators=(',',':'),allow_nan=False)
    except (KeyError,TypeError,ValueError):
        raise Unknown('missing native reconciliation identity fields') from None


def validate_account_mode(account_config, symbol_config):
    if (account_config.get('dualSidePosition') is not False
            or account_config.get('multiAssetsMargin') is not False):
        raise Blocked('Binance single-asset one-way account required')
    if (symbol_config.get('symbol') != 'BTCUSDT'
            or symbol_config.get('marginType') != 'ISOLATED'
            or number(symbol_config.get('leverage')) != 20
            or symbol_config.get('isAutoAddMargin') is not False):
        raise Blocked('Binance isolated 20x BTCUSDT without automatic margin required')


def account_report(uid, config, symbol_config, account, positions, orders, algos, mark):
    """Decode one observed USDT account without translating inverse BTC units.

    Caller must establish observation consistency. This pure decoder is not an
    authorization gate or proof of atomic entry/partial-fill protection.
    """
    validate_account_mode(config,symbol_config)
    if not str(uid).isdigit() or int(uid)<=0:raise Unknown('missing account UID')
    mark=number(mark,positive=True)
    assets=account.get('assets');account_positions=account.get('positions')
    if not isinstance(assets,list) or not isinstance(account_positions,list):
        raise Unknown('missing account assets or positions')
    usdt=[a for a in assets if a.get('asset')=='USDT']
    if len(usdt)!=1:raise Unknown('missing or duplicate USDT wallet')
    for asset in assets:
        if asset.get('asset')!='USDT' and number(asset.get('walletBalance'))!=0:
            raise Blocked('non-USDT collateral is outside the single settlement account model')
    for p in account_positions:
        if p.get('symbol')!='BTCUSDT' and number(p.get('positionAmt'))!=0:
            raise Blocked('foreign position affects full account equity')
    if not isinstance(positions,list) or len(positions)>1:
        raise Unknown('ambiguous native BTCUSDT position response')
    pos=positions[0] if positions else None
    q=number(pos.get('positionAmt')) if pos else number(0)
    if pos and (pos.get('symbol')!='BTCUSDT' or pos.get('positionSide')!='BOTH'
                or pos.get('marginAsset')!='USDT'):
        raise Blocked('unexpected native position scope or settlement')
    ap=[p for p in account_positions if p.get('symbol')=='BTCUSDT']
    if len(ap)>1 or (ap and ap[0].get('positionSide')!='BOTH'):
        raise Unknown('ambiguous account position')
    aq=number(ap[0].get('positionAmt')) if ap else number(0)
    if q!=aq:raise Unknown('account and position observations disagree')
    wallet=number(usdt[0].get('walletBalance'))
    if wallet!=number(account.get('totalWalletBalance')):
        raise Unknown('USDT wallet and account totals disagree')
    unrealized=number(account.get('totalUnrealizedProfit'))
    if not q and unrealized!=0:
        raise Unknown('flat single-symbol account has unexplained unrealized PnL')
    if abs(wallet+unrealized-number(account.get('totalMarginBalance'))) > number('.00000001'):
        raise Unknown('account equity arithmetic is inconsistent')
    entry=number(pos.get('entryPrice'),positive=True) if q else number(0)
    liquidation=number(pos.get('liquidationPrice'),positive=True) if q else number(0)
    isolated=number(pos.get('isolatedWallet')) if q else number(0)
    if isolated<0:raise Unknown('invalid isolated USDT wallet')
    if q and number(ap[0].get('isolatedWallet')) != isolated:
        raise Unknown('account and position isolated margins disagree')
    if q:
        position_mark=number(pos.get('markPrice'),positive=True)
        if abs(number(pos.get('unRealizedProfit'))-q*(position_mark-entry))>number('.00000001'):
            raise Unknown('native position PnL is inconsistent with its own mark')
    if not isinstance(orders,list) or not isinstance(algos,list):
        raise Unknown('missing ordinary or algo order list')
    if any(o.get('symbol')!='BTCUSDT' for o in orders+algos):
        raise Blocked('foreign orders affect the single-symbol account')
    close_side='SELL' if q>0 else 'BUY'
    protective=[]
    algo_ids=set()
    for a in algos:
        identity=a.get('algoId')
        if (isinstance(identity,bool) or not str(identity).isascii()
                or not str(identity).isdigit() or int(identity)<=0
                or int(identity) in algo_ids):
            raise Unknown('missing or duplicate native protective order identity')
        algo_ids.add(int(identity))
        if (a.get('algoStatus')=='NEW' and a.get('side')==close_side
                and a.get('positionSide')=='BOTH' and a.get('closePosition') is True
                and a.get('workingType')=='MARK_PRICE' and a.get('priceProtect') is False
                and a.get('orderType') in ('STOP_MARKET','TAKE_PROFIT_MARKET')):
            trigger=number(a.get('triggerPrice'),positive=True)
            stop=a['orderType']=='STOP_MARKET'
            if (trigger<mark if (q>0)==stop else trigger>mark):
                protective.append({'algo_id':a.get('algoId'),'type':a['orderType'],'trigger':str(trigger)})
    protected=bool(q) and {a['type'] for a in protective}=={'STOP_MARKET','TAKE_PROFIT_MARKET'}
    safe_stops=[a for a in protective if a['type']=='STOP_MARKET'
                and (number(a['trigger'])>liquidation if q>0 else number(a['trigger'])<liquidation)]
    entries=[o for o in orders if o.get('reduceOnly') is not True]
    entries += [a for a in algos if a.get('closePosition') is not True and a.get('reduceOnly') is not True]
    return {'status':'read_only_migration_observation','account_uid':str(uid),'symbol':'BTCUSDT',
            'wallet_usdt':str(wallet),'equity_usdt':str(wallet+q*(mark-entry)),
            'native_account_equity_usdt':str(wallet+unrealized),
            'quantity_btc':str(q),'entry':str(entry),'native_full_position_protected':protected,
            'isolated_wallet_usdt':str(isolated),'native_liquidation_price':str(liquidation),
            'stop_before_liquidation':bool(safe_stops),
            'protective_algos':protective,'possible_entry_remainders':len(entries),
            'qualification':'NOT_QUALIFIED','writes_supported':False}
