"""L3 research-only causal forecast screen, never account qualification."""
import argparse
import bisect
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import zipfile

from pancakequant.research import invocations, spec, timestamp

DAY = 86400000


def solve(a, b):
    """Four-dimensional positive-definite ridge system; no fitting dependency."""
    rows = [list(row) + [value] for row, value in zip(a, b)]
    for i in range(len(b)):
        pivot = rows[i][i]
        if pivot <= 0 or not math.isfinite(pivot):
            raise ValueError('invalid ridge system')
        rows[i] = [x / pivot for x in rows[i]]
        for j in range(len(b)):
            if j != i:
                factor = rows[j][i]
                rows[j] = [x - factor * y for x, y in zip(rows[j], rows[i])]
    return [row[-1] for row in rows]


def forecast(observations, now):
    """Only labels whose maturity <= now can affect coefficients."""
    a = [[10.0 if i == j else 0.0 for j in range(4)] for i in range(4)]
    b = [0.0] * 4
    count = 0
    for maturity, x, y in observations:
        if maturity > now:
            continue
        count += 1
        for i in range(4):
            b[i] += x[i] * y
            for j in range(4):
                a[i][j] += x[i] * x[j]
    return (solve(a, b), count)


def archive_rows(root, relative):
    p = root / relative
    raw = p.read_bytes()
    checksum = Path(str(p) + '.CHECKSUM').read_text().split()[0]
    if hashlib.sha256(raw).hexdigest() != checksum:
        raise ValueError('archive checksum mismatch')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if len(z.namelist()) != 1 or z.testzip() is not None:
            raise ValueError('invalid ZIP')
        rows = list(csv.reader(io.StringIO(z.read(z.namelist()[0]).decode())))
    return rows[1:] if not rows[0][0].isdigit() else rows


