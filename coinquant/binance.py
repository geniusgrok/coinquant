"""Single Binance adapter with bounded reads and explicitly authorized order writes.

Private reads require explicitly supplied credentials; raw identity/balance
responses must never be printed or persisted.
"""
import hashlib
import hmac
import json
import time
from collections import deque
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from coinquant.types import Blocked, Unknown, number

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


class Binance:
    def __init__(self, *, key='', secret='', opener=None, clock=time.time, authorize_writes=False):
        self.key, self.secret = key, secret
        self.opener = opener or build_opener(NoRedirect())
        self.clock = clock
        self.authorize_writes = authorize_writes is True
        self.cooldown_until = 0
        self.request_weights = deque()
        self.check_all_orders = True
        self.deadline = time.monotonic() + 120

    def begin_cycle(self, seconds=120):
        self.deadline = time.monotonic() + min(120, max(1, seconds))
        self.check_all_orders = True

    def ensure_capacity(self, reserve):
        now=time.monotonic()
        while self.request_weights and self.request_weights[0][0]<=now-60:
            self.request_weights.popleft()
        if sum(cost for _,cost in self.request_weights)+reserve>2200:
            raise Unknown('local request-weight reserve unavailable; wait before new risk')

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
        if method == 'POST' and path.endswith('/order'):
            if (p.get('positionSide') != 'BOTH' or p.get('side') not in ('BUY', 'SELL')
                    or not str(p.get('newClientOrderId', '')).startswith('cq-')
                    or number(p.get('quantity'), positive=True) <= 0):
                raise Blocked('invalid identified ordinary order')
            if p.get('reduceOnly') != 'true' and (p.get('type') != 'LIMIT' or p.get('timeInForce') != 'IOC'):
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
                 '/fapi/v1/order':1,'/fapi/v1/algoOrder':1,'/fapi/v1/positionMargin':1}
        weight=40 if path.endswith(('/openOrders','/openAlgoOrders')) and 'symbol' not in params else weights[path]
        self.ensure_capacity(weight)
        if any(k in params for k in ('signature', 'timestamp', 'recvWindow')):
            raise Blocked('caller cannot override request signing fields')
        if 'symbol' in params and params['symbol'] != 'BTCUSDT':
            raise Blocked('only BTCUSDT is supported')
        headers = {'User-Agent':'coinquant'}
        if private:
            if not self.key or not self.secret:
                raise Blocked('explicit Binance credentials required for private reads')
            params.update(timestamp=int(self.clock()*1000), recvWindow=5000)
            headers['X-MBX-APIKEY'] = self.key
        query = urlencode(sorted(params.items()))
        if private:
            query += '&signature=' + hmac.new(self.secret.encode(),query.encode(),hashlib.sha256).hexdigest()
        host = 'api.binance.com' if path == '/api/v3/account' else 'fapi.binance.com'
        if method == 'GET':
            url, data = 'https://'+host+path+('?' + query if query else ''), None
        else:
            url, data = 'https://'+host+path, query.encode()
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        request = Request(url, data=data, headers=headers, method=method)
        remaining = self.deadline-time.monotonic()
        if time.monotonic() < self.cooldown_until:
            raise Unknown('Binance rate limit cooldown; no request sent')
        if remaining <= 0: raise Unknown('bounded Binance observation deadline exceeded')
        try:
            self.request_weights.append((time.monotonic(),weight))
            with self.opener.open(request, timeout=min(8,remaining)) as response:
                raw = response.read(2000001)
            if len(raw)>2000000: raise Unknown('oversized Binance response')
            result = json.loads(raw)
        except HTTPError as exc:
            if exc.code in (418,429):
                try:delay=max(60,min(86400,float(exc.headers.get('Retry-After','60'))))
                except (TypeError,ValueError):delay=60
                self.cooldown_until=time.monotonic()+delay
            raise Unknown('Binance HTTP outcome unresolved; query stable identity after cooldown') from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise Unknown('Binance request unavailable; read by stable identity before any retry') from None
        if not isinstance(result,(dict,list)) or (isinstance(result,dict) and 'code' in result and not (method != 'GET' and result['code'] == 200)):
            raise Unknown('unexpected Binance read response')
        return result

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
        for cursor in range(start,end,120*interval):
            page_end=min(end,cursor+120*interval)
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
        observed=self.query_intent(identity,conditional=True)
        parent,child=observed['parent'],observed['child']
        if parent.get('algoStatus') not in ('CANCELED','EXPIRED','REJECTED','FINISHED'):return False
        if child is None:
            if parent['algoStatus']=='FINISHED':raise Unknown('finished protection lacks child evidence')
            return True
        original=number(child.get('origQty'),positive=True);filled=number(child.get('executedQty'))
        if original<=0 or not 0<=filled<=original:raise Unknown('invalid protection child quantities')
        status=child.get('status')
        if status=='FILLED' and filled!=original:raise Unknown('incomplete filled protection child')
        if status=='REJECTED' and filled:raise Unknown('rejected child with fills')
        return status in ('FILLED','CANCELED','EXPIRED','EXPIRED_IN_MATCH','REJECTED')

    def recover_pending(self, state):
        """Read-only terminal reconciliation; no missing-order retry inference.

        Binance intents store the original native request fields. Unknown or
        unsupported intent kinds stay pending; never infer resolution.
        A canceled conditional parent does not settle a still-active child.
        """
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
            if kind not in ('binance_order', 'binance_algo'):
                continue
            try:
                conditional = kind == 'binance_algo'
                observed = self.query_intent(intent['id'], conditional=conditional)
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
                    parent_terminal = parent.get('algoStatus') in ('FINISHED', 'CANCELED', 'EXPIRED', 'REJECTED')
                    if not parent_terminal:
                        continue
                    if child is None:
                        # FINISHED without child identity is insufficient evidence.
                        if parent.get('algoStatus') == 'FINISHED':
                            continue
                        state.finish(intent['id'], 'confirmed', {'algo_status': parent['algoStatus'], 'child': None})
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
                state.finish(intent['id'], 'confirmed', {'status': status, 'executed_quantity': str(executed)})
                resolved += 1
            except (Blocked, Unknown, KeyError, TypeError, ValueError, ArithmeticError):
                # Keep independent recoverable intents moving, never erase unknowns.
                continue
        return {'resolved': resolved, 'pending': len(state.pending())}

    def snapshot(self, expected_uid):
        uid=self.account_identity()
        if uid!=str(expected_uid):raise Blocked('Binance account UID does not match the configured account')
        scan_all=self.check_all_orders
        for _ in range(2):
            def observe():
                return {'config':self.get('/fapi/v1/accountConfig'),
                        'symbol':self.get('/fapi/v1/symbolConfig',{'symbol':'BTCUSDT'}),
                        'account':self.get('/fapi/v3/account'),
                        'positions':self.get('/fapi/v3/positionRisk',{'symbol':'BTCUSDT'}),
                        'orders':self.get('/fapi/v1/openOrders',{} if scan_all else {'symbol':'BTCUSDT'}),
                        'algos':self.get('/fapi/v1/openAlgoOrders',{} if scan_all else {'symbol':'BTCUSDT'})}
            first=observe()
            fills=self.get('/fapi/v1/userTrades',{'symbol':'BTCUSDT','limit':1000})
            second=observe()
            if not isinstance(fills,list) or len(fills)>=1000:
                raise Unknown('recent trade response is missing or may be truncated')
            if any(f.get('symbol')!='BTCUSDT' for f in fills):
                raise Unknown('unexpected recent trade scope')
            if (any(type(f.get('id')) is not int or f['id']<0 for f in fills)
                    or len({f['id'] for f in fills})!=len(fills)):
                raise Unknown('invalid native fill cursor')
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
                          observed_at_ms=int(self.clock()*1000),recovery_history_complete=False)
            self.check_all_orders=False
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
    return {'status':'read_only_observation','account_uid':str(uid),'symbol':'BTCUSDT',
            'wallet_usdt':str(wallet),'equity_usdt':str(wallet+q*(mark-entry)),
            'available_usdt':str(number(account['availableBalance'])) if 'availableBalance' in account else None,
            'native_account_equity_usdt':str(wallet+unrealized),
            'quantity_btc':str(q),'entry':str(entry),'native_full_position_protected':protected,
            'isolated_wallet_usdt':str(isolated),'native_liquidation_price':str(liquidation),
            'stop_before_liquidation':bool(safe_stops),
            'protective_algos':protective,'possible_entry_remainders':len(entries),
            'open_orders':orders,'open_algos':algos,
            'qualification':'NOT_QUALIFIED','writes_supported':False}


def market_quantity(maximum, mark, instrument, *, reduce_only=False):
    """Round DOWN a risk-sized quantity using one observed native filter snapshot.

    This validates quantity/minimum shape, not fill certainty or historical rules.
    Caller must retain snapshot provenance and enforce execution lifecycle gates.
    Never rounds up to manufacture an executable order outside its risk budget.
    """
    from decimal import Decimal
    from math import lcm
    maximum=number(maximum);mark=number(mark,positive=True)
    if maximum<0 or instrument.get('symbol')!='BTCUSDT':
        raise Blocked('invalid BTCUSDT risk-sized quantity')
    filters=instrument.get('filters')
    if not isinstance(filters,list):raise Unknown('missing native order filters')
    selected={}
    for name in ('LOT_SIZE','MARKET_LOT_SIZE','MIN_NOTIONAL'):
        rows=[r for r in filters if r.get('filterType')==name]
        if len(rows)!=1:raise Unknown('missing or duplicate native quantity filter')
        selected[name]=rows[0]
    lots=[selected['LOT_SIZE'],selected['MARKET_LOT_SIZE']]
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
