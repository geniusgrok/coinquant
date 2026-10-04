"""Finite BTC failure routes, using original owned fills and completed bars.

Event attribution and forward-close studies only admit account work. They never
change a default or claim an independently financed counterfactual account.
"""
import argparse
from bisect import bisect_right
from collections import defaultdict, deque, Counter
from decimal import Decimal as D
import gzip
import json
from pathlib import Path
from statistics import median
import subprocess
import time

from research import flow_risk as f, continuous_routes as c

SPEC = Path(__file__).with_name('persistent-spec.json')


def status(checks, enough):
    return 'ACCOUNT_ENTRANT' if all(checks.values()) else 'SUPPORT_PENDING' if not enough else 'REJECT_MECHANISM'


def entry_gate(events, controls):
    result = f.gate(events, controls, len(events), D(1))
    enough = result['gates']['count'] and result['gates']['era_count']
    result.update(status=status(result['gates'], enough), events=events,
                  meaning='Owned basket attribution; no reinvestment, wallet or prospective alpha proof.')
    return result


def owned_spot(ledger):
    """Rebuild the new questions' sale fractions, including actual BTC fees."""
    owners = {str(json.loads(a[3])['orderId']): json.loads(a[1])
              for a in ledger['allocations'] if 'orderId' in json.loads(a[3])}
    books, cohorts = defaultdict(deque), []
    meta = {e['id']: e for e in ledger['opportunity_ledger'] if e['event'] == 'fill'}
    for trade in ledger['fills']:
        qty, quote, fee = (D(trade[k]) for k in ('qty', 'quote', 'commission'))
        owner = owners[str(trade['order_id'])]
        weights = {int(k): D(v) for k, v in owner['weights'].items()}
        total = sum(weights.values())
        if trade['buyer']:
            net = qty-(fee if trade['commission_asset'] == 'BTC' else D(0))
            cost = quote+(fee if trade['commission_asset'] == 'USDT' else D(0))
            cohort = dict(id=trade['order_id'], time_ms=trade['time'], quantity=net,
                          notional=cost, left=net, owner=owner, meta=meta[trade['id']],
                          settlements=[], price=D(trade['price']))
            cohorts.append(cohort)
            for w, weight in weights.items():
                books[w].append(dict(cohort=cohort, left=net*weight/total))
        else:
            sold = qty+(fee if trade['commission_asset'] == 'BTC' else D(0))
            proceeds = quote-(fee if trade['commission_asset'] == 'USDT' else D(0))
            for w, weight in weights.items():
                amount = sold*weight/total
                while amount > D('1e-24'):
                    if not books[w]:
                        raise ValueError('unowned spot sale')
                    lot = books[w][0]
                    take = min(amount, lot['left'])
                    lot['left'] -= take
                    lot['cohort']['left'] -= take
                    lot['cohort']['settlements'].append(dict(time_ms=trade['time'], sleeve=w,
                        quantity=take, proceeds=proceeds*take/sold))
                    amount -= take
                    if lot['left'] <= D('1e-24'):
                        books[w].popleft()
    return cohorts


def rolling(bars, length):
    rows, result = deque(maxlen=length), {}
    for stamp, row in sorted(bars.items()):
        if len(rows) == length:
            closes = [r[3] for r in rows]
            returns = [b/a-1 for a, b in zip(closes, closes[1:])]
            result[stamp] = dict(low=min(r[2] for r in rows), high=max(r[1] for r in rows),
                close_high=max(closes), close_low=min(closes), first=closes[0],
                rms=(sum(r*r for r in returns)/len(returns)).sqrt(),
                volume_median=median(r[4] for r in rows))
        rows.append(row)
    return result


