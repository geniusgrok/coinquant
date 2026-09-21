"""L9 native Binance development account diagnostic, never qualification."""
import argparse
from collections import Counter, deque
import csv
from decimal import Decimal as D
import gzip
import hashlib
import json
from pathlib import Path

from pancakequant.research import invocations, spec, timestamp, iso
from pancakequant.types import ZERO, floor_step
from pancakequant.binance import market_quantity
from research.linear_forecast import archive_rows, DAY
from research.audit_binance import repair_rows
from research.linear_replay import Account, FEE, MMR, LOT, TICK
from research.minute_evidence import load as minute_load, steps
from research.edge_allocation import target_fraction
from research.volatility_target import target_fraction as volatility_fraction, funded_target

HOUR=3600000


def inputs(root,warmup,repairs):
    series={'klines':{},'markPriceKlines':{}};funding={};identity=[]
    for year in range(2020,2024):
        for month in range(1,13):
            for kind in ('klines','markPriceKlines','fundingRate'):
                date=f'{year}-{month:02}'
                path=(f'monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-{date}.zip' if kind=='fundingRate'
                      else f'monthly/{kind}/BTCUSDT/1h/BTCUSDT-1h-{date}.zip')
                raw=(root/path).read_bytes();identity.append(dict(path=path,sha256=hashlib.sha256(raw).hexdigest()))
                for r in archive_rows(root,path):
                    t=int(r[0])
                    if kind=='fundingRate':
                        if t in funding:raise ValueError('duplicate funding')
                        funding[t]=D(r[2])
                    else:
                        if t in series[kind]:raise ValueError('duplicate price')
                        series[kind][t]=r
    rows,receipt=repair_rows(repairs)
    end=timestamp('2024-01-01T00:00:00Z')
    for r in rows:
        t=int(r[0])
        if t>=end:continue
        if t in series['markPriceKlines']:raise ValueError('repair overlaps original')
        series['markPriceKlines'][t]=r
    identity.extend(receipt)
    start=timestamp('2020-01-01T00:00:00Z')
    for x in series.values():
        if sorted(x)!=list(range(start,end,HOUR)):raise ValueError('development price gap')
    if [t//(8*HOUR) for t in sorted(funding)]!=list(range(start//(8*HOUR),end//(8*HOUR))):
        raise ValueError('funding gap')
    raw=(warmup/'warmup-trade.json').read_bytes()
    receipts=json.loads((warmup/'warmup-receipt.json').read_text())['records']
    expected=[r for r in receipts if r['file']=='warmup-trade.json']
    if len(expected)!=1 or expected[0]['sha256']!=hashlib.sha256(raw).hexdigest():raise ValueError('warmup identity')
    identity.extend(expected)
    warm={int(r[0]):r for r in json.loads(raw)}
    if sorted(warm)!=list(range(timestamp('2019-12-01T00:00:00Z'),start,HOUR)):raise ValueError('warmup gap')
    return series,funding,warm,identity


def channel_state(window, previous):
    if len(window)<21:return previous
    prior=list(window)[:-1];close=window[-1][2]
    if close>max(x[0] for x in prior):return 1
    if close<min(x[1] for x in prior):return -1
    return previous


def decision_times(frozen, end, schedule):
    if schedule == 'sparse':
        return set(t for t in invocations(frozen) if t < end)
    if schedule == 'hourly':
        return set(range(timestamp(frozen['start']), end, HOUR))
    raise ValueError('unknown research schedule')


def run(root,warmup,repairs,output,minutes=None,baseline=False,schedule='sparse',quantity_rules=None,lifecycle='persistent',allocation='fixed',reference='channel',protection='fixed'):
    if allocation not in ('fixed','edge','unit','volatility'):raise ValueError('unknown allocation')
    if lifecycle not in ('persistent','one_campaign'):raise ValueError('unknown lifecycle')
    if reference not in ('channel','long'):raise ValueError('unknown reference')
    if protection not in ('fixed','trailing'):raise ValueError('unknown protection')
    targeting=allocation in ('unit','volatility')
    frozen=spec();start=timestamp(frozen['start']);end=timestamp(frozen['development_end'])
    series,funding,warm,identity=inputs(root,warmup,repairs)
    if minutes is not None:
        minutes,minute_identity=minute_load(minutes,series);identity.extend(minute_identity)
    trade=series['klines'];marks=series['markPriceKlines']
    fund_hours={t//HOUR*HOUR:(t,r) for t,r in funding.items()}
    daily=deque(maxlen=21);regime=0
    for t in range(min(warm),start,DAY):
        rows=[warm[s] for s in range(t,t+DAY,HOUR)]
        daily.append((max(D(r[2]) for r in rows),min(D(r[3]) for r in rows),D(rows[-1][4])))
        regime=channel_state(daily,regime)
    daily_returns=deque((daily[i][2]/daily[i-1][2]-1 for i in range(1,len(daily))),maxlen=20)
    edge_observations=deque(maxlen=252);day_funding=ZERO;prior_day_direction=regime;previous_daily_close=daily[-1][2]
    initial=D(frozen['initial_cny'])/D(frozen['cny_per_usd'])
    account=Account(initial*(1-D(frozen['initial_conversion_cost'])))
    peak=initial;mdd=ZERO;counts=Counter();seen=[];triggers=decision_times(frozen,end,schedule)
    instrument=json.loads(quantity_rules.read_text())['instrument'] if quantity_rules else None
    if quantity_rules:identity.append(dict(path=str(quantity_rules),sha256=hashlib.sha256(quantity_rules.read_bytes()).hexdigest()))
    exposure_sum=ZERO;max_exposure=ZERO;holding_hours=0;turnover=ZERO;regime_since=start;delays=[];binding=Counter();campaign_epoch=0;last_entry_epoch=-1
    slip=D(frozen['slippage_fraction']);spread=D(frozen['spread_fraction']);previous_quote=D(warm[start-HOUR][7])
    output.mkdir(parents=True,exist_ok=False)
    with gzip.open(output/'equity.csv.gz','wt') as ef,gzip.open(output/'orders.csv.gz','wt') as of,gzip.open(output/'decisions.csv.gz','wt') as df:
        ew=csv.writer(ef);ow=csv.writer(of);dw=csv.writer(df)
        dw.writerow(['time','regime','equity','quantity','notional','margin','free_wallet','sl','tp','regime_age_hours','action','binding_cap','risk_quantity','exposure_quantity','margin_quantity','notional_quantity','liquidity_quantity','requested_quantity','accepted_quantity','edge_target_fraction','edge_samples'])
        ew.writerow(['time','event','equity_usdt','drawdown','quantity','mark','margin','fees','funding']);ow.writerow(['time','event','quantity_btc','price_or_mark','funding_rate','quantity_after'])
        def observe(t,event,mark):
            nonlocal peak,mdd
            eq=account.equity(mark);peak=max(peak,eq);dd=1-eq/peak;mdd=max(mdd,dd)
            ew.writerow([t,event,str(eq),str(dd),str(account.q),str(mark),str(account.margin),str(account.fees),str(account.funding)])
        def close(t,event,reference,bankruptcy=False):
            nonlocal turnover
            q=account.q
            price=reference if bankruptcy else reference*(1-slip-spread/2 if q>0 else 1+slip+spread/2)
            turnover+=abs(q)*price
            account.close(abs(q),price);counts[event]+=1
            ow.writerow([t,event,str(q),str(price),'',str(account.q)])
        def funding_bound(t,mark,q):
            ft,rate=fund_hours[t]
            if q*rate>0:
                p=mark[0] if ft==t else mark[1]
                # Offset settlement follows the invocation. Charge old exposure
                # even if it might already have exited: explicit adverse bound.
                cost=q*p*rate
                account.wallet-=cost;account.funding+=cost
                if account.q and account.wallet<account.margin:account.margin=max(ZERO,account.wallet)
                ow.writerow([ft,'funding_adverse_bound',str(q),str(p),str(rate),str(account.q)])
                counts['funding_charge']+=1
            elif q:counts['ambiguous_funding_credit_omitted']+=1
        for t in range(start,end,HOUR):
            r=trade[t];mr=marks[t];bar=tuple(D(x) for x in r[1:5]);mark=tuple(D(x) for x in mr[1:5])
            o,h,lo,c=bar;mo,mh,ml,mc=mark
            observe(t,'open',mo)
            if t in fund_hours:day_funding+=max(ZERO,D(regime)*fund_hours[t][1])
            charged=False;exited=False;opening_q=account.q
            if account.q and t in fund_hours and fund_hours[t][0]==t:
                funding_bound(t,mark,opening_q);charged=True
            if account.q:
                long=account.q>0;liq=account.liquidation()
                if (long and mo<=liq) or (not long and mo>=liq):
                    close(t,'liquidation',account.liquidation(ZERO),True);exited=True
                elif (long and mo<=account.sl) or (not long and mo>=account.sl):
                    close(t,'stop_gap',o);exited=True
                elif (long and mo>=account.tp) or (not long and mo<=account.tp):
                    close(t,'take_gap',o);exited=True
            if t in triggers:
                seen.append(t);counts['invocations']+=1
                window=list(daily)
                direction=1 if reference=='long' else regime
                edge_target=(volatility_fraction(daily_returns,slip+spread/2) if allocation=='volatility' else D(1) if allocation=='unit' else target_fraction(edge_observations) if allocation=='edge' else D(2))
                action='hold' if account.q else 'no_signal';caps={};qty=ZERO;raw_qty=ZERO;limiter=''
                decision_state=[t,regime,str(account.equity(mo)),str(account.q),str(abs(account.q)*mo),str(account.margin),str(account.wallet-account.margin),str(account.sl),str(account.tp),(t-regime_since)//HOUR]
                if targeting and protection=='trailing' and account.q:
                    proposed=min(x[1] for x in window[-10:]) if account.q>0 else max(x[0] for x in window[-10:])
                    if account.q>0 and account.sl<proposed<mo:account.sl=floor_step(proposed,TICK)
                    elif account.q<0 and mo<proposed<account.sl:account.sl=floor_step(proposed,TICK)+TICK
                if targeting:
                    if account.q and account.q*direction<0:
                        close(t,'regime_exit',o);exited=True;action='regime_exit'
                    elif not exited and direction:
                        consumed=(not account.q and lifecycle=='one_campaign' and last_entry_epoch==campaign_epoch)
                        if consumed:
                            counts['campaign_consumed']+=1;action='campaign_consumed'
                        else:
                            adding=account.equity(mo)*edge_target/max(o,mo)>abs(account.q)
                            execution_direction=direction if adding else -direction
                            price=o*(1+D(execution_direction)*(slip+spread/2))
                            sl=account.sl if account.q else floor_step(min(x[1] for x in window[-10:]) if direction>0 else max(x[0] for x in window[-10:]),TICK)+(TICK if direction<0 else ZERO)
                            tp=account.tp if account.q else floor_step(price*(price/sl)**20,TICK)+(TICK if direction>0 else ZERO)
                            if min(sl,tp)<=0:
                                action='unsafe_geometry';counts[action]+=1
                            else:
                                change=funded_target(account,direction,edge_target,price,mo,sl,tp,previous_quote/60*D(frozen['volume_participation'])/price,instrument)
                                action=change['event'] or change['reason'];limiter=change['reason'];binding[limiter]+=1
                                raw_qty=D(change['requested']);qty=D(change['accepted']);counts[action]+=1
                                if change['event']:
                                    turnover+=change['amount']*price
                                    ow.writerow([t,change['event'],str(direction*change['amount']),str(price),'',str(account.q)])
                                    if change['event']=='entry':
                                        last_entry_epoch=campaign_epoch;delays.append((t-regime_since)//HOUR)
                elif account.q:
                    if baseline:
                        proposed=min(x[1] for x in window[-10:]) if account.q>0 else max(x[0] for x in window[-10:])
                        if account.q>0 and account.sl<proposed<mo:account.sl=floor_step(proposed,TICK)
                        elif account.q<0 and mo<proposed<account.sl:account.sl=floor_step(proposed,TICK)+TICK
                        counts['hold']+=1
                    elif account.q*regime<0:
                        close(t,'regime_exit',o);exited=True;action='regime_exit'
                    else: counts['hold']+=1
                elif not exited:
                    direction=regime
                    if lifecycle=='one_campaign' and last_entry_epoch==campaign_epoch:
                        counts['campaign_consumed']+=1;action='campaign_consumed'
                    elif not direction:counts['no_breakout']+=1
                    elif allocation=='edge' and not edge_target:
                        counts['no_estimated_edge']+=1;action='no_estimated_edge'
                    else:
                        price=o*(1+slip+spread/2 if direction>0 else 1-slip-spread/2)
                        sl=min(x[1] for x in window[-10:]) if direction>0 else max(x[0] for x in window[-10:])
                        sl=floor_step(sl,TICK)+(TICK if direction<0 else ZERO)
                        unit=direction*(price-sl)
                        tp=floor_step(price*(price/sl)**20,TICK)+(TICK if direction>0 else ZERO)
                        if unit<=0 or tp<=0 or not (sl<mo<tp if direction>0 else tp<mo<sl):
                            counts['unsafe_geometry']+=1;action='unsafe_geometry'
                        else:
                            required_per_btc=max(price/20,unit+price*(D('.01')+MMR+FEE))
                            risk=unit+FEE*(price+sl)+sl*(slip+spread/2)
                            caps=dict(risk=account.equity(mo)*(D('.20') if allocation=='edge' else D('.006'))/risk,
                                exposure=account.equity(mo)*edge_target/price,margin=account.wallet/(required_per_btc+2*price*FEE),
                                notional=D('1000000')/price,liquidity=previous_quote/60*D(frozen['volume_participation'])/price)
                            limiter=min(caps,key=caps.get);binding[limiter]+=1;raw_qty=caps[limiter]
                            qty=market_quantity(raw_qty,price,instrument) if instrument else floor_step(raw_qty,LOT)
                            if qty:
                                account.open(direction*qty,price,sl,tp);account.margin=qty*required_per_btc
                                turnover+=qty*price;delays.append((t-regime_since)//HOUR);action='entry';last_entry_epoch=campaign_epoch
                                liq=account.liquidation()
                                if not (liq<sl<mo if direction>0 else mo<sl<liq):raise ValueError('unsafe funded stop geometry')
                                counts['entry']+=1;ow.writerow([t,'entry',str(account.q),str(price),'',str(account.q)])
                            else:counts['size_below_minimum']+=1;action='size_below_minimum'
                dw.writerow(decision_state+[action,limiter]+[str(caps.get(k,'')) for k in ('risk','exposure','margin','notional','liquidity')]+[str(raw_qty),str(qty),str(edge_target),len(edge_observations)])
            if not charged and t in fund_hours and (opening_q or account.q):
                if account.q:observe(t,'pre_offset_funding_possible_peak',mh if account.q>0 else ml)
                charge_q=(max((opening_q,account.q),key=lambda q:q*fund_hours[t][1]) if targeting else opening_q or account.q)
                funding_bound(t,mark,charge_q)
            for st,sbar,smark in steps(t,bar,mark,minutes):
                if not account.q:break
                so,sh,slo,sc=sbar;smo,smh,sml,smc=smark
                long=account.q>0;liq=account.liquidation()
                # Each native subinterval resolves only BEFORE later intervals.
                # Remaining within-minute ambiguity is still liquidation-first.
                if st>t and ((long and smo<=liq) or (not long and smo>=liq)):
                    close(st,'liquidation',account.liquidation(ZERO),True)
                elif st>t and ((long and smo<=account.sl) or (not long and smo>=account.sl)):
                    close(st,'stop_gap',so)
                elif st>t and ((long and smo>=account.tp) or (not long and smo<=account.tp)):
                    close(st,'take_gap',so)
                else:
                    for price in sorted((smh,sml),key=account.equity,reverse=True):observe(st,'conservative_envelope',price)
                    hit_liq=(long and sml<=liq) or (not long and smh>=liq)
                    hit_stop=(long and sml<=account.sl) or (not long and smh>=account.sl)
                    if hit_liq:
                        if hit_stop:counts['unresolved_same_interval_stop_liquidation']+=1
                        close(st,'liquidation',account.liquidation(ZERO),True)
                    elif hit_stop:close(st,'stop',min(account.sl,so) if long else max(account.sl,so))
                    elif (long and smh>=account.tp) or (not long and sml<=account.tp):close(st,'take',account.tp)
            observe(t+HOUR,'close',mc)
            exposure=abs(account.q)*mc/account.equity(mc) if account.equity(mc)>0 else ZERO
            exposure_sum+=exposure;max_exposure=max(max_exposure,exposure);holding_hours+=bool(account.q)
            if account.equity(mc)<=0:raise ValueError('account insolvent; no reset or truncation')
            if (t+HOUR)%DAY==0:
                rows=[trade[s] for s in range(t+HOUR-DAY,t+HOUR,HOUR)]
                observation=D(regime)*(D(rows[-1][4])/previous_daily_close-1)-day_funding
                if regime!=prior_day_direction:observation-=2*(FEE+slip+spread/2)
                edge_observations.append(observation);day_funding=ZERO;prior_day_direction=regime;previous_daily_close=D(rows[-1][4])
                daily_returns.append(D(rows[-1][4])/daily[-1][2]-1)
                daily.append((max(D(x[2]) for x in rows),min(D(x[3]) for x in rows),D(rows[-1][4])))
                new_regime=channel_state(daily,regime)
                if new_regime!=regime:regime_since=t+HOUR;campaign_epoch+=1
                regime=new_regime
            previous_quote=D(r[7])
        final=account.equity(mc)
    if seen!=sorted(triggers):raise ValueError('frozen invocation mismatch')
    years=(end-start)/31556952000;cagr=float(final/initial)**(1/years)-1
    result=dict(candidate=('L7' if baseline else 'L9')+'-minute-refined',qualification='NOT_QUALIFIED',validation_used=False,cagr=cagr,mdd_conservative_envelope=str(mdd),
                final_cny=str(final*D(frozen['cny_per_usd'])),counts=dict(counts),fees_usdt=str(account.fees),funding_bound_paid_usdt=str(account.funding),
                progression_passed=None,progression_status='requires paired refined comparison',code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                limitations=['Proxy dated rules/fees/liquidity and USDT=USD','Adverse interval funding valuation, not exact cashflow',
                             'Minute refinement on six days only; remaining interval liquidation-first ambiguity','Margin transfer and full-position execution unverified'])
    result['reference']=reference
    result['candidate']=('L18' if allocation=='edge' else 'L17' if lifecycle=='one_campaign' else 'L7' if baseline else 'L9')+'-minute-refined'
    if targeting:result['candidate']='L21' if allocation=='volatility' else 'B1' if reference=='long' else 'B2'
    result['protection']=protection
    if targeting and protection=='trailing':result['candidate']='L22'
    sources=output/'measured_source';sources.mkdir()
    source_hashes={}
    for source in (Path(__file__),Path('research/edge_allocation.py'),Path('research/volatility_target.py'),Path('research/linear_replay.py'),Path('research/minute_evidence.py'),Path('pancakequant/binance.py'),Path('research/spec.json')):
        raw=source.read_bytes();(sources/source.name).write_bytes(raw);source_hashes[str(source)]=hashlib.sha256(raw).hexdigest()
    result['source_hashes']=source_hashes
    result.update(schedule=schedule,lifecycle=lifecycle,allocation=allocation,quantity_rule_scope='2026_snapshot_scenario_NOT_historical' if instrument else 'legacy_hypothetical',
        mean_close_exposure=str(exposure_sum/((end-start)//HOUR)),max_close_exposure=str(max_exposure),holding_hours=holding_hours,
        turnover_usdt=str(turnover),binding_caps=dict(binding),mean_entry_regime_age_hours=sum(delays)/len(delays) if delays else None,
        schedule_sha256=hashlib.sha256(json.dumps(seen).encode()).hexdigest())
    (output/'inputs.json').write_text(json.dumps(identity,indent=2)+'\n')
    (output/'invocations.json').write_text(json.dumps(seen)+'\n')
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('root','warmup','repairs','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--minutes',type=Path)
    p.add_argument('--baseline',action='store_true',help='Exact L7 ratchet comparison, research only')
    p.add_argument('--schedule',choices=('sparse','hourly'),default='sparse')
    p.add_argument('--quantity-rules',type=Path)
    p.add_argument('--lifecycle',choices=('persistent','one_campaign'),default='persistent')
    p.add_argument('--allocation',choices=('fixed','edge','unit','volatility'),default='fixed')
    p.add_argument('--reference',choices=('channel','long'),default='channel')
    p.add_argument('--protection',choices=('fixed','trailing'),default='fixed')
    a=p.parse_args();run(a.root,a.warmup,a.repairs,a.output,a.minutes,a.baseline,a.schedule,a.quantity_rules,a.lifecycle,a.allocation,a.reference,a.protection)
