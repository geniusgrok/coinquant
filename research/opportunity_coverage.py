"""Reconcile sparse calls with completed-bar impulse lifecycles.

This is descriptive accounting. Post-invalidation price labels are reported
separately and never participate in the event, call, or account joins.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from decimal import Decimal as D
from pathlib import Path

from coinquant.opportunities import FOUR_HOURS, Opportunities
from coinquant.research import invocations, iso, spec, timestamp
from research.persistent_hold_replay import inputs

HOUR = 3_600_000
DAY = 86_400_000


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(input_root: Path, account_root: Path, output: Path) -> dict:
    frozen = spec()
    start, end = timestamp(frozen['start']), timestamp(frozen['end'])
    series, _, warm, source_identity = inputs(
        input_root/'native', input_root/'warmup', input_root/'repairs', full_window=True)
    trade = series['klines']

    model = Opportunities('impulse_hold', FOUR_HOURS)
    states = {}
    events = {}
    bars = {}
    for begin in range(min(warm), end, FOUR_HOURS):
        source = warm if begin < start else trade
        rows = [source[t] for t in range(begin, begin+FOUR_HOURS, HOUR)]
        high = max(D(row[2]) for row in rows)
        low = min(D(row[3]) for row in rows)
        close = D(rows[-1][4])
        completed = begin+FOUR_HOURS
        bars[completed] = (high, low, close)
        before = model.active
        reasons = []
        if before:
            if before.expires is not None and completed >= before.expires:
                reasons.append('expiry')
            if before.direction > 0:
                if low <= before.stop:
                    reasons.append('stop')
                if high >= before.take:
                    reasons.append('take')
            else:
                if high >= before.stop:
                    reasons.append('stop')
                if low <= before.take:
                    reasons.append('take')
        active = model.update(completed, high, low, close)
        if before and reasons and before.identity in events:
            events[before.identity]['invalidated_at'] = completed
            events[before.identity]['invalidation_reasons'] = reasons
        if active and active.identity == completed and completed >= start:
            events[active.identity] = dict(
                identity=active.identity, direction=active.direction, created_at=completed,
                stop=str(active.stop), take=str(active.take), expires_at=active.expires,
                origin_high=str(high), origin_low=str(low), origin_close=str(close),
                invalidated_at=None, invalidation_reasons=[])
        states[completed] = active

    calls = sorted(t for t in invocations(frozen) if start <= t < end)
    decisions_path = account_root/'decisions.csv.gz'
    orders_path = account_root/'orders.csv.gz'
    with gzip.open(decisions_path, 'rt') as stream:
        decisions = {int(row['time']): row for row in csv.DictReader(stream)}
    with gzip.open(orders_path, 'rt') as stream:
        orders = list(csv.DictReader(stream))
    if len(calls) != len(decisions) or len(calls) != 795:
        raise ValueError('frozen call and saved decision counts differ')

    call_rows = []
    for t in calls:
        opportunity = states.get(t//FOUR_HOURS*FOUR_HOURS)
        decision = decisions[t]
        expected = opportunity.direction if opportunity else 0
        if int(decision['regime']) != expected:
            raise ValueError(f'saved regime mismatch at {iso(t)}')
        call_rows.append(dict(
            time=t, year=iso(t)[:4], identity=opportunity.identity if opportunity else None,
            signal_direction=expected, account_quantity=decision['quantity'],
            action=decision['action'], binding_cap=decision['binding_cap'],
            risk_quantity=decision['risk_quantity'],
            liquidity_quantity=decision['liquidity_quantity']))

    for event in events.values():
        live = [row for row in call_rows if row['identity'] == event['identity']]
        event['valid_call_count'] = len(live)
        event['call_times'] = [row['time'] for row in live]
        event['first_call_time'] = live[0]['time'] if live else None
        event['first_call_delay_hours'] = (
            (live[0]['time']-event['created_at'])/HOUR if live else None)
        event['call_account_actions'] = dict(Counter(row['action'] for row in live))
        event['call_account_states'] = dict(Counter(
            'occupied' if D(row['account_quantity']) else 'flat' for row in live))
        event['first_call_action'] = live[0]['action'] if live else None
        event['first_call_quantity'] = live[0]['account_quantity'] if live else None

        # Explicitly record the first manual call after a completed event has
        # ended. It is not counted as a call to the invalidated parent signal.
        later = next((row for row in call_rows
                      if event['invalidated_at'] is not None
                      and row['time'] > event['invalidated_at']), None)
        event['first_call_after_invalidation'] = later['time'] if later else None
        event['hours_inactive_before_next_call'] = (
            (later['time']-event['invalidated_at'])/HOUR
            if later and event['invalidated_at'] is not None else None)
        event['post_invalidation_call_action'] = later['action'] if later else None
        event['post_invalidation_call_quantity'] = (
            later['account_quantity'] if later else None)

        # Diagnostic only: these future highs/lows never determine eligibility.
        stop_at = event['invalidated_at'] or min(end, event['created_at']+42*FOUR_HOURS)
        label_end = min(end, stop_at+42*FOUR_HOURS)
        future = [value for t, value in bars.items() if stop_at < t <= label_end]
        close0 = D(event['origin_close'])
        if future:
            event['post_invalidation_7d_max_return'] = str(
                max(value[0] for value in future)/close0-1
                if event['direction'] > 0 else close0/min(value[1] for value in future)-1)
            event['post_invalidation_7d_min_return'] = str(
                min(value[1] for value in future)/close0-1
                if event['direction'] > 0 else close0/max(value[0] for value in future)-1)
        else:
            event['post_invalidation_7d_max_return'] = None
            event['post_invalidation_7d_min_return'] = None

    call_cells = Counter((row['action'], row['signal_direction'],
                          'occupied' if D(row['account_quantity']) else 'flat')
                         for row in call_rows)
    call_year = defaultdict(Counter)
    event_year = defaultdict(Counter)
    for row in call_rows:
        call_year[row['year']][row['action']] += 1
    for event in events.values():
        year = iso(event['created_at'])[:4]
        stats = event_year[year]
        stats['events'] += 1
        stats['long' if event['direction'] > 0 else 'short'] += 1
        stats['no_call'] += not bool(event['valid_call_count'])
        stats['at_least_one_call'] += bool(event['valid_call_count'])
        if event['direction'] > 0:
            stats['long_events'] += 1
            stats['long_events_no_call'] += not bool(event['valid_call_count'])
            stats['long_events_account_occupied_first'] += bool(
                event['valid_call_count'] and D(event['first_call_quantity']))

    long_events = [event for event in events.values() if event['direction'] > 0]
    missed = [event for event in long_events if not event['valid_call_count']
              and event['invalidated_at'] is not None
              and 'stop' in event['invalidation_reasons']]
    posthoc = [D(event['post_invalidation_7d_max_return']) for event in missed
               if event['post_invalidation_7d_max_return'] is not None]
    short_calls = sum(row['signal_direction'] < 0 for row in call_rows)
    terminal_reasons = Counter(
        '+'.join(event['invalidation_reasons']) if event['invalidation_reasons'] else 'active_at_end'
        for event in events.values())

    summary = dict(
        input=dict(begin=iso(start), end_exclusive=iso(end), invocations=len(calls),
                   event_count=len(events),
                   event_mechanism='completed 4h abs(close-prior_close)>3*prior ATR14; '
                                   'midpoint stop; far 20R take; 42-bar expiry',
                   status_alignment='all saved call regimes match reconstructed signal direction',
                   invocation_draws_sha256=sha256(Path('research/invocation_draws.json')),
                   spec_sha256=sha256(Path('research/legacy/spec.json')),
                   account_decisions_sha256=sha256(decisions_path),
                   account_orders_sha256=sha256(orders_path),
                   account_inputs_sha256=sha256(account_root/'inputs.json'),
                   market_source_identity=hashlib.sha256(json.dumps(
                       sorted(item['sha256'] for item in source_identity)).encode()).hexdigest()),
        call_actions=[dict(action=key[0], signal_direction=key[1],
                           account_state=key[2], count=value)
                      for key, value in sorted(call_cells.items())],
        call_year={year: dict(counts) for year, counts in sorted(call_year.items())},
        event_year={year: dict(counts) for year, counts in sorted(event_year.items())},
        event_totals=dict(long=len(long_events), short=len(events)-len(long_events),
                          long_no_call=sum(not event['valid_call_count'] for event in long_events),
                          long_completed_no_call_stop=len(missed),
                          long_first_call_overlap=sum(bool(event['valid_call_count']) for event in long_events),
                          terminal_reasons=dict(terminal_reasons)),
        missed_long_next_call=dict(count=len(missed),
            delay_hours=[event['hours_inactive_before_next_call'] for event in missed],
            next_actions=Counter(event['post_invalidation_call_action'] for event in missed),
            flat_after_invalidation=sum(
                D(event['post_invalidation_call_quantity'] or '0') == 0 for event in missed)),
        posthoc_missed_long_7d_labels=dict(
            count=len(posthoc), positive_high_excursion=sum(value > 0 for value in posthoc),
            median_max_return=str(sorted(posthoc)[len(posthoc)//2]) if posthoc else None,
            label='future high/low diagnostic only; not an executable return or a rule-selection input'),
        call_short_only=short_calls,
        existing_orders=dict(rows=len(orders), events=dict(Counter(row['event'] for row in orders))),
        scope='Descriptive opportunity coverage. Parent identity, call-time state and saved account '
              'decisions are joined by frozen timestamp. Future labels are not used for selection.')

    output.mkdir(parents=True, exist_ok=True)
    (output/'summary.json').write_text(json.dumps(summary, indent=2, default=str)+'\n')
    (output/'opportunities.jsonl').write_text(''.join(
        json.dumps(event, default=str)+'\n' for event in events.values()))
    (output/'calls.jsonl').write_text(''.join(
        json.dumps(row)+'\n' for row in call_rows))
    (output/'verified_source_identity.json').write_text(
        json.dumps(source_identity, indent=2)+'\n')
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-root', type=Path, required=True)
    parser.add_argument('--account-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.input_root, args.account_root, args.output), indent=2, default=str))


if __name__ == '__main__':
    main()
