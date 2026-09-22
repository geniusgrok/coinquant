"""Read saved continuous accounts; never optimize, place orders, or synthesize bars."""
import argparse
import csv
import gzip
import hashlib
import json
from bisect import bisect_right
from decimal import Decimal as D
from pathlib import Path

from coinquant.linear_account import FEE, TICK
from coinquant.research import iso, spec, timestamp
from coinquant.types import floor_step
from research.sustainable_validation import cash_components
from research.verify_account_ledger import verify


def rows(path, name):
    with gzip.open(path / (name + '.csv.gz'), 'rt') as stream:
        return list(csv.DictReader(stream))


def drawdown(points, initial):
    peak = initial
    peak_time = timestamp(spec()['start'])
    worst = D(0)
    episode = None
    for t, equity in points:
        if equity > peak:
            peak, peak_time = equity, t
        dd = 1 - equity / peak
        if dd > worst:
            worst = dd
            episode = dict(peak_time=peak_time, trough_time=t, peak=peak, trough=equity)
    if episode is not None:
        recovery = next((t for t, e in points if t > episode['trough_time'] and e >= episode['peak']), None)
        episode.update(peak_utc=iso(episode['peak_time']), trough_utc=iso(episode['trough_time']),
                       recovery_utc=iso(recovery) if recovery else None,
                       days_from_peak_to_recovery_or_end=D((recovery or points[-1][0])-episode['peak_time'])/86400000,
                       recovered=recovery is not None)
    return dict(mdd=worst, episode=episode)


