"""Read-only exploration of existing single-signal definitions on frozen calls.

Run from repository root: PYTHONPATH=. python evidence/alternative-signal-probes-20260923/reproduce.py INPUT_ROOT OUTPUT_JSON
"""
import hashlib
import json
import sys
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path

from coinquant.opportunities import Opportunities, FOUR_HOURS
from coinquant.research import invocations, iso, spec, timestamp
from research.persistent_hold_replay import inputs

HOUR = 3_600_000
DAY = 86_400_000
CASES = {'shock_reversal_4h': ('shock', FOUR_HOURS),
         'daily_directional_swing': ('swing', DAY),
         'impulse_continuation_1h': ('impulse_hold', HOUR)}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(root):
    frozen = spec()
    start, end = timestamp(frozen['start']), timestamp(frozen['end'])
    series, _, warm, identity = inputs(root/'native', root/'warmup', root/'repairs', full_window=True)
    trade = series['klines']
    calls = [t for t in invocations(frozen) if start <= t < end]
    if len(calls) != 795:
        raise ValueError('frozen full call count differs')
    output = {'scope': 'retrospective gross-price call-time signal diagnosis; no account',
              'source': {'input_root_receipt_sha256': digest(root/'RESTORE_RECEIPT.json'),
                         'market_sources_sha256': hashlib.sha256(json.dumps(
                             sorted(record['sha256'] for record in identity)).encode()).hexdigest(),
                         'spec_sha256': digest('research/spec.json'),
                         'draws_sha256': digest('research/invocation_draws.json'),
                         'opportunities_sha256': digest('coinquant/opportunities.py'),
                         'calls': len(calls)},
              'label': 'price at hour open t+168h / hour open at call t minus 1; multiplied by signal side',
              'cases': {}}
    for name, (mechanism, interval) in CASES.items():
        model = Opportunities(mechanism, interval)
        states = {}
        for begin in range(min(warm), end, interval):
            source = warm if begin < start else trade
            bars = [source[t] for t in range(begin, begin+interval, HOUR)]
            states[begin+interval] = model.update(begin+interval,
                max(D(row[2]) for row in bars), min(D(row[3]) for row in bars), D(bars[-1][4]))
        rows = []
        for t in calls:
            opportunity = states[t//interval*interval]
            row = {'call_time': iso(t), 'identity': opportunity.identity if opportunity else None,
                   'side': opportunity.direction if opportunity else 0}
            if opportunity and t+7*DAY < end:
                row['gross_168h'] = str(D(opportunity.direction)*(
                    D(trade[t+7*DAY][1])/D(trade[t][1])-1))
            else:
                row['gross_168h'] = None
            rows.append(row)
        groups = defaultdict(list)
        for row in rows:
            if row['side']:
                groups[(row['call_time'][:4], row['side'])].append(row)
        output['cases'][name] = {
            'interval_ms': interval,
            'grouped': [dict(year=y, side=side, calls=len(group),
                identities=len({row['identity'] for row in group}),
                labels=sum(row['gross_168h'] is not None for row in group),
                mean_gross_168h=str(sum(D(row['gross_168h']) for row in group
                    if row['gross_168h'] is not None)/sum(row['gross_168h'] is not None
                    for row in group)) if any(row['gross_168h'] is not None for row in group) else None)
                for (y, side), group in sorted(groups.items())],
            'rows': rows}
    return output


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: reproduce.py INPUT_ROOT OUTPUT_JSON')
    target = Path(sys.argv[2])
    if target.exists():
        raise SystemExit('refusing to overwrite prior signal output')
    target.write_text(json.dumps(run(Path(sys.argv[1])), indent=2)+'\n')
