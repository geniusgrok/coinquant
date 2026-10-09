"""Single Binance adapter with bounded reads and explicitly authorized order writes.

Private reads require explicitly supplied credentials; raw identity/balance
responses must never be printed or persisted.
"""
import hashlib
import hmac
import json
import time
from collections import deque
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from decimal import Decimal

from coinquant.types import Blocked, Missing, NotSent, ObservationDeadline, Rejected, Unknown, number

PUBLIC = {'/fapi/v1/time', '/fapi/v1/exchangeInfo', '/fapi/v1/klines',
          '/fapi/v1/premiumIndex', '/fapi/v1/depth'}
PRIVATE = {'/api/v3/account', '/fapi/v3/account', '/fapi/v1/accountConfig',
           '/fapi/v1/symbolConfig', '/fapi/v3/positionRisk', '/fapi/v1/openOrders',
           '/fapi/v1/openAlgoOrders', '/fapi/v1/userTrades',
           '/fapi/v1/commissionRate', '/fapi/v1/leverageBracket',
           '/fapi/v1/order', '/fapi/v1/algoOrder', '/fapi/v1/income',
           '/fapi/v1/positionMargin/history'}
# A refusal of this request: nothing new was accepted under the identity.
# -4116 (duplicate client id), -4117 (stop is triggering) and -4115/-4111
# (duplicate client transfer id) are not in this set: the earlier object may exist.
# Anything else, including -1006/-1007 and every 5xx, stays an unknown execution.
REJECT_CODES = frozenset({
    -1021, -1022, -1100, -1101, -1102, -1103, -1104, -1105, -1106, -1108, -1111,
    -1114, -1115, -1116, -1117, -1118, -1119, -1120, -1121, -1127, -1128, -1130,
    -2010, -2011, -2013, -2014, -2015, -2018, -2019, -2020, -2021, -2022, -2024, -2025,
    -4000, -4001, -4002, -4003, -4004, -4005, -4006, -4007, -4008, -4009, -4010,
    -4011, -4012, -4013, -4014, -4015, -4016, -4022, -4023, -4024, -4028, -4044,
    -4045, -4050, -4051, -4054, -4055, -4060, -4061, -4062, -4087, -4118, -4120,
    -4131, -4137, -4138, -4140, -4141, -4142, -4144, -4164, -4183, -4184,
})
# HTTP 503 bodies Binance documents as failed operations (-1008 is matched by
# code). "Unknown error, please check your request or try again later." and
# every other 503 keep an unknown execution status.
FAILED_503 = frozenset({'Service Unavailable.',
                        'Internal error; unable to process your request. Please try again.'})
# A signed request is refused after timestamp+recvWindow (5 s). Past this age a
# request that is still not visible can no longer be accepted.
UNACCEPTED_AFTER_MS = 300000
# Binance keeps a canceled or expired zero-fill order queryable for about three
# days. Inside one day, "order does not exist" means this identity was not accepted.
# A failed query is not this observation. After the retention window it stays unknown.
QUERYABLE_MS = 86400000
# A slower time sample cannot bound the offset well inside the 5 s recvWindow.
MAX_CLOCK_ROUND_TRIP = 1.0
# The all-symbol exchangeInfo read is required by every protection and exit.
MAX_RESPONSE_BYTES = 8000000
# A write is only sent with time to read its answer; otherwise it is never sent.
MIN_WRITE_SECONDS = 2.0


def conditional_is_terminal(observed):
    """A terminal child settles a triggered parent, even before FINISHED arrives."""
    parent,child=observed['parent'],observed['child']
    status=parent.get('algoStatus')
    if status not in ('CANCELED','EXPIRED','REJECTED','FINISHED','TRIGGERED'):
        return False
    if child is None:
        return status not in ('FINISHED','TRIGGERED')
    original=number(child.get('origQty'),positive=True);filled=number(child.get('executedQty'))
    if not 0<=filled<=original:raise Unknown('invalid protection child quantities')
    status=child.get('status')
    if status=='FILLED' and filled!=original:raise Unknown('incomplete filled protection child')
    if status in ('NEW','REJECTED') and filled:raise Unknown('unfilled child status reports fills')
    return status in ('FILLED','CANCELED','EXPIRED','EXPIRED_IN_MATCH','REJECTED')


def _retry_after(exc):
    try:
        return max(60, min(86400, float(exc.headers.get('Retry-After', '60'))))
    except (TypeError, ValueError, AttributeError):
        return 60


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise Blocked('Binance API redirects are refused')


# Local rolling-minute request-weight budget, below Binance's 2400 per IP.
WEIGHT_LIMIT = 2200

# Spot account identity host and USD-M futures host per environment. Demo is
# Binance's virtual-balance environment; its UID and account semantics are not
# natively verified here.
HOSTS = {'live': ('api.binance.com', 'fapi.binance.com'),
         'demo': ('demo-api.binance.com', 'demo-fapi.binance.com')}


