"""Summarize one uninterrupted diagnostic account; years never reset it."""
import argparse
import csv
from decimal import Decimal as D
import gzip
import json
from pathlib import Path
from pancakequant.research import iso


def summarize(root):
    result=json.loads((root/'result.json').read_text());years={};previous=None
    with gzip.open(root/'equity.csv.gz','rt') as f:
        for r in csv.DictReader(f):
            t=int(r['time']);year=iso(t-1 if r['event']=='close' else t)[:4]
            eq=D(r['equity_usdt']);fees=D(r['fees']);funding=D(r['funding'])
            if year not in years:
                beginning=previous if previous else dict(equity=eq,fees=D(0),funding=D(0))
                years[year]=dict(start=beginning['equity'],peak=beginning['equity'],mdd=D(0),hours=0,holding_hours=0,exposure_sum=D(0),margin_sum=D(0),max_margin=D(0),fees_start=beginning['fees'],funding_start=beginning['funding'])
            y=years[year];y['peak']=max(y['peak'],eq);y['mdd']=max(y['mdd'],1-eq/y['peak']);y['end']=eq;y['fees']=fees-y['fees_start'];y['funding']=funding-y['funding_start']
            if r['event']=='close':
                y['hours']+=1;y['holding_hours']+=bool(D(r['quantity']))
                y['exposure_sum']+=abs(D(r['quantity']))*D(r['mark'])/eq
                utilization=D(r['margin'])/eq;y['margin_sum']+=utilization;y['max_margin']=max(y['max_margin'],utilization)
                previous=dict(equity=eq,fees=fees,funding=funding)
    for y in years.values():
        y['net_return']=y['end']/y['start']-1
        y['gross_pnl_usdt']=y['end']-y['start']+y['fees']+y['funding']
        y['mean_exposure']=y.pop('exposure_sum')/y['hours'];y['mean_margin_equity']=y.pop('margin_sum')/y['hours']
        for k in ['fees_start','funding_start','peak']:y.pop(k)
    value=dict(candidate=result['candidate'],schedule=result['schedule'],yearly=years,counts=result['counts'],limitations=result['limitations'])
    (root/'attribution.json').write_text(json.dumps(value,indent=2,default=str)+'\n')
    return value

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('roots',nargs='+',type=Path);a=p.parse_args()
    for root in a.roots:
        value=summarize(root)
        print(root.name,json.dumps({y:{k:str(v[k]) for k in ['net_return','mdd','mean_exposure','fees','funding']} for y,v in value['yearly'].items()}))
