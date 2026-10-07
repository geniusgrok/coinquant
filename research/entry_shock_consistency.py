"""Read-only, aggregate check of the frozen held-shock statistic at entry.

Inputs are the local 50-row original-fill attribution, qualified original UM 4h
ZIPs and zero or more already-paired baseline observation SQLite files. No wallet
or venue is opened; output omits campaign, order and session identifiers.
"""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal as D
import json
from pathlib import Path
import sqlite3

from held_shock_support import DAY, daily_closes


def shock(closes, end):
    dates = [end - i * DAY for i in range(20, -1, -1)]
    if any(date not in closes for date in dates):
        return None
    returns = [closes[b] / closes[a] - 1 for a, b in zip(dates, dates[1:])]
    short = sum((min(value, D(0)) ** 2 for value in returns[-5:]), D(0)) / 5
    long = sum((min(value, D(0)) ** 2 for value in returns), D(0)) / 20
    return bool(long and short > D('2.25') * long)


def wallet_observations(path, closes):
    with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as db:
        rows = [json.loads(row[0]) for row in db.execute(
            'SELECT payload FROM observations ORDER BY sequence')]
    enter = defaultdict(list)
    held = defaultdict(list)
    actions = Counter()
    identities = defaultdict(set)
    for row in rows:
        preview = row.get('model_preview') or {}
        action = preview.get('action')
        if action not in ('enter', 'hold'):
            continue
        opportunity = preview.get('opportunity') or {}
        identity = opportunity.get('identity')
        through = row.get('market_through')
        if type(identity) is not int or type(through) is not int:
            actions['missing_identity_or_clock'] += 1
            continue
        label = shock(closes, through // DAY * DAY)
        key = (identity, row['session_started_at_ms'])
        if action == 'enter':
            enter[key].append((label, row))
        elif D(str((row.get('actual') or {}).get('quantity_btc', '0'))) > 0:
            held[key].append((label, row))
    for (identity, start), cycles in enter.items():
        category = 'macro' if identity < 0 else 'primary'
        labels = {item[0] for item in cycles}
        if len(labels) != 1:
            actions['changed_daily_label_within_session'] += 1
        label = next(iter(labels)) if len(labels) == 1 else None
        suffix = 'source_gap' if label is None else 'shock' if label else 'clear'
        identities[category].add(identity)
        actions[f'{category}_entry_opportunities_{suffix}'] += 1
        actions['entry_poll_cycles'] += len(cycles)
        if len(cycles) > 1:
            actions['repeated_entry_opportunities'] += 1
        if any(D(str((r.get('actual') or {}).get('quantity_btc', '0'))) > 0
               for _, r in cycles):
            actions[f'{category}_filled_opportunities_{suffix}'] += 1
        else:
            actions['entry_opportunity_without_first_fill'] += 1
        actions['entry_cycles_without_first_fill'] += sum(
            D(str((r.get('actual') or {}).get('quantity_btc', '0'))) == 0
            for _, r in cycles)
        if (identity, start) in held and any(s for s, _ in held[identity, start]):
            actions[f'{category}_same_session_shocked_held'] += 1
    for category, values in identities.items():
        actions[f'{category}_distinct_entry_identities'] = len(values)
    return actions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('intervals', type=Path)
    parser.add_argument('h4_dir', type=Path)
    parser.add_argument('observation_sqlites', nargs='*', type=Path)
    args = parser.parse_args()
    intervals = json.loads(args.intervals.read_text())
    if len(intervals) != 50:
        raise ValueError('expected 50 original first fills')
    closes = daily_closes(args.h4_dir)
    counts = Counter()
    net = defaultdict(D)
    for interval in intervals:
        start, first = interval['entry_session_start_ms'], interval['first_ms']
        if start // DAY != first // DAY:
            counts['start_to_first_fill_crossed_utc_day'] += 1
            continue
        label = shock(closes, start // DAY * DAY)
        kind = interval['kind']
        suffix = 'source_gap' if label is None else 'shock' if label else 'clear'
        key = f'{kind}_{suffix}'
        counts[key] += 1
        pnl = D(str(interval['net_usdt']))
        counts[key + ('_winners' if pnl > 0 else '_nonwinners')] += 1
        net[key] += pnl
    result = {'first_fill_counts': dict(sorted(counts.items())),
              'first_fill_net_usdt': {k: str(v.quantize(D('.01'))) for k, v in sorted(net.items())},
              'paired_baseline_observation_counts': {
                  str(i + 1): dict(sorted(wallet_observations(path, closes).items()))
                  for i, path in enumerate(args.observation_sqlites)}}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
