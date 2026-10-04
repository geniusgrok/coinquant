"""Gated finite account screen; never reruns accounts without an entrant."""
import argparse
from contextlib import nullcontext
from datetime import datetime, timezone
from decimal import Decimal as D
import gzip
import json
from pathlib import Path
import tempfile
import time
from unittest.mock import patch

from research import persistent_routes as routes


def selected(screen,kind):
    choices={name:r for group in screen['projects'][kind].values() for name,r in group.items()}
    order=json.loads(routes.SPEC.read_text())['account_screen']['entrant_order']
    return next(((name,choices[name]) for name in order if name in choices and choices[name]['status']=='ACCOUNT_ENTRANT'),None)


def quarter(stamp):
    d=datetime.fromtimestamp(stamp/1000,timezone.utc)
    month=1+3*((d.month-1)//3)
    begin=datetime(d.year,month,1,tzinfo=timezone.utc)
    end=datetime(d.year+1,1,1,tzinfo=timezone.utc) if month==10 else datetime(d.year,month+3,1,tzinfo=timezone.utc)
    return int(begin.timestamp()*1000),int(end.timestamp()*1000)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kind',choices=('spot','coin'),required=True)
    p.add_argument('--screen',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--market',type=Path);p.add_argument('--prints',type=Path)
    p.add_argument('--fx',type=Path);p.add_argument('--features',type=Path)
    p.add_argument('--schedule',type=Path)
    args=p.parse_args(argv)
    if args.out.exists():raise ValueError('preserve prior account results')
    raw=args.screen.read_bytes();screen=json.loads(raw)
    if screen['spec_sha256']!=routes.f.sha(routes.SPEC.read_bytes()):raise ValueError('registered account question changed')
    from research.rebuild import source_identity
    source=source_identity()
    if source['dirty']:raise ValueError('freeze source before financial work')
    candidate=selected(screen,args.kind)
    args.out.mkdir(parents=True)
    report=dict(format='btc-persistent-accounts-v1',source=source,screen_sha256=routes.f.sha(raw),
                original795_replays=0,new_accounts=0,new_sessions=0,rows=[],runtime_promoted=False)
    if candidate is None:
        report.update(status='NO_ACCOUNT_ENTRANT',reason='Every registered branch failed its economic or independent-opportunity gate; no zero-treatment account matrix.')
    else:
        name,event_screen=candidate
        if args.kind=='coin' and name not in ('state-trend','state-range'):
            raise ValueError('Lifecycle event attribution has not admitted a protected account execution bridge; no speculative runtime replacement')
        if not all(getattr(args,k) for k in ('market','fx','features')):raise ValueError('entrant requires original market/FX/feature inputs')
        spec=json.loads(routes.SPEC.read_text())
        events=event_screen['events']
        windows=[]
        for early in (True,False):
            eligible=[e for e in events if (e['time_ms']<routes.f.CUT)==early]
            if eligible:windows.append(quarter(min(e['time_ms'] for e in eligible)))
        if args.schedule is None:raise ValueError('original source-bound schedule required for an entrant')
        starts=json.loads(args.schedule.read_text())['primary']['starts_ms']
        if routes.f.sha(json.dumps(starts,separators=(',',':')).encode())!=spec['contract']['schedule_sha256']:
            raise ValueError('original starts changed')
        began=time.monotonic()
        if args.kind=='spot':
            from research import complete_spot as meter,persistent_spot as policy
            from research.edge_features import FeatureBook
            from research.edge_spot import FEATURE_SHA256
            from research.market import load_daily
            fx=meter.PriorFX(args.fx)
            bars=load_daily(args.market/'klines',routes.f.END,require_through=routes.f.END)
            features=FeatureBook(args.features,FEATURE_SHA256)
            inputs=[];causal=routes.f.market(args.market,routes.f.DAY,inputs)
            original=meter.START_MS,meter.END_MS
            try:
                for begin,end in windows:
                    if time.monotonic()-began>1800:break
                    subset=[s for s in starts if begin<=s<end]
                    if len(subset)>40:raise ValueError('registered finite account budget exceeded')
                    meter.START_MS,meter.END_MS=begin,end
                    rows={}
                    for label in ('baseline','candidate','uniform'):
                        row=(meter.measure('crowding-interaction','base',bars,subset,fx,features,canonical=True)
                             if label=='baseline' else policy.measure(name if label=='candidate' else 'uniform',bars,subset,fx,features,causal))
                        if label=='baseline':row.update(window_account_finished=row.pop('complete'),complete=False,cagr=None)
                        rows[label]=row
                    save_window(report,args.out,begin,end,rows)
            finally:meter.START_MS,meter.END_MS=original
        else:
            if args.prints is None:raise ValueError('verified original public prints required')
            from research import structure_screen as finite,persistent_perp as policy
            from research.session_market import load_base
            from research.unified_perp import PriorFX
            from functools import lru_cache
            market=load_base(args.market);market._load_month=lru_cache(maxsize=8)(market._load_month)
            fx=PriorFX(args.fx);inputs=[];causal=routes.f.market(args.market,routes.f.FOUR,inputs)
            warm_raw=(routes.SPEC.parent.parent/'evidence/binance-boundary-20260921/warmup-trade.json').read_bytes()
            if routes.f.sha(warm_raw)!=routes.f.WARMUP:raise ValueError('warmup changed')
            warm=dict(routes.f.kline(r,3600000) for r in json.loads(warm_raw))
            for h in sorted(warm):
                if h%routes.f.FOUR==0 and all(h+i*3600000 in warm for i in range(4)):
                    values=[warm[h+i*3600000] for i in range(4)]
                    causal[h]=(values[0][0],max(r[1] for r in values),min(r[2] for r in values),values[-1][3],
                               sum(r[4] for r in values),sum(r[5] for r in values))
            with tempfile.TemporaryDirectory(prefix='persistent-accounts-') as directory:
                tape=finite.BoundedPrints(Path(directory)/'prints',args.prints)
                for begin,end in windows:
                    if time.monotonic()-began>1800:break
                    subset=[s for s in starts if begin<=s<end]
                    if len(subset)>40:raise ValueError('registered finite account budget exceeded')
                    journal=[]
                    with patch.object(finite.candidate,'variant',lambda:policy.variant(name,causal,journal)):
                        rows=finite.window(market,tape,fx,subset,begin,end,Path(directory)/str(begin))
                    treatments={e['opportunity'] for e in journal if e['event']=='decision'
                        and (e.get('trigger') or {}).get('signal_family')==name and D(e.get('quantity_after','0'))>0}
                    rows['candidate']['treatment_fill_events']=len(treatments)
                    rows['candidate']['opportunity_ledger']=journal
                    with patch.object(finite.candidate,'variant',lambda:policy.variant('uniform',causal,[])):
                        control=finite.window(market,tape,fx,subset,begin,end,Path(directory)/(str(begin)+'-control'),rows['baseline'])
                    rows['uniform']=control['candidate']
                    save_window(report,args.out,begin,end,rows)
        report['wall_seconds']=time.monotonic()-began
        good=bool(report['rows']) and len(report['rows'])==2 and all(r['passed'] for r in report['rows'])
        report['status']='FINAL_COMPARISON_ENTRANT' if good else 'SCREEN_REJECTED_OR_SUPPORT_PENDING'
        report['candidate']=name
    (args.out/'summary.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('rows','source')},default=str))


def save_window(report,out,begin,end,rows):
    index=len(report['rows']);summary={}
    for label,row in rows.items():
        path=out/f'window-{index}-{label}.json.gz'
        with gzip.open(path,'wt') as handle:json.dump(row,handle,default=str,separators=(',',':'))
        summary[label]=dict(final_cny=row['final_cny'],mdd=row['mdd'],finished=row['window_account_finished'],
            audits_passed=row['audit']['passed'],sessions=len(row['sessions']),treatments=row.get('treatment_fill_events',0),
            raw_file=path.name,raw_sha256=routes.f.sha(path.read_bytes()))
        report['new_accounts']+=1;report['new_sessions']+=len(row['sessions'])
    base,candidate,uniform=(summary[n] for n in ('baseline','candidate','uniform'))
    wealth=float(candidate['final_cny'])/float(base['final_cny']);draw=float(candidate['mdd'])
    passed=(all(x['finished'] and x['audits_passed'] for x in summary.values()) and candidate['treatments']>0
        and ((wealth>=1 and draw<=float(base['mdd'])+.01) or (draw<=float(base['mdd'])*.8 and wealth>=.95))
        and float(candidate['final_cny'])>float(uniform['final_cny']) and draw<=float(uniform['mdd'])+.01)
    report['rows'].append(dict(window=[begin,end],**summary,passed=passed))


if __name__=='__main__':main()
