"""Fixed completed-day downside shocks through the original offline Lifecycle.

This changes held exposure only. Initial sizing, funding, owned-fill reconciliation,
native close-all protection and ordinary campaign consumption remain authoritative.
The half expression reduces dollar exposure; it makes no margin-buffer-ratio claim.
"""
from contextlib import contextmanager
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from coinquant.binance import market_quantity
from coinquant.ownership import TERMINAL, owned_observation
from coinquant.state import client_id
from coinquant.types import Blocked, Unknown, number

DAY = 86400000
POLICIES = ('downside-shock-half', 'downside-shock-exit')
STATE_KEY = 'held_downside_caps'
THRESHOLD = D('1.5')
PROTOCOL = dict(format='btc-held-downside-shock-v1', short_days=5,
    long_days=20, threshold=str(THRESHOLD), policies=list(POLICIES),
    statistic='sqrt(mean(min(completed_daily_return,0)^2))',
    trigger='short_rms > 1.5*long_rms; long window includes short window',
    overlap_ratio_upper_bound='2; strict threshold 2 could never trigger',
    cap='once per confirmed campaign; fixed half or zero of trigger quantity',
    unchanged='fresh sizing, consumed opportunities, costs, funding, ownership and protection')


def measure(returns, *, completed_through_ms, decision_ms):
    """Causal statistic only; a completed return does not establish ownership."""
    if (type(completed_through_ms) is not int or completed_through_ms % DAY
            or type(decision_ms) is not int or completed_through_ms > decision_ms):
        raise Blocked('held downside requires causally completed daily returns')
    values = [D(str(v)) for v in list(returns)[-20:]]
    if any(not v.is_finite() or v <= -1 for v in values):
        raise ValueError('finite completed returns greater than -1 required')
    row = dict(ready=len(values) == 20, observations=len(values),
               completed_through_ms=completed_through_ms, decision_ms=decision_ms,
               short_rms=D(0), long_rms=D(0), ratio=None, triggered=False)
    if not row['ready']:
        return row
    short_square = sum((min(v, D(0))**2 for v in values[-5:]), D(0))/5
    long_square = sum((min(v, D(0))**2 for v in values), D(0))/20
    row.update(short_rms=short_square.sqrt(), long_rms=long_square.sqrt(),
        ratio=(short_square/long_square).sqrt() if long_square else None,
        triggered=bool(long_square and short_square > THRESHOLD**2*long_square))
    return row


def _serial(row):
    if isinstance(row, D):
        return str(row)
    if isinstance(row, dict):
        return {k: _serial(v) for k, v in row.items()}
    if isinstance(row, (tuple, list)):
        return [_serial(v) for v in row]
    return row


def _caps(state, policy):
    saved = state.get(STATE_KEY)
    rows = {} if saved is None else saved
    if not isinstance(rows, dict):
        raise Blocked('invalid held downside checkpoint')
    for key, row in rows.items():
        try:
            initial, cap = number(row['initial_btc'], positive=True), number(row['cap_btc'])
            if (key != str(row['campaign']) or type(row['campaign']) is not int
                    or not row['campaign'] or row['policy'] != policy
                    or type(row['direction']) is not int or row['direction'] != 1
                    or cap != (initial/2 if policy == POLICIES[0] else D(0))
                    or type(row['triggered_ms']) is not int
                    or type(row['completed_through_ms']) is not int
                    or row['completed_through_ms'] % DAY
                    or row['completed_through_ms'] > row['triggered_ms']
                    or row['phase'] not in ('CAP_ACTIVE', 'CAP_SATISFIED', 'FLAT', 'ROUNDING_LIMIT')
                    or type(row['confirmed_orders']) is not int or row['confirmed_orders'] < 0):
                raise ValueError('cap fields')
            attempt = row['attempt']
            if attempt is not None and (type(attempt['epoch']) is not int
                    or not 0 < number(attempt['quantity']) <= number(attempt['before_btc']) <= initial
                    or type(attempt['prepared_ms']) is not int
                    or attempt['prepared_ms'] < row['triggered_ms']):
                raise ValueError('reduction attempt')
        except (KeyError, ValueError, TypeError, ArithmeticError) as exc:
            raise Blocked('invalid held downside checkpoint') from exc
    return rows


