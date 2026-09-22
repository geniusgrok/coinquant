"""Descriptive output from the shared account traces, not another trading ledger."""
from __future__ import annotations

import json
from decimal import Decimal as D
from pathlib import Path

from pancakequant.research import iso, spec
from research.opportunity_attribution import rows
from research.verify_account_ledger import verify


def analyze(path: Path) -> dict:
    audit=verify(path)
    result=json.loads((path/'result.json').read_text())
    execution=json.loads((path/'execution_summary.json').read_text())
    equity=rows(path,'equity');orders=rows(path,'orders');decisions=rows(path,'decisions')
    frozen=spec();initial=D(frozen['initial_cny'])/D(frozen['cny_per_usd'])
    slip=D(frozen['slippage_fraction'])*(2 if execution['configuration']['cost_multiplier']==2 else 1)
    spread=D(frozen['spread_fraction']);rate=slip+spread/2
    parents=[p for p in execution['parents'] if D(p['maximum'])>0]
    calls={p['first_fill']:p['call_time'] for p in parents}
    closed=[];current=None;fees=D(0);funding=D(0);entry_fees=D(0);exit_fees=D(0)
    base_slip=spread_cost=extra_impact=D(0)
    exit_records={(int(r['time']),r['event']):r for r in execution['exits']}
    for r in orders:
        t=int(r['time']);q=D(r['quantity_btc']);price=D(r['price_or_mark']);event=r['event']
        if event=='entry':
            if current is not None:closed.append(current)
            current=dict(call_time=calls.get(t,t),entry_time=t,quantity=D(0),average_entry=D(0),
                         entry_fees=D(0),exit_fees=D(0),funding=D(0),gross=D(0),exit_time=None)
        if event in ('entry','rebalance_add'):
            assert current is not None and current['exit_time'] is None
            old=current['quantity'];new=old+q
            current['average_entry']=(old*current['average_entry']+q*price)/new
            current['quantity']=new
            fee=abs(q)*price*D('.00075');entry_fees+=fee;fees+=fee;current['entry_fees']+=fee
            quote=price/(1+rate);base_slip+=abs(q)*quote*slip;spread_cost+=abs(q)*quote*spread/2
        elif event=='funding_adverse_bound':
            cost=q*price*D(r['funding_rate']);funding+=cost
            if current is not None:current['funding']+=cost
        else:
            assert current is not None and q==current['quantity']
            fee=abs(q)*price*D('.00075');exit_fees+=fee;fees+=fee;current['exit_fees']+=fee
            current.update(gross=q*(price-current['average_entry']),exit_time=t,exit_price=price,exit_event=event)
            record=exit_records[(t,event)];reference=D(record['reference'])
            base_slip+=abs(q)*reference*slip;spread_cost+=abs(q)*reference*spread/2
            extra_impact+=D(record['extra_impact_usdt'])
    if current is not None:
        if current['exit_time'] is None:
            current['gross']=current['quantity']*(D(equity[-1]['mark'])-current['average_entry'])
        closed.append(current)
    for trade in closed:
        trade['net']=trade['gross']-trade['entry_fees']-trade['exit_fees']-trade['funding']
    actual=D(equity[-1]['equity_usdt'])-initial*(1-D(frozen['initial_conversion_cost']))
    assert abs(actual-sum((r['net'] for r in closed),D(0)))<=D('1e-18')
    assert abs(fees-D(result['fees_usdt']))<=D('1e-18') and abs(funding-D(result['funding_bound_paid_usdt']))<=D('1e-18')
    peak=initial;peak_time=int(equity[0]['time']);worst=D(0);worst_peak=peak;worst_peak_time=peak_time;trough=0
    extremes={};annual={};insolvent=0
    for index,r in enumerate(equity):
        value=D(r['equity_usdt']);q=abs(D(r['quantity']));mark=D(r['mark']);margin=D(r['margin']);wallet=D(r['wallet'])
        if value>peak:peak=value;peak_time=int(r['time'])
        drawdown=1-value/peak
        if drawdown>worst:worst=drawdown;worst_peak=peak;worst_peak_time=peak_time;trough=index
        if value<=0 or wallet<0:insolvent+=1
        if q and value>0:
            values=dict(notional_usdt=q*mark,exposure=q*mark/value,margin_usdt=margin,
                        margin_equity=margin/value,stop_loss_fraction=max(D(0),q*(D(r['average_entry'])-D(r['sl'])))/value)
            for label,number in values.items():
                if label not in extremes or number>extremes[label]['value']:
                    extremes[label]=dict(value=number,time=iso(int(r['time'])),event=r['event'],wallet=wallet,margin=margin,equity=value,free_wallet=wallet-margin)
            free=wallet-margin
            if 'minimum_free_wallet' not in extremes or free<extremes['minimum_free_wallet']['value']:
                extremes['minimum_free_wallet']=dict(value=free,time=iso(int(r['time'])),event=r['event'])
        if r['event']=='close':annual[iso(int(r['time'])-1)[:4]]=value
    prior=initial
    for year,value in annual.copy().items():
        annual[year]=dict(return_fraction=value/prior-1,end_cny=value*D(frozen['cny_per_usd']));prior=value
    assert abs(worst-D(result['mdd_conservative_envelope']))<=D('1e-18')
    recovered=next((r for r in equity[trough+1:] if D(r['equity_usdt'])>=worst_peak),None)
    positive=sum((r['net'] for r in closed if r['net']>0),D(0))
    largest=max((r['net'] for r in closed),default=D(0))
    original_entries=[r for r in decisions if r['action']=='entry']
    filled=sum((D(p['filled']) for p in parents),D(0)) if parents else sum((D(r['accepted_quantity']) for r in original_entries),D(0))
    target=sum((D(p['maximum']) for p in parents),D(0)) if parents else sum((D(r['requested_quantity']) for r in original_entries),D(0))
    children=[]
    with (path/'execution.jsonl').open() as stream:
        for line in stream:
            r=json.loads(line)
            if r['kind']=='child':children.append(r)
    stats=dict(parent_count=len(execution['parents']),funded_parents=len(parents),filled_btc=filled,
               target_btc=target,aggregate_fill_fraction=filled/target if target else None,
               target_definition='fundable frozen mother maximum' if parents else 'raw original target',
               liquidity_limited_parents=sum(p['liquidity_limited'] for p in parents) if parents else sum(r['binding_cap']=='liquidity_cap' for r in original_entries),
               unfinished_parents=sum(D(p['remainder'])>0 for p in parents),remaining_btc=sum((D(p['remainder']) for p in parents),D(0)),
               confirmed_children=sum(D(r['accepted'])>0 for r in children),
               intermediate_protection_stops=sum(p['terminal_reason'].startswith('protection_or_exit:') for p in parents),
               unresolved_parents=sum(p['unresolved'] for p in execution['parents']),
               delay_price_cost_usdt=sum((D(r.get('delay_price_cost','0')) for r in children),D(0)))
    raw_target=sum((D(p['raw_target']) for p in parents),D(0)) if parents else target
    stats['raw_target_btc']=raw_target
    stats['raw_target_fill_fraction']=filled/raw_target if raw_target else None
    stats['raw_unfilled_btc']=raw_target-filled
    if not parents:
        stats['unfinished_parents']=None
        stats['remaining_btc']=raw_target-filled
    for label,key in [('last_fill_delay_ms','decision_to_last_fill_ms'),('building_ms','build_ms')]:
        values=[p[key] for p in parents if p[key] is not None]
        stats[label]=dict(mean=sum(values)/len(values) if values else 0,maximum=max(values,default=0))
    durations=[p['finished_at']-p['start'] for p in parents if p['finished_at'] is not None]
    stats['window_active_ms']=dict(mean=sum(durations)/len(durations) if durations else 0,maximum=max(durations,default=0))
    out=dict(result=result,ledger=audit,annual=annual,drawdown=dict(fraction=worst,peak=iso(worst_peak_time),trough=iso(int(equity[trough]['time'])),
            recovery=iso(int(recovered['time'])) if recovered else None,recovery_days=(int(recovered['time'])-worst_peak_time)/86400000 if recovered else None),
            costs=dict(entry_fees=entry_fees,exit_fees=exit_fees,funding=funding,base_slippage=base_slip,spread=spread_cost,extra_exit_impact=extra_impact),
            account_extremes=extremes,insolvent_observations=insolvent,execution=stats,trades=closed,
            positive_trades=sum(r['net']>0 for r in closed),largest_profit_share_of_positive=largest/positive if positive else None,
            quantity_risk_note='Larger absolute inventory and cash exposure; not a same-risk comparison. Stop-risk peak excludes uncertain gap impact; explicit exit-pressure results retained.',
            native_safety_verified=False)
    (path/'ATTRIBUTION.json').write_text(json.dumps(out,indent=2,default=str)+'\n')
    return out


