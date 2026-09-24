"""Read-only audit of saved continuous accounts; no counterfactual returns."""
import argparse
import csv
import gzip
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path


def rows(path):
    with gzip.open(path, 'rt') as stream:
        return list(csv.DictReader(stream))


def year(ms):
    return datetime.fromtimestamp(int(ms) / 1000, timezone.utc).year


def audit(root):
    equity, orders, decisions = (rows(root / (name + '.csv.gz'))
                                for name in ('equity', 'orders', 'decisions'))
    result = json.loads((root / 'result.json').read_text())
    summary = json.loads((root / 'execution_summary.json').read_text())
    parents = summary['parents']
    parent_rows = []
    for parent in parents:
        first = parent['first_fill']
        parent_rows.append({
            'call_time': parent['call_time'], 'year': year(parent['call_time']),
            'signal_age_hours': (parent['call_time'] - parent['campaign']) / 3600000,
            'first_fill_delay_minutes': (first - parent['call_time']) / 60000 if first else None,
            'filled_btc': parent['filled'], 'risk_budget_usdt': parent['risk_budget'],
            'terminal_reason': parent['terminal_reason'],
        })
    by_time = defaultdict(list)
    flat = []
    for row in equity:
        by_time[int(row['time'])].append(row)
        if D(row['quantity']) == 0 and row['event'] in ('open', 'close'):
            flat.append(row)
    filled = {int(p['first_fill']): p for p in parents if p['first_fill']}
    previous_flat = D(equity[0]['equity_usdt'])
    flat_index = 0
    before = D(0)
    opened = None
    trades = []
    for order in orders:
        when = int(order['time'])
        while flat_index < len(flat) and int(flat[flat_index]['time']) <= when:
            previous_flat = D(flat[flat_index]['equity_usdt'])
            flat_index += 1
        after = D(order['quantity_after'])
        if before == 0 and after > 0:
            parent = filled.get(when)
            if parent is None:
                raise ValueError('first fill has no parent: ' + str(when))
            opened = (when, previous_flat, parent['call_time'])
        if before > 0 and after == 0:
            if opened is None:
                raise ValueError('exit has no entry: ' + str(when))
            close_rows = [r for r in by_time[when] if D(r['quantity']) == 0
                          and r['event'] != 'conservative_envelope']
            if close_rows:
                exit_equity = D(close_rows[-1]['equity_usdt'])
            elif flat_index < len(flat):
                exit_equity = D(flat[flat_index]['equity_usdt'])
            else:
                raise ValueError('exit has no following flat observation')
            started, balance, call = opened
            trades.append({'entry_time': started, 'call_time': call, 'year': year(started),
                           'holding_hours': (when-started)/3600000,
                           'exit_event': order['event'],
                           'net_usdt': str(exit_equity-balance),
                           'net_over_entry_equity': str((exit_equity-balance)/balance)})
            opened = None
        before = after
    if opened is not None:
        raise ValueError('account ends with an unclosed position')
    initial, final = D(equity[0]['equity_usdt']), D(equity[-1]['equity_usdt'])
    error = final-initial-sum((D(t['net_usdt']) for t in trades), D(0))
    if abs(error) > D('0.000000000000001'):
        raise ValueError('trade/account reconciliation: ' + str(error))
    children = Counter()
    with (root / 'execution.jsonl').open() as stream:
        for line in stream:
            event = json.loads(line)
            if event['kind'] == 'child' and D(event['accepted']) == 0:
                children[event['reason']] += 1
    return {
        'account': root.name, 'result': {k: result.get(k) for k in
            ('cagr', 'mdd_conservative_envelope', 'final_cny', 'fees_usdt',
             'funding_bound_paid_usdt', 'holding_hours')},
        'counts': {'invocations': result['counts']['invocations'],
                   'decision_actions': dict(Counter(x['action'] for x in decisions)),
                   'parents': len(parents), 'filled_parents': sum(D(p['filled']) > 0 for p in parents),
                   'unfilled_child_reasons': dict(children), 'closed_trades': len(trades)},
        'initial_usdt': str(initial), 'final_usdt': str(final),
        'reconciliation_error_usdt': str(error),
        'parents': parent_rows, 'closed_trades': trades,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('accounts', nargs='+', type=Path)
    arguments = parser.parse_args()
    print(json.dumps([audit(p) for p in arguments.accounts], ensure_ascii=False, indent=2))
