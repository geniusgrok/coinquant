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
