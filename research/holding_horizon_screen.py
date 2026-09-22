"""L16 causal completed-day trend screen, not an account replay or qualification."""
import argparse
from collections import deque
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import mean
from research.persistent_hold_replay import inputs,channel_state
from coinquant.research import spec,invocations,timestamp
from research.linear_forecast import DAY
HOUR=3600000

def score(closes):
    if len(closes)<20:return 0.
    y=[math.log(float(x)) for x in closes[-20:]]
    center=9.5
    slope=sum((i-center)*v for i,v in enumerate(y))/sum((i-center)**2 for i in range(20))
    rms=math.sqrt(mean((b-a)**2 for a,b in zip(y,y[1:])))
    return slope/rms if rms else 0.

def run(root,warmup,repairs,output):
    series,funding,warm,identity=inputs(root,warmup,repairs)
    frozen=spec();start=timestamp(frozen['start']);end=timestamp(frozen['development_end'])
    bars=dict(warm);bars.update(series['klines']);daily=deque(maxlen=21)
    regimes={};scores={};regime=0
    for t in range(min(warm),end,DAY):
        regimes[t]=regime;scores[t]=score([r[2] for r in daily])
        rows=[bars[h] for h in range(t,t+DAY,HOUR)]
        daily.append((max(float(r[2]) for r in rows),min(float(r[3]) for r in rows),float(rows[-1][4])))
        regime=channel_state(daily,regime)
    friction=2*.00075+float(frozen['spread_fraction'])+2*float(frozen['slippage_fraction'])
    rows=[]
    for t in invocations(frozen):
        maturity=t+30*DAY
        if maturity>=end:break
        day=t//DAY*DAY;s=scores[day];direction=1 if s>0 else -1 if s<0 else 0
        entry=float(bars[t][1]);exit=float(bars[maturity][1]);raw=exit/entry-1
        carry=sum(float(r) for ft,r in funding.items() if t<ft<=maturity)
        regime=regimes[day]
        net=lambda d:d*(raw-carry)-friction*abs(d)
        rows.append(dict(time=t,maturity=maturity,score=s,raw_return=raw,
                         slope_net=net(direction),channel_net=net(regime),long_net=net(1)))
    x=[r['score'] for r in rows];y=[r['raw_return'] for r in rows]
    mx,my=mean(x),mean(y)
    denominator=math.sqrt(sum((a-mx)**2 for a in x)*sum((a-my)**2 for a in y))
    corr=sum((a-mx)*(b-my) for a,b in zip(x,y))/denominator if denominator else 0.
    spaced=[];next_time=start
    for r in rows:
        if r['time']>=next_time:spaced.append(r);next_time=r['maturity']
    means={k:mean(r[k] for r in rows) for k in ('slope_net','channel_net','long_net')}
    result=dict(candidate='L16',qualification='forecast_diagnostic_only',validation_used=False,
                observations=len(rows),mean_net=means,score_return_correlation=corr,
                nonoverlap_count=len(spaced),nonoverlap_mean_net=mean(r['slope_net'] for r in spaced),
                progression_passed=means['slope_net']>max(means['channel_net'],means['long_net'])+.005
                and corr>.05 and mean(r['slope_net'] for r in spaced)>0,
                code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                limitations=['Fixed horizon is not actual orders/holding lifecycle',
                             'Funding rate sum is an approximate return, not settlement cashflow',
                             'No leverage, margin, account CAGR or drawdown claim'])
    output.mkdir(parents=True,exist_ok=False)
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    with (output/'observations.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (output/'inputs.json').write_text(json.dumps(identity,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('root','warmup','repairs','output'):p.add_argument('--'+n,type=Path,required=True)
    run(**vars(p.parse_args()))
