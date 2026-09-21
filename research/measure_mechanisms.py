"""Development-only, paired accounts and causal signal diagnostics."""
import argparse,csv,gzip,json
from pathlib import Path
from decimal import Decimal as D
from research.persistent_hold_replay import inputs,run,HOUR
from research.target_attribution import summarize
from pancakequant.opportunities import Opportunities


def measure(native,output,mechanism):
    warmup=Path('evidence/binance-boundary-20260921');repairs=Path('evidence/binance-mark-repair-20260921')
    series,funding,warm,identity=inputs(native,warmup,repairs);trade=series['klines'];start=min(trade);end=max(trade)+HOUR
    model=Opportunities(mechanism);events=[];last=None
    for t in range(min(warm),end,4*HOUR):
        source=warm if t<start else trade;bars=[source[x] for x in range(t,t+4*HOUR,HOUR)]
        a=model.update(t+4*HOUR,max(D(r[2]) for r in bars),min(D(r[3]) for r in bars),D(bars[-1][4]))
        if a and a.identity!=last and t+4*HOUR>=start:
            events.append((t+4*HOUR,a));last=a.identity
    screen={};raw=[]
    for horizon in ((24,168) if mechanism in ('squeeze','impulse','impulse_hold','persistent_impulse') else (4,24)):
        outcomes=[]
        for t,a in events:
            if t+horizon*HOUR>=end:continue
            price=D(trade[t][1]);exit=D(trade[t+horizon*HOUR][1])
            gross=D(a.direction)*(exit/price-1)
            # Forecast diagnostic, not a funded account or exact settlement cashflow.
            fund=sum((D(a.direction)*r for ft,r in funding.items() if t<=ft<t+horizon*HOUR),D(0))
            net=gross-D('.0037')-fund
            outcomes.append(net);raw.append([t,horizon,a.direction,str(gross),str(fund),str(net)])
        screen[horizon]=dict(events=len(outcomes),mean_net=str(sum(outcomes)/len(outcomes)) if outcomes else None,
            positive=sum(x>0 for x in outcomes),worst=str(min(outcomes)) if outcomes else None)
    output.mkdir(parents=True,exist_ok=True)
    (output/'screen.json').write_text(json.dumps(dict(mechanism=mechanism,qualification='DIAGNOSTIC_ONLY',horizons=screen,overlapping_not_independent=True),indent=2)+'\n')
    with gzip.open(output/'screen.csv.gz','wt') as f:
        w=csv.writer(f);w.writerow(['time','horizon_hours','direction','gross_return','funding_rate_sum','net_return']);w.writerows(raw)
    for schedule in ('four_hour','sparse'):
        dest=output/schedule
        days=[d for d in json.loads(Path('research/mechanism-minute-days.json').read_text()) if d<'2024-01-01']
        run(native,warmup,repairs,dest,native,False,schedule,warmup/'current-instrument.json','one_campaign','volatility',mechanism,'fixed',False,days)
        summarize(dest)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--mechanism',choices=('squeeze','sweep','shock','impulse','impulse_hold','persistent_impulse'),required=True)
    a=p.parse_args();measure(a.native,a.output,a.mechanism)
