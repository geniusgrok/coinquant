"""Research-only macro entry deferral under the archived completed-day shock.

No opportunity is consumed, no position or protection is modified, and no
unattended decision is introduced. Only the original offline wallet may use it.
"""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from coinquant.types import Blocked, number
from research.held_risk import measure


@contextmanager
def configured(policy, *, binding, journal=None):
    if policy != 'entry-shock-defer' or not isinstance(binding, dict) or not binding:
        raise ValueError('frozen offline entry-shock policy and binding required')
    from coinquant import session
    from coinquant.lifecycle import Lifecycle
    identity = json.loads(json.dumps(dict(family='entry-shock-defer-v1',
        statistic='archived held_risk.measure: 5/20 completed daily downside RMS > 1.5',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        binding=binding), sort_keys=True))
    events = journal if journal is not None else []
    seen = set()
    old_guard, old_decide = session._guard_strategy, Lifecycle.decide

    def guard(state):
        stored = state.get('lifecycle_identity')
        if stored != identity:
            if (stored is not None or state.get('linear_campaign') is not None
                    or state.get('entry_plan') or state.get('entry_fill')
                    or state.get('entry_campaigns') or state.get('position_protection')
                    or state.db.execute('SELECT 1 FROM intents LIMIT 1').fetchone()):
                raise Blocked('entry shock identity mismatch before recovery')
            state.set('lifecycle_identity', identity)
        return old_guard(state)

    def decide(engine, model, snapshot):
        if getattr(engine.reader, 'offline', False) is not True:
            raise Blocked('entry shock requires original offline venue')
        if (number(snapshot['quantity_btc']) == 0 and model.action(0) == 'enter'
                and model.active is model.macro_opportunity and engine.risk_audit_ok
                and engine.may_enter()):
            now = int(engine.reader.clock() * 1000)
            stats = measure(model.returns, completed_through_ms=model.last // 86400000 * 86400000,
                            decision_ms=now)
            if stats['ready'] and stats['triggered']:
                key = (model.active.identity, engine.session)
                if key not in seen:
                    seen.add(key)
                    events.append(dict(event='entry-shock-deferred', policy=policy,
                                       campaign=model.active.identity, session=engine.session,
                                       completed_through_ms=stats['completed_through_ms']))
                return 'deferred', snapshot
        return old_decide(engine, model, snapshot)

    with (patch.object(session, '_LIFECYCLE_IDENTITY', identity),
          patch.object(session, '_guard_strategy', guard),
          patch.object(Lifecycle, 'decide', decide)):
        def run(config, venue, **kwargs):
            if getattr(venue, 'offline', False) is not True:
                raise ValueError('entry shock refuses non-offline adapters')
            return session.run(config, venue, **kwargs)
        yield SimpleNamespace(run=run, identity=identity)
