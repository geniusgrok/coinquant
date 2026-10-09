"""Native Binance entry, protection, recovery and bounded cleanup.

Order intents require native state evidence; unknown writes are never retried.
The CLI permits only explicit bounded trial writes.
"""
import json
from decimal import Decimal as D, ROUND_CEILING, ROUND_FLOOR

from . import binance_safety as safety
from .native_preview import (MAX_ISOLATED_MARGIN_FRACTION,
                             commission, entry_preview, holding_risk, limit_matches, topup_preview)
from .ownership import TERMINAL, owned_observation
from .opportunities import FOUR_HOURS
from .state import client_id
from .binance import UNACCEPTED_AFTER_MS, market_quantity
from .types import Blocked, Unknown, number, floor_step

# Measured: first entry with protection about 400; an add under standing
# close-all protection about 130 (210 with a margin transfer); preview about 60.
ENTRY_RESERVE = 800
TOPUP_RESERVE = 250
PREVIEW_WEIGHT = 100
# Network budget reserved for an owned fill's protection, and separately for
# the bounded reduction after protection failed; neither is cut by the session
# deadline. The reduction needs one full observation (ten reads), the fill proof
# (two reads) and its write even when every response takes nearly the 8 s
# request timeout.
PROTECT_SECONDS = 120
REDUCE_SECONDS = 120
# Final verification after the trading deadline. Together the three budgets are the
# most any renewal may extend the session's absolute end (Binance.hard_deadline).
FINISH_SECONDS = 120
ABSOLUTE_GRACE = PROTECT_SECONDS + REDUCE_SECONDS + FINISH_SECONDS
# Entry preflight rules remain reusable for five minutes after observation.
RULES_FRESH_MS = 300000
# Query Algo Order stops retaining parents created more than 90 days ago.
# Renew an observed native pair before that boundary, using its creation time.
PROTECTION_RENEW_MS = 75 * 86400000
ALGO_HISTORY_MS = 90 * 86400000




def _protection_fits(snapshot, stop, take):
    """Whether the planned stop already sits on the safe side of liquidation."""
    q = number(snapshot['quantity_btc'])
    mark = number(snapshot['mark_price'])
    liq = number(snapshot['native_liquidation_price'])
    stop, take = number(stop), number(take)
    if q > 0:
        return 0 <= liq < stop < mark < take
    return 0 < take < mark < stop < liq


def _guard_prices(snapshot, plan, rules):
    """A stop that fits the current liquidation, one tick on the safe side of it.

    The planned stop is installed after margin is added. This only covers the
    transfer. None when no price sits between liquidation and the mark.
    """
    from decimal import ROUND_CEILING, ROUND_FLOOR
    filters = [item for item in rules.get('filters', []) if item.get('filterType') == 'PRICE_FILTER']
    if len(filters) != 1:
        return None
    tick = number(filters[0].get('tickSize'), positive=True)
    floor = number(filters[0].get('minPrice'))
    ceiling = number(filters[0].get('maxPrice'), positive=True)
    q = number(snapshot['quantity_btc'])
    mark = number(snapshot['mark_price'])
    liq = number(snapshot['native_liquidation_price'])
    planned_take = number(plan['take'])
    if q > 0:
        stop = (liq / tick).to_integral_value(rounding=ROUND_CEILING) * tick
        if stop <= liq:
            stop += tick
        take = planned_take if planned_take > mark else mark + tick
        if not (liq < stop < mark < take):
            return None
    else:
        stop = (liq / tick).to_integral_value(rounding=ROUND_FLOOR) * tick
        if stop >= liq:
            stop -= tick
        take = planned_take if 0 < planned_take < mark else mark - tick
        if not (0 < take < mark < stop < liq):
            return None
    if not floor <= stop <= ceiling or not floor <= take <= ceiling or stop % tick or take % tick:
        return None
    return stop, take


def blocking(state):
    """Unknown intents that block every decision.

    A risk-reducing intent (margin, reduce-only, close-all protection or its
    cancellation) blocks only new risk: entry, add and every enter/top-up gate
    still require no pending intent. Protection and exits remain possible.
    """
    return [p for p in state.pending() if not safety.risk_reducing(state,p)]


def _guard_replacement_request(state,plan):
    if plan.get('guard_epoch') is None:return None
    return dict(old_ids=[client_id(state.identity,plan['guard_epoch'],k) for k in ('STOP_MARKET','TAKE_PROFIT_MARKET')],
                new_ids=[client_id(state.identity,plan['epoch'],k) for k in ('STOP_MARKET','TAKE_PROFIT_MARKET')],
                stop=str(number(plan['stop'])),take=str(number(plan['take'])))


