"""Frictionless opportunity indices, explicitly NOT executable account results."""
from collections import deque
from decimal import Decimal as D
import json
from pathlib import Path
from research.persistent_hold_replay import inputs, channel_state, HOUR
from research.linear_forecast import DAY
from pancakequant.research import iso


def run(root, output):
    series,_,warm,_=inputs(root,Path('evidence/binance-boundary-20260921'),Path('evidence/binance-mark-repair-20260921'))
    trade=series['klines'];daily=deque(maxlen=21);regime=0
    for t in range(min(warm),max(warm),DAY):
        rows=[warm[s] for s in range(t,t+DAY,HOUR)]
        daily.append((max(D(r[2]) for r in rows),min(D(r[3]) for r in rows),D(rows[-1][4])))
        regime=channel_state(daily,regime)
    previous=daily[-1][2];long=D(1);trend=D(1);annual={};oldyear=None
    for t in range(min(trade),max(trade),DAY):
        year=iso(t)[:4]
        if year!=oldyear:
            annual[year]={'long_start':long,'trend_start':trend};oldyear=year
        rows=[trade[s] for s in range(t,t+DAY,HOUR)];close=D(rows[-1][4]);ret=close/previous-1
        long*=1+ret;trend*=1+D(regime)*ret
        annual[year].update(long_gross=long/annual[year]['long_start']-1,channel_gross=trend/annual[year]['trend_start']-1)
        daily.append((max(D(r[2]) for r in rows),min(D(r[3]) for r in rows),close))
        regime=channel_state(daily,regime);previous=close
    out={'scope':'frictionless unlevered daily unit-inventory opportunity indices; NOT executable account returns or alpha',
         'annual':annual,'full_multiple':{'long':long,'channel':trend}}
    output.write_text(json.dumps(out,indent=2,default=str)+'\n')

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.root,a.output)