@contextmanager
def configured(policy, *, binding, journal=None):
    """Scoped actual offline session, with identity checks before recovery.

    The cap and each stable reduce identity are durable before a write. Unknown
    reductions cannot be counted as complete or sent under another identity.
    Ordinary recovery first establishes ownership and preserves hosted protection.
    """
    if policy not in POLICIES or not isinstance(binding, dict) or not binding:
        raise ValueError('registered held expression and immutable binding required')
    from coinquant import binance_safety as safety, session
    from coinquant.lifecycle import Lifecycle
    identity = json.loads(json.dumps(dict(family='held-downside-shock', policy=policy,
        protocol=PROTOCOL, source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        binding=binding), sort_keys=True))
    journal = journal if journal is not None else []
    base_guard, base_decide = session._guard_strategy, Lifecycle.decide
    base_recover, base_topup = Lifecycle.recover_exposure, Lifecycle.top_up
    base_rebalance, base_preview = Lifecycle.rebalance, session.preview

    def record(event, **values):
        journal.append(_serial(dict(event=event, policy=policy, **values)))

    def guard(state):
        stored = state.get('lifecycle_identity')
        if stored != identity and (stored is not None or state.get('linear_campaign') is not None
                or state.get('entry_plan') or state.get('entry_fill')
                or state.get('entry_campaigns') or state.get('position_protection')
                or state.get(STATE_KEY)
                or state.db.execute('SELECT 1 FROM intents LIMIT 1').fetchone()):
            raise Blocked('held downside identity mismatch before recovery')
        if stored is None:
            state.set('lifecycle_identity', identity)
        _caps(state, policy)
        return base_guard(state)

    def cap_for(engine, model):
        active = model.active
        return _caps(engine.state, policy).get(str(active.identity)) if active is not None else None

    def save(engine, row):
        rows = _caps(engine.state, policy)
        rows[str(row['campaign'])] = row
        values = {STATE_KEY: rows}
        fill = engine.state.get('entry_fill')
        if fill and fill.get('campaign') == row['campaign']:
            values['entry_fill'] = dict(fill, requested=str(min(number(fill['requested']),
                                                               number(row['cap_btc']))))
        engine.state.set_many(values)

    def acknowledge(engine, row, snapshot):
        attempt = row['attempt']
        if attempt is None:
            return row
        identity = client_id(engine.state.identity, attempt['epoch'], 'reduce')
        status = engine.state.db.execute('SELECT status FROM intents WHERE id=?', (identity,)).fetchone()
        if status is None:
            return row  # Crash after cap/epoch commit and before intent preparation.
        if status[0] == 'rejected':
            raise Blocked('held downside reduction rejected; no automatic retry')
        if status[0] != 'confirmed':
            raise Unknown('held downside reduction unresolved; stable identity retained')
        parent = owned_observation(engine.state, engine.reader, identity)['parent']
        executed = number(parent['executedQty'])
        if parent.get('status') not in TERMINAL or executed <= 0:
            raise Unknown('held downside reduction lacks positive terminal fill')
        q = number(snapshot['quantity_btc'])
        if q < 0 or q > number(attempt['before_btc'])-executed:
            raise Unknown('held downside fill conflicts with owned remaining quantity')
        row = dict(row, attempt=None, confirmed_orders=row['confirmed_orders']+1)
        save(engine, row)
        record('held-downside-reduction-confirmed', at_ms=int(engine.reader.clock()*1000),
               campaign=row['campaign'], client_order_id=identity, executed_btc=executed,
               remaining_btc=q, cap_btc=row['cap_btc'])
        return row

    def enforce(engine, row, snapshot):
        if getattr(engine.reader, 'offline', False) is not True:
            raise Blocked('held downside requires an offline venue before reduction')
        row = acknowledge(engine, row, snapshot)
        q, cap = number(snapshot['quantity_btc']), number(row['cap_btc'])
        if q < 0 or q > number(row['initial_btc']):
            raise Unknown('held downside owned position grew or changed direction')
        if not q:
            if row['attempt'] is not None:
                raise Unknown('flat snapshot does not confirm held reduction')
            if row['phase'] != 'FLAT':
                row = dict(row, phase='FLAT')
                save(engine, row)
                record('held-downside-flat-observed', campaign=row['campaign'],
                       at_ms=int(engine.reader.clock()*1000), reduction_fill_claim=False)
            return snapshot
        protection = engine.state.get('position_protection')
        fill = engine.state.get('entry_fill')
        if (not protection or protection.get('campaign') != row['campaign']
                or not fill or fill.get('campaign') != row['campaign']
                or snapshot['possible_entry_remainders'] or not engine.planned_protection(snapshot)):
            raise Unknown('held downside cap needs confirmed ownership and original protection')
        if q <= cap:
            if row['attempt'] is not None:
                raise Unknown('cap observation does not confirm held reduction')
            if row['phase'] != 'CAP_SATISFIED':
                save(engine, dict(row, phase='CAP_SATISFIED'))
            return snapshot
        if engine.state.pending():
            raise Unknown('pending intent blocks a new held downside reduction')
        rules = engine.instrument()
        attempt = row['attempt']
        if attempt is None:
            legal = market_quantity(q-cap, snapshot['mark_price'], rules, reduce_only=True)
            if legal <= 0:
                # Rounding is never rounded up past the fixed cap. The tiny
                # unsellable residue stays protected and is never bought back.
                if row['phase'] != 'ROUNDING_LIMIT':
                    save(engine, dict(row, phase='ROUNDING_LIMIT'))
                    record('held-downside-rounding-limit', campaign=row['campaign'],
                           remaining_btc=q, cap_btc=cap)
                return snapshot
            attempt = dict(epoch=engine.epoch(), quantity=str(legal), before_btc=str(q),
                           prepared_ms=int(engine.reader.clock()*1000))
            row = dict(row, attempt=attempt)
            save(engine, row)
        else:
            # A saved unsent attempt may be completed only with unchanged size;
            # changing its payload would invalidate the durable order identity.
            if (q != number(attempt['before_btc'])
                    or market_quantity(attempt['quantity'], snapshot['mark_price'], rules,
                                       reduce_only=True) != number(attempt['quantity'])):
                raise Unknown('held downside unsent reduction observation changed')
        result = safety.reduce_existing(engine.reader, engine.state, engine.send, engine.uid,
            attempt['epoch'], attempt['quantity'], instrument=rules,
            authorized=engine.authorized, snapshot=snapshot)
        result = base_recover(engine, result)
        row = acknowledge(engine, row, result)
        remaining = number(result['quantity_btc'])
        if remaining <= cap:
            save(engine, dict(row, phase='FLAT' if not remaining else 'CAP_SATISFIED'))
        return result

    def recover(engine, snapshot):
        # The original path reconciles every native fill, including stop races.
        # This runs in ordinary recovery and finish; it never needs market replay.
        result = base_recover(engine, snapshot)
        rows = _caps(engine.state, policy)
        protection = engine.state.get('position_protection')
        if protection:
            row = rows.get(str(protection['campaign']))
            if row:
                return enforce(engine, row, result)
        elif not number(result['quantity_btc']):
            for row in rows.values():
                if row['phase'] != 'FLAT':
                    enforce(engine, row, result)
        return result

    def decide(engine, model, snapshot):
        if getattr(engine.reader, 'offline', False) is not True:
            raise Blocked('held downside requires an offline venue before decision')
        q = number(snapshot['quantity_btc'])
        action = model.action(q)
        row = cap_for(engine, model)
        if row is None and action == 'hold' and q > 0:
            now = int(engine.reader.clock()*1000)
            if type(model.last) is not int or model.last > now:
                raise Blocked('held downside requires causally completed history')
            stats = measure(model.returns, completed_through_ms=model.last//DAY*DAY,
                            decision_ms=now)
            if stats['triggered']:
                # Reuse original ownership/protection recovery before establishing
                # a cap. Only an actual confirmed non-dust position can trigger.
                snapshot = base_recover(engine, snapshot)
                q = number(snapshot['quantity_btc'])
                fill, protection = engine.state.get('entry_fill'), engine.state.get('position_protection')
                campaign = model.active.identity
                if (q <= 0 or model.position_campaign != campaign or not fill
                        or fill.get('campaign') != campaign or not protection
                        or protection.get('campaign') != campaign or engine.state.pending()
                        or snapshot['possible_entry_remainders'] or not engine.planned_protection(snapshot)):
                    raise Unknown('held downside trigger has no confirmed owned protected campaign')
                cap = q/2 if policy == POLICIES[0] else D(0)
                if market_quantity(q-cap, snapshot['mark_price'], engine.instrument(), reduce_only=True) > 0:
                    row = dict(policy=policy, campaign=campaign, direction=1,
                        initial_btc=str(q), cap_btc=str(cap), triggered_ms=now,
                        completed_through_ms=stats['completed_through_ms'],
                        phase='CAP_ACTIVE', attempt=None, confirmed_orders=0)
                    save(engine, row)
                    record('held-downside-cap', at_ms=now, campaign=campaign, initial_btc=q,
                           cap_btc=cap, completed_returns=list(map(str, model.returns)),
                           **stats)
        if row and q > 0:
            snapshot = enforce(engine, row, snapshot)
            if not number(snapshot['quantity_btc']):
                return 'exit', snapshot
        return base_decide(engine, model, snapshot)

    def topup(engine, model, snapshot):
        if cap_for(engine, model) is not None:
            return snapshot
        return base_topup(engine, model, snapshot)

    def rebalance(engine, model, snapshot):
        if cap_for(engine, model) is not None:
            return snapshot
        return base_rebalance(engine, model, snapshot)

    def preview(model, snapshot):
        result = base_preview(model, snapshot)
        now = snapshot.get('observed_at_ms')
        if type(now) is int and type(model.last) is int and model.last <= now:
            stats = measure(model.returns, completed_through_ms=model.last//DAY*DAY, decision_ms=now)
            result['held_downside_preview'] = _serial(dict(stats,
                held_long=number(snapshot['quantity_btc']) > 0,
                execution_qualified=False, policy=policy))
        return result

    with (patch.object(session, '_LIFECYCLE_IDENTITY', identity),
          patch.object(session, '_guard_strategy', guard),
          patch.object(session, 'preview', preview),
          patch.object(Lifecycle, 'decide', decide),
          patch.object(Lifecycle, 'recover_exposure', recover),
          patch.object(Lifecycle, 'top_up', topup),
          patch.object(Lifecycle, 'rebalance', rebalance)):
        def run(config, venue, **kwargs):
            if getattr(venue, 'offline', False) is not True:
                raise ValueError('held downside refuses adapters before clock or recovery')
            return session.run(config, venue, **kwargs)
        yield SimpleNamespace(run=run, identity=identity)
