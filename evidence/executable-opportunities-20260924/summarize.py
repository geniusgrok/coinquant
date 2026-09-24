"""Audit and summarize the frozen independent-event output, without treating gaps as losses."""
import json
from collections import Counter, defaultdict
from decimal import Decimal as D
from pathlib import Path
from statistics import median
import sys


def main(root):
    rows=[json.loads(line) for line in (root/'EVENTS.jsonl').read_text().splitlines()]
    assert len(rows)==165 and len({(r['core'],r['campaign'],r['call_time'],r['direction']) for r in rows})==165
    assert all(D(r['target_notional_usdt'])==D(1000) and D(r['capital_usdt'])==D(1000) for r in rows)
    for r in rows:
        assert abs(D(r['final_wallet_usdt'])+D(r['unrealized_usdt'])-D(1000)-D(r['net_pnl_usdt']))<D('1e-16')
        assert all(v['time']>=r['call_time']+60000 for v in r['fills'] if D(v['accepted']))
        if r['status']=='closed':assert D(r['final_quantity_btc'])==0 and r['unknown'] is None
        if r['status']=='blocked':assert not r['fills'] and D(r['net_pnl_usdt'])==0
    known=[r for r in rows if r['status']=='closed']
    blocked=[r for r in rows if r['status']=='blocked']
    def stats(group):
        vals=[D(r['net_pnl_usdt']) for r in group]
        return dict(count=len(group),sum_net_usdt=str(sum(vals,D(0))),
                    mean_net_usdt=str(sum(vals,D(0))/len(vals)) if vals else None,
                    median_net_usdt=str(median(vals)) if vals else None,
                    worst_net_usdt=str(min(vals)) if vals else None,
                    loss_count=sum(v<0 for v in vals))
    sections={}
    for name,predicate in (
        ('SX60',lambda r:r['core']=='SX60'),('UC4',lambda r:r['core']=='UC4'),
        ('2020-2021',lambda r:r['call_time']<1640995200000),
        ('2022-2023',lambda r:r['call_time']>=1640995200000),
        ('original_RR_rejected',lambda r:'RR' in r['sources'] and D(r['sources']['RR']['original_fill'])==0),
        ('original_PF55_rejected',lambda r:'PF55' in r['sources'] and D(r['sources']['PF55']['original_fill'])==0),
        ('original_any_filled',lambda r:any(D(s['original_fill'])>0 for s in r['sources'].values()))):
        eligible=[r for r in rows if predicate(r)]
        sections[name]=dict(total_events=len(eligible),closed=stats([r for r in eligible if r['status']=='closed']),
                            blocked=sum(r['status']=='blocked' for r in eligible),
                            unknown=sum(r['status']=='data_insufficient' for r in eligible))
    grouped=defaultdict(list)
    for r in known:grouped[r['core'],r['campaign']].append(r)
    campaigns=[dict(core=key[0],campaign=key[1],calls=len(group),
                    sum_net_usdt=str(sum((D(r['net_pnl_usdt']) for r in group),D(0))))
               for key,group in grouped.items()]
    intervals=sorted((r['entry_time'],r['exit_time']) for r in known if r['entry_time'] is not None)
    overlaps=sum(a[0]<b[1] and b[0]<a[1] for i,a in enumerate(intervals) for b in intervals[i+1:])
    pnl=sorted((D(r['net_pnl_usdt']) for r in known),reverse=True)
    summary=dict(protocol_sha256=json.loads((root/'FREEZE.json').read_text())['protocol_sha256'],
        all_events=len(rows),closed=stats(known),blocked=len(blocked),
        unknown_by_reason=dict(Counter(r['unknown'].split(':')[0] for r in rows if r['unknown'])),
        sections=sections,campaign_count=len(grouped),campaign_repeated=sum(len(g)>1 for g in grouped.values()),
        overlapping_closed_event_pairs=overlaps,
        top_five_share_of_positive_pnl=str(sum(pnl[:5])/sum((v for v in pnl if v>0),D(0))),
        worst_five_net_usdt=[str(x) for x in sorted(pnl)[:5]],
        campaigns=sorted(campaigns,key=lambda c:(c['core'],c['campaign'])))
    (root/'SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:summary[k] for k in ('all_events','closed','unknown_by_reason','campaign_count','campaign_repeated','overlapping_closed_event_pairs','top_five_share_of_positive_pnl','sections')},indent=2))


if __name__=='__main__':main(Path(sys.argv[1]))
