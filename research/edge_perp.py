"""Registered edge mechanisms through the unchanged finite perpetual meter."""
import argparse
from collections import Counter, deque
from contextlib import ExitStack, contextmanager
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal as D
import gzip
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from coinquant import campaign, lifecycle, linear_preview
from coinquant.types import Blocked
from research import alpha_perp as alpha, complete_perp as meter, rebuild, session_schedule
from research.edge_features import FeatureBook, _read, _digest

DAY = 86400000
BAR = alpha.FOUR_HOURS
CUTOFF = alpha.CUTOFF
CANDIDATES = ('incumbent', 'quality-budget', 'cost-horizon', 'crowding-interaction')
SPEC = Path(__file__).with_name('edge_spec.json')
PROTOCOL = Path(__file__).with_name('edge-PROTOCOL.md')
FEATURE_SHA256 = 'bf920626cc13653b8bbeafd171650cc1a76888e15aad0c20bbd1061fb41da512'
file_hash = alpha.file_hash
_load_frozen_schedule = session_schedule.load


def components(name):
    values = name.replace(',', '+').split('+') if name != 'incumbent' else []
    if any(v not in CANDIDATES[1:] for v in values) or len(set(values)) != len(values):
        raise ValueError('unknown or duplicate registered component')
    return tuple(v for v in CANDIDATES[1:] if v in values)


def calibration(path, names):
    if path is None:
        return {}, None
    body = _read(Path(path).read_bytes())
    if (set(body) != {'format', 'project_kind', 'cutoff_ms', 'baseline_candidate', 'spec_sha256', 'profiles'} or
            type(body['format']) is not int or body['format'] != 1 or body['project_kind'] != 'perp' or
            type(body['cutoff_ms']) is not int or body['cutoff_ms'] != CUTOFF or
            body['baseline_candidate'] != 'incumbent' or body['spec_sha256'] != file_hash(SPEC)):
        raise ValueError('risk calibration schema, project, baseline, cutoff or spec mismatch')
    profiles = body['profiles']
    # A project document contains all four singles; a fixed combination may be added.
    expected = set(CANDIDATES) | {n for n in names if len(components(n)) > 1}
    if not isinstance(profiles, dict) or set(profiles) != expected:
        raise ValueError('missing, extra or foreign risk profiles')
    for name, profile in profiles.items():
        if (set(profile) != {'candidate', 'project_kind', 'scale', 'effective_from_ms',
                'calibration_end_ms', 'training_end_day_exclusive', 'baseline_candidate', 'base_bundle_sha256'} or
                profile['candidate'] != name or profile['project_kind'] != 'perp' or
                profile['baseline_candidate'] != 'incumbent' or
                type(profile['effective_from_ms']) is not int or profile['effective_from_ms'] != CUTOFF or
                type(profile['calibration_end_ms']) is not int or profile['calibration_end_ms'] != CUTOFF or
                profile['training_end_day_exclusive'] != '2022-01-01' or not isinstance(profile['scale'], str)):
            raise ValueError('invalid candidate risk calibration')
        _digest(profile['base_bundle_sha256'])
        scale = D(profile['scale'])
        if not scale.is_finite() or not 0 <= scale <= 1 or (name == 'incumbent' and scale != 1):
            raise ValueError('invalid risk scale')
    return profiles, file_hash(path)


def registered_sessions(binding):
    frozen = _load_frozen_schedule()
    offset = binding.get('start_offset_ms')
    if type(offset) is not int or offset not in (-60000, 0, 60000):
        raise ValueError('invalid registered session offset')
    starts = [stamp+offset for stamp in frozen['primary']['starts_ms']]
    if (binding.get('original_schedule_sha256') != frozen['primary']['sha256'] or
            binding.get('actual_starts_sha256') != meter.checksum(starts)):
        raise ValueError('extension session schedule binding mismatch')
    return {stamp: stamp+frozen['session_seconds']*1000 for stamp in starts}