def analyze(path):
    result = json.loads((path/'result.json').read_text())
    cfg = spec(); fx = D(cfg['cny_per_usd']); initial = D(cfg['initial_cny'])/fx
    equity = rows(path, 'equity'); orders = rows(path, 'orders'); decisions = rows(path, 'decisions')
    trace = [json.loads(line) for line in (path/'execution.jsonl').read_text().splitlines()]
    summary = json.loads((path/'execution_summary.json').read_text())
    points = [(int(r['time']), D(r['equity_usdt'])) for r in equity]
    closes = [(int(r['time']), D(r['equity_usdt'])) for r in equity if r['event']=='close']
    annual = []; previous = D(cfg['initial_cny'])
    for year in range(2020, 2024):
        end = timestamp(f'{year+1}-01-01T00:00:00Z')
        final = next(value*fx for t,value in closes if t==end)
        annual.append(dict(year=year, start_cny=previous, end_cny=final, net_return=final/previous-1))
        previous = final
    # One entry campaign remains one trade through same-parent fills and risk reductions.
    q = average = D(0); current = None; trades = []; post_exit_funding = D(0)
    parents = {p['parent_id']: p for p in summary['parents']}
    entries = {int(p['first_fill']):p for p in parents.values() if p['first_fill'] is not None}
    for order in orders:
        t=int(order['time']); qty=D(order['quantity_btc']); price=D(order['price_or_mark']); event=order['event']
        if event=='funding_adverse_bound':
            cost=qty*price*D(order['funding_rate'])
            if current is not None: current['funding']+=cost
            else: post_exit_funding+=cost
            continue
        if event=='entry':
            assert q==0 and current is None
            p=entries[t]
            current=dict(entry_time=t,call_time=p['call_time'],campaign=p['campaign'],entry_utc=iso(t),
                         entry_quantity=qty,total_entry_quantity=D(0),gross_realized=D(0),fees=D(0),funding=D(0),exits=[])
        assert current is not None
        current['fees']+=abs(qty)*price*FEE
        if event in ('entry','rebalance_add'):
            average=(q*average+qty*price)/(q+qty);q+=qty;current['total_entry_quantity']+=qty
        else:
            assert 0<qty<=q
            current['gross_realized']+=qty*(price-average);q-=qty
            current['exits'].append(dict(time=t,utc=iso(t),event=event,quantity=qty,price=price,remaining=q))
            if q==0:
                current.update(exit_time=t,exit_utc=iso(t),holding_days=D(t-current['entry_time'])/86400000,
                               net=current['gross_realized']-current['fees']-current['funding'])
                trades.append(current);current=None;average=D(0)
        assert q==D(order['quantity_after'])
    assert not q and current is None
    cash=cash_components(path)
    assert abs(sum((r['net'] for r in trades),D(0))-post_exit_funding-cash['net'])<D('1e-17')
    invocation_times=json.loads((path/'invocations.json').read_text())
    gaps=[]
    for trade in trades:
        during=[t for t in invocation_times if trade['entry_time']<t<trade['exit_time']]
        gaps.extend(b-a for a,b in zip([trade['entry_time'],*during],[*during,trade['exit_time']]))
    holding=[r for r in equity if D(r['quantity'])]
    errors=[]
    for child in (r for r in trace if r['kind']=='child' and D(r['accepted'])>0):
        parent=parents[child['parent_id']]
        if not parent['start']<=int(child['time'])<parent['deadline']: errors.append(['entry_deadline',child['time']])
    for parent in parents.values():
        assert not parent['unresolved'] and parent['terminal_reason']
        expected=floor_step(D(parent['original_price'])*(D(parent['original_price'])/D(parent['stop']))**20,TICK)+TICK
        if result['candidate']=='M60' and expected!=D(parent['take']): errors.append(['non_impulse_tp',parent['call_time']])
    for parent in summary['planned_exits']:
        assert not parent['unresolved'] and parent['terminal_reason']
    minfree=min(D(r['wallet'])-D(r['margin']) for r in holding)
    return dict(result=result, ledger=verify(path), annual=annual, continuous=drawdown(points,initial),
                completed_hour_closes=drawdown(closes,initial), cash=cash, trades=trades,
                post_exit_adverse_funding=post_exit_funding,
                holding_fraction=D(result['holding_hours'])/len(closes),
                longest_holding_days=max(r['holding_days'] for r in trades),
                longest_no_invocation_while_held_days=D(max(gaps))/86400000,
                longest_held_trade=max(trades,key=lambda r:r['holding_days']),
                maximum_notional_equity=max(abs(D(r['quantity']))*D(r['mark'])/D(r['equity_usdt']) for r in holding),
                maximum_allocated_margin_equity=max(D(r['margin'])/D(r['equity_usdt']) for r in holding),
                minimum_free_wallet=minfree,
                winners=sum(r['net']>0 for r in trades), losers=sum(r['net']<=0 for r in trades),
                execution_errors=errors, observed_native_unknown_events=sum(v for k,v in result['counts'].items() if 'unknown' in k),
                observed_liquidations=result['counts'].get('liquidation',0),
                native_execution_qualification='NOT_VERIFIED: historical proxy replay cannot establish live unknown-result safety',
                finite_budget=json.loads((path/'FINITE_BUDGET.json').read_text()),
                risk_audit=json.loads((path/'RISK_AUDIT.json').read_text()),
                gap_audit=json.loads((path/'BUFFER_AUDIT.json').read_text()))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('accounts',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();out={name:analyze(args.accounts/(name+'-development')) for name in ('M60','SX60')}
    m,c=out['M60'],out['SX60'];me={r['call_time'] for r in m['trades']};ce={r['call_time'] for r in c['trades']}
    out['entry_changes']=dict(common_calls=sorted(me&ce),new_trades=[r for r in m['trades'] if r['call_time'] not in ce],
                              lost_trades=[r for r in c['trades'] if r['call_time'] not in me],
                              interpretation='Compared by original invocation time, not by different model-specific campaign IDs. Descriptive only.')
    out['cash_difference_M60_minus_SX60']={k:m['cash'][k]-c['cash'][k] for k in m['cash'] if isinstance(m['cash'][k],D)}
    cfg=spec();years=D(timestamp(cfg['end'])-timestamp(cfg['start']))/D(31556952000)
    target=D(cfg['initial_cny'])*D('2.5')**years
    sx=D('1149830.31')
    out['full_target']=dict(years=years,cagr=D('1.5'),required_cny=target,
                           saved_sx60_cny=sx,gap_cny=target-sx,required_terminal_multiplier=target/sx,
                           note='M60 full-window not run: development risk failure. Saved SX60 value is historical, not a new full-window run.')
    assert not m['execution_errors'] and not c['execution_errors']
    assert abs(m['continuous']['mdd']-D(m['result']['mdd_conservative_envelope']))<D('1e-20')
    args.output.write_text(json.dumps(out,indent=2,default=str)+'\n')
    for name in ('M60','SX60'):
        r=out[name];print(name,json.dumps({k:r[k] for k in ('annual','completed_hour_closes','longest_holding_days','longest_no_invocation_while_held_days','maximum_notional_equity','maximum_allocated_margin_equity','minimum_free_wallet','cash','winners','losers')},default=str))
    print('target',json.dumps(out['full_target'],default=str))
    print('entry_counts',len(me&ce),len(me-ce),len(ce-me))


if __name__=='__main__':main()
