"""Native Binance protection, reduction and margin operations.

The default CLI is read-only. Explicit bounded trials use these operations
through the same lifecycle; routine production remains unqualified.
"""
import json
from decimal import Decimal as D, ROUND_CEILING
from .config import scope
from .state import client_id
from .binance import market_quantity
from .types import Blocked, NotSent, Rejected, Unknown


def risk_reducing(state, pending):
    """Whether an unsettled intent can only lower exposure if it executes.

    Margin additions, reduce-only orders, close-all protection and its
    cancellation qualify. Any other intent could still open or add risk.
    """
    kind,payload=pending['kind'],pending['payload']
    if kind=='binance_algo_cancel':
        owner=state.db.execute('SELECT kind,payload FROM intents WHERE id=?',(payload.get('clientAlgoId'),)).fetchone()
        return bool(owner and owner[0]=='binance_algo'
                    and json.loads(owner[1]).get('symbol')=='BTCUSDT'
                    and json.loads(owner[1]).get('closePosition')=='true')
    return (kind=='binance_margin' or
            kind=='binance_order' and payload.get('reduceOnly')=='true' or
            kind=='binance_algo' and (payload.get('closePosition')=='true' or payload.get('reduceOnly')=='true'))


def _gate(reader, state, uid, authorized, *, canceling_entry=False, snapshot=None):
    """Scope and pending-intent checks before a safety write.

    `snapshot` may only be an observation taken after the caller's latest write.
    """
    if authorized is not True:raise Blocked('explicit operation authorization required')
    if state.identity != scope(reader.environment, uid):
        raise Blocked('state and native reader account scope differ')
    if snapshot is None or state.pending():reader.recover_pending(state)
    if not canceling_entry:
        if not all(risk_reducing(state,p) for p in state.pending()):
            raise Unknown('unsettled possible entry intent; reconcile before reporting safety')
    if snapshot is None:snapshot=reader.snapshot(uid)
    if snapshot['account_uid']!=str(uid):raise Blocked('account mismatch')
    return snapshot


def _once(state, identity, kind, payload, send, method, path, *, at_ms):
    # Existing intent means possibly sent, even after a crash before HTTP began.
    old=state.db.execute('SELECT kind,payload,status FROM intents WHERE id=?',(identity,)).fetchone()
    if old and old[2]!='rejected':
        if old[0]!=kind or json.loads(old[1])!=payload:raise Unknown('stable intent payload changed')
        return
    # The adapter clock at preparation bounds when the signed request can be accepted.
    state.prepare(identity,kind,payload,result={'prepared_at_ms':at_ms})
    send_once(state,identity,send,method,path,payload)
    # A refused cancel usually means the target is already terminal; callers
    # settle cancellations from the target's own state.
    if not kind.endswith('_cancel') and rejected(state,identity):
        raise Blocked('request was not sent or was refused by Binance; nothing changed at the exchange')


def rejected(state, identity):
    row=state.db.execute('SELECT status FROM intents WHERE id=?',(identity,)).fetchone()
    return bool(row) and row[0]=='rejected'


def absent(state, identity):
    """Nothing exists at the exchange under this identity: refused or retired void."""
    row=state.db.execute('SELECT status FROM intents WHERE id=?',(identity,)).fetchone()
    return bool(row) and row[0] in ('rejected','void')


def send_once(state, identity, send, method, path, payload):
    """Send a prepared intent. Only a local refusal or a documented native
    rejection is terminal; every other error keeps the intent unknown."""
    try:send(method,path,payload)
    except (Blocked,NotSent) as exc:
        state.finish(identity,'rejected',{'not_sent':str(exc)})
    except Rejected as exc:
        state.finish(identity,'rejected',{'native_rejection':str(exc)})
    except Exception as exc:
        # Never interpret transport/API errors as proof that the write failed.
        # Keep the identity unknown and record only the exception type.
        row=state.db.execute('SELECT result FROM intents WHERE id=?',(identity,)).fetchone()
        current=json.loads(row[0]) if row else {}
        current['unresolved']={'stage':'send','error_type':type(exc).__name__,
                               **{k:v for k,v in (('http_status',getattr(exc,'http_status',None)),
                                                  ('native_code',getattr(exc,'native_code',None))) if v is not None}}
        state.finish(identity,'unknown',current)


