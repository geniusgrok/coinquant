"""Native Binance safety operations; no entry or network writer is exposed.

The injected sender is used by offline lifecycle tests. Production CLI stays
read-only until authorized native lifecycle validation and economic acceptance.
"""
from decimal import Decimal as D
from .state import client_id
from .binance import market_quantity
from .types import Blocked, Unknown


def _gate(reader, state, uid, authorized):
    if authorized is not True:raise Blocked('explicit operation authorization required')
    if state.identity != f'binance:BTCUSDT:live:{uid}':
        raise Blocked('state and native reader account scope differ')
    snapshot=reader.snapshot(uid)
    if snapshot['account_uid']!=str(uid):raise Blocked('account mismatch')
    return snapshot


def _once(state, identity, kind, payload, send, method, path):
    # Existing intent means possibly sent, even after a crash before HTTP began.
    old=state.db.execute('SELECT kind,payload FROM intents WHERE id=?',(identity,)).fetchone()
    if old:
        import json
        if old[0]!=kind or json.loads(old[1])!=payload:raise Unknown('stable intent payload changed')
        return
    state.prepare(identity,kind,payload)
    try:send(method,path,payload)
    except Exception:
        # Never interpret transport/API errors as proof that the write failed.
        pass


def protect_existing(reader,state,send,uid,epoch,stop,take,*,instrument,authorized=False):
    """Install full-position SL then TP, retaining every existing protection.

    There must be no possible entry remainder. A partial position is protected
    by closePosition, never by the requested entry size. ACK is not readback.
    """
    before=_gate(reader,state,uid,authorized)
    q=D(before['quantity_btc']);mark=D(before['mark_price']);liq=D(before['native_liquidation_price'])
    stop,take=D(stop),D(take)
    filters=[f for f in instrument.get('filters',[]) if f.get('filterType')=='PRICE_FILTER']
    if instrument.get('symbol')!='BTCUSDT' or len(filters)!=1:raise Blocked('missing native price rule')
    rule=filters[0];tick=D(rule['tickSize'])
    if tick<=0 or any(p%tick or not D(rule['minPrice'])<=p<=D(rule['maxPrice']) for p in (stop,take)):
        raise Blocked('protection violates native price filter')
    if not q or before['possible_entry_remainders']:raise Blocked('flat or entry remainder unresolved')
    if not (0<liq<stop<mark<take if q>0 else 0<take<mark<stop<liq):
        raise Blocked('invalid protection or liquidation geometry')
    for kind,trigger in (('STOP_MARKET',stop),('TAKE_PROFIT_MARKET',take)):
        identity=client_id(state.identity,epoch,kind)
        payload=dict(symbol='BTCUSDT',positionSide='BOTH',side='SELL' if q>0 else 'BUY',
            algoType='CONDITIONAL',type=kind,triggerPrice=str(trigger),closePosition='true',
            workingType='MARK_PRICE',priceProtect='false',clientAlgoId=identity)
        _once(state,identity,'binance_algo',payload,send,'POST','/fapi/v1/algoOrder')
        observed=reader.query_intent(identity,conditional=True);parent=observed['parent']
        expected=dict(symbol='BTCUSDT',positionSide='BOTH',side=payload['side'],
            orderType=kind,closePosition=True,workingType='MARK_PRICE',priceProtect=False,
            clientAlgoId=identity,algoStatus='NEW')
        if (any(parent.get(k)!=v for k,v in expected.items())
                or D(parent.get('triggerPrice','0'))!=trigger or observed['child'] is not None):
            raise Unknown('native protection not confirmed active; reconcile exposure')
        state.finish(identity,'confirmed',{'algo_id':parent['algoId'],'status':'NEW'})
    after=reader.snapshot(uid)
    if (D(after['quantity_btc'])!=q or after['possible_entry_remainders']
            or not after['native_full_position_protected'] or not after['stop_before_liquidation']):
        raise Unknown('exposure changed or full-position protection not established')
    return after


