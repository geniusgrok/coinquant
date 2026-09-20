"""Bounded reconcile/decide/execute/verify lifecycle, without an exit canceller."""
from dataclasses import replace
from decimal import ROUND_CEILING

from .bybit import TERMINAL
from . import pending
from .model import decide, protected, repair_target, validate_risk_increase
from .state import State, client_id
from .types import D, INTERVAL_MS, ZERO, Blocked, Unknown, Target, floor_step, number, serial


def _coverage(snapshot) -> bool:
    """Position price fields alone are NOT evidence of exchange-hosted orders."""
    p = snapshot.position
    if not p.quantity:
        return True
    if abs(p.quantity) > snapshot.rules.maximum or not protected(snapshot):
        return False
    side = 'Sell' if p.quantity > 0 else 'Buy'
    for kind, price in (('TakeProfit', p.take_profit), ('StopLoss', p.stop_loss)):
        matches = [o for o in snapshot.orders if
                   o.get('stopOrderType') == kind and o.get('orderStatus') == 'Untriggered'
                   and o.get('side') == side and o.get('positionIdx') == 0
                   and o.get('orderType') == 'Market' and o.get('tpslMode') == 'Full'
                   and o.get('closeOnTrigger') is True and o.get('triggerBy') == 'MarkPrice'
                   and number(o.get('triggerPrice')) == price
                   and (number(o.get('qty')) == 0 or number(o.get('qty')) >= abs(p.quantity))]
        if len(matches) != 1:
            return False
    return True


def coverage(snapshot) -> bool:
    try:
        return _coverage(snapshot)
    except (Blocked, ValueError, TypeError, KeyError, ArithmeticError):
        return False


def entry_orders(snapshot):
    return [o for o in snapshot.orders if o.get('reduceOnly') is not True
            and o.get('closeOnTrigger') is not True]


def close_target(snapshot, config, candle=-1):
    p = snapshot.position
    price = snapshot.bid * (1 - config.model.slippage_fraction) if p.quantity > 0 else snapshot.ask * (1 + config.model.slippage_fraction)
    tick = snapshot.rules.tick
    price = floor_step(price, tick) if p.quantity > 0 else (price / tick).to_integral_value(rounding=ROUND_CEILING) * tick
    return Target(candle, ZERO, price, ZERO, ZERO, ZERO, ZERO, ZERO, 'reduce-only risk removal')


