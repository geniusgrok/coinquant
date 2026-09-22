"""Funding cashflow interval on a FROZEN measured inventory path, not a replay."""
import argparse
from bisect import bisect_left,bisect_right
import csv
from decimal import Decimal as D
import gzip
import json
from pathlib import Path
from research.persistent_hold_replay import inputs

HOUR=3600000

def run(root,warmup,repairs,evidence,output):
    measured=json.loads((evidence/'result.json').read_text())
    full_window=measured.get('validation_used',False)
    series,funding,_,_=inputs(root,warmup,repairs,full_window)
    changes=[]
    with gzip.open(evidence/'orders.csv.gz','rt') as stream:
        for row in csv.DictReader(stream):
            if row['event']!='funding_adverse_bound':
                changes.append((int(row['time']),D(row['quantity_after'])))
    times=[t for t,_ in changes]
    total_low=total_high=D(0);ambiguous=0;records=[]
    for ft,rate in sorted(funding.items()):
        hour=ft//HOUR*HOUR
        left=bisect_left(times,hour);right=bisect_left(times,hour+HOUR)
        before=changes[left-1][1] if left else D(0)
        # The whole-hour inventory envelope deliberately includes possible exits
        # whose sub-minute timing is unknown, never claiming exact settlement cash.
        qs={before,*[q for _,q in changes[left:right]]}
        if ft==hour:qs={before}
        else:ambiguous+=len(qs)>1
        r=series['markPriceKlines'][hour]
        prices=[D(r[1])] if ft==hour else [D(r[2]),D(r[3])]
        costs=[q*p*rate for q in qs for p in prices]
        lo,hi=min(costs),max(costs);total_low+=lo;total_high+=hi
        records.append([ft,str(lo),str(hi),len(qs)])
    measured=json.loads((evidence/'result.json').read_text())
    result={'scope':'fixed measured inventory only; account feedback NOT replayed',
            'qualification':'NOT_QUALIFIED','validation_used':full_window,
            'net_funding_cost_lower_usdt':str(total_low),'net_funding_cost_upper_usdt':str(total_high),
            'old_adverse_debits_only_usdt':measured['funding_bound_paid_usdt'],
            'inventory_ambiguous_events':ambiguous,'events':len(records),
            'limitations':['Hourly mark interval, exact-hour opening-mark convention unchanged',
                           'Inventory is measured scenario, not native account history',
                           'No claim these cash intervals bound strategy CAGR or MDD under changed cashflow']}
    output.mkdir(parents=True,exist_ok=False)
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    with gzip.open(output/'cashflow-intervals.csv.gz','wt') as stream:
        writer=csv.writer(stream);writer.writerow(['funding_time_ms','minimum_cost','maximum_cost','inventory_states']);writer.writerows(records)
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('root','warmup','repairs','evidence','output'):p.add_argument('--'+n,type=Path,required=True)
    run(**vars(p.parse_args()))
