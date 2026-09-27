"""The Binance order lifecycle used by both finite sessions and event replay.

No daemon, independent cash ledger or strategy selector. Transport acknowledgments
never settle an intent. The live CLI remains gated until native qualification.
"""
import json
from decimal import Decimal as D

from . import binance_safety as safety
from .linear_preview import research_side
from .native_preview import entry_preview, topup_preview
from .ownership import owned_observation
from .state import client_id
from .types import Blocked, Unknown, number, floor_step


class Lifecycle:
    def __init__(self, reader, state, uid, *, authorized=False, may_enter=lambda:True, session=None):
        self.reader, self.state, self.uid = reader, state, uid
        self.session = session
        self.authorized = authorized is True
        self.may_enter = may_enter
        self.actions = []
        self.entry_constraint = None

    def send(self, method, path, payload):
        if not self.authorized:
            raise Blocked('read-only session cannot send orders')
        self.state.set('write_attempt_count',(self.state.get('write_attempt_count') or 0)+1)
        self.actions.append(dict(method=method, path=path, id=payload.get('newClientOrderId', payload.get('clientAlgoId', payload.get('origClientOrderId')))))
        return self.reader.send(method, path, payload)

    def epoch(self):
        value = max(int(self.reader.clock()*1000), (self.state.get('operation_sequence') or 0)+1)
        self.state.set('operation_sequence', value)
        return value

    def snapshot(self):
        return self.reader.snapshot(self.uid)

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
                         self.send, 'DELETE', '/fapi/v1/algoOrder')
            if not safety.settled_protection(self.reader,self.state,identity):
                raise Unknown('flat protection child or cancellation unresolved')
            self.state.finish(cancel_id, 'confirmed', {'target':identity, 'terminal':True})
            snapshot = self.snapshot()
            if number(snapshot['quantity_btc']) or snapshot['possible_entry_remainders']:
                raise Unknown('account changed during flat cleanup')
        return snapshot

    def settle(self):
        self.reader.recover_pending(self.state)
        snapshot = self.cancel_entries(self.snapshot())
        self.reader.recover_pending(self.state)
        if self.state.pending():
            raise Unknown('durable operation remains unknown; no additional risk')
        return snapshot

    def protect_entry(self, snapshot, plan):
        """Protect only verified fills of the journaled entry, including partials."""
        q = number(snapshot['quantity_btc'])
        if not q:
            return snapshot
        expected = number(plan['quantity_btc'])
        if q*expected <= 0 or abs(q) > abs(expected):
            raise Unknown('entry fill direction or size conflicts with its plan')
        observed = owned_observation(self.state,self.reader,plan['id'])['parent']
        if number(observed['executedQty']) != abs(q):
            raise Unknown('actual position is not the verified entry fill')
        # The reserve was calculated before entry; scale to actual executed size.
        target = number(plan['allocated_margin_usdt'])*abs(q/expected)
        rules = self.instrument()
        try:
            if number(snapshot['isolated_wallet_usdt']) < target:
                snapshot = safety.add_margin(self.reader,self.state,self.send,self.uid,
                    plan['epoch'],target,authorized=self.authorized)
            snapshot = safety.protect_existing(self.reader,self.state,self.send,self.uid,
                plan['epoch'],plan['stop'],plan['take'],instrument=rules,authorized=self.authorized)
        except (Blocked, Unknown):
            # Native entry and protection are NOT atomic. Try a bounded reduction,
            # but never assert that a disconnected venue accepted it.
            try:
                current = self.snapshot()
                if number(current['quantity_btc']) and not current['possible_entry_remainders']:
                    self.close(current, rules)
            except (Blocked, Unknown):
                pass
            raise
        self.state.set('position_protection', dict(epoch=plan['epoch'],stop=plan['stop'],
                       take=plan['take'],campaign=plan['campaign']))
        self.state.set('entry_plan', None)
        return snapshot

    def close(self, snapshot, rules=None):
        q = number(snapshot['quantity_btc'])
        if not q:
            return snapshot
        if snapshot['possible_entry_remainders']:
            raise Unknown('cannot close while a remainder could reopen the position')
        operation = self.state.get('position_exit')
        if operation is not None:
            prior=client_id(self.state.identity,operation['epoch'],'reduce')
            row=self.state.db.execute('SELECT status,result FROM intents WHERE id=?',(prior,)).fetchone()
            if row is None and q*operation['direction']>0 and abs(q)<number(operation['quantity']):
                # The preflight rejected before preparing/sending an intent, so
                # native protection may safely shrink this unsent request.
                operation={**operation,'quantity':str(abs(q))}
                self.state.set('position_exit',operation)
            if row and row[0]=='confirmed':
                terminal=owned_observation(self.state,self.reader,prior)['parent']
                if terminal.get('status') not in ('FILLED','CANCELED','EXPIRED','EXPIRED_IN_MATCH','REJECTED'):
                    raise Unknown('confirmed reduction is not terminal at exchange')
                if number(terminal['executedQty'])<=0:
                    raise Unknown('zero-fill reduction requires review before another attempt')
                # Only a known terminal partial may create a fresh remainder order.
                # Unknown outcomes keep the previous identity and never resend.
                operation=None
        if operation is None:
            operation = dict(epoch=self.epoch(), quantity=str(abs(q)),direction=1 if q>0 else -1)
            self.state.set('position_exit',operation)
        if q*operation['direction']<=0 or abs(q) > number(operation['quantity']):
            raise Unknown('position grew during durable exit')
        result = safety.reduce_existing(self.reader,self.state,self.send,self.uid,
            operation['epoch'],operation['quantity'],instrument=rules or self.instrument(),authorized=self.authorized)
        if number(result['quantity_btc']):
            raise Unknown('partial exit remains; reconcile before another reduction')
        self.state.set('position_exit',None)
        return self.cleanup_flat(result)

    def recover_exposure(self, snapshot):
        # Match the complete native fill history before changing any position.
        # A stored plan alone cannot authorize changes to external/manual trades.
        if number(snapshot['quantity_btc']) or self.state.get('entry_campaigns'):
            from .campaign import Campaign
            from .ownership import reconcile
            checkpoint=self.state.get('linear_campaign')
            if checkpoint is None:
                raise Unknown('position recovery lacks its model/ownership checkpoint')
            reconcile(self.state,self.reader,Campaign.restore(checkpoint),snapshot)
        if not number(snapshot['quantity_btc']):
            snapshot = self.cleanup_flat(snapshot)
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
        if self.state.get('position_exit'):
            return self.close(snapshot)
        plan = self.state.get('entry_plan')
        if plan:
            return self.protect_entry(snapshot,plan)
        replacement=self.state.get('session_replacement')
        if replacement:
            return self.complete_replacement(replacement,self.instrument())
        if not self.planned_protection(snapshot):
            protection = self.state.get('position_protection')
            if not protection:
                raise Unknown('unprotected position has no owned protection plan')
            try:
                return safety.protect_existing(self.reader,self.state,self.send,self.uid,
                    protection['epoch'],protection['stop'],protection['take'],
                    instrument=self.instrument(),authorized=self.authorized)
            except (Blocked,Unknown):
                self.close(snapshot)
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
        return snapshot['native_full_position_protected'] and snapshot['stop_before_liquidation']

    def complete_replacement(self,replacement,rules):
        result=safety.replace_protection(self.reader,self.state,self.send,self.uid,
            replacement['old_epoch'],replacement['epoch'],replacement['stop'],replacement['take'],
            instrument=rules,authorized=self.authorized)
        self.state.set('position_protection',{k:v for k,v in replacement.items() if k!='old_epoch'})
        self.state.set('session_replacement',None)
        return result

    def enter(self, model, snapshot):
        if self.state.pending() or snapshot['possible_entry_remainders'] or number(snapshot['quantity_btc']):
            raise Unknown('entry requires reconciled flat account')
        plan = entry_preview(self.reader,model,snapshot,side=research_side(self.state))
        self.entry_constraint = plan.get('constraint')
        if not number(plan['quantity_btc']):
            return snapshot
        if self.state.get('research_chase_bound') and not self._within_chase_bound(model, plan):
            # The campaign stays unconsumed. A later fresh poll can enter inside the bound.
            self.entry_constraint = 'chase_bound'
            return snapshot
        if self.state.get('research_funding_gate') and not self._funding_allows(plan):
            # Crowded funding skips this poll only. The campaign stays open.
            self.entry_constraint = 'funding_gate'
            return snapshot
        # Recheck after all sizing inputs. Never treat a preview as an order.
        fresh = self.snapshot()
        if any(fresh[k] != snapshot[k] for k in ('quantity_btc','wallet_usdt','available_usdt','possible_entry_remainders')) or fresh['open_algos'] or fresh['open_orders']:
            raise Unknown('account changed between sizing and entry')
        if abs(int(self.reader.clock()*1000)-plan['observed_at']) > 15000:
            raise Unknown('entry preflight expired')
        self.reader.ensure_capacity(1600)
        if not self.may_enter():
            raise Blocked('session deadline or stop request prohibits a new entry')
        # An entry begun within the session retains a bounded protection budget;
        # the trading deadline must not cut network access immediately after fill.
        # Use the adapter clock. A wall monotonic here would outlive a virtual session
        # or expire a historical one immediately.
        self.reader.deadline=self.reader.monotonic()+120
        epoch = self.epoch()
        identity = client_id(self.state.identity,epoch,'entry')
        payload = dict(symbol='BTCUSDT',positionSide='BOTH',side=plan['side'],type='LIMIT',
                       timeInForce='IOC',quantity=str(abs(number(plan['quantity_btc']))),
                       price=plan['entry_estimate'],newClientOrderId=identity,newOrderRespType='RESULT')
        plan.update(epoch=epoch,id=identity)
        self.state.set('entry_plan',plan)
        self.state.set('entry_fill',dict(campaign=plan['campaign'],requested=plan['requested_btc'],
                                         session=self.session))
        self.state.prepare(identity,'binance_order',payload,campaign=plan['campaign'],flat_snapshot=fresh)
        try:
            self.send('POST','/fapi/v1/order',payload)
        except Exception:
            pass  # query, never resend an uncertain write
        snapshot = self.settle()
        return self.recover_exposure(snapshot)

    def _funding_allows(self, plan):
        """Skip a new entry when the last settled funding already charges that side.

        0.0001 per eight hours is the exchange's ordinary quoted rate. A long is
        skipped only above it, a short only below its negative. The campaign
        is not consumed.
        """
        query = getattr(self.reader, 'last_settled_funding', None)
        if query is None:
            raise Blocked('funding gate requires settled funding on the reader')
        rate = query(int(self.reader.clock() * 1000))
        if rate is None:
            return False
        rate = number(rate)
        neutral = number('0.0001')
        side = plan.get('side')
        if side == 'BUY':
            return rate <= neutral
        if side == 'SELL':
            return rate >= -neutral
        raise Blocked('funding gate requires a buy or sell plan')

    def _within_chase_bound(self, model, plan):
        """Entry may not extend more than one signal risk beyond that bar's close.

        The risk distance is the signal close minus its own stop. No new multiple.
        """
        opportunity = model.model.active
        if opportunity is None:
            raise Unknown('chase bound requires the active opportunity')
        interval = model.model.interval
        if type(opportunity.identity) is not int or opportunity.identity % interval:
            raise Unknown('opportunity identity is not a completed bar')
        open_ms = opportunity.identity - interval
        rows = self.reader.get('/fapi/v1/klines', {
            'symbol': 'BTCUSDT', 'interval': '4h', 'startTime': open_ms,
            'endTime': opportunity.identity - 1, 'limit': 1})
        if len(rows) != 1 or int(rows[0][0]) != open_ms:
            raise Unknown('signal bar unavailable for the chase bound')
        close = number(rows[0][4], positive=True)
        span = abs(close - opportunity.stop)
        if span <= 0:
            return False
        price = number(plan['entry_estimate'], positive=True)
        if opportunity.direction > 0:
            return price <= close + span
        if opportunity.direction < 0:
            return price >= close - span
        return False

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
        take=floor_step(opportunity.take,tick)+tick if q>0 else floor_step(opportunity.take,tick)
        if D(protection['stop'])==stop and D(protection['take'])==take and not self.state.get('session_replacement'):
            return snapshot
        replacement = self.state.get('session_replacement')
        if replacement is None:
            replacement=dict(old_epoch=protection['epoch'],epoch=self.epoch(),stop=str(stop),take=str(take),campaign=opportunity.identity)
            self.state.set('session_replacement',replacement)
        return self.complete_replacement(replacement,rules)

    def decide(self, model, snapshot):
        """One shared decision path: existing exposure is settled before new risk."""
        action=model.action(number(snapshot['quantity_btc']),research_side(self.state))
        if action=='enter':
            snapshot=self.enter(model,snapshot)
        elif action=='exit':
            snapshot=self.close(snapshot)
        elif action=='hold':
            snapshot=self.maintain(model,snapshot)
            snapshot=self.top_up(model,snapshot)
        return action,snapshot

    def top_up(self, model, snapshot):
        """Within the entry's own session, IOC-add toward the committed campaign size.

        Margin is added before the order so the enlarged isolated position still
        liquidates beyond the unchanged close-all stop. IOC leaves no remainder.
        """
        fill = self.state.get('entry_fill')
        protection = self.state.get('position_protection')
        if (not fill or self.session is None or fill.get('session') != self.session or not protection
                or fill.get('campaign') != protection.get('campaign') or model.active is None
                or model.active.identity != fill['campaign'] or not self.may_enter()):
            return snapshot
        if (self.state.pending() or snapshot['possible_entry_remainders'] or snapshot['open_orders']
                or not self.planned_protection(snapshot)):
            return snapshot
        if abs(number(snapshot['quantity_btc'])) >= number(fill['requested']):
            return snapshot
        try:
            plan = topup_preview(self.reader, model, snapshot, fill['requested'],
                                 protection['stop'], protection['take'])
        except ValueError:
            return snapshot
        self.entry_constraint = plan['constraint']
        if not number(plan['quantity_btc']):
            return snapshot
        fresh = self.snapshot()
        if (any(fresh[k] != snapshot[k] for k in ('quantity_btc','wallet_usdt','possible_entry_remainders'))
                or fresh['open_orders'] or not self.planned_protection(fresh)):
            raise Unknown('account changed between top-up sizing and order')
        if abs(int(self.reader.clock()*1000)-plan['observed_at']) > 15000:
            raise Unknown('top-up preflight expired')
        self.reader.ensure_capacity(400)
        if not self.may_enter():
            raise Blocked('session deadline or stop request prohibits a new entry')
        self.reader.deadline=self.reader.monotonic()+120
        epoch = self.epoch()
        # The venue moves the add's initial margin into the isolated wallet on fill.
        target = (number(plan['allocated_margin_usdt'])
                  - number(plan['quantity_btc'])*number(plan['entry_estimate'])/20)
        if number(fresh['isolated_wallet_usdt']) < target:
            fresh = safety.add_margin(self.reader,self.state,self.send,self.uid,epoch,
                                      target,authorized=self.authorized)
        identity = client_id(self.state.identity,epoch,'entry')
        payload = dict(symbol='BTCUSDT',positionSide='BOTH',side=plan['side'],type='LIMIT',
                       timeInForce='IOC',quantity=plan['quantity_btc'],
                       price=plan['entry_estimate'],newClientOrderId=identity,newOrderRespType='RESULT')
        self.state.prepare(identity,'binance_order',payload,campaign=fill['campaign'],position_snapshot=fresh)
        try:
            self.send('POST','/fapi/v1/order',payload)
        except Exception:
            pass  # query, never resend an uncertain write
        snapshot = self.settle()
        return self.recover_exposure(snapshot)

    def finish(self):
        snapshot=self.recover_exposure(self.settle())
        if number(snapshot['quantity_btc']) and not self.planned_protection(snapshot):
            raise Unknown('session ended without confirmed exchange-hosted protection')
        return snapshot
