"""Retrospective, gross only: reconstruct all 795 call labels used during DC10 selection.

Run from repository root: PYTHONPATH=. python evidence/drawdown-reclaim-20260923/selection_reproduce.py INPUT_ROOT OUTPUT_JSON
"""
import hashlib
import json
import sys
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path

from coinquant.research import invocations, iso, spec, timestamp
from research.persistent_hold_replay import inputs

HOUR = 3_600_000
WEEK = 7*86_400_000


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(root):
    frozen = spec()
    start, end = timestamp(frozen['start']), timestamp(frozen['end'])
    series, _, warm, identity = inputs(root/'native',root/'warmup',root/'repairs',full_window=True)
    trade = series['klines']
    calls = [t for t in invocations(frozen) if start <= t < end]
    if len(calls) != 795:
        raise ValueError('frozen invocation count changed')
    output = dict(scope='retrospective call-time price labels, NO economic account',
        source=dict(receipt_sha256=sha(root/'RESTORE_RECEIPT.json'),
            market_sha256=hashlib.sha256(json.dumps(sorted(r['sha256'] for r in identity)).encode()).hexdigest(),
            spec_sha256=sha('research/spec.json'),draws_sha256=sha('research/invocation_draws.json')),
        rule='past week: close at t-1h / close at t-169h; future: open at t+168h / open at t; negative past <= -10 percent was explored',
        rows=[],annual={})
    buckets = defaultdict(list)
    for t in calls:
        older = trade if t-WEEK-HOUR in trade else warm
        newer = trade if t-HOUR in trade else warm
        if t-WEEK-HOUR not in older or t-HOUR not in newer:
            raise ValueError('missing completed previous week')
        past = D(newer[t-HOUR][4])/D(older[t-WEEK-HOUR][4])-1
        future = D(trade[t+WEEK][1])/D(trade[t][1])-1 if t+WEEK<end else None
        row=dict(call=iso(t),previous_7d=str(past),future_168h_gross=str(future) if future is not None else None,
            past_drop_at_least_10pct=past<=D('-.10'))
        output['rows'].append(row)
        if future is not None:
            year=row['call'][:4]
            if row['past_drop_at_least_10pct']:
                buckets[(year,'drop')].append(future)
            side=1 if past>0 else -1 if past<0 else 0
            if side:buckets[(year,'past_week_direction')].append(side*future)
    for (year,kind),values in sorted(buckets.items()):
        output['annual'].setdefault(year,{})[kind]=dict(calls=len(values),positive=sum(v>0 for v in values),mean_gross=str(sum(values)/len(values)))
    return output


if __name__=='__main__':
    if len(sys.argv)!=3:
        raise SystemExit('usage: selection_reproduce.py INPUT_ROOT OUTPUT_JSON')
    output=Path(sys.argv[2])
    if output.exists():
        raise SystemExit('refusing overwrite')
    output.write_text(json.dumps(run(Path(sys.argv[1])),indent=2)+'\n')