class Lifecycle:
    def __init__(self, reader, state, uid, *, authorized=False, may_enter=lambda:True, session=None):
        self.reader, self.state, self.uid = reader, state, uid
        self.session = session
        self.authorized = authorized is True
        self.may_enter = may_enter
        self.actions = []
        self.entry_constraint = None
        self.reconciled = None
        # A cleanup retry is allowed only after another owned terminal reduction
        # has strictly shrunk exposure. Unknown or zero-fill writes never count.
        self.exit_progress = 0
        # Set only by a cashflow audit closed against the wallet observed for this
        # decision (audit.allows_new_risk). Entry and top-up both require it.
        self.risk_audit_ok = False
        self.new_risk_bar = None
        self.new_risk_observed_at = None

    def check_entry_clock(self, model, snapshot, observed_at):
        """A fresh quote cannot authorize risk after its model candle expires."""
        mark_time=snapshot.get('mark_time')
        now=int(self.reader.clock()*1000)+getattr(self.reader,'time_offset_ms',0)
        if (type(model.last) is not int or model.last%FOUR_HOURS
                or type(mark_time) is not int or mark_time//FOUR_HOURS*FOUR_HOURS!=model.last
                or now//FOUR_HOURS*FOUR_HOURS!=model.last):
            raise Blocked('completed model candle changed before new exposure')
        self.new_risk_bar=model.last
        self.new_risk_observed_at=observed_at

    def send(self, method, path, payload):
        if not self.authorized:
            raise Blocked('read-only session cannot send orders')
        plan=self.state.get('entry_plan')
        if plan and method=='POST':
            timing=self.state.get('entry_timing') or {'entry_id':plan['id']}
            field=None
            if path=='/fapi/v1/order' and payload.get('newClientOrderId')==plan['id']:
                field='entry_send_attempt_at_ms'
            elif path=='/fapi/v1/algoOrder' and payload.get('type')=='STOP_MARKET' and plan:
                # The first stop for this fill, including a guard placed before margin.
                if 'stop_send_attempt_at_ms' not in timing:
                    field='stop_send_attempt_at_ms'
                    timing['first_stop_id']=payload.get('clientAlgoId')
            if field:
                timing[field]=int(self.reader.clock()*1000)
                self.state.set('entry_timing',timing)
        self.state.set('write_attempt_count',(self.state.get('write_attempt_count') or 0)+1)
        action=dict(method=method, path=path, id=payload.get('newClientOrderId', payload.get('clientAlgoId', payload.get('origClientOrderId'))),
                    at_ms=int(self.reader.clock()*1000))
        exit_operation=self.state.get('position_exit')
        if (method=='POST' and path=='/fapi/v1/order' and payload.get('reduceOnly')=='true'
                and exit_operation and action['id']==client_id(self.state.identity,exit_operation['epoch'],'reduce')):
            action['position_before_btc']=str(exit_operation['position_at_request'])
        if method=='POST' and path=='/fapi/v1/order' and payload.get('reduceOnly')!='true':
            # Durable preparation/fsync can itself straddle the close or a stop
            # request. Refuse locally before this entry reaches the transport.
            now=int(self.reader.clock()*1000)+getattr(self.reader,'time_offset_ms',0)
            if (self.new_risk_bar is None or now//FOUR_HOURS*FOUR_HOURS!=self.new_risk_bar
                    or type(self.new_risk_observed_at) is not int
                    or abs(int(self.reader.clock()*1000)-self.new_risk_observed_at)>15000
                    or not self.may_enter()):
                raise Blocked('entry quote/model expired or session stopped before send')
        self.actions.append(action)
        return self.reader.send(method, path, payload)

    def epoch(self):
        value = max(int(self.reader.clock()*1000), (self.state.get('operation_sequence') or 0)+1)
        self.state.set('operation_sequence', value)
        return value

    def _gap(self, snapshot, stop):
        """Absolute price distance from the stop to liquidation. None if none exists."""
        q=number(snapshot['quantity_btc'])
        if not q:
            return None
        liq=number(snapshot['native_liquidation_price'])
        if q>0 and liq==0:
            return None
        stop=number(stop,positive=True)
        return (stop-liq) if q>0 else (liq-stop)

    def _save_protection(self, payload, snapshot, *, clear_entry_plan=False):
        previous=self.state.get('position_protection')
        started=payload.pop('started_at_ms',payload.get('accepted_at_ms'))
        gap=(number(previous['buffer_distance'])
             if previous and previous.get('campaign')==payload.get('campaign') and 'buffer_distance' in previous
             else self._gap(snapshot, payload['stop']))
        if gap is not None:
            payload['buffer_distance']=str(gap)
        if previous and previous.get('campaign')==payload.get('campaign'):
            if previous.get('epoch')==payload.get('epoch'):
                if any(number(previous[k])!=number(payload[k]) for k in ('stop','take')):
                    raise Unknown('the same native protection identity cannot change its prices')
                if type(previous.get('accepted_at_ms')) is int:
                    # Reconfirming the same pair after a crash cannot erase its
                    # known history before the next model catch-up succeeds.
                    payload['accepted_at_ms']=previous['accepted_at_ms']
            ceilings=[number(p['loss_ceiling_usdt']) for p in (previous,payload)
                      if p.get('loss_ceiling_usdt') is not None]
            if ceilings:
                payload['loss_ceiling_usdt']=str(min(ceilings))
        history=self.state.get('protection_catchup') or []
        through=((self.state.get('linear_campaign') or {}).get('body') or {}).get('last',0)
        history=[p for p in history if p['ended_at_ms']>through]
        if (previous and previous.get('campaign')==payload.get('campaign')
                and previous.get('epoch')!=payload.get('epoch')
                and type(previous.get('accepted_at_ms')) is int and type(started) is int
                and previous['accepted_at_ms']<started):
            history.append({**{key:previous[key] for key in ('campaign','stop','take','accepted_at_ms')},
                            'ended_at_ms':started})
        updates={'position_protection':payload,'protection_catchup':history}
        if clear_entry_plan:
            updates['entry_plan']=None
        self.state.set_many(updates)

    def recover_entry_protection(self,snapshot):
        """Recover a live entry pair's history before any candle is checkpointed.

        This records geometry only. Entry ownership, collateral and the initial
        liquidation buffer still pass the normal recovery before risk can grow.
        """
        plan=self.state.get('entry_plan')
        if (not plan or not number(snapshot['quantity_btc'])
                or self.state.get('position_protection') or self.state.get('position_exit')):
            return
        epoch=plan['epoch']
        request=_guard_replacement_request(self.state,plan)
        journal=self.state.get('binance_protection_replacement') or {}
        if request and (request==journal.get('request') or request in journal.get('superseded',[])):
            epoch=journal['epoch']
        candidates=[(epoch,plan['stop'],plan['take'])]
        if plan.get('guard_epoch') is not None:
            candidates.append((plan['guard_epoch'],plan['guard_stop'],plan['guard_take']))
        active={a.get('clientAlgoId'):a for a in snapshot['open_algos']}
        now=max(int(self.reader.clock()*1000)+getattr(self.reader,'time_offset_ms',0),snapshot.get('mark_time',0))
        for epoch,stop,take in candidates:
            ids=[client_id(self.state.identity,epoch,k) for k in ('STOP_MARKET','TAKE_PROFIT_MARKET')]
            if any(active.get(identity,{}).get('algoStatus')!='NEW' for identity in ids):continue
            accepted=[]
            for identity,price in zip(ids,(stop,take)):
                observed=owned_observation(self.state,self.reader,identity,conditional=True)
                parent=observed['parent']
                if (parent.get('algoStatus')!='NEW' or observed['child'] is not None
                        or parent.get('closePosition') is not True
                        or parent.get('side')!=('SELL' if number(snapshot['quantity_btc'])>0 else 'BUY')
                        or number(parent.get('triggerPrice'),positive=True)!=number(price,positive=True)):
                    raise Unknown('entry protection changed while recovering its history')
                row=self.state.db.execute('SELECT result FROM intents WHERE id=?',(identity,)).fetchone()
                proof=json.loads(row[0])
                if proof.get('algo_id') is not None and str(proof['algo_id'])!=str(parent.get('algoId')):
                    raise Unknown('entry protection native identity changed')
                stamp=proof.get('first_confirmed_at_ms',parent.get('createTime'))
                if type(stamp) is not int or not 0<stamp<=now:
                    raise Unknown('entry protection history lacks a verified acceptance time')
                created=parent.get('createTime')
                if created is not None:
                    if type(created) is not int or not 0<created<=now:
                        raise Unknown('entry protection native creation time is invalid')
                    stamp=max(stamp,created)
                accepted.append(stamp)
            # Both exact native parents remain NEW, so neither has terminated
            # since its first readback (or its verified native creation time).
            self.state.set('position_protection',dict(epoch=epoch,stop=stop,take=take,
                campaign=plan['campaign'],accepted_at_ms=max(accepted)))
            return

    def enforce_holding_risk(self, snapshot):
        """Recheck owned exposure before market catch-up and before stopping.

        Only observed native costs can tighten a campaign's net loss ceiling.
        A missing audit leaves its existing protection in place, blocks adds and
        is reported as unverified. A known collateral breach can still exit.
        """
        q=number(snapshot['quantity_btc'])
        if not q:
            self.state.set('holding_risk',None)
            return snapshot
        if not self.authorized:
            raise Blocked('holding risk maintenance requires execution authorization')
        protection=self.state.get('position_protection')
        campaign=protection.get('campaign') if protection else None
        report=dict(status='unverified',campaign=campaign,
                    observed_at_ms=snapshot.get('observed_at_ms'))
        rules=None
        try:
            if not protection or not self.planned_protection(snapshot):
                raise Unknown('holding risk requires the owned native protection')
            rules=self.instrument()
            replacement=self.state.get('session_replacement')
            if replacement and replacement.get('campaign')!=campaign:
                raise Unknown('pending protection belongs to another campaign')
            if replacement and replacement.get('loss_ceiling_usdt') is not None:
                ceiling=number(replacement['loss_ceiling_usdt'])
                if protection.get('loss_ceiling_usdt') is not None:
                    ceiling=min(ceiling,number(protection['loss_ceiling_usdt']))
                protection={**protection,'loss_ceiling_usdt':str(ceiling)}
            proof=self.reconciled
            if not (proof and proof[0] is snapshot and proof[1]==len(self.actions)):
                from .campaign import Campaign
                from .ownership import reconcile
                ownership=reconcile(self.state,self.reader,
                                    Campaign.restore(self.state.get('linear_campaign')),snapshot)
                self.reconciled=(snapshot,len(self.actions),ownership)
            else:
                ownership=proof[2]
            if (ownership.get('status')!='reconciled' or ownership.get('campaign')!=campaign
                    or number(ownership.get('quantity','0'))!=number(snapshot['quantity_btc'])):
                raise Unknown('holding risk lacks current campaign ownership')
            fee=funding=None
            cost_error=None
            try:
                fee=commission(self.reader)
                from .audit import funding_debit
                funding=funding_debit(self.reader,self.state,campaign,snapshot)
            except (Blocked,Unknown,OSError,ValueError,KeyError,TypeError,ArithmeticError) as exc:
                cost_error=exc
            try:
                risk=holding_risk(snapshot,protection,self.state.get('entry_fill'),rules,fee,
                    paid_commission_usdt=ownership.get('campaign_fee_usdt'),
                    realized_pnl_usdt=ownership.get('campaign_realized_pnl_usdt'),
                    paid_funding_usdt=funding,
                    loss_fraction=getattr(self.reader,'loss_fraction',None),
                    slip_fraction=getattr(self.reader,'slip_fraction',None),
                    capital_limit=getattr(self.reader,'capital_limit',None))
            except (Blocked,Unknown):
                if cost_error is not None:raise cost_error
                raise
            report.update(risk,observed_at_ms=snapshot.get('observed_at_ms'),
                          quantity_btc=snapshot['quantity_btc'],entry=snapshot['entry'],
                          wallet_usdt=snapshot['wallet_usdt'],mark_price=snapshot['mark_price'],
                          last_fill_id=snapshot.get('last_fill_id'))
            if risk['action']=='exit':
                report['status']='exit_pending'
                self.state.set('holding_risk',report)
                self.risk_audit_ok=False
                self.entry_constraint=risk['reason']
                self.reader.set_deadline(REDUCE_SECONDS,extend_only=True)
                result=self.close(snapshot,rules)
                self.state.set('holding_risk',None)
                return result
            if replacement:
                # Known budget breaches exit before an unrelated strategy
                # amendment can block them. A pending identity still settles
                # before another replacement is created; then recheck its result.
                snapshot=self.complete_replacement(replacement,rules,snapshot=snapshot)
                return self.enforce_holding_risk(snapshot)
            if risk['action']=='tighten':
                replacement=dict(old_epoch=protection['epoch'],epoch=self.epoch(),
                                 stop=risk['stop'],take=protection['take'],campaign=campaign,
                                 loss_ceiling_usdt=risk['loss_ceiling_usdt'],
                                 started_at_ms=int(self.reader.clock()*1000))
                # A failed or interrupted replacement retains this exact target;
                # it must not be recalculated from a later, lower mark on restart.
                self.state.set('session_replacement',replacement)
                snapshot=self.complete_replacement(replacement,rules,snapshot=snapshot)
                if not number(snapshot['quantity_btc']):
                    self.state.set('holding_risk',None)
                    return snapshot
            else:
                self._save_protection({**protection,'loss_ceiling_usdt':risk['loss_ceiling_usdt']},snapshot)
            report.update(status='observed',native_stop=self.state.get('position_protection')['stop'],
                          current_protected_loss_usdt=risk['modeled_stop_loss_usdt'])
            self.state.set('holding_risk',report)
            return snapshot
        except (Blocked,Unknown,OSError,ValueError,KeyError,TypeError,ArithmeticError) as exc:
            report.update(status='unverified',reason=str(exc) if isinstance(exc,(Blocked,Unknown))
                          else 'holding risk inputs could not be verified')
            self.state.set('holding_risk',report)
            self.risk_audit_ok=False
            self.entry_constraint='holding_risk_unverified'
            if report.get('action')=='exit' or self.state.get('position_exit'):
                raise
            replacement=self.state.get('session_replacement')
            if replacement:
                # A refused strategy amendment must not trap a separately
                # required exit behind it. Only a fresh complete ownership
                # audit and the still-active old pair can keep this path open.
                from .campaign import Campaign
                from .ownership import reconcile
                current=self.reader.snapshot(self.uid)
                ownership=reconcile(self.state,self.reader,
                                    Campaign.restore(self.state.get('linear_campaign')),current)
                self.reconciled=(current,len(self.actions),ownership)
                if not number(current['quantity_btc']):
                    return self.recover_exposure(current)
                if (replacement.get('campaign')!=campaign or ownership.get('campaign')!=campaign
                        or number(current['quantity_btc'])*q<=0
                        or current['possible_entry_remainders'] or not self.planned_protection(current)):
                    raise
                required_risk_stop=(report.get('action')=='tighten' or
                    report.get('action') is None and replacement.get('loss_ceiling_usdt') is not None
                    and (number(replacement['stop'])-number(self.state.get('position_protection')['stop']))*q>0)
                if required_risk_stop:
                    # A required risk stop that cannot be established is not a
                    # successful hold, even when the older looser pair survives.
                    self.reader.set_deadline(REDUCE_SECONDS,extend_only=True)
                    result=self.close(current,rules)
                    self.state.set('holding_risk',None)
                    return result
                return current
            return snapshot

    def ensure_liquidation_buffer(self, snapshot):
        """Restore the entry liquidation gap, or leave while the stop is still valid.

        The saved distance is absolute. A higher mark must not by itself look like
        a smaller buffer.
        """
        if getattr(self,'_in_buffer',False) or not self.authorized:
            return snapshot
        protection=self.state.get('position_protection')
        q=number(snapshot['quantity_btc'])
        if not q or not protection or 'buffer_distance' not in protection:
            if not q or not protection or snapshot.get('stop_before_liquidation') is not False:
                return snapshot
        self._in_buffer=True
        try:
            gap=self._gap(snapshot, protection['stop'])
            target=D(protection.get('buffer_distance') or 0)
            unsafe=snapshot.get('stop_before_liquidation') is False
            shrunk=gap is not None and target>0 and gap<target
            if not unsafe and not shrunk:
                return snapshot
            equity=number(snapshot.get('equity_usdt') or 0)
            wallet=number(snapshot['wallet_usdt'])
            limit=getattr(self.reader,'capital_limit',None)
            capital=wallet if limit is None else min(wallet,limit)
            risk=max(D(0),min(capital,equity))
            isolated=number(snapshot['isolated_wallet_usdt'])
            cap=risk*MAX_ISOLATED_MARGIN_FRACTION
            if isolated<cap:
                rules=self.instrument()
                places=rules.get('quotePrecision')
                if type(places) is not int or not 0<=places<=8:
                    raise Blocked('settlement amount precision unavailable')
                # The transfer rounds up to the asset precision; leave no fraction
                # above the collateral ceiling for that rounding to consume.
                cap=cap.quantize(D(1).scaleb(-places),rounding=ROUND_FLOOR)
                try:
                    snapshot=safety.add_margin(self.reader,self.state,self.send,self.uid,self.epoch(),
                        cap,instrument=rules,authorized=self.authorized,snapshot=snapshot,
                        expected_owner=dict(snapshot))
                except Blocked:
                    pass
                except Unknown:
                    # This endpoint has no request identity for a lost answer.
                    # Never retry it, and do not let it prevent an owned exit.
                    # It may already have funded the buffer: first settle and
                    # reread, preserving a sufficient protected position then.
                    self.reader.set_deadline(REDUCE_SECONDS,extend_only=True)
                    snapshot=self.recover_exposure(self.settle())
                    if not number(snapshot['quantity_btc']):return snapshot
                    gap=self._gap(snapshot,protection['stop'])
                    if snapshot.get('stop_before_liquidation') and (gap is None or gap>=target):
                        return snapshot
                else:
                    gap=self._gap(snapshot, protection['stop'])
                    if snapshot.get('stop_before_liquidation') and (gap is None or gap>=target):
                        return snapshot
            closed=self.close(snapshot)
            return closed if closed is not None else snapshot
        finally:
            self._in_buffer=False

    def instrument(self):
        rows = [r for r in self.reader.get('/fapi/v1/exchangeInfo')['symbols'] if r.get('symbol') == 'BTCUSDT']
        if len(rows) != 1 or rows[0].get('status') != 'TRADING' or rows[0].get('contractType') != 'PERPETUAL' or rows[0].get('marginAsset') != 'USDT':
            raise Unknown('current BTCUSDT contract rules unavailable')
        return rows[0]

    def cancel_entries(self, snapshot):
        """Cancel/replace, never amend an order with an ambiguous cumulative fill."""
        if any(a.get('closePosition') is not True and a.get('reduceOnly') is not True for a in snapshot['open_algos']):
            raise Unknown('unmanaged conditional entry; cannot assume it is canceled')
        for algo in snapshot['open_algos']:
            row=self.state.db.execute('SELECT kind,payload FROM intents WHERE id=?',(algo.get('clientAlgoId'),)).fetchone()
            if not row or row[0]!='binance_algo':
                raise Unknown('unowned conditional protection cannot establish managed safety')
            payload=json.loads(row[1])
            if (any(algo.get(k)!=payload.get(k) for k in ('symbol','side','positionSide','workingType'))
                    or algo.get('orderType')!=payload.get('type')
                    or algo.get('closePosition') is not True or payload.get('closePosition')!='true'
                    or algo.get('priceProtect') is not False or payload.get('priceProtect')!='false'
                    or number(algo.get('triggerPrice'),positive=True)!=number(payload.get('triggerPrice'),positive=True)):
                raise Unknown('native protection differs from its durable request')
        for order in snapshot['open_orders']:
            if order.get('reduceOnly') is True:
                raise Unknown('working reduction must settle before strategy actions')
            identity = order.get('clientOrderId')
            row = self.state.db.execute('SELECT kind,payload FROM intents WHERE id=?', (identity,)).fetchone()
            if not row or row[0] != 'binance_order':
                raise Unknown('unowned entry order; no cancellation or additional risk')
            original = json.loads(row[1])
            if original.get('reduceOnly') == 'true' or any(original.get(k) != order.get(k) for k in ('symbol', 'side', 'positionSide', 'type')):
                raise Unknown('entry scope differs from durable request')
            snapshot = safety.cancel_entry(self.reader, self.state, self.send, self.uid,
                0, identity, authorized=self.authorized)
        if snapshot['possible_entry_remainders']:
            raise Unknown('entry remainder not confirmed terminal')
        return snapshot

    def cleanup_flat(self, snapshot):
        if number(snapshot['quantity_btc']) or snapshot['possible_entry_remainders']:
            raise Unknown('cleanup requires verified flat account without entry remainders')
        for order in snapshot['open_algos']:
            identity = order.get('clientAlgoId')
            row = self.state.db.execute('SELECT kind,payload FROM intents WHERE id=?', (identity,)).fetchone()
            if not row or row[0] != 'binance_algo' or json.loads(row[1]).get('closePosition') != 'true':
                raise Unknown('unowned conditional order blocks new exposure')
            # A new external position or entry can appear after the flat
            # readback. Check before removing a leg that may now protect it,
            # including between the two cancellations; never discover it only
            # after the protection has already been removed.
            snapshot=safety._gate(self.reader,self.state,self.uid,self.authorized,
                                  expected_owner=dict(snapshot))
            if number(snapshot['quantity_btc']) or snapshot['possible_entry_remainders']:
                raise Unknown('account changed before flat protection cleanup')
            cancel_id = client_id(self.state.identity, 0, 'flat-retire:'+identity)
            safety._once(self.state, cancel_id, 'binance_algo_cancel', {'clientAlgoId':identity},
                         self.send, 'DELETE', '/fapi/v1/algoOrder', at_ms=int(self.reader.clock()*1000))
            if not safety.settled_protection(self.reader,self.state,identity):
                raise Unknown('flat protection child or cancellation unresolved')
            self.state.finish(cancel_id, 'confirmed', {'target':identity, 'terminal':True})
            snapshot = self.reader.snapshot(self.uid)
            if number(snapshot['quantity_btc']) or snapshot['possible_entry_remainders']:
                raise Unknown('account changed during flat cleanup')
        return snapshot

    def retire_stale(self, snapshot):
        """Retire unresolved risk-reducing requests on a verified flat account.

        With no position, no working order or conditional order and no possible
        entry, such a request can no longer change exposure. It may have run
        earlier (a transfer, or a close-all order cancelled by flat cleanup);
        `void` does not assert that it was never accepted. Its signed timestamp
        expired long ago, so it cannot be accepted later. Entries and partial
        fills are never retired.
        """
        if (number(snapshot['quantity_btc']) or snapshot['possible_entry_remainders']
                or snapshot['open_orders'] or snapshot['open_algos'] or blocking(self.state)):
            return
        observed = snapshot.get('observed_at_ms')
        if type(observed) is not int:
            return
        for pending in self.state.pending():
            row = self.state.db.execute('SELECT result FROM intents WHERE id=?', (pending['id'],)).fetchone()
            result = json.loads(row[0])
            prepared = result.get('prepared_at_ms')
            if pending['status'] != 'unknown' or type(prepared) is not int or observed-prepared < UNACCEPTED_AFTER_MS:
                continue
            if pending['kind'] in ('binance_order','binance_algo'):
                # A fill-capable identity stays unknown unless Binance reports -2013.
                if not self.reader.proven_absent(self.state, pending):
                    continue
            elif pending['kind'] not in ('binance_margin','binance_cancel','binance_algo_cancel'):
                continue
            self.state.finish(pending['id'], 'void', {**result, 'flat_observed_at_ms': observed})

    def settle(self):
        self.reader.recover_pending(self.state)
        snapshot = self.cancel_entries(self.reader.snapshot(self.uid))
        self.reader.recover_pending(self.state)
        # An unresolved risk-reducing intent blocks new risk (entry, add and the
        # next transfer all require no pending intent) but not protection or exits.
        if blocking(self.state):
            raise Unknown('durable operation remains unknown; no additional risk')
        return snapshot

    def entry_fill_proven(self, plan, snapshot):
        """Every native fill after the entry's flat boundary is that entry's own
        fill, and together they are the current position.

        One complete trade page after the flat snapshot's cursor. Without a recent
        cursor (the default trade read covers seven days) a single time window
        from the flat boundary is read instead. An external, manual or other
        owned fill, a missing boundary or an unreadable page is no proof; this
        never authorizes a write without it.
        """
        link = (self.state.get('entry_campaigns') or {}).get(plan['id'])
        cursor = link.get('after_trade_id') if link else None
        start = link.get('prepared_at') if link else None
        q = number(snapshot['quantity_btc'])
        now = int(self.reader.clock()*1000)
        if (type(cursor) is not int or cursor < -1 or type(start) is not int or not 0 < start <= now
                or not q or snapshot['possible_entry_remainders']):
            return False
        parent = owned_observation(self.state,self.reader,plan['id'])['parent']
        if parent.get('status') not in TERMINAL or (q > 0) != (parent.get('side') == 'BUY'):
            return False
        if cursor >= 0:
            query = {'symbol':'BTCUSDT','fromId':cursor+1,'limit':1000}
        elif now-start < 7*86400000:
            query = {'symbol':'BTCUSDT','startTime':start,'endTime':now,'limit':1000}
        else:
            return False
        page = self.reader.get('/fapi/v1/userTrades',query)
        if not isinstance(page,list) or len(page) >= 1000:
            return False
        ids = set(); total = D(0)
        for trade in page:
            if (trade.get('symbol') != 'BTCUSDT' or trade.get('positionSide') != 'BOTH'
                    or str(trade.get('orderId')) != str(parent.get('orderId')) or trade.get('side') != parent['side']
                    or type(trade.get('id')) is not int or trade['id'] <= cursor or trade['id'] in ids):
                return False
            ids.add(trade['id']); total += number(trade.get('qty'),positive=True)
        last = snapshot.get('last_fill_id')
        return parent if total == number(parent['executedQty']) == abs(q) and (last == cursor or last in ids) else None

    def protect_entry(self, snapshot, plan, *, proven_order=None):
        """Protect only verified fills of the journaled entry, including partials.

        `snapshot` must be observed after the latest write; it is reused by the
        first safety write so protection is not delayed by repeated reads.
        """
        q = number(snapshot['quantity_btc'])
        if not q:
            return snapshot
        expected = number(plan['quantity_btc'])
        if q*expected <= 0 or abs(q) > abs(expected):
            raise Unknown('entry fill direction or size conflicts with its plan')
        observed = proven_order or owned_observation(self.state,self.reader,plan['id'])['parent']
        if number(observed['executedQty']) != abs(q):
            raise Unknown('actual position is not the verified entry fill')
        # The reserve was calculated before entry; scale to actual executed size.
        target = number(plan['allocated_margin_usdt'])*abs(q/expected)
        replacement_started=snapshot.get('wallet_observed_from_ms',int(self.reader.clock()*1000))
        # Refresh stale preflight rules before protecting a resumed entry.
        fresh = (type(plan.get('observed_at')) is int
                 and 0 <= int(self.reader.clock()*1000)-plan['observed_at'] <= RULES_FRESH_MS)
        rules = plan.get('instrument') if fresh and plan.get('instrument') else self.instrument()
        self.reader.set_deadline(PROTECT_SECONDS, extend_only=True)
        try:
            # With an earlier transfer unresolved, protection is still tried
            # against the observed liquidation price; it never sends another.
            # Place the stop before the margin transfer when liquidation already
            # sits beyond it, so that write is not a bare position.
            fits = _protection_fits(snapshot, plan['stop'], plan['take'])
            if plan.get('guard_epoch') is not None:
                guard = (number(plan['guard_stop']), number(plan['guard_take']))
                guard_epoch = plan['guard_epoch']
            else:
                guard = None if fits else _guard_prices(snapshot, plan, rules)
                guard_epoch = None
                if guard is not None:
                    guard_epoch = self.epoch()
                    plan['guard_epoch'] = guard_epoch
                    plan['guard_stop'] = str(guard[0])
                    plan['guard_take'] = str(guard[1])
                    self.state.set('entry_plan', plan)
            journal=self.state.get('binance_protection_replacement')
            request=_guard_replacement_request(self.state,plan)
            resuming_guard=bool(request and journal and
                                (journal.get('request')==request or request in journal.get('superseded',[])))
            if resuming_guard:
                # The replacement may already have retired one or both guard
                # legs. Resume its pinned identities before touching that guard.
                snapshot=safety.replace_protection(self.reader,self.state,self.send,self.uid,
                    guard_epoch,plan['epoch'],plan['stop'],plan['take'],instrument=rules,
                    authorized=self.authorized,expected_owner=dict(snapshot))
                # A finished journal is idempotent, not proof that its pair is
                # still active at this restart. Confirm the successor itself.
                snapshot=safety.protect_existing(self.reader,self.state,self.send,self.uid,
                    safety.replacement_epoch(self.state,plan['epoch']),plan['stop'],plan['take'],
                    instrument=rules,authorized=self.authorized,snapshot=snapshot,
                    expected_owner=dict(snapshot))
            elif guard is not None:
                # Cover the fill at the current liquidation before moving margin.
                snapshot = safety.protect_existing(self.reader,self.state,self.send,self.uid,
                    guard_epoch,guard[0],guard[1],instrument=rules,authorized=self.authorized,
                    snapshot=snapshot,expected_owner=dict(snapshot))
            elif fits:
                snapshot = safety.protect_existing(self.reader,self.state,self.send,self.uid,
                    plan['epoch'],plan['stop'],plan['take'],instrument=rules,authorized=self.authorized,
                    snapshot=snapshot,expected_owner=dict(snapshot))
            # A saved entry target is not permission to exceed today's cap,
            # including when its transfer/replacement already completed.
            capital=min(number(snapshot['wallet_usdt']),number(snapshot.get('equity_usdt')))
            limit=getattr(self.reader,'capital_limit',None)
            if limit is not None:capital=min(capital,number(limit,positive=True))
            places=rules.get('quotePrecision')
            if type(places) is not int or not 0<=places<=8:
                raise Blocked('settlement amount precision unavailable')
            cap=floor_step(max(D(0),capital)*MAX_ISOLATED_MARGIN_FRACTION,D(1).scaleb(-places))
            if max(target,number(snapshot['isolated_wallet_usdt']))>cap:
                raise Blocked('entry margin target exceeds the current collateral limit')
            if (not resuming_guard and number(snapshot['isolated_wallet_usdt']) < target
                    and not any(p['kind']=='binance_margin' for p in self.state.pending())):
                snapshot = safety.add_margin(self.reader,self.state,self.send,self.uid,
                    plan['epoch'],target,instrument=rules,authorized=self.authorized,snapshot=snapshot,
                    expected_owner=dict(snapshot))
            if guard_epoch is not None and not resuming_guard:
                snapshot = safety.replace_protection(self.reader,self.state,self.send,self.uid,
                    guard_epoch,plan['epoch'],plan['stop'],plan['take'],instrument=rules,
                    authorized=self.authorized,expected_owner=dict(snapshot))
            elif not fits and not resuming_guard:
                snapshot = safety.protect_existing(self.reader,self.state,self.send,self.uid,
                    plan['epoch'],plan['stop'],plan['take'],instrument=rules,authorized=self.authorized,
                    snapshot=snapshot,expected_owner=dict(snapshot))
            if number(snapshot['isolated_wallet_usdt']) < target:
                # A completed transfer must not be sent again after restart.
                # Nor may withdrawn/unconfirmed collateral become a smaller
                # initial liquidation buffer merely because the pair is NEW.
                raise Blocked('entry collateral no longer funds its original protection buffer')
        except (Blocked, Unknown):
            # Native entry and protection are NOT atomic. Try a bounded reduction
            # with its own budget, but never assert that a disconnected venue accepted it.
            # Only the proven own fill is reduced: a manual or external fill that
            # arrived meanwhile leaves the whole position untouched and unknown.
            self.reader.set_deadline(REDUCE_SECONDS, extend_only=True)
            try:
                current = self.reader.snapshot(self.uid)
                if number(current['quantity_btc']) != q:
                    # A protective child may have reduced the fill between reads.
                    # Full native fill reconciliation is required for that residual.
                    self.recover_exposure(current)
                elif (not current['possible_entry_remainders']
                        and self.entry_fill_proven(plan, current)):
                    self.close(current, rules)
            except (Blocked, Unknown):
                pass
            raise
        self._save_protection(dict(epoch=safety.replacement_epoch(self.state,plan['epoch']) if guard_epoch is not None else plan['epoch'],
                       stop=plan['stop'],take=plan['take'],campaign=plan['campaign'],
                       accepted_at_ms=int(self.reader.clock()*1000),started_at_ms=replacement_started),
                       snapshot,clear_entry_plan=True)
        return snapshot

    def entry_residual(self, snapshot, plan, ownership):
        """A smaller position is reducible only after native ownership closes."""
        q = number(snapshot['quantity_btc'])
        parent = owned_observation(self.state,self.reader,plan['id'])['parent']
        filled = number(parent['executedQty'])
        if (not q or snapshot['possible_entry_remainders'] or parent.get('status') not in TERMINAL
                or q*number(plan['quantity_btc'])<=0 or not 0<abs(q)<filled
                or ownership.get('status')!='reconciled' or ownership.get('campaign')!=plan['campaign']):
            return False
        # Reconciliation accounts for every fill. A partially filled protective
        # child still working could reduce the position again during our write.
        for identity, raw, status in self.state.db.execute("SELECT id,payload,status FROM intents WHERE kind='binance_algo'"):
            if status in ('rejected','void'):
                continue
            payload=json.loads(raw)
            if payload.get('closePosition')!='true':
                continue
            observed=owned_observation(self.state,self.reader,identity,conditional=True)
            child=observed['child']
            if child is not None and number(child['executedQty']):
                if not safety.conditional_is_terminal(observed):
                    raise Unknown('protective child fill is not terminal')
        fresh=self.reader.snapshot(self.uid)
        if any(fresh[k]!=snapshot[k] for k in ('quantity_btc','wallet_usdt','entry','possible_entry_remainders')):
            raise Unknown('residual changed after protective child readback')
        return True

    def close(self, snapshot, rules=None, *, stop=None):
        """Durable reduce-only exit from an owned snapshot.

        The reduction refreshes the account and checks that this ownership
        boundary has not changed.
        """
        q = number(snapshot['quantity_btc'])
        if not q:
            return snapshot
        if snapshot['possible_entry_remainders']:
            raise Unknown('cannot close while a remainder could reopen the position')
        rules = rules or self.instrument()
        operation = self.state.get('position_exit')
        row=None
        retry_zero=False
        retry_budget={}
        if operation is not None:
            if 'zero_retry_session' in operation:
                retry_budget={'zero_retry_session':operation['zero_retry_session']}
            prior=client_id(self.state.identity,operation['epoch'],'reduce')
            row=self.state.db.execute('SELECT status,result FROM intents WHERE id=?',(prior,)).fetchone()
            if row is None and q*operation['direction']>0:
                # Unsent request. One market order cannot exceed the current
                # MARKET_LOT_SIZE, so a larger position leaves in slices.
                legal=market_quantity(abs(q),snapshot['mark_price'],rules,reduce_only=True)
                if legal<=0:
                    raise Blocked('position is below the native reducible quantity')
                if number(operation['quantity'])!=legal:
                    operation={**operation,'quantity':str(legal),'position_at_request':str(abs(q))}
                    self.state.set('position_exit',operation)
            if row and row[0]=='confirmed':
                terminal=owned_observation(self.state,self.reader,prior)['parent']
                if terminal.get('status') not in TERMINAL:
                    raise Unknown('confirmed reduction is not terminal at exchange')
                if number(terminal['executedQty'])<=0:
                    if (q*operation['direction']<=0
                            or abs(q)!=number(operation.get('position_at_request',operation['quantity']))):
                        raise Unknown('position changed after zero-fill reduction')
                    if retry_budget and retry_budget['zero_retry_session']==self.session:
                        raise Unknown('zero-fill reduction retry exhausted for this session')
                    # One proven zero-fill retry per manual session, including
                    # cleanup. A later session rechecks ownership before retrying.
                    retry_budget={'zero_retry_session':self.session}
                    operation=None
                    retry_zero=True
                else:
                    # Only a known terminal partial may create a fresh remainder order.
                    retry_budget={}
                    operation=None
            elif row and row[0]=='rejected':
                # Refused locally or by Binance: nothing executed under that identity.
                operation=None
        if operation is None:
            legal=market_quantity(abs(q),snapshot['mark_price'],rules,reduce_only=True)
            if legal<=0:
                raise Blocked('position is below the native reducible quantity')
            operation = dict(epoch=self.epoch(), quantity=str(legal),direction=1 if q>0 else -1,
                             position_at_request=str(abs(q)),**retry_budget)
            if stop is not None and (retry_zero or not row or row[0] in ('rejected','void')):
                operation['trigger_stop']=str(number(stop,positive=True))
            self.state.set('position_exit',operation)
        elif row is None:
            # Explicit unconditional exits override an unsent stop condition;
            # recovery supplies its saved condition until an intent is prepared.
            operation=dict(operation)
            operation.pop('trigger_stop',None)
            if stop is not None:operation['trigger_stop']=str(number(stop,positive=True))
            self.state.set('position_exit',operation)
        opened=number(operation.get('position_at_request', operation['quantity']))
        if q*operation['direction']<=0 or abs(q)>opened:
            raise Unknown('position grew during durable exit')
        identity=client_id(self.state.identity,operation['epoch'],'reduce')
        readback_changed=False
        try:
            result = safety.reduce_existing(self.reader,self.state,self.send,self.uid,
                operation['epoch'],operation['quantity'],instrument=rules,authorized=self.authorized,
                expected_owner=dict(snapshot),
                expected_direction=operation['direction'],
                stop=stop if retry_zero or not row or row[0] in ('rejected','void') else None)
        except Unknown:
            row=self.state.db.execute('SELECT status FROM intents WHERE id=?',(identity,)).fetchone()
            if not row or row[0]!='confirmed':
                raise
            # Another owned protective fill can win the readback race. Only a
            # complete fresh fill audit can turn that conflict into exit progress.
            result=self.reader.snapshot(self.uid)
            readback_changed=True
        if result is None:
            self.state.set('position_exit',None)
            return None
        if number(result['quantity_btc']) or readback_changed:
            terminal=owned_observation(self.state,self.reader,identity)['parent']
            if terminal.get('status') not in TERMINAL or number(terminal['executedQty'])<=0:
                raise Unknown('exit has no terminal fill progress')
            from .campaign import Campaign
            from .ownership import reconcile
            ownership=reconcile(self.state,self.reader,Campaign.restore(self.state.get('linear_campaign')),result)
            self.reconciled=(result,len(self.actions),ownership)
            remaining=number(result['quantity_btc'])
            if remaining*q<0 or abs(remaining)>=abs(q):
                raise Unknown('owned terminal exit did not shrink exposure')
            if remaining:
                self.exit_progress+=1
                raise Unknown('partial exit remains; reconcile before another reduction')
        self.state.set('position_exit',None)
        return self.cleanup_flat(result)

    def close_owned(self, rules=None, *, stop=None):
        """Reconcile before reducing; an optional stop must still be crossed."""
        from .campaign import Campaign
        from .ownership import reconcile
        if stop is not None:stop=number(stop,positive=True)
        self.reader.set_deadline(REDUCE_SECONDS, extend_only=True)
        rules=rules or self.instrument()
        current=self.settle()
        ownership=reconcile(self.state,self.reader,
                            Campaign.restore(self.state.get('linear_campaign')),current)
        self.reconciled=(current,len(self.actions),ownership)
        q=number(current['quantity_btc'])
        mark=number(current['mark_price'])
        if stop is not None and q and not (mark<=stop if q>0 else mark>=stop):
            return None
        return self.close(current,rules,stop=stop)

    def recover_exposure(self, snapshot):
        # Match the complete native fill history before changing any position;
        # only protection of the journaled entry's own verified fill precedes it.
        # A stored plan alone cannot authorize changes to external/manual trades.
        self.recover_entry_protection(snapshot)
        plan=self.state.get('entry_plan')
        if plan and number(snapshot['quantity_btc']) and not self.state.get('position_exit'):
            try:
                proven=self.entry_fill_proven(plan,snapshot)
            except (Blocked,Unknown):
                proven=False
            if proven:
                snapshot=self.protect_entry(snapshot,plan,proven_order=proven)
        ownership=None
        if number(snapshot['quantity_btc']) or self.state.get('entry_campaigns'):
            from .campaign import Campaign
            from .ownership import reconcile
            checkpoint=self.state.get('linear_campaign')
            if checkpoint is None:
                raise Unknown('position recovery lacks its model/ownership checkpoint')
            try:
                ownership=reconcile(self.state,self.reader,Campaign.restore(checkpoint),snapshot)
                self.reconciled=(snapshot,len(self.actions),ownership)
            except (Blocked,Unknown):
                # A fill of the journaled entry, sent from a verified flat account,
                # is protected when every fill since that flat boundary is its own,
                # even if the full history audit is unavailable. An external or
                # manual fill, or no such proof, leaves the position untouched.
                # The audit still gates new risk.
                plan=self.state.get('entry_plan')
                if plan and number(snapshot['quantity_btc']) and not self.state.get('position_exit'):
                    try:
                        proven=self.entry_fill_proven(plan,snapshot)
                        if proven:self.protect_entry(snapshot,plan,proven_order=proven)
                    except (Blocked,Unknown):pass
                raise
        if not number(snapshot['quantity_btc']):
            snapshot = self.cleanup_flat(snapshot)
            self.retire_stale(snapshot)
            if not self.state.pending():
                replacement=self.state.get('binance_protection_replacement')
                if replacement and not replacement.get('done'):
                    for identity in replacement['request']['old_ids']+replacement['request']['new_ids']:
                        if self.state.db.execute('SELECT 1 FROM intents WHERE id=?',(identity,)).fetchone() and not safety.settled_protection(self.reader,self.state,identity):
                            raise Unknown('flat replacement leg is not terminal')
                    replacement['done']=True
                    self.state.set('binance_protection_replacement',replacement)
                self.state.set('entry_plan',None)
                self.state.set('entry_fill',None)
                self.state.set('position_exit',None)
                self.state.set('position_protection',None)
                self.state.set('session_replacement',None)
            return snapshot
        if ownership and ownership.get('protective_exit_started'):
            # A native closePosition child has already begun this campaign's
            # exit. A terminal partial is not permission to hold or buy it back
            # under another healthy pair, even in the original entry session.
            self.risk_audit_ok=False
            self.entry_constraint='native_protection_exit_started'
            self.reader.set_deadline(REDUCE_SECONDS,extend_only=True)
            return self.close(snapshot)
        operation=self.state.get('position_exit')
        if operation:
            reduced=self.close(snapshot,stop=operation.get('trigger_stop'))
            if reduced is not None:return reduced
        plan = self.state.get('entry_plan')
        if plan:
            if self.entry_residual(snapshot,plan,ownership):
                self.reader.set_deadline(REDUCE_SECONDS, extend_only=True)
                return self.close(snapshot)
            return self.protect_entry(snapshot,plan)
        replacement=self.state.get('session_replacement')
        if replacement:
            # A complete owned old pair keeps this position safe while the
            # model decides. Holding retries the amendment in maintain(); an
            # exit can reduce the proven position even if the new leg is refused.
            # Entry remainders and unproven ownership were rejected above.
            if self.planned_protection(snapshot):
                return snapshot
            try:
                return self.complete_replacement(replacement,self.instrument(),snapshot=snapshot)
            except (Blocked,Unknown):
                # Keep a complete native pair; otherwise try an owned exit
                # when no entry remainders remain.
                if not snapshot['native_full_position_protected'] and not snapshot['possible_entry_remainders']:
                    self.close_owned()
                raise
        if not self.planned_protection(snapshot):
            protection = self.state.get('position_protection')
            if not protection:
                raise Unknown('unprotected position has no owned protection plan')
            try:
                return safety.protect_existing(self.reader,self.state,self.send,self.uid,
                    protection['epoch'],protection['stop'],protection['take'],
                    instrument=self.instrument(),authorized=self.authorized,expected_owner=dict(snapshot))
            except (Blocked,Unknown):
                self.close_owned()
                raise
        return self.ensure_liquidation_buffer(snapshot)

    def planned_protection(self,snapshot):
        protection=self.state.get('position_protection')
        if not protection:return False
        active={a.get('clientAlgoId'):a for a in snapshot['open_algos']}
        for kind,price in (('STOP_MARKET',protection['stop']),('TAKE_PROFIT_MARKET',protection['take'])):
            identity=client_id(self.state.identity,protection['epoch'],kind)
            order=active.get(identity)
            if order is None or order.get('algoStatus')!='NEW':return False
            if order.get('orderType')!=kind or number(order['triggerPrice'])!=number(price):
                raise Unknown('active protection does not match the owned position plan')
        confirmed=snapshot['native_full_position_protected'] and snapshot['stop_before_liquidation']
        if confirmed and type(protection.get('accepted_at_ms')) is not int:
            protection['accepted_at_ms']=int(self.reader.clock()*1000)
            self.state.set('position_protection',protection)
        return confirmed

    def complete_replacement(self,replacement,rules,*,snapshot=None):
        before=snapshot if snapshot is not None else self.reader.snapshot(self.uid)
        protection=self.state.get('position_protection')
        if (protection and protection.get('campaign')==replacement.get('campaign')
                and protection.get('epoch')==replacement.get('old_epoch')
                and self.planned_protection(before)):
            # An earlier failed preflight did not retire this still-NEW pair.
            # Its latest observed live interval survives delayed retry/catch-up.
            # The wallet read starts before the algo list, so it is a safe lower
            # bound even if a cancellation wins just after that list was read.
            observed=before.get('wallet_observed_from_ms')
            started=replacement.get('started_at_ms')
            if (type(observed) is int and observed>=protection.get('accepted_at_ms',observed)
                    and (type(started) is not int or observed>started)):
                replacement={**replacement,'started_at_ms':observed}
                self.state.set('session_replacement',replacement)
        q=number(before['quantity_btc'])
        mark=number(before['mark_price'])
        stop=number(replacement['stop'])
        if q and (mark<=stop if q>0 else mark>=stop):
            reduced=self.close_owned(rules,stop=stop)
            if reduced is not None:
                return self.recover_exposure(reduced)
        try:
            result=safety.replace_protection(self.reader,self.state,self.send,self.uid,
                replacement['old_epoch'],replacement['epoch'],replacement['stop'],replacement['take'],
                instrument=rules,authorized=self.authorized,expected_owner=dict(before))
        except (Blocked,Unknown):
            # The mark may cross between the session decision and the adapter's
            # geometry gate. A fresh owned position can still leave safely.
            reduced=self.close_owned(rules,stop=stop)
            if reduced is not None:
                return self.recover_exposure(reduced)
            raise
        saved={**{k:v for k,v in replacement.items() if k!='old_epoch'},
               'epoch':safety.replacement_epoch(self.state,replacement['epoch']),
               'accepted_at_ms':int(self.reader.clock()*1000)}
        self._save_protection(saved, result)
        self.state.set('session_replacement',None)
        if number(result['quantity_btc'])!=q:
            return self.recover_exposure(result)
        return result

    def enter(self, model, snapshot):
        if self.state.pending() or snapshot['possible_entry_remainders'] or number(snapshot['quantity_btc']):
            raise Unknown('entry requires reconciled flat account')
        if not self.risk_audit_ok:
            raise Blocked('cashflow audit does not close the current wallet; no new exposure')
        self.reader.refresh_safety_observation()
        self.reader.ensure_capacity(ENTRY_RESERVE+PREVIEW_WEIGHT)
        plan = entry_preview(self.reader,model,snapshot)
        self.entry_constraint = plan.get('constraint')
        if not number(plan['quantity_btc']):
            return snapshot
        # Recheck after all sizing inputs. Never treat a preview as an order.
        fresh = self.reader.snapshot(self.uid)
        if any(fresh[k] != snapshot[k] for k in ('quantity_btc','wallet_usdt','available_usdt','possible_entry_remainders')) or fresh['open_algos'] or fresh['open_orders']:
            raise Unknown('account changed between sizing and entry')
        if abs(int(self.reader.clock()*1000)-plan['observed_at']) > 15000:
            raise Unknown('entry preflight expired')
        self.reader.ensure_capacity(ENTRY_RESERVE)
        if not self.may_enter():
            raise Blocked('session deadline or stop request prohibits a new entry')
        tick=[f['tickSize'] for f in plan['instrument']['filters'] if f.get('filterType')=='PRICE_FILTER'][0]
        if not limit_matches(self.reader,1 if plan['side']=='BUY' else -1,plan['entry_estimate'],tick,
                             quantity=abs(number(plan['quantity_btc'])),
                             completed_through=model.last):
            raise Unknown('order book changed before the order was sent')
        safety._check_cursor(self.reader,fresh)
        if not self.may_enter():
            raise Blocked('session deadline or stop request prohibits a new entry')
        if abs(int(self.reader.clock()*1000)-plan['observed_at'])>15000:
            raise Unknown('entry preflight expired during the final book read')
        self.check_entry_clock(model,fresh,plan['observed_at'])
        # An entry begun within the session retains a bounded protection budget;
        # the trading deadline must not cut network access immediately after fill.
        # Use the adapter clock. A wall monotonic here would outlive a virtual session
        # or expire a historical one immediately.
        self.reader.set_deadline(120, extend_only=True)
        epoch = self.epoch()
        identity = client_id(self.state.identity,epoch,'entry')
        payload = dict(symbol='BTCUSDT',positionSide='BOTH',side=plan['side'],type='LIMIT',
                       timeInForce='IOC',quantity=str(abs(number(plan['quantity_btc']))),
                       price=plan['entry_estimate'],newClientOrderId=identity,newOrderRespType='RESULT')
        plan.update(epoch=epoch,id=identity)
        self.state.set('entry_plan',plan)
        self.state.set('entry_fill',dict(campaign=plan['campaign'],requested=plan['requested_btc'],
                                         session=self.session,stop_budget=plan.get('stop_budget_usdt'),
                                         stop_slippage_fraction=plan.get('stop_slippage_fraction'),
                                         sizing_capital=plan.get('sizing_capital_usdt')))
        self.state.prepare(identity,'binance_order',payload,campaign=plan['campaign'],flat_snapshot=fresh,
                           result={'prepared_at_ms':int(self.reader.clock()*1000)})
        self.state.set('entry_timing',{'entry_id':identity,'quote_observation':plan['quote_observation'],
                                       'entry_limit_price':plan['entry_estimate']})
        safety.send_once(self.state,identity,self.send,'POST','/fapi/v1/order',payload)
        # Confirm this order, then protect, before cancel/history work.
        self.reader.recover_pending(self.state)
        try:
            snapshot,proven=self.reader.entry_snapshot(self.state,self.uid,identity,flat_snapshot=fresh)
        except (Blocked,Unknown):
            snapshot=self.reader.snapshot(self.uid)
            try:
                proven=self.entry_fill_proven(plan,snapshot)
            except (Blocked,Unknown):
                proven=False
        if proven:
            timing=self.state.get('entry_timing') or {}
            if timing.get('entry_id')==identity:
                timing['fill_confirmed_at_ms']=int(self.reader.clock()*1000)
                timing['entry_executed_btc']=str(number(proven['executedQty']))
                if number(proven.get('avgPrice','0'))>0:
                    timing['entry_avg_price']=str(number(proven['avgPrice']))
                self.state.set('entry_timing',timing)
            snapshot = self.protect_entry(snapshot,plan,proven_order=proven)
            return self.recover_exposure(snapshot)
        return self.recover_exposure(self.settle())

    def maintain(self, model, snapshot):
        snapshot=self.ensure_liquidation_buffer(snapshot)
        if not number(snapshot['quantity_btc']):
            return snapshot
        protection = self.state.get('position_protection')
        if not protection:
            raise Unknown('position protection ownership unavailable')
        opportunity = model.active
        if opportunity is None or opportunity.identity != protection['campaign']:
            raise Unknown('protection and model campaign disagree')
        rules = self.instrument()
        ticks = [r for r in rules['filters'] if r.get('filterType')=='PRICE_FILTER']
        if len(ticks)!=1:
            raise Unknown('current price tick unavailable')
        tick=number(ticks[0]['tickSize'],positive=True)
        q=number(snapshot['quantity_btc'])
        stop=floor_step(opportunity.stop,tick) if q>0 else -floor_step(-opportunity.stop,tick)
        if q>0 and opportunity.extended and model.entry_fill is not None:
            stop=max(stop,(model.entry_fill/tick).to_integral_value(rounding=ROUND_CEILING)*tick)
        # Strategy updates cannot spend a loss allowance already locked at the
        # exchange by a prior risk review of this same campaign.
        stop=max(stop,number(protection['stop'])) if q>0 else min(stop,number(protection['stop']))
        take=floor_step(opportunity.take,tick)+tick if q>0 else floor_step(opportunity.take,tick)
        same_prices=D(protection['stop'])==stop and D(protection['take'])==take
        replacement = self.state.get('session_replacement')
        active={a.get('clientAlgoId'):a for a in snapshot['open_algos']}
        now=int(self.reader.clock()*1000)
        ages=[]
        for kind in ('STOP_MARKET','TAKE_PROFIT_MARKET'):
            order=active.get(client_id(self.state.identity,protection['epoch'],kind),{})
            created=order.get('createTime') if order.get('algoStatus')=='NEW' else None
            ages.append(now-created if type(created) is int and 0<created<=now else None)
        if any(age is not None and age>=ALGO_HISTORY_MS for age in ages) and (not same_prices or replacement):
            raise Unknown('native protection is outside algo history; replacement needs manual resolution')
        renew=(all(age is not None and age<ALGO_HISTORY_MS for age in ages)
               and any(age>=PROTECTION_RENEW_MS for age in ages))
        if same_prices and not renew and replacement is None:
            return snapshot
        if replacement is None:
            replacement=dict(old_epoch=protection['epoch'],epoch=self.epoch(),stop=str(stop),take=str(take),campaign=opportunity.identity,
                             started_at_ms=int(self.reader.clock()*1000))
            self.state.set('session_replacement',replacement)
        return self.complete_replacement(replacement,rules,snapshot=snapshot)

    def decide(self, model, snapshot):
        """One shared decision path: existing exposure is settled before new risk."""
        action=model.action(number(snapshot['quantity_btc']))
        if action=='enter':
            snapshot=self.enter(model,snapshot)
            if number(snapshot['quantity_btc']):
                snapshot=self.enforce_holding_risk(snapshot)
                if not number(snapshot['quantity_btc']):action='exit'
        elif action=='exit':
            price_exit=(model.exit_cause=='price' and model.exit_campaign==model.position_campaign
                        and model.exit_stop is not None)
            if price_exit:
                updated=self.close_owned(stop=model.exit_stop)
                if updated is not None:
                    snapshot=updated
            else:
                snapshot=self.close(snapshot)
        elif action=='hold':
            snapshot=self.maintain(model,snapshot)
            if number(snapshot['quantity_btc']):
                before=snapshot
                snapshot=self.top_up(model,snapshot)
                if snapshot is not before:
                    snapshot=self.enforce_holding_risk(snapshot)
            if not number(snapshot['quantity_btc']):action='exit'
        return action,snapshot

    def top_up(self, model, snapshot):
        """Within the entry's own session, IOC-add toward the committed campaign size.

        A macro campaign's whole position stays inside its entry stop budget.
        Margin is added before the order so the enlarged isolated position still
        liquidates beyond the unchanged close-all stop; the deadline, stop request,
        quote, position and owned protection are checked again after that transfer.
        IOC leaves no remainder.
        """
        fill = self.state.get('entry_fill')
        protection = self.state.get('position_protection')
        if (not self.risk_audit_ok or not fill or self.session is None or fill.get('session') != self.session or not protection
                or fill.get('campaign') != protection.get('campaign') or model.active is None
                or model.active.identity != fill['campaign'] or not self.may_enter()):
            return snapshot
        risk=self.state.get('holding_risk') or {}
        if risk.get('status')!='observed' or risk.get('campaign')!=fill['campaign']:
            self.entry_constraint='holding_risk_unverified'
            return snapshot
        if (self.state.pending() or snapshot['possible_entry_remainders'] or snapshot['open_orders']
                or not self.planned_protection(snapshot)):
            return snapshot
        if abs(number(snapshot['quantity_btc'])) >= number(fill['requested']):
            return snapshot
        if model.active is model.macro_opportunity and fill.get('stop_budget') is None:
            return snapshot
        proof=self.reconciled
        ownership=proof[2] if proof and proof[0] is snapshot and proof[1]==len(self.actions) else {}
        if (ownership.get('status')!='reconciled'
                or ownership.get('campaign')!=fill['campaign']
                or ownership.get('protective_exit_started')
                or type(ownership.get('last_fill_id')) is not int
                or ownership['last_fill_id']!=snapshot.get('last_fill_id')
                or number(ownership.get('quantity','0'))!=number(snapshot['quantity_btc'])
                or ownership.get('campaign_fee_usdt') is None
                or ownership.get('campaign_realized_pnl_usdt') is None):
            self.entry_constraint='campaign_costs_unverified'
            return snapshot
        expected_owner=dict(snapshot)
        try:
            from .audit import funding_debit
            paid_funding=funding_debit(self.reader,self.state,fill['campaign'],snapshot)
        except (Blocked,Unknown,OSError,ValueError,KeyError,TypeError,ArithmeticError):
            self.entry_constraint='campaign_funding_unverified'
            return snapshot
        try:
            self.reader.refresh_safety_observation()
            self.reader.ensure_capacity(TOPUP_RESERVE+PREVIEW_WEIGHT)
        except Unknown:
            return snapshot  # a later poll of this session may add
        try:
            plan = topup_preview(self.reader, model, snapshot, fill['requested'],
                                 protection['stop'], protection['take'], fill.get('stop_budget'),
                                 fill.get('sizing_capital'),fill.get('stop_slippage_fraction'),
                                 paid_commission_usdt=ownership['campaign_fee_usdt'],
                                 realized_pnl_usdt=ownership['campaign_realized_pnl_usdt'],
                                 paid_funding_usdt=paid_funding,
                                 loss_ceiling_usdt=protection.get('loss_ceiling_usdt'))
        except ValueError:
            return snapshot
        self.entry_constraint = plan['constraint']
        if not number(plan['quantity_btc']):
            return snapshot
        fresh = self.reader.snapshot(self.uid)
        safety._check_owner(fresh,expected_owner)
        if any(number(fresh[k])!=number(snapshot[k]) for k in ('isolated_wallet_usdt','available_usdt')):
            raise Unknown('collateral changed between top-up sizing and order')
        if fresh['open_orders'] or not self.planned_protection(fresh):
            raise Unknown('account changed between top-up sizing and order')
        if abs(int(self.reader.clock()*1000)-plan['observed_at']) > 15000:
            raise Unknown('top-up preflight expired')
        self.reader.ensure_capacity(TOPUP_RESERVE)
        if not self.may_enter():
            raise Blocked('session deadline or stop request prohibits a new entry')
        self.reader.set_deadline(120, extend_only=True)
        epoch = self.epoch()
        # The venue moves the add's initial margin into the isolated wallet on fill.
        target = (number(plan['allocated_margin_usdt'])
                  - number(plan['quantity_btc'])*number(plan['entry_estimate'])/20)
        if number(fresh['isolated_wallet_usdt']) < target:
            if target > number(plan['sizing_capital_usdt']):
                raise Blocked('margin addition would exceed the sizing capital')
            fresh = safety.add_margin(self.reader,self.state,self.send,self.uid,epoch,
                                      target,instrument=self.instrument(),authorized=self.authorized,
                                      expected_owner=dict(fresh))
            # The transfer takes time. The deadline, a stop request and the quote
            # are checked again; the added margin only lowers risk.
            if not self.may_enter() or abs(int(self.reader.clock()*1000)-plan['observed_at']) > 15000:
                return fresh
            try:
                self.reader.ensure_capacity(TOPUP_RESERVE)
            except Unknown:
                return fresh
            # The earlier safety checks predate the transfer; the add needs them again.
            safety._check_owner(fresh,expected_owner)
            if (fresh['possible_entry_remainders'] or fresh['open_orders']
                    or not self.planned_protection(fresh)):
                raise Unknown('exposure or protection changed during the margin transfer; no add')
        safety._check_cursor(self.reader,expected_owner)
        if not self.may_enter() or abs(int(self.reader.clock()*1000)-plan['observed_at'])>15000:
            return fresh
        if not limit_matches(self.reader,1 if plan['side']=='BUY' else -1,plan['entry_estimate'],plan['tick'],
                             quantity=abs(number(plan['quantity_btc'])),
                             completed_through=model.last):
            return fresh
        # A stop can fill during the final book read. The old position cursor
        # cannot authorize an add that would reopen the now-flat account.
        safety._check_cursor(self.reader,expected_owner)
        if not self.may_enter() or abs(int(self.reader.clock()*1000)-plan['observed_at'])>15000:
            return fresh
        self.check_entry_clock(model,fresh,plan['observed_at'])
        projected_margin=(number(fresh['isolated_wallet_usdt'])
                          +number(plan['quantity_btc'])*number(plan['entry_estimate'])/20)
        if projected_margin>number(plan['stop_budget_capital_usdt'])*MAX_ISOLATED_MARGIN_FRACTION:
            self.entry_constraint='margin_or_funding_cap'
            return fresh
        identity = client_id(self.state.identity,epoch,'entry')
        payload = dict(symbol='BTCUSDT',positionSide='BOTH',side=plan['side'],type='LIMIT',
                       timeInForce='IOC',quantity=plan['quantity_btc'],
                       price=plan['entry_estimate'],newClientOrderId=identity,newOrderRespType='RESULT')
        self.state.prepare(identity,'binance_order',payload,campaign=fill['campaign'],position_snapshot=fresh,
                           result={'prepared_at_ms':int(self.reader.clock()*1000),
                                   'position_before_btc':str(fresh['quantity_btc'])})
        safety.send_once(self.state,identity,self.send,'POST','/fapi/v1/order',payload)
        snapshot = self.settle()
        return self.recover_exposure(snapshot)

    def finish(self):
        snapshot=self.recover_exposure(self.settle())
        snapshot=self.enforce_holding_risk(snapshot)
        if number(snapshot['quantity_btc']) and not self.planned_protection(snapshot):
            raise Unknown('session ended without confirmed exchange-hosted protection')
        return snapshot
