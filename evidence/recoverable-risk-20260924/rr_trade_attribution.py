"""Attribute the completed shared account's realized net trades by entry year."""
import argparse
import csv
import gzip
import json
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path


def attribute(root):
    with gzip.open(root/'equity.csv.gz', 'rt') as stream:
        equity = list(csv.DictReader(stream))
    with gzip.open(root/'orders.csv.gz', 'rt') as stream:
        orders = list(csv.DictReader(stream))
    at = defaultdict(list)
    flat = []
    for row in equity:
        at[int(row['time'])].append(row)
        if D(row['quantity']) == 0 and row['event'] in ('open', 'close'):
            flat.append(row)
    totals = defaultdict(lambda: {'trades': 0, 'wins': 0, 'losses': 0, 'net_usdt': D(0)})
    prior = D(0)
    previous_flat = D(equity[0]['equity_usdt'])
    opened = None
    flat_idx = 0
    for order in orders:
        now = int(order['time'])
        while flat_idx < len(flat) and int(flat[flat_idx]['time']) <= now:
            previous_flat = D(flat[flat_idx]['equity_usdt'])
            flat_idx += 1
        after = D(order['quantity_after'])
        if prior == 0 and after > 0:
            opened = (now, previous_flat)
        if prior > 0 and after == 0:
            if opened is None:
                raise ValueError('closed position without a recorded first fill')
            matching = [r for r in at[now] if D(r['quantity']) == 0
                        and r['event'] != 'conservative_envelope']
            if matching:
                exit_equity = D(matching[-1]['equity_usdt'])
            elif flat_idx < len(flat):
                # Some minute exits are followed by the next hourly flat mark.
                exit_equity = D(flat[flat_idx]['equity_usdt'])
            else:
                raise ValueError('no account equity observed after closed exit')
            net = exit_equity - opened[1]
            year = datetime.fromtimestamp(opened[0]/1000,timezone.utc).year
            item = totals[year]
            item['trades'] += 1
            item['wins' if net > 0 else 'losses'] += 1
            item['net_usdt'] += net
            opened = None
        prior = after
    if opened is not None:
        raise ValueError('account ends with unclosed exposure')
    first = D(equity[0]['equity_usdt'])
    final = D(equity[-1]['equity_usdt'])
    if first + sum((x['net_usdt'] for x in totals.values()),D(0)) != final:
        raise ValueError('trade net amounts do not reconcile to shared account')
    return {'initial_usdt':str(first),'final_usdt':str(final),
            'by_entry_year':{str(y):{k:str(v) if isinstance(v,D) else v for k,v in data.items()}
                             for y,data in sorted(totals.items())}}


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('original',type=Path)
    print(json.dumps(attribute(parser.parse_args().original),indent=2))
