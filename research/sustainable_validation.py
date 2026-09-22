"""Read-only attribution, actual prefix identity and finite capital diagnostics."""
import csv
import gzip
import hashlib
import json
from collections import defaultdict, deque
from dataclasses import replace
from decimal import Decimal as D
from pathlib import Path

from pancakequant.capital import CapitalBudget
from pancakequant.linear_account import FEE
from pancakequant.research import invocations, spec, timestamp, iso


def rows(path,name):
    with gzip.open(path/(name+'.csv.gz'),'rt') as f:return list(csv.DictReader(f))


def cash_components(path):
    trace=[json.loads(x) for x in (path/'execution.jsonl').read_text().splitlines()]
    children={int(c['time']):c for c in trace if c['kind']=='child' and D(c['accepted'])>0}
    exits=defaultdict(deque)
    for e in json.loads((path/'execution_summary.json').read_text())['exits']:
        exits[(int(e['time']),e['event'])].append(e)
    q=average=gross=entry_cost=exit_basic=exit_extra=fees=funding=D(0)
    for o in rows(path,'orders'):
        qty=D(o['quantity_btc']);price=D(o['price_or_mark']);event=o['event'];t=int(o['time'])
        if event=='funding_adverse_bound':
            funding+=qty*price*D(o['funding_rate']);continue
        fees+=abs(qty)*price*FEE
        if event in ('entry','rebalance_add'):
            ref=D(children[t]['quote']);entry_cost+=qty*(price-ref)
            average=(q*average+qty*ref)/(q+qty);q+=qty
        else:
            e=exits[(t,event)].popleft();assert D(e['quantity'])==qty
            ref=D(e['reference']);gross+=qty*(ref-average)
            exit_basic+=qty*ref*(D(e['base_slippage'])+D(e['spread'])/2)
            exit_extra+=D(e['extra_impact_usdt']);q-=qty
            if not q:average=D(0)
        assert q==D(o['quantity_after'])
    assert not q,'open final inventory needs unrealized component; do not silently omit'
    cfg=spec();initial=D(cfg['initial_cny'])/D(cfg['cny_per_usd'])*(1-D(cfg['initial_conversion_cost']))
    net=gross-entry_cost-exit_basic-exit_extra-fees-funding
    actual=D(json.loads((path/'result.json').read_text())['final_cny'])/D(cfg['cny_per_usd'])
    assert abs(initial+net-actual)<D('1e-17')
    return dict(gross_reference_pnl=gross,entry_friction=entry_cost,exit_base_friction=exit_basic,
                exit_extra_impact=exit_extra,fees=fees,funding=funding,net=net,
                reconciliation_error=initial+net-actual)


def paired_bridge(control,candidate):
    c=cash_components(control);s=cash_components(candidate)
    control_exits={p['parent_id']:p for p in json.loads((control/'execution_summary.json').read_text())['planned_exits']}
    c_records=[json.loads(x) for x in (control/'execution.jsonl').read_text().splitlines()]
    reference={r['parent_id']:D(r['reference']) for r in c_records
               if r['kind']=='planned_child' and D(r['accepted'])>0}
    delay=D(0);events=[]
    for r in (json.loads(x) for x in (candidate/'execution.jsonl').read_text().splitlines()):
        if r['kind']!='planned_child' or D(r['accepted'])<=0:continue
        if r['parent_id'] not in reference:raise ValueError('unpaired planned exit')
        delta=D(r['accepted'])*(D(r['reference'])-reference[r['parent_id']]);delay+=delta
        events.append(dict(time=r['time'],parent_id=r['parent_id'],raw_delay_pnl=str(delta)))
    costs=sum((c[k]-s[k] for k in ('entry_friction','exit_base_friction','exit_extra_impact','fees')),D(0))
    fund=c['funding']-s['funding']
    residual=s['gross_reference_pnl']-c['gross_reference_pnl']-delay
    terminal=s['net']-c['net']
    assert abs(costs+fund+delay+residual-terminal)<D('1e-17')
    return dict(control=c,candidate=s,terminal_difference_usdt=terminal,
        actual_execution_cost_saving=costs,actual_funding_cost_saving=fund,
        planned_exit_raw_delay_at_candidate_quantities=delay,
        quantity_compounding_capital_and_other_reference_path_residual=residual,
        delay_events=events,interpretation='Exact additive terminal-wallet accounting bridge, not independent causal effects. Delay holds candidate exit quantities fixed; residual includes altered quantities, compounding and capital reductions. No trade profits are summed into a substitute account.')


