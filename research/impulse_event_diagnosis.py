"""Development event pairing; common units separate timing from account sizing."""
import csv,gzip,json
from collections import Counter,defaultdict
from decimal import Decimal as D
from pathlib import Path
from research.persistent_hold_replay import inputs,HOUR
from pancakequant.opportunities import Opportunities
from research.linear_replay import FEE


def read(root,name):
    with gzip.open(root/(name+'.csv.gz'),'rt') as f:return list(csv.DictReader(f))


def diagnose(native,runs,out,mechanism='impulse_hold'):
    series,funding,warm,identity=inputs(native,Path('evidence/binance-boundary-20260921'),Path('evidence/binance-mark-repair-20260921'))
    trade=series['klines'];start=min(trade);end=max(trade)+HOUR;m=Opportunities(mechanism);events={};states={};prior=None
    for t in range(min(warm),end,4*HOUR):
        src=warm if t<start else trade;rs=[src[x] for x in range(t,t+4*HOUR,HOUR)];close=D(rs[-1][4])
        a=m.update(t+4*HOUR,max(D(r[2]) for r in rs),min(D(r[3]) for r in rs),close);states[t+4*HOUR]=a
        if prior and (not a or a.identity!=prior.identity):events[prior.identity]['market_end']=t+4*HOUR
        if a and a.identity not in events:events[a.identity]=dict(identity=a.identity,direction=a.direction,signal_close=str(close),stop=str(a.stop),take=str(a.take),expires=a.expires,market_end=end)
        prior=a
    events={t:e for t,e in events.items() if e['market_end']>start}
    by_mode={};summary={}
    for mode in ('four_hour','sparse'):
        root=runs/mode;decisions=read(root,'decisions');entries={int(r['time']):r for r in decisions if r['action']=='entry'};trades={};active=None;last=None
        for r in read(root,'orders'):
            t=int(r['time']);q=D(r['quantity_btc']);p=D(r['price_or_mark'])
            if r['event']=='entry':
                a=states[t//(4*HOUR)*(4*HOUR)];e=events[a.identity];R=abs(D(e['signal_close'])-D(e['stop']))
                active=dict(event=a.identity,side=a.direction,entry=t,entry_price=str(p),quantity=str(abs(q)),age_hours=(t-a.identity)/HOUR,
                    progress_R=str(D(a.direction)*(D(trade[t][1])-D(e['signal_close']))/R),
                    stop_distance_R=str(D(a.direction)*(p-a.stop)/R),
                    initial_R=str(R),entry_stop=str(a.stop),fees_per_btc=str(p*FEE),funding_per_btc='0',entry_equity=entries[t]['equity'])
                trades[a.identity]=active
            elif r['event']=='funding_adverse_bound':
                target=active or last
                assert target and abs(q)==D(target['quantity'])
                target['funding_per_btc']=str(D(target['funding_per_btc'])+D(target['side'])*p*D(r['funding_rate']))
            else:
                assert active,r
                active.update(exit=t,exit_price=str(p),exit_reason=r['event'])
                active['fees_per_btc']=str(D(active['fees_per_btc'])+p*FEE);last=active;active=None
        assert active is None,'development ends flat for frozen D3'
        for event,r in trades.items():
            r['net_per_btc']=str(D(r['side'])*(D(r['exit_price'])-D(r['entry_price']))-D(r['fees_per_btc'])-D(r['funding_per_btc']))
            r['net_R']=str(D(r['net_per_btc'])/D(r['initial_R']));r['net_cash']=str(D(r['net_per_btc'])*D(r['quantity']))
            r['stop_loss_cash_before_gap']=str(D(r['quantity'])*(D(r['side'])*(D(r['entry_price'])-D(r['entry_stop']))+FEE*(D(r['entry_price'])+D(r['entry_stop']))+D(r['entry_stop'])*D('.0011')))
        by_mode[mode]=trades
        missing=[]
        for event,e in events.items():
            if event in trades:continue
            available=[r for r in decisions if max(start,event)<=int(r['time'])<e['market_end']]
            first=next((int(r['time']) for r in decisions if int(r['time'])>=event),None)
            missing.append(dict(event=event,first_invocation=first,market_end=e['market_end'],reason='no_invocation_during_market_life' if not available else 'invoked_not_entered',actions=dict(Counter(r['action'] for r in available))))
        summary[mode]=dict(entries=len(trades),missed=missing,side={side:dict(n=sum(r['side']==side for r in trades.values()),net_cash=str(sum((D(r['net_cash']) for r in trades.values() if r['side']==side),D(0))),net_R_sum=str(sum((D(r['net_R']) for r in trades.values() if r['side']==side),D(0)))) for side in (1,-1)})
    paired=[]
    for event,e in events.items():
        n=by_mode['four_hour'].get(event);s=by_mode['sparse'].get(event);row=dict(event=e,normal=n,sparse=s)
        if n and s:
            entry=-D(e['direction'])*(D(s['entry_price'])-D(n['entry_price']));exit=D(e['direction'])*(D(s['exit_price'])-D(n['exit_price']))
            cost=-(D(s['fees_per_btc'])+D(s['funding_per_btc'])-D(n['fees_per_btc'])-D(n['funding_per_btc']))
            assert abs(entry+exit+cost-(D(s['net_per_btc'])-D(n['net_per_btc'])))<D('1e-18')
            row['timing_delta_R']={k:str(v/D(n['initial_R'])) for k,v in [('entry',entry),('exit',exit),('cost',cost)]}
            timing=D(s['quantity'])*(D(s['net_per_btc'])-D(n['net_per_btc']))
            sizing=(D(s['quantity'])-D(n['quantity']))*D(n['net_per_btc'])
            assert abs(timing+sizing-(D(s['net_cash'])-D(n['net_cash'])))<D('1e-18')
            row['cash_decomposition']=dict(timing_at_sparse_quantity=str(timing),quantity_path_at_normal_unit_pnl=str(sizing))
        for r in (n,s):
            if r and r['entry']+24*HOUR in trade:
                t=r['entry'];finish=t+24*HOUR
                r['next24h_diagnostic_return']=str(D(e['direction'])*(D(trade[finish][1])/D(trade[t][1])-1)-D('.0037')-sum((D(e['direction'])*rate for ft,rate in funding.items() if t<=ft<finish),D(0)))
        paired.append(row)
    # Broad economically defined categories only; no age-threshold search.
    groups={}
    for side in (1,-1):
        for label,fn in [('all',lambda r:True),('price_advanced',lambda r:D(r['progress_R'])>0),('not_advanced',lambda r:D(r['progress_R'])<=0)]:
            rows=[r for r in by_mode['sparse'].values() if r['side']==side and fn(r)]
            groups[f'{side}:{label}']=dict(n=len(rows),mean_age_hours=sum(r['age_hours'] for r in rows)/len(rows) if rows else None,net_R_sum=str(sum((D(r['net_R']) for r in rows),D(0))),net_cash=str(sum((D(r['net_cash']) for r in rows),D(0))))
    out.mkdir(parents=True,exist_ok=True)
    (out/'paired-events.json').write_text(json.dumps(paired,indent=2)+'\n')
    report=dict(qualification='DIAGNOSTIC_ONLY',window_end='2024-01-01',input_identity=identity,summary=summary,broad_groups=groups,limitations=['Small dependent event sample; groups are descriptive, not causal treatment effects.','Common BTC/R units remove quantity but not hypothetical financing/execution constraints.','No counterfactual PnL is credited to account.'])
    (out/'diagnosis.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(summary=summary,broad_groups=groups),indent=2))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser()
    for k in ('native','runs','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();diagnose(a.native,a.runs,a.output)
