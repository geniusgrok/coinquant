"""Rebuild PIR1 child identities and join them to frozen calls and fills."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path

from coinquant.opportunities import FOUR_HOURS, Opportunities
from coinquant.research import invocations, spec, timestamp
from research.persistent_hold_replay import inputs

HOUR = 3_600_000


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def build(input_root: Path, account_root: Path, parent_events: Path,
          protocol: Path, output: Path, *, full_window: bool = False) -> dict:
    frozen = spec()
    start = timestamp(frozen['start'])
    end = timestamp(frozen['end' if full_window else 'development_end'])
    series, _, warm, source_identity = inputs(
        input_root/'native', input_root/'warmup', input_root/'repairs',
        full_window=full_window)
    trade = series['klines']
    parent_by_id = {int(row['identity']): row for row in read_jsonl(parent_events)}
    model = Opportunities('post_impulse_restart', FOUR_HOURS)
    bars: dict[int, tuple[D, D, D]] = {}
    signal_at: dict[int, object] = {}
    children = {}

    for begin in range(min(warm), end, FOUR_HOURS):
        source = warm if begin < start else trade
        hourly = [source[t] for t in range(begin, begin+FOUR_HOURS, HOUR)]
        completed = begin+FOUR_HOURS
        high = max(D(row[2]) for row in hourly)
        low = min(D(row[3]) for row in hourly)
        close = D(hourly[-1][4])
        bars[completed] = (high, low, close)
        signal = model.update(completed, high, low, close)
        signal_at[completed] = signal
        if signal and signal.parent_identity is not None and signal.identity == completed:
            context = model.restart_context
            if context is None or not context['emitted']:
                raise ValueError('emitted child lacks frozen restart context')
            parent_id = context['identity']
            pullback_at = context['pullback_at']
            prior_highs = [bar[0] for t, bar in bars.items()
                           if parent_id <= t < pullback_at]
            if not prior_highs:
                raise ValueError('no completed peak bar before pullback')
            peak_before = max(prior_highs)
            parent = parent_by_id.get(parent_id)
            if parent is None:
                raise ValueError('child parent is absent from original event ledger')
            if context['invalidated_at'] != parent['invalidated_at']:
                raise ValueError('child parent invalidation time differs from base event ledger')
            children[signal.identity] = dict(
                identity=signal.identity, parent_identity=parent_id,
                parent_invalidation_time=context['invalidated_at'],
                parent_invalidation_reasons=parent['invalidation_reasons'],
                risk_r=str(context['risk']), peak_before=str(peak_before),
                pullback_at=pullback_at, pullback_high=str(context['pullback_high']),
                pullback_low=str(context['pullback_low']),
                pullback_distance=str(peak_before-context['pullback_low']),
                confirmed_at=completed, confirmation_close=str(close),
                direction=signal.direction, stop=str(signal.stop), take=str(signal.take),
                expires=signal.expires)

    calls = sorted(t for t in invocations(frozen) if start <= t < end)
    by_child_calls = defaultdict(list)
    for t in calls:
        signal = signal_at.get(t//FOUR_HOURS*FOUR_HOURS)
        if signal and signal.parent_identity is not None:
            by_child_calls[signal.identity].append(t)

    execution_path = account_root/'execution.jsonl'
    execution = read_jsonl(execution_path)
    parents = {row['identity']: row for row in children.values()}
    child_ids = set(children)
    mothers = [row for row in execution
               if row.get('kind') == 'mother_created' and row.get('campaign') in child_ids]
    mother_by_campaign = defaultdict(list)
    for row in mothers:
        mother_by_campaign[row['campaign']].append(row)

    for row in children.values():
        intents = mother_by_campaign[row['identity']]
        intent_ids = {item['parent_id'] for item in intents}
        fills = [item for item in execution if item.get('kind') == 'child'
                 and item.get('parent_id') in intent_ids and D(item.get('accepted', '0')) > 0]
        row['active_call_times'] = by_child_calls.get(row['identity'], [])
        row['entry_intent_count'] = len(intents)
        row['entry_filled'] = any(item.get('event') == 'entry' for item in fills)
        row['accepted_child_slices'] = len(fills)
        row['accepted_quantity_total'] = str(sum((D(item['accepted']) for item in fills), D(0)))
        row['intent_terminal_reasons'] = [item.get('terminal_reason') for item in execution
            if item.get('kind') in ('mother_final', 'mother_stop')
            and item.get('parent_id') in intent_ids]
        if (D(row['pullback_distance']) < D(row['risk_r'])
                or not row['parent_invalidation_time'] < row['confirmed_at']
                or D(row['confirmation_close']) <= D(row['pullback_high'])
                or D(row['pullback_low']) != D(row['stop'])):
            raise ValueError('child does not satisfy its frozen causal geometry')

    result = json.loads((account_root/'result.json').read_text())
    expected = {int(item['identity']) for item in result['restart_children']}
    if expected != set(children) or len(children) != result['restart_children_generated']:
        raise ValueError('signal reconstruction differs from the saved account child manifest')
    body = dict(
        protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),
        account_result_sha256=hashlib.sha256((account_root/'result.json').read_bytes()).hexdigest(),
        execution_sha256=hashlib.sha256(execution_path.read_bytes()).hexdigest(),
        source_identity_hash=hashlib.sha256(json.dumps(
            sorted(item['sha256'] for item in source_identity)).encode()).hexdigest(),
        development_calls=len(calls), generated_children=len(children),
        children=[children[key] for key in sorted(children)])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(body, indent=2)+'\n')
    return body


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-root', type=Path, required=True)
    parser.add_argument('--account-root', type=Path, required=True)
    parser.add_argument('--parent-events', type=Path, required=True)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--full-window', action='store_true')
    args = parser.parse_args()
    result = build(args.input_root, args.account_root, args.parent_events,
                   args.protocol, args.output, full_window=args.full_window)
    print(json.dumps({key: result[key] for key in
                      ('development_calls', 'generated_children')}, indent=2))


if __name__ == '__main__':
    main()
