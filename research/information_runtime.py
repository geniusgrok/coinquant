"""Frozen information expressions through the original offline session/Lifecycle.

The incremental screen source and its original measured identity stay unchanged.
This separate adapter changes initial real orders, never rescales an equity curve.
"""
from contextlib import contextmanager
from copy import deepcopy
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from research.incremental_information import DAY, EXPRESSIONS, ReleaseBook, digest, serial

KIND = 'coin'
RULE = 'btc-release-actual-runtime-20261005-v1'


def admitted(book, binding, admission, kind):
    """An arbitrary caller's ELIGIBLE flag cannot admit account measurement."""
    if (not isinstance(book, ReleaseBook) or not isinstance(binding, dict) or not binding
            or not isinstance(admission, dict) or kind not in ('coin', 'spot')):
        raise ValueError('registered immutable information book/admission required')
    raw = (json.dumps(admission, indent=2)+'\n').encode()
    if (binding.get('information_result_sha256') != hashlib.sha256(raw).hexdigest()
            or binding.get('information_spec_sha256') != admission.get('spec_sha256')
            or admission.get('input_sha256') != book.input_sha256):
        raise ValueError('information screen/source/input binding mismatch')
    row = admission.get('assessments', {}).get(kind, {})
    if (row.get('status') != 'ELIGIBLE_FINITE_ACCOUNT_PROPOSAL'
            or row.get('account_entrant') is not True or not row.get('gates')
            or not all(value is True for value in row['gates'].values())):
        raise ValueError('mature incremental information has not admitted this kind')
    sources = admission.get('source_sha256', {})
    for name in ('incremental_information.py', 'edge_features.py', 'continuous_routes.py',
                 'tradeoff_routes.py', 'replacement_routes.py'):
        expected = [sha for path, sha in sources.items() if Path(path).name == name]
        actual = hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
        if expected != [actual]:
            raise ValueError('original information calculation source changed: '+name)


def identity(expression, book, binding, kind):
    return json.loads(json.dumps(dict(rule=RULE, expression=expression, kind=kind,
        input_sha256=book.input_sha256, source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        binding=binding), sort_keys=True))


def new_fraction(book, now):
    row = book.at(now)
    if row['status'] != 'FEATURE_READY':
        return None, row
    return D(1) if row['release'] else D('.5'), row