def settled_protection(reader,state,identity):
    """Retain conclusive terminal child evidence before exchange history expires."""
    settled=state.get('settled_protection') or {}
    if identity in settled or absent(state,identity):return True
    archived=(state.get('terminal_native_orders') or {}).get(identity)
    if archived and 'algoStatus' in archived['parent']:
        settled[identity]=archived;state.set('settled_protection',settled)
        return True
    if not reader.conditional_terminal(identity):return False
    observed=reader.query_intent(identity,conditional=True)
    parent,child=observed['parent'],observed['child']
    if parent.get('algoStatus') not in ('CANCELED','EXPIRED','REJECTED','FINISHED'):
        raise Unknown('protective terminal state changed')
    if child is not None:
        if (child.get('status') not in ('FILLED','CANCELED','EXPIRED','EXPIRED_IN_MATCH','REJECTED')
                or not 0<=D(child['executedQty'])<=D(child['origQty'])
                or child['status']=='FILLED' and D(child['executedQty'])!=D(child['origQty'])
                or child['status']=='REJECTED' and D(child['executedQty'])):
            raise Unknown('protective child terminal state changed')
    elif parent['algoStatus']=='FINISHED':
        raise Unknown('finished protection lacks child evidence')
    settled[identity]=observed
    state.set('settled_protection',settled)
    return True


def protect_existing(reader,state,send,uid,epoch,stop,take,*,instrument,authorized=False,snapshot=None):
    """Install full-position SL then TP, retaining every existing protection.

    There must be no possible entry remainder. A partial position is protected
    by closePosition, never by the requested entry size. ACK is not readback.
    """
    before=_gate(reader,state,uid,authorized,snapshot=snapshot)
    q=D(before['quantity_btc']);mark=D(before['mark_price']);liq=D(before['native_liquidation_price'])
    stop,take=D(stop),D(take)
    filters=[f for f in instrument.get('filters',[]) if f.get('filterType')=='PRICE_FILTER']
    if instrument.get('symbol')!='BTCUSDT' or len(filters)!=1:raise Blocked('missing native price rule')
    rule=filters[0];tick=D(rule['tickSize'])
    if tick<=0 or any(p%tick or not D(rule['minPrice'])<=p<=D(rule['maxPrice']) for p in (stop,take)):
        raise Blocked('protection violates native price filter')
    if not q or before['possible_entry_remainders']:raise Blocked('flat or entry remainder unresolved')
    if not (0<=liq<stop<mark<take if q>0 else 0<take<mark<stop<liq):
        raise Blocked('invalid protection or liquidation geometry')
    for kind,trigger in (('STOP_MARKET',stop),('TAKE_PROFIT_MARKET',take)):
        identity=client_id(state.identity,epoch,kind)
        payload=dict(symbol='BTCUSDT',positionSide='BOTH',side='SELL' if q>0 else 'BUY',
            algoType='CONDITIONAL',type=kind,triggerPrice=str(trigger),closePosition='true',
            workingType='MARK_PRICE',priceProtect='false',clientAlgoId=identity)
        _once(state,identity,'binance_algo',payload,send,'POST','/fapi/v1/algoOrder',at_ms=int(reader.clock()*1000))
        observed=reader.query_intent(identity,conditional=True);parent=observed['parent']
        expected=dict(symbol='BTCUSDT',positionSide='BOTH',side=payload['side'],
            orderType=kind,closePosition=True,workingType='MARK_PRICE',priceProtect=False,
            clientAlgoId=identity,algoStatus='NEW')
        if (any(parent.get(k)!=v for k,v in expected.items())
                or D(parent.get('triggerPrice','0'))!=trigger or observed['child'] is not None):
            raise Unknown('native protection not confirmed active; reconcile exposure')
        state.finish(identity,'confirmed',{'algo_id':parent['algoId'],'status':'NEW'})
        timing=state.get('entry_timing') if kind=='STOP_MARKET' else None
        plan=state.get('entry_plan') if timing else None
        if timing and kind=='STOP_MARKET' and plan and plan.get('epoch')==epoch:
            timing['stop_accepted_at_ms']=int(reader.clock()*1000)
            state.set('entry_timing',timing)
        if kind=='TAKE_PROFIT_MARKET':break  # the final readback follows
        observed_account=reader.snapshot(uid)
        if (observed_account['account_uid']!=str(uid) or D(observed_account['quantity_btc'])!=q
                or observed_account['possible_entry_remainders']):
            raise Unknown('exposure changed between protection legs; reconcile before next write')
        if timing and plan and plan.get('epoch')==epoch:
            timing['stop_account_readback_at_ms']=int(reader.clock()*1000)
            state.set('entry_timing',timing)
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
        _once(state,identity,'binance_cancel',payload,send,'DELETE','/fapi/v1/order',at_ms=int(reader.clock()*1000))
    final=reader.query_intent(entry_id)['parent']
    qty=D(final.get('origQty','0'));filled=D(final.get('executedQty','-1'))
    if (final.get('status') not in terminal or not 0<=filled<=qty or qty<=0
            or (final['status']=='FILLED' and filled!=qty)):
        raise Unknown('entry remainder/child fill is not terminal')
    if state.db.execute('SELECT 1 FROM intents WHERE id=?',(identity,)).fetchone():
        state.finish(identity,'confirmed',{'status':final['status'],'executed_quantity':str(filled)})
    reader.recover_pending(state)
    return reader.snapshot(uid)