class EdgeCampaign(alpha.AlphaCampaign):
    features = None
    session_deadlines = {}

    def __init__(self):
        super().__init__()
        self.closes = deque(maxlen=20)
        self.extension = None
        self.rules = {}
        self.cost_exit = False

    def update(self, end, high, low, close):
        result = super().update(end, high, low, close)
        self.closes.append(D(close))
        if self.extension and (result is None or result.identity != self.extension['campaign']):
            self.extension = None
        return result

    def signals(self):
        values = list(self.closes)
        return {'momentum': None if len(values) < 7 else values[-1] > values[-7],
                'trend': None if len(values) < 20 else values[-1] > sum(values)/20}

    def evaluate(self):
        signal = self.signals()
        factor, missing, features = D(1), [], {}
        active = self.active
        primary = active is not None and active.identity > 0
        fresh = primary and self.position_campaign is None and active.identity != self.primary_consumed
        for name in ('funding', 'basis'):
            needed = ((name == 'funding' and 'cost-horizon' in self.components) or
                      (fresh and 'crowding-interaction' in self.components))
            if needed:
                value = self.features.value(name, self.decision_ms)
                features[name] = deepcopy(self.features.last_lookup)
                if value is None:
                    missing.append(name)
        if fresh and 'quality-budget' in self.components:
            trigger = self.trigger
            if (not trigger or trigger['identity'] != active.identity or trigger['prior_atr'] is None or
                    signal['trend'] is None or signal['momentum'] is None):
                missing.append('quality_history_or_trigger')
            elif not (signal['trend'] and signal['momentum'] and
                      self.decision_mark >= D(trigger['close'])-D('.5')*D(trigger['prior_atr'])):
                factor *= D('.5')
        if fresh and 'crowding-interaction' in self.components:
            if signal['momentum'] is None:
                missing.append('momentum_history')
            elif not any(k in missing for k in ('funding', 'basis')) and (
                    D(features['funding']['value']) > D('.0003') and
                    D(features['basis']['value']) > D('.01') and not signal['momentum']):
                factor *= D('.5')
        blocked = fresh and (('quality-budget' in self.components and 'quality_history_or_trigger' in missing) or
                            ('crowding-interaction' in self.components and bool(missing)))
        self.rules = {'signals': signal, 'factor': str(factor), 'features': features,
                      'missing': missing, 'blocked_primary_new_risk': bool(blocked)}
        return self.rules

    def select_macro(self, row, mark, call, *, bootstrap=False):
        super().select_macro(row, mark, call, bootstrap=bootstrap)
        self.cost_exit = False
        self.evaluate()

    def action(self, quantity):
        action = super().action(quantity)
        if action == 'hold' and self.cost_exit:
            self.reason = 'cost_horizon_weak_momentum_high_known_funding'
            return 'exit'
        if action == 'enter' and self.rules.get('blocked_primary_new_risk'):
            self.reason = 'missing_primary_edge_inputs'
            return 'flat'
        return action

    def entry_fraction(self, friction):
        # Lifecycle top_up consumes its durable requested target, never this fraction.
        fraction = super().entry_fraction(friction)
        if self.active is not None and self.active.identity > 0 and self.position_campaign is None:
            fraction *= D(self.rules.get('factor', '1'))
        return fraction

    def prepare_decision(self, engine, snapshot):
        now = int(engine.reader.clock()*1000)
        self.decision_ms, self.decision_mark = now, D(snapshot['mark_price'])
        self.cost_exit = False
        self.evaluate()
        quantity = D(snapshot['quantity_btc'])
        legal = (engine.authorized and engine.session is not None and
                 engine.session <= now < engine.session+300000 and engine.may_enter())
        if ('cost-horizon' not in self.components or not legal or quantity <= 0 or
                super().action(quantity) != 'hold'):
            return
        funding = self.rules['features'].get('funding', {}).get('value')
        signal = self.rules['signals']
        if funding is None:
            return
        if signal['momentum'] is False and D(funding) > D('.0003'):
            self.cost_exit = True
            return
        active = self.active
        if (active.identity > 0 and self.position_campaign == active.identity and self.extension is None and
                5*DAY <= now-active.identity < 7*DAY and active.expires == active.identity+7*DAY and
                engine.session in self.session_deadlines and
                now < self.session_deadlines[engine.session] and self.last <= now < self.last+BAR and
                signal['trend'] and signal['momentum'] and D(funding) <= D('.0003') and
                active.stop < self.decision_mark < active.take):
            self.extension = {'campaign': active.identity, 'decision_at_ms': now,
                'session_ms': engine.session, 'session_deadline_ms': self.session_deadlines[engine.session], 'owned_campaign': self.position_campaign,
                'old_expiry_ms': active.expires, 'new_expiry_ms': active.identity+10*DAY,
                'binding': self.binding, 'features': deepcopy(self.rules['features']),
                'closes': list(map(str, self.closes)), 'bar_ms': self.last,
                'decision_mark': str(self.decision_mark), 'stop': str(active.stop), 'take': str(active.take)}
            self.model.active = replace(active, expires=self.extension['new_expiry_ms'])
            engine.state.set('linear_campaign', self.checkpoint())
            self.journal.append({'event': 'horizon_extension', 'at_ms': now, **deepcopy(self.extension)})

    def checkpoint(self):
        saved = super().checkpoint()
        saved['body']['edge'] = {'closes': list(map(str, self.closes)), 'extension': self.extension}
        saved['sha256'] = meter.checksum(saved['body'])
        return saved

    @classmethod
    def restore(cls, saved):
        try:
            body = deepcopy(saved['body'])
            if saved['sha256'] != meter.checksum(body):
                raise ValueError('digest')
            extra = body.pop('edge')
            if set(extra) != {'closes', 'extension'}:
                raise ValueError('edge fields')
            result = super().restore({'body': body, 'sha256': meter.checksum(body)})
            closes = [D(v) for v in extra['closes']]
            if len(closes) != min(20, (result.last-campaign.ORIGIN)//BAR) or any(not v.is_finite() or v <= 0 for v in closes):
                raise ValueError('completed close history')
            if closes and closes[-1] != result.model.close:
                raise ValueError('completed close boundary')
            result.closes = deque(closes, maxlen=20)
            result.extension = extra['extension']
            active = result.model.active
            if result.extension is not None:
                event = result.extension
                expected_keys = {'campaign', 'decision_at_ms', 'session_ms', 'session_deadline_ms', 'owned_campaign', 'old_expiry_ms',
                    'new_expiry_ms', 'binding', 'features', 'closes', 'bar_ms', 'decision_mark', 'stop', 'take'}
                if not isinstance(event, dict) or set(event) != expected_keys or 'cost-horizon' not in cls.components:
                    raise ValueError('extension fields')
                for key in ('campaign', 'decision_at_ms', 'session_ms', 'session_deadline_ms', 'owned_campaign', 'old_expiry_ms', 'new_expiry_ms', 'bar_ms'):
                    if type(event[key]) is not int:
                        raise ValueError('extension clock')
                identity, now = event['campaign'], event['decision_at_ms']
                values = [D(v) for v in event['closes']]
                if (active is None or active.identity != identity or identity <= 0 or
                        event['owned_campaign'] != identity or event['binding'] != cls.binding or
                        event['old_expiry_ms'] != identity+7*DAY or event['new_expiry_ms'] != identity+10*DAY or
                        active.expires != event['new_expiry_ms'] or not 5*DAY <= now-identity < 7*DAY or
                        event['session_ms'] not in cls.session_deadlines or
                        event['session_deadline_ms'] != cls.session_deadlines[event['session_ms']] or
                        not event['session_ms'] <= now < event['session_deadline_ms'] or
                        event['bar_ms'] % BAR or not event['bar_ms'] <= now < event['bar_ms']+BAR or
                        event['bar_ms'] > result.last or len(values) != 20 or
                        any(not v.is_finite() or v <= 0 for v in values) or
                        not (values[-1] > sum(values)/20 and values[-1] > values[-7]) or
                        D(event['stop']) != active.stop or D(event['take']) != active.take or
                        not active.stop < D(event['decision_mark']) < active.take):
                    raise ValueError('extension provenance')
                funding = cls.features.value('funding', now)
                if (funding is None or funding > D('.0003') or
                        event['features'] != {'funding': cls.features.last_lookup}):
                    raise ValueError('extension source feature')
            elif active is not None and active.expires != active.identity+7*DAY:
                raise ValueError('unproven expiry')
            return result
        except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
            raise Blocked('invalid edge checkpoint') from exc


@contextmanager
def variant(name, *, features, binding, legacy_binding=None, profile=None, journal=None):
    selected = components(name)
    deadlines = registered_sessions(binding) if 'cost-horizon' in selected else {}
    profile = profile or {}
    journal = journal if journal is not None else []
    identity = {'candidate': name, 'components': list(selected), 'binding': binding,
                'features_sha256': features.sha256, 'profile': profile,
                'spec_sha256': file_hash(SPEC), 'protocol_sha256': file_hash(PROTOCOL)}
    digest = meter.checksum(identity)
    original_init = lifecycle.Lifecycle.__init__

    def initialize(engine, reader, state, *args, **kwargs):
        # Pure local validation precedes even settle(), recovery and final cleanup.
        stored = state.get('edge_identity')
        saved = state.get('linear_campaign')
        if stored is not None and stored != identity or (saved is not None and stored is None):
            raise Blocked('edge account identity mismatch before recovery')
        if saved is not None:
            campaign.Campaign.restore(saved)
        if stored is None:
            state.set('edge_identity', identity)
        original_init(engine, reader, state, *args, **kwargs)

    with alpha.variant('incumbent', binding=legacy_binding, profile=profile, journal=journal), ExitStack() as stack:
        stack.enter_context(patch.object(lifecycle.Lifecycle, '__init__', initialize))
        original_decide = lifecycle.Lifecycle.decide
        if not selected:
            def incumbent_decide(engine, model, snapshot):
                index = len(journal)
                try:
                    return original_decide(engine, model, snapshot)
                finally:
                    completed = int(engine.reader.clock()*1000)
                    decisions = [e for e in journal[index:] if e['event'] == 'decision']
                    for event in decisions:
                        journal.append({'event': 'decision_completion', 'at_ms': completed,
                            'decision_at_ms': event['at_ms'], 'opportunity': event['opportunity'],
                            'after_return': {k: event[k] for k in ('action', 'reason', 'quantity_after', 'constraint', 'error') if k in event}})
            stack.enter_context(patch.object(lifecycle.Lifecycle, 'decide', incumbent_decide))
        if selected:

            def decide(engine, model, snapshot):
                model.prepare_decision(engine, snapshot)
                started = int(engine.reader.clock()*1000)
                journal.append({'event': 'edge_predecision', 'at_ms': started,
                    'bar_ms': model.last, 'opportunity': model.active.identity if model.active else None,
                    'mark': snapshot['mark_price'], 'quantity_before': snapshot['quantity_btc'],
                    'closes': list(map(str, model.closes)), 'trigger': deepcopy(model.trigger),
                    'rules': deepcopy(model.rules), 'cost_exit': model.cost_exit, 'binding': digest})
                index = len(journal)
                try:
                    return original_decide(engine, model, snapshot)
                finally:
                    # The inherited journal retains original predecision stamps;
                    # explicitly date its after-return fields and errors.
                    completed = int(engine.reader.clock()*1000)
                    for event in journal[index:]:
                        if event['event'] == 'decision':
                            event['completed_at_ms'] = completed
                            event['after_return_fields'] = ['action', 'reason', 'quantity_after', 'constraint', 'error']

            for obj, key, value in ((campaign, 'Campaign', EdgeCampaign), (linear_preview, 'Campaign', EdgeCampaign),
                    (EdgeCampaign, 'components', selected), (EdgeCampaign, 'binding', digest),
                    (EdgeCampaign, 'features', features), (EdgeCampaign, 'session_deadlines', deadlines),
                    (lifecycle.Lifecycle, 'decide', decide)):
                stack.enter_context(patch.object(obj, key, value))
        yield identity


def measure(args):
    names = [args.candidate] if args.candidate else list(CANDIDATES)
    if args.combo:
        selected = components(args.combo)
        if len(selected) < 2:
            raise ValueError('a fixed combination requires at least two registered components')
        names = ['+'.join(selected)]
    profiles, risk_hash = calibration(args.risk_calibration, names)
    features = FeatureBook(args.features, expected_sha256=FEATURE_SHA256)
    source = rebuild.source_identity()
    if source['dirty']:
        raise ValueError('commit research and production sources before measurement')
    scenarios = {k: v for k, v in meter.SCENARIOS.items() if args.scenario is None or k == args.scenario}
    original_schedule = session_schedule.load()
    schedule = deepcopy(original_schedule)
    schedule['primary']['starts_ms'] = [v+args.start_offset_ms for v in schedule['primary']['starts_ms']]
    legacy_binding = {'measured_source': source, 'spec_sha256': file_hash(alpha.SPEC),
        'protocol_sha256': file_hash(alpha.PROTOCOL), 'risk_calibration_sha256': risk_hash,
        'initial_cny': str(args.initial_cny), 'start_offset_ms': args.start_offset_ms,
        'original_schedule_sha256': original_schedule['primary']['sha256'],
        'actual_starts_sha256': meter.checksum(schedule['primary']['starts_ms'])}
    binding = {'measured_source': source, 'spec_sha256': file_hash(SPEC), 'protocol_sha256': file_hash(PROTOCOL),
        'feature_file_sha256': features.sha256, 'feature_source': features.source,
        'feature_reader_sha256': file_hash(Path(__file__).with_name('edge_features.py')),
        'risk_calibration_sha256': risk_hash, 'risk_profiles': profiles,
        'risk_calibration_document': None if args.risk_calibration is None else Path(args.risk_calibration).read_text(),
        'initial_cny': str(args.initial_cny), 'start_offset_ms': args.start_offset_ms,
        'original_schedule_sha256': original_schedule['primary']['sha256'],
        'actual_starts_sha256': meter.checksum(schedule['primary']['starts_ms'])}
    ledgers, exchanges, current = {}, {}, {}
    original_run = meter.run

    @contextmanager
    def scoped(name, _crowding):
        current['name'] = name
        yield

    def run(config, exchange, **kwargs):
        name, uid = current['name'], exchange.uid
        ledger = ledgers.setdefault(uid, [])
        exchanges[uid] = exchange
        with variant(name, features=features, binding=binding, legacy_binding=legacy_binding,
                     profile=profiles.get(name), journal=ledger):
            report = original_run(config, exchange, **kwargs)
        alpha.record_session_phases(ledger, report, int(exchange.clock()*1000))
        return report

    shared = SimpleNamespace(**vars(args), crowding=None, portfolio_budgets=False, portfolio_selected=None)
    tapes = []
    with ExitStack() as stack:
        if args.restore_prints:
            from research.edge_prints import VerifiedPrints
            def tape(root):
                value = VerifiedPrints(root)
                tapes.append(value)
                return value
            stack.enter_context(patch.object(meter, 'RollingPrints', tape))
        for obj, key, value in ((meter, 'CANDIDATES', names), (meter, 'SCENARIOS', scenarios),
                (meter, 'Crowding', alpha.NoCrowding), (meter, 'variant', scoped), (meter, 'run', run),
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
                orders = {str(v['orderId']): v for v in exchange.orders.values()}
                triggers = {str(v.get('actualOrderId')): v for v in exchange.algos.values()
                            if v.get('actualOrderId') not in (None, '0')}
                for trade in exchange.trades:
                    order = orders.get(str(trade['orderId']), {})
                    ledger.append({'event': 'fill', 'at_ms': trade['time'], 'trade': trade,
                        'recorded_at_ms': exchange.now_ms, 'timestamp_basis': 'native_trade_time_post_run_extraction',
                        'exit_type': (triggers.get(str(trade['orderId']), {}).get('orderType') or
                            order.get('type', 'liquidation_or_unclassified')) if trade['side'] == 'SELL' else None,
                        'client_order_id': order.get('clientOrderId')})
            ledger.sort(key=lambda v: v.get('at_ms', v.get('session_ms', 0)))
            output['results'][name][scenario]['opportunity_ledger'] = ledger
    output['edge'] = {**binding, 'candidates': {n: list(components(n)) for n in names},
        'original_inputs': deepcopy(output['inputs']), 'original_conditions': deepcopy(output['conditions']),
        'decision_coverage': {name: {scenario: decision_coverage(
            output['results'][name][scenario]['opportunity_ledger'])
            for scenario in scenarios} for name in names},
        'print_restore_receipts': [row for tape in tapes for row in tape.receipts]}
    return output


def decision_coverage(ledger):
    rows = [e for e in ledger if e['event'] == 'edge_predecision']
    return {'actual_decisions': sum(e['event'] == 'decision' for e in ledger),
        'edge_evaluations': len(rows),
        'primary_new_risk_blocked': sum(e['rules']['blocked_primary_new_risk'] for e in rows),
        'missing_inputs': dict(Counter(cause for e in rows for cause in e['rules']['missing'])),
        'feature_lookups': dict(Counter(name+':'+(value['cause'] or 'known')
            for e in rows for name, value in e['rules']['features'].items()))}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--market', type=Path, default=Path('/tmp/coinquant-market'))
    parser.add_argument('--prints', type=Path, default=Path('/tmp/coinquant-edge-prints'))
    parser.add_argument('--fx', type=Path, default=Path('/workspace/starquant/data/usdcny_frankfurter.json'))
    parser.add_argument('--features', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--candidate', choices=CANDIDATES)
    parser.add_argument('--scenario', choices=tuple(meter.SCENARIOS))
    parser.add_argument('--combo', help='All independently eligible registered components, comma separated')
    parser.add_argument('--risk-calibration', type=Path)
    parser.add_argument('--initial-cny', type=D, default=D(10000))
    parser.add_argument('--start-offset-ms', type=int, choices=(-60000, 0, 60000), default=0)
    parser.add_argument('--restore-prints', action='store_true')
    args = parser.parse_args(argv)
    if args.combo and args.candidate:
        parser.error('choose candidate or fixed combo')
    if not args.initial_cny.is_finite() or args.initial_cny not in (D(2500), D(5000), D(7500), D(10000)):
        parser.error('initial CNY must be registered 2500, 5000, 7500 or 10000')
    if (args.start_offset_ms or args.initial_cny != 10000) and (args.scenario != 'base' or not (args.candidate or args.combo)):
        parser.error('capital/start diagnostics require one fixed candidate and base')
    if not args.out.name.endswith('.json.gz'):
        parser.error('output must end in .json.gz')
    if args.out.exists() or args.out.with_suffix('.progress.json').exists():
        parser.error('never overwrite results or progress')
    if args.limit is not None and (not 1 <= args.limit <= 795 or not args.out.resolve().is_relative_to('/tmp')):
        parser.error('incomplete smoke limit must be 1..795 and output under /tmp')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # Reserve before measurement, so concurrent invocations cannot share an output.
    with args.out.open('xb') as raw:
        output = measure(args)
        with gzip.open(raw, 'wt', encoding='utf-8') as stream:
            json.dump(output, stream, default=str, allow_nan=False)
            stream.write('\n')
    rows = [row for scenarios in output['results'].values() for row in scenarios.values()]
    return 2 if any(r['failure'] or not r['audit']['passed'] for r in rows) else 0


if __name__ == '__main__':
    raise SystemExit(main())
