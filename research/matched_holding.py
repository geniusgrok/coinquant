"""Matched-entry event accounts: descriptive holding attribution, never portfolio CAGR."""
import argparse,csv,gzip,json
from decimal import Decimal as D
from pathlib import Path
from coinquant.campaign import Campaign
from coinquant.linear_account import Account,FEE,MMR,TICK
from coinquant.types import floor_step
from research.persistent_hold_replay import inputs,decision_times,HOUR
from research.minute_evidence import load,steps
from coinquant.research import spec,timestamp


def run(native,baseline,output):
    output.mkdir(parents=True,exist_ok=False)
    frozen=spec();start=timestamp(frozen['start']);end=timestamp(frozen['development_end'])
    series,funding,warm,identity=inputs(native,Path('evidence/binance-boundary-20260921'),Path('evidence/binance-mark-repair-20260921'))
    days=[d for d in json.loads(Path('research/mechanism-minute-days.json').read_text())+['2021-01-02'] if d<'2024-01-01']
    minutes,mi=load(native,series,days);identity+=mi
    trade,marks=series['klines'],series['markPriceKlines'];opps={};bear=set();model=Campaign()
    for t in range(min(warm),end,4*HOUR):
        source=warm if t<start else trade;rs=[source[s] for s in range(t,t+4*HOUR,HOUR)]
        high=max(D(r[2]) for r in rs);low=min(D(r[3]) for r in rs);close=D(rs[-1][4])
        if len(model.model.tr)==14 and model.model.bars:
            if close-model.model.bars[-1][3]<-3*sum(model.model.tr)/14:bear.add(t+4*HOUR)
        opps[t+4*HOUR]=model.update(t+4*HOUR,high,low,close)
    decisions={int(r['time']):r for r in csv.DictReader(gzip.open(baseline/'decisions.csv.gz','rt'))}
    orders=list(csv.DictReader(gzip.open(baseline/'orders.csv.gz','rt')))
    entries=[r for r in orders if r['event']=='entry' and int(r['time'])<end]
    triggers=decision_times(frozen,end,'sparse');fh={t//HOUR*HOUR:(t,r) for t,r in funding.items()}
    friction=D(frozen['slippage_fraction'])+D(frozen['spread_fraction'])/2;results=[]
    for entry in entries:
        t0=int(entry['time']);q=D(entry['quantity_btc']);price=D(entry['price_or_mark']);initial=D(decisions[t0]['equity'])
        op=opps[t0//(4*HOUR)*(4*HOUR)];assert op and op.direction==1 and q>0
        sl=floor_step(op.stop,TICK);tp=floor_step(op.take,TICK)+TICK;mark0=D(marks[t0][1])
        margin=max(q*price/20,q*price-(q-q*(MMR+FEE))*(sl-mark0*D('.10')))
        expected=next(r for r in orders if int(r['time'])>t0 and r['event'] not in ('entry','funding_adverse_bound'))
        pair={'entry_time':t0,'campaign':op.identity,'quantity':str(q),'entry_price':str(price),'initial_wallet':str(initial)}
        for policy in ('control','opposing_impulse'):
            account=Account(initial-q*price*FEE,q=q,entry=price,margin=margin,sl=sl,tp=tp,fees=q*price*FEE)
            assert account.wallet>=margin+q*max(price,mark0)*(D('.01')+FEE)
            invalid=False;peak=initial;mdd=D(0);exit_record=None
            with gzip.open(output/f'{t0}-{policy}.csv.gz','wt') as stream:
                writer=csv.writer(stream);writer.writerow(['time','event','equity','quantity','mark','fees','funding'])
                def observe(t,event,mark):
                    nonlocal peak,mdd
                    equity=account.equity(mark);peak=max(peak,equity);mdd=max(mdd,1-equity/peak)
                    writer.writerow([t,event,str(equity),str(account.q),str(mark),str(account.fees),str(account.funding)])
                def close(t,event,reference,bankruptcy=False):
                    nonlocal exit_record
                    execution=reference if bankruptcy else reference*(1-friction)
                    account.close(abs(account.q),execution);exit_record=dict(time=t,event=event,price=str(execution))
                def charge(t,mark,quantity):
                    ft,rate=fh[t]
                    if quantity*rate>0:
                        cost=quantity*(mark[0] if ft==t else mark[1])*rate
                        account.wallet-=cost;account.funding+=cost
                        if account.q and account.wallet<account.margin:account.margin=max(D(0),account.wallet)
                for t in range(t0,end,HOUR):
                    bar=tuple(D(x) for x in trade[t][1:5]);mark=tuple(D(x) for x in marks[t][1:5]);opening_q=account.q
                    observe(t,'open',mark[0]);charged=False
                    if t in fh and fh[t][0]==t:charge(t,mark,opening_q);charged=True
                    if account.q and t>t0:
                        if mark[0]<=account.liquidation():close(t,'liquidation',account.liquidation(D(0)),True)
                        elif mark[0]<=sl:close(t,'stop_gap',bar[0])
                        elif mark[0]>=tp:close(t,'take_gap',bar[0])
                    if t in bear and t>t0:invalid=True
                    if t in triggers and t>t0 and account.q:
                        current=opps[t//(4*HOUR)*(4*HOUR)]
                        expired=current is None or current.identity!=op.identity or current.direction!=1
                        if (expired if policy=='control' else invalid):close(t,'regime_exit',bar[0])
                    if not charged and t in fh:charge(t,mark,opening_q)
                    for st,sbar,smark in steps(t,bar,mark,minutes):
                        if not account.q:break
                        so,sh,slo,sc=sbar;smo,smh,sml,smc=smark;liq=account.liquidation()
                        if st>t and smo<=liq:close(st,'liquidation',account.liquidation(D(0)),True)
                        elif st>t and smo<=sl:close(st,'stop_gap',so)
                        elif st>t and smo>=tp:close(st,'take_gap',so)
                        else:
                            observe(st,'envelope_high',smh);observe(st,'envelope_low',sml)
                            if sml<=liq:close(st,'liquidation',account.liquidation(D(0)),True)
                            elif sml<=sl:close(st,'stop',min(sl,so))
                            elif smh>=tp:close(st,'take',tp)
                    observe(t+HOUR,'close',mark[3])
                    if not account.q:break
            final=account.equity(mark[3]);pair[policy]=dict(net=str(final-initial),mdd=str(mdd),fees=str(account.fees),funding=str(account.funding),exit=exit_record,open_quantity=str(account.q))
            if policy=='control':
                assert exit_record and exit_record['time']==int(expected['time']) and exit_record['event']==expected['event'] and D(exit_record['price'])==D(expected['price_or_mark']),(t0,exit_record,expected)
        pair['net_difference']=str(D(pair['opposing_impulse']['net'])-D(pair['control']['net']));results.append(pair)
    (output/'inputs.json').write_text(json.dumps(identity,indent=2)+'\n')
    (output/'result.json').write_text(json.dumps({'qualification':'MATCHED_EVENT_DIAGNOSTIC_NOT_ACCOUNT_CAGR','overlapping_events_not_independent':True,'pairs':results},indent=2)+'\n')
    print(json.dumps({'pairs':len(results),'sum_event_net_difference_descriptive':str(sum((D(p['net_difference']) for p in results),D(0))),'improved_pairs':sum(D(p['net_difference'])>0 for p in results)}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.native,a.baseline,a.output)
