"""Owned BTC lifecycle decisions; proposals and attribution, never wallet proof.

The fixed two mechanisms use actual settled ownership and completed prices. A
request, current mark high, residual position or hypothetical trade cannot create
economic campaign memory. The same small implementation is shared by both repos.
"""
from bisect import bisect_left, bisect_right
from contextlib import contextmanager
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

DAY = 86400000
SPEC = Path(__file__).with_name('lifecycle-spec.json')
POLICIES = ('debt-half', 'debt-two-loss', 'giveback-half', 'giveback-full')


def serial(value):
    if isinstance(value, D):
        return str(value)
    if isinstance(value, dict):
        return {str(k): serial(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serial(v) for v in value]
    return value


def digest(value):
    return hashlib.sha256(json.dumps(serial(value), sort_keys=True).encode()).hexdigest()


class DebtMemory:
    """One account's causal settled-campaign state; price history proves no fills."""
    def __init__(self, saved=None):
        saved = saved or dict(losses=0, barrier=None, settled=[], last_close_ms=None)
        self.losses = saved['losses']
        self.barrier = None if saved['barrier'] is None else D(saved['barrier'])
        self.settled = set(saved['settled'])
        self.last_close_ms = saved['last_close_ms']
        if (type(self.losses) is not int or self.losses < 0 or
                self.barrier is not None and (not self.barrier.is_finite() or self.barrier <= 0) or
                self.last_close_ms is not None and type(self.last_close_ms) is not int):
            raise ValueError('invalid campaign debt checkpoint')

    def checkpoint(self):
        return serial(dict(losses=self.losses, barrier=self.barrier,
                           settled=sorted(self.settled), last_close_ms=self.last_close_ms))

    def close(self, completed_ms, close):
        close = D(close)
        if (type(completed_ms) is not int or completed_ms % DAY not in (0, 60000) or
                not close.is_finite() or close <= 0):
            raise ValueError('invalid completed close')
        if self.last_close_ms is not None and completed_ms <= self.last_close_ms:
            raise ValueError('completed close chronology')
        self.last_close_ms = completed_ms
        if self.barrier is not None and close > self.barrier:
            self.losses, self.barrier = 0, None

    def settle(self, campaign, observed_ms):
        identity = str(campaign['id'])
        if identity in self.settled:
            return
        gain, peak = D(campaign['gain']), D(campaign['owned_close_peak'])
        if (campaign.get('fully_closed') is not True or campaign['end_ms'] > observed_ms or
                not gain.is_finite() or not peak.is_finite() or peak <= 0):
            raise ValueError('only confirmed fully settled campaigns create debt')
        self.settled.add(identity)
        if gain < 0:
            self.losses += 1
            self.barrier = max(self.barrier or peak, peak)
        else:
            self.losses, self.barrier = 0, None

    def factor(self, policy):
        if policy == 'debt-half':
            return D('.5') if self.losses else D(1)
        if policy == 'debt-two-loss':
            return D(0) if self.losses >= 2 else D(1)
        raise ValueError('unregistered debt expression')


def giveback_proposal(policy, *, offline, now_ms, fill_ms, entry, initial_stop,
                      stop_received_ms, completed_closes, owned_btc, pending=False):
    """Full/half reduce proposal from qualified owned R; no order submission."""
    if policy not in ('giveback-half', 'giveback-full') or offline is not True:
        raise ValueError('registered offline lifecycle proposal required')
    if initial_stop is None or stop_received_ms is None:
        return dict(status='BLOCKED_INPUT', reason='initial installed-stop receipt missing', orders=0)
    entry, stop, quantity = D(entry), D(initial_stop), D(owned_btc)
    if (type(now_ms) is not int or type(fill_ms) is not int or type(stop_received_ms) is not int or
            not fill_ms <= stop_received_ms <= now_ms or pending or
            not all(v.is_finite() for v in (entry, stop, quantity)) or
            not 0 < stop < entry or quantity <= 0):
        return dict(status='BLOCKED_INPUT', reason='ownership/protection/clock unqualified', orders=0)
    rows = [(int(t), D(p)) for t, p in completed_closes]
    if (any(t % DAY or t <= fill_ms or t > now_ms or not p.is_finite() or p <= 0 for t, p in rows) or
            any(a[0] >= b[0] for a, b in zip(rows, rows[1:]))):
        raise ValueError('causal owned completed closes required')
    # A day that began before this fill is omitted, including its unknown high.
    rows = [(t, p) for t, p in rows if t-DAY >= fill_ms]
    if len(rows) < 2:
        return dict(status='NO_EVENT', reason='two completed owned days required', orders=0)
    peak, last = max(p for _, p in rows), rows[-1][1]
    earned = peak-entry
    eligible = earned >= entry-stop and entry <= last <= entry+earned/2
    amount = quantity*(D('.5') if policy == 'giveback-half' else D(1)) if eligible else D(0)
    return serial(dict(status='REDUCE_PROPOSAL' if eligible else 'NO_EVENT', owned_btc=quantity,
                       reduce_btc=amount, initial_risk=entry-stop, owned_close_peak=peak,
                       last_completed_close=last, completed_ms=rows[-1][0], orders=0,
                       account_entrant=False, native_qualified=False))


def peak_owned(bars, begin, end, entry):
    return max([D(entry), *[p for t, p in bars if t//DAY*DAY-DAY >= begin and t <= end]])


def coin_campaigns(ledger, bars):
    """Exact full-flat groups from actual owned long fills and actual income."""
    writes = {e['identity']: e for e in ledger['opportunity_ledger']
              if e['event'] == 'write_attempt' and e['method'] == 'POST'
              and e['payload'].get('side') == 'BUY'}
    fills = {e['trade']['id']: e for e in ledger['opportunity_ledger'] if e['event'] == 'fill'}
    quantity, current, rows = D(0), None, []
    for trade in sorted(ledger['trades'], key=lambda t: (t['time'], t['id'])):
        amount, price = D(trade['qty']), D(trade['price'])
        if trade['side'] == 'BUY':
            write = writes[fills[trade['id']]['client_order_id']]
            identity = str(write['opportunity'])
            if not quantity:
                current = dict(id=identity, time_ms=trade['time'], decision_ms=write['at_ms'],
                               notional=D(0), buy_btc=D(0), sell_quote=D(0), fully_closed=False)
                rows.append(current)
            if current['id'] != identity:
                raise ValueError('overlapping Coin campaigns')
            current['notional'] += amount*price
            current['buy_btc'] += amount
            quantity += amount
        else:
            if current is None or amount > quantity:
                raise ValueError('unowned Coin sale')
            quantity -= amount
            current['sell_quote'] += amount*price
            if not quantity:
                current.update(fully_closed=True, end_ms=trade['time'])
    for row in rows:
        if not row['fully_closed']:
            continue
        income = [v for v in ledger['funding_ledger'] if row['time_ms'] <= v['time'] <= row['end_ms']]
        realized = sum((D(v['income']) for v in income if v['incomeType'] == 'REALIZED_PNL'), D(0))
        if abs(realized-(row['sell_quote']-row['notional'])) > D('.01'):
            raise ValueError('Coin realized cash disagrees with owned fills')
        row['gain'] = sum((D(v['income']) for v in income), D(0))
        row['owned_close_peak'] = peak_owned(bars, row['time_ms'], row['end_ms'], row['notional']/row['buy_btc'])
    return rows


def spot_campaigns(ledger, bars):
    """Reuse accepted sleeve-aware FIFO; unsold BTC dust remains censored."""
    from research.persistent_routes import owned_spot
    metadata = {e['id']: e for e in ledger['opportunity_ledger'] if e['event'] == 'fill'}
    rows = []
    for lot in owned_spot(ledger):
        row = dict(id=str(lot['id']), time_ms=lot['time_ms'],
                   decision_ms=metadata[lot['meta']['id']]['decision_ms'], notional=lot['notional'],
                   fully_closed=lot['left'] <= D('1e-20'))
        if row['fully_closed']:
            row['end_ms'] = max(s['time_ms'] for s in lot['settlements'])
            row['gain'] = sum((s['proceeds'] for s in lot['settlements']), D(0))-lot['notional']
            row['owned_close_peak'] = peak_owned(bars, row['time_ms'], row['end_ms'], lot['price'])
        rows.append(row)
    return rows


def debt_screen(campaigns, bars, cutoff):
    """Frozen realized-basket attribution; suppressed fills are not new accounts."""
    closed = [c for c in campaigns if c['fully_closed']]
    output = {}
    for policy in ('debt-half', 'debt-two-loss'):
        memory, changes = DebtMemory(), []
        timeline = [(t, 0, p) for t, p in bars]
        timeline += [(c['end_ms'], 1, c) for c in closed]
        timeline += [(c['decision_ms'], 2, c) for c in campaigns]
        for stamp, kind, event in sorted(timeline, key=lambda e: e[:2]):
            if kind == 0:
                memory.close(stamp, event)
            elif kind == 1:
                memory.settle(event, stamp)
            else:
                factor = memory.factor(policy)
                if factor < 1:
                    changes.append(dict(id=event['id'], decision_ms=stamp, factor=factor,
                        preceding_losses=memory.losses, causal_barrier=memory.barrier,
                        fully_closed=event['fully_closed'],
                        avoided_cash=-(1-factor)*event['gain'] if event['fully_closed'] else None))
        eras = {}
        for name, early in (('early', True), ('late', False)):
            changed = [c for c in changes if c['fully_closed'] and (c['decision_ms'] < cutoff) == early]
            control = [c for c in closed if (c['decision_ms'] < cutoff) == early]
            avoided = sum((c['avoided_cash'] for c in changed), D(0))
            uniform = -sum((c['gain']/2 for c in control), D(0))
            eras[name] = dict(changed_closed=len(changed), avoided_cash=avoided,
                              fixed_half_entry_avoided_cash=uniform)
        enough = sum(e['changed_closed'] for e in eras.values()) >= 10 and all(e['changed_closed'] >= 3 for e in eras.values())
        alpha = enough and all(e['avoided_cash'] > 0 and e['avoided_cash'] > e['fixed_half_entry_avoided_cash'] for e in eras.values())
        output[policy] = serial(dict(status='ACCOUNT_ENTRANT' if alpha else 'SUPPORT_PENDING' if not enough else 'REJECT_MECHANISM',
            eras=eras, changes=changes, fully_settled_cohorts=len(closed), censored_cohorts=len(campaigns)-len(closed),
            counterfactual_wallet=False, prospective_alpha_proven=False))
    return output


def spot_initial_stops(ledger, client_events):
    """Join actual accepted native order ID to its original receipt UTC clock."""
    calls = {e['client_id']: e for e in client_events if e['method'] == 'POST'}
    accepted = []
    for client, raw, status, response in ledger['allocations']:
        owner, reply = json.loads(raw), json.loads(response)
        if owner['order'].get('type') != 'STOP_LOSS':
            continue
        call = calls.get(client)
        if (call and status == 'settled' and reply.get('orderId') is not None and
                reply.get('status') in ('NEW', 'PARTIALLY_FILLED', 'FILLED', 'CANCELED', 'EXPIRED') and
                call['order'] == owner['order']):
            accepted.append(dict(owner=owner, reply=reply, received_ms=call['received_ms'],
                                 sent_ms=call['sent_ms'], client_id=client))
    result = {}
    from research.persistent_routes import owned_spot
    for lot in owned_spot(ledger):
        stops = [r for r in accepted if r['owner']['signal_ms'] == lot['owner']['signal_ms'] and
                 set(r['owner']['sleeves']) == set(lot['owner']['sleeves']) and
                 lot['time_ms'] <= r['sent_ms'] <= r['received_ms']]
        if stops:
            receipt = min(stops, key=lambda r: r['received_ms'])
            result[str(lot['id'])] = dict(initial_stop=D(receipt['owner']['order']['stopPrice']),
                stop_received_ms=receipt['received_ms'], stop_client_id=receipt['client_id'],
                stop_native_order_id=receipt['reply']['orderId'])
    return result


def giveback_spot_screen(ledger, packet, stops, cutoff):
    """Qualified installed-R event screen at original held decisions only."""
    from research.persistent_routes import owned_spot
    bars = [(int(t)+DAY+60000, D(v['close'])) for t,v in
            sorted(packet['bars'].items(), key=lambda item:int(item[0]))]
    lows = [(int(t), D(v['low'])) for t,v in packet['bars'].items()]
    decisions = [e for e in ledger['opportunity_ledger'] if e['event'] == 'decision']
    decision_times = [e['decision_ms'] for e in decisions]
    picked, controls, missing = [], [], []
    for lot in owned_spot(ledger):
        receipt = stops.get(str(lot['id']))
        if not receipt:
            missing.append(str(lot['id']))
            continue
        first_control, first_event = None, None
        weights = {int(w):D(v) for w,v in lot['owner']['weights'].items()}
        total = sum(weights.values(), D(0))
        considered = set()
        terminal = max((s['time_ms'] for s in lot['settlements']), default=bars[-1][0])
        left = bisect_left(decision_times, receipt['stop_received_ms'])
        right = bisect_right(decision_times, terminal) if lot['left'] <= D('1e-20') else len(decisions)
        for decision in decisions[left:right]:
            at = decision['decision_ms']
            if at <= receipt['stop_received_ms'] or at//DAY in considered:
                continue
            owned = [r for r in bars if r[0]-60000-DAY >= lot['time_ms'] and r[0] <= at]
            if len(owned) < 2:
                continue
            quantities = {}
            for w,weight in weights.items():
                left = lot['quantity']*weight/total-sum(s['quantity'] for s in lot['settlements']
                    if s['sleeve'] == w and s['time_ms'] <= at)
                if left >= D('.00001') and decision['sleeves'][str(w)]['action'] == 'hold':
                    quantities[w] = left
            if not quantities:
                continue
            considered.add(at//DAY)
            # Completed close is a fixed quote proxy; no recorded execution claim.
            mark = owned[-1][1]
            quantity = sum(quantities.values(), D(0))
            future = [s for s in lot['settlements'] if s['time_ms'] > at and s['sleeve'] in quantities]
            by_sleeve = {w:sum((s['quantity'] for s in future if s['sleeve'] == w), D(0)) for w in quantities}
            closed = all(abs(by_sleeve[w]-q) <= D('1e-20') for w,q in quantities.items())
            proceeds = sum((s['proceeds'] for s in future), D(0))
            removed_downside = D(0)
            if closed:
                for settlement in future:
                    later = [low for start,low in lows if start >= at and start+DAY+60000 <= settlement['time_ms']]
                    if later:
                        removed_downside += settlement['quantity']*max(D(0),mark-min(later))
            event = dict(id=str(lot['id']), time_ms=at, mark_proxy=mark, quantity=quantity,
                owned_close_peak=max(p for _,p in owned), closed=closed,
                avoided_cash=quantity*mark*D('.9995')*D('.999')-proceeds if closed else None,
                removed_downside_usdt=removed_downside, **receipt)
            if first_control is None:
                first_control = event
            earned = event['owned_close_peak']-lot['price']
            if earned >= lot['price']-receipt['initial_stop'] and lot['price'] <= mark <= lot['price']+earned/2:
                first_event = event
                break
        if first_control:
            controls.append(first_control)
        if first_event:
            picked.append(first_event)
    output = {}
    for policy, fraction in (('giveback-half',D('.5')), ('giveback-full',D(1))):
        eras = {}
        for name,early in (('early',True), ('late',False)):
            events = [e for e in picked if e['closed'] and (e['time_ms'] < cutoff) == early]
            uniform = [e for e in controls if e['closed'] and (e['time_ms'] < cutoff) == early]
            gain = fraction*sum((e['avoided_cash'] for e in events), D(0))
            risk = fraction*sum((e['removed_downside_usdt'] for e in events), D(0))
            control_gain = fraction*sum((e['avoided_cash'] for e in uniform), D(0))
            control_risk = fraction*sum((e['removed_downside_usdt'] for e in uniform), D(0))
            ratio = max(D(0),-gain)/risk if risk > 0 else None
            control_ratio = max(D(0),-control_gain)/control_risk if control_risk > 0 else None
            eras[name] = dict(changed_closed=len(events), avoided_cash=gain, removed_downside_usdt=risk,
                foregone_cash_per_removed_downside=ratio, unconditional_timing_avoided_cash=control_gain,
                unconditional_timing_downside=control_risk, unconditional_timing_ratio=control_ratio)
        enough = len([e for e in picked if e['closed']]) >= 10 and all(e['changed_closed'] >= 3 for e in eras.values())
        passes = enough and all(e['removed_downside_usdt'] > 0 and
            e['foregone_cash_per_removed_downside'] <= D('.50') and
            e['unconditional_timing_ratio'] is not None and
            e['foregone_cash_per_removed_downside'] < e['unconditional_timing_ratio'] for e in eras.values())
        output[policy] = serial(dict(status='RISK_ACCOUNT_ENTRANT' if passes else 'SUPPORT_PENDING' if not enough else 'REJECT_MECHANISM',
            eras=eras, selected_events=picked, timing_controls=controls, missing_initial_stop_cohorts=missing,
            initial_stop_qualified_cohorts=len(stops), counterfactual_wallet=False, prospective_alpha_proven=False))
    return output


def update_debt(saved, campaigns, bars, now):
    memory = DebtMemory(saved)
    newly_settled = [c for c in campaigns if c['fully_closed'] and str(c['id']) not in memory.settled]
    # A delayed native confirmation may predate the cached last close. Replay
    # only this small account's immutable economic events, never a wallet path.
    if memory.last_close_ms is not None and any(c['end_ms'] <= memory.last_close_ms for c in newly_settled):
        memory = DebtMemory()
    events = [(t, 0, p) for t, p in bars if t <= now and
              (memory.last_close_ms is None or t > memory.last_close_ms)]
    events += [(c['end_ms'], 1, c) for c in campaigns if c['fully_closed'] and
               str(c['id']) not in memory.settled and c['end_ms'] <= now]
    for stamp, kind, value in sorted(events, key=lambda e: e[:2]):
        memory.close(stamp, value) if kind == 0 else memory.settle(value, now)
    return memory


@contextmanager
def _configured_coin(policy, *, bars, binding, journal=None):
    """Debt gate around the original offline Lifecycle; guards before recovery.

    Uses actual venue fills/income and durable campaign ownership. No held add
    calls entry_fraction with a debt multiplier. An order adapter is refused.
    """
    if policy not in ('debt-half', 'debt-two-loss'):
        raise ValueError('only supported debt policies have a Coin runtime hook')
    from coinquant import campaign, session
    from coinquant.lifecycle import Lifecycle
    from coinquant.types import Blocked
    identity = dict(policy=policy, spec_sha256=hashlib.sha256(SPEC.read_bytes()).hexdigest(),
                    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), binding=binding)
    base_guard, base_decide, base_fraction = session._guard_strategy, Lifecycle.decide, campaign.Campaign.entry_fraction
    journal = journal if journal is not None else []
    def guard(state):
        stored = state.get('lifecycle_identity')
        if stored != identity and (stored is not None or state.get('linear_campaign') is not None or
                state.db.execute('SELECT 1 FROM intents LIMIT 1').fetchone()):
            raise Blocked('lifecycle account identity mismatch before recovery')
        if stored is None:
            state.set('lifecycle_identity', identity)
        return base_guard(state)
    def decide(engine, model, snapshot):
        venue = engine.reader
        if getattr(venue, 'offline', False) is not True:
            raise Blocked('lifecycle requires an offline confirmed-fill venue')
        links = dict(engine.state.get('settled_entry_campaigns') or {}, **(engine.state.get('entry_campaigns') or {}))
        order_clients = {v['orderId']: k for k, v in venue.orders.items()}
        writes, fills = [], []
        for trade in venue.trades:
            if trade['side'] != 'BUY':
                continue
            client = order_clients[trade['orderId']]
            owner = links.get(client)
            if owner is None:
                raise Blocked('actual fill has no durable campaign owner')
            writes.append(dict(event='write_attempt', method='POST', identity=client,
                opportunity=owner['campaign'], at_ms=trade['time'], payload=dict(side='BUY')))
            fills.append(dict(event='fill', trade=trade, client_order_id=client))
        owned = coin_campaigns(dict(trades=venue.trades, funding_ledger=venue.income,
                                    opportunity_ledger=writes+fills), bars)
        now = int(venue.clock()*1000)
        memory = update_debt(engine.state.get('lifecycle_debt'), owned, bars, now)
        engine.state.set('lifecycle_debt', memory.checkpoint())
        fresh = model.action(D(snapshot['quantity_btc'])) == 'enter'
        factor = memory.factor(policy) if fresh else D(1)
        journal.append(serial(dict(event='lifecycle-debt', at_ms=now, factor=factor,
                                   fresh_enter=fresh, memory=memory.checkpoint())))
        if fresh and factor == 0:
            return 'flat', snapshot
        # The scoped replacement lasts only this original fresh-entry decision.
        def fraction(selected, friction):
            return base_fraction(selected, friction)*(factor if selected is model else D(1))
        with patch.object(campaign.Campaign, 'entry_fraction', fraction):
            return base_decide(engine, model, snapshot)
    with patch.object(session, '_LIFECYCLE_IDENTITY', identity), patch.object(session, '_guard_strategy', guard), patch.object(Lifecycle, 'decide', decide):
        yield session


@contextmanager
def _configured_spot(policy, *, bars, binding, journal=None):
    """Resize original new BUY only; original ATR/crowding/protection survive."""
    if policy not in ('debt-half', 'debt-two-loss'):
        raise ValueError('only supported debt policies have a Spot runtime hook')
    from spotquant import session
    from spotquant.types import Blocked
    from research.alpha_spot import cached_fills
    from research.edge_spot import resize
    from spotquant.preview import BASE_STEP
    identity = dict(policy=policy, spec_sha256=hashlib.sha256(SPEC.read_bytes()).hexdigest(),
                    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), binding=binding)
    original_guard, original_portfolio = session._guard_state, session.portfolio
    journal = journal if journal is not None else []
    current = {}
    def guard(state):
        stored = state.get('lifecycle_identity')
        if stored != identity and (stored is not None or state.get('models') is not None or
                state.db.execute('SELECT 1 FROM intents LIMIT 1').fetchone()):
            raise Blocked('lifecycle account identity mismatch before recovery')
        if stored is None:
            state.set('lifecycle_identity', identity)
        current['state'] = state
        return original_guard(state)
    def portfolio(views, owned, snapshot, **kwargs):
        state = current['state']
        fills = cached_fills(state)
        rows = list(state.db.execute("SELECT id,payload,status,result FROM intents WHERE kind='p4'"))
        meta = [dict(f, event='fill', decision_ms=f['time']) for f in fills]
        campaigns = spot_campaigns(dict(fills=fills, allocations=rows, opportunity_ledger=meta), bars)
        # Current snapshot's UTC clock is supplied by the incumbent coordinator.
        now = kwargs['decision_ms']
        memory = update_debt(state.get('lifecycle_debt'), campaigns, bars, now)
        state.set('lifecycle_debt', memory.checkpoint())
        decision = original_portfolio(views, owned, snapshot, **kwargs)
        factor = memory.factor(policy)
        for order in list(decision['orders']):
            if order['side'] != 'BUY':
                continue
            # A filled held sleeve cannot receive a new risk expression here.
            def held(w):
                position = kwargs['positions'].get(w) or {}
                closed_dust = position.get('dust') is True and bool(position.get('sell_applied'))
                return D(owned[w]) >= BASE_STEP or (D(owned[w]) > 0 and not closed_dust)
            if any(held(w) for w in order['sleeves']):
                raise Blocked('campaign debt may not resize held-sleeve topup')
            before = D(order['quoteOrderQty'])
            after = resize(decision, order, before*factor)
            journal.append(serial(dict(event='lifecycle-debt-new-buy', at_ms=now, factor=factor,
                sleeves=order['sleeves'], original_quote=before, requested_quote=after,
                changed=before != after, memory=memory.checkpoint())))
        decision['order'] = decision['orders'][0] if decision['orders'] else None
        if not decision['orders']:
            decision['action'] = 'hold' if any(D(q) >= BASE_STEP for q in owned.values()) else 'flat'
        return decision
    with patch.object(session, '_LIFECYCLE_IDENTITY', identity), patch.object(session, '_guard_state', guard), patch.object(session, 'portfolio', portfolio):
        yield session


@contextmanager
def configured(policy, *, bars, binding, journal=None):
    """Root account producer supplies independent cold venue/state and packet."""
    kind = Path(__file__).resolve().parents[1].name
    context = _configured_coin if kind == 'coinquant' else _configured_spot
    with context(policy, bars=bars, binding=binding, journal=journal) as selected:
        def run(config, venue, **kwargs):
            if getattr(venue, 'offline', False) is not True:
                raise ValueError('lifecycle refuses account adapters before recovery')
            return selected.run(config, venue, **kwargs)
        yield SimpleNamespace(run=run)