def compare(control: dict,candidate: dict) -> dict:
    old={r['call_time']:r for r in control['trades']};new={r['call_time']:r for r in candidate['trades']}
    components=[]
    for t in sorted(old.keys()|new.keys()):
        a=old.get(t);b=new.get(t)
        if a is None or b is None:
            components.append(dict(call_time=t,event='unpaired_actual_event',net_delta=(b['net'] if b else D(0))-(a['net'] if a else D(0))))
            continue
        gross_quantity=(b['quantity']-a['quantity'])*(a['exit_price']-a['average_entry'])
        entry_price=b['quantity']*(a['average_entry']-b['average_entry'])
        exit_price=b['quantity']*(b['exit_price']-a['exit_price'])
        fees=-(b['entry_fees']+b['exit_fees']-a['entry_fees']-a['exit_fees'])
        funding=-(b['funding']-a['funding'])
        net=b['net']-a['net']
        assert abs(net-(gross_quantity+entry_price+exit_price+fees+funding))<=D('1e-18')
        components.append(dict(call_time=t,control_profitable=a['net']>0,quantity_delta=b['quantity']-a['quantity'],
                               gross_quantity=gross_quantity,entry_price=entry_price,exit_price=exit_price,fees=fees,funding=funding,net_delta=net))
    net=sum((r['net_delta'] for r in components),D(0))
    annual={y:dict(control_return=control['annual'][y]['return_fraction'],candidate_return=candidate['annual'][y]['return_fraction']) for y in control['annual']}
    return dict(cagr_delta=candidate['result']['cagr']-control['result']['cagr'],
                terminal_cny_delta=D(candidate['result']['final_cny'])-D(control['result']['final_cny']),
                terminal_ratio=D(candidate['result']['final_cny'])/D(control['result']['final_cny']),
                mdd_delta=D(candidate['result']['mdd_conservative_envelope'])-D(control['result']['mdd_conservative_envelope']),
                annual=annual,net_usdt_delta=net,components=components,
                largest_positive_increment_share=max((r['net_delta'] for r in components),default=D(0))/net if net else None,
                note='Exact descriptive decomposition of two continuous accounts. Quantity contribution includes inherited compounding and exposure changes, not isolated execution alpha.')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);args=parser.parse_args()
    summary={}
    for stage in ('development','stress','full'):
        a=analyze(args.root/(stage+'-instant'));b=analyze(args.root/(stage+'-five-minute'))
        summary[stage]=compare(a,b)
        print(stage,json.dumps({k:summary[stage][k] for k in ('cagr_delta','terminal_cny_delta','terminal_ratio','mdd_delta','largest_positive_increment_share')},default=str))
    (args.root/'COMPARISON.json').write_text(json.dumps(summary,indent=2,default=str)+'\n')