class Binance:
    def __init__(self, *, key='', secret='', opener=None, clock=time.time, authorize_writes=False, monotonic=None,
                 environment='live', capital_limit=None):
        if environment not in HOSTS:
            raise Blocked('unknown Binance environment')
        self.environment = environment
        self.capital_limit = None if capital_limit is None else Decimal(capital_limit)
        self.key, self.secret = key, secret
        self.opener = opener or build_opener(NoRedirect())
        self.clock = clock
        self._monotonic = monotonic
        self.authorize_writes = authorize_writes is True
        self.cooldown_until = 0
        self.request_weights = deque()
        self.check_all_orders = True
        self.all_orders_checked_at = None
        self.deadline = self.monotonic() + 120
        # Absolute end of every budget renewal; set by the session coordinator.
        self.hard_deadline = None
        self._dfii10 = None
        self.align_time = False
        self.time_offset_ms = 0
        self.time_aligned_at = None
        self.server_weight = None

    def dfii10_snapshot(self):
        from .dfii10 import Source
        if self._dfii10 is None:self._dfii10=Source()
        remaining=self.deadline-self.monotonic()
        if remaining<=1:raise Unknown('no session budget left for the DFII10 read')
        return self._dfii10.snapshot(int(self.clock()*1000),budget=remaining)

    def monotonic(self):
        """Budget clock for this adapter. Subclasses and replay inject their own.

        Session deadlines and this adapter must share one clock. The process
        wall monotonic is only the default when nobody injected one.
        """
        if self._monotonic is not None:
            return self._monotonic()
        return time.monotonic()

    def set_deadline(self, seconds, *, extend_only=False):
        """Bound the current observation. A renewal never passes `hard_deadline`."""
        target = self.monotonic() + seconds
        if extend_only:
            target = max(target, self.deadline)
        if self.hard_deadline is not None:
            target = min(target, self.hard_deadline)
        self.deadline = target

    def begin_cycle(self, seconds=120):
        self.set_deadline(min(120, max(1, seconds)))
        # Weight-40 all-symbol scans run at most once per rolling minute.
        last = self.all_orders_checked_at
        if last is None or self.monotonic() - last >= 60:
            self.check_all_orders = True
        self._cycle_config = None
        if self.align_time:
            self.align_clock()

    def refresh_safety_observation(self, max_age=60):
        """Before new risk, re-read account mode and the all-symbol scan once they are `max_age` seconds old.

        A weight-40 scan on every five-second top-up poll would exhaust the local request-weight
        reserve and stop the session from completing the very orders it is protecting.
        """
        now = self.monotonic()
        if getattr(self, '_cycle_config', None) is not None and now - getattr(self, '_config_at', -max_age) >= max_age:
            self._cycle_config = None
        last = self.all_orders_checked_at
        if last is None or now - last >= max_age:
            self.check_all_orders = True

    def align_clock(self):
        """Set the signing offset from Binance server time. Does not widen recvWindow.

        The time read spends the same request-weight and deadline budget as any
        other request. A failure is an explicit Unknown: the clock is then not
        trusted and no signed request follows.
        """
        host = HOSTS[self.environment][1]
        if self.monotonic() < self.cooldown_until:
            raise NotSent('Binance rate limit cooldown; no request sent')
        self.ensure_capacity(1)
        remaining = self.deadline - self.monotonic()
        if remaining <= 0:
            raise ObservationDeadline('bounded Binance observation deadline exceeded; no request sent')
        local = int(self.clock() * 1000)
        started = self.monotonic()
        self.request_weights.append((started, 1))
        try:
            with self.opener.open(Request('https://' + host + '/fapi/v1/time'), timeout=min(5, remaining)) as response:
                body = json.loads(response.read(10000))
        except HTTPError as exc:
            if exc.code in (418, 429):
                self.cooldown_until = self.monotonic() + _retry_after(exc)
            raise Unknown('Binance server time unavailable; clock not aligned') from None
        except (URLError, TimeoutError, OSError, ValueError, HTTPException, Blocked):
            raise Unknown('Binance server time unavailable; clock not aligned') from None
        server = body.get('serverTime') if isinstance(body, dict) else None
        if type(server) is not int:
            raise Unknown('Binance time response is not usable')
        elapsed = self.monotonic() - started
        if elapsed > MAX_CLOCK_ROUND_TRIP:
            raise Unknown('Binance time sample was too slow to align the clock')
        halfway = int(elapsed * 500)
        self.time_offset_ms = server - (local + halfway)
        self.time_aligned_at = self.monotonic()

    def ensure_capacity(self, reserve):
        now=self.monotonic()
        while self.request_weights and self.request_weights[0][0]<=now-60:
            self.request_weights.popleft()
        used=sum(cost for _,cost in self.request_weights)
        server=self.server_weight
        if server is not None and server[0] > now-60:
            used=max(used, server[1])
        if used+reserve>WEIGHT_LIMIT:
            raise NotSent('local request-weight reserve unavailable; wait before new risk')

    def get(self, path, parameters=None):
        if path not in PUBLIC | PRIVATE:
            raise Blocked('operation outside Binance read-only allowlist')
        return self._request('GET', path, parameters)

    def send(self, method, path, parameters):
        if not self.authorize_writes:
            raise Blocked('explicit Binance write authorization required')
        allowed = {('POST', '/fapi/v1/order'), ('DELETE', '/fapi/v1/order'),
                   ('POST', '/fapi/v1/algoOrder'), ('DELETE', '/fapi/v1/algoOrder'),
                   ('POST', '/fapi/v1/positionMargin')}
        if (method, path) not in allowed:
            raise Blocked('order lifecycle only; account-setting writes are forbidden')
        p = parameters
        if path == '/fapi/v1/algoOrder' and method == 'DELETE':
            if set(p) != {'clientAlgoId'} or not p['clientAlgoId'].startswith('cq-'):
                raise Blocked('only identified owned protection may be canceled')
        elif p.get('symbol') != 'BTCUSDT':
            raise Blocked('only BTCUSDT writes are supported')
        if path == '/fapi/v1/order' and method == 'DELETE':
            if set(p) != {'symbol', 'origClientOrderId'} or not str(p['origClientOrderId']).startswith('cq-'):
                raise Blocked('only identified owned orders may be canceled')
        if method == 'POST' and path.endswith('/order'):
            if (p.get('positionSide') != 'BOTH' or p.get('side') not in ('BUY', 'SELL')
                    or not str(p.get('newClientOrderId', '')).startswith('cq-')
                    or number(p.get('quantity'), positive=True) <= 0):
                raise Blocked('invalid identified ordinary order')
            if p.get('reduceOnly') == 'true':
                if p.get('type') != 'MARKET':
                    raise Blocked('reduction must be an immediate market order')
            elif p.get('type') != 'LIMIT' or p.get('timeInForce') != 'IOC':
                raise Blocked('new exposure requires bounded IOC limit execution')
        if method == 'POST' and path.endswith('/algoOrder'):
            if (p.get('type') not in ('STOP_MARKET', 'TAKE_PROFIT_MARKET')
                    or p.get('closePosition') != 'true' or p.get('positionSide') != 'BOTH'
                    or p.get('workingType') != 'MARK_PRICE' or p.get('priceProtect') != 'false'
                    or p.get('side') not in ('BUY', 'SELL') or 'quantity' in p or 'reduceOnly' in p):
                raise Blocked('only native full-position mark protection is supported')
        if path.endswith('/positionMargin') and (p.get('type') != 1 or number(p.get('amount'), positive=True) <= 0):
            raise Blocked('margin withdrawal is forbidden')
        return self._request(method, path, p)

    def _request(self, method, path, parameters=None):
        private = method != 'GET' or path in PRIVATE
        params = dict(parameters or {})
        # Conservative per-process rolling budget; leave headroom under the usual
        # 2400/min allowance. Unfiltered order scans are restricted to cycle start.
        weights={'/api/v3/account':20,'/fapi/v1/accountConfig':5,'/fapi/v1/symbolConfig':5,
                 '/fapi/v3/account':5,'/fapi/v3/positionRisk':5,'/fapi/v1/openOrders':5,
                 '/fapi/v1/openAlgoOrders':1,'/fapi/v1/userTrades':5,'/fapi/v1/premiumIndex':1,
                 '/fapi/v1/exchangeInfo':1,'/fapi/v1/time':1,'/fapi/v1/depth':5,
                 '/fapi/v1/klines':2,
                 '/fapi/v1/commissionRate':20,'/fapi/v1/leverageBracket':1,
                 '/fapi/v1/order':1,'/fapi/v1/algoOrder':1,'/fapi/v1/positionMargin':1,
                 '/fapi/v1/positionMargin/history':1,'/fapi/v1/income':30}
        weight=(40 if path.endswith(('/openOrders','/openAlgoOrders')) and 'symbol' not in params
                else 1 if path=='/fapi/v1/openOrders' else weights[path])
        if path == '/fapi/v1/klines':
            limit=params.get('limit',500)
            if type(limit) is not int or not 1<=limit<=1500:
                raise Blocked('invalid Binance candle page size')
            weight=1 if limit<100 else 2 if limit<500 else 5 if limit<=1000 else 10
        self.ensure_capacity(weight)
        if any(k in params for k in ('signature', 'timestamp', 'recvWindow')):
            raise Blocked('caller cannot override request signing fields')
        if 'symbol' in params and params['symbol'] != 'BTCUSDT':
            raise Blocked('only BTCUSDT is supported')
        headers = {'User-Agent':'coinquant'}
        if private:
            if not self.key or not self.secret:
                raise Blocked('explicit Binance credentials required for private reads')
            if self.align_time and (self.time_aligned_at is None or self.monotonic()-self.time_aligned_at > 60):
                # A long cycle re-aligns instead of signing with a stale offset.
                try:
                    self.align_clock()
                except NotSent:
                    raise
                except Unknown:
                    raise NotSent('exchange clock is not aligned; no signed request') from None
            params.update(timestamp=int(self.clock()*1000)+self.time_offset_ms, recvWindow=5000)
            headers['X-MBX-APIKEY'] = self.key
        query = urlencode(sorted(params.items()))
        if private:
            query += '&signature=' + hmac.new(self.secret.encode(),query.encode(),hashlib.sha256).hexdigest()
        spot, futures = HOSTS[self.environment]
        host = spot if path == '/api/v3/account' else futures
        if method == 'GET':
            url, data = 'https://'+host+path+('?' + query if query else ''), None
        else:
            url, data = 'https://'+host+path, query.encode()
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        request = Request(url, data=data, headers=headers, method=method)
        remaining = self.deadline-self.monotonic()
        if self.monotonic() < self.cooldown_until:
            raise NotSent('Binance rate limit cooldown; no request sent')
        if remaining <= 0 or (method != 'GET' and remaining < MIN_WRITE_SECONDS):
            raise ObservationDeadline('bounded Binance observation deadline exceeded; no request sent')
        try:
            self.request_weights.append((self.monotonic(),weight))
            result = self._transport(request, timeout=min(8,remaining))
        except HTTPError as exc:
            if exc.code in (418,429):
                self.cooldown_until=self.monotonic()+_retry_after(exc)
            code,message=_error_body(exc)
            if method != 'GET' and exc.code in (400,401) and code in REJECT_CODES:
                raise Rejected(f'Binance rejected the request with code {code}') from None
            if method != 'GET' and exc.code == 503 and (code == -1008 or message in FAILED_503):
                raise Rejected('Binance reported a failed operation with HTTP 503') from None
            if (method == 'GET' and path in ('/fapi/v1/order','/fapi/v1/algoOrder')
                    and exc.code == 400 and code == -2013):
                raise Missing('Binance reports that the order does not exist') from None
            raise Unknown('Binance HTTP outcome unresolved; query stable identity after cooldown',
                          http_status=exc.code,native_code=code) from None
        except (URLError, TimeoutError, OSError, ValueError, HTTPException, Blocked):
            # A refused redirect or broken response arrives after the request left.
            raise Unknown('Binance request unavailable; read by stable identity before any retry') from None
        if not isinstance(result,(dict,list)) or (isinstance(result,dict) and 'code' in result and not (method != 'GET' and str(result['code']) == '200')):
            raise Unknown('unexpected Binance read response')
        return result

    def _transport(self, request, timeout):
        """Network exchange. Historical replay overrides this and does not patch time."""
        with self.opener.open(request, timeout=timeout) as response:
            headers = getattr(response, 'headers', None)
            used = headers.get('X-MBX-USED-WEIGHT-1M') if headers is not None else None
            if used is not None:
                try:
                    self.server_weight = (self.monotonic(), int(used))
                except (TypeError, ValueError):
                    pass
            raw = response.read(MAX_RESPONSE_BYTES+1)
        if len(raw)>MAX_RESPONSE_BYTES: raise Unknown('oversized Binance response')
        # Numeric amounts, such as a margin response, stay exact decimals.
        return json.loads(raw, parse_float=Decimal)

    def completed_market(self, start=None, *, on_page=None):
        """Page complete four-hour bars from an exact checkpoint; never truncate."""
        response = self.get('/fapi/v1/time')
        now = response.get('serverTime') if isinstance(response, dict) else None
        if type(now) is not int or abs(int(self.clock()*1000)-now) > 15000:
            raise Unknown('Binance server time is missing or local clock is stale')
        interval = 4*60*60*1000
        end = now//interval*interval
        start=end-120*interval if start is None else start
        if type(start) is not int or start%interval or not 0<=start<=end:
            raise Unknown('invalid model checkpoint time')
        if end-start>160*120*interval:
            raise Unknown('history exceeds bounded recovery; import verified checkpoint')
        candles=[]
        # Full bootstrap needs years of bars; 1000 keeps the documented weight
        # at five while avoiding hundreds of small network round trips.
        for cursor in range(start,end,1000*interval):
            page_end=min(end,cursor+1000*interval)
            count=(page_end-cursor)//interval
            rows = self.get('/fapi/v1/klines', {'symbol':'BTCUSDT','interval':'4h',
                                             'startTime':cursor,'endTime':page_end-1,'limit':count})
            if not isinstance(rows, list) or len(rows) != count:
                raise Unknown('complete Binance market history unavailable')
            page=[]
            for offset, row in enumerate(rows):
                if (not isinstance(row, list) or len(row) < 11
                        or type(row[0]) is not int or row[0] != cursor+offset*interval
                        or type(row[6]) is not int or row[6] != row[0]+interval-1
                        or row[6] >= now):
                    raise Unknown('Binance candle sequence is incomplete or still forming')
                o,h,l,c,v = [number(x) for x in row[1:6]]
                if not 0 < l <= min(o,c) <= max(o,c) <= h or v < 0:
                    raise Unknown('invalid native Binance candle values')
                page.append({'time':row[0],'open':str(o),'high':str(h),'low':str(l),
                             'close':str(c),'volume':str(v)})
            if on_page is not None:on_page(page)
            candles.extend(page)
        return {'server_time':now,'complete_through':end,'interval_ms':interval,'candles':candles}

    def account_identity(self):
        # One API key belongs to one account; a verified UID holds for this adapter.
        cached = getattr(self, '_verified_uid', None)
        if cached is not None:
            return cached
        raw = self.get('/api/v3/account', {'omitZeroBalances':'true'})
        uid = raw.get('uid') if isinstance(raw,dict) else None
        if type(uid) is not int or uid <= 0:
            raise Unknown('Binance account UID is unavailable')
        self._verified_uid = str(uid)
        return self._verified_uid  # do not retain or log the raw spot account response

    def query_intent(self, client_identity, *, conditional=False):
        """Observe a stable identity, including the conditional order's child.

        Missing history may use a freshly observed, untriggered close-all parent.
        Its durable request is still checked by the caller. No absence authorizes
        resubmission or proves a terminal state;
        a parent trigger/cancel status is not evidence of its child's fill state.
        """
        if (not isinstance(client_identity, str) or not 1 <= len(client_identity) <= 36
                or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.:/'
                       for c in client_identity)):
            raise Blocked('invalid stable Binance order identity')
        if conditional:
            try:
                parent = self.get('/fapi/v1/algoOrder', {'clientAlgoId':client_identity})
            except Missing:
                # The history endpoint has a 90-day creation-time boundary.
                # Current open orders can prove only a NEW, childless parent.
                rows=self.get('/fapi/v1/openAlgoOrders', {'symbol':'BTCUSDT'})
                if not isinstance(rows,list) or any(not isinstance(row,dict) for row in rows):
                    raise Unknown('current conditional order evidence unavailable')
                matches=[row for row in rows if row.get('clientAlgoId')==client_identity]
                if len(matches)!=1:
                    raise Unknown('missing or ambiguous current conditional identity')
                parent=matches[0]
                if (parent.get('algoType')!='CONDITIONAL' or parent.get('algoStatus')!='NEW'
                        or type(parent.get('actualOrderId')) not in (int,str)
                        or parent['actualOrderId'] not in ('','0',0)
                        or parent.get('closePosition') is not True or parent.get('priceProtect') is not False
                        or parent.get('workingType')!='MARK_PRICE'
                        or parent.get('orderType') not in ('STOP_MARKET','TAKE_PROFIT_MARKET')
                        or isinstance(parent.get('algoId'),bool) or not str(parent.get('algoId')).isascii()
                        or not str(parent.get('algoId')).isdigit()
                        or int(parent['algoId'])<=0):
                    raise Unknown('current conditional parent is not verified untriggered protection')
                number(parent.get('triggerPrice'),positive=True)
            identity_field = 'clientAlgoId'
        else:
            parent = self.get('/fapi/v1/order', {'symbol':'BTCUSDT',
                                               'origClientOrderId':client_identity})
            identity_field = 'clientOrderId'
        if (not isinstance(parent, dict) or parent.get('symbol') != 'BTCUSDT'
                or parent.get(identity_field) != client_identity
                or parent.get('side') not in ('BUY','SELL')
                or parent.get('positionSide') != 'BOTH'):
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

    def conditional_terminal(self, identity):
        """A canceled parent is not proof that its triggered child stopped trading."""
        return conditional_is_terminal(self.query_intent(identity,conditional=True))

    def recover_pending(self, state):
        """Read-only terminal reconciliation; no missing-order retry inference.

        Binance intents store the original native request fields. Unknown or
        unsupported intent kinds stay pending; never infer resolution.
        A canceled conditional parent does not settle a still-active child.
        """
        # Missing-query rejections require an explicit -2013 within native retention.
        # Anything without that proof returns to pending for identity recovery.
        for identity, raw in state.db.execute("SELECT id,result FROM intents WHERE kind='binance_order' AND status='rejected'").fetchall():
            result=json.loads(raw)
            if 'absent_at_ms' in result and not result.get('query_absent_within_retention'):
                state.finish(identity,'unknown',{**result,'legacy_absence_reopened':True})
        resolved = 0
        for intent in state.pending():
            kind, payload = intent['kind'], intent['payload']
            if kind=='binance_cancel':
                try:
                    target=payload['origClientOrderId']
                    original=state.db.execute('SELECT kind,payload FROM intents WHERE id=?',(target,)).fetchone()
                    if not original or original[0]!='binance_order' or payload.get('symbol')!='BTCUSDT':
                        raise Unknown('cancellation ownership missing')
                    expected=json.loads(original[1])
                    parent=self.query_intent(target)['parent']
                    if any(parent.get(k)!=expected.get(k) for k in ('symbol','side','positionSide','type')):
                        raise Unknown('cancellation target scope changed')
                    filled=number(parent['executedQty']);quantity=number(parent['origQty'],positive=True)
                    if not 0<=filled<=quantity or quantity!=number(expected['quantity'],positive=True):
                        raise Unknown('canceled fill quantity conflicts')
                    if parent['status'] in ('FILLED','CANCELED','EXPIRED','EXPIRED_IN_MATCH','REJECTED'):
                        if parent['status']=='FILLED' and filled!=quantity or parent['status']=='REJECTED' and filled:
                            raise Unknown('invalid terminal cancellation')
                        state.finish(intent['id'],'confirmed',{'status':parent['status'],'executed_quantity':str(filled)})
                        resolved+=1
                except (Blocked,Unknown,KeyError,TypeError,ValueError,ArithmeticError):
                    pass
                continue
            if kind=='binance_algo_cancel':
                try:
                    target=payload['clientAlgoId']
                    row=state.db.execute('SELECT kind,payload FROM intents WHERE id=?',(target,)).fetchone()
                    if not row or row[0]!='binance_algo':
                        raise Unknown('cancellation ownership missing')
                    owned=json.loads(row[1])
                    if owned.get('symbol')!='BTCUSDT' or owned.get('closePosition')!='true':
                        raise Unknown('not BTCUSDT close-all cancellation')
                    if self.conditional_terminal(target):
                        state.finish(intent['id'],'confirmed',{'target':target,'terminal':True});resolved+=1
                except (Blocked,Unknown,KeyError,TypeError,ValueError,ArithmeticError):
                    pass
                continue
            if kind=='binance_margin':
                try:
                    if self.recover_margin(state,intent):resolved+=1
                except (Blocked,Unknown,KeyError,TypeError,ValueError,ArithmeticError):
                    pass
                continue
            if kind not in ('binance_order', 'binance_algo'):
                continue
            try:
                conditional = kind == 'binance_algo'
                try:
                    observed = self.query_intent(intent['id'], conditional=conditional)
                except Missing:
                    if not conditional and self.absent_within_retention(state, intent):
                        resolved += 1
                    continue
                parent, child = observed['parent'], observed['child']
                for field in ('symbol', 'side', 'positionSide'):
                    if field not in payload or payload[field] != parent.get(field):
                        raise Unknown('recovered order scope conflicts with durable intent')
                type_field = 'orderType' if conditional else 'type'
                if not payload.get('type') or parent.get(type_field) != payload['type']:
                    raise Unknown('recovered order type conflicts with durable intent')
                for flag in ('reduceOnly', 'priceProtect'):
                    if flag in payload:
                        expected={'true':True,'false':False}.get(payload[flag])
                        if expected is None or parent.get(flag) is not expected:
                            raise Unknown('recovered execution flag conflicts with intent')
                if payload.get('closePosition') == 'true':
                    if not conditional or parent.get('closePosition') is not True:
                        raise Unknown('close-all intent is not native close-all')
                else:
                    quantity_field = 'quantity' if conditional else 'origQty'
                    if number(parent.get(quantity_field), positive=True) != number(payload.get('quantity'), positive=True):
                        raise Unknown('recovered order quantity conflicts with durable intent')
                if conditional:
                    if number(parent.get('triggerPrice'), positive=True) != number(payload.get('triggerPrice'), positive=True):
                        raise Unknown('recovered trigger conflicts with durable intent')
                    if parent.get('workingType') != payload.get('workingType'):
                        raise Unknown('recovered trigger source conflicts with durable intent')
                    if parent.get('algoStatus')=='NEW' and child is None and payload.get('closePosition')=='true':
                        # Lost POST/readback can leave an accepted protective leg
                        # active. Matching native readback resolves acceptance,
                        # allowing the durable lifecycle to install its other leg.
                        state.finish(intent['id'],'confirmed',{'algo_id':parent['algoId'],'status':'NEW'})
                        resolved+=1
                        continue
                    if not conditional_is_terminal(observed):
                        continue
                    if child is None:
                        state.finish(intent['id'], 'confirmed', {'algo_status': parent['algoStatus'], 'child': None},
                                     native=observed)
                        resolved += 1
                        continue
                order = child if conditional else parent
                status = order.get('status')
                if status not in ('NEW', 'PARTIALLY_FILLED', 'FILLED', 'CANCELED', 'EXPIRED', 'EXPIRED_IN_MATCH', 'REJECTED'):
                    raise Unknown('unknown recovered order status')
                executed = number(order.get('executedQty'))
                original = number(order.get('origQty'), positive=True)
                if not 0 <= executed <= original or (status == 'FILLED' and executed != original):
                    raise Unknown('inconsistent recovered filled quantity')
                if status == 'NEW' and executed:
                    raise Unknown('NEW order reports nonzero fills')
                if status == 'NEW' or status == 'PARTIALLY_FILLED':
                    if executed:
                        state.finish(intent['id'],'partial',{'status':status,'executed_quantity':str(executed)})
                    continue
                if status == 'REJECTED' and executed:
                    raise Unknown('rejected order cannot prove a nonzero fill')
                state.finish(intent['id'], 'confirmed', {'status': status, 'executed_quantity': str(executed)},
                             native=observed)
                resolved += 1
            except (Blocked, Unknown, KeyError, TypeError, ValueError, ArithmeticError):
                # Keep independent recoverable intents moving, never erase unknowns.
                continue
        return {'resolved': resolved, 'pending': len(state.pending())}

    def absent_within_retention(self, state, intent):
        """An ordinary order Binance reports as nonexistent, after its signature
        expired and while a zero-fill order would still be queryable, was not
        accepted. A failed query never reaches here. Without a preparation time,
        or once retention has passed, the intent stays unknown."""
        row=state.db.execute('SELECT result,payload FROM intents WHERE id=?',(intent['id'],)).fetchone()
        result=json.loads(row[0]) if row else {}
        payload=json.loads(row[1]) if row else {}
        prepared=result.get('prepared_at_ms')
        now=int(self.clock()*1000)
        if (intent['status']!='unknown' or type(prepared) is not int
                or not UNACCEPTED_AFTER_MS<=now-prepared<QUERYABLE_MS):
            return False
        # Recovery and flat retirement use the same evidence. A missing-query
        # result alone cannot bypass the open-order and complete-fill checks.
        if not self.proven_absent(state,intent):
            return False
        # Binance keeps every order that ever had a fill queryable, so "does not exist"
        # inside the retention window is authoritative. A reduction can only reduce
        # whatever is left. An entry or add is retired only when the position is
        # still what it was at preparation (flat for an entry); anything else could
        # be the fill this query failed to show.
        if payload.get('reduceOnly')!='true':
            try:
                snap=self.snapshot(state.identity.rsplit(':',1)[-1])
            except Exception:
                return False
            before=result.get('position_before_btc','0')
            if (number(snap.get('quantity_btc'))!=number(before)
                    or snap.get('possible_entry_remainders')):
                return False
        state.finish(intent['id'],'rejected',{**result,'absent_at_ms':now,
                                               'query_absent_within_retention':True})
        return True

    def recover_margin(self, state, intent):
        """Settle a transfer whose answer was lost from bounded native margin history.

        A margin write has no client identity. Exactly one matching user add in
        the window after preparation confirms it, and only when no other margin
        intent could have produced a row in that window; any other add there is
        ambiguous and stays unknown. An empty window is not treated as final: a
        history publication delay is not documented. Such an intent is only
        retired by the verified flat account (Lifecycle.retire_stale).
        Balance changes never decide it.
        """
        row=state.db.execute('SELECT result FROM intents WHERE id=?',(intent['id'],)).fetchone()
        prepared=json.loads(row[0]).get('prepared_at_ms') if row else None
        if type(prepared) is not int:
            raise Unknown('margin intent lacks its preparation time; operator review required')
        now=int(self.clock()*1000);begin=prepared-15000
        if not begin<now<=begin+29*86400000:
            raise Unknown('margin history window unavailable; operator review required')
        for other,updated in state.db.execute("SELECT result,updated FROM intents WHERE kind='binance_margin' AND id!=? AND status!='rejected'",(intent['id'],)):
            # Intents from before preparation times were recorded are bounded by
            # their last local update, which follows the transfer.
            at=json.loads(other).get('prepared_at_ms')
            if type(at) is not int:at=int(updated*1000)
            if at>=begin-15000:
                raise Unknown('another margin transfer may own a history row in this window')
        rows=self.get('/fapi/v1/positionMargin/history',
                      {'symbol':'BTCUSDT','startTime':begin,'endTime':now,'limit':500})
        if not isinstance(rows,list) or len(rows)>=500:
            raise Unknown('margin history incomplete')
        adds=[]
        for r in rows:
            if (r.get('symbol')!='BTCUSDT' or r.get('asset','USDT')!='USDT'
                    or r.get('positionSide','BOTH')!='BOTH' or type(r.get('time')) is not int
                    or not begin<=r['time']<=now or str(r.get('type')) not in ('1','2')):
                raise Unknown('unexpected margin history scope')
            if str(r['type'])=='1' and r.get('deltaType','USER_ADJUST')=='USER_ADJUST':
                adds.append(r)
        amount=number(intent['payload']['amount'],positive=True)
        if len(adds)==1 and number(adds[0].get('amount'))==amount:
            state.finish(intent['id'],'confirmed',{'prepared_at_ms':prepared,'amount':str(amount),'history_time':adds[0]['time']})
            return True
        return False

    def proven_absent(self, state, intent):
        """A fill-capable identity is absent only after -2013 inside retention.

        The open list must not contain it, and every trade since preparation must
        already be archived. A failed query or a full trade page is not absence.
        """
        row=state.db.execute('SELECT kind,result FROM intents WHERE id=?',(intent['id'],)).fetchone()
        if not row:return False
        kind=row[0]
        if kind not in ('binance_order','binance_algo'):
            return False
        result=json.loads(row[1])
        prepared=result.get('prepared_at_ms')
        now=int(self.clock()*1000)
        if type(prepared) is not int or not UNACCEPTED_AFTER_MS<=now-prepared<QUERYABLE_MS:
            return False
        try:
            if kind=='binance_order':
                self.get('/fapi/v1/order',{'symbol':'BTCUSDT','origClientOrderId':intent['id']})
            else:
                self.get('/fapi/v1/algoOrder',{'clientAlgoId':intent['id']})
            return False
        except Missing:
            pass
        except (Blocked,Unknown):
            return False
        try:
            if kind=='binance_order':
                rows=self.get('/fapi/v1/openOrders',{'symbol':'BTCUSDT'})
                field='clientOrderId'
            else:
                rows=self.get('/fapi/v1/openAlgoOrders',{'symbol':'BTCUSDT'})
                field='clientAlgoId'
            if (not isinstance(rows,list) or any(not isinstance(item,dict)
                    or item.get('symbol')!='BTCUSDT' or not isinstance(item.get(field),str) for item in rows)
                    or any(item[field]==intent['id'] for item in rows)):
                return False
            begin=max(0,prepared-15000)
            trades=self._trade_page({'symbol':'BTCUSDT','startTime':begin,'endTime':now,'limit':1000})
        except (Blocked,Unknown,TypeError):
            return False
        if len(trades)>=1000:
            return False
        known={tid:json.loads(raw) for tid,raw in state.db.execute('SELECT trade_id,payload FROM native_fills')}
        return all(known.get(trade['id'])==trade for trade in trades)

    def snapshot(self, expected_uid):
        uid=self.account_identity()
        if uid!=str(expected_uid):raise Blocked('Binance account UID does not match the configured account')
        scan_all=self.check_all_orders
        for _ in range(2):
            # Position mode, margin type and leverage are read once per cycle.
            config=getattr(self,'_cycle_config',None)
            if config is None:
                config=(self.get('/fapi/v1/accountConfig'),self.get('/fapi/v1/symbolConfig',{'symbol':'BTCUSDT'}))
                self._config_at=self.monotonic()
            def observe():
                return {'config':config[0],'symbol':config[1],
                        'account':self.get('/fapi/v3/account'),
                        'positions':self.get('/fapi/v3/positionRisk',{'symbol':'BTCUSDT'}),
                        'orders':self.get('/fapi/v1/openOrders',{} if scan_all else {'symbol':'BTCUSDT'}),
                        'algos':self.get('/fapi/v1/openAlgoOrders',{} if scan_all else {'symbol':'BTCUSDT'})}
            wallet_observed_from_ms=int(self.clock()*1000)
            first=observe()
            fills,fills_complete=self._recent_fills()
            second=observe()
            wallet_observed_until_ms=int(self.clock()*1000)
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
                          recent_fill_count=len(fills),last_fill_id=max((f['id'] for f in fills),default=-1),
                          recent_fill_window_complete=fills_complete,
                          observed_at_ms=int(self.clock()*1000),
                          wallet_observed_from_ms=wallet_observed_from_ms,
                          wallet_observed_until_ms=wallet_observed_until_ms,
                          recovery_history_complete=False)
            if scan_all:self.all_orders_checked_at=self.monotonic()
            self._cycle_config=config
            self.check_all_orders=False
            return report
        raise Unknown('Binance account changed during bounded reconciliation')

    def entry_snapshot(self, state, expected_uid, entry_id, *, flat_snapshot):
        """Observe only the first terminal IOC's fill for immediate protection.

        A fresh, verified flat boundary and the independently queried terminal
        order replace the ordinary snapshot's second account round. Every fill
        since that boundary must be this entry, including its price and fees.
        The safety write must still recheck the final native fill cursor. Any
        unavailable evidence falls back to snapshot plus full ownership recovery.
        """
        from .config import scope
        from .ownership import owned_observation
        try:
            now=int(self.clock()*1000)
            uid=str(expected_uid)
            observed_at=flat_snapshot.get('observed_at_ms')
            cursor=flat_snapshot.get('last_fill_id')
            if (getattr(self,'_verified_uid',None)!=uid or state.identity!=scope(self.environment,uid)
                    or flat_snapshot.get('account_uid')!=uid
                    or number(flat_snapshot.get('quantity_btc'))!=0
                    or number(flat_snapshot.get('entry'))!=0
                    or flat_snapshot.get('possible_entry_remainders')!=0
                    or flat_snapshot.get('open_orders')!=[] or flat_snapshot.get('open_algos')!=[]
                    or flat_snapshot.get('recent_fill_window_complete') is not True
                    or type(cursor) is not int or cursor < -1
                    or type(observed_at) is not int or not 0<=now-observed_at<=15000):
                raise Unknown('immediate entry lacks a fresh verified flat boundary')
            links=state.get('entry_campaigns') or {}
            if set(links)!={entry_id} or links[entry_id].get('add'):
                raise Unknown('immediate protection requires the campaign first entry')
            link=links[entry_id];start=link.get('prepared_at')
            if (type(start) is not int or start<=0 or start!=observed_at-15000
                    or type(link.get('after_trade_id')) is not int or link['after_trade_id']!=cursor
                    or type(link.get('campaign')) is not int or not link['campaign']):
                raise Unknown('entry journal does not bind this flat observation')
            row=state.db.execute('SELECT kind,payload,status FROM intents WHERE id=?',(entry_id,)).fetchone()
            if not row or row[0]!='binance_order' or row[2]!='confirmed' or state.pending():
                raise Unknown('entry has not been independently settled')
            payload=json.loads(row[1])
            if (payload.get('symbol')!='BTCUSDT' or payload.get('positionSide')!='BOTH'
                    or payload.get('side') not in ('BUY','SELL')
                    or payload.get('type')!='LIMIT' or payload.get('timeInForce')!='IOC'
                    or payload.get('newClientOrderId')!=entry_id
                    or payload.get('reduceOnly','false')!='false'
                    or payload.get('closePosition','false')!='false'):
                raise Unknown('immediate protection requires the journaled opening IOC')
            # Only recover_pending's native order query can establish this
            # archive; neither a POST result nor a confirmed local status is it.
            if entry_id not in (state.get('terminal_native_orders') or {}):
                raise Unknown('queried terminal entry evidence unavailable')
            parent=owned_observation(state,self,entry_id)['parent']
            if (parent.get('clientOrderId')!=entry_id or type(parent.get('orderId')) is not int
                    or parent['orderId']<=0 or parent.get('timeInForce')!='IOC'
                    or parent.get('reduceOnly') is not False or parent.get('closePosition',False) is not False
                    or parent.get('status') not in ('FILLED','CANCELED','EXPIRED','EXPIRED_IN_MATCH')):
                raise Unknown('native entry is not a terminal opening IOC')
            executed=number(parent.get('executedQty'),positive=True)
            config=getattr(self,'_cycle_config',None)
            if (config is None or self.check_all_orders
                    or not 0<=self.monotonic()-getattr(self,'_config_at',-60)<60
                    or not isinstance(config[1],list) or len(config[1])!=1):
                raise Unknown('fresh entry account configuration unavailable')
            wallet_from=int(self.clock()*1000)
            account=self.get('/fapi/v3/account')
            wallet_until=int(self.clock()*1000)
            positions=self.get('/fapi/v3/positionRisk',{'symbol':'BTCUSDT'})
            # One all-symbol round also rules out other pending account risk.
            orders=self.get('/fapi/v1/openOrders')
            algos=self.get('/fapi/v1/openAlgoOrders')
            if orders!=[] or algos!=[]:
                raise Unknown('orders changed after the verified flat entry')
            ticker=self.get('/fapi/v1/premiumIndex',{'symbol':'BTCUSDT'})
            if (not isinstance(ticker,dict) or ticker.get('symbol')!='BTCUSDT'
                    or type(ticker.get('time')) is not int
                    or abs(int(self.clock()*1000)-ticker['time'])>15000):
                raise Unknown('stale or invalid Binance mark observation')
            report=account_report(uid,config[0],config[1][0],account,positions,orders,algos,ticker['markPrice'])
            q=number(report['quantity_btc'])
            if abs(q)!=executed or (q>0)!=(parent['side']=='BUY'):
                raise Unknown('native position is not the terminal entry fill')
            query=({'symbol':'BTCUSDT','fromId':cursor+1,'limit':1000} if cursor>=0 else
                   {'symbol':'BTCUSDT','startTime':start,'endTime':int(self.clock()*1000),'limit':1000})
            fills=self._trade_page(query)
            if not fills or len(fills)>=1000:
                raise Unknown('immediate entry fill history is incomplete')
            total=notional=fees=number(0);last=cursor
            now=int(self.clock()*1000);limit=number(payload['price'],positive=True)
            for trade in fills:
                stamp=trade.get('time')
                if (trade.get('positionSide')!='BOTH' or trade.get('orderId')!=parent['orderId']
                        or trade.get('side')!=parent['side'] or trade['id']<=last
                        or type(stamp) is not int or not start<=stamp<=now
                        or trade.get('commissionAsset')!='USDT'):
                    raise Unknown('external or invalid fill after the entry flat boundary')
                amount=number(trade.get('qty'),positive=True);price=number(trade.get('price'),positive=True)
                fee=number(trade.get('commission'))
                if (fee<0 or number(trade.get('realizedPnl'))!=0
                        or (price>limit if q>0 else price<limit)):
                    raise Unknown('entry fill price or cost conflicts with its opening IOC')
                total+=amount;notional+=amount*price;fees+=fee;last=trade['id']
            # Compare in USDT: an entry price rounded by Binance may leave a
            # residue, bounded by the same native 1e-8 unit as account arithmetic.
            if (total!=executed or abs(total*number(report['entry'])-notional)>number('.00000001')
                    or number(report['wallet_usdt'])!=number(flat_snapshot['wallet_usdt'])-fees):
                raise Unknown('entry fills do not close native quantity, price and wallet')
            now=int(self.clock()*1000)
            if not 0<wallet_from<=wallet_until<=now:
                raise Unknown('entry wallet observation clock changed')
            if abs(now-ticker['time'])>15000:
                raise Unknown('entry mark expired while verifying native fills')
            report.update(mark_time=ticker['time'],mark_price=ticker['markPrice'],
                          recent_fill_count=len(fills),last_fill_id=last,recent_fill_window_complete=True,
                          observed_at_ms=now,wallet_observed_from_ms=wallet_from,
                          wallet_observed_until_ms=wallet_until,recovery_history_complete=False)
            self.all_orders_checked_at=self.monotonic()
            return report,parent
        except (Blocked,KeyError,TypeError,ValueError,ArithmeticError,AttributeError) as exc:
            raise Unknown('immediate entry proof unavailable; full reconciliation required') from exc

    def _trade_page(self, parameters):
        fills=self.get('/fapi/v1/userTrades',parameters)
        if not isinstance(fills,list) or len(fills)>1000:
            raise Unknown('recent trade response is missing or oversized')
        if any(not isinstance(f,dict) or f.get('symbol')!='BTCUSDT' for f in fills):
            raise Unknown('unexpected recent trade scope')
        if (any(type(f.get('id')) is not int or f['id']<0 for f in fills)
                or len({f['id'] for f in fills})!=len(fills)):
            raise Unknown('invalid native fill cursor')
        if 'startTime' in parameters or 'endTime' in parameters:
            if any(type(f.get('time')) is not int or not parameters.get('startTime',0)<=f['time']<=parameters.get('endTime',int(self.clock()*1000)) for f in fills):
                raise Unknown('fill response is outside the requested time window')
        return fills

    def _recent_fills(self):
        """Verify the latest BTCUSDT cursor, independently of full ownership history."""
        fills=self._trade_page({'symbol':'BTCUSDT','limit':1000})
        if len(fills)<1000:
            return fills,True
        seen={f['id'] for f in fills}
        cursor=max(seen)
        for _ in range(20):
            page=self._trade_page({'symbol':'BTCUSDT','fromId':cursor+1,'limit':1000})
            if not page:
                return fills,True
            for trade in page:
                if trade['id']<=cursor or trade['id'] in seen:
                    raise Unknown('fill id page did not advance')
                seen.add(trade['id'])
                fills.append(trade)
            cursor=max(trade['id'] for trade in page)
            if len(page)<1000:
                return fills,True
        raise Unknown('recent fill cursor exceeds bounded pages')


