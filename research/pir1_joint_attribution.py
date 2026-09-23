"""Read saved continuous accounts; do not rerun or alter any economic paths."""
import argparse
import csv
import gzip
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path
from statistics import median


FEE = D('.00075')


def year(time):
    return datetime.fromtimestamp(int(time)/1000, timezone.utc).year


def table(path):
    with gzip.open(path, 'rt') as stream:
        return list(csv.DictReader(stream))


def source_hashes(path):
    return {name: hashlib.sha256((path/name).read_bytes()).hexdigest()
            for name in ('result.json','decisions.csv.gz','orders.csv.gz','equity.csv.gz','execution.jsonl')}


def trades(path):
    decisions = {int(row['time']):row for row in table(path/'decisions.csv.gz')}
    events = [json.loads(line) for line in (path/'execution.jsonl').read_text().splitlines()]
    mothers = {row['parent_id']:row for row in events if row['kind']=='mother_created'}
    first_fill = {int(row['time']):(mothers[row['parent_id']],row) for row in events
                  if row['kind']=='child' and row.get('event')=='entry'}
    accepted = {}
    for event in events:
        if event['kind']=='child' and D(event.get('accepted','0'))>0:
            accepted.setdefault(mothers[event['parent_id']]['campaign'],[]).append(event)
    result=[];quantity=entry=D(0);current=None
    for row in table(path/'orders.csv.gz'):
        t=int(row['time']);kind=row['event'];amount=D(row['quantity_btc']);price=D(row['price_or_mark'])
        if kind=='entry':
            if quantity or t not in first_fill:raise ValueError('entry has no matched flat mother')
            mother,child=first_fill[t];quantity=amount;entry=price
            current=dict(campaign=mother['campaign'],call_time=mother['call_time'],first_fill=t,
                         entry_equity=D(decisions[mother['call_time']]['equity']),
                         risk_budget=D(mother['risk_budget']),first_price=price,
                         stop=D(mother['stop']),first_notional=D(child['quantity_after'])*D(child['mark']),
                         first_margin=D(child['margin']),net=D(0),fees=D(0),funding=D(0))
            fee=amount*price*FEE;current['net']-=fee;current['fees']+=fee
        elif kind=='rebalance_add':
            if current is None or amount<=0:raise ValueError('unowned add')
            entry=(quantity*entry+amount*price)/(quantity+amount);quantity+=amount
            fee=amount*price*FEE;current['net']-=fee;current['fees']+=fee
        elif kind=='funding_adverse_bound':
            if current is None:raise ValueError('unowned funding')
            cost=amount*price*D(row['funding_rate']);current['net']-=cost;current['funding']+=cost
        else:
            if current is None or not 0<amount<=quantity:raise ValueError('unowned reduction')
            fee=amount*price*FEE;current['net']+=amount*(price-entry)-fee;current['fees']+=fee
            quantity-=amount
            if not quantity:
                current.update(flat_at=t,exit_reason=kind,
                               final_stop_risk=D(accepted[current['campaign']][-1]['stop_risk']),
                               accepted_slices=len(accepted[current['campaign']]))
                result.append(current);current=None;entry=D(0)
        if quantity!=D(row['quantity_after']):raise ValueError('order quantity mismatch')
    if current is not None:raise ValueError('terminal position needs separate unrealized attribution')
    return result


def drawdown(path):
    peak=worst_peak=trough=None
    with gzip.open(path/'equity.csv.gz','rt') as stream:
        for row in csv.DictReader(stream):
            if peak is None or D(row['equity_usdt'])>D(peak['equity_usdt']):peak=row
            if trough is None or D(row['drawdown'])>D(trough['drawdown']):worst_peak=peak;trough=row
    def state(row):
        return {key:row[key] for key in ('time','event','equity_usdt','quantity','mark',
                                         'wallet','average_entry','fees','funding','drawdown')}
    p,t=state(worst_peak),state(trough)
    unrealized=lambda x:D(x['quantity'])*(D(x['mark'])-D(x['average_entry']))
    return dict(peak=p,trough=t,equity_change_usdt=str(D(t['equity_usdt'])-D(p['equity_usdt'])),
                wallet_change_usdt=str(D(t['wallet'])-D(p['wallet'])),
                unrealized_change_usdt=str(unrealized(t)-unrealized(p)),
                unrealized_at_peak_usdt=str(unrealized(p)),
                unrealized_at_trough_usdt=str(unrealized(t)))


def annual(path,closed):
    annual={};calls=Counter();actions={}
    with gzip.open(path/'equity.csv.gz','rt') as stream:
        for row in csv.DictReader(stream):
            if row['event']!='close':continue
            y=year(row['time']);entry=annual.setdefault(y,dict(hours=0,holding_hours=0))
            entry['hours']+=1;entry['holding_hours']+=D(row['quantity'])!=0
            entry['last_equity_usdt']=row['equity_usdt']
    for row in table(path/'decisions.csv.gz'):
        y=year(row['time']);calls[y]+=1
        actions.setdefault(y,Counter())[row['action']]+=1
    for y,entry in annual.items():
        items=[x for x in closed if year(x['flat_at'])==y]
        entry.update(calls=calls[y],actions=dict(actions.get(y,{})),opened=sum(year(x['first_fill'])==y for x in closed),
                     closed=len(items),wins=sum(x['net']>0 for x in items),
                     closed_trade_net_usdt=str(sum((x['net'] for x in items),D(0))),
                     closed_trade_fees_usdt=str(sum((x['fees'] for x in items),D(0))),
                     closed_trade_funding_usdt=str(sum((x['funding'] for x in items),D(0))))
    return annual


