"""Descriptive ledger attribution. No statistic here forms production signals."""
import csv,gzip,json
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path
from coinquant.research import iso,spec
from research.linear_replay import FEE


def rows(root,name):
    with gzip.open(root/(name+'.csv.gz'),'rt') as f:return list(csv.DictReader(f))


def analyze(root):
    equity=rows(root,'equity');orders=rows(root,'orders');decisions=rows(root,'decisions')
    result=json.loads((root/'result.json').read_text());initial=D(spec()['initial_cny'])/D(spec()['cny_per_usd'])
    peak_value=initial;peak=None;worst=(D(0),None,None)
    for i,r in enumerate(equity):
        value=D(r['equity_usdt'])
        if value>peak_value:peak_value=value;peak=i
        dd=1-value/peak_value
        if dd>worst[0]:worst=(dd,peak,i)
    dd,a,b=worst
    peak_eq=D(equity[a]['equity_usdt']) if a is not None else initial
    recovered=next((r for r in equity[b+1:] if D(r['equity_usdt'])>=peak_eq),None)
    assert abs(dd-D(result['mdd_conservative_envelope']))<D('1e-18')
    parts=defaultdict(D);trades=[];opened=None;fees=D(0);funding=D(0);friction=D(0)
    rate=D(spec()['slippage_fraction'])+D(spec()['spread_fraction'])/2
    for r in orders:
        q=D(r['quantity_btc']);price=D(r['price_or_mark']);event=r['event']
        if event=='entry':
            assert opened is None
            friction+=abs(q)*price/(1+(1 if q>0 else -1)*rate)*rate
            opened=(int(r['time']),q,price);fees=abs(q)*price*FEE;funding=D(0)
        elif event=='funding_adverse_bound':
            charge=q*price*D(r['funding_rate']);funding+=charge
            parts[('long' if q>0 else 'short')+'_funding']+=charge
        elif event in ('regime_exit','stop','stop_gap','take','take_gap','liquidation','final_close'):
            assert opened is not None,event
            t,entryq,entryprice=opened
            if event!='liquidation':friction+=abs(entryq)*price/(1-(1 if entryq>0 else -1)*rate)*rate
            gross=entryq*(price-entryprice);fees+=abs(entryq)*price*FEE
            side='long' if entryq>0 else 'short'
            # Liquidation engine may use a special liquidation price/fee; residual below exposes it.
            parts[side+'_gross_execution']+=gross;parts[side+'_fees']+=fees
            trades.append(dict(entry=t,exit=int(r['time']),side=side,event=event,
                hours=(int(r['time'])-t)/3600000,gross=str(gross),fees=str(fees),funding=str(funding),net=str(gross-fees-funding)))
            opened=None
    if opened:
        t,q,p=opened;gross=q*(D(equity[-1]['mark'])-p);side='long' if q>0 else 'short'
        parts[side+'_gross_execution']+=gross;parts[side+'_fees']+=fees
    pnl=sum((v if k.endswith('execution') else -v for k,v in parts.items()),D(0))
    actual=D(equity[-1]['equity_usdt'])-initial*(1-D(spec()['initial_conversion_cost']))
    assert abs(actual-pnl)<D('1e-18'),(root,actual-pnl)
    close=[r for r in equity if r['event']=='close']
    # q and the last observed q cover ordinary hourly account occupancy independently of calls.
    cash_hours=sum(D(r['quantity'])==0 for r in close)
    out=dict(candidate=result['candidate'],schedule=result['schedule'],qualification='DESCRIPTIVE_ONLY',
        drawdown=dict(fraction=str(dd),peak=iso(int(equity[a]['time'])) if a is not None else spec()['start'],
            trough=iso(int(equity[b]['time'])),recovery=iso(int(recovered['time'])) if recovered else None,
            recovery_hours=(int(recovered['time'])-int(equity[a]['time']))/3600000 if recovered and a is not None else None),
        side_components={k:str(v) for k,v in parts.items()},
        slippage_usdt=str(friction*D(spec()['slippage_fraction'])/rate),
        spread_usdt=str(friction*D(spec()['spread_fraction'])/2/rate),
        gross_before_friction_usdt=str(sum((v for k,v in parts.items() if k.endswith('execution')),D(0))+friction),
        ledger_residual=str(actual-pnl),
        completed_trades=len(trades),mean_hold_hours=sum(r['hours'] for r in trades)/len(trades) if trades else 0,
        positive_trades=sum(D(r['net'])>0 for r in trades),
        mean_net_trade=str(sum((D(r['net']) for r in trades),D(0))/len(trades)) if trades else None,
        empty_hours=cash_hours,hours=len(close),mean_leverage=result['mean_close_exposure'],
        max_leverage=result['max_close_exposure'],turnover_usdt=result['turnover_usdt'],trades=trades,
        native_protection_failures_verified=False,
        limitations=['Execution gross is after modeled spread/slippage; these costs are embedded, not double-subtracted.',
                    'Side ledger includes offset funding charged after an exit; trade net alone may omit that adverse boundary charge.',
                    'Drawdown is the conservative mark envelope, not a uniquely observed intrabar path.'])
    (root/'opportunity_attribution.json').write_text(json.dumps(out,indent=2)+'\n')
    return out

if __name__=='__main__':
    import sys
    for path in sys.argv[1:]:
        for result in Path(path).rglob('result.json'):analyze(result.parent)
