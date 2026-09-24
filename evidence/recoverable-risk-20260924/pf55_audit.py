"""Reproduce PF55 budget exhaustion from its complete account original."""
import argparse
import csv
import gzip
import json
from bisect import bisect_right
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path


def audit(root):
    parents = json.loads((root / 'execution_summary.json').read_text())['parents']
    with gzip.open(root / 'equity.csv.gz', 'rt') as stream:
        equity = list(csv.DictReader(stream))
    times, peaks, flat = [], [], []
    peak = D(0)
    for row in equity:
        peak = max(peak, D(row['equity_usdt']))
        times.append(int(row['time']))
        peaks.append(peak)
        if D(row['quantity']) == 0 and row['event'] in ('open', 'close'):
            flat.append(row)
    with gzip.open(root / 'orders.csv.gz', 'rt') as stream:
        orders = list(csv.DictReader(stream))
    filled = [p for p in parents if D(p['filled']) > 0]
    last = filled[-1]
    last_flat_before = next(r for r in reversed(flat) if int(r['time']) <= last['call_time'])
    first_flat_after = next(r for r in flat if int(r['time']) > last['last_fill'])
    before = D(last_flat_before['equity_usdt'])
    after = D(first_flat_after['equity_usdt'])
    call_peak = peaks[bisect_right(times, last['call_time']) - 1]
    # PF55 froze this budget at the call; the remainder cannot grow while flat.
    frozen = D(last['risk_budget'])
    final = D(flat[-1]['equity_usdt'])
    final_peak = peaks[-1]
    assert final == after
    assert abs(final - D('.55') * final_peak - D(parents[-1]['risk_budget'])) < D('.00000001')
    assert all(p['filled'] == '0' for p in parents[parents.index(last)+1:])
    post = [o for o in orders if int(o['time']) >= last['first_fill']]
    return {
        'parents': len(parents), 'filled_parents': len(filled),
        'last_fill_utc': datetime.fromtimestamp(last['first_fill']/1000, timezone.utc).isoformat(),
        'last_exit_utc': datetime.fromtimestamp(int(first_flat_after['time'])/1000, timezone.utc).isoformat(),
        'last_parent_budget_usdt': str(frozen), 'last_entry_equity_usdt': str(before),
        'last_exit_equity_usdt': str(after), 'last_trade_net_equity_change_usdt': str(after-before),
        'high_water_before_last_entry_usdt': str(call_peak),
        'post_fill_order_events': post[-5:],
        'final_equity_usdt': str(final), 'final_high_water_usdt': str(final_peak),
        'final_spendable_budget_usdt': str(final - D('.55')*final_peak),
        'remaining_unfilled_parents': len(parents)-parents.index(last)-1,
        'flat_after_last_exit': all(D(r['quantity']) == 0 for r in equity if int(r['time']) >= int(first_flat_after['time'])),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('original', type=Path)
    print(json.dumps(audit(parser.parse_args().original), indent=2))