class Execution:
    def __init__(self, venue, state, config, report):
        self.venue, self.state, self.config, self.report = venue, state, config, report
        self.last_snapshot = None
        self.observation_current = False
        self.write_attempted = False

    def observe(self):
        # An observation is not current while a newer read is incomplete.
        self.observation_current = False
        observed = self.venue.snapshot()
        observed.validate()
        self.last_snapshot = observed
        self.observation_current = True
        return observed

    def before_write(self):
        # Invalidate BEFORE sending, including writes with lost acknowledgments.
        self.observation_current = False
        self.write_attempted = True

    def recover(self, snapshot):
        changed = False
        for intent in self.state.pending():
            payload, kind = intent['payload'], intent['kind']
            if kind in ('entry', 'amend'):
                snapshot = pending.reconcile(self, intent)
                changed = True
            elif kind in ('order', 'cancel'):
                order = self.venue.lookup(payload['link'])
                if order and order.get('orderStatus') in TERMINAL:
                    self.state.finish(intent['id'], 'confirmed', {'order': order})
                    changed = True
                    self.report['actions'].append({'operation': 'reconcile', 'id': intent['id'], 'outcome': order['orderStatus']})
            elif kind == 'protect':
                p = snapshot.position
                if (not p.quantity or (coverage(snapshot) and p.take_profit == number(payload['tp']) and p.stop_loss == number(payload['sl']))):
                    self.state.finish(intent['id'], 'confirmed', {'position': serial(p)})
        # A fill observed during lookup invalidates the earlier position size.
        return self.observe() if changed else snapshot
        # Unknown absence remains pending, including a crash before send.

    def cancel(self, link):
        identity = client_id(self.state.identity, 0, 'cancel:' + link)
        known = self.venue.lookup(link)
        if known and known.get('orderStatus') in TERMINAL:
            return
        if any(i['id'] == identity for i in self.state.pending()):
            raise Unknown('previous cancellation remains unknown; no resend')
        self.state.prepare(identity, 'cancel', {'link': link})
        self.before_write()
        try:
            self.venue.cancel(link)
        except (Unknown, Blocked):
            pass
        observed = self.venue.lookup(link)
        if not observed or observed.get('orderStatus') not in TERMINAL:
            raise Unknown('entry cancellation has not been confirmed')
        self.state.finish(identity, 'confirmed', {'order': observed})
        self.report['actions'].append({'operation': 'cancel', 'id': link, 'outcome': observed['orderStatus']})

    def clean_entries(self, snapshot, *, keep_pending=False):
        if (keep_pending and not self.state.pending() and not self.state.get('native_fok_violation')
                and pending.working(snapshot, self.config.max_position_usd)):
            return snapshot
        for order in entry_orders(snapshot):
            link = order.get('orderLinkId', '')
            if not link.startswith('pq-'):
                raise Blocked('unowned BTC entry remains; it was not altered')
            self.cancel(link)
        return self.observe() if entry_orders(snapshot) else snapshot

    def protect(self, snapshot, target):
        if not snapshot.position.quantity:
            return snapshot
        if target.quantity * snapshot.position.quantity <= 0:
            target = repair_target(snapshot, self.config.model, target.candle)
        if not protected(snapshot, target.take_profit, target.stop_loss):
            target = repair_target(snapshot, self.config.model, target.candle)
        if (coverage(snapshot) and snapshot.position.take_profit == target.take_profit
                and snapshot.position.stop_loss == target.stop_loss):
            return snapshot
        identity = client_id(self.state.identity, snapshot.time,
                             f'protect:{target.take_profit}:{target.stop_loss}')
        if any(i['kind'] == 'protect' for i in self.state.pending()):
            raise Unknown('previous protection replacement remains unknown')
        self.state.prepare(identity, 'protect', {'tp': target.take_profit, 'sl': target.stop_loss})
        self.before_write()
        try:
            self.venue.protect(target)  # native amendment of BOTH sides; never cancel old first
        except (Unknown, Blocked):
            pass
        observed = self.observe()
        if observed.position.quantity:
            if not coverage(observed) or observed.position.take_profit != target.take_profit or observed.position.stop_loss != target.stop_loss:
                raise Unknown('full native protection was not confirmed')
        self.state.finish(identity, 'confirmed', {'position': serial(observed.position)})
        self.report['actions'].append({'operation': 'protect', 'outcome': 'readback_confirmed',
                                       'tp': target.take_profit, 'sl': target.stop_loss})
        return observed

    def trade(self, snapshot, target, delta, operation, *, reduce_only=False):
        if not delta:
            return snapshot
        rules, p = snapshot.rules, snapshot.position
        if abs(delta) % rules.step or abs(delta) < rules.minimum or abs(delta) > rules.maximum:
            raise Blocked('delta violates native quantity constraints')
        if reduce_only:
            if delta * p.quantity >= 0 or abs(delta) > abs(p.quantity):
                raise Blocked('invalid reduce-only delta')
        else:
            if abs(target.quantity) > self.config.max_position_usd or abs(target.quantity) > rules.maximum:
                raise Blocked('target exceeds authorized or full-market-exit capacity')
            if p.quantity and not coverage(snapshot):
                raise Blocked('cannot add risk before full protection is verified')
            if self.state.get('native_fok_violation'):
                raise Blocked('native entry safety contract failed; no new exposure')
            if self.state.pending() or entry_orders(snapshot):
                raise Unknown('unresolved intent or entry blocks additional risk')
        link = client_id(self.state.identity, target.candle, operation)
        prior = self.venue.lookup(link)  # survives loss of all local files
        if prior:
            self.report['actions'].append({'operation': 'reconcile_existing', 'id': link,
                                           'outcome': prior.get('orderStatus', 'unknown')})
            if prior.get('orderStatus') not in TERMINAL:
                self.cancel(link)
            return self.observe()
        if not reduce_only:
            validate_risk_increase(snapshot, target, self.config.model,
                                   notional_limit=self.config.max_position_usd)
        self.state.prepare(link, 'order', {'link': link, 'delta': delta, 'reduce_only': reduce_only})
        self.before_write()
        try:
            self.venue.place(link, delta, target, reduce_only=reduce_only)
        except (Unknown, Blocked):
            pass
        observed = self.venue.lookup(link)
        if not observed:
            raise Unknown('order result unknown; client identifier was not found, not retried')
        if observed.get('orderStatus') not in TERMINAL:
            self.state.finish(link, 'partial', {'order': observed})
            self.cancel(link)  # bounded IOC/GTC remainder confirmation; no offline entry
            observed = self.venue.lookup(link)
        if not observed or observed.get('orderStatus') not in TERMINAL:
            raise Unknown('order is not terminal after bounded reconciliation')
        filled = number(observed['cumExecQty'])
        if filled < 0 or filled > abs(delta):
            raise Unknown('exchange fill quantity is inconsistent')
        self.state.finish(link, 'confirmed', {'order': observed})
        self.report['actions'].append({'operation': 'reduce' if reduce_only else 'increase',
                                       'id': link, 'requested': abs(delta), 'filled': filled,
                                       'outcome': observed['orderStatus']})
        if filled != abs(delta):
            self.report['partial'] = True
        return self.observe()

    def target(self, snapshot, target, bars):
        existing = pending.working(snapshot, self.config.max_position_usd)
        if existing and (not target.trigger_price or
                         (existing['side'] == 'Buy') != (target.quantity > 0)):
            self.cancel(existing['orderLinkId'])
            snapshot = self.observe()
            target = decide(bars, snapshot, self.config.model,
                            notional_limit=self.config.max_position_usd)
        p = snapshot.position
        if p.quantity and (not target.quantity or p.quantity * target.quantity < 0):
            reduction = close_target(snapshot, self.config, target.candle)
            delta = -p.quantity
            if abs(delta) > snapshot.rules.maximum:
                delta = (-1 if p.quantity > 0 else 1) * snapshot.rules.maximum
            snapshot = self.trade(snapshot, reduction, delta, 'close', reduce_only=True)
            if snapshot.position.quantity:
                self.report['partial'] = True
                return snapshot
            target = decide(bars, snapshot, self.config.model, notional_limit=self.config.max_position_usd)  # actual equity after closing
        if target.trigger_price:
            snapshot = pending.apply(self, snapshot, target)
            if snapshot.position.quantity and not coverage(snapshot):
                snapshot = self.protect(snapshot, repair_target(snapshot, self.config.model, target.candle))
            self.report['target'] = serial(target)
            return snapshot
        delta = target.quantity - snapshot.position.quantity
        if delta:
            reduction = snapshot.position.quantity * delta < 0
            order_target = replace(target, entry=close_target(snapshot, self.config, target.candle).entry) if reduction else target
            snapshot = self.trade(snapshot, order_target, delta,
                                  'decrease' if reduction else 'increase', reduce_only=reduction)
        if snapshot.position.quantity:
            snapshot = self.protect(snapshot, target)
        self.report['target'] = serial(target)
        return snapshot