def prefix_check(root,label):
    dev=root/(label+'-development');full=root/(label+'-full');end=timestamp('2024-01-01T00:00:00Z')
    out={}
    for name in ('orders','equity','decisions'):
        a=rows(dev,name);b=[r for r in rows(full,name) if int(r['time'])<end or (name=='equity' and int(r['time'])==end and r['event']=='close')]
        assert a==b,(label,name,'future input changed development prefix')
        out[name]=dict(rows=len(a),sha256=hashlib.sha256(json.dumps(a,sort_keys=True).encode()).hexdigest())
    return out


def finite_budget_check(path):
    trace=[json.loads(x) for x in (path/'execution.jsonl').read_text().splitlines()]
    parents={p['parent_id']:p for p in json.loads((path/'execution_summary.json').read_text())['parents']}
    count=fail21=0;minimum7=None;minimum21=None;violations=[]
    for r in trace:
        if r['kind']!='child' or D(r['accepted'])<=0:continue
        b=CapitalBudget.restore(parents[r['parent_id']]['capital'])
        qty,entry,price,mark,free=map(D,(r['quantity_after'],r['entry_price'],r['price'],r['mark'],r['free_wallet']))
        seven=free-b.reserve(qty,entry,price,mark)
        twenty_one=free-replace(b,horizon_days=21).reserve(qty,entry,price,mark)
        count+=1;fail21+=twenty_one<0
        if seven<D('-1e-18'):violations.append(r['time'])
        minimum7=seven if minimum7 is None else min(seven,minimum7)
        minimum21=twenty_one if minimum21 is None else min(twenty_one,minimum21)
    cfg=spec();normal=set(invocations(cfg));absent=set(invocations(cfg,stress=True));removed=sorted(normal-absent)
    affected=[r for r in rows(path,'decisions') if int(r['time']) in removed]
    noops=all(D(r['quantity'])==0 and r['action'] in ('no_signal','edge_realized','campaign_consumed') for r in affected)
    return dict(accepted_children=count,seven_day_minimum_reserved_cash_surplus=minimum7,
        seven_day_entry_violations=violations,twenty_one_day_same_rate_minimum_surplus=minimum21,
        twenty_one_day_insufficient_entry_children=fail21,
        frozen_absence_removed_calls=[iso(t) for t in removed],frozen_absence_original_decisions=affected,
        frozen_absence_removed_only_flat_noops=noops,
        qualification='7-day settled-rate/10%-notional planning proxy only; 21-day reserve test is not a production rule. Arbitrarily long absence and historical native rates are not certified.')


def validate(root,output):
    out=dict(prefix={label:prefix_check(root,label) for label in ('S60','SC60','SX60')},
        bridges={stage:paired_bridge(root/('SC60-'+stage),root/('SX60-'+stage)) for stage in ('development','full','full-stress')},
        finite_capital={label+'-'+stage:finite_budget_check(root/(label+'-'+stage))
                        for label in ('S60','SX60') for stage in ('full','full-stress')})
    output.write_text(json.dumps(out,indent=2,default=str)+'\n')
    return out


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    r=validate(a.root,a.output)
    print(json.dumps({k:{n:v for n,v in x.items() if n not in ('control','candidate','delay_events','interpretation')} for k,x in r['bridges'].items()},indent=2,default=str))
    print(json.dumps(r['finite_capital'],indent=2,default=str))
