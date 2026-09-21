"""Research-only L4 frozen taker-flow screen; no account or execution claim."""
import argparse
import bisect
import hashlib
import json
from pathlib import Path
import statistics

from pancakequant.research import invocations, timestamp
from research.linear_forecast import archive_rows, DAY


def run(root, identity_path, output):
    identity_raw = identity_path.read_bytes()
    identity = json.loads(identity_raw)
    frozen = identity['frozen_spec']
    end = timestamp(frozen['development_end'])
    bars = {}; funding = {}
    for item in identity['inputs']:
        relative = item['path']
        if not relative.startswith('monthly/'):
            continue
        raw = (root / relative).read_bytes()
        if len(raw) != item['bytes'] or hashlib.sha256(raw).hexdigest() != item['sha256']:
            raise ValueError('development input identity mismatch')
        rows = archive_rows(root, relative)
        target = bars if '/klines/' in relative else funding
        for row in rows:
            t = int(row[0])
            if t in target:
                raise ValueError('duplicate input')
            target[t] = row if target is bars else float(row[2])
    start = timestamp(frozen['start'])
    if sorted(bars) != list(range(start, end, 3600000)):
        raise ValueError('incomplete development trade input')
    ft = sorted(funding)
    results = []; skipped = 0
    costs = .0015 + float(frozen['spread_fraction']) + 2*float(frozen['slippage_fraction'])
    for t in invocations(frozen):
        if t >= end:
            break
        if t-DAY < start or t+4*DAY >= end:
            skipped += 1
            continue
        prior = [bars[s] for s in range(t-DAY, t, 3600000)]
        volume = sum(float(x[7]) for x in prior)
        bought = sum(float(x[10]) for x in prior)
        if not 0 <= bought <= volume or volume <= 0:
            raise ValueError('invalid taker volume')
        signal = (2*bought-volume)/volume
        direction = (signal > 0)-(signal < 0)
        forward = float(bars[t+4*DAY][1])/float(bars[t][1])-1
        carry = sum(funding[s] for s in ft[bisect.bisect_right(ft,t):bisect.bisect_right(ft,t+4*DAY)])
        results.append(dict(time=t,signal=signal,forward_return=forward,
                            directional_net=direction*(forward-carry)-costs*abs(direction),
                            long_control_net=forward-carry-costs))
    corr = statistics.correlation([r['signal'] for r in results], [r['forward_return'] for r in results])
    net = statistics.mean(r['directional_net'] for r in results)
    control = statistics.mean(r['long_control_net'] for r in results)
    report = dict(candidate='L4',qualification='NOT_QUALIFIED',validation_used=False,
                  observations=len(results),skipped_boundary=skipped,correlation=corr,
                  mean_directional_net=net,mean_long_control_net=control,
                  progression_passed=corr>0 and net>control,
                  input_identity_sha256=hashlib.sha256(identity_raw).hexdigest(),
                  code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  limitations=['Overlapping four-day forecast observations, not account CAGR/MDD',
                               'Funding rate sum approximation; fixed proxy costs',
                               'No margin, liquidation, TP/SL or USDT valuation replay'])
    output.mkdir(parents=True,exist_ok=False)
    (output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    (output/'observations.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--identity',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.root,a.identity,a.output)
