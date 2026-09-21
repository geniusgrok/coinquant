"""Binance migration probe: bounded GET only, no order or account-setting writes.

Not yet wired into production run_once. Private reads require explicitly supplied
credentials; raw identity/balance responses must never be printed or persisted.
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
           '/fapi/v1/commissionRate', '/fapi/v1/leverageBracket'}


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

    def account_identity(self):
        raw = self.get('/api/v3/account', {'omitZeroBalances':'true'})
        uid = raw.get('uid') if isinstance(raw,dict) else None
        if type(uid) is not int or uid <= 0:
            raise Unknown('Binance account UID is unavailable')
        return str(uid)  # do not retain or log the raw spot account response


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
    if q and abs(number(pos.get('unRealizedProfit'))-unrealized)>number('.00000001'):
        raise Unknown('native position and account unrealized PnL disagree')
    if not isinstance(orders,list) or not isinstance(algos,list):
        raise Unknown('missing ordinary or algo order list')
    if any(o.get('symbol')!='BTCUSDT' for o in orders+algos):
        raise Blocked('foreign orders affect the single-symbol account')
    close_side='SELL' if q>0 else 'BUY'
    protective=[]
    for a in algos:
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
            'wallet_usdt':str(wallet),'equity_usdt':str(wallet+unrealized),
            'quantity_btc':str(q),'entry':str(entry),'native_full_position_protected':protected,
            'isolated_wallet_usdt':str(isolated),'native_liquidation_price':str(liquidation),
            'stop_before_liquidation':bool(safe_stops),
            'protective_algos':protective,'possible_entry_remainders':len(entries),
            'qualification':'NOT_QUALIFIED','writes_supported':False}