@contextmanager
def coin_budget(book, binding, journal, venue):
    from coinquant import session
    from coinquant.lifecycle import Lifecycle
    from coinquant.types import Blocked
    selected_identity = identity(EXPRESSIONS[1], book, binding, 'coin')
    original_guard, original_enter = session._guard_strategy, Lifecycle.enter
    original_preview, original_readonly = session.preview, session.entry_preview

    def guard(state):
        stored = state.get('lifecycle_identity')
        occupied = any(state.get(k) is not None for k in (
            'linear_campaign', 'entry_plan', 'entry_fill', 'entry_campaigns', 'position_protection'))
        if stored != selected_identity and (stored is not None or occupied or
                state.db.execute('SELECT 1 FROM intents LIMIT 1').fetchone()):
            raise Blocked('information budget identity mismatch before recovery')
        if stored is None:
            state.set('lifecycle_identity', selected_identity)
        return original_guard(state)

    @contextmanager
    def sizing(model, now, *, record=False):
        if model.position_campaign is not None or model.last > now:
            raise Blocked('information budget applies only to a causal fresh campaign')
        factor, row = new_fraction(book, now)
        if factor is None:
            raise Blocked('information budget refuses missing causal information')
        original_fraction = type(model).entry_fraction
        def fraction(target, friction):
            base = original_fraction(target, friction)
            return base*factor if target is model else base
        if record:
            journal.append(serial(dict(event='information-initial-sizing', at_ms=now,
                campaign=model.active.identity, factor=factor, release=row['release'],
                signal_day_ms=row['day_ms'], latest_input_available_ms=row['latest_input_available_ms'],
                original_fraction=original_fraction(model, '.0011'),
                funded_requested='Unmodified Lifecycle commits the new initial target before sending; topup reads that requested BTC')))
        with patch.object(type(model), 'entry_fraction', fraction):
            yield

    def enter(engine, model, snapshot):
        if engine.reader is not venue or getattr(venue, 'offline', False) is not True:
            raise Blocked('information refuses account adapters before sizing')
        with sizing(model, int(venue.clock()*1000), record=True):
            return original_enter(engine, model, snapshot)

    def preview(model, snapshot):
        if D(str(snapshot['quantity_btc'])) == 0 and model.action(D(0)) == 'enter':
            with sizing(model, int(venue.clock()*1000)):
                return original_preview(model, snapshot)
        return original_preview(model, snapshot)

    def readonly(reader, model, snapshot):
        if reader is not venue or getattr(reader, 'offline', False) is not True:
            raise Blocked('information refuses account adapters before sizing')
        with sizing(model, int(reader.clock()*1000)):
            return original_readonly(reader, model, snapshot)

    with (patch.object(session, '_LIFECYCLE_IDENTITY', selected_identity),
          patch.object(session, '_guard_strategy', guard), patch.object(Lifecycle, 'enter', enter),
          patch.object(session, 'preview', preview), patch.object(session, 'entry_preview', readonly)):
        def run(config, reader, **kwargs):
            if reader is not venue or getattr(reader, 'offline', False) is not True:
                raise ValueError('information venue changed before recovery')
            return session.run(config, reader, **kwargs)
        yield SimpleNamespace(run=run, identity=selected_identity)


