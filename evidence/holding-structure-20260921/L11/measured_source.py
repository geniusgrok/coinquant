"""L11 native Binance development account diagnostic, never qualification."""
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
from research.linear_forecast import archive_rows, DAY
from research.audit_binance import repair_rows
from research.linear_replay import Account, FEE, MMR, LOT, TICK

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


def run(root,warmup,repairs,output):
    frozen=spec();start=timestamp(frozen['start']);end=timestamp(frozen['development_end'])
    series,funding,warm,identity=inputs(root,warmup,repairs)
    trade=series['klines'];marks=series['markPriceKlines']
    fund_hours={t//HOUR*HOUR:(t,r) for t,r in funding.items()}
    daily=deque(maxlen=21);regime=0
    for t in range(min(warm),start,DAY):
        rows=[warm[s] for s in range(t,t+DAY,HOUR)]
        daily.append((max(D(r[2]) for r in rows),min(D(r[3]) for r in rows),D(rows[-1][4])))
        regime=channel_state(daily,regime)
    initial=D(frozen['initial_cny'])/D(frozen['cny_per_usd'])
    account=Account(initial*(1-D(frozen['initial_conversion_cost'])))
    peak=initial;mdd=ZERO;counts=Counter();seen=[];triggers=set(t for t in invocations(frozen) if t<end)
    slip=D(frozen['slippage_fraction']);spread=D(frozen['spread_fraction']);previous_quote=D(warm[start-HOUR][7])
    output.mkdir(parents=True,exist_ok=False)
    with gzip.open(output/'equity.csv.gz','wt') as ef,gzip.open(output/'orders.csv.gz','wt') as of:
        ew=csv.writer(ef);ow=csv.writer(of)
        ew.writerow(['time','event','equity_usdt','drawdown']);ow.writerow(['time','event','quantity_btc','price_or_mark','funding_rate','quantity_after'])
        def observe(t,event,mark):
            nonlocal peak,mdd
            eq=account.equity(mark);peak=max(peak,eq);dd=1-eq/peak;mdd=max(mdd,dd)
            ew.writerow([t,event,str(eq),str(dd)])
        def close(t,event,reference,bankruptcy=False):
            q=account.q
            price=reference if bankruptcy else reference*(1-slip-spread/2 if q>0 else 1+slip+spread/2)
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
                if account.q:
                    if account.q*regime<0:
                        close(t,'regime_exit',o);exited=True
                    else:
                        proposed=min(x[1] for x in window[-10:]) if account.q>0 else max(x[0] for x in window[-10:])
                        if account.q>0 and account.sl<proposed<mo:account.sl=floor_step(proposed,TICK)
                        elif account.q<0 and mo<proposed<account.sl:account.sl=floor_step(proposed,TICK)+TICK
                        counts['hold']+=1
                elif not exited:
                    direction=regime
                    if not direction:counts['no_breakout']+=1
                    else:
                        price=o*(1+slip+spread/2 if direction>0 else 1-slip-spread/2)
                        sl=min(x[1] for x in window[-10:]) if direction>0 else max(x[0] for x in window[-10:])
                        sl=floor_step(sl,TICK)+(TICK if direction<0 else ZERO)
                        unit=direction*(price-sl)
                        tp=floor_step(price*(price/sl)**20,TICK)+(TICK if direction>0 else ZERO)
                        if unit<=0 or tp<=0 or not (sl<mo<tp if direction>0 else tp<mo<sl):counts['unsafe_geometry']+=1
                        else:
                            required_per_btc=max(price/20,unit+price*(D('.01')+MMR+FEE))
                            risk=unit+FEE*(price+sl)+sl*(slip+spread/2)
                            qty=floor_step(min(account.equity(mo)*D('.006')/risk,
                                account.equity(mo)*2/price,account.wallet/(required_per_btc+2*price*FEE),
                                D('1000000')/price,previous_quote/60*D(frozen['volume_participation'])/price),LOT)
                            if qty:
                                account.open(direction*qty,price,sl,tp);account.margin=qty*required_per_btc
                                liq=account.liquidation()
                                if not (liq<sl<mo if direction>0 else mo<sl<liq):raise ValueError('unsafe funded stop geometry')
                                counts['entry']+=1;ow.writerow([t,'entry',str(account.q),str(price),'',str(account.q)])
                            else:counts['size_below_minimum']+=1
            if not charged and t in fund_hours and (opening_q or account.q):
                if account.q:observe(t,'pre_offset_funding_possible_peak',mh if account.q>0 else ml)
                funding_bound(t,mark,opening_q or account.q)
            if account.q:
                for price in sorted((mh,ml),key=account.equity,reverse=True):observe(t,'conservative_envelope',price)
                long=account.q>0;liq=account.liquidation()
                if (long and ml<=liq) or (not long and mh>=liq):close(t,'liquidation',account.liquidation(ZERO),True)
                elif (long and ml<=account.sl) or (not long and mh>=account.sl):
                    close(t,'stop',min(account.sl,o) if long else max(account.sl,o))
                elif (long and mh>=account.tp) or (not long and ml<=account.tp):close(t,'take',account.tp)
            observe(t+HOUR,'close',mc)
            if account.equity(mc)<=0:raise ValueError('account insolvent; no reset or truncation')
            if (t+HOUR)%DAY==0:
                rows=[trade[s] for s in range(t+HOUR-DAY,t+HOUR,HOUR)]
                daily.append((max(D(x[2]) for x in rows),min(D(x[3]) for x in rows),D(rows[-1][4])))
                regime=channel_state(daily,regime)
            previous_quote=D(r[7])
        final=account.equity(mc)
    if seen!=sorted(triggers):raise ValueError('frozen invocation mismatch')
    years=(end-start)/31556952000;cagr=float(final/initial)**(1/years)-1
    result=dict(candidate='L11',qualification='NOT_QUALIFIED',validation_used=False,cagr=cagr,mdd_conservative_envelope=str(mdd),
                final_cny=str(final*D(frozen['cny_per_usd'])),counts=dict(counts),fees_usdt=str(account.fees),funding_bound_paid_usdt=str(account.funding),
                progression_passed=cagr>0.04863302406009273 and mdd<D('.5') and D(str(cagr))/mdd>D('0.04863302406009273')/D('0.1136320269446116339717390128') and counts['liquidation']<=2,code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                limitations=['Proxy dated rules/fees/liquidity and USDT=USD','Adverse interval funding valuation, not exact cashflow',
                             'Hourly conservative envelope and liquidation-first ambiguity','Margin transfer and full-position execution unverified'])
    (output/'inputs.json').write_text(json.dumps(identity,indent=2)+'\n')
    (output/'invocations.json').write_text(json.dumps(seen)+'\n')
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('root','warmup','repairs','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();run(a.root,a.warmup,a.repairs,a.output)
