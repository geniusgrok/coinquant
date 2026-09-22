"""Preregistered spot continuation information screen; not an account backtest."""
import argparse
import bisect
import hashlib
import itertools
import json
from pathlib import Path
from decimal import Decimal as D
import numpy as np
from research.basis_direction import valid, direction_label, month, DAY
from research.persistent_hold_replay import inputs, HOUR
from research.linear_forecast import archive_rows
from coinquant.research import spec, invocations, timestamp
from coinquant.opportunities import Opportunities

HURDLE = .0037
NCONTROL = 6


def normalize(row):
    r = list(row)
    scale = 1000 if int(r[0]) >= 10**14 else 1
    if int(r[0]) % scale:
        raise ValueError('unaligned timestamp')
    r[0], r[6] = str(int(r[0]) // scale), str(int(r[6]) // scale)
    return r


def valid_flow(r):
    try:
        q, buy = float(r[7]), float(r[10])
        return valid(r) and np.isfinite(buy) and 0 <= buy <= q
    except (ValueError, IndexError, OverflowError):
        return False


def load_spot(root):
    manifest = json.loads((root / 'manifest.json').read_text())
    rows, bad, seen = {}, [], set()
    for item in manifest['records']:
        p = root / item['file']
        if hashlib.sha256(p.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('spot receipt mismatch')
        for raw in archive_rows(root, item['file']):
            r = normalize(raw)
            t = int(r[0])
            if t in seen:
                raise ValueError('duplicate spot hour')
            seen.add(t)
            if valid_flow(r): rows[t] = r
            else: bad.append(t)
    return rows, bad, manifest


def features(t, spot, trade, opps):
    end = t - HOUR  # last bar closes at t-1h, one hour publication lag
    windows = [list(range(end - n * HOUR, end, HOUR)) for n in (24, 168)]
    last = end - HOUR
    price_times = list(range(last - 168 * HOUR, last + HOUR, HOUR))
    if any(x not in trade or not valid_flow(trade[x]) for x in price_times): return None
    if any(x not in spot or not valid_flow(spot[x]) for x in windows[1]): return None
    def imbalance(src, w):
        q = sum(float(src[x][7]) for x in w)
        return 2 * sum(float(src[x][10]) for x in w) / q - 1
    close = lambda x: float(trade[x][4])
    controls = [close(last) / close(last - n * HOUR) - 1 for n in (24, 168)]
    controls += [float(np.std(np.diff(np.log([close(x) for x in price_times]))))]
    controls += [opps.get(end // (4 * HOUR) * (4 * HOUR), 0)]
    controls += [imbalance(trade, w) for w in windows]
    return controls + [imbalance(spot, w) for w in windows]


def samples_for(spot, trade, marks, funding, warm):
    model, opps = Opportunities('impulse_hold'), {}
    alltrade = warm | trade
    for t in range(min(warm), max(trade) + HOUR, 4 * HOUR):
        rs = [alltrade[x] for x in range(t, t + 4 * HOUR, HOUR)]
        a = model.update(t + 4 * HOUR, max(D(r[2]) for r in rs), min(D(r[3]) for r in rs), D(rs[-1][4]))
        opps[t + 4 * HOUR] = a.direction if a else 0
    triggers = [t for t in invocations(spec()) if t < timestamp(spec()['development_end'])]
    samples, omitted, next_entry = [], [], 0
    for t in triggers:
        k = bisect.bisect_left(triggers, t + 7 * DAY)
        if k == len(triggers): continue
        u = triggers[k]
        primary = t >= next_entry
        if primary: next_entry = u
        x = features(t, spot, alltrade, opps)
        if x is None:
            omitted.append(dict(t=t, u=u, primary=primary, reason='missing_or_invalid_feature'))
            continue
        samples.append(dict(t=t, u=u, primary=primary, month=month(t), x=x,
            gross=float(trade[u][1]) / float(trade[t][1]) - 1,
            long=direction_label(t,u,1,trade,marks,funding)[0],
            short=direction_label(t,u,-1,trade,marks,funding)[0],
            L_side=1 if opps.get(t // (4*HOUR)*(4*HOUR),0)>0 else 0))
    return samples, omitted


def fit(train, test):
    a = np.array([r['x'] for r in train]); b = np.array([r['x'] for r in test])
    y = np.array([r['gross'] for r in train])
    mean, sd = a.mean(0), a.std(0); sd[sd < 1e-12] = 1
    a = np.column_stack([np.ones(len(a)), (a-mean)/sd])
    b = np.column_stack([np.ones(len(b)), (b-mean)/sd])
    def solve(cols):
        c = a[:,cols]; penalty = np.eye(len(cols)); penalty[0,0] = 0
        beta = np.linalg.solve(c.T@c+penalty, c.T@y)
        loss = float(np.sum((y-c@beta)**2)+beta[1:]@beta[1:])
        return beta, loss
    controls = list(range(NCONTROL+1))
    base, _ = solve(controls)
    best = None
    for mask in itertools.product((False,True),repeat=2):
        cols = controls + [NCONTROL+1+i for i,active in enumerate(mask) if active]
        beta, loss = solve(cols)
        if np.any(beta[len(controls):]<0): continue
        if best is None or loss<best[0]: best=(loss,cols,beta)
    _, cols, beta = best
    full = np.zeros(9); full[cols]=beta
    return b[:,controls]@base, b@full, dict(mean=mean.tolist(),sd=sd.tolist(),control_beta=base.tolist(),expanded_beta=full.tolist())


def sequential(samples):
    rows, fits = [], []
    for m in sorted({r['month'] for r in samples}):
        boundary = timestamp(m+'-01T00:00:00Z')
        train = [r for r in samples if r['primary'] and r['u'] < boundary-7*DAY]
        test = [r for r in samples if r['month']==m]
        if len(train)<30:
            pred = (np.zeros(len(test)),np.zeros(len(test)),{})
        else: pred = fit(train,test)
        fits.append(dict(month=m,n=len(train),max_training_exit=max((r['u'] for r in train),default=None),cold_start=len(train)<30,**pred[2]))
        for i,r in enumerate(test):
            out={k:v for k,v in r.items() if k!='x'}
            for name, values in zip(('control','expanded'),pred[:2]):
                p=float(values[i]); side=1 if p>HURDLE else -1 if p<-HURDLE else 0
                out[name]=dict(pred=p,side=side,net=r['long'] if side>0 else r['short'] if side<0 else 0.)
            rows.append(out)
    return rows,fits


def summary(rows):
    if not rows: return dict(n=0)
    d=np.array([r['expanded']['net']-r['control']['net'] for r in rows])
    e=np.array([r['expanded']['net'] for r in rows])
    return dict(n=len(rows),control_mean_net=float(np.mean([r['control']['net'] for r in rows])),expanded_mean_net=float(e.mean()),
        paired_increment=float(d.mean()),long_mean_net=float(np.mean([r['long'] for r in rows])),
        L_signal_mean_net=float(np.mean([r['long']*r['L_side'] for r in rows])),
        changed_decisions=sum(r['expanded']['side']!=r['control']['side'] for r in rows),
        expanded_active=sum(r['expanded']['side']!=0 for r in rows),
        expanded_active_L_flat=sum(r['expanded']['side']!=0 and r['L_side']==0 for r in rows),
        expanded_L_flat_net_sum=float(sum(r['expanded']['net'] for r in rows if r['L_side']==0)))


def robustness(rows):
    d=np.array([r['expanded']['net']-r['control']['net'] for r in rows])
    e=np.array([r['expanded']['net'] for r in rows]); keys=sorted({r['month'] for r in rows})
    groups={m:np.array([i for i,r in enumerate(rows) if r['month']==m]) for m in keys}
    rng=np.random.default_rng(20260921)
    boot=[np.mean(np.concatenate([d[groups[m]] for m in rng.choice(keys,len(keys))])) for _ in range(2000)]
    best_delta=max(keys,key=lambda m:d[groups[m]].sum());best_profit=max(keys,key=lambda m:e[groups[m]].sum())
    return dict(month_block_95=np.quantile(boot,[.025,.975]).tolist(),
        drop_best_increment_event=float(np.delete(d,int(d.argmax())).mean()),
        drop_best_profit_event=float(np.delete(d,int(e.argmax())).mean()),
        drop_best_increment_month=float(np.mean([v for i,v in enumerate(d) if rows[i]['month']!=best_delta])),
        drop_best_profit_month=float(np.mean([v for i,v in enumerate(d) if rows[i]['month']!=best_profit])),
        best_increment_month=best_delta,best_profit_month=best_profit)


def run(native,spot,output):
    output.mkdir(parents=True,exist_ok=False)
    series,funding,warm,identity=inputs(native,Path('evidence/binance-boundary-20260921'),Path('evidence/binance-mark-repair-20260921'))
    sp,bad,manifest=load_spot(spot)
    samples,omitted=samples_for(sp,series['klines'],series['markPriceKlines'],funding,warm)
    rows,fits=sequential(samples)
    evaluation={}
    for name in ('all_invocations','nonoverlap'):
        selected=[r for r in rows if r['month']>='2022-01' and (name=='all_invocations' or r['primary'])]
        evaluation[name]={period:summary([r for r in selected if period=='all' or r['month'].startswith(period)]) for period in ('all','2022','2023')}
        evaluation[name]['robustness']=robustness(selected)
    primary=evaluation['nonoverlap']
    advance=(all(primary[y]['paired_increment']>0 for y in ('2022','2023'))
             and primary['robustness']['drop_best_increment_event']>0 and primary['robustness']['drop_best_increment_month']>0
             and evaluation['all_invocations']['all']['paired_increment']>0)
    result=dict(qualification='INFORMATION_SCREEN_NOT_ACCOUNT',advance=advance,evaluation=evaluation,
        samples=len(samples),primary_samples=sum(r['primary'] for r in samples),omitted=omitted,rejected_spot_hours=bad,
        input_identity=identity,spot_manifest=manifest,
        protocol_sha256=hashlib.sha256(Path('evidence/spot-flow-20260921/PROTOCOL.md').read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        limitations=['Proxy costs and delayed live-kline availability, not historically proven execution',
        'Revised archive vintages; not point-in-time raw snapshots','Sparse observations and reused historical research, not independent future validation',
        'No continuous account, margin, liquidation, native protection or CNY valuation measured'])
    for name,data in [('result',result),('samples',samples),('predictions',rows),('fits',fits)]:
        (output/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(dict(advance=advance,evaluation=evaluation,samples=len(samples),omitted=len(omitted)),indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('native','spot','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();run(a.native,a.spot,a.output)
