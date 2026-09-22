"""Non-overlapping sparse funding-information screen, not an account backtest."""
import argparse,json,bisect
from decimal import Decimal as D
from pathlib import Path
from research.persistent_hold_replay import inputs,HOUR
from coinquant.research import invocations,spec,timestamp

def screen(native,output):
    series,funding,_,identity=inputs(native,Path('evidence/binance-boundary-20260921'),Path('evidence/binance-mark-repair-20260921'))
    trade=series['klines'];mark=series['markPriceKlines'];end=timestamp(spec()['development_end'])
    times=sorted(t for t in invocations(spec()) if t<end)
    ft=sorted(funding);week=7*24*HOUR;records=[];i=0
    while i<len(times):
        t=times[i];j=bisect.bisect_left(times,t+week)
        if j>=len(times):break
        exit=times[j];past=[f for f in ft if t-week-HOUR<=f<t-HOUR]
        if len(past)!=21:i+=1;continue
        value=sum(funding[f] for f in past)
        if not value:i=j;continue
        side=1 if value<0 else -1
        entry=D(trade[t][1])*(1+D(side)*D('.0011'))
        close=D(trade[exit][1])*(1-D(side)*D('.0011'))
        fees=(entry+close)*D('.00075');cost=D(0)
        for f in ft:
            if t<f<=exit:
                rate=D(side)*funding[f]
                cost+=rate*D(mark[f//HOUR*HOUR][2 if rate>0 else 3])
        net=(D(side)*(close-entry)-fees-cost)/entry
        records.append(dict(entry=t,exit=exit,side=side,past_funding=str(value),net_return=str(net),
                            funding_cost_per_btc=str(cost),fees_per_btc=str(fees)))
        i=j
    groups={}
    for side in (1,-1):
        for label,start,stop in [('all',0,end),('2020-21',0,1640995200000),('2022-23',1640995200000,end)]:
            vals=[D(r['net_return']) for r in records if r['side']==side and start<=r['entry']<stop]
            groups[f'{side}:{label}']=dict(n=len(vals),mean=str(sum(vals)/len(vals)) if vals else None,positive=sum(v>0 for v in vals))
    result=dict(qualification='INFORMATION_SCREEN_NOT_ACCOUNT',input_identity=identity,funding_events=len(ft),records=records,groups=groups,
                limitations=['No protective execution, margin or liquidation: cannot infer account CAGR/MDD','Hourly mark funding bound, not exact timestamp mark','Development reused; no independent unseen claim'])
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(groups,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();screen(a.native,a.output)
