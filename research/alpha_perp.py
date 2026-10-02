"""Frozen alpha/beta mechanisms, using the existing finite-session economic meter.

Hooks are process-local, restored on every exit, and read only observations that
Lifecycle already obtained. This module never enables native account access.
"""
import argparse
from collections import Counter, deque
from contextlib import ExitStack, contextmanager
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal as D
import gzip
import hashlib
import json
from pathlib import Path
from statistics import median
from types import SimpleNamespace
from unittest.mock import patch

from coinquant import campaign, lifecycle, linear_preview, ownership, session
from coinquant.opportunities import Opportunity, FOUR_HOURS
from coinquant.types import Blocked
from research import complete_perp as meter, rebuild, session_schedule

CANDIDATES = ('incumbent', 'fresh-entry', 'atr-trail', 'compression-breakout', 'single-topup')
CUTOFF = 1640995200000
SPEC = Path(__file__).with_name('alpha_beta_spec.json')
PROTOCOL = Path(__file__).with_name('alpha-beta-PROTOCOL.md')
BaseCampaign = campaign.Campaign


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def components(name):
    values = name.split('+') if name != 'incumbent' else []
    if any(v not in CANDIDATES[1:] for v in values) or len(set(values)) != len(values):
        raise ValueError('unknown or duplicate registered component')
    return tuple(v for v in CANDIDATES[1:] if v in values)


def calibration(path, names):
    if path is None:
        return {}, None
    body = json.loads(Path(path).read_bytes())
    if (body.get('format') != 1 or body.get('cutoff_ms') != CUTOFF or
            body.get('spec_sha256') != file_hash(SPEC)):
        raise ValueError('risk calibration format, cutoff or spec mismatch')
    profiles = {}
    for name in names:
        p = body['profiles'][name]
        scale = D(p['scale'])
        digest = p.get('base_bundle_sha256', '')
        if (not scale.is_finite() or not 0 <= scale <= 1 or
                p.get('effective_from_ms') != CUTOFF or p.get('calibration_end_ms') != CUTOFF or
                p.get('training_end_day_exclusive') != '2022-01-01' or
                p.get('baseline_candidate') != 'incumbent' or len(digest) != 64 or
                any(c not in '0123456789abcdef' for c in digest)):
            raise ValueError('invalid candidate risk calibration')
        profiles[name] = p
    return profiles, file_hash(path)


