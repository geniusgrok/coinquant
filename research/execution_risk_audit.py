"""Read-only risk audit of saved shared-account snapshots, not a trading engine."""
from collections import Counter
from decimal import Decimal as D
import json
from pathlib import Path

from coinquant.linear_account import FEE, MMR
from coinquant.linear_sizing import FUNDING_RESERVE, GAP
from research.opportunity_attribution import rows


def audit(path: Path) -> dict:
    result = json.loads((path/'result.json').read_text())
    summary = json.loads((path/'execution_summary.json').read_text())
    parents = {p['parent_id']:p for p in summary['parents']}
    children = [json.loads(line) for line in (path/'execution.jsonl').read_text().splitlines()
                if json.loads(line)['kind']=='child']
    accepted = [r for r in children if D(r['accepted'])>0]
    violations=[]; minima={}; maxima={}; count=0

    def record(target, name, value, row, smaller=False):
        if name not in target or (value<target[name]['value'] if smaller else value>target[name]['value']):
            target[name]=dict(value=value,time=int(row['time']),event=row.get('event','child'))

    for r in accepted:
        p=parents[r['parent_id']]
        q,price,mark,entry,margin,free=map(D,(r['quantity_after'],r['price'],r['mark'],r['entry_price'],r['margin'],r['free_wallet']))
        stop=D(p['stop']);boundary=stop-mark*GAP
        reserve=q*max(price,mark)*(FUNDING_RESERVE+FEE)
        gap_cover=margin+q*(boundary-entry)-q*boundary*(MMR+FEE)
        excess=free-reserve
        for name,value in (('entry_free_after_all_reserves',excess),('entry_gap_coverage',gap_cover)):
            record(minima,name,value,r,True)
            if value < D('-1e-18'):violations.append(dict(time=r['time'],rule=name,value=str(value)))
        if q>D(p['maximum']) or D(r['stop_risk'])>D(p['risk_budget']) or D(r['accepted'])>D(r['capacity']):
            violations.append(dict(time=r['time'],rule='parent_risk_quantity_or_capacity'))
    filled=Counter()
    for r in accepted:filled[r['parent_id']]+=D(r['accepted'])
    for key,p in parents.items():
        if filled[key]!=D(p['filled']) or p['unresolved']:
            violations.append(dict(time=p['call_time'],rule='parent_fill_or_unknown'))

    for r in rows(path,'equity'):
        q,mark,wallet,margin,equity,entry,stop=map(D,(r['quantity'],r['mark'],r['wallet'],r['margin'],r['equity_usdt'],r['average_entry'],r['sl']))
        if wallet<0 or equity<=0 or margin>wallet or margin<0:
            violations.append(dict(time=r['time'],rule='wallet_margin_equity',event=r['event']))
        if not q:continue
        count+=1
        liq=(q*entry-margin)/(q*(1-MMR-FEE))
        values={'free_wallet':wallet-margin,
                'mark_to_liquidation_fraction':(mark-liq)/mark,
                'stop_to_liquidation_fraction':(stop-liq)/mark,
                'isolated_equity_less_maintenance_and_fee':margin+q*(mark-entry)-q*mark*(MMR+FEE),
                'stop_coverage_usdt':margin+q*(stop-entry)-q*stop*(MMR+FEE),
                'rolling_reserve_surplus_usdt':wallet-margin-q*max(mark,entry)*(FUNDING_RESERVE+FEE)}
        for name,value in values.items():record(minima,name,value,r,True)
        for name,value in (('margin_equity',margin/equity),('exposure',q*mark/equity),('margin_usdt',margin),('notional_usdt',q*mark)):
            record(maxima,name,value,r)
        if liq>=stop or liq>=mark:
            violations.append(dict(time=r['time'],rule='liquidation_geometry',event=r['event']))
    funded=[p for p in parents.values() if D(p['maximum'])>0]
    shortfall=sum((D(p['raw_target'])-D(p['maximum']) for p in funded),D(0))
    # A <1 lot difference is precision, not a capital-binding event.
    capital_limited=sum(D(p['raw_target'])-D(p['maximum'])>=D('.001') and D(p['maximum'])*max(D(p['original_price']),D(p['original_quote']))<D('999900') for p in funded)
    out=dict(risk_scale=result['risk_scale'],observed_holding_points=count,accepted_children=len(accepted),
             minimum=minima,maximum=maxima,violations=violations,passed=not violations,
             parent_raw_minus_fundable_btc=shortfall,capital_limited_parent_count=capital_limited,
             child_reasons=dict(Counter(r['reason'] for r in children)),
             counts=result['counts'],assumptions=['Synchronous IOC: pending-order reserve is zero only in this replay; native unresolved orders cannot spend it.',
             'Cash is the shared wallet; isolated collateral remains part of equity, not deducted twice.',
             'Rolling reserve surplus during holding is descriptive, not an unused-entry-budget guarantee.',
             'MMR=.005, cumulative deduction=0, fixed fees and original gap rules remain historical proxies.'])
    (path/'RISK_AUDIT.json').write_text(json.dumps(out,indent=2,default=str)+'\n')
    return out


