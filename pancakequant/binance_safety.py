"""Native Binance safety operations; no entry or network writer is exposed.

The injected sender is used by offline lifecycle tests. Production CLI stays
read-only until authorized native lifecycle validation and economic acceptance.
"""
from decimal import Decimal as D
from .state import client_id
from .binance import market_quantity
from .types import Blocked, Unknown


def _gate(reader, state, uid, authorized, *, canceling_entry=False):
    if authorized is not True:raise Blocked('explicit operation authorization required')
    if state.identity != f'binance:BTCUSDT:live:{uid}':
        raise Blocked('state and native reader account scope differ')
    reader.recover_pending(state)
    if not canceling_entry:
        for pending in state.pending():
            kind,payload=pending['kind'],pending['payload']
            safe=(kind=='binance_margin' or
                  kind=='binance_order' and payload.get('reduceOnly')=='true' or
                  kind=='binance_algo' and (payload.get('closePosition')=='true' or payload.get('reduceOnly')=='true'))
            if kind=='binance_algo_cancel':
                import json
                owner=state.db.execute('SELECT kind,payload FROM intents WHERE id=?',(payload.get('clientAlgoId'),)).fetchone()
                safe=bool(owner and owner[0]=='binance_algo'
                          and json.loads(owner[1]).get('symbol')=='BTCUSDT'
                          and json.loads(owner[1]).get('closePosition')=='true')
            if not safe:raise Unknown('unsettled possible entry intent; reconcile before reporting safety')
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
        observed_account=reader.snapshot(uid)
        if (observed_account['account_uid']!=str(uid) or D(observed_account['quantity_btc'])!=q
                or observed_account['possible_entry_remainders']):
            raise Unknown('exposure changed between protection legs; reconcile before next write')
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
    _gate(reader,state,uid,authorized,canceling_entry=True)
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


def replace_protection(reader,state,send,uid,old_epoch,epoch,stop,take,*,instrument,authorized=False):
    """Try a new close-all pair, then retire owned old parents after readback.

    No atomic amendment or duplicate-close-all acceptance is assumed. Rejection or
    missing readback retains old protection and blocks cancellation. A durable
    journal pins the request/exposure across crashes; uncertain writes never retry.
    This injected-sender lifecycle is not enabled by the production read-only CLI.
    """
    import json
    if authorized is not True:raise Blocked('explicit operation authorization required')
    if state.identity!=f'binance:BTCUSDT:live:{uid}':raise Blocked('account scope mismatch')
    if old_epoch==epoch:raise Blocked('replacement needs a distinct stable epoch')
    old_ids=[client_id(state.identity,old_epoch,k) for k in ('STOP_MARKET','TAKE_PROFIT_MARKET')]
    new_ids=[client_id(state.identity,epoch,k) for k in ('STOP_MARKET','TAKE_PROFIT_MARKET')]
    key='binance_protection_replacement'
    request=dict(old_ids=old_ids,new_ids=new_ids,stop=str(D(stop)),take=str(D(take)))
    journal=state.get(key)
    if journal and journal['request']!=request:
        if not journal.get('done'):raise Unknown('another protection replacement is unresolved')
        journal=None
    # Missing ownership after local state loss never authorizes order cancellation.
    for identity in old_ids:
        row=state.db.execute('SELECT kind,payload FROM intents WHERE id=?',(identity,)).fetchone()
        if not row or row[0]!='binance_algo':raise Blocked('old protection ownership unavailable; recover read-only')
        payload=json.loads(row[1])
        if payload.get('closePosition')!='true':raise Blocked('old order is not owned close-all protection')
    # Resolve this operation's cancellation uncertainty before normal safety gates.
    for identity in old_ids+new_ids:
        cancel_id=client_id(state.identity,epoch,'retire:'+identity)
        pending=state.db.execute('SELECT status FROM intents WHERE id=?',(cancel_id,)).fetchone()
        if pending and pending[0] in ('unknown','partial'):
            if not reader.conditional_terminal(identity):raise Unknown('cancel or child still unsettled; no retry')
            state.finish(cancel_id,'confirmed',{'target':identity,'terminal':True})
    before=_gate(reader,state,uid,authorized)
    q=D(before['quantity_btc'])
    if before['possible_entry_remainders']:raise Unknown('entry remainder blocks replacement')
    if journal is None:
        if not q:raise Blocked('no exposure to replace protection for')
        journal=dict(request=request,quantity=str(q),done=False)
        state.set(key,journal)
    if journal.get('done'):return before  # same operation must never protect a later position
    original=D(journal['quantity'])
    if q and q!=original:raise Unknown('partial fill or exposure change; retain protection and reconcile')

    def retire(identity):
        if reader.conditional_terminal(identity):return
        cancel_id=client_id(state.identity,epoch,'retire:'+identity)
        payload=dict(clientAlgoId=identity)
        _once(state,cancel_id,'binance_algo_cancel',payload,send,'DELETE','/fapi/v1/algoOrder')
        if not reader.conditional_terminal(identity):raise Unknown('protection cancellation/child unresolved')
        state.finish(cancel_id,'confirmed',{'target':identity,'terminal':True})

    if q:
        # Every attempt first reuses/queries the same new identities, never blindly
        # resends a timed-out request. Native acceptance is the coexistence check.
        protect_existing(reader,state,send,uid,epoch,stop,take,instrument=instrument,authorized=True)
        for identity in old_ids:
            # Read BOTH new legs and the account again before each destructive step.
            protect_existing(reader,state,send,uid,epoch,stop,take,instrument=instrument,authorized=True)
            observed=reader.query_intent(identity,conditional=True)
            p=observed['parent']
            if (p.get('closePosition') is not True or p.get('side')!=('SELL' if q>0 else 'BUY')
                    or p.get('orderType') not in ('STOP_MARKET','TAKE_PROFIT_MARKET')):
                raise Unknown('old protection scope changed')
            if observed['child'] is not None and not reader.conditional_terminal(identity):
                raise Unknown('old protection child still working; reconcile partial exposure')
            retire(identity)
            after=reader.snapshot(uid)
            if after['account_uid']!=str(uid) or D(after['quantity_btc'])!=q or after['possible_entry_remainders']:
                raise Unknown('protection filled during retirement; reconcile before next write')
        after=protect_existing(reader,state,send,uid,epoch,stop,take,instrument=instrument,authorized=True)
    else:
        # A previously journaled position closed during replacement. Cancel only
        # known accepted close-all intents; unknown acceptance still fails closed.
        for identity in old_ids+new_ids:
            if not state.db.execute('SELECT 1 FROM intents WHERE id=?',(identity,)).fetchone():continue
            now=reader.snapshot(uid)
            if now['account_uid']!=str(uid) or D(now['quantity_btc']) or now['possible_entry_remainders']:
                raise Unknown('flat cleanup scope changed')
            retire(identity)
        after=reader.snapshot(uid)
        if after['account_uid']!=str(uid) or D(after['quantity_btc']) or after['possible_entry_remainders']:
            raise Unknown('flat cleanup exposure changed')
    journal['done']=True;state.set(key,journal)
    return after