def _error_body(error):
    """Native error code and message of an HTTP error body; None when unreadable."""
    try:
        raw = error.read(4097)[:4096].decode()
    except Exception:
        return None, None
    try:
        body = json.loads(raw)
    except ValueError:
        return None, None  # a proxy or CDN text body is not a Binance answer
    if not isinstance(body, dict):
        return None, None
    code, message = body.get('code'), body.get('msg')
    return (code if type(code) is int else None), (message.strip() if isinstance(message, str) else None)


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
        return json.dumps(stable,sort_keys=True,separators=(',',':'),allow_nan=False,default=str)
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
    # An over-collateralised isolated long reports 0: it cannot be liquidated.
    liquidation=(number(pos.get('liquidationPrice')) if q>0 else
                 number(pos.get('liquidationPrice'),positive=True) if q else number(0))
    if liquidation<0:raise Unknown('invalid native liquidation price')
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
    return {'status':'read_only_observation','account_uid':str(uid),'symbol':'BTCUSDT',
            'wallet_usdt':str(wallet),'equity_usdt':str(wallet+q*(mark-entry)),
            'available_usdt':str(number(account['availableBalance'])) if 'availableBalance' in account else None,
            'native_account_equity_usdt':str(wallet+unrealized),
            'quantity_btc':str(q),'entry':str(entry),'native_full_position_protected':protected,
            'isolated_wallet_usdt':str(isolated),'native_liquidation_price':str(liquidation),
            'stop_before_liquidation':bool(safe_stops),
            'protective_algos':protective,'possible_entry_remainders':len(entries),
            'open_orders':orders,'open_algos':algos}


