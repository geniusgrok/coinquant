"""L2 development-only linear-account diagnostic on explicitly proxy venue data.

Native Bybit inverse prices/funding are reused as a market proxy, not relabeled
OKX data. USDT=USD and linear lot/rules below are explicit research assumptions.
This cannot qualify economics and is never imported by production.
"""
import argparse
from collections import Counter, deque
from decimal import Decimal as D
import csv
import gzip
import json
from pathlib import Path

from coinquant.data import Dataset
from coinquant.replay import aggregate
from coinquant.research import digest, invocations, iso, spec, timestamp
from coinquant.types import Blocked, ZERO, floor_step, serial
from research.sparse_trend import signal

from coinquant.linear_account import Account, FEE, MMR, LOT, TICK


def run(manifest, output):
    frozen = spec(); end = timestamp(frozen['development_end'])
    dataset = Dataset(manifest, frozen, warmup_bars=121)
    root = Path(output); root.mkdir(parents=True, exist_ok=False)
    initial = D(frozen['initial_cny']) / D(frozen['cny_per_usd'])
    account = Account(initial * (1 - D(frozen['initial_conversion_cost'])))
    triggers = set(t for t in invocations(frozen) if t < end)
    spread, slip = D(frozen['spread_fraction']), D(frozen['slippage_fraction'])
    history, chunk = deque(maxlen=121), []
    previous_volume = ZERO; last_rate = ZERO; counts = Counter(); pending = ''
    peak, mdd = initial, ZERO; actual=[]; last_mark=None
    hold_hours=0; annual={}; last_year=None; year_initial=initial; last_equity=initial
    with gzip.open(root/'equity.csv.gz','wt') as eq, gzip.open(root/'orders.csv.gz','wt') as orders:
        ew, ow = csv.writer(eq), csv.writer(orders)
        ew.writerow(['time','event','equity_usdt','drawdown'])
        ow.writerow(['time','event','quantity_btc','price','quantity_after','sl','tp'])
        def observe(t, event, mark):
            nonlocal peak, mdd
            value=account.equity(mark); peak=max(peak,value)
            dd=1-value/peak; mdd=max(mdd,dd)
            ew.writerow([t,event,str(value),str(dd)])
        for tick in dataset.ticks():
            bar, mark = tick.trade, tick.mark; t=bar.time
            if t >= end:
                break  # never inspect validation prices or compute validation metrics
            if t >= dataset.start:
                year=iso(t)[:4]
                if year != last_year:
                    if last_year: annual[last_year]=str(last_equity/year_initial-1)
                    last_year=year; year_initial=last_equity
                if t in dataset.funding:
                    rate, funding_mark=dataset.funding[t]; last_rate=rate; account.pay_funding(funding_mark,rate)
                capacity=floor_step(bar.volume / 60 * D(frozen['volume_participation']) / bar.open,LOT)
                exited=False
                def reduce(reason, reference, full=False):
                    nonlocal capacity, exited, pending
                    q=account.q
                    if not q: return
                    amount=abs(q) if full else min(abs(q),capacity)
                    if not amount: return
                    price=reference if full else reference*(1-slip-spread/2 if q>0 else 1+slip+spread/2)
                    account.close(amount,price); capacity=max(ZERO,capacity-amount)
                    counts[reason]+=1; exited=True
                    ow.writerow([t,reason,str(amount),str(price),str(account.q),str(account.sl),str(account.tp)])
                    if not account.q: pending=''
                observe(t,'open',mark.open)
                if account.q:
                    long=account.q>0; liq=account.liquidation()
                    if (long and mark.open<=liq) or (not long and mark.open>=liq):
                        reduce('liquidation',account.liquidation(ZERO),True)
                    elif pending or (long and mark.open<=account.sl) or (not long and mark.open>=account.sl):
                        pending=pending or 'stop'
                        ref=min(account.sl,bar.open) if long else max(account.sl,bar.open)
                        if pending=='take': ref=account.tp
                        reduce(pending,ref)
                    elif (long and mark.open>=account.tp) or (not long and mark.open<=account.tp):
                        pending='take';reduce(pending,account.tp)
                if t in triggers:
                    actual.append(t)
                    if not exited and not pending:
                        value=signal(list(history),t); counts['decisions']+=1
                        if account.q:
                            if account.q*value.direction<=0:
                                reduce('manual_close',bar.open)
                            else:
                                distance=mark.open*value.daily_rms*2
                                proposed=floor_step(mark.open-distance,TICK) if account.q>0 and mark.open>distance else (
                                    floor_step(mark.open+distance,TICK)+TICK if account.q<0 else account.sl)
                                # Preserve protection and original TP. Never add/rebalance same-direction exposure.
                                if account.q>0 and account.sl<proposed<mark.open: account.sl=proposed
                                if account.q<0 and mark.open<proposed<account.sl: account.sl=proposed
                                counts['hold']+=1
                        elif value.direction:
                            direction=value.direction
                            price=bar.open*(1+slip+spread/2 if direction>0 else 1-slip-spread/2)
                            distance=min(mark.open*value.daily_rms*2,mark.open*D('.015'))
                            stop=floor_step(mark.open-distance,TICK) if direction>0 and mark.open>distance else (
                                floor_step(mark.open+distance,TICK)+TICK if direction<0 else ZERO)
                            unit=abs(price-stop)
                            tp=floor_step(price+direction*8*unit,TICK) if price+direction*8*unit>0 else ZERO
                            if direction>0: tp+=TICK
                            estimated=Account(account.wallet)
                            if min(stop,tp)>0:
                                # At 20x, projected liquidation ratio does not depend on order size.
                                estimated.q=D(direction);estimated.entry=price;estimated.margin=price/20
                                liq=estimated.liquidation(); cushion=max(TICK*2,mark.open*D('.003'))
                                safe=liq+cushion<stop<mark.open<tp if direction>0 else ZERO<tp<mark.open<stop<liq-cushion
                            else: safe=False
                            if not safe:
                                counts['unsafe_initial_stop']+=1
                            else:
                                # Future funding is unknown; use latest known settled rate below.
                                risk_per_btc=unit+FEE*(price+stop)+stop*slip+price*abs(last_rate)
                                risk_qty=account.equity(mark.open)*D('.006')*value.conviction/risk_per_btc
                                depth_qty=previous_volume/60*D(frozen['book_proxy_fraction'])*D('.05')/price
                                q=floor_step(min(risk_qty,account.equity(mark.open)*2/price,
                                    account.wallet/(price*(D('.05')+2*FEE)),D('1000000')/price,
                                    depth_qty,capacity),LOT)
                                if q:
                                    account.open(direction*q,price,stop,tp);capacity-=q
                                    counts['entry']+=1
                                    ow.writerow([t,'entry',str(direction*q),str(price),str(account.q),str(stop),str(tp)])
                                else: counts['size_below_minimum']+=1
                        else: counts['no_direction']+=1
                if account.q:
                    hold_hours+=1
                    # Conservative extrema envelope; no favorable stop-clipped drawdown.
                    for p in sorted((mark.high,mark.low),key=account.equity,reverse=True): observe(t,'envelope',p)
                    long=account.q>0;liq=account.liquidation()
                    if (long and mark.low<=liq) or (not long and mark.high>=liq):
                        reduce('liquidation',account.liquidation(ZERO),True)
                    else:
                        if not pending:
                            if (long and mark.low<=account.sl) or (not long and mark.high>=account.sl): pending='stop'
                            elif (long and mark.high>=account.tp) or (not long and mark.low<=account.tp): pending='take'
                        if pending:
                            reference=account.sl if pending=='stop' else account.tp
                            if pending=='stop': reference=min(reference,bar.open) if long else max(reference,bar.open)
                            reduce(pending,reference)
                observe(t+dataset.interval,'close',mark.close)
                last_equity=account.equity(mark.close);last_mark=mark.close
                if last_equity<=0: raise Blocked('linear diagnostic insolvent; cannot truncate/reset')
            if t in dataset.funding: last_rate=dataset.funding[t][0]
            elif t==dataset.warmup_start: last_rate=ZERO
            chunk.append(bar)
            if (t+dataset.interval)%14400000==0:
                if len(chunk)!=4: raise Blocked('incomplete signal aggregation')
                history.append(aggregate(chunk));chunk=[]
            previous_volume=bar.volume
        if actual!=sorted(triggers): raise Blocked('missing frozen development invocation')
    annual[last_year]=str(last_equity/year_initial-1)
    years=(end-dataset.start)/31556952000
    result={'qualification':'NOT_QUALIFIED','provenance':'hypothetical_linear_account_on_Bybit_inverse_market_and_funding_proxy',
        'candidate':'L2','scope':'2020-2023 development only','cagr':float(last_equity/initial)**(1/years)-1,
        'mdd':str(mdd),'final_cny':str(last_equity*D(frozen['cny_per_usd'])),'fees_usdt':str(account.fees),
        'net_funding_paid_usdt':str(account.funding),'counts':dict(counts),'invocations':len(actual),
        'holding_hours':hold_hours,'yearly':annual,'data_manifest_sha256':digest(manifest),
        'code_sha256':digest(__file__),'signal_sha256':digest(Path(__file__).with_name('sparse_trend.py')),
        'validation_inspected':False,'limitations':['Not native linear data/rules or execution validation',
        'USDT=USD assumption; no stablecoin depeg series','Hourly conservative exit ambiguity and liquidity proxy',
        'No guarantee of atomic attached native protection','No continuous favorable mark-path assumption']}
    (root/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();run(a.manifest,a.output)