class AlphaCampaign(BaseCampaign):
    components = ()
    binding = None
    scale = D(1)
    journal = None

    def __init__(self):
        super().__init__()
        self.highs = deque(maxlen=20)
        self.atrs = deque(maxlen=20)
        self.trigger = None
        self.macro_trigger = None
        self.trail = None
        self.decision_ms = None
        self.decision_mark = None
        self.decision_stop = None
        self.reason = None

    def update(self, end, high, low, close):
        high, low, close = map(D, (high, low, close))
        prior_atr = sum(self.model.tr)/14 if len(self.model.tr) == 14 else None
        old = self.model.active
        breakout = ('compression-breakout' in self.components and len(self.highs) == 20 and
                    len(self.atrs) == 20 and prior_atr is not None and prior_atr > 0 and
                    close > max(self.highs) and prior_atr <= D('.75')*median(self.atrs))
        super().update(end, high, low, close)
        created_breakout = self.model.active is None and breakout
        if created_breakout:
            stop = close-2*prior_atr
            if stop > 0:
                self.model.active = Opportunity(end, 1, stop, close*(close/stop)**20,
                                                end+42*FOUR_HOURS)
        active = self.model.active
        if active is not None and (old is None or old.identity != active.identity):
            self.trigger = {'identity': active.identity, 'close': str(close),
                            'prior_atr': str(prior_atr) if prior_atr is not None else None,
                            'direction': active.direction,
                            'kind': 'compression-breakout' if created_breakout else 'impulse'}
            if self.journal is not None:
                self.journal.append({'event': 'opportunity', 'at_ms': end, **self.trigger})
        if active is None:
            self.trigger = None
        self.highs.append(high)
        # Each observation is ATR at that completed bar, so every median input
        # precedes the next trigger (including its immediately prior ATR).
        if len(self.model.tr) == 14:
            self.atrs.append(sum(self.model.tr)/14)
        if self.trail and end-FOUR_HOURS >= self.trail['confirmed_at_ms']:
            self.trail['high'] = str(max(D(self.trail['high']), high))
        return active

    @property
    def active(self):
        selected = super().active
        if (selected is not None and selected.identity > 0 and self.decision_stop is not None and
                selected.identity == self.position_campaign):
            return replace(selected, stop=max(selected.stop, self.decision_stop))
        return selected

    def select_macro(self, row, mark, call, *, bootstrap=False):
        previous = self.macro_opportunity
        super().select_macro(row, mark, call, bootstrap=bootstrap)
        self.decision_ms, self.decision_mark = call, D(mark)
        active = self.macro_opportunity
        if active is None:
            self.macro_trigger = None
        elif previous is None or previous.identity != active.identity:
            self.macro_trigger = {'identity': active.identity, 'created_at_ms': call,
                'decision_mark': str(D(mark)), 'dfii10': deepcopy(row), 'kind': 'macro', 'direction': 1}
            if self.journal is not None:
                self.journal.append({'event': 'opportunity', 'at_ms': call, **deepcopy(self.macro_trigger)})

    def action(self, quantity):
        self.reason = None
        action = super().action(quantity)
        if action == 'hold' and self.decision_stop is not None and self.decision_stop >= self.decision_mark:
            self.reason = 'atr_trail_through_mark'
            return 'exit'
        if action == 'enter' and self.active.identity > 0 and 'fresh-entry' in self.components:
            trigger = self.trigger
            if not trigger or trigger['identity'] != self.active.identity or trigger['prior_atr'] is None:
                raise Blocked('immutable primary trigger provenance unavailable')
            if self.decision_ms-self.active.identity > 86400000:
                self.reason = 'stale_primary'
            elif self.decision_mark > D(trigger['close'])+D(trigger['prior_atr']):
                self.reason = 'chased_primary'
            if self.reason:
                return 'flat'
        return action

    def entry_fraction(self, friction):
        scale = self.scale if self.decision_ms is not None and self.decision_ms >= CUTOFF else D(1)
        return super().entry_fraction(friction)*scale

    def checkpoint(self):
        saved = super().checkpoint()
        saved['body']['alpha'] = {'binding': self.binding, 'highs': list(map(str, self.highs)),
            'atrs': list(map(str, self.atrs)), 'trigger': self.trigger,
            'macro_trigger': self.macro_trigger, 'trail': self.trail}
        saved['sha256'] = meter.checksum(saved['body'])
        return saved

    @classmethod
    def restore(cls, saved):
        try:
            body = dict(saved['body'])
            if saved['sha256'] != meter.checksum(body):
                raise ValueError('digest')
            extra = body.pop('alpha')
            if extra['binding'] != cls.binding:
                raise ValueError('candidate/input binding')
            model = BaseCampaign.restore.__func__(cls, {'body': body, 'sha256': meter.checksum(body)})
            for key in ('highs', 'atrs'):
                values = [D(v) for v in extra[key]]
                if len(values) > 20 or any(not v.is_finite() or v < 0 or (key == 'highs' and not v) for v in values):
                    raise ValueError('rolling history')
                setattr(model, key, deque(values, maxlen=20))
            model.trigger, model.trail = extra['trigger'], extra['trail']
            if model.trigger:
                t = model.trigger
                if (model.model.active is None or t['identity'] != model.model.active.identity or
                        t['kind'] not in ('impulse', 'compression-breakout') or
                        not D(t['close']).is_finite() or D(t['close']) <= 0 or
                        (t['prior_atr'] is not None and (not D(t['prior_atr']).is_finite() or D(t['prior_atr']) <= 0))):
                    raise ValueError('trigger provenance')
            elif model.model.active is not None:
                raise ValueError('missing trigger provenance')
            model.macro_trigger = extra['macro_trigger']
            if model.macro_trigger:
                t = model.macro_trigger
                if (model.macro_opportunity is None or t['identity'] != model.macro_opportunity.identity or
                        type(t['created_at_ms']) is not int or
                        not -t['identity'] <= t['created_at_ms'] < model.last+FOUR_HOURS or
                        t['kind'] != 'macro' or t['direction'] != 1 or not isinstance(t['dfii10'], dict) or
                        not D(t['decision_mark']).is_finite() or D(t['decision_mark']) <= 0):
                    raise ValueError('macro trigger provenance')
            elif model.macro_opportunity is not None:
                raise ValueError('missing macro trigger provenance')
            if model.trail:
                t = model.trail
                if (type(t['campaign']) is not int or t['campaign'] <= 0 or
                        type(t['confirmed_at_ms']) is not int or t['confirmed_at_ms'] < t['campaign'] or
                        not D(t['high']).is_finite() or D(t['high']) <= 0):
                    raise ValueError('entry trail')
            return model
        except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
            raise Blocked('invalid alpha checkpoint') from exc


