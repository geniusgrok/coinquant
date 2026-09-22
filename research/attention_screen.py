"""One preregistered retrospective attention screen; no production/account writes."""
import argparse
import bisect
from collections import Counter
import hashlib
import json
from pathlib import Path
import numpy as np
from coinquant.research import timestamp, iso
from research.executable_payoff import fit_targets, rank, DAY


def load_daily(raw):
    daily={};sources=[]
    for path in sorted(raw.glob('wiki_full_*.body')):
        meta=json.loads(path.with_suffix('.json').read_text());body=path.read_bytes()
        assert meta['status']==200 and hashlib.sha256(body).hexdigest()==meta['sha256']
        sources.append(meta)
        for row in json.loads(body)['items']:
            assert (row['project'],row['article'],row['access'],row['agent'],row['granularity'])==('en.wikipedia','Bitcoin','all-access','user','daily')
            assert type(row['views']) is int and row['views']>=0
            s=row['timestamp'];t=timestamp(f'{s[:4]}-{s[4:6]}-{s[6:8]}T00:00:00Z')
            assert s[8:]=='00' and t not in daily
            daily[t]=row['views']
    if not daily:raise ValueError('no count data; do not produce economic results')
    return daily,sources


def weeks(daily):
    # Fixed Monday epoch. Never sum an incomplete week or backfill an absent day.
    anchor=timestamp('2019-10-28T00:00:00Z');week=7*DAY
    first=anchor+(min(daily)-anchor)//week*week
    totals={};records=[]
    for start in range(first,max(daily)+DAY,week):
        days=list(range(start,start+week,DAY))
        totals[start]=sum(daily[t] for t in days) if all(t in daily for t in days) else None
        history=[totals.get(start-j*week) for j in range(5)]
        value=history[0]-sum(history[1:])/4 if all(v is not None for v in history) else None
        records.append(dict(period_start=start,period_end=start+week,available_at=None,
                            assumed_available_at=start+week+2*DAY,vintage_status='RETROSPECTIVE_PROXY',
                            count=totals[start],attention=value))
    return records


def features(records,times,extra_lag=0):
    ends=[r['assumed_available_at']+extra_lag for r in records];result={};missing={}
    for t in times:
        i=bisect.bisect_right(ends,t)-1
        if i<0:missing[t]='unpublished';continue
        r=records[i]
        if t-ends[i]>=7*DAY:missing[t]='stale';continue
        if r['attention'] is None:missing[t]='incomplete_week_or_reference';continue
        result[t]=dict(value=r['attention'],week_end=r['period_end'],assumed_available_at=ends[i],available_at=None)
    return result,missing


def predict(rows,attention):
    fits=[];details=[]
    for month in sorted({r['month'] for r in rows if r.get('x') is not None}):
        boundary=timestamp(month+'-01T00:00:00Z')
        train=[r for r in rows if r.get('status')=='eligible' and r['primary'] and r['u']<boundary-7*DAY and r['t'] in attention]
        test=[r for r in rows if r.get('month')==month and r.get('x') is not None and r['t'] in attention]
        fit=dict(month=month,n=len(train),train_times=[r['t'] for r in train],cold=len(train)<30)
        if len(train)<30:
            fits.append(fit);continue
        if not test:
            fits.append(fit);continue
        # Reuse original regression implementation; only the protected column is used.
        p1,params1=fit_targets(train,[r['x'] for r in test])
        augment=lambda r:dict(r,x=r['x']+[attention[r['t']]['value']])
        p2,params2=fit_targets([augment(r) for r in train],[augment(r)['x'] for r in test])
        c0=float(np.mean([r['protected']['net'] for r in train]))
        fit.update(max_training_maturity=max(r['u'] for r in train),C0=c0,C1=params1,C2=params2)
        fits.append(fit)
        for r,a,b in zip(test,p1,p2):
            details.append(dict(t=r['t'],u=r['u'],month=month,primary=r['primary'],status=r['status'],
                y=r['protected']['net'] if r['status']=='eligible' else None,
                C0=c0,C1=float(a[1]),C2=float(b[1]),**attention[r['t']]))
    return fits,details


