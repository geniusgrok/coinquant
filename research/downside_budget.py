"""Two frozen downside statistics for a campaign's initial funded target.

Research-only context around the actual finite session and Lifecycle. It changes
the initial target statistic, never stops, reserve amounts, capital, commissions,
native bracket checks, clock, or committed top-up quantity. No account producer
or network client lives here.
"""
from contextlib import contextmanager
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from coinquant.linear_account import FEE
from coinquant.linear_sizing import FUNDING_RESERVE, GAP
from coinquant.types import Blocked

POLICIES = ('downside-semivar', 'downside-tail4')
WINDOW = 20
SHRINKAGE = D('.5')
# phi(Phi^-1(.8))/.2 = 1.399809602039041... . This fixed normal-reference
# scale gives a worst-20%-mean loss the units of standard deviation. It is not
# a fitted parameter, a Gaussian assumption about BTC, or a seven-day ES claim.
NORMAL_ES20 = D('1.399809602')
PROTOCOL = dict(format='btc-initial-downside-budget-v1', window=WINDOW,
    shrinkage=str(SHRINKAGE), policies=list(POLICIES), tail_count=4,
    normal_es20=str(NORMAL_ES20), absence_days=7, multiplier='2.33',
    semivar='sqrt(.5*mean(r^2)+.5*2*mean(min(r,0)^2))',
    tail4='sqrt(.5*mean(r^2)+.5*(mean(top4(max(-r,0)))/normal_es20)^2)',
    unchanged='risk, gap, funding, fees, stop budget, capital and quantity preflight',
    ownership='initial fresh campaign only; top-up reads committed requested BTC')


def estimate(returns, policy):
    """Finite completed daily returns; fixed shrinkage bounds sizing optimism.

    The shrinkage gives sigma >= symmetric RMS/sqrt(2), including zero observed
    losses. That is an estimator-stability bound, not an economic risk guarantee.
    Positive-only history can still increase targets; real funding/protection
    bounds stay authoritative. A short history is not padded with zero returns.
    """
    if policy not in POLICIES:
        raise ValueError('unregistered downside expression')
    values = [D(str(value)) for value in list(returns)[-WINDOW:]]
    if any(not value.is_finite() or value <= -1 for value in values):
        raise ValueError('finite daily returns greater than -1 required')
    if len(values) < WINDOW:
        return dict(ready=False, observations=len(values), rms=D(0), sigma=D(0),
                    raw_downside_sigma=D(0), policy=policy)
    symmetric = sum((value*value for value in values), D(0))/WINDOW
    if policy == 'downside-semivar':
        downside = 2*sum((min(value, D(0))**2 for value in values), D(0))/WINDOW
    else:
        losses = sorted((max(-value, D(0)) for value in values), reverse=True)
        downside = (sum(losses[:4], D(0))/4/NORMAL_ES20)**2
    return dict(ready=True, observations=WINDOW, rms=symmetric.sqrt(),
                sigma=((1-SHRINKAGE)*symmetric+SHRINKAGE*downside).sqrt(),
                raw_downside_sigma=downside.sqrt(), policy=policy)


def target_fraction(returns, friction, policy, *, risk=1, absence_days=7):
    """Original budget denominator, with only its volatility statistic changed."""
    friction, risk = D(str(friction)), D(str(risk))
    if (not friction.is_finite() or friction < 0 or not risk.is_finite() or risk < 0
            or type(absence_days) is not int or absence_days != 7):
        raise ValueError('finite budget and fixed seven-day reserve required')
    stats = estimate(returns, policy)
    if not stats['ready']:
        return D(0)
    denominator = (D('2.33')*stats['sigma']*D(absence_days).sqrt()
                   + GAP+FUNDING_RESERVE+2*(FEE+friction))
    return risk*D('.20')/denominator


def measure(returns, *, policy, risk, friction='.0011',
            completed_through_ms=None, decision_ms=None):
    """Cheap sizing diagnostic, never a wallet or counterfactual equity curve."""
    if (completed_through_ms is not None or decision_ms is not None) and not (
            type(completed_through_ms) is int and type(decision_ms) is int
            and completed_through_ms <= decision_ms):
        raise Blocked('downside sizing requires causally completed history')
    values = list(returns)
    from coinquant.linear_sizing import target_fraction as symmetric_fraction
    result = estimate(values, policy)
    candidate = target_fraction(values, friction, policy, risk=risk)
    original = D(str(risk))*symmetric_fraction([D(str(v)) for v in values], D(str(friction)))
    result.update(original_fraction=original, candidate_fraction=candidate,
                  multiplier=candidate/original if original else None,
                  completed_through_ms=completed_through_ms, decision_ms=decision_ms,
                  counterfactual_wallet=False, economic_improvement_proven=False)
    return result


