"""Preregistered causal relative-pricing screen. Not an account backtest."""
import argparse, bisect, csv, hashlib, io, json, zipfile
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
from research.persistent_hold_replay import inputs, HOUR
from coinquant.research import spec, invocations, timestamp
from coinquant.opportunities import Opportunities
from decimal import Decimal as D

DAY=24*HOUR

def stamp(t):return datetime.fromtimestamp(t/1000,timezone.utc).isoformat()
def month(t):return stamp(t)[:7]
def valid(r):
    t=int(r[0]);o,h,l,c,v,q=map(float,[r[1],r[2],r[3],r[4],r[5],r[7]])
    return (int(r[6])==t+HOUR-1 and np.isfinite([o,h,l,c,v,q]).all()
            and 0<l<=min(o,c)<=max(o,c)<=h and v>0 and q>0 and l*.999999<=q/v<=h*1.000001)

def spot_rows(root):
    manifest=json.loads((root/'manifest.json').read_text());rows={};bad=[]
    for item in manifest['records']:
        raw=(root/item['file']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=item['sha256']:raise ValueError('spot hash')
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            for r in csv.reader(io.StringIO(z.read(z.namelist()[0]).decode())):
                t=int(r[0])
                if t in rows:raise ValueError('duplicate spot hour')
                if not valid(r):bad.append(t);continue
                rows[t]=r
    return rows,bad,manifest

def features(t,spot,trade,opportunities):
    # The final observed candle closes one full hour before the invocation.
    end=t-HOUR
    windows=[list(range(end-24*HOUR,end,HOUR)),list(range(end-48*HOUR,end-24*HOUR,HOUR))]
    if any(x not in spot or x not in trade or not valid(trade[x]) for w in windows for x in w):return None
    def premium(w):
        def vwap(src):return sum(float(src[x][7]) for x in w)/sum(float(src[x][5]) for x in w)
        return vwap(spot)/vwap(trade)-1
    level,old=map(premium,windows)
    last=end-HOUR
    if last-168*HOUR not in trade:return None
    close=lambda x:float(trade[x][4])
    changes=np.diff(np.log([close(x) for x in range(last-168*HOUR,last+HOUR,HOUR)]))
    controls=[close(last)/close(last-24*HOUR)-1,close(last)/close(last-168*HOUR)-1,float(np.std(changes)),opportunities.get(end//(4*HOUR)*(4*HOUR),0)]
    return [level,level-old,*controls]

def direction_label(t,u,side,trade,marks,funding):
    friction=float(spec()['slippage_fraction'])+float(spec()['spread_fraction'])/2
    entry=float(trade[t][1])*(1+side*friction);exit=float(trade[u][1])*(1-side*friction)
    cost=.00075*(entry+exit);worst=best=0.
    for ft,rate in funding.items():
        boundary=abs(ft-t)<=15000 or abs(ft-u)<=15000
        if t<ft<u or boundary:
            r=marks[ft//HOUR*HOUR];rate=float(rate)
            lo,hi=float(r[3]),float(r[2])
            adverse=side*rate*(hi if side*rate>0 else lo)
            favorable=side*rate*(lo if side*rate>0 else hi)
            worst+=max(0.,adverse) if boundary else adverse
            best+=min(0.,favorable) if boundary else favorable
    return (side*(exit-entry)-cost-worst)/entry,(side*(exit-entry)-cost-best)/entry

def make_samples(spot,trade,marks,funding,warm):
    model=Opportunities('impulse_hold');opps={};alltrade=warm|trade
    for t in range(min(warm),max(trade)+HOUR,4*HOUR):
        rows=[alltrade[x] for x in range(t,t+4*HOUR,HOUR)]
        a=model.update(t+4*HOUR,max(D(r[2]) for r in rows),min(D(r[3]) for r in rows),D(rows[-1][4]))
        opps[t+4*HOUR]=a.direction if a else 0
    triggers=[t for t in invocations(spec()) if t<timestamp(spec()['development_end'])]
    samples=[];next_entry=0;missing=0
    for t in triggers:
        k=bisect.bisect_left(triggers,t+7*DAY)
        if k==len(triggers):continue
        u=triggers[k];x=features(t,spot,alltrade,opps)
        # Select nonoverlap clock independently of feature validity.
        primary=t>=next_entry
        if primary:next_entry=u
        if x is None:missing+=1;continue
        long=direction_label(t,u,1,trade,marks,funding);short=direction_label(t,u,-1,trade,marks,funding)
        samples.append(dict(t=t,u=u,month=month(t),primary=primary,x=x,gross=float(trade[u][1])/float(trade[t][1])-1,long=long,short=short))
    return samples,missing,opps

def fit_predict(train,test):
    a=np.array([r['x'] for r in train]);b=np.array([r['x'] for r in test]);y=np.array([r['gross'] for r in train])
    mean=a.mean(0);sd=a.std(0);sd[sd<1e-12]=1
    a=(a-mean)/sd;b=(b-mean)/sd
    c=np.column_stack([np.ones(len(a)),a[:,2:]]);d=np.column_stack([np.ones(len(b)),b[:,2:]])
    beta=np.linalg.lstsq(c,y,rcond=None)[0];base=d@beta
    z=a[:,:2].mean(1);zt=b[:,:2].mean(1)
    gamma=np.linalg.lstsq(c,z,rcond=None)[0];res=z-c@gamma;rest=zt-d@gamma
    slope=float(res@(y-c@beta)/(res@res)) if res@res>1e-12 else 0.
    r2=1-float(res@res)/float(((z-z.mean())**2).sum()) if np.var(z)>0 else 1.
    return base,base+max(0,slope)*rest,base+min(0,slope)*rest,slope,r2

def evaluate(samples):
    rows=[];fits=[]
    for m in sorted({r['month'] for r in samples if r['month']>='2022-01'}):
        boundary=timestamp(m+'-01T00:00:00Z')
        train=[r for r in samples if r['primary'] and r['u']<boundary-7*DAY]
        test=[r for r in samples if r['month']==m and r['primary']]
        if not test:continue
        if len(train)<30:raise ValueError('insufficient preregistered training samples')
        pred=fit_predict(train,test);fits.append(dict(month=m,n=len(train),max_training_exit=max(r['u'] for r in train),slope=pred[3],score_control_r2=pred[4]))
        for i,r in enumerate(test):
            out={k:v for k,v in r.items() if k!='x'}
            for name,values in zip(('control','continuation','reversal'),pred[:3]):
                p=float(values[i]);side=1 if p>0 else -1 if p<0 else 0
                out[name]=dict(pred=p,net=r['long'][0] if side>0 else r['short'][0] if side<0 else 0.,side=side)
            rows.append(out)
    report={}
    rng=np.random.default_rng(20260921)
    for name in ('control','continuation','reversal'):
        report[name]={}
        for period in ('all','2022','2023'):
            rs=[r for r in rows if period=='all' or r['month'].startswith(period)]
            diff=np.array([r[name]['net']-r['control']['net'] for r in rs]);nets=np.array([r[name]['net'] for r in rs])
            report[name][period]=dict(n=len(rs),mean_net=float(nets.mean()),mean_increment=float(diff.mean()),mse=float(np.mean([(r[name]['pred']-r['gross'])**2 for r in rs])),positive=int((nets>0).sum()))
        blocks={m:np.array([r[name]['net']-r['control']['net'] for r in rows if r['month']==m]) for m in sorted({r['month'] for r in rows})}
        keys=list(blocks);boot=[]
        for _ in range(2000):
            picked=rng.choice(keys,len(keys));values=np.concatenate([blocks[k] for k in picked]);boot.append(values.mean())
        diffs=np.array([r[name]['net']-r['control']['net'] for r in rows])
        report[name]['robustness']=dict(month_block_mean_increment_95=np.quantile(boot,[.025,.975]).tolist(),leave_one_month_out_min=float(min(np.concatenate([v for k,v in blocks.items() if k!=m]).mean() for m in keys)),drop_best_three_mean_increment=float(np.sort(diffs)[:-3].mean()),changed_directions=sum(r[name]['side']!=r['control']['side'] for r in rows))
    return report,rows,fits

def run(native,spot,output):
    output.mkdir(parents=True,exist_ok=False)
    s,f,w,identity=inputs(native,Path('evidence/binance-boundary-20260921'),Path('evidence/binance-mark-repair-20260921'))
    sp,bad,manifest=spot_rows(spot);samples,missing,opps=make_samples(sp,s['klines'],s['markPriceKlines'],f,w)
    report,rows,fits=evaluate(samples)
    shared=sorted(set(sp)&set(s['klines']));close=np.array([float(sp[t][4])/float(s['klines'][t][4])-1 for t in shared]);vwap=np.array([(float(sp[t][7])/float(sp[t][5]))/(float(s['klines'][t][7])/float(s['klines'][t][5]))-1 for t in shared])
    diagnostics=dict(valid_hours=len(shared),rejected_spot=bad,missing_hours=sorted(set(s['klines'])-set(sp)),omitted_samples=missing,samples=len(samples),nonoverlap_samples=sum(r['primary'] for r in samples),close_vwap_correlation=float(np.corrcoef(close,vwap)[0,1]),close_minus_vwap_abs_quantiles=np.quantile(abs(close-vwap),[.5,.95,.99,1]).tolist(),close_sign_disagreement=float(np.mean(np.sign(close)!=np.sign(vwap))))
    result=dict(qualification='INFORMATION_SCREEN_NOT_ACCOUNT',evaluation=report,diagnostics=diagnostics,training=fits,input_identity=identity,spot_manifest=manifest,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),protocol_sha256=hashlib.sha256(Path('evidence/basis-direction-20260921/PROTOCOL.md').read_bytes()).hexdigest(),limitations=['Retrospective mechanism design; chronological fitting is not independent unseen evidence','No account, margin, liquidation, protection or account CAGR','VWAP is not simultaneous executable bid/ask','One-hour publication delay and open execution are assumptions','2024+ not examined for this mechanism'])
    for name,data in [('result.json',result),('samples.json',samples),('predictions.json',rows)]:
        (output/name).write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(dict(evaluation=report,diagnostics={k:v for k,v in diagnostics.items() if k not in ('missing_hours','rejected_spot')}),indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('native','spot','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();run(a.native,a.spot,a.output)
