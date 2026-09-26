"""Rebuild ownership from durable entry identity and complete native fill history."""
import json
import calendar
from datetime import datetime, timezone
from decimal import Decimal as D
from .types import Unknown, number


TERMINAL = ('FILLED','CANCELED','EXPIRED','EXPIRED_IN_MATCH','REJECTED')


def owned_observation(state,reader,identity,*,conditional=False):
    """Archive only immutable, verified terminal native orders, never an ACK."""
    row=state.db.execute('SELECT kind,payload FROM intents WHERE id=?',(identity,)).fetchone()
    if not row or row[0]!=('binance_algo' if conditional else 'binance_order'):
        raise Unknown('missing durable native order ownership')
    payload=json.loads(row[1])
    archived=state.get('terminal_native_orders') or {}
    observed=archived.get(identity) or (state.get('settled_protection') or {}).get(identity)
    if observed is None:observed=reader.query_intent(identity,conditional=conditional)
    parent=observed['parent'];order=observed['child'] if conditional else parent
    for field in ('symbol','side','positionSide'):
        if parent.get(field)!=payload.get(field):raise Unknown('owned order scope changed')
    if parent.get('orderType' if conditional else 'type')!=payload.get('type'):
        raise Unknown('owned order type changed')
    for field in ('reduceOnly','closePosition','priceProtect'):
        if field in payload and parent.get(field) is not {'true':True,'false':False}.get(payload[field]):
            raise Unknown('owned order execution flag changed')
    if conditional:
        if (parent.get('workingType')!=payload.get('workingType')
                or number(parent.get('triggerPrice'),positive=True)!=number(payload.get('triggerPrice'),positive=True)):
            raise Unknown('owned protection differs from its durable request')
    elif 'price' in payload and number(parent.get('price'))!=number(payload['price']):
        raise Unknown('owned entry price changed')
    terminal=(not conditional or parent.get('algoStatus') in ('FINISHED','CANCELED','EXPIRED','REJECTED'))
    if order is None:
        terminal &= parent.get('algoStatus')!='FINISHED'
    else:
        if (any(order.get(k)!=parent.get(k) for k in ('symbol','side','positionSide'))
                or not 0<=number(order.get('executedQty'))<=number(order.get('origQty'),positive=True)):
            raise Unknown('invalid native order fill evidence')
        if not conditional and number(order['origQty'])!=number(payload.get('quantity'),positive=True):
            raise Unknown('owned order quantity changed')
        status=order.get('status');executed=number(order['executedQty'])
        if (status=='FILLED' and executed!=number(order['origQty'])
                or status in ('NEW','REJECTED') and executed):
            raise Unknown('inconsistent native order status')
        terminal &= status in TERMINAL
    if terminal and identity not in archived:
        archived[identity]=observed;state.set('terminal_native_orders',archived)
    return observed


def fill_history(reader,start,end,after_id=None):
    """Complete time windows; dense windows continue by ID, never time+ID.

    An existing flat/campaign cursor includes even >1000 fills in one millisecond.
    Older journals without that cursor split time windows until completeness is
    provable; an unresolved saturated millisecond remains unknown.
    """
    trades=[];cursor=after_id
    windows=[(b,min(end,b+7*86400000-1)) for b in range(start,end+1,7*86400000)][::-1]
    while windows:
        begin,finish=windows.pop()
        page=reader.get('/fapi/v1/userTrades',{'symbol':'BTCUSDT','startTime':begin,'endTime':finish,'limit':1000})
        if not isinstance(page,list) or len(page)>1000:raise Unknown('invalid fill history page')
        if len(page)==1000 and cursor is None:
            if begin==finish:raise Unknown('dense legacy fill window lacks a verified ID boundary')
            middle=(begin+finish)//2
            windows.extend(((middle+1,finish),(begin,middle)));continue
        if len(page)==1000:
            next_id=cursor+1;previous_time=-1;collected={}
            required={}
            for trade in page:
                tid=trade.get('id');stamp=trade.get('time')
                if type(tid) is not int or tid<0 or tid in required or type(stamp) is not int or not begin<=stamp<=finish:
                    raise Unknown('invalid saturated fill page')
                required[tid]=trade
            while True:
                part=reader.get('/fapi/v1/userTrades',{'symbol':'BTCUSDT','fromId':next_id,'limit':1000})
                if not isinstance(part,list) or len(part)>1000:raise Unknown('invalid ID fill page')
                previous=next_id-1;past_end=False
                for trade in part:
                    tid=trade.get('id');stamp=trade.get('time')
                    if type(tid) is not int or tid<=previous or type(stamp) is not int or stamp<previous_time:
                        raise Unknown('fill ID page did not advance chronologically')
                    previous,previous_time=tid,stamp
                    if stamp>finish:past_end=True
                    elif stamp>=begin:trades.append(trade);collected[tid]=trade
                if past_end or len(part)<1000:break
                next_id=previous+1
            if any(tid>cursor and collected.get(tid)!=trade for tid,trade in required.items()):
                raise Unknown('time and ID fill pages disagree')
            if collected:cursor=max(collected)
        else:
            ids=set()
            for trade in page:
                tid=trade.get('id');stamp=trade.get('time')
                if type(tid) is not int or tid<0 or tid in ids or type(stamp) is not int or not begin<=stamp<=finish:
                    raise Unknown('invalid fill chronology')
                ids.add(tid)
                if after_id is not None and tid<=after_id:continue
                trades.append(trade);cursor=max(cursor if cursor is not None else -1,tid)
    return trades


