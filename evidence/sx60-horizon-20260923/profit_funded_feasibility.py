"""Retrospective feasibility only; crossing 1R never executes an order.

Usage: python evidence/sx60-horizon-20260923/profit_funded_feasibility.py \
    SX60_FULL_ACCOUNT SX60_FULL_POSTDEV_ATTRIBUTION.json OUTPUT.json
"""
import bisect
import csv
import gzip
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime
from decimal import Decimal as D
from pathlib import Path


EXPECTED = {
    'execution_summary.json': 'fd8d82dcda8ddd49141b67545d77098b5ed202b56289fabb07d5e753f47e9619',
    'execution.jsonl': 'fdde28a8aaeb73c1470eb2746a403ff103c1d064800d78f90256ee9b11a8477e',
    'equity.csv.gz': 'a41cdd77c5442bda2c3ff0c6d4f2c0e92d1b4aa0e02fda4aa305840276bd17f9',
    'invocations.json': '4e48e33467e699608be89e62749f438f3cc436d2c533b90d419159d694372e4f',
    'attribution': '839b731acbb9555713305f93df725aec57ee97442982c6a89fc9672b2c915441',
}


def reproduce(account, attribution):
    for name, expected in EXPECTED.items():
        path = attribution if name == 'attribution' else account / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'input identity mismatch: {name}')
    parents = [p for p in json.loads((account / 'execution_summary.json').read_text())['parents']
               if D(p['filled']) > 0]
    segments = json.loads(attribution.read_text())['segments']
    calls = json.loads((account / 'invocations.json').read_text())
    if len(parents) != len(segments) or len(parents) != 30 or len(calls) != 795:
        raise ValueError('old continuous account identities changed')
    last_child = {}
    for raw in (account / 'execution.jsonl').open():
        x = json.loads(raw)
        if x.get('kind') == 'child' and D(x.get('accepted', '0')) > 0:
            last_child[x['parent_id']] = x
    closes = []
    with gzip.open(account / 'equity.csv.gz', 'rt') as handle:
        for record in csv.DictReader(handle):
            if record['event'] == 'close':
                closes.append((int(record['time']), D(record['mark']), D(record['quantity'])))
    times = [t for t, _, _ in closes]
    rows = []
    annual = defaultdict(lambda: defaultdict(int))
    for parent, segment in zip(parents, segments):
        child = last_child[parent['parent_id']]
        if D(child['quantity_after']) != D(parent['filled']):
            raise ValueError('last accepted child differs from confirmed parent')
        start = int(datetime.fromisoformat(segment['start'].replace('Z', '+00:00')).timestamp() * 1000)
        end = int(datetime.fromisoformat(segment['end'].replace('Z', '+00:00')).timestamp() * 1000)
        if start != parent['first_fill'] or not start < parent['last_fill'] + 1 < end:
            raise ValueError('segment and parent fill identity mismatch')
        entry = D(child['entry_price'])
        stop = D(parent['stop'])
        if not stop < entry:
            raise ValueError('invalid actual initial stop')
        target = entry + (entry - stop)
        first = next((t for t, mark, q in closes[
            bisect.bisect_right(times, parent['last_fill']):bisect.bisect_left(times, end)]
            if q > 0 and mark >= target), None)
        index = bisect.bisect_right(calls, first) if first is not None else len(calls)
        later_call = calls[index] if index < len(calls) and calls[index] < end else None
        won = D(segment['net_wallet_usdt']) > 0
        year = segment['start'][:4]
        annual[year]['profitable' if won else 'loss'] += 1
        if later_call is not None:
            annual[year]['profitable_reachable' if won else 'loss_reachable'] += 1
        rows.append({'parent_id': parent['parent_id'], 'segment_start': segment['start'],
                     'segment_end': segment['end'], 'net_wallet_usdt': segment['net_wallet_usdt'],
                     'confirmed_quantity_btc': parent['filled'],
                     'confirmed_entry_price': str(entry), 'initial_stop': str(stop),
                     'one_r_mark_threshold': str(target),
                     'first_completed_hour_mark_cross_ms': first,
                     'next_frozen_call_before_actual_exit_ms': later_call})
    return {'scope': 'RETROSPECTIVE feasibility on unchanged SX60 paths; no alternative sizing, fills, stop amendments, CAGR or counterfactual PnL',
            'input_sha256': EXPECTED, 'rows': rows,
            'annual': {k: dict(v) for k, v in sorted(annual.items())}}


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit('usage: profit_funded_feasibility.py SX60_ACCOUNT ATTRIBUTION_JSON OUTPUT_JSON')
    output = Path(sys.argv[3])
    if output.exists():
        raise SystemExit('refusing overwrite')
    output.write_text(json.dumps(reproduce(Path(sys.argv[1]), Path(sys.argv[2])), indent=2) + '\n')
