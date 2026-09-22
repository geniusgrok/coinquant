"""One frozen payoff-target comparison on the existing continuous account engine."""
import argparse
import bisect
import csv
import gzip
import hashlib
import json
from pathlib import Path
from decimal import Decimal as D
import numpy as np
from pancakequant.research import spec, invocations, timestamp, iso
from pancakequant.opportunities import Opportunities
from pancakequant.types import floor_step
from research.persistent_hold_replay import run as replay, inputs, HOUR, DAY, TICK
from research.minute_evidence import load as load_minutes

WARM = Path('evidence/binance-boundary-20260921')
REPAIR = Path('evidence/binance-mark-repair-20260921')
RULES = WARM/'current-instrument.json'


def load(native, full=False):
    bundle=inputs(native,WARM,REPAIR,full)
    end=timestamp(spec()['end' if full else 'development_end'])
    days=[p.stem[-10:] for p in (native/'daily/klines/BTCUSDT/1m').glob('*.zip') if timestamp(p.stem[-10:]+'T00:00:00Z')<end]
    minutes=load_minutes(native,bundle[0],sorted(days))
    return bundle,minutes


def feature_table(bundle):
    series,_,warm,_=bundle;trade=warm|series['klines'];model=Opportunities('impulse_hold');opps={}
    for t in range(min(trade),max(trade)+HOUR,4*HOUR):
        rs=[trade[s] for s in range(t,t+4*HOUR,HOUR)]
        a=model.update(t+4*HOUR,max(D(r[2]) for r in rs),min(D(r[3]) for r in rs),D(rs[-1][4]))
        opps[t+4*HOUR]=a.direction if a else 0
    result={};friction=D(spec()['slippage_fraction'])+D(spec()['spread_fraction'])/2
    for t in invocations(spec()):
        if t not in series['klines']:continue
        prior=list(range(t-169*HOUR,t,HOUR))
        day_end=t//DAY*DAY
        stops=list(range(day_end-10*DAY,day_end,HOUR))
        if any(s not in trade for s in prior+stops):continue
        close=lambda s:float(trade[s][4])
        sl=floor_step(min(D(trade[s][3]) for s in stops),TICK)
        entry=D(trade[t][1])*(1+friction)
        x=[close(t-HOUR)/close(t-25*HOUR)-1,close(t-HOUR)/close(t-169*HOUR)-1,
           float(np.std(np.diff(np.log([close(s) for s in prior])))),opps.get(t//(4*HOUR)*(4*HOUR),0),float((entry-sl)/entry)]
        result[t]=x
    return result


def account(native,output,bundle,minutes,predictions,name,**options):
    return replay(native,WARM,REPAIR,output,quantity_rules=RULES,lifecycle='one_campaign',allocation='volatility',
        reference='long',risk_scale=D('3.6'),entry_side='long',full_window=options.pop('full_window',False),
        payoff=dict(name=name,predictions=predictions,**options),cached_inputs=bundle,cached_minutes=minutes)


def orders(path):
    with gzip.open(path/'orders.csv.gz','rt') as f:return list(csv.DictReader(f))


def make_labels(native,output,bundle,minutes):
    output.mkdir(parents=True,exist_ok=False);xs=feature_table(bundle)
    triggers=[t for t in invocations(spec()) if t<=max(bundle[0]['klines'])]
    frozen=spec();reference=D(frozen['initial_cny'])/D(frozen['cny_per_usd'])*(1-D(frozen['initial_conversion_cost']))
    rows=[];next_entry=0
    for i,t in enumerate(triggers):
        k=bisect.bisect_left(triggers,t+7*DAY)
        if k==len(triggers):
            rows.append(dict(t=t,status='unmatured_at_window_end'));continue
        u=triggers[k];primary=t>=next_entry
        if primary:next_entry=u
        row=dict(t=t,u=u,primary=primary,x=xs.get(t),month=iso(t)[:7])
        if t not in xs:
            row['status']='missing_features';rows.append(row);continue
        pair={};entry_records=[]
        for name,terminal in (('terminal',True),('protected',False)):
            folder=output/str(t)/name
            r=account(native,folder,bundle,minutes,{t:1.0},name,start=t,end=u+HOUR,scenario=True,terminal_label=terminal)
            fills=orders(folder);entries=[r for r in fills if r['event']=='entry'];entry_records.append(entries)
            exits=[r for r in fills if r['event'] not in ('entry','funding_adverse_bound')]
            pair[name]=dict(net=float((D(r['final_equity_usdt'])-reference)/reference),fees=r['fees_usdt'],funding=r['funding_bound_paid_usdt'],
                counts=r['counts'],entry=entries[0] if entries else None,exit=exits[-1] if exits else None,final=r['final_equity_usdt'])
        assert entry_records[0]==entry_records[1], 'paired entry/quantity differs'
        row.update(pair);row['status']='eligible' if entry_records[0] else 'unfunded_or_unsafe'
        rows.append(row)
        if i%50==0:print('labels',i+1,'/',len(triggers),flush=True)
    (output/'labels.json').write_text(json.dumps(rows,indent=2)+'\n')
    return rows


def fit_targets(train,test):
    a=np.array([r['x'] for r in train]);b=np.array(test)
    mean=a.mean(0);sd=a.std(0);sd[sd<1e-12]=1
    a=np.column_stack([np.ones(len(a)),(a-mean)/sd]);b=np.column_stack([np.ones(len(b)),(b-mean)/sd])
    penalty=np.eye(a.shape[1]);penalty[0,0]=0
    y=np.array([[r[k]['net'] for k in ('terminal','protected')] for r in train])
    beta=np.linalg.solve(a.T@a+penalty,a.T@y)
    return b@beta,dict(mean=mean.tolist(),sd=sd.tolist(),beta=beta.tolist())


def predict(rows,xs):
    predictions={name:{} for name in ('B0','B1')};fits=[];details=[]
    for m in sorted({iso(t)[:7] for t in xs}):
        boundary=timestamp(m+'-01T00:00:00Z')
        train=[r for r in rows if r.get('status')=='eligible' and r['primary'] and r['u']<boundary-7*DAY]
        ts=sorted(t for t in xs if iso(t)[:7]==m)
        if len(train)<30:
            fits.append(dict(month=m,n=len(train),cold=True));continue
        values,params=fit_targets(train,[xs[t] for t in ts])
        fits.append(dict(month=m,n=len(train),max_training_maturity=max(r['u'] for r in train),cold=False,**params))
        for t,v in zip(ts,values):
            for i,name in enumerate(predictions):predictions[name][t]=float(v[i])
            details.append(dict(t=t,B0=float(v[0]),B1=float(v[1]),changed=bool((v[0]>0)!=(v[1]>0))))
    return predictions,fits,details


def rank(x):
    values=np.asarray(x);order=np.argsort(values,kind='stable');r=np.empty(len(x),dtype=float)
    for value in np.unique(values):
        pos=np.flatnonzero(values[order]==value);r[order[pos]]=pos.mean()
    return r


def label_summary(rows):
    eligible=[r for r in rows if r['status']=='eligible'];a=np.array([r['terminal']['net'] for r in eligible]);b=np.array([r['protected']['net'] for r in eligible])
    exits={};infeasible=ambiguous=0
    for r in eligible:
        event=r['protected']['exit']['event'] if r['protected']['exit'] else 'open'
        exits[event]=exits.get(event,0)+1
        infeasible+=bool(r['terminal']['counts'].get('hypothetical_liquidation_crossing'))
        ambiguous+=bool(r['protected']['counts'].get('unresolved_same_interval_stop_liquidation'))
    return dict(total=len(rows),eligible=len(eligible),status_counts={s:sum(r['status']==s for r in rows) for s in {r['status'] for r in rows}},
        sign_changes=int(np.sum((a>0)!=(b>0))),mean_terminal=float(a.mean()),mean_protected=float(b.mean()),
        mean_abs_difference=float(abs(a-b).mean()),rank_correlation=float(np.corrcoef(rank(a),rank(b))[0,1]),
        protected_exits=exits,hypothetical_liquidation_scenarios=infeasible,protected_liquidation_stop_ambiguous=ambiguous,
        largest_differences=[dict(t=eligible[i]['t'],terminal=float(a[i]),protected=float(b[i])) for i in np.argsort(abs(b-a))[-10:][::-1]])


def run(native,output,labels_path=None,full=False):
    output.mkdir(parents=True,exist_ok=False)
    bundle,minutes=load(native,full)
    rows=json.loads(labels_path.read_text()) if labels_path else make_labels(native,output/'scenarios',bundle,minutes)
    xs=feature_table(bundle);predictions,fits,details=predict(rows,xs)
    for name,value in [('fits',fits),('predictions',details),('label_summary',label_summary(rows))]:
        (output/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
    results={}
    for name in ('B0','B1'):
        results[name]=account(native,output/name,bundle,minutes,predictions[name],name,full_window=full)
    (output/'comparison.json').write_text(json.dumps(results,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--labels',type=Path);p.add_argument('--full-window',action='store_true')
    a=p.parse_args();run(a.native,a.output,a.labels,a.full_window)
