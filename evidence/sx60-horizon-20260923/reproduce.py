"""Retrospective gross price labels for the 30 filled SX60 full-account parents.

From repository root: PYTHONPATH=. python evidence/sx60-horizon-20260923/reproduce.py INPUT_ROOT SX60_ACCOUNT OUTPUT_JSON
INPUT_ROOT is the full official hourly restoration with native/, warmup/, repairs/.
"""
import hashlib
import json
import sys
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path

from coinquant.research import iso, spec, timestamp
from research.persistent_hold_replay import HOUR, inputs


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reproduce(root, account):
    receipt = digest(root / 'RESTORE_RECEIPT.json')
    result = digest(account / 'result.json')
    summary = digest(account / 'execution_summary.json')
    if receipt != '547fbc42920823e37561a344d1ff9c9a2d258f5918cada7ae37d5583c34850e9':
        raise ValueError('different full-hour market restoration')
    if result != 'b2e6b6b71ff765331fad3e6626ea82d3cb234ea5edbf920912401be35dc0671c':
        raise ValueError('different historical SX60 full account')
    if summary != 'fd8d82dcda8ddd49141b67545d77098b5ed202b56289fabb07d5e753f47e9619':
        raise ValueError('different historical SX60 parent identities')
    series, _, _, identity = inputs(root / 'native', root / 'warmup', root / 'repairs', full_window=True)
    market = hashlib.sha256(json.dumps(sorted(x['sha256'] for x in identity)).encode()).hexdigest()
    if market != 'fb5adb7afeacffdcbce1745111b373ded79f3cc128c4d87bed6d174bc91ad674':
        raise ValueError('different verified hourly market inputs')
    trade = series['klines']
    parents = json.loads((account / 'execution_summary.json').read_text())['parents']
    end = timestamp(spec()['end'])
    rows = []
    years = defaultdict(lambda: defaultdict(list))
    for parent in parents:
        if D(parent['filled']) <= 0:
            continue
        t = parent['call_time']
        if t not in trade:
            raise ValueError('parent call lacks official hourly price')
        start = D(trade[t][1])
        row = {'call': iso(t), 'parent_id': parent['parent_id'], 'filled_btc': parent['filled']}
        for horizon in (24, 168):
            key = f'gross_open_to_open_{horizon}h'
            if t + horizon * HOUR < end:
                gross = D(trade[t + horizon * HOUR][1]) / start - 1
                row[key] = str(gross)
                years[iso(t)[:4]][str(horizon)].append(gross)
            else:
                row[key] = None
        rows.append(row)
    if len(parents) != 31 or len(rows) != 30 or len({r['parent_id'] for r in rows}) != 30:
        raise ValueError('historical filled parent identity count changed')
    annual = {
        year: {
            horizon: {'n': len(values), 'positive': sum(v > 0 for v in values),
                      'mean_gross': str(sum(values) / len(values))}
            for horizon, values in sorted(horizons.items())
        }
        for year, horizons in sorted(years.items())
    }
    return {
        'scope': 'Retrospective 30 filled SX60 parents, call-hour open to future-hour open; NOT actual entry/exit execution, independent sample or account return',
        'source_sha256': {'receipt': receipt, 'account_result': result,
                          'parent_summary': summary, 'market_identity_aggregate': market},
        'filled_parents': len(rows), 'rows': rows, 'annual': annual,
    }


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit('usage: reproduce.py FULL_INPUT_ROOT SX60_FULL_ACCOUNT OUTPUT_JSON')
    output = Path(sys.argv[3])
    if output.exists():
        raise SystemExit('refusing overwrite')
    output.write_text(json.dumps(reproduce(Path(sys.argv[1]), Path(sys.argv[2])), indent=2) + '\n')