def reduce_existing(reader,state,send,uid,epoch,quantity,*,instrument,authorized=False,snapshot=None):
    """Bounded reduce-only market request; caller supplies rule-rounded quantity."""
    before=_gate(reader,state,uid,authorized,snapshot=snapshot);q=D(before['quantity_btc']);qty=D(quantity)
    if before['possible_entry_remainders'] or not 0<qty<=abs(q):raise Blocked('unsafe reduction')
    if market_quantity(qty,before['mark_price'],instrument,reduce_only=True)!=qty:raise Blocked('reduction violates native quantity rule')
    identity=client_id(state.identity,epoch,'reduce')
    payload=dict(symbol='BTCUSDT',positionSide='BOTH',side='SELL' if q>0 else 'BUY',
        type='MARKET',quantity=str(qty),reduceOnly='true',newClientOrderId=identity)
    _once(state,identity,'binance_order',payload,send,'POST','/fapi/v1/order',at_ms=int(reader.clock()*1000))
    reader.recover_pending(state)
    if any(p['id']==identity for p in state.pending()):raise Unknown('reduction result unresolved')
    after=reader.snapshot(uid);remaining=D(after['quantity_btc'])
    if after['possible_entry_remainders'] or remaining*q<0 or abs(remaining)>abs(q)-qty:
        raise Unknown('risk removal readback conflicts')
    return after


def add_margin(reader,state,send,uid,epoch,target,*,instrument,authorized=False,snapshot=None):
    """Model-selected isolated wallet target; never withdraw or retry unknown adds.

    Binance margin writes have no client transaction ID. The amount is rounded up
    to the settlement asset's native precision. A definitive success response is
    persisted before the separate wallet readback; a lost answer is settled only
    from native margin history, never from a balance change or a resend.
    """
    before=_gate(reader,state,uid,authorized,snapshot=snapshot)
    if not D(before['quantity_btc']) or before['possible_entry_remainders']:raise Blocked('unsafe margin scope')
    places=instrument.get('quotePrecision')
    if (instrument.get('symbol')!='BTCUSDT' or instrument.get('marginAsset')!='USDT'
            or type(places) is not int or not 0<=places<=8):
        raise Blocked('settlement amount precision unavailable')
    amount=(D(target)-D(before['isolated_wallet_usdt'])).quantize(D(1).scaleb(-places),rounding=ROUND_CEILING)
    if not 0<amount<=D(before['wallet_usdt'])-D(before['isolated_wallet_usdt']):
        raise Blocked('margin addition must be funded from existing wallet')
    identity=client_id(state.identity,epoch,'margin_add')
    payload=dict(symbol='BTCUSDT',positionSide='BOTH',amount=format(amount.normalize(),'f'),type=1)
    if any(p['kind']=='binance_margin' for p in state.pending()):raise Unknown('previous margin outcome unresolved')
    prepared=int(reader.clock()*1000)
    state.prepare(identity,'binance_margin',payload,result={'prepared_at_ms':prepared})
    try:answer=send('POST','/fapi/v1/positionMargin',payload)
    except (Blocked,NotSent) as exc:
        state.finish(identity,'rejected',{'prepared_at_ms':prepared,'not_sent':str(exc)})
        raise Blocked('margin transfer was not sent') from None
    except Rejected as exc:
        state.finish(identity,'rejected',{'prepared_at_ms':prepared,'native_rejection':str(exc)})
        raise Blocked('margin transfer rejected by Binance') from None
    except Exception:raise Unknown('margin outcome unknown; no automatic retry') from None
    if (not isinstance(answer,dict) or answer.get('code')!=200 or str(answer.get('type'))!='1'
            or D(str(answer.get('amount',0)))!=amount):
        raise Unknown('margin response not definitive')
    # Later history attribution needs this time to exclude this transfer's row.
    state.finish(identity,'confirmed',{'prepared_at_ms':prepared,'amount':str(amount),'acknowledged':True})
    after=reader.snapshot(uid)
    if D(after['quantity_btc'])!=D(before['quantity_btc']) or D(after['isolated_wallet_usdt'])<D(target):
        raise Unknown('margin/position readback changed; reconcile without retry')
    return after


