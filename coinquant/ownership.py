"""Rebuild ownership from durable entry identity and complete native fill history."""
import json
import calendar
from datetime import datetime, timezone
from decimal import Decimal as D
from .types import Unknown, number


def reconcile(state, reader, model, snapshot):
    links=state.get('entry_campaigns') or {}
    if not links:
        if number(snapshot['quantity_btc']):raise Unknown('entry campaign journal unavailable')
        return {'status':'flat_without_entry_journal'}
    # Only one entry campaign can own the one-way isolated position. Later
    # rejected/zero-fill orders must not hide an older actually filled entry.
    filled=[];native={}
    for identity,link in links.items():
        observed=reader.query_intent(identity)['parent']
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
        return {'status':'no_campaign_fill'}
    start,identity,link,entry=max(filled,key=lambda x:x[0])
    now=int(reader.clock()*1000)
    current=datetime.fromtimestamp(now/1000,timezone.utc)
    month_index=current.year*12+current.month-1-3
    year,month=divmod(month_index,12);month+=1
    earliest=current.replace(year=year,month=month,day=min(current.day,calendar.monthrange(year,month)[1]))
    if type(start) is not int or not int(earliest.timestamp()*1000)<=start<=now:
        raise Unknown('fill history outside bounded recovery; verified archive required')
    trades=[];ids=set()
    for begin in range(start,now+1,7*86400000):
        end=min(now,begin+7*86400000-1)
        page=reader.get('/fapi/v1/userTrades',{'symbol':'BTCUSDT','startTime':begin,'endTime':end,'limit':1000})
        if not isinstance(page,list) or len(page)>=1000:raise Unknown('fill history may be truncated')
        for trade in page:
            if trade['id'] in ids or type(trade['time']) is not int or not begin<=trade['time']<=end:
                raise Unknown('invalid fill chronology')
            ids.add(trade['id']);trades.append(trade)
    # Resolve owned protection children and reductions; ACK alone is not used.
    for oid,kind,raw in state.db.execute("SELECT id,kind,payload FROM intents WHERE updated>=?",(start/1000,)):
        if kind not in ('binance_order','binance_algo') or oid in links:continue
        payload=json.loads(raw)
        if payload.get('reduceOnly')!='true' and payload.get('closePosition')!='true':continue
        observed=reader.query_intent(oid,conditional=kind=='binance_algo')
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
    model.consumed=max(model.consumed or campaign,campaign) if not total else campaign
    model.position_campaign=campaign if total else None
    state.set('linear_campaign',model.checkpoint())
    if not total and snapshot['possible_entry_remainders']==0 and all(
            observed['status'] not in ('NEW','PARTIALLY_FILLED')
            for oid,observed in native.values() if oid in links):
        # Keep the campaign audit trail, but do not query terminal old entries
        # forever after an independently reconciled flat boundary.
        settled=state.get('settled_entry_campaigns') or {}
        settled.update(links)
        with state.db:
            for key,value in (('settled_entry_campaigns',settled),('entry_campaigns',{})):
                state.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',(key,json.dumps(value,sort_keys=True)))
    return {'status':'reconciled','campaign':campaign,'quantity':str(total),'fill_count':len(trades),
            'protection_confirmed':snapshot.get('native_full_position_protected',False),
            'entry_remainder':snapshot['possible_entry_remainders']}