def signal(bars, stamp, name, project):
    interval, length = (f.DAY, 20) if project == 'spot' else (f.FOUR, 60 if name == 'state-trend' else 42)
    keys = list(range(stamp-length*interval, stamp+interval, interval))
    if not all(t in bars for t in keys) or stamp-interval not in bars:
        return None
    previous, row = bars[stamp-interval], bars[stamp]
    prior = [bars[t] for t in keys[:-1]]
    closes = [r[3] for r in prior]
    low, high = min(r[2] for r in prior), max(r[1] for r in prior)
    if name == 'state-trend':
        old_keys = list(range(stamp-(length+1)*interval, stamp-interval, interval))
        if not all(t in bars for t in old_keys):
            return None
        valid = (previous[3] > max(bars[t][3] for t in old_keys)
                 and row[3] > max(closes) and row[4] >= median(r[4] for r in prior))
        stop = min(r[2] for r in prior[-10:])
        take = row[3]*(row[3]/stop)**20
        life = 7*f.DAY
    else:
        returns = [b/a-1 for a,b in zip(closes,closes[1:])]
        rms = (sum(r*r for r in returns)/len(returns)).sqrt()
        midpoint = (high+low)/2
        cost = D('.003') if project == 'spot' else D('.0037')
        valid = (abs(closes[-1]/closes[0]-1) <= rms and previous[3] <= low+(high-low)/4
                 and previous[3] < midpoint < row[3] and high-low > 4*cost*row[3])
        stop, take, life = low, high, 7*f.DAY if project == 'spot' else 14*f.FOUR
    if not valid or not 0 < stop < row[3] < take:
        return None
    return dict(signal_ms=stamp, available_ms=stamp+interval, stop=stop, take=take, life_ms=life)


