"""Native Binance entry, protection, recovery and bounded cleanup.

No daemon, independent cash ledger or strategy selector. Transport acknowledgments
never settle an intent. The CLI permits only explicit bounded trial writes.
"""
import json
from decimal import Decimal as D, ROUND_CEILING

from . import binance_safety as safety
from .native_preview import entry_preview, topup_preview
from .ownership import TERMINAL, owned_observation
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
# Contract rules from the entry preflight are reused only within one session.
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
            if field:
                timing[field]=int(self.reader.clock()*1000)
                self.state.set('entry_timing',timing)
        self.state.set('write_attempt_count',(self.state.get('write_attempt_count') or 0)+1)
        self.actions.append(dict(method=method, path=path, id=payload.get('newClientOrderId', payload.get('clientAlgoId', payload.get('origClientOrderId'))),
                                 at_ms=int(self.reader.clock()*1000)))
        return self.reader.send(method, path, payload)

    def epoch(self):
        value = max(int(self.reader.clock()*1000), (self.state.get('operation_sequence') or 0)+1)
        self.state.set('operation_sequence', value)
        return value

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
        # Rules from this entry's own preflight; a plan resumed later reads them again.
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
            if guard is not None:
                # Cover the fill at the current liquidation before moving margin.
                snapshot = safety.protect_existing(self.reader,self.state,self.send,self.uid,
                    guard_epoch,guard[0],guard[1],instrument=rules,authorized=self.authorized,
                    snapshot=snapshot,expected_owner=dict(snapshot))
            elif fits:
                snapshot = safety.protect_existing(self.reader,self.state,self.send,self.uid,
                    plan['epoch'],plan['stop'],plan['take'],instrument=rules,authorized=self.authorized,
                    snapshot=snapshot,expected_owner=dict(snapshot))
            if (number(snapshot['isolated_wallet_usdt']) < target
                    and not any(p['kind']=='binance_margin' for p in self.state.pending())):
                snapshot = safety.add_margin(self.reader,self.state,self.send,self.uid,
                    plan['epoch'],target,instrument=rules,authorized=self.authorized,snapshot=snapshot,
                    expected_owner=dict(snapshot))
            if guard_epoch is not None:
                snapshot = safety.replace_protection(self.reader,self.state,self.send,self.uid,
                    guard_epoch,plan['epoch'],plan['stop'],plan['take'],instrument=rules,
                    authorized=self.authorized,expected_owner=dict(snapshot))
            elif not fits:
                snapshot = safety.protect_existing(self.reader,self.state,self.send,self.uid,
                    plan['epoch'],plan['stop'],plan['take'],instrument=rules,authorized=self.authorized,
                    snapshot=snapshot,expected_owner=dict(snapshot))
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
        self.state.set('position_protection', dict(epoch=safety.replacement_epoch(self.state,plan['epoch']) if guard_epoch is not None else plan['epoch'],
                       stop=plan['stop'],take=plan['take'],campaign=plan['campaign'],
                       accepted_at_ms=int(self.reader.clock()*1000)))
        self.state.set('entry_plan', None)
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
                if observed['parent'].get('algoStatus') not in ('FINISHED','CANCELED','EXPIRED','REJECTED') or child.get('status') not in TERMINAL:
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
        if operation is not None:
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
                    raise Unknown('zero-fill reduction requires review before another attempt')
                # Only a known terminal partial may create a fresh remainder order.
                # Unknown outcomes keep the previous identity and never resend.
                operation=None
            elif row and row[0]=='rejected':
                # Refused locally or by Binance: nothing executed under that identity.
                operation=None
        if operation is None:
            legal=market_quantity(abs(q),snapshot['mark_price'],rules,reduce_only=True)
            if legal<=0:
                raise Blocked('position is below the native reducible quantity')
            operation = dict(epoch=self.epoch(), quantity=str(legal),direction=1 if q>0 else -1,
                             position_at_request=str(abs(q)))
            if stop is not None and (not row or row[0] in ('rejected','void')):
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
                stop=stop if not row or row[0] in ('rejected','void') else None)
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
                # Only a position with no native full protection at all is
                # reduced; a healthy leg or unresolved order keeps the block.
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
        return snapshot

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
        self.state.set('position_protection',{**{k:v for k,v in replacement.items() if k!='old_epoch'},
                       'epoch':safety.replacement_epoch(self.state,replacement['epoch']),
                       'accepted_at_ms':int(self.reader.clock()*1000)})
        self.state.set('session_replacement',None)
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
        snapshot = self.settle()
        # Shortest path to protection for this IOC's own proven fill; the full
        # ownership audit follows before any further decision.
        try:
            proven = self.entry_fill_proven(plan,snapshot)
        except (Blocked,Unknown):
            proven = False
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

    def maintain(self, model, snapshot):
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
            replacement=dict(old_epoch=protection['epoch'],epoch=self.epoch(),stop=str(stop),take=str(take),campaign=opportunity.identity)
            self.state.set('session_replacement',replacement)
        return self.complete_replacement(replacement,rules,snapshot=snapshot)

    def decide(self, model, snapshot):
        """One shared decision path: existing exposure is settled before new risk."""
        action=model.action(number(snapshot['quantity_btc']))
        if action=='enter':
            snapshot=self.enter(model,snapshot)
        elif action=='exit':
            snapshot=self.close(snapshot)
        elif action=='hold':
            snapshot=self.maintain(model,snapshot)
            if number(snapshot['quantity_btc']):
                snapshot=self.top_up(model,snapshot)
            else:
                action='exit'
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
                or type(ownership.get('last_fill_id')) is not int
                or ownership['last_fill_id']!=snapshot.get('last_fill_id')
                or number(ownership.get('quantity','0'))!=number(snapshot['quantity_btc'])
                or ownership.get('campaign_fee_usdt') is None
                or ownership.get('campaign_realized_pnl_usdt') is None):
            self.entry_constraint='campaign_costs_unverified'
            return snapshot
        expected_owner=dict(snapshot)
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
                                 realized_pnl_usdt=ownership['campaign_realized_pnl_usdt'])
        except ValueError:
            return snapshot
        self.entry_constraint = plan['constraint']
        if not number(plan['quantity_btc']):
            return snapshot
        fresh = self.reader.snapshot(self.uid)
        safety._check_owner(fresh,expected_owner)
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
        if number(snapshot['quantity_btc']) and not self.planned_protection(snapshot):
            raise Unknown('session ended without confirmed exchange-hosted protection')
        return snapshot
