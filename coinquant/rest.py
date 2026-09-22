"""Bounded Bybit REST transport. Writes are NEVER automatically retried."""
import hashlib
import hmac
import json
import os
import time
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError

from .types import Blocked, Unknown


OFFICIAL_HOSTS = {
    'testnet': (
        'api-testnet.bybit.com',
        'api-testnet.manepa.jp',
        'api-testnet.spark-fintech.com',
    ),
    'live': (
        'api.bybit.com',
        'api.bytick.com',
        'api.bybit.nl',
        'api.bybit.tr',
        'api.bybit.kz',
        'api.bybitgeorgia.ge',
        'api.bybit.ae',
        'api.bybit.eu',
        'api.bybit.id',
        'api.manepa.jp',
        'api.spark-fintech.com',
    ),
}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise Blocked('refusing API redirect; credentials never leave the selected host')


class Rest:
    def __init__(self, environment: str, *, api_host: str = '', execute: bool = False, opener=None):
        if environment not in OFFICIAL_HOSTS:
            raise Blocked('invalid explicit exchange environment')
        host = api_host or OFFICIAL_HOSTS[environment][0]
        if host not in OFFICIAL_HOSTS[environment]:
            raise Blocked('api_host is not an approved Bybit host for this environment')
        self.base = 'https://' + host
        self.environment = environment
        self.execute = execute
        self.opener = opener or build_opener(NoRedirect())
        self.deadline = time.monotonic() + 180

    def call(self, method: str, path: str, parameters=None, *, private=False) -> dict:
        if method not in ('GET', 'POST') or not path.startswith('/v5/'):
            raise Blocked('invalid API operation')
        if method == 'POST' and not self.execute:
            raise Blocked('transport is read-only')
        parameters = parameters or {}
        body = urlencode(sorted(parameters.items())) if method == 'GET' else json.dumps(parameters, separators=(',', ':'))
        headers = {'Content-Type': 'application/json', 'User-Agent': 'coinquant'}
        if private:
            prefix = 'COINQUANT_' + self.environment.upper()
            key, secret = os.getenv(prefix + '_KEY', ''), os.getenv(prefix + '_SECRET', '')
            if not key or not secret:
                raise Blocked('matching environment credentials are not configured')
            stamp, window = str(int(time.time() * 1000)), '5000'
            signature = hmac.new(secret.encode(), (stamp + key + window + body).encode(), hashlib.sha256).hexdigest()
            headers.update({'X-BAPI-API-KEY': key, 'X-BAPI-SIGN': signature,
                            'X-BAPI-TIMESTAMP': stamp, 'X-BAPI-RECV-WINDOW': window})
        url = self.base + path + ('?' + body if method == 'GET' and body else '')
        request = Request(url, data=body.encode() if method == 'POST' else None, headers=headers, method=method)
        if time.monotonic() >= self.deadline:
            raise Unknown('bounded invocation deadline exceeded; no write retry')
        try:
            with self.opener.open(request, timeout=min(8, max(.1, self.deadline - time.monotonic()))) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise Unknown('oversized API response')
            result = json.loads(raw)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError):
            # Do not log HTTP bodies, signed headers, keys, or exception messages.
            raise Unknown(f'{method} {path}: transport outcome unknown') from None
        if not isinstance(result, dict) or type(result.get('retCode')) is not int:
            raise Unknown('unrecognized exchange response')
        if result['retCode'] != 0:
            # Some nonzero codes mean a duplicate/request timeout, not rejection.
            error = Unknown if method == 'POST' else Blocked
            raise error(f'{method} {path}: exchange code {result["retCode"]}; reconcile before any retry')
        if not isinstance(result.get('result'), dict) or not isinstance(result.get('time'), int):
            raise Unknown('missing exchange result or timestamp')
        if abs(int(time.time() * 1000) - result['time']) > 15_000:
            raise Unknown('exchange timestamp outside freshness allowance')
        return result

    def get(self, path: str, parameters=None, *, private=False):
        return self.call('GET', path, parameters, private=private)['result']

    def pages(self, path: str, parameters: dict, *, private=False) -> list[dict]:
        rows, seen, cursor = [], set(), ''
        for _ in range(40):
            args = dict(parameters)
            if cursor:
                args['cursor'] = cursor
            result = self.get(path, args, private=private)
            if not isinstance(result.get('list'), list):
                raise Unknown('missing paginated list; not an empty account')
            rows.extend(result['list'])
            cursor = result.get('nextPageCursor', '')
            if not cursor:
                return rows
            if not isinstance(cursor, str) or cursor in seen:
                raise Unknown('invalid pagination cursor')
            seen.add(cursor)
        raise Unknown('pagination bound exceeded; snapshot is incomplete')
