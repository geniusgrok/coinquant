"""L5 single online Bayesian change-point model; research forecast screen only."""
import argparse
import bisect
import hashlib
import json
import math
from pathlib import Path
import statistics

from pancakequant.research import invocations, timestamp
from research.linear_forecast import archive_rows, DAY

PRIOR=(0.0,1.0,3.0,.0032)
HAZARD=1/90


def updated(state,x):
    mu,k,a,b=state
    return ((k*mu+x)/(k+1),k+1,a+.5,b+k*(x-mu)**2/(2*(k+1)))


def log_predictive(state,x):
    mu,k,a,b=state
    nu=2*a; scale2=b*(k+1)/(a*k)
    return (math.lgamma((nu+1)/2)-math.lgamma(nu/2)-.5*math.log(nu*math.pi*scale2)
            -(nu+1)/2*math.log1p((x-mu)**2/(nu*scale2)))


class ChangePoint:
    def __init__(self):
        self.states=[PRIOR];self.weights=[1.0]

    def add(self,x):
        if not math.isfinite(x):raise ValueError('invalid daily return')
        scores=[math.log(HAZARD)+log_predictive(PRIOR,x)]
        scores.extend(math.log1p(-HAZARD)+math.log(w)+log_predictive(s,x)
                      if w>0 else -math.inf for w,s in zip(self.weights,self.states))
        maximum=max(scores);weights=[math.exp(x-maximum) for x in scores];total=sum(weights)
        self.weights=[x/total for x in weights]
        self.states=[updated(PRIOR,x)]+[updated(s,x) for s in self.states]

    def expected(self):
        return sum(w*s[0] for w,s in zip(self.weights,self.states))


def run(root,warmup,identity_path,output):
    identity_raw=identity_path.read_bytes();identity=json.loads(identity_raw)
    frozen=identity['frozen_spec'];start=timestamp(frozen['start']);end=timestamp(frozen['development_end'])
    warm_receipt=json.loads((warmup/'warmup-receipt.json').read_text())
    raw=(warmup/'warmup-trade.json').read_bytes()
    match=[r for r in warm_receipt['records'] if r['file']=='warmup-trade.json']
    if len(match)!=1 or match[0]['bytes']!=len(raw) or match[0]['sha256']!=hashlib.sha256(raw).hexdigest():
        raise ValueError('warmup identity mismatch')
    bars={int(r[0]):r for r in json.loads(raw)};funding={}
    for item in identity['inputs']:
        relative=item['path']
        if not relative.startswith('monthly/'):continue
        raw=(root/relative).read_bytes()
        if len(raw)!=item['bytes'] or hashlib.sha256(raw).hexdigest()!=item['sha256']:
            raise ValueError('native development input identity mismatch')
        for row in archive_rows(root,relative):
            t=int(row[0]);target=bars if '/klines/' in relative else funding
            if t in target:raise ValueError('duplicate native input')
            target[t]=row if target is bars else float(row[2])
    times=sorted(bars)
    if times!=list(range(timestamp('2019-12-01T00:00:00Z'),end,3600000)):
        raise ValueError('development hourly coverage gap')
    ft=sorted(funding)
    if [t//28800000 for t in ft]!=list(range(start//28800000,end//28800000)):
        raise ValueError('development funding coverage gap')
    model=ChangePoint();forecasts={};previous=None
    for t in range(times[0],end,DAY):
        close=float(bars[t+DAY-3600000][4])
        if not math.isfinite(close) or close<=0:raise ValueError('invalid daily close')
        if previous is not None:model.add(math.log(close/previous))
        previous=close;forecasts[t+DAY]=4*model.expected()
    costs=.0015+float(frozen['spread_fraction'])+2*float(frozen['slippage_fraction'])
    observations=[]
    for t in invocations(frozen):
        if t>=end:break
        if t+4*DAY>=end:continue
        prediction=forecasts[t//DAY*DAY]
        direction=(1 if prediction>0 else -1) if abs(prediction)>costs else 0
        forward=float(bars[t+4*DAY][1])/float(bars[t][1])-1
        carry=sum(funding[s] for s in ft[bisect.bisect_right(ft,t):bisect.bisect_right(ft,t+4*DAY)])
        observations.append(dict(time=t,prediction=prediction,direction=direction,forward_return=forward,
                                 directional_net=direction*(forward-carry)-costs*abs(direction),
                                 long_control_net=forward-carry-costs))
    corr=statistics.correlation([r['prediction'] for r in observations],[r['forward_return'] for r in observations])
    net=statistics.mean(r['directional_net'] for r in observations)
    control=statistics.mean(r['long_control_net'] for r in observations)
    report=dict(candidate='L5',qualification='NOT_QUALIFIED',validation_used=False,
                scope='2020-2023 development overlapping forecast screen',observations=len(observations),
                active_observations=sum(r['direction']!=0 for r in observations),correlation=corr,
                mean_directional_net=net,mean_long_control_net=control,progression_passed=corr>0 and net>control,
                code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                input_identity_sha256=hashlib.sha256(identity_raw).hexdigest(),
                limitations=['Not account CAGR/MDD or executable trades','Fixed proxy costs and funding rate-sum approximation',
                             'No margin/liquidation/protection/USDT valuation model'])
    output.mkdir(parents=True,exist_ok=False)
    (output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    (output/'observations.json').write_text(json.dumps(observations,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('root','warmup','identity','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();run(a.root,a.warmup,a.identity,a.output)