def metrics(rows):
    if not rows:return dict(n=0)
    y=np.array([r['y'] for r in rows]);result=dict(n=len(rows),unique_updates=len({r['week_end'] for r in rows}),
        max_update_reuse=max(Counter(r['week_end'] for r in rows).values()))
    for name in ('C0','C1','C2'):
        p=np.array([r[name] for r in rows]);pay=(p>0)*y
        result[name]=dict(mse=float(np.mean((p-y)**2)),rank_correlation=float(np.corrcoef(rank(p),rank(y))[0,1]),
            entry_count=int(sum(p>0)),entry_fraction=float(np.mean(p>0)),reference_mean=float(pay.mean()))
    for control in ('C0','C1'):
        p=np.array([r['C2'] for r in rows]);c=np.array([r[control] for r in rows]);delta=((p>0).astype(int)-(c>0).astype(int))*y
        months=sorted({r['month'] for r in rows});blocks=[delta[[r['month']==m for r in rows]] for m in months]
        rng=np.random.default_rng(24877);boot=[]
        for _ in range(2000):
            chosen=[blocks[i] for i in rng.integers(0,len(blocks),len(blocks))];boot.append(float(np.concatenate(chosen).mean()))
        monthly={m:float(b.sum()) for m,b in zip(months,blocks)};best=max(monthly,key=monthly.get)
        leave=[float(np.concatenate([b for m,b in zip(months,blocks) if m!=drop]).mean()) for drop in months] if len(months)>1 else []
        result['C2-'+control]=dict(mean=float(delta.mean()),bootstrap95=np.quantile(boot,[.025,.975]).tolist(),
            changed=int(sum((p>0)!=(c>0))),flat_to_long=int(sum((p>0)&(c<=0))),long_to_flat=int(sum((p<=0)&(c>0))),
            monthly_contributions=monthly,best_month=best,best_month_contribution=monthly[best],
            best_month_share_of_net=monthly[best]/float(delta.sum()) if delta.sum()!=0 else None,
            sum_ex_best_month=float(delta.sum())-monthly[best],leave_one_month_mean_range=[min(leave),max(leave)] if leave else None)
    result['years']={year:dict(n=sum(r['month'][:4]==year for r in rows),**{
        name:float(np.mean([(r[name]>0)*r['y'] for r in rows if r['month'][:4]==year])) for name in ('C0','C1','C2')})
        for year in sorted({r['month'][:4] for r in rows})}
    return result


def run(labels,raw,output):
    output.mkdir(parents=True,exist_ok=False)
    body=labels.read_bytes();rows=json.loads(body);daily,sources=load_daily(raw);records=weeks(daily)
    times=[r['t'] for r in rows if r.get('x') is not None]
    attention,missing=features(records,times);lagged,lag_missing=features(records,times,7*DAY)
    fits,details=predict(rows,attention);lagfits,lagdetails=predict(rows,lagged)
    eligible=[r for r in details if r['status']=='eligible'];primary=[r for r in eligible if r['primary']]
    primary_metrics=metrics(primary);all_metrics=metrics(eligible)
    lag_by_t={r['t']:r for r in lagdetails if r['status']=='eligible'}
    common=[r for r in eligible if r['t'] in lag_by_t]
    lag_metrics={name:metrics([r for r in data if r['primary']]) for name,data in (
        ('base_same_sample',common),('extra7days',[lag_by_t[r['t']] for r in common]))}
    gate=bool(primary and primary_metrics['C2-C1']['mean']>0 and primary_metrics['C2-C0']['mean']>0 and
        sum(r['C2']>r['C1'] for r in primary_metrics['years'].values())>=2 and primary_metrics['C2-C1']['sum_ex_best_month']>0)
    summary=dict(status='RETROSPECTIVE_PROXY',protocol_commit='c0fd62b7360eecd4385ed28600f16d1e5a42f4aa',
        labels_sha256=hashlib.sha256(body).hexdigest(),labels_total=len(rows),counts=len(daily),
        data_start=iso(min(daily)),data_end=iso(max(daily)+DAY),missing_days=[iso(t) for t in range(min(daily),max(daily)+DAY,DAY) if t not in daily],
        explicit_zero_days=sum(v==0 for v in daily.values()),features=len(attention),feature_missing=missing,
        no_x=[r['t'] for r in rows if r.get('x') is None],predictions=len(details),cold_months=[r['month'] for r in fits if r['cold']],
        primary=primary_metrics,all_dependent=all_metrics,lag_sensitivity_primary=lag_metrics,
        continuous_account_gate=gate,formal_historical_availability='UNVERIFIED',sources=sources)
    for name,value in [('SUMMARY',summary),('weeks',records),('fits',fits),('predictions',details),('lag7_fits',lagfits),('lag7_predictions',lagdetails)]:
        (output/(name+'.json')).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:summary[k] for k in ('status','counts','features','predictions','continuous_account_gate')},indent=2))
    print(json.dumps(primary_metrics,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--labels',type=Path,required=True);p.add_argument('--raw',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.labels,a.raw,a.output)
