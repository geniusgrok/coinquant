"""Reconcile realized and open macro/SX60 positions in saved paired accounts."""
import csv
from decimal import Decimal as D
import gzip
import json
from pathlib import Path

from coinquant.linear_account import FEE
from coinquant.research import iso, spec


def rows(path, name):
    with gzip.open(path/(name+'.csv.gz'),'rt') as stream:
        return list(csv.DictReader(stream))


def campaigns(path):
    result=json.loads((path/'result.json').read_text())
    summary=json.loads((path/'execution_summary.json').read_text())
    by_first={int(p['first_fill']):p for p in summary['parents'] if p['first_fill'] is not None}
    assert len(by_first)==sum(p['first_fill'] is not None for p in summary['parents'])
    active=None;finished=[];q=average=D(0);last=None
    for row in rows(path,'orders'):
        event=row['event'];t=int(row['time']);amount=D(row['quantity_btc']);price=D(row['price_or_mark'])
        if event=='funding_adverse_bound':
            target=active if active is not None else last
            assert target is not None and (active is not None or target['last_order_time']==t)
            target['funding']+=amount*price*D(row['funding_rate'])
            continue
        if event=='entry':
            assert not q and active is None and t in by_first
            parent=by_first[t]
            active=dict(campaign=parent['campaign'],mother_id=parent['parent_id'],
                first_fill_utc=iso(t),last_order_time=t,macro=parent['campaign']<0,
                gross_realized=D(0),unrealized=D(0),fees=D(0),funding=D(0),
                entry_count=1,exit_count=0,open_quantity=D(0))
            q=amount;average=price
        elif event=='rebalance_add':
            assert active is not None and q>0 and amount>0
            average=(q*average+amount*price)/(q+amount);q+=amount
            active['entry_count']+=1
        else:
            assert active is not None and 0<amount<=q
            active['gross_realized']+=amount*(price-average)
            q-=amount;active['exit_count']+=1
        active['fees']+=amount*price*FEE
        active['last_order_time']=t
        assert q==D(row['quantity_after'])
        if not q:
            active['exit_utc']=iso(t);finished.append(active)
            last=active;active=None;average=D(0)
    equity=rows(path,'equity')[-1]
    assert q==D(equity['quantity'])
    if active is not None:
        active['unrealized']=q*(D(equity['mark'])-average)
        active['open_quantity']=q
        active['exit_utc']=None
        finished.append(active)
    for item in finished:
        item['net']=item['gross_realized']+item['unrealized']-item['fees']-item['funding']
    initial=D(spec()['initial_cny'])/D(spec()['cny_per_usd'])*(1-D(spec()['initial_conversion_cost']))
    actual=D(result['final_cny'])/D(spec()['cny_per_usd'])
    error=initial+sum((item['net'] for item in finished),D(0))-actual
    assert abs(error)<D('1e-17'),error
    assert len(finished)==result['counts']['entry']
    assert sum((item['fees'] for item in finished),D(0))==D(result['fees_usdt'])
    assert sum((item['funding'] for item in finished),D(0))==D(result['funding_bound_paid_usdt'])
    return finished,dict(initial_usdt=initial,terminal_usdt=actual,
        exact_reconciliation_error_usdt=error,positions=len(finished),
        macro_positions=sum(item['macro'] for item in finished),
        macro_net_usdt=sum((item['net'] for item in finished if item['macro']),D(0)),
        sx60_net_usdt=sum((item['net'] for item in finished if not item['macro']),D(0)),
        open_positions=sum(bool(item['open_quantity']) for item in finished),
        fees_usdt=sum((item['fees'] for item in finished),D(0)),
        funding_usdt=sum((item['funding'] for item in finished),D(0)),
        worst_macro_net_usdt=min((item['net'] for item in finished if item['macro']),default=None))


def pair(control,candidate):
    c,control_totals=campaigns(control)
    m,candidate_totals=campaigns(candidate)
    candidate_sx={r['campaign'] for r in m if not r['macro']}
    displaced=[r for r in c if r['campaign'] not in candidate_sx]
    gained=[r for r in m if not r['macro'] and r['campaign'] not in {p['campaign'] for p in c}]
    return dict(control=control_totals,candidate=candidate_totals,
        terminal_difference_usdt=candidate_totals['terminal_usdt']-control_totals['terminal_usdt'],
        displaced_sx60_campaigns=[r['campaign'] for r in displaced],
        displaced_control_net_usdt=sum((r['net'] for r in displaced),D(0)),
        newly_executable_sx60_campaigns=[r['campaign'] for r in gained],
        caveat='Macro and displaced campaign net amounts reflect each realized single-account path; differences also include position sizing, capital competition and compounding.',
        control_positions=c,candidate_positions=m)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('accounts',type=Path)
    p.add_argument('output',type=Path)
    args=p.parse_args()
    stages=('development','full','full-stress','absence-787')
    outcome={name:pair(args.accounts/('SX60-'+name),args.accounts/('DFII10-'+name)) for name in stages}
    args.output.write_text(json.dumps(outcome,indent=2,default=str)+'\n')
    print(json.dumps({stage:{side:str(record['candidate'][side]) for side in ('macro_net_usdt','sx60_net_usdt')}
        for stage,record in outcome.items()}))
