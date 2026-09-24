"""Conditional independent-event execution diagnostic; no exchange calls."""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path

from coinquant.campaign import Campaign, disposition
from coinquant.capital import CapitalBudget, sustain_position
from coinquant.channel_core import ChannelCore
from coinquant.linear_account import Account
from coinquant.research import invocations, iso, spec, timestamp
from coinquant.types import ZERO
from research.bounded_execution import BoundedEntry, exit_fill
from research.bounded_execution_data import HOUR, MINUTE, _rows, validate_hour
from research.bounded_execution_replay import prepare
from research.minute_evidence import missing_protection_minutes, steps
from research.planned_exit import PlannedExit
from research.sustainable_replay import exit_minutes

DAY = 24 * HOUR
PROTOCOL = Path('evidence/executable-opportunities-20260924/PROTOCOL.md')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parents(roots):
    found = {}
    for source, root in roots.items():
        for parent in json.loads((root/'execution_summary.json').read_text())['parents']:
            key = ('SX60' if source == 'SX60' else 'UC4', int(parent['campaign']), int(parent['call_time']), 1)
            row = found.setdefault(key, dict(core=key[0], campaign=key[1], call_time=key[2],
                                             direction=1, sources={}, original={}))
            if row['sources'] and (row['original']['stop'] != parent['stop'] or
                                   row['original']['take'] != parent['take']):
                raise ValueError('conflicting original opportunity protection')
            row['sources'][source] = dict(original_fill=parent['filled'],
                                          terminal_reason=parent['terminal_reason'],
                                          attempted=parent['attempted'])
            row['original'] = {name:parent[name] for name in ('stop','take','original_quote','original_price',
                         'previous_hour_quote','entry_limit','maximum','risk_budget')}
    return [found[k] for k in sorted(found,key=lambda v:(v[2],v[0],v[1]))]


def opportunities(cache):
    series, _, warm, _ = cache
    trade = series['klines'];start=timestamp(spec()['start']);end=timestamp(spec()['development_end'])
    models = {'SX60':Campaign('impulse_hold'), 'UC4':ChannelCore()}
    states = {'SX60':{},'UC4':{}}
    for t in range(min(warm),end,4*HOUR):
        source=warm if t<start else trade
        bars=[source[x] for x in range(t,t+4*HOUR,HOUR)]
        hi=max(D(r[2]) for r in bars);lo=min(D(r[3]) for r in bars);close=D(bars[-1][4])
        for name,model in models.items():states[name][t+4*HOUR]=model.update(t+4*HOUR,hi,lo,close)
    return states


class MinuteStore:
    def __init__(self, prepared, roots):
        self.series=prepared[0][0];self.tables={k:dict(v) for k,v in prepared[1][0].items()}
        self.quotes=dict(prepared[2]);self.index={};self.loaded={};self.provenance={}
        for root in roots:
            for path in root.rglob('BTCUSDT-1m-*.zip'):
                kind='markPriceKlines' if 'markPriceKlines' in path.parts else 'klines' if 'klines' in path.parts else None
                if kind is not None:
                    key=(kind,path.name[len('BTCUSDT-1m-'):-4])
                    old=self.index.get(key)
                    if old and digest(old)!=digest(path):raise ValueError('conflicting archived minute day: '+str(key))
                    self.index[key]=path

    def load(self, kind, hour):
        if hour in self.tables[kind]:return True
        date=iso(hour)[:10]
        path=self.index.get((kind,date)) or self.index.get((kind,date[:7]))
        if path is None:return False
        if path not in self.loaded:
            raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
            if Path(str(path)+'.CHECKSUM').read_text().split()[0]!=sha:raise ValueError('minute checksum mismatch')
            rows=_rows(raw);table={int(r[0]):r for r in rows}
            if len(rows)!=len(table):raise ValueError('duplicate minute timestamp')
            self.loaded[path]=table
            self.provenance[str(path)]=dict(bytes=len(raw),sha256=sha)
        rows=self.loaded[path]
        bars=[rows[x] for x in range(hour,hour+HOUR,MINUTE) if x in rows]
        validate_hour(bars,self.series[kind][hour],trade=kind=='klines')
        self.tables[kind].update({int(r[0]):tuple(map(D,r[1:5])) for r in bars})
        if kind=='klines':self.quotes.update({int(r[0]):D(r[7]) for r in bars})
        return True

    def hour(self, t, needs_entry=False):
        # A crossing is ambiguous at hourly precision; resolve its full hour or fail closed.
        if any(t not in self.tables[k] for k in self.tables):
            if not all(self.load(k,t) for k in self.tables):return False
        if needs_entry and t-MINUTE not in self.quotes:
            if not self.load('klines',t-HOUR):return False
        return all(t in self.tables[k] for k in self.tables)


