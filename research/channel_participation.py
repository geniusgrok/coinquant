"""Development-only attribution of measured inventory; never a new backtest."""
import argparse
from bisect import bisect_right
import csv
from decimal import Decimal as D
import gzip
import json
from pathlib import Path
from research.persistent_hold_replay import inputs

def run(root,warmup,repairs,evidence,output):
    series,_,_,_=inputs(root,warmup,repairs)
    changes=[]
    for row in csv.DictReader(gzip.open(evidence/'orders.csv.gz','rt')):
        if row['event']!='funding_adverse_bound':
            changes.append((int(row['time']),D(row['quantity_after'])))
    if changes!=sorted(changes,key=lambda x:x[0]):raise ValueError('inventory events unordered')
    times=[t for t,_ in changes];values=[];active=[];signs={'long':0,'short':0,'flat':0}
    for row in csv.DictReader(gzip.open(evidence/'equity.csv.gz','rt')):
        if row['event']!='close':continue
        t=int(row['time']);index=bisect_right(times,t-1)-1
        q=changes[index][1] if index>=0 else D(0)
        mark=D(series['markPriceKlines'][t-3600000][4]);equity=D(row['equity_usdt'])
        exposure=abs(q)*mark/equity;values.append(exposure)
        signs['long' if q>0 else 'short' if q<0 else 'flat']+=1
        if q:active.append(exposure)
    result={'qualification':'diagnostic_only','hours':len(values),'hours_by_direction':signs,
            'mean_account_notional_multiple':str(sum(values)/len(values)),
            'mean_notional_multiple_when_held':str(sum(active)/len(active)),
            'max_close_notional_multiple':str(max(values)),
            'scope':'native development close observations; not intrahour maximum',
            'interpretation':'20x exchange setting does not imply 20x account exposure; this attribution does not authorize leverage escalation'}
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('root','warmup','repairs','evidence','output'):p.add_argument('--'+n,type=Path,required=True)
    run(**vars(p.parse_args()))