def cancel_entry(reader,state,send,uid,epoch,entry_id,*,authorized=False):
    """Cancel an owned ordinary entry and settle any cancel/fill race by query.

    Does not assume cancel ACK means zero fill; conditional entries are unsupported.
    After terminality the caller must read full exposure before risk removal.
    """
    _gate(reader,state,uid,authorized)
    row=state.db.execute('SELECT kind FROM intents WHERE id=?',(entry_id,)).fetchone()
    if not row or row[0]!='binance_order':raise Blocked('entry ownership is not durable')
    original=reader.query_intent(entry_id)['parent']
    if original.get('reduceOnly') is not False:raise Blocked('not a risk-increasing entry')
    identity=client_id(state.identity,epoch,'cancel:'+entry_id)
    payload=dict(symbol='BTCUSDT',origClientOrderId=entry_id)
    terminal=('FILLED','CANCELED','EXPIRED','EXPIRED_IN_MATCH','REJECTED')
    if original.get('status') not in terminal:
        _once(state,identity,'binance_cancel',payload,send,'DELETE','/fapi/v1/order')
    final=reader.query_intent(entry_id)['parent']
    qty=D(final.get('origQty','0'));filled=D(final.get('executedQty','-1'))
    if (final.get('status') not in terminal or not 0<=filled<=qty or qty<=0
            or (final['status']=='FILLED' and filled!=qty)):
        raise Unknown('entry remainder/child fill is not terminal')
    if state.db.execute('SELECT 1 FROM intents WHERE id=?',(identity,)).fetchone():
        state.finish(identity,'confirmed',{'status':final['status'],'executed_quantity':str(filled)})
    reader.recover_pending(state)
    return reader.snapshot(uid)


def reduce_existing(reader,state,send,uid,epoch,quantity,*,instrument,authorized=False):
    """Bounded reduce-only market request; caller supplies rule-rounded quantity."""
    before=_gate(reader,state,uid,authorized);q=D(before['quantity_btc']);qty=D(quantity)
    if before['possible_entry_remainders'] or not 0<qty<=abs(q):raise Blocked('unsafe reduction')
    if market_quantity(qty,before['mark_price'],instrument)!=qty:raise Blocked('reduction violates native quantity rule')
    identity=client_id(state.identity,epoch,'reduce')
    payload=dict(symbol='BTCUSDT',positionSide='BOTH',side='SELL' if q>0 else 'BUY',
        type='MARKET',quantity=str(qty),reduceOnly='true',newClientOrderId=identity)
    _once(state,identity,'binance_order',payload,send,'POST','/fapi/v1/order')
    reader.recover_pending(state)
    if any(p['id']==identity for p in state.pending()):raise Unknown('reduction result unresolved')
    after=reader.snapshot(uid);remaining=D(after['quantity_btc'])
    if after['possible_entry_remainders'] or remaining*q<0 or abs(remaining)>abs(q)-qty:
        raise Unknown('risk removal readback conflicts')
    return after


def add_margin(reader,state,send,uid,epoch,target,*,authorized=False):
    """Model-selected isolated wallet target; never withdraw or retry unknown adds.

    Binance margin writes have no client transaction ID. Only a successful response
    plus native wallet readback resolves this intent; uncertain writes stay blocked.
    """
    before=_gate(reader,state,uid,authorized)
    if not D(before['quantity_btc']) or before['possible_entry_remainders']:raise Blocked('unsafe margin scope')
    amount=D(target)-D(before['isolated_wallet_usdt'])
    if not 0<amount<=D(before['wallet_usdt'])-D(before['isolated_wallet_usdt']):
        raise Blocked('margin addition must be funded from existing wallet')
    identity=client_id(state.identity,epoch,'margin_add')
    payload=dict(symbol='BTCUSDT',positionSide='BOTH',amount=str(amount),type=1)
    if any(p['kind']=='binance_margin' for p in state.pending()):raise Unknown('previous margin outcome unresolved')
    state.prepare(identity,'binance_margin',payload)
    try:answer=send('POST','/fapi/v1/positionMargin',payload)
    except Exception:raise Unknown('margin outcome unknown; no automatic retry') from None
    if not isinstance(answer,dict) or answer.get('code')!=200 or answer.get('type')!=1 or D(str(answer.get('amount',0)))!=amount:
        raise Unknown('margin response not definitive')
    after=reader.snapshot(uid)
    if D(after['quantity_btc'])!=D(before['quantity_btc']) or D(after['isolated_wallet_usdt'])<D(target):
        raise Unknown('margin/position readback changed; reconcile without retry')
    state.finish(identity,'confirmed',{'amount':str(amount),'isolated_wallet':after['isolated_wallet_usdt']})
    return after