@contextmanager
def configured(policy, *, binding, journal=None):
    """Actual offline session; matching durable identity precedes recovery.

    The class-local entry_fraction override deliberately bypasses any research
    subclass's symmetric fraction override. It lasts only a fresh entry/preflight
    or its read-only preview. The unmodified Lifecycle commits its funded target
    into entry_fill.requested before sending; unmodified top_up reads that same
    requested BTC and cannot return to the former symmetric target.
    """
    if policy not in POLICIES or not isinstance(binding, dict) or not binding:
        raise ValueError('registered expression and nonempty immutable input binding required')
    from coinquant import campaign, session
    from coinquant.lifecycle import Lifecycle
    identity = dict(family='initial-downside-budget', policy=policy,
        protocol=PROTOCOL,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        binding=json.loads(json.dumps(binding, sort_keys=True)))
    identity = json.loads(json.dumps(identity, sort_keys=True))
    journal = journal if journal is not None else []
    original_guard, original_enter = session._guard_strategy, Lifecycle.enter
    original_preview, original_readonly = session.preview, session.entry_preview

    def guard(state):
        stored = state.get('lifecycle_identity')
        if stored != identity and (stored is not None or state.get('linear_campaign') is not None
                or state.get('entry_plan') or state.get('entry_fill')
                or state.get('entry_campaigns') or state.get('position_protection')
                or state.db.execute('SELECT 1 FROM intents LIMIT 1').fetchone()):
            raise Blocked('downside account identity mismatch before recovery')
        if stored is None:
            state.set('lifecycle_identity', identity)
        return original_guard(state)

    @contextmanager
    def sizing(model, *, now_ms=None, record=False):
        if model.position_campaign is not None:
            raise Blocked('downside expression applies only to a fresh campaign')
        if now_ms is not None and (type(model.last) is not int or model.last > now_ms):
            raise Blocked('downside sizing requires causally completed history')
        risk = (campaign.MACRO_RISK if model.macro_opportunity is not None
                and model.active is model.macro_opportunity else campaign.PRIMARY_RISK)
        original_fraction = type(model).entry_fraction
        if record:
            row = measure(model.returns, policy=policy, risk=risk,
                          completed_through_ms=model.last, decision_ms=now_ms)
            journal.append(dict(event='downside-initial-sizing', policy=policy,
                at_ms=now_ms, campaign=model.active.identity,
                completed_returns=list(map(str, model.returns)),
                **{key: str(value) if isinstance(value, D) else value for key, value in row.items()}))
        def fraction(selected, friction):
            if selected is model:
                return target_fraction(selected.returns, friction, policy, risk=risk)
            return original_fraction(selected, friction)
        with patch.object(type(model), 'entry_fraction', fraction):
            yield

    def enter(engine, model, snapshot):
        if getattr(engine.reader, 'offline', False) is not True:
            raise Blocked('downside requires an offline venue before sizing')
        now = int(engine.reader.clock()*1000)
        with sizing(model, now_ms=now, record=True):
            return original_enter(engine, model, snapshot)

    def preview(model, snapshot):
        if D(str(snapshot['quantity_btc'])) == 0 and model.action(D(0)) == 'enter':
            with sizing(model):
                return original_preview(model, snapshot)
        return original_preview(model, snapshot)

    def readonly(reader, model, snapshot):
        if getattr(reader, 'offline', False) is not True:
            raise Blocked('downside requires an offline venue before sizing')
        with sizing(model, now_ms=int(reader.clock()*1000)):
            return original_readonly(reader, model, snapshot)

    with (patch.object(session, '_LIFECYCLE_IDENTITY', identity),
          patch.object(session, '_guard_strategy', guard),
          patch.object(Lifecycle, 'enter', enter),
          patch.object(session, 'preview', preview),
          patch.object(session, 'entry_preview', readonly)):
        def run(config, venue, **kwargs):
            if getattr(venue, 'offline', False) is not True:
                raise ValueError('downside refuses account adapters before clock or recovery')
            return session.run(config, venue, **kwargs)
        yield SimpleNamespace(run=run, identity=identity)
