"""Registered L19 unit-inventory information probe, never account qualification."""
import argparse
from bisect import bisect_left, bisect_right
from collections import deque
from decimal import Decimal as D
import csv
import json
from pathlib import Path
from statistics import median
from coinquant.research import spec, timestamp, invocations, digest
from research.persistent_hold_replay import inputs, channel_state, HOUR, DAY
from research.linear_replay import FEE
from coinquant.types import ZERO


def direction(rates):
    if len(rates)<91:return 0
    delta=rates[-1]-median(rates[-91:-1])
    return -1 if delta>0 else 1 if delta<0 else 0


def funding_cash(times,rates,marks,start,end,side,entry):
    """Entry is after boundary settlement; exit is after its settlement."""
    cash=ZERO
    for j in range(bisect_right(times,start),bisect_right(times,end)):
        r=rates[j];bar=marks[times[j]//HOUR*HOUR]
        price=D(bar[1] if times[j]%HOUR==0 else bar[2] if side*r>0 else bar[3])
        cash+=side*r*price/entry
    return cash


def run(root,output):
    frozen=spec();start=timestamp(frozen['start']);end=timestamp(frozen['development_end'])
    series,funding,warm,identity=inputs(root,Path('evidence/binance-boundary-20260921'),Path('evidence/binance-mark-repair-20260921'))
    trade=series['klines'];marks=series['markPriceKlines'];times=sorted(funding);rates=[funding[t] for t in times]
    daily=deque(maxlen=21);regime=0;states={}
    for t in range(min(warm),end,DAY):
        states[t]=regime
        source=warm if t<start else trade
        rows=[source[h] for h in range(t,t+DAY,HOUR)]
        daily.append((max(D(r[2]) for r in rows),min(D(r[3]) for r in rows),D(rows[-1][4])))
        regime=channel_state(daily,regime)
    schedule=[t for t in invocations(frozen) if t<end];observations=[]
    cost=2*(FEE+D(frozen['slippage_fraction'])+D(frozen['spread_fraction'])/2)
    for t,u in zip(schedule,schedule[1:]):
        i=bisect_left(times,t)
        if i<91:continue
        entry=D(trade[t][1]);exit=D(trade[u][1]);d=direction(rates[:i]);channel=states[t//DAY*DAY]
        row=dict(time=t,end=u,signal=d,latest_funding_time=times[i-1],latest_rate=str(rates[i-1]))
        for name,side in [('crowding',d),('long',1),('channel',channel)]:
            cash=funding_cash(times,rates,marks,t,u,side,entry)
            row[name+'_net']=str(D(side)*(exit/entry-1)-cash-(cost if side else ZERO))
        observations.append(row)
    means={k:str(sum((D(r[k+'_net']) for r in observations),ZERO)/len(observations)) for k in ('crowding','long','channel')}
    result=dict(candidate='L19_funding_crowding',qualification='NOT_QUALIFIED',scope='2020-2023_nonoverlapping_unit_inventory_forecast',validation_used=False,samples=len(observations),active=sum(r['signal']!=0 for r in observations),mean_net=means,screen_passed=D(means['crowding'])>0 and (D(means['crowding'])>D(means['long']) or D(means['crowding'])>D(means['channel'])),source_sha256=digest(__file__),limitations=['Not account CAGR/MDD','Dated costs/rules and USDT valuation proxy','Funding mark interval approximation; no exact cashflow claim'])
    output.mkdir(parents=True,exist_ok=False)
    with (output/'observations.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(observations[0]));w.writeheader();w.writerows(observations)
    (output/'measured_driver.py').write_bytes(Path(__file__).read_bytes())
    (output/'inputs.json').write_text(json.dumps(identity,indent=2)+'\n')
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.root,a.output)