def primary_class(book):
    """Additional independently consumed Coin opportunity, original entries lead."""
    from coinquant.campaign import Campaign as Legacy
    from coinquant.opportunities import Opportunity
    from coinquant.types import Blocked

    class InformationCampaign(Legacy):
        core_rule = RULE+':new-primary'

        def __init__(self):
            super().__init__()
            self.information_active = None
            self.information_regime = self.information_consumed = None
            self.information_call = self.information_day = None
            self.information_peak = self.information_peak_after = None
            self.information_stop_crossed = False

        def information_owned(self):
            return (self.information_consumed is not None and
                    self.position_campaign == self.information_consumed)

        @property
        def active(self):
            if self.information_owned():
                return self.information_active
            original = Legacy.active.fget(self)
            consumed = self.macro_consumed if original is self.macro_opportunity else self.primary_consumed
            if original is not None and (self.position_campaign is not None or original.identity != consumed):
                return original
            return self.information_active if self.information_active is not None else original

        def macro_relevant(self):
            return False if self.information_owned() else Legacy.macro_relevant(self)

        def update(self, end, high, low, close):
            Legacy.update(self, end, high, low, close)
            a = self.information_active
            if a is not None:
                if end >= a.expires:
                    self.information_active = None
                elif self.information_owned():
                    eligible = self.information_peak_after is not None and end-self.model.interval >= self.information_peak_after
                    self.information_peak = max(self.information_peak, D(high) if eligible else D(close))
                    self.information_active = Opportunity(a.identity, 1, max(a.stop, self.information_peak*D('.75')), a.take, a.expires)
            return self.active

        def select_macro(self, row, mark, call, *, bootstrap=False):
            # The original DFII10 reader and unknown-input behavior still run
            # whenever the incumbent can use it. A missing macro is not cash.
            Legacy.select_macro(self, row, mark, call, bootstrap=bootstrap)
            feature = book.at(call)
            self.information_call = call
            self.information_day = feature.get('day_ms')
            if self.information_owned():
                self.information_stop_crossed = bool(self.information_active is not None and D(mark) <= self.information_active.stop)
                return
            if self.position_campaign is not None:
                return
            if feature['status'] != 'FEATURE_READY':
                self.information_active = None
                return  # No new entry; the original known strategy still works.
            if not feature['release']:
                self.information_regime = self.information_active = None
                return
            if self.information_regime is None:
                # Incumbent primary IDs are exact completed four-hour ends;
                # macro IDs are negative. This positive millisecond is disjoint.
                self.information_regime = self.last-1
            if self.information_regime == self.information_consumed:
                self.information_active = None
                return
            if call >= self.information_regime+1+7*DAY:
                self.information_active = None
                return
            original = Legacy.active.fget(self)
            used = self.macro_consumed if original is self.macro_opportunity else self.primary_consumed
            if original is not None and original.identity != used:
                self.information_active = None
                return
            if row is None or row.get('missing_reason') is not None:
                self.information_active = None
                return  # A known missing macro value cannot create idle cash.
            if self.information_active is None:
                price = D(mark)
                if not price.is_finite() or price <= 0:
                    raise Blocked('causal information entry mark required')
                self.information_peak = price
                self.information_peak_after = (call//self.model.interval+1)*self.model.interval
                self.information_active = Opportunity(self.information_regime, 1, price*D('.75'),
                                                      price*4, self.information_regime+1+7*DAY)
                if self.information_active.expires <= call:
                    self.information_active = None

        def entry_fraction(self, friction):
            return D(1) if self.active is self.information_active and self.information_active is not None else Legacy.entry_fraction(self, friction)

        def action(self, quantity):
            if self.information_owned():
                return 'exit' if self.information_active is None or self.information_stop_crossed else 'hold' if quantity else 'consumed'
            if quantity:
                return Legacy.action(self, quantity)
            if self.active is self.information_active and self.information_active is not None:
                return 'consumed' if self.information_regime == self.information_consumed else 'enter'
            return Legacy.action(self, quantity)

        def checkpoint(self):
            saved = Legacy.checkpoint(self)
            a = self.information_active
            saved['body']['information'] = serial(dict(rule=self.core_rule, input_sha256=book.input_sha256,
                regime=self.information_regime, consumed=self.information_consumed,
                call=self.information_call, day=self.information_day,
                peak=self.information_peak, peak_after=self.information_peak_after,
                stop_crossed=self.information_stop_crossed,
                active=None if a is None else vars(a)))
            # The incumbent restore already rejects a foreign core checkpoint.
            saved['body']['core'] = dict(rule=self.core_rule, input_sha256=book.input_sha256)
            saved['sha256'] = digest(saved['body'])
            return saved

        @classmethod
        def restore(cls, saved):
            try:
                if saved['sha256'] != digest(saved['body']):
                    raise ValueError('information checkpoint digest')
                body = dict(saved['body']); extra = body.pop('information')
                if body.pop('core') != dict(rule=cls.core_rule, input_sha256=book.input_sha256):
                    raise ValueError('information core marker')
                if extra['rule'] != cls.core_rule or extra['input_sha256'] != book.input_sha256:
                    raise ValueError('information source identity')
                result = Legacy.restore.__func__(cls, dict(body=body, sha256=digest(body)))
                for old, new in (('regime', 'information_regime'), ('consumed', 'information_consumed'),
                                 ('call', 'information_call'), ('day', 'information_day'),
                                 ('peak_after', 'information_peak_after'), ('stop_crossed', 'information_stop_crossed')):
                    setattr(result, new, extra[old])
                result.information_peak = None if extra['peak'] is None else D(extra['peak'])
                a = extra['active']
                result.information_active = None if a is None else Opportunity(
                    a['identity'], a['direction'], D(a['stop']), D(a['take']), a['expires'])
                for key in ('information_regime', 'information_consumed'):
                    value = getattr(result, key)
                    if value is not None and (type(value) is not int or not 1575158400000 < value <= result.last
                                              or value % result.model.interval != result.model.interval-1):
                        raise ValueError('information opportunity identity')
                if result.information_call is not None:
                    if type(result.information_call) is not int or not 1575158400000 < result.information_call < result.last+result.model.interval:
                        raise ValueError('information causal decision clock')
                    feature = book.at(result.information_call)
                    if result.information_day != feature.get('day_ms'):
                        raise ValueError('information feature checkpoint clock')
                if a is not None and (a['identity'] != result.information_regime or a['direction'] != 1
                        or type(a['expires']) is not int or a['expires'] != a['identity']+1+7*DAY
                        or not 0 < result.information_active.stop < result.information_active.take
                        or not result.information_active.stop.is_finite() or not result.information_active.take.is_finite()):
                    raise ValueError('information protection geometry')
                if (type(result.information_stop_crossed) is not bool or
                        result.information_peak_after is not None and (type(result.information_peak_after) is not int
                            or result.information_peak_after % result.model.interval
                            or result.information_peak_after > result.last+result.model.interval) or
                        result.information_peak is not None and (not result.information_peak.is_finite() or result.information_peak <= 0)):
                    raise ValueError('information owned peak')
                return result
            except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
                raise Blocked('invalid information checkpoint; no reset') from exc

    return InformationCampaign


def reconcile_information(original, state, reader, model, snapshot):
    """Fold independent consumption only inside proven native reconciliation.

    The incumbent reconcile writes the checkpoint immediately after it has
    proved all order links, fills and the stable wallet. Adjust that one write,
    so even an interruption before this wrapper returns preserves correct
    independent consumption and the previous incumbent primary consumption.
    """
    from coinquant.types import Unknown
    if getattr(model, 'core_rule', None) != RULE+':new-primary':
        return original(state, reader, model, snapshot)
    prior_primary = model.primary_consumed
    original_checkpoint = model.checkpoint
    reconciled_campaign = []
    def checkpoint():
        campaign = model.consumed
        if campaign == model.information_regime and campaign is not None:
            # Only original reconcile reaches this checkpoint after native
            # ownership is proved. The disjoint integer ID prevents inferring
            # an information fill from an incumbent primary's same-bar fill.
            if (campaign % model.model.interval != model.model.interval-1
                    or model.position_campaign not in (None, campaign)):
                raise Unknown('information campaign ownership namespace mismatch')
            model.information_consumed = campaign
            model.primary_consumed = prior_primary
            reconciled_campaign.append(campaign)
        return original_checkpoint()
    with patch.object(model, 'checkpoint', checkpoint):
        result = original(state, reader, model, snapshot)
    if reconciled_campaign and (result.get('status') != 'reconciled'
            or result.get('campaign') != reconciled_campaign[-1]):
        raise Unknown('information consumption lacks successful native reconciliation')
    return result


@contextmanager
def coin_primary(book, binding, journal, venue):
    from coinquant import linear_preview, ownership, session
    from coinquant.lifecycle import Lifecycle
    from coinquant.types import Blocked
    selected = primary_class(book)
    selected_identity = identity(EXPRESSIONS[0], book, binding, 'coin')
    original_guard, original_topup, original_enter = session._guard_strategy, Lifecycle.top_up, Lifecycle.enter
    original_reconcile = ownership.reconcile
    def guard(state):
        stored = state.get('lifecycle_identity')
        occupied = any(state.get(k) is not None for k in ('linear_campaign', 'entry_plan', 'entry_fill', 'entry_campaigns', 'position_protection'))
        if stored != selected_identity and (stored is not None or occupied or state.db.execute('SELECT 1 FROM intents LIMIT 1').fetchone()):
            raise Blocked('information primary identity mismatch before recovery')
        if stored is None:
            state.set('lifecycle_identity', selected_identity)
        return original_guard(state)
    def topup(engine, model, snapshot):
        return snapshot if isinstance(model, selected) and model.information_owned() else original_topup(engine, model, snapshot)
    def enter(engine, model, snapshot):
        if isinstance(model, selected) and model.active is model.information_active and model.information_active is not None:
            feature = book.at(int(venue.clock()*1000))
            journal.append(serial(dict(event='information-new-primary', at_ms=int(venue.clock()*1000),
                event_identity=model.information_regime, signal_day_ms=feature.get('day_ms'),
                release=feature.get('release'), gross_equity_cap='1', topup=False,
                expires_ms=model.information_active.expires)))
        return original_enter(engine, model, snapshot)
    def reconcile(state, reader, model, snapshot):
        return reconcile_information(original_reconcile, state, reader, model, snapshot)
    def run(config, reader, **kwargs):
        if reader is not venue or getattr(reader, 'offline', False) is not True:
            raise ValueError('information refuses account adapters before recovery')
        report = session.run(config, reader, **kwargs)
        journal.append(dict(event='information-primary-session', status=report['status']))
        return report
    with (patch.object(linear_preview, 'Campaign', selected), patch.object(session, '_LIFECYCLE_IDENTITY', selected_identity),
          patch.object(session, '_guard_strategy', guard), patch.object(Lifecycle, 'top_up', topup),
          patch.object(Lifecycle, 'enter', enter), patch.object(ownership, 'reconcile', reconcile),
          patch.object(session, 'reconcile', reconcile)):
        yield SimpleNamespace(run=run, identity=selected_identity)


@contextmanager
def spot_budget(book, binding, journal, venue, features):
    from research import edge_spot as edge
    from spotquant import session
    if features is None or features.sha256 != book.features.sha256:
        raise ValueError('the original mandatory crowding source is required')
    selected_identity = identity(EXPRESSIONS[1], book, binding, 'spot')
    class Policy(edge.Policy):
        def __call__(self, views, owned, snapshot, **kwargs):
            decision = super().__call__(views, owned, snapshot, **kwargs)
            for order in list(decision['orders']):
                if order['side'] != 'BUY':
                    continue
                before = D(order['quoteOrderQty'])
                factor, row = new_fraction(book, venue.now_ms)
                after = edge.resize(decision, order, before*(factor if factor is not None else D(0)))
                journal.append(serial(dict(event='information-new-buy-budget', at_ms=venue.now_ms,
                    signal_day_ms=row.get('day_ms'), release=row.get('release'), factor=factor,
                    original_legal_quote=before, resulting_quote=after,
                    reason=None if factor is not None else row['reason'], held_changes=False)))
            decision['order'] = decision['orders'][0] if decision['orders'] else None
            if not decision['orders']:
                decision['action'] = 'hold' if any(D(q) >= edge.preview.BASE_STEP for q in owned.values()) else 'flat'
            return decision
    policy = Policy('crowding-interaction', venue, features)
    policy.identity.update(information_runtime=selected_identity)
    policy.journal = journal
    with edge.configured(policy):
        def run(config, reader, **kwargs):
            if reader is not venue or getattr(reader, 'offline', False) is not True:
                raise ValueError('information refuses account adapters before recovery')
            return session.run(config, reader, **kwargs)
        yield SimpleNamespace(run=run, policy=policy, identity=selected_identity)


@contextmanager
def configured(expression, *, book, binding, venue, admission, journal=None, features=None, kind=KIND):
    if expression not in EXPRESSIONS or getattr(venue, 'offline', False) is not True:
        raise ValueError('registered offline information venue required before clock/recovery')
    admitted(book, binding, admission, kind)
    journal = journal if journal is not None else []
    if kind == 'coin':
        context = coin_budget(book, binding, journal, venue) if expression == EXPRESSIONS[1] else coin_primary(book, binding, journal, venue)
    elif expression == EXPRESSIONS[1]:
        context = spot_budget(book, binding, journal, venue, features)
    else:
        raise ValueError('Spot standalone information core requires its separate owned-hold expression; Coin core cannot substitute')
    with context as selected:
        yield selected