def build(original,corrected,control,full_control,attribution,semantics):
    children={row['identity']:row for row in json.loads(attribution.read_text())['children']}
    accounts={name:trades(path) for name,path in
              [('original',original),('corrected',corrected),('control',control),('full_control',full_control)]}
    original_children=[]
    for trade in accounts['original']:
        identity=trade['campaign']
        if identity not in children:continue
        child=children[identity];eq=trade['entry_equity']
        original_children.append(dict(campaign=identity,first_fill=trade['first_fill'],
            parent_identity=child['parent_identity'],parent_invalidation_reasons=child['parent_invalidation_reasons'],
            entry_price=str(trade['first_price']),stop=str(trade['stop']),
            distance_to_stop_fraction=str((trade['first_price']-trade['stop'])/trade['first_price']),
            planned_stop_risk_usdt=str(trade['final_stop_risk']),
            planned_stop_risk_fraction=str(trade['final_stop_risk']/eq),
            first_notional_to_equity=str(trade['first_notional']/eq),
            first_margin_to_equity=str(trade['first_margin']/eq),
            accepted_slices=trade['accepted_slices'],fees_usdt=str(trade['fees']),
            funding_usdt=str(trade['funding']),net_usdt=str(trade['net']),
            flat_at=trade['flat_at'],exit_reason=trade['exit_reason']))
    if len(original_children)!=6:raise ValueError('saved original child fill count changed')
    child_sum=sum((D(row['net_usdt']) for row in original_children),D(0))
    corrected_children=[x for x in accounts['corrected'] if x['campaign'] in children]
    affected=[]
    observed_equity=table(original/'equity.csv.gz')
    observed_orders=table(original/'orders.csv.gz')
    original_by_id={x['campaign']:x for x in accounts['original']}
    corrected_by_id={x['campaign']:x for x in accounts['corrected']}
    seen=set()
    for row in json.loads(semantics.read_text())['rows']:
        owner=row['held_campaign']
        if owner in seen:continue
        seen.add(owner)
        beginning=next(x for x in observed_equity if x['event']=='open' and int(x['time'])==row['call_time'])
        ending=next(x for x in observed_equity if x['event']=='close'
                    and int(x['time'])>=row['first_flat_time'] and D(x['quantity'])==0)
        later=[x for x in observed_orders if row['call_time']<=int(x['time'])<=row['first_flat_time']]
        old=original_by_id[owner];fixed=corrected_by_id.get(owner)
        affected.append(dict(campaign=owner,first_held_call=row['call_time'],
            actual_first_flat=row['first_flat_time'],exposure_extension_hours=row['exposure_extension_hours'],
            actual_first_flat_event=row['first_flat_event'],
            observed_mark_to_flat_equity_change_usdt=str(D(ending['equity_usdt'])-D(beginning['equity_usdt'])),
            observed_extension_fees_usdt=str(sum((abs(D(x['quantity_btc']))*D(x['price_or_mark'])*FEE
                for x in later if x['event']!='funding_adverse_bound'),D(0))),
            observed_extension_funding_usdt=str(sum((D(x['quantity_btc'])*D(x['price_or_mark'])*D(x['funding_rate'])
                for x in later if x['event']=='funding_adverse_bound'),D(0))),
            old_whole_campaign_net_usdt=str(old['net']),old_whole_campaign_fees_usdt=str(old['fees']),
            old_whole_campaign_funding_usdt=str(old['funding']),
            corrected_same_campaign_net_usdt=str(fixed['net']) if fixed else None,
            corrected_same_campaign_flat_time=fixed['flat_at'] if fixed else None))
    if len(affected)!=9:raise ValueError('semantics trace changed')
    full=accounts['full_control']
    spans={}
    for label,start,end in [('2020_2023',2020,2023),('2024_2026',2024,2026)]:
        values=[x['net']/x['entry_equity'] for x in full if start<=year(x['first_fill'])<=end]
        risks=[x['risk_budget']/x['entry_equity'] for x in full if start<=year(x['first_fill'])<=end]
        spans[label]=dict(trades=len(values),wins=sum(v>0 for v in values),
            mean_net_to_entry_equity=str(sum(values)/len(values)),
            median_net_to_entry_equity=str(median(values)),
            median_mother_stop_risk_to_entry_equity=str(median(risks)))
    return dict(status='saved_account_attribution_no_new_economic_account',
        original_children=original_children,original_child_trade_net_usdt=str(child_sum),
        affected_ownership=affected,
        corrected_children_count=len(corrected_children),
        corrected_child_trade_net_usdt=str(sum((x['net'] for x in corrected_children),D(0))),
        worst_drawdown={name:drawdown(path) for name,path in
            [('original',original),('corrected',corrected),('control',control),('full_control',full_control)]},
        full_control_annual=annual(full_control,full),full_control_trade_spans=spans,
        account_sha256={name:source_hashes(path) for name,path in
            [('original',original),('corrected',corrected),('control',control),('full_control',full_control)]})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('original','corrected','control','full-control','attribution','semantics','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    a.output.write_text(json.dumps(build(a.original,a.corrected,a.control,a.full_control,a.attribution,a.semantics),
                                    indent=2,default=str)+'\n')