def buffer_audit(path: Path) -> dict:
    """Track the original last-fill gap boundary without changing saved accounts.

    Funding may consume allocated collateral in the shared model after free cash
    runs out. Entry preflight alone therefore does not certify a holding buffer.
    """
    summary = json.loads((path/'execution_summary.json').read_text())
    parents = {p['parent_id']: p for p in summary['parents']}
    events = [json.loads(line) for line in (path/'execution.jsonl').read_text().splitlines()]
    children = [r for r in events if r['kind']=='child' and D(r['accepted'])>0]
    minimum = None; affected = set(); negative = zero_free = 0
    previous = None; draws = []
    for r in rows(path, 'equity'):
        q, wallet, margin = map(D, (r['quantity'], r['wallet'], r['margin']))
        t = int(r['time'])
        if (previous is not None and q and q==D(previous['quantity'])
                and margin<D(previous['margin']) and D(r['funding'])>D(previous['funding'])):
            draws.append(dict(time=t, margin_decrease=str(D(previous['margin'])-margin),
                              funding_delta=str(D(r['funding'])-D(previous['funding']))))
        previous = r
        if not q:
            continue
        if 'gap_anchor_child' in r:
            eligible = [c for c in children if c['child_id']==r['gap_anchor_child']
                        and int(c['time'])<=t and q<=D(c['quantity_after'])
                        and D(c['entry_price'])==D(r['average_entry'])
                        and D(c['mark'])==D(r['gap_anchor_mark'])]
        else:
            eligible = [c for c in children if int(c['time'])<=t and D(c['quantity_after'])==q
                        and D(c['entry_price'])==D(r['average_entry'])]
        if not eligible:
            raise ValueError('saved holding has no causal confirmed child anchor')
        child = eligible[-1]; parent = parents[child['parent_id']]
        boundary = D(r['sl'])-D(child['mark'])*GAP
        coverage = margin+q*(boundary-D(r['average_entry']))-q*boundary*(MMR+FEE)
        if minimum is None or coverage<D(minimum['gap_coverage_usdt']):
            minimum = dict(time=t, event=r['event'], gap_coverage_usdt=str(coverage),
                           gap_boundary=str(boundary), call_time=parent['call_time'],
                           quantity=str(q), wallet=str(wallet), margin=str(margin),
                           equity=r['equity_usdt'], free_wallet=str(wallet-margin),
                           funding_since_entry=str(D(r['funding'])-D(parent['starting_funding'])))
        zero_free += wallet==margin
        if coverage<D('-1e-18'):
            negative += 1; affected.add(parent['call_time'])
    out = dict(minimum_original_last_fill_gap_coverage=minimum,
               negative_gap_observations=negative, affected_parents=len(affected),
               zero_free_observations=zero_free, funding_margin_draws=draws,
               total_funding_taken_from_margin=str(sum((D(r['margin_decrease']) for r in draws), D(0))),
               original_gap_maintained=not negative,
               qualification='READ_ONLY_BUFFER_DIAGNOSTIC_NOT_NATIVE_SAFETY')
    (path/'BUFFER_AUDIT.json').write_text(json.dumps(out,indent=2)+'\n')
    return out


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('paths',nargs='+',type=Path)
    p.add_argument('--buffer-only',action='store_true');a=p.parse_args()
    for path in a.paths:
        r=buffer_audit(path) if a.buffer_only else audit(path)
        print(path, json.dumps(r,default=str))