def run(root, warmup, output):
    frozen = spec(); start = timestamp(frozen['start']); end = timestamp(frozen['development_end'])
    inputs=[]
    warmup_receipt=json.loads((warmup/'warmup-receipt.json').read_text())
    def warmup_rows(name):
        raw=(warmup/name).read_bytes()
        matches=[r for r in warmup_receipt['records'] if r['file']==name]
        if (len(matches)!=1 or matches[0]['bytes']!=len(raw)
                or matches[0]['sha256']!=hashlib.sha256(raw).hexdigest()):
            raise ValueError('warmup receipt mismatch')
        inputs.append({'path':name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
        return json.loads(raw)
    warmup_trade=warmup_rows('warmup-trade.json');warmup_funding=warmup_rows('warmup-funding.json')
    bars = {int(x[0]): x for x in warmup_trade}
    funding = {int(x['fundingTime']): float(x['fundingRate'])
               for x in warmup_funding}
    if len(bars)!=len(warmup_trade) or len(funding)!=len(warmup_funding):
        raise ValueError('duplicate warmup observation')
    for year in range(2020, 2024):
        for month in range(1, 13):
            date = f'{year}-{month:02}'
            trade_path=f'monthly/klines/BTCUSDT/1h/BTCUSDT-1h-{date}.zip'
            funding_path=f'monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-{date}.zip'
            for row in archive_rows(root, trade_path):
                t = int(row[0])
                if t in bars: raise ValueError('duplicate trade bar')
                bars[t] = row
            for row in archive_rows(root, funding_path):
                t = int(row[0])
                if t in funding: raise ValueError('duplicate funding')
                funding[t] = float(row[2])
            for relative in (trade_path,funding_path):
                raw=(root/relative).read_bytes()
                inputs.append({'path':relative,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
    times = sorted(bars)
    if any(not math.isfinite(float(x)) or float(x)<=0 for row in bars.values() for x in row[1:5]):
        raise ValueError('invalid forecast price input')
    if any(not math.isfinite(rate) for rate in funding.values()):
        raise ValueError('invalid forecast funding input')
    if times != list(range(timestamp('2019-12-01T00:00:00Z'), end, 3600000)):
        raise ValueError('development trade gap or overrun')
    ft = sorted(funding)
    # Preserve real milliseconds; an 8h settlement may be a few ms late.
    slots = [t // 28800000 for t in ft]
    if len(slots) != len(set(slots)) or slots != list(range(slots[0], (end-1)//28800000+1)):
        raise ValueError('missing/duplicate funding slot')
    daily = {t+DAY: float(bars[t+DAY-3600000][4]) for t in range(times[0], end, DAY)}
    features = {}; labels = []
    for t in sorted(daily):
        if t < times[0]+21*DAY: continue
        returns = [math.log(daily[s]/daily[s-DAY]) for s in range(t-19*DAY,t+1,DAY)]
        energy = sum(x*x for x in returns); rms = math.sqrt(energy/20)
        if rms <= 0: raise ValueError('zero volatility')
        i = bisect.bisect_right(ft,t)-1
        if i < 0: raise ValueError('missing known funding')
        x = [1.0, math.tanh(sum(returns)/math.sqrt(energy)),
             math.tanh(returns[-1]/rms), math.tanh(3*funding[ft[i]]/rms)]
        features[t] = x
        if t+4*DAY <= end:
            labels.append((t+4*DAY,x,math.log(daily[t+4*DAY]/daily[t])/(2*rms)))
    results = []; skipped = 0
    costs = .0015 + float(frozen['spread_fraction']) + 2*float(frozen['slippage_fraction'])
    for t in invocations(frozen):
        if t >= end: break
        if t+4*DAY >= end: skipped += 1; continue
        coef, n = forecast(labels,t)
        if n < 90: skipped += 1; continue
        x = features[t//DAY*DAY]
        prediction = sum(a*b for a,b in zip(coef,x))
        direction = 1 if prediction > 0 else -1 if prediction < 0 else 0
        forward = float(bars[t+4*DAY][1])/float(bars[t][1])-1
        carry = sum(funding[s] for s in ft[bisect.bisect_right(ft,t):bisect.bisect_right(ft,t+4*DAY)])
        results.append({'time':t,'matured_labels':n,'prediction':prediction,'forward_return':forward,
                        'directional_net':direction*(forward-carry)-costs*abs(direction),
                        'long_control_net':forward-carry-costs})
    predictions = [r['prediction'] for r in results]; targets = [r['forward_return'] for r in results]
    correlation = statistics.correlation(predictions,targets)
    net = statistics.mean(r['directional_net'] for r in results)
    control = statistics.mean(r['long_control_net'] for r in results)
    report = {'candidate':'L3','qualification':'NOT_QUALIFIED','scope':'2020-2023 development forecast screen',
              'observations':len(results),'skipped_warmup_or_unmatured':skipped,'correlation':correlation,
              'direction_accuracy':statistics.mean(r['prediction']*r['forward_return']>0 for r in results),
              'mean_directional_net':net,'mean_long_control_net':control,
              'progression_passed':correlation>0 and net>control,'validation_used':False,
              'limitations':['Overlapping forward labels, not independent trades or account CAGR',
              'Funding rates summed as return deduction; not exact marked contract funding cashflows',
              'No TP/SL, margin, liquidation or collateral-risk account replay',
              'Fixed fee/spread/slippage assumptions, not verified dated native rules'],
              'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    output.mkdir(parents=True,exist_ok=False)
    identity=json.dumps({'venue':'Binance','symbol':'BTCUSDT','inputs':inputs,
                         'frozen_spec':frozen},indent=2)+'\n'
    (output/'input-identity.json').write_text(identity)
    report['input_identity_sha256']=hashlib.sha256(identity.encode()).hexdigest()
    (output/'observations.json').write_text(json.dumps(results,indent=2)+'\n')
    (output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--warmup',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.root,a.warmup,a.output)