def reconcile(state, reader, model, snapshot):
    links=state.get('entry_campaigns') or {}
    if not links:
        if number(snapshot['quantity_btc']):raise Unknown('entry campaign journal unavailable')
        return {'status':'flat_without_entry_journal'}
    # Only one entry campaign can own the one-way isolated position. Later
    # rejected/zero-fill orders must not hide an older actually filled entry.
    filled=[];native={}
    for identity,link in links.items():
        observed=owned_observation(state,reader,identity)['parent']
        row=state.db.execute('SELECT kind,payload FROM intents WHERE id=?',(identity,)).fetchone()
        if not row or row[0]!='binance_order':raise Unknown('missing durable entry intent')
        payload=json.loads(row[1])
        if any(observed.get(k)!=payload.get(k) for k in ('symbol','side','positionSide','type')):
            raise Unknown('entry identity differs from original request')
        executed=number(observed['executedQty']);original=number(observed['origQty'],positive=True)
        if original!=number(payload['quantity'],positive=True) or not 0<=executed<=original:
            raise Unknown('inconsistent entry fill quantities')
        status=observed.get('status')
        if (status not in ('NEW','PARTIALLY_FILLED','FILLED','CANCELED','EXPIRED','EXPIRED_IN_MATCH','REJECTED')
                or status=='FILLED' and executed!=original or status in ('NEW','REJECTED') and executed):
            raise Unknown('inconsistent entry status')
        if executed:
            filled.append((link['prepared_at'],identity,link,observed))
        native[str(observed['orderId'])]=(identity,observed)
    if not filled:
        if number(snapshot['quantity_btc']):raise Unknown('position has no verified campaign fill')
        terminal=all(o['status'] in ('FILLED','CANCELED','EXPIRED','EXPIRED_IN_MATCH','REJECTED') for _,o in native.values())
        if terminal and not snapshot['possible_entry_remainders'] and not state.pending():
            again=reader.snapshot(snapshot['account_uid'])
            if any(again.get(k)!=snapshot.get(k) for k in ('quantity_btc','wallet_usdt','entry','possible_entry_remainders')):
                raise Unknown('account changed while settling zero-fill entries')
            _archive_links(state,links)
        return {'status':'no_campaign_fill'}
    start,identity,link,entry=max(filled,key=lambda x:x[0])
    now=int(reader.clock()*1000)
    current=datetime.fromtimestamp(now/1000,timezone.utc)
    month_index=current.year*12+current.month-1-3
    year,month=divmod(month_index,12);month+=1
    earliest=current.replace(year=year,month=month,day=min(current.day,calendar.monthrange(year,month)[1]))
    if type(start) is not int or not 0<start<=now:
        raise Unknown('invalid entry history boundary')
    coverage=state.get('ownership_coverage') or {}
    saved=[];begin=start;cursor=link.get('after_trade_id')
    if coverage.get('entry_id')==identity:
        if coverage.get('start')!=start or not start<=coverage['through']<=now:
            raise Unknown('invalid durable history coverage')
        saved=[json.loads(r[0]) for r in state.db.execute('SELECT payload FROM native_fills WHERE entry_id=?',(identity,))]
        begin=max(start,coverage['through']-15000)
        preceding=[t['id'] for t in saved if t['time']<begin]
        if preceding:cursor=max([cursor if cursor is not None else -1]+preceding)
    if begin<int(earliest.timestamp()*1000):
        raise Unknown('fill history outside bounded recovery; verified archive required')
    observed_trades=fill_history(reader,begin,now,cursor)
    merged={t['id']:t for t in saved}
    for trade in observed_trades:
        if link.get('after_trade_id') is not None and trade['id']<=link['after_trade_id']:continue
        if trade['id'] in merged and merged[trade['id']]!=trade:
            raise Unknown('native fill changed after durable observation')
        merged[trade['id']]=trade
    trades=sorted(merged.values(),key=lambda t:(t['time'],t['id']))
    # Resolve owned protection children and reductions; ACK alone is not used.
    for oid,kind,raw in state.db.execute("SELECT id,kind,payload FROM intents WHERE updated>=?",(start/1000,)):
        if kind not in ('binance_order','binance_algo') or oid in links:continue
        payload=json.loads(raw)
        if payload.get('reduceOnly')!='true' and payload.get('closePosition')!='true':continue
        observed=owned_observation(state,reader,oid,conditional=kind=='binance_algo')
        parent=observed['parent'];order=observed['child'] if kind=='binance_algo' else parent
        if any(parent.get(k)!=payload.get(k) for k in ('symbol','side','positionSide')):
            raise Unknown('reduction scope mismatch')
        flag='closePosition' if payload.get('closePosition')=='true' else 'reduceOnly'
        if parent.get(flag) is not True:raise Unknown('reduction intent differs from native order')
        if order is not None:native[str(order['orderId'])]=(oid,order)
    total=D(0);entry_total=D(0)
    for trade in trades:
        if trade.get('symbol')!='BTCUSDT' or trade.get('positionSide')!='BOTH' or trade.get('side') not in ('BUY','SELL'):
            raise Unknown('unexpected native fill scope')
        order=native.get(str(trade['orderId']))
        if order is None or trade['side']!=order[1]['side']:
            raise Unknown('external or unowned fill prevents campaign inference')
        if order[0] in links and order[0]!=identity:
            raise Unknown('multiple entry campaigns overlap in native fills')
        qty=number(trade['qty'],positive=True)
        total+=qty if trade['side']=='BUY' else -qty
        if order[0]==identity:entry_total+=qty
    if entry_total!=number(entry['executedQty']) or total!=number(snapshot['quantity_btc']):
        raise Unknown('native fills do not reconcile to current position')
    again=reader.snapshot(snapshot['account_uid'])
    if any(again[k]!=snapshot[k] for k in ('quantity_btc','entry','wallet_usdt','possible_entry_remainders')):
        raise Unknown('account changed during ownership recovery')
    campaign=link['campaign']
    if type(campaign) is not int or not 0<campaign<=model.last:raise Unknown('invalid campaign clock')
    with state.db:
        for trade in trades:
            prior=state.db.execute('SELECT entry_id,payload FROM native_fills WHERE trade_id=?',(trade['id'],)).fetchone()
            if prior and (prior[0]!=identity or json.loads(prior[1])!=trade):
                raise Unknown('durable fill identity conflicts')
            state.db.execute('INSERT OR IGNORE INTO native_fills VALUES (?,?,?)',
                             (trade['id'],identity,json.dumps(trade,sort_keys=True)))
        state.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',
                         ('ownership_coverage',json.dumps(dict(entry_id=identity,start=start,through=now))))
    model.consumed=max(model.consumed or campaign,campaign) if not total else campaign
    model.position_campaign=campaign if total else None
    state.set('linear_campaign',model.checkpoint())
    if not total and snapshot['possible_entry_remainders']==0 and all(
            observed['status'] not in ('NEW','PARTIALLY_FILLED')
            for oid,observed in native.values() if oid in links):
        # Keep the campaign audit trail, but do not query terminal old entries
        # forever after an independently reconciled flat boundary.
        _archive_links(state,links)
    return {'status':'reconciled','campaign':campaign,'quantity':str(total),'fill_count':len(trades),
            'protection_confirmed':snapshot.get('native_full_position_protected',False),
            'entry_remainder':snapshot['possible_entry_remainders']}


def _archive_links(state,links):
    settled=state.get('settled_entry_campaigns') or {}
    settled.update(links)
    with state.db:
        for key,value in (('settled_entry_campaigns',settled),('entry_campaigns',{})):
            state.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',(key,json.dumps(value,sort_keys=True)))