def market_quantity(maximum, mark, instrument, *, reduce_only=False, order='MARKET'):
    """Round DOWN a risk-sized quantity using one observed native filter snapshot.

    LIMIT uses LOT_SIZE. MARKET also uses MARKET_LOT_SIZE. A reduce-only order
    may be below the minimum notional. This validates quantity shape, not fill
    certainty. Never rounds up past the caller's risk budget.
    """
    if order not in ('MARKET', 'LIMIT'):
        raise Blocked('unknown order quantity rule')
    from math import lcm
    maximum=number(maximum);mark=number(mark,positive=True)
    if maximum<0 or instrument.get('symbol')!='BTCUSDT':
        raise Blocked('invalid BTCUSDT risk-sized quantity')
    filters=instrument.get('filters')
    if not isinstance(filters,list):raise Unknown('missing native order filters')
    selected={}
    required=('LOT_SIZE','MIN_NOTIONAL') if order=='LIMIT' else ('LOT_SIZE','MARKET_LOT_SIZE','MIN_NOTIONAL')
    for name in required:
        rows=[r for r in filters if r.get('filterType')==name]
        if len(rows)!=1:raise Unknown('missing or duplicate native quantity filter')
        selected[name]=rows[0]
    lots=[selected[name] for name in required if name!='MIN_NOTIONAL']
    steps=[number(r.get('stepSize')) for r in lots]
    minima=[number(r.get('minQty')) for r in lots]
    maxima=[number(r.get('maxQty'),positive=True) for r in lots]
    notional=number(selected['MIN_NOTIONAL'].get('notional'))
    if min(steps+minima+[notional])<0 or max(minima)>min(maxima):
        raise Unknown('inconsistent native quantity limits')
    positive=[s for s in steps if s>0]
    if not positive:raise Unknown('native quantity increment unavailable')
    unit=Decimal(10)**min(s.as_tuple().exponent for s in positive)
    step=unit*lcm(*(int(s/unit) for s in positive))
    q=(min(maximum,*maxima)//step)*step
    if q<max(minima) or (not reduce_only and q*mark<notional):return Decimal(0)
    return q