def execute(event, states, calls, prepared, store, instrument):
    t0=event['call_time'];core=event['core'];campaign=event['campaign'];initial=D(1000)
    series,funding,_,_=prepared[0];trade=series['klines'];marks=series['markPriceKlines']
    frozen=spec();slip=D(frozen['slippage_fraction']);spread=D(frozen['spread_fraction'])
    row=dict(event, target_notional_usdt='1000', capital_usdt='1000', status='unresolved',
             fills=[],exit_fills=[],costs={},unknown=None)
    signal=states[core].get(t0//(4*HOUR)*4*HOUR)
    if not signal or signal.identity!=campaign or signal.direction!=1:
        row.update(status='signal_identity_mismatch',unknown='original mother no longer matches current causal signal')
        return row
    if t0 not in calls:raise ValueError('mother outside frozen calls')
    row['signal_at_call']=dict(identity=signal.identity,direction=signal.direction,
                              stop=str(signal.stop),expires=getattr(signal,'expires',None))
    account=Account(initial);parent=None;planned=None;entry_done=False;anchor=None;anchor_id=''
    worst=initial;best=initial;cost=ZERO;prev_exit='';exit_time=None;last_mark=D(0)
    first=t0;end=timestamp(frozen['development_end'])
    for t in range(t0,end,HOUR):
        r=trade[t];m=marks[t];bar=tuple(map(D,r[1:5]));mark=tuple(map(D,m[1:5]))
        o,_,_,c=bar;mo,mh,ml,mc=mark;last_mark=mc
        previous_quote=D(trade[t-HOUR][7])
        # Funding settlement with the original conservative adverse slot convention.
        settled=[(ft,rate) for ft,rate in funding.items() if ft//HOUR*HOUR==t]
        if len(settled)>1:raise ValueError('multiple funding rates in one hour')
        charged=False
        if account.q and settled:
            ft,rate=settled[0]
            if rate>0:account.apply_funding_cost(account.q*(mo if ft==t else mh)*rate)
            charged=True

        def exit_at(now,reason,reference,amount=None):
            nonlocal prev_exit,exit_time
            q=account.q if amount is None else amount
            price,impact=exit_fill(reference,q,previous_quote,slip,spread)
            account.close(q,price);row['exit_fills'].append(dict(time=now,reason=reason,**impact))
            prev_exit=reason;exit_time=now
            if parent is not None and not parent.terminal_reason:parent.finish('protection_or_exit:'+reason,now)
            if planned is not None and not planned.terminal_reason:planned.finish('protection_or_exit:'+reason)

        if account.q:
            if mo<=account.liquidation():
                row.update(status='liquidation_risk',unknown='opening mark crosses liquidation boundary');break
            if mo<=account.sl:exit_at(t,'stop_gap',o)
            elif mo>=account.tp:exit_at(t,'take_gap',o)
        if t in calls:
            budget=CapitalBudget.from_history(t,funding,previous_quote,slip,spread,times=sorted(funding))
            if account.q and not planned:
                if t>=t0+7*DAY or disposition(states[core][t//(4*HOUR)*4*HOUR],account.q,campaign)=='exit':
                    if not store.hour(t,True):row.update(status='data_insufficient',unknown=f'planned_exit_minute:{iso(t)}');break
                    planned=PlannedExit.freeze(account,t,campaign,o,anchor,anchor_id,budget,sliced=True,stress=False)
                else:
                    change=sustain_position(account,budget,o,mo,anchor,instrument,
                                            lambda q:exit_fill(o,q,previous_quote,slip,spread)[0])
                    if change['amount']:
                        row['exit_fills'].append(dict(time=t,reason=change['reason'],quantity=str(change['amount']),
                                                      fill_price=str(change['price'])))
            if t==t0:
                if not budget.valid:row.update(status='blocked',block_reason=budget.reason);break
                if not store.hour(t,True):row.update(status='data_insufficient',unknown=f'entry_minute:{iso(t)}');break
                price=o*(1+slip+spread/2)
                stop=D(event['original']['stop'])
                # The impulse signal's TP is anchored to its earlier completed bar;
                # only UC4 computes the geometric TP from the call price.
                take=D(event['original']['take'])
                if not stop<min(price,mo)<=max(price,mo)<take:
                    row.update(status='blocked',block_reason='unsafe_quote_or_protection');break
                fraction=D(1000)*max(price,mo)/(price*account.equity(mo))
                parent=BoundedEntry.freeze(account,t,campaign,fraction,o,mo,stop,take,previous_quote,
                                           instrument,slip,spread,None,budget=D(6),capital=budget)
                row['call_inputs']=dict(trade_open=str(o),mark_open=str(mo),stop=str(stop),take=str(take),
                                        previous_hour_quote=str(previous_quote),fraction=str(fraction),
                                        initial_budget=budget.record(),parent_maximum=str(parent.maximum),
                                        original_parent=event['original'])
                if parent.maximum==0:row.update(status='blocked',block_reason=parent.terminal_reason);break
        if account.q and missing_protection_minutes(t,account,mark,store.tables):
            if not store.hour(t):
                row.update(status='data_insufficient',unknown=f'held_protection_minute:{iso(t)}');break
        for st,sbar,smark in steps(t,bar,mark,store.tables):
            so,sh,slo,sc=sbar;smo,smh,sml,smc=smark
            if parent and parent.call_time==t and parent.available(st) and st>=parent.start:
                child=parent.attempt(st,account,so,smo,store.quotes,instrument)
                row['fills'].append(child)
                if D(child['accepted']):anchor=smo;anchor_id=child['child_id'];entry_done=True
            if planned and planned.call_time==t and not planned.terminal_reason:
                child=planned.attempt(st,account,so,smo,store.quotes,instrument)
                if D(child['accepted']):
                    row['exit_fills'].append(child)
                    prev_exit=child['event'];exit_time=st
            if account.q:
                if smo<=account.liquidation():row.update(status='liquidation_risk',unknown=f'minute_open_liquidation:{iso(st)}');break
                if smo<=account.sl:exit_at(st,'stop_gap',so)
                elif smo>=account.tp:exit_at(st,'take_gap',so)
            if account.q:
                if smark[2]<=account.liquidation() and smark[2]<=account.sl:
                    row.update(status='data_insufficient',unknown=f'same_minute_stop_liquidation:{iso(st)}');break
                if smark[2]<=account.sl:exit_at(st,'stop',min(account.sl,so))
                elif smark[1]>=account.tp:exit_at(st,'take',account.tp)
        if row['status']!='unresolved':break
        if settled and not charged and account.q:
            ft,rate=settled[0]
            if rate>0:account.apply_funding_cost(account.q*(mo if ft==t else mh)*rate)
        if account.q:
            best=max(best,account.equity(mh));worst=min(worst,account.equity(ml))
        if parent and t>t0 and not account.q and (entry_done or parent.terminal_reason):
            row['status']='closed' if entry_done else 'not_filled';break
        if planned and planned.terminal_reason and account.q:
            row.update(status='data_insufficient',unknown='unresolved_plan_remainder');break
    if row['status']=='unresolved':row['status']='window_end_mark_to_market' if account.q else 'not_filled'
    net=account.equity(last_mark)-initial
    row.update(actual_notional_usdt=str(sum(D(v.get('accepted','0'))*D(v.get('price','0')) for v in row['fills'])),
               final_quantity_btc=str(account.q),net_pnl_usdt=str(account.equity(last_mark)-initial),
               gross_price_pnl_usdt=str(net+account.fees+account.funding),
               net_return=str(account.equity(last_mark)/initial-1),fees_usdt=str(account.fees),
               funding_usdt=str(account.funding),final_wallet_usdt=str(account.wallet),
               unrealized_usdt=str(account.q*(last_mark-account.entry)),entry_time=parent.first_fill if parent else None,
               exit_time=exit_time,exit_reason=prev_exit,holding_hours=((exit_time or end)-(parent.first_fill or t0))/HOUR if parent and parent.first_fill else 0,
               worst_mark_equity_usdt=str(worst),best_mark_equity_usdt=str(best),
               margin_usdt=str(account.margin))
    return row


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('bounded','sx60','pf55','rr','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--minute-root',type=Path,action='append',required=True)
    a=p.parse_args()
    roots={'SX60':a.sx60/'results/accounts/SX60-development',
           'PF55':a.pf55/'replay/UC4-PF55-development-r01',
           'RR':a.rr/'replay/UC4-RR-development-r17'}
    events=parents(roots)
    if len(events)!=165:raise ValueError('conditional mother event set differs from frozen originals')
    root=a.bounded/'inputs/development'
    prepared=exit_minutes(a.sx60/'exit-minutes',prepare(root,a.bounded/'old-controls/development',
                 a.bounded/'inputs/entry-minutes',a.bounded/'evidence/MINUTE_REQUEST.json',
                 a.bounded/'inputs/mark-repair'))
    states=opportunities(prepared[0]);calls=set(invocations(spec()))
    store=MinuteStore(prepared,a.minute_root)
    instrument=json.loads((root/'quantity/current-instrument.json').read_text())['instrument']
    identity=dict(protocol_sha256=digest(PROTOCOL),source_sha256=digest(__file__),
                  initial_prepared_input_identity=prepared[4],originals={name:{file:digest(path/'execution_summary.json')
                  for file,path in [(name,root)]} for name,root in roots.items()},
                  events=len(events),minute_archive_roots=[str(x) for x in a.minute_root])
    a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'FREEZE.json').write_text(json.dumps(identity,indent=2)+'\n')
    with (a.output/'EVENTS.jsonl').open('w') as f:
        for i,event in enumerate(events):
            result=execute(event,states,calls,prepared,store,instrument)
            f.write(json.dumps(result,default=str,ensure_ascii=False)+'\n');f.flush()
            if i%20==0:print(i,result['status'],flush=True)
    (a.output/'MINUTE_SOURCES.json').write_text(json.dumps(store.provenance,indent=2)+'\n')
    print(Counter(json.loads(x)['status'] for x in (a.output/'EVENTS.jsonl').read_text().splitlines()))


if __name__=='__main__':main()