def _recover_safety(engine, config, report):
    """One bounded fresh reconciliation, then protection or reduce-only removal."""
    fresh = engine.observe()
    # An unresolved parent/cancellation must block new exposure, not prevent
    # repairing the protection of a separately observed existing position.
    for reconcile in (engine.clean_entries, engine.recover):
        try:
            fresh = reconcile(fresh)
        except (Blocked, Unknown) as exc:
            report.setdefault('recovery_issues', []).append(str(exc))
            fresh = engine.observe()
    if fresh.position.quantity and not coverage(fresh):
        # An unknown prior protection amendment must not be duplicated. If its
        # outcome cannot be verified, only reduction of the real position is safe.
        pending_protect = any(i['kind'] == 'protect' for i in engine.state.pending())
        if not pending_protect:
            try:
                fresh = engine.protect(fresh, repair_target(fresh, config.model))
            except (Blocked, Unknown):
                fresh = engine.observe()
        if fresh.position.quantity and not coverage(fresh):
            removal = close_target(fresh, config, fresh.time // INTERVAL_MS * INTERVAL_MS)
            qty = min(abs(fresh.position.quantity), fresh.rules.maximum)
            fresh = engine.trade(fresh, removal, -qty if fresh.position.quantity > 0 else qty,
                                 'emergency-close', reduce_only=True)
    report['emergency'] = ('flat_verified' if not fresh.position.quantity else
                           'protected_verified' if coverage(fresh) else 'partial_or_unprotected')


def _observation_report(engine, report):
    current, last = engine.observation_current, engine.last_snapshot
    report.update(actual=None, account_observation_current=current,
                  offline_safe_at_observation=False, protection_verified_at_observation=False)
    if last is None:
        return
    if not current:
        # Historical data is useful for recovery but must never look like actual
        # position or proof that a post-write account is flat/protected.
        report['last_observed'] = serial(last)
        return
    report['actual'] = serial(last)
    report['protection_verified_at_observation'] = coverage(last)
    parent = pending.working(last, engine.config.max_position_usd)
    report['hosted_entry_contract_verified_at_observation'] = parent is not None
    report['offline_safe_at_observation'] = (coverage(last) and (not entry_orders(last) or parent is not None)
                                              and not engine.state.pending()
                                              and not engine.state.get('native_fok_violation'))
    report['position_btc_at_mark'] = str(abs(last.position.quantity) / last.mark)
    report['effective_derivative_leverage'] = str(abs(last.position.quantity) / last.equity_usd)
    # Fiat delta of the BTC wallet AND inverse position, not just derivative notional.
    delta_btc = last.wallet_btc
    if last.position.quantity:
        delta_btc += last.position.quantity / last.position.entry
    report['net_btc_delta'] = str(delta_btc)
    report['effective_fiat_delta_leverage'] = str(delta_btc * last.mark / last.equity_usd)


def run_once(venue, config, *, execute=False):
    uid = venue.identity()
    report = {'status': 'read_only', 'environment': config.environment, 'account_uid': uid,
              'actions': [], 'partial': False,
              'limitations': ['Only flat-account native conditional FOK parents may remain; native integration is not yet qualified',
                              'BTC collateral retains fiat price risk when the derivative is flat',
                              'native testnet and live execution are not yet integration-qualified']}
    with State(config.state_dir, f'{config.environment}:{uid}') as state:
        engine = Execution(venue, state, config, report)
        account_verified = False
        try:
            if execute:
                config.authorize(uid, True)
            snapshot = engine.observe()
            account_verified = True
            if execute:
                snapshot = engine.recover(snapshot)
                if snapshot.position.quantity and not coverage(snapshot):
                    snapshot = engine.protect(snapshot, repair_target(snapshot, config.model))
                snapshot = engine.clean_entries(snapshot, keep_pending=True)
                if snapshot.position.quantity and not coverage(snapshot):
                    snapshot = engine.protect(snapshot, repair_target(snapshot, config.model))
            bars = venue.candles(snapshot.time)
            target = decide(bars, snapshot, config.model, notional_limit=config.max_position_usd if config.max_position_usd > 0 else None)
            report['target'], report['market_time'] = serial(target), snapshot.time
            if execute:
                if state.pending():
                    raise Unknown('unresolved prior operation blocks strategy execution')
                if state.get('last_candle') == target.candle:
                    report['status'] = 'no_action'
                else:
                    if not snapshot.position.quantity and any(
                        o.get('stopOrderType') in ('TakeProfit', 'StopLoss') for o in snapshot.orders
                    ):
                        raise Blocked('orphan protection on flat account requires reconciliation before entry')
                    state.set('last_candle', target.candle)
                    engine.target(snapshot, target, bars)
                    report['status'] = 'partial' if report['partial'] else 'executed'
                snapshot = engine.clean_entries(engine.observe(), keep_pending=True)
                if not coverage(snapshot):
                    raise Unknown('final full-position protection is not verified')
        except (Blocked, Unknown) as exc:
            report['status'] = 'unknown' if isinstance(exc, Unknown) else 'blocked'
            report['reason'] = str(exc)
            last = engine.last_snapshot
            needs_recovery = engine.write_attempted or (last is not None and not coverage(last))
            # An incompatible account/mode was NEVER accepted for writes. An
            # engineering invocation must not opportunistically flatten it.
            if execute and account_verified and needs_recovery:
                try:
                    _recover_safety(engine, config, report)
                except (Blocked, Unknown) as recovery_error:
                    report['emergency'] = 'unknown: ' + str(recovery_error)
        if execute and report['status'] in ('executed', 'no_action'):
            changed = any(a['operation'] in ('increase', 'reduce', 'protect', 'cancel', 'place_entry', 'amend_entry')
                          for a in report['actions'])
            report['status'] = 'executed' if changed else 'no_action'
        _observation_report(engine, report)
        report['pending_intents'] = state.pending()
        state.report(report)
    return serial(report)