def replace_protection(reader,state,send,uid,old_epoch,epoch,stop,take,*,instrument,authorized=False):
    """Try a new close-all pair, then retire owned old parents after readback.

    No atomic amendment or duplicate-close-all acceptance is assumed. Rejection or
    missing readback retains old protection and blocks cancellation. A durable
    journal pins the request/exposure across crashes; uncertain writes never retry.
    The default CLI is read-only; controlled trials use this same lifecycle.
    """
    import json
    if authorized is not True:raise Blocked('explicit operation authorization required')
    if state.identity!=scope(reader.environment,uid):raise Blocked('account scope mismatch')
    if old_epoch==epoch:raise Blocked('replacement needs a distinct stable epoch')
    old_ids=[client_id(state.identity,old_epoch,k) for k in ('STOP_MARKET','TAKE_PROFIT_MARKET')]
    new_ids=[client_id(state.identity,epoch,k) for k in ('STOP_MARKET','TAKE_PROFIT_MARKET')]
    key='binance_protection_replacement'
    request=dict(old_ids=old_ids,new_ids=new_ids,stop=str(D(stop)),take=str(D(take)))
    journal=state.get(key)
    if journal and journal['request']!=request:
        if request in journal.get('superseded',[]):
            # The same operation continues under the fresh generation it rotated to.
            request=journal['request'];old_ids=request['old_ids'];new_ids=request['new_ids'];epoch=journal['epoch']
        elif journal.get('done'):
            journal=None
        else:
            raise Unknown('another protection replacement is unresolved')
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
        journal=dict(request=request,quantity=str(q),done=False,epoch=epoch)
        state.set(key,journal)
    if journal.get('done'):return before  # same operation must never protect a later position
    if 'original_quantity' not in journal:
        journal['original_quantity']=journal['quantity']
        state.set(key,journal)
    original=D(journal['original_quantity'])
    if q and q!=D(journal['quantity']):
        # A smaller same-direction position continues only when confirmed terminal
        # fills of this operation's own protection legs explain exactly the missing
        # size. A leg still healthy (NEW, no child) stays as protection; a leg that
        # is spent cannot be reused, so the new pair moves to a fresh generation.
        # An external change or a child that is still working stays unknown.
        if q*original<=0 or abs(q)>abs(original):
            raise Unknown('exposure grew or reversed during protection replacement')
        executed=D(0);live=[];spent_new=False
        for identity in old_ids+new_ids:
            if not state.db.execute('SELECT 1 FROM intents WHERE id=?',(identity,)).fetchone():
                continue
            if settled_protection(reader,state,identity):
                child=(state.get('settled_protection') or {}).get(identity,{}).get('child')
                if child is not None:executed+=D(child.get('executedQty') or 0)
                spent_new|=identity in new_ids
                continue
            observed=reader.query_intent(identity,conditional=True)
            parent=observed['parent']
            if parent.get('algoStatus')!='NEW' or observed['child'] is not None or parent.get('closePosition') is not True:
                raise Unknown('partial fill or exposure change; retain protection and reconcile')
            live.append(identity)
        if executed<=0:
            raise Unknown('position changed without a terminal owned protection fill')
        if abs(original)-abs(q)!=executed:
            raise Unknown('position change is not explained by confirmed owned protection fills')
        journal={**journal,'quantity':str(q)}
        if spent_new:
            fresh=max(int(reader.clock()*1000),(state.get('operation_sequence') or 0)+1)
            state.set('operation_sequence',fresh)
            epoch=fresh
            old_ids=live
            new_ids=[client_id(state.identity,epoch,k) for k in ('STOP_MARKET','TAKE_PROFIT_MARKET')]
            journal=dict(request=dict(old_ids=old_ids,new_ids=new_ids,stop=request['stop'],take=request['take']),
                         quantity=str(q),original_quantity=str(q),done=False,epoch=epoch,
                         superseded=journal.get('superseded',[])+[journal['request']])
        state.set(key,journal)
        q=D(q)

    def retire(identity):
        if settled_protection(reader,state,identity):return
        cancel_id=client_id(state.identity,epoch,'retire:'+identity)
        payload=dict(clientAlgoId=identity)
        _once(state,cancel_id,'binance_algo_cancel',payload,send,'DELETE','/fapi/v1/algoOrder',at_ms=int(reader.clock()*1000))
        if not settled_protection(reader,state,identity):raise Unknown('protection cancellation/child unresolved')
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


def replacement_epoch(state, default):
    """Epoch under which a finished replacement left its live protection."""
    journal=state.get('binance_protection_replacement')
    if journal and journal.get('done') and type(journal.get('epoch')) is int:
        return journal['epoch']
    return default