def proxy_return(bars, at, mark, stop, take, life, funding=()):
    """Full subsequent bars, adverse barrier first; partial entry bar unknown."""
    step = f.FOUR if any(t % f.DAY for t in bars) else f.DAY
    deadline = min(at+life, f.END)
    keys = [t for t in sorted(bars) if at < t and t+step <= deadline]
    if not keys or deadline >= f.END:
        return None
    exit_price, exit_ms = bars[keys[-1]][3], keys[-1]+step
    for t in keys:
        row = bars[t]
        if row[2] <= stop:
            exit_price, exit_ms = min(row[0], stop), t+step
            break
        if row[1] >= take:
            exit_price, exit_ms = take, t+step
            break
    carry = sum((rate*bars.get(t//step*step, bars[keys[0]])[0]/mark
                 for t,rate in funding if at < t <= exit_ms), D(0))
    cost = D('.0037') if step == f.FOUR else D('.003')
    return dict(net_return=exit_price/mark-1-cost-carry, exit_ms=exit_ms,
                cost=cost, funding=carry, partial_entry_bar='OMITTED_UNCERTAIN', account=False)


def spot_lifecycle(ledger, bars, old_screen):
    cohorts = owned_spot(ledger)
    controls = [dict(r,notional=D(r['notional']),gain=D(r['gain'])) for r in old_screen['alpha_events']]
    by_id = {r['id']: r for r in controls}
    atr = f.atr_trail(bars)
    chased, partial = [], []
    for lot in cohorts:
        stamp = lot['owner']['signal_ms']
        if stamp not in bars or stamp not in atr:
            continue
        # Unclipped ATR is needed for the chase question, not the stop distance.
        keys = list(range(stamp-13*f.DAY,stamp+f.DAY,f.DAY))
        if not all(t in bars and t-f.DAY in bars for t in keys):
            continue
        raw_atr = sum(max(bars[t][1]-bars[t][2],abs(bars[t][1]-bars[t-f.DAY][3]),
                          abs(bars[t][2]-bars[t-f.DAY][3])) for t in keys)/14
        before = D(lot['meta']['decision_price'])
        if before > bars[stamp][3]+raw_atr:
            event = dict(by_id[lot['id']], signal_ms=stamp, signal_close=bars[stamp][3],
                         prior_atr=raw_atr, decision_price=before)
            chased.append(event)
            partial.append(dict(event, notional=event['notional']/2, gain=event['gain']/2))
    rules = {name: [] for name in ('repair-stall','repair-rebreak')}
    controls_risk = []
    prior20 = rolling(bars,20)
    decisions = [e for e in ledger['opportunity_ledger'] if e['event']=='decision']
    stamps = sorted(bars)
    for lot in cohorts:
        weights = {int(k):D(v) for k,v in lot['owner']['weights'].items()}
        repair = {w for w in weights if lot['owner'].get('repair',{}).get(str(w))}
        if not repair:
            continue
        handoffs, first = {}, {}
        for day in stamps:
            if day < lot['time_ms']//f.DAY*f.DAY:
                continue
            for w in repair:
                if w in handoffs:
                    continue
                history = [bars.get(day-i*f.DAY) for i in range(400)]
                if all(history) and bars[day][3] > sum(r[3] for r in history[:w])/w and bars[day][3] >= D('.89')*max(r[3] for r in history):
                    handoffs[w] = day+f.DAY
        seen = set()
        for e in decisions:
            at, day = e['decision_ms'], e['completed_bar_ms']
            if at < lot['time_ms'] or day not in prior20:
                continue
            quantities = {}
            for w in repair:
                total = lot['quantity']*weights[w]/sum(weights.values())
                left = total-sum(s['quantity'] for s in lot['settlements'] if s['sleeve']==w and s['time_ms']<=at)
                if (left > D('.00001') and at < handoffs.get(w,f.END+1)
                        and e['sleeves'][str(w)]['action']=='hold'):
                    quantities[w] = left
            if not quantities:
                continue
            mark = f.price_at(bars,at)
            event = dict(id=lot['id'],time_ms=at,mark=mark,quantity=sum(quantities.values()),
                         quantities=quantities,reductions=quantities,removed=sum(quantities.values()),
                         notional=sum(quantities.values())*mark,closed=True,gain=D(0))
            for w, amount in quantities.items():
                future=[s for s in lot['settlements'] if s['sleeve']==w and s['time_ms']>at]
                sold=sum(s['quantity'] for s in future)
                event['closed'] &= sold >= amount*D('.999')
                if sold:
                    event['gain'] += amount*(mark*D('.9985005')-sum(s['proceeds'] for s in future)/sold)
            event['removed_downside_usdt'],event['full_owned_days']=c.stress(lot,event,bars,'spot')
            if not first:
                controls_risk.append(event)
                first['control']=True
            triggers={'repair-stall':day+f.DAY >= lot['time_ms']+14*f.DAY and bars[day][3]<=lot['price'],
                      'repair-rebreak':bars[day][3]<prior20[day]['low']}
            for name, yes in triggers.items():
                if yes and name not in seen:
                    rules[name].append(event)
                    seen.add(name)
    output={'entry-chase':entry_gate(chased,controls),'entry-chase-soft':entry_gate(partial,controls)}
    for name,events in rules.items():
        direct=entry_gate(events,controls_risk)
        risk=c.risk_gate(events,controls_risk)
        # A valid risk tradeoff may admit sacrificing profit; not waive counts.
        if risk['status']=='RISK_ACCOUNT_ENTRANT':
            direct['status']='ACCOUNT_ENTRANT'
        direct.update(risk_tradeoff=risk,owned_repair_cohorts=len(controls_risk))
        output[name]=direct
    return output


def coin_lifecycle(ledger, bars, funding):
    from datetime import date, datetime, timezone
    from types import SimpleNamespace
    # Original recorded primary creation events, not a newly fitted generator.
    creations={e['at_ms']:e for e in ledger['opportunity_ledger'] if e['event']=='opportunity'
               and e.get('identity',0)>0 and e.get('kind')=='impulse'}
    active, close_pairs, op = {}, {}, None
    for stamp,row in sorted(bars.items()):
        end=stamp+f.FOUR
        if op and (end>=op.expires or row[2]<=op.stop or row[1]>=op.take):op=None
        creation=creations.get(end)
        if creation and creation['direction']>0 and stamp-f.FOUR in bars:
            stop=(bars[stamp-f.FOUR][3]+row[3])/2
            op=SimpleNamespace(identity=end,direction=1,stop=stop,take=row[3]*(row[3]/stop)**20,
                               expires=end+42*f.FOUR)
        elif creation:op=None
        active[stamp+f.FOUR]=op
        close_pairs[stamp+f.FOUR]=row[3]
    def eligible(row,at):
        if not row or row['missing_reason']:return False
        age=(datetime.fromtimestamp(at/1000,timezone.utc).date()-date.fromisoformat(row['latest_observation_date'])).days
        return (0<=age<=7 and row['latest_value_available_ms']<at and row['prior20_value_available_ms']<at
                and D(row['latest_value'])<=D(row['prior20_value'])-D('.25'))
    fills = {e['trade']['id']:e for e in ledger['opportunity_ledger'] if e['event']=='fill'}
    trades=sorted(ledger['trades'],key=lambda t:t['time'])
    decisions=[e for e in ledger['opportunity_ledger'] if e['event']=='decision']
    changes={'macro-handoff':[],'macro-restart':[]}
    seen, previous_stop, ix = set(), None, 0
    for e in decisions:
        at=e['at_ms'];identity=e.get('opportunity');trigger=e.get('trigger') or {}
        while ix<len(trades) and trades[ix]['time']<=at:
            t=trades[ix]; record=fills[t['id']]
            if t['side']=='SELL' and record.get('exit_type')=='STOP_MARKET':
                previous_stop=t
            ix+=1
        if not identity or identity>=0 or trigger.get('kind')!='macro':
            continue
        bar=e['bar_ms']; op=active.get(bar)
        name=None
        if e.get('action')=='hold' and D(e['quantity_before'])>0 and op and op.direction>0:
            name='macro-handoff'
        elif (e.get('action')=='consumed' and D(e['quantity_before'])==0 and previous_stop
              and previous_stop['time']>-identity and eligible(trigger['dfii10'],at)
              and bar-2*f.FOUR>=previous_stop['time']
              and all(close_pairs.get(t,D(0))>D(previous_stop['price']) for t in (bar-f.FOUR,bar))):
            name='macro-restart'
        if name is None or (name,identity) in seen:
            continue
        seen.add((name,identity))
        mark=D(e['decision_mark'])
        stop=op.stop if name=='macro-handoff' else min(bars[t][2] for t in sorted(bars) if bar-10*f.DAY<=t<bar)
        take=op.take if name=='macro-handoff' else mark*(mark/stop)**20
        if not 0<stop<mark<take:
            continue
        proxy=proxy_return(bars,at,mark,stop,take,7*f.DAY,funding)
        if proxy:
            changes[name].append(dict(id=identity,time_ms=at,primary_id=op.identity if op else None,
                                     price=mark,**proxy))
    result={}
    for name,events in changes.items():
        eras={era:[x for x in events if (x['time_ms']<f.CUT)==early]
              for era,early in [('early',True),('late',False)]}
        checks=dict(count=len(events)>=10,eras=all(len(v)>=3 for v in eras.values()),
                    positive=bool(events) and sum(x['net_return'] for x in events)>0,
                    both_eras=all(v and sum(x['net_return'] for x in v)>0 for v in eras.values()))
        result[name]=dict(status=status(checks,checks['count'] and checks['eras']),gates=checks,
            events=events,meaning='Schedule-visible owned macro branch census and gross-per-old-budget event proxy; incumbent alternative profit and full rotation costs require paired accounts.',
            rotation_close_cost_unmodeled=name=='macro-handoff')
        # A positive new leg alone cannot prove replacing a profitable old leg.
        if name=='macro-handoff' and result[name]['status']=='ACCOUNT_ENTRANT':
            result[name]['status']='PAIRED_PATH_REQUIRED'
    return result


def new_opportunities(bars,starts,kind,funding):
    result={}
    interval=f.DAY if kind=='spot' else f.FOUR
    daily=f.aggregate(bars,interval) if kind=='coin' else bars
    for name in ('state-trend','state-range'):
        events=[]; last=-1; raw_count=0
        for stamp in sorted(bars):
            if stamp<f.START or stamp>=f.END:
                continue
            candidate=signal(bars,stamp,name,kind)
            if not candidate:
                continue
            raw_count+=1
            at=next((s for s in starts if s>=candidate['available_ms']),f.END)
            if at>=candidate['available_ms']+candidate['life_ms'] or at<last:
                continue
            # Revalidate on the bar actually complete at the unchanged session.
            current=at//interval*interval-interval
            visible=signal(bars,current,name,kind)
            if visible is None:
                continue
            if at//f.DAY*f.DAY not in daily:continue
            mark=f.price_at(daily,at)
            if not visible['stop']<mark<visible['take']:
                continue
            trade=proxy_return(bars,at,mark,visible['stop'],visible['take'],visible['life_ms'],funding)
            if trade:
                events.append(dict(time_ms=at,signal_ms=current,price=mark,**trade))
                last=trade['exit_ms']
        eras={era:[x for x in events if (x['time_ms']<f.CUT)==early]
              for era,early in [('early',True),('late',False)]}
        checks=dict(count=len(events)>=10,eras=all(len(v)>=3 for v in eras.values()),
                    positive=bool(events) and sum(x['net_return'] for x in events)>0,
                    both_eras=all(v and sum(x['net_return'] for x in v)>0 for v in eras.values()))
        result[name]=dict(status=status(checks,checks['count'] and checks['eras']),gates=checks,
            raw_signals=raw_count,independent_schedule_visible_events=len(events),events=events,
            average_net_return=sum((e['net_return'] for e in events),D(0))/len(events) if events else None,
            limitations='Completed-bar proxy, omitted partial entry bar, no wallet/macro competition/depth/native qualification. All historical periods are development data.')
    return result


def joint_admission(accounts,proposal,now,returns,rule='gross-entry-cap',context=None):
    """Read-only proposed new risk. Never transfers, reduces or submits orders."""
    if rule not in ('gross-entry-cap','stress-entry-cap','state-exposure'):
        raise ValueError('unregistered joint rule')
    try:
        if len(accounts)!=2 or {a['kind'] for a in accounts}!={'spot','coin'}:
            raise ValueError('two separately financed accounts required')
        equity=gross=risk=D(0)
        for a in accounts:
            if (a['symbol']!='BTCUSDT' or type(a['receipt_ms']) is not int or a['receipt_ms']>now or now-a['receipt_ms']>60000
                    or a['owned'] is not True or a['protected'] is not True or a['pending'] is not False):
                raise ValueError('unknown/stale ownership or protection')
            e,n,r=(D(a[k]) for k in ('equity_usdt','gross_notional_usdt','stop_risk_usdt'))
            if not all(x.is_finite() for x in (e,n,r)) or e<=0 or n<0 or r<0:
                raise ValueError('invalid separately financed amounts')
            equity+=e;gross+=n;risk+=r
        amount=D(proposal['gross_notional_usdt']); added_risk=D(proposal['stop_risk_usdt'])
        if (proposal['symbol']!='BTCUSDT' or proposal['side']!='BUY' or amount<0 or added_risk<0
                or not amount.is_finite() or not added_risk.is_finite()):
            raise ValueError('invalid new-risk proposal')
        if rule!='gross-entry-cap' and (len(returns)!=20 or any(not D(r).is_finite() for r in returns)):
            raise ValueError('twenty causal completed returns required')
        if rule!='gross-entry-cap':
            if (not context or type(context['completed_through_ms']) is not int
                    or context['completed_through_ms']%f.DAY or context['completed_through_ms']>now
                    or type(context['available_ms']) is not int or context['available_ms']>now
                    or len(context['source_sha256'])!=64):raise ValueError('causal completed risk context required')
        negative=False
        if rule=='state-exposure':
            for a in accounts:
                if type(a['momentum_available_ms']) is not int or a['momentum_available_ms']>now or not D(a['momentum20']).is_finite():
                    raise ValueError('causal direction required for both accounts')
            negative=all(D(a['momentum20'])<0 for a in accounts)
        cap=D(2) if negative else D(4)
        admitted=gross+amount<=cap*equity
        if rule=='stress-entry-cap':
            shock=max(D(0),-min(map(D,returns)))
            admitted &= shock*(gross+amount)+risk+added_risk<=D('.20')*equity
        return dict(status='ADMIT_RESEARCH_PROPOSAL' if admitted else 'BLOCK_NEW_RISK',
                    gross_over_equity=(gross+amount)/equity,rule=rule,orders=0,transfers=0)
    except (KeyError,TypeError,ValueError,ArithmeticError) as error:
        return dict(status='BLOCK_UNKNOWN',reason=str(error),rule=rule,orders=0,transfers=0)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('spot-root','coin-root','warmup','features','schedule','output'):
        p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args(argv)
    if args.output.exists():raise ValueError('preserve existing outputs')
    began=time.monotonic(); inputs=[]
    spot=f.market(args.spot_root,f.DAY,inputs); coin=f.market(args.coin_root,f.FOUR,inputs)
    raw=args.warmup.read_bytes()
    if f.sha(raw)!=f.WARMUP:raise ValueError('warmup changed')
    warm=dict(f.kline(r,3600000) for r in json.loads(raw))
    for h in sorted(warm):
        if h%f.FOUR==0 and all(h+i*3600000 in warm for i in range(4)):
            rows=[warm[h+i*3600000] for i in range(4)]
            coin[h]=(rows[0][0],max(r[1] for r in rows),min(r[2] for r in rows),rows[-1][3],
                     sum(r[4] for r in rows),sum(r[5] for r in rows))
    feature_raw=args.features.read_bytes()
    if f.sha(feature_raw)!='bf920626cc13653b8bbeafd171650cc1a76888e15aad0c20bbd1061fb41da512':raise ValueError('funding source changed')
    funding=[(r['observation_ms'],D(r['value'])) for r in json.loads(feature_raw)['funding']]
    starts=json.loads(args.schedule.read_text())['primary']['starts_ms']
    if f.sha(json.dumps(starts,separators=(',',':')).encode())!=json.loads(SPEC.read_text())['contract']['schedule_sha256']:raise ValueError('schedule changed')
    original=SPEC.parent.parent/'evidence/btc-flow-risk-20261004'
    ledgers={}
    for kind in ('spot','coin'):
        raw=(original/f'{kind}-baseline-projection.json.gz').read_bytes()
        if f.sha(raw)!=f.PROJECTIONS[kind]:raise ValueError('original projection changed')
        ledgers[kind]=json.loads(gzip.decompress(raw))
    old=json.loads((original/'screen-recovery2.json').read_text())
    projects={
        'spot':dict(lifecycle=spot_lifecycle(ledgers['spot'],spot,old['results']['spot']),
                    opportunities=new_opportunities(spot,starts,'spot',[])),
        'coin':dict(lifecycle=coin_lifecycle(ledgers['coin'],coin,funding),
                    opportunities=new_opportunities(coin,starts,'coin',funding))}
    joint_raw=(SPEC.parent.parent/'evidence/btc-continuous-20261004/joint-accepted-projection.json').read_bytes()
    if f.sha(joint_raw)!=c.JOINT_SHA:raise ValueError('joint original changed')
    joint_rows=json.loads(joint_raw)['portfolios']['selected']
    joint=[dict(budgets=r['budgets'],closing_peak=max(x['gross_exposure_over_equity'] for x in r['curve']),
                closing_days_over4=sum(x['gross_exposure_over_equity']>4 for x in r['curve']),
                actual_raw_sha256=r['account_raw_sha256']) for r in joint_rows]
    result=dict(format='btc-persistent-screen-v1',spec_sha256=f.sha(SPEC.read_bytes()),
        source_sha256=f.sha(Path(__file__).read_bytes()),git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        original_bindings={k:r['parent_binding'] for k,r in ledgers.items()},inputs=inputs,
        projects=projects,joint=dict(status='CAUSAL_ADMISSION_IMPLEMENTED_ACCOUNT_PATH_PENDING',rows=joint,
            rules=['gross-entry-cap','stress-entry-cap','state-exposure'],curve_rescaled=False,
            closing_exceedance_is_not_buy_event=True,continuous_joint_mdd=False),
        execution=dict(status='PRIOR_COST_EVIDENCE_REUSED_WAIT_RECORDED_BOOK',
            source='evidence/btc-continuous-20261004/continuous-results-risk-fix1.json',
            action='Finite new public book receipts; no invented missed/maker fills or duplicate IOC account replay.'),
        information=dict(status='WAIT_QUALIFIED_FORWARD_RECEIPTS',families=['oi-deleveraging','option-skew'],
            prior_retrospective_publication_rejection_retained=True),
        forward=dict(status='WAIT_NEW_INTERVAL',frozen_after=f.END,old_ledgers_modified=False),
        wall_seconds=time.monotonic()-began,original795_replays=0,large_vault_scans=0,
        runtime_promoted=False,prospective_alpha_proven=False)
    args.output.write_text(json.dumps(f.serial(result),indent=2)+'\n')
    print(json.dumps({k:{n:v['status'] for group in project.values() for n,v in group.items()} for k,project in projects.items()},indent=2))
    print('elapsed seconds',result['wall_seconds'])


if __name__=='__main__':main()