def confirmed_topup(state, campaign_id, bar):
    """Only cached terminal fills linked to a reconciled owned add consume it."""
    archived = state.get('terminal_native_orders') or {}
    fills = [json.loads(row[0]) for row in state.db.execute('SELECT payload FROM native_fills')]
    for identity, link in (state.get('entry_campaigns') or {}).items():
        if link.get('campaign') != campaign_id or not link.get('add'):
            continue
        order = archived.get(identity, {}).get('parent', {})
        result = (state.get('alpha_topup_attempts') or {}).get(identity, {})
        if (D(order.get('executedQty', '0')) > 0 and D(result.get('position_before_btc', '0')) != 0 and
                any(str(fill['orderId']) == str(order.get('orderId')) and D(fill['qty']) > 0 and
                    fill['time']//FOUR_HOURS*FOUR_HOURS == bar for fill in fills)):
            return True
    return False


@contextmanager
def variant(name, *, binding=None, profile=None, journal=None):
    """Wrap the existing coordinator without extra reads, waits, or safety gates."""
    selected = components(name)
    profile = profile or {}
    binding = meter.checksum({'name': name, 'components': selected, 'inputs': binding,
                              'profile': profile, 'spec': file_hash(SPEC)})
    journal = journal if journal is not None else []
    original_reconcile = ownership.reconcile
    original_decide, original_topup = lifecycle.Lifecycle.decide, lifecycle.Lifecycle.top_up
    original_send = lifecycle.Lifecycle.send
    original_cycle = session.cycle
    cycle_sequence = 0

    def reconcile(state, reader, model, snapshot):
        result = original_reconcile(state, reader, model, snapshot)
        if 'atr-trail' in selected:
            owner = model.position_campaign
            if owner is not None and owner > 0 and D(snapshot['quantity_btc']) > 0:
                if model.trail is None or model.trail['campaign'] != owner:
                    # Start at the confirmed actual entry, never a pre-entry bar high.
                    model.trail = {'campaign': owner, 'confirmed_at_ms': int(reader.clock()*1000),
                                   'high': snapshot['entry']}
            else:
                model.trail = None
            state.set('linear_campaign', model.checkpoint())
        return result

    def decide(engine, model, snapshot):
        protection = engine.state.get('position_protection')
        if ('atr-trail' in selected and model.position_campaign is not None and model.position_campaign > 0
                and D(snapshot['quantity_btc']) > 0 and protection and model.trail and
                protection['campaign'] == model.position_campaign and
                model.trail['campaign'] == model.position_campaign and len(model.model.tr) == 14):
            model.decision_stop = max(D(protection['stop']), D(model.trail['high'])-3*sum(model.model.tr)/14)
        active = model.active
        trigger = (model.trigger if active.identity > 0 else model.macro_trigger) if active else None
        created_at = (active.identity if active.identity > 0 else trigger['created_at_ms']) if active else None
        decision_at = int(engine.reader.clock()*1000)
        event = {'event': 'decision', 'at_ms': decision_at, 'bar_ms': model.last,
                 'opportunity': active.identity if active else None,
                 'age_ms': decision_at-created_at if active else None,
                 'trigger': deepcopy(trigger),
                 'decision_mark': snapshot['mark_price'], 'quantity_before': snapshot['quantity_btc'],
                 'idle_cash_usdt': snapshot.get('available_usdt'), 'wallet_usdt': snapshot.get('wallet_usdt'),
                 'desired_stop': str(model.decision_stop) if model.decision_stop is not None else None,
                 'risk_scale': str(model.scale if model.decision_ms >= CUTOFF else D(1))}
        journal.append(event)
        try:
            action, after = original_decide(engine, model, snapshot)
            event.update(action=action, reason=model.reason or action, quantity_after=after['quantity_btc'],
                         constraint=engine.entry_constraint)
            return action, after
        except session.RECOVERABLE as exc:
            event.update(reason=str(exc), error=type(exc).__name__)
            raise

    def top_up(engine, model, snapshot):
        if 'single-topup' in selected and model.active and confirmed_topup(engine.state, model.active.identity, model.last):
            journal.append({'event': 'topup_blocked', 'at_ms': int(engine.reader.clock()*1000),
                            'opportunity': model.active.identity, 'reason': 'one_confirmed_add_per_bar'})
            return snapshot
        return original_topup(engine, model, snapshot)

    def send(engine, method, path, payload):
        identity = payload.get('newClientOrderId', payload.get('clientAlgoId', payload.get('origClientOrderId')))
        link = (engine.state.get('entry_campaigns') or {}).get(identity, {})
        if 'single-topup' in selected and link.get('add') and method == 'POST':
            row = engine.state.db.execute('SELECT result FROM intents WHERE id=?', (identity,)).fetchone()
            attempted = engine.state.get('alpha_topup_attempts') or {}
            # Lifecycle settles over its transient result; preserve this original
            # causal bar/position anchor before sending, including unknown replies.
            attempted.setdefault(identity, json.loads(row[0]))
            engine.state.set('alpha_topup_attempts', attempted)
        journal.append({'event': 'write_attempt', 'at_ms': int(engine.reader.clock()*1000),
                        'method': method, 'path': path, 'identity': identity,
                        'opportunity': link.get('campaign'), 'payload': dict(payload)})
        return original_send(engine, method, path, payload)

    def cycle(reader, state, uid, **kwargs):
        nonlocal cycle_sequence
        cycle_sequence += 1
        try:
            return original_cycle(reader, state, uid, **kwargs)
        except session.RECOVERABLE as exc:
            journal.append({'event': 'cycle_blocked', 'at_ms': int(reader.clock()*1000),
                            'session_ms': kwargs.get('session'), 'cycle_sequence': cycle_sequence, 'phase': 'cycle',
                            'reason': str(exc), 'error': type(exc).__name__})
            raise

    def observe_plan(original, kind):
        def wrapped(reader, model, snapshot, *args, **kwargs):
            plan = original(reader, model, snapshot, *args, **kwargs)
            journal.append({'event': kind, 'at_ms': int(reader.clock()*1000),
                'opportunity': model.active.identity, 'desired_btc': plan.get('requested_btc', args[0] if args else None),
                'accepted_btc': plan['quantity_btc'], 'constraint': plan['constraint'],
                'entry_estimate': plan['entry_estimate'], 'sizing_capital_usdt': plan.get('sizing_capital_usdt'),
                'allocated_margin_usdt': plan.get('allocated_margin_usdt')})
            return plan
        return wrapped

    with ExitStack() as stack:
        for obj, key, value in (
            (campaign, 'Campaign', AlphaCampaign), (linear_preview, 'Campaign', AlphaCampaign),
            (AlphaCampaign, 'components', selected), (AlphaCampaign, 'binding', binding),
            (AlphaCampaign, 'scale', D(profile.get('scale', '1'))), (AlphaCampaign, 'journal', journal),
            (ownership, 'reconcile', reconcile), (session, 'reconcile', reconcile), (session, 'cycle', cycle),
            (lifecycle.Lifecycle, 'decide', decide), (lifecycle.Lifecycle, 'top_up', top_up),
            (lifecycle.Lifecycle, 'send', send),
            (lifecycle, 'entry_preview', observe_plan(lifecycle.entry_preview, 'entry_sizing')),
            (lifecycle, 'topup_preview', observe_plan(lifecycle.topup_preview, 'topup_sizing'))):
            stack.enter_context(patch.object(obj, key, value))
        yield


def record_session_phases(journal, report, reported_at_ms):
    # Cycle failures were recorded once at their actual failure time. Other
    # bounded report phases have no event clock; label their report-time summary.
    for error in report.get('errors', []):
        if error['phase'] != 'cycle':
            journal.append({'event': 'session_phase_summary', 'at_ms': reported_at_ms,
                'timestamp_basis': 'session_report_completed',
                'session_ms': report['session_started_at_ms'], **error})


class NoCrowding:
    """The four registered mechanisms consume no funding/basis feature file."""
    def __init__(self, _path):
        self.sha256 = meter.checksum(None)
        self.source = 'not used by alpha/beta mechanisms'
        self.coverage = Counter()


def measure(args):
    names = [args.candidate] if args.candidate else list(CANDIDATES)
    if args.combo:
        names = ['+'.join(components(args.combo.replace(',', '+')))]
        if len(components(names[0])) < 2:
            raise ValueError('a combination requires at least two registered mechanisms')
    profiles, risk_hash = calibration(args.risk_calibration, names)
    scenarios = {k: v for k, v in meter.SCENARIOS.items() if args.scenario is None or k == args.scenario}
    original_schedule = session_schedule.load()
    import copy
    schedule = copy.deepcopy(original_schedule)
    schedule['primary']['starts_ms'] = [v+args.start_offset_ms for v in schedule['primary']['starts_ms']]
    binding = {'measured_source': rebuild.source_identity(), 'spec_sha256': file_hash(SPEC), 'protocol_sha256': file_hash(PROTOCOL),
               'risk_calibration_sha256': risk_hash, 'initial_cny': str(args.initial_cny),
               'start_offset_ms': args.start_offset_ms,
               'original_schedule_sha256': original_schedule['primary']['sha256'],
               'actual_starts_sha256': meter.checksum(schedule['primary']['starts_ms'])}
    ledgers, exchanges = {}, {}
    current = {}
    original_run = meter.run

    @contextmanager
    def scoped(name, _crowding):
        current['name'] = name
        yield  # run below binds the per-account journal before creating a model

    def run(config, exchange, **kwargs):
        uid = exchange.uid
        ledger = ledgers.setdefault(uid, [])
        exchanges[uid] = exchange
        name = current['name']
        with variant(name, binding=binding, profile=profiles.get(name), journal=ledger):
            report = original_run(config, exchange, **kwargs)
        record_session_phases(ledger, report, int(exchange.clock()*1000))
        return report

    shared = SimpleNamespace(**vars(args), crowding=None, portfolio_budgets=False, portfolio_selected=None)
    with ExitStack() as stack:
        for obj, key, value in ((meter, 'CANDIDATES', names), (meter, 'SCENARIOS', scenarios),
                (meter, 'Crowding', NoCrowding), (meter, 'variant', scoped), (meter, 'run', run),
                (session_schedule, 'load', lambda: schedule),
                (meter, 'select', lambda _: {'production_promoted': False, 'native_execution_verified': False,
                                           'selection_pending': 'independent complete matched-risk analysis'})):
            stack.enter_context(patch.object(obj, key, value))
        output = meter.measure(shared)
    for i, name in enumerate(names):
        for j, scenario in enumerate(scenarios):
            uid = 12000+i*4+j
            ledger, exchange = ledgers.get(uid, []), exchanges.get(uid)
            if exchange is not None:
                # Diagnosis is attached only after every session/final audit has run.
                # These future completed closes are not attainable missed fills.
                for event in ledger:
                    if event['event'] == 'opportunity':
                        event['post_run_diagnostic_closes'] = {}
                        for days in (5, 20):
                            end = event['at_ms']+days*86400000
                            # Macro creation is intrabar: use the last completed
                            # 4h close at the diagnostic horizon, without lookahead.
                            completed = end//FOUR_HOURS*FOUR_HOURS
                            bar = exchange.market.bar4(completed-FOUR_HOURS)
                            event['post_run_diagnostic_closes'][str(days)] = {
                                'at_ms': completed, 'horizon_ms': end, 'close': str(bar[3]) if bar else None}
                orders = {str(v['orderId']): v for v in exchange.orders.values()}
                triggers = {str(v.get('actualOrderId')): v for v in exchange.algos.values()
                            if v.get('actualOrderId') not in (None, '0')}
                for trade in exchange.trades:
                    order = orders.get(str(trade['orderId']), {})
                    ledger.append({'event': 'fill', 'at_ms': trade['time'], 'trade': trade,
                                   'exit_type': (triggers.get(str(trade['orderId']), {}).get('orderType') or
                                                 order.get('type', 'liquidation_or_unclassified'))
                                                if trade['side'] == 'SELL' else None,
                                   'client_order_id': order.get('clientOrderId')})
            ledger.sort(key=lambda v: v.get('at_ms', v.get('session_ms', 0)))
            output['results'][name][scenario]['opportunity_ledger'] = ledger
    output['inputs'].update(binding, candidates={n: list(components(n)) for n in names},
                            risk_profiles=profiles, original_meter_protocol_sha256=output['inputs']['protocol_sha256'])
    output['inputs']['protocol_sha256'] = binding['protocol_sha256']
    output['conditions'].update(qualification='NOT_QUALIFIED', alpha_beta_research=True,
                                post_run_diagnostic_prices_used_for_decisions=False)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--market', type=Path, default=Path('/tmp/coinquant-market'))
    parser.add_argument('--prints', type=Path, default=Path('/workspace/.btc-third-round-prints'))
    parser.add_argument('--fx', type=Path, default=Path('/workspace/starquant/data/usdcny_frankfurter.json'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--candidate', choices=CANDIDATES)
    parser.add_argument('--scenario', choices=tuple(meter.SCENARIOS))
    parser.add_argument('--combo', help='Comma-separated registered compatible components; no subset search')
    parser.add_argument('--risk-calibration', type=Path)
    parser.add_argument('--initial-cny', type=D, default=D(10000))
    parser.add_argument('--start-offset-ms', type=int, choices=(-60000, 0, 60000), default=0)
    parser.add_argument('--restore-prints', action='store_true')
    args = parser.parse_args(argv)
    if args.combo and args.candidate:
        parser.error('choose candidate or combo')
    if not args.initial_cny.is_finite() or args.initial_cny not in (D(9900), D(10000), D(10100)):
        parser.error('initial CNY must be registered 9900, 10000, or 10100')
    if (args.start_offset_ms or args.initial_cny != 10000) and (args.scenario != 'base' or not (args.candidate or args.combo)):
        parser.error('capital/start diagnostics require one fixed candidate and --scenario base')
    if args.out.suffix not in ('.json', '.gz'):
        parser.error('output must be JSON or lossless .json.gz')
    if args.out.suffix == '.gz' and not args.out.name.endswith('.json.gz'):
        parser.error('compressed output must end in .json.gz')
    if args.out.exists() or args.out.with_suffix('.progress.json').exists():
        parser.error('never overwrite results or progress')
    if args.limit is not None and (not 1 <= args.limit <= 795 or not args.out.resolve().is_relative_to('/tmp')):
        parser.error('incomplete smoke limit must be 1..795 and output under /tmp')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    output = measure(args)
    opener = gzip.open if args.out.suffix == '.gz' else open
    with opener(args.out, 'xt', encoding='utf-8') as stream:
        json.dump(output, stream, default=str, allow_nan=False)
        stream.write('\n')
    rows = [row for scenarios in output['results'].values() for row in scenarios.values()]
    return 2 if any(r['failure'] or not r['audit']['passed'] for r in rows) else 0


if __name__ == '__main__':
    raise SystemExit(main())
