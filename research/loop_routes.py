"""Successive BTC mechanisms: qualify, screen, retain failures, admit accounts."""
import argparse
from datetime import datetime,timezone
from decimal import Decimal as D
import gzip
import json
from pathlib import Path
import time

from research import nine_routes as r, nine_alpha, persistent_data, flow_risk as f
from research import loop_alpha as alpha, loop_risk as risk, loop_data as data
from research.continuous_routes import solve

SPEC=data.SPEC


def signal(bars,coin,stamp,*,inverse=False):
    through=(stamp-60000)//r.DAY*r.DAY;days=(through-2*r.DAY,through-r.DAY)
    if not all(t in bars and t in coin and t-r.DAY in bars for t in days):return None
    rows=[]
    for day in days:
        s,p=bars[day],coin[day]
        rows.append((2*s[5]/s[4]-1,2*p[5]/p[4]-1,s[3]/bars[day-r.DAY][3]-1,s[3]/p[3]-1))
    return (all(si<D('-.10') and pi>=0 and ret<0 and basis>=0 for si,pi,ret,basis in rows) if inverse
            else all(si>D('.10') and pi<=0 and ret>0 and basis<=0 for si,pi,ret,basis in rows))


def residual(events):
    if len(events)<=4 or len({x['signal'] for x in events})<2:return None
    xs=[[1.0,float(e['signal']),float(e['momentum']),float(e['rms'])] for e in events];ys=[float(e['net']) for e in events]
    try:return solve([[sum(x[i]*x[j] for x in xs) for j in range(4)] for i in range(4)],
                     [sum(x[i]*y for x,y in zip(xs,ys)) for i in range(4)])[1]
    except ValueError:return None


def opportunity_gate(events,total):
    eligible=[];through=-1
    for e in sorted(events,key=lambda row:row['at_ms']):
        if e['at_ms']>through:eligible.append(e);through=e['end_ms']
    eras=[[e for e in eligible if (e['at_ms']<f.CUT)==early] for early in (True,False)]
    hits=[[e for e in part if e['signal']] for part in eras];coefficients=[residual(part) for part in eras]
    gates=dict(coverage=D(len(events))/total>=D('.9') if total else False,
        count=sum(len(rows) for rows in hits)>=10,each_era=all(len(rows)>=3 for rows in hits),
        net=all(rows and sum(e['net'] for e in rows)>0 for rows in hits),
        incremental=all(c is not None and c>0 for c in coefficients))
    enough=gates['count'] and gates['each_era'] and gates['coverage'] and all(c is not None for c in coefficients)
    return dict(status='ACCOUNT_ENTRANT' if all(gates.values()) else 'REJECT_MECHANISM' if enough else 'SUPPORT_PENDING',
        account_entrant=all(gates.values()),gates=gates,signals=sum(len(rows) for rows in hits),
        independent_periods=len(eligible),residual_coefficients=coefficients,
        selected_events=[e for rows in hits for e in rows],events=events,prospective_alpha_proven=False,
        meaning='Completed seven-day price/declared-cost opportunity proxy, not account economics; all original history already development.')


def discovery(bars,coin,starts,source_sha):
    output={}
    for kind in ('spot','coin'):
        events=[];total=0;cost=D('.003' if kind=='spot' else '.0037')
        for stamp in starts:
            flag=signal(bars,coin,stamp);ctx=alpha.context(bars,stamp,source_sha)
            if flag is None or ctx is None:continue
            total+=1;entry_day=stamp//r.DAY;end_day=entry_day+7*r.DAY
            if end_day+r.DAY>f.END or entry_day not in bars or end_day not in bars:continue
            # Entry uses the actual known completed close, never forming-day OHLC.
            entry=bars[ctx['completed_through_ms']-r.DAY][3]
            events.append(dict(id=str(stamp),at_ms=stamp,end_ms=end_day+r.DAY,signal=flag,
                net=bars[end_day][3]/entry-1-cost,momentum=ctx['prior_momentum'],rms=ctx['prior_rms']))
        result=opportunity_gate(events,total);result.update(kind=kind,family='spot-price-discovery',expression=0,
            available_ms_rule='Two completed days plus60sec, original session only',failure_next='post-announcement-repair')
        output[kind]=result
    return output


def discovery_filter(pairs,bars,coin,source_sha,now):
    output={}
    for kind in ('spot','coin'):
        rows=[];eligible=0;pending={}
        for pair in pairs:
            if pair['scenario']!='baseline':continue
            account=pair['accounts'][kind];baskets=alpha.spot_baskets(account) if kind=='spot' else alpha.coin_baskets(account)
            seen=set()
            for event in pair['proposal_ledger']:
                p=event['proposal'];stamp=p['at_ms']
                if p['kind']!=kind or p['id'] in seen:continue
                snapshot=next(a for a in event['accounts'] if a['kind']==kind)
                if not snapshot['owned'] or not snapshot['protected'] or snapshot['pending'] or not p['feasible']:continue
                seen.add(p['id']);eligible+=1
                ctx=alpha.context(bars,stamp,source_sha);flag=signal(bars,coin,stamp,inverse=True)
                matches=[b for b in baskets if 0<=b['at_ms']-stamp<=15000 and b['closed'] and b['settled_ms']<=now]
                if ctx is None or flag is None or len(matches)!=1:
                    pending['WAIT_ACTUAL_MATURE_CONTEXT']=pending.get('WAIT_ACTUAL_MATURE_CONTEXT',0)+1;continue
                b=matches[0];begin=(b['at_ms']//r.DAY-1)*r.DAY;end=(b['settled_ms']//r.DAY-1)*r.DAY
                macro=(event.get('context') or {}).get('dfii10')
                if kind=='coin' and (not macro or macro['available_ms']>stamp):
                    pending['WAIT_ACTUAL_CAUSAL_DFII10']=pending.get('WAIT_ACTUAL_CAUSAL_DFII10',0)+1;continue
                if begin not in bars or end not in bars:continue
                row=dict(b,selected=flag,factor=D('.75') if flag else D(1),market_return=bars[end][3]/bars[begin][3]-1,
                    prior_momentum=ctx['prior_momentum'],prior_rms=ctx['prior_rms'])
                if kind=='coin':row['dfii10']=r.number(macro['value'])
                rows.append(row)
        result=alpha.information(rows,eligible,kind);result.update(kind=kind,family='spot-price-discovery',expression=1,
            pending=pending,events=rows,failure_next='post-announcement-repair')
        output[kind]=result
    return output


def macro_events(calendar,bars,starts,source_sha,now):
    events=[];known=calendar['events'];total=0
    for release in known:
        if release['known_ms']>=release['at_ms']:raise ValueError('event was not known before release')
        calls=[t for t in starts if release['at_ms']+r.DAY<=t<=release['at_ms']+7*r.DAY]
        if not calls:continue
        stamp=min(calls);ctx=alpha.context(bars,stamp,source_sha)
        day=release['at_ms']//r.DAY*r.DAY;completed=(stamp//r.DAY-1)*r.DAY;end=stamp//r.DAY*r.DAY+7*r.DAY
        if ctx is None or day not in bars or completed not in bars:continue
        total+=1
        if end+r.DAY>now or end not in bars:continue
        flag=bars[day][3]/bars[day][0]-1<=D('-.02') and bars[completed][3]>=bars[day][0]
        events.append(dict(id=str(release['at_ms']),at_ms=stamp,end_ms=end+r.DAY,signal=flag,
            net=bars[end][3]/bars[completed][3]-1-D('.0037'),momentum=ctx['prior_momentum'],rms=ctx['prior_rms']))
    result=opportunity_gate(events,total);result.update(calendar_status=calendar['status'],known_releases=len(known),
        status='WAIT_KNOWN_EVENT_AND_MATURE_BTC' if not events else result['status'],failure_next='session-bounded-execution')
    return result


def execution(pairs,public):
    parsed=persistent_data.qualify(public);books={row['name']:row for row in parsed['parsed'] if row['name'].endswith('-book')}
    campaigns=[]
    for pair in pairs:
        if pair['scenario']!='baseline':continue
        account=pair['accounts']['coin'];seen=set()
        for event in pair['proposal_ledger']:
            p=event['proposal']
            if p['kind']!='coin' or p['id'] in seen:continue
            seen.add(p['id']);ends=[s['ended_ms'] for s in account['sessions'] if s['start_ms']<=p['at_ms']<=s['ended_ms']]
            if not ends:continue
            fills=[t for t in account['trades'] if p['at_ms']<=t['time']<=min(ends) and t['side']=='BUY']
            campaigns.append(dict(id=p['id'],decision_ms=p['at_ms'],buy_fills=len(fills),filled_btc=str(sum((D(t['qty']) for t in fills),D(0))),
                requested_notional_usdt=p['gross_notional_usdt'],exact_ioc_orders_unknown=True))
    return dict(status='WAIT_EXECUTION_EVIDENCE',account_entrant=False,campaigns=campaigns,
        received_books=books,queue_proven=False,valid_historical_book_pairs=0,
        existing_fragment_commission_saving='0',native_orders=0,
        failure_next='New source or recorded execution mechanism; no candle-touch maker fills.')


def brake(pairs):
    rows=[];pending=0;state_by_window={}
    for pair in pairs:
        if pair['scenario']!='baseline':continue
        state=None;daily=risk.closes(pair);seen=set();cohorts=alpha.coin_baskets(pair['accounts']['coin'])
        for event in pair['proposal_ledger']:
            p=event['proposal'];stamp=p['at_ms']
            if p['kind']!='coin' or p['id'] in seen:continue
            seen.add(p['id'])
            try:state=risk.brake_state(state,[d for d in daily if d['at_ms']<=stamp],event['accounts'],stamp)
            except ValueError:pending+=1;continue
            account=next(a for a in event['accounts'] if a['kind']=='coin');plan=risk.brake_plan(state,account)
            matches=[c for c in cohorts if 0<=c['at_ms']-stamp<=15000 and c['closed']]
            if len(matches)!=1:pending+=1;continue
            c=matches[0];rows.append(dict(id=p['id'],at_ms=stamp,settled_ms=c['settled_ms'],closed=True,
                gain=c['gain'],notional=c['notional'],selected=state['braking'],factor=D('.5') if state['braking'] else D(1),
                plan=plan,drawdown=state['drawdown']))
        state_by_window[str(pair['window'][0])]=state
    independent=alpha.nonoverlapping(rows);hits=[row for row in independent if row['selected']]
    effects=[sum((-row['gain']*D('.5') for row in hits if (row['at_ms']<f.CUT)==early),D(0)) for early in (True,False)]
    controls=[-D('.25')*sum((row['gain'] for row in independent if (row['at_ms']<f.CUT)==early),D(0)) for early in (True,False)]
    gates=dict(count=len(hits)>=10,each_era=all(sum((row['at_ms']<f.CUT)==early for row in hits)>=3 for early in (True,False)),
        net=all(v>0 for v in effects),beats_uniform=all(a>b for a,b in zip(effects,controls)))
    enough=gates['count'] and gates['each_era']
    return dict(status='ACCOUNT_ENTRANT' if all(gates.values()) else 'REJECT_MECHANISM' if enough else 'SUPPORT_PENDING',
        account_entrant=all(gates.values()),gates=gates,independent_commitments=len(independent),affected=len(hits),
        unqualified_or_unsettled=pending,rows=rows,states=state_by_window,
        avoided_cash_halves=list(map(str,effects)),uniform25_cash_halves=list(map(str,controls)),
        held_action_support='WAIT_CONFIRMED_HISTORICAL_HELD_SNAPSHOTS',failure_next='implied-risk-budget',
        actual_candidate_wallet=False,offline_joint_executor=False)


def implied(history,bars,source_sha,now):
    daily={};pending=[]
    for packet in history:
        parsed=[x for x in packet['parsed'] if x.get('term')==30 and x['status']=='FORWARD_RESEARCH_OBSERVATION']
        if len(parsed)!=2:continue
        stamp=max(x['available_ms'] for x in parsed);iv=sum(D(x['iv']) for x in parsed)/2;day=stamp//r.DAY
        if stamp>now:continue
        if day not in daily or stamp<daily[day][0]:daily[day]=stamp,iv
    matured=[];through=-1
    for stamp,iv in sorted(daily.values()):
        ctx=alpha.context(bars,stamp,source_sha);begin=(stamp//r.DAY+1)*r.DAY;end=begin+7*r.DAY
        if ctx is None or ctx['completed_through_ms']<stamp//r.DAY*r.DAY:
            pending.append(dict(status='WAIT_FRESH_COMPLETED_BTC',at_ms=stamp,iv=str(iv)));continue
        keys=list(range(begin-r.DAY,end,r.DAY))
        if end>now or not all(t in bars for t in keys):
            pending.append(dict(status='WAIT_REALIZED_SEVEN_DAY_PERIOD',at_ms=stamp,iv=str(iv)));continue
        if begin<=through:continue
        through=end
        returns=[bars[b][3]/bars[a][3]-1 for a,b in zip(keys,keys[1:])]
        realized=(sum(v*v for v in returns)/7).sqrt()*D('365.25').sqrt();old=ctx['prior_rms']*D('365.25').sqrt()
        matured.append(dict(at_ms=stamp,end_ms=end,iv=iv,realized=realized,implied_error=(iv-realized)**2,
            historical_error=(old-realized)**2,factor=risk.implied_factor(iv,ctx['prior_rms'],stamp,stamp)))
    half=len(matured)//2;parts=[matured[:half],matured[half:]]
    gains=[sum((e['historical_error']-e['implied_error'] for e in part),D(0)) for part in parts]
    gates=dict(count=len(matured)>=10,each_half=all(len(p)>=3 for p in parts),incremental=all(g>0 for g in gains))
    enough=gates['count'] and gates['each_half'];passed=all(gates.values())
    return dict(status='ACCOUNT_ENTRANT' if passed else 'REJECT_IMPLIED_PREDICTOR' if enough else 'SUPPORT_PENDING',
        account_entrant=passed,gates=gates,real_receipt_days=len(daily),periods=len(matured),
        error_improvement_halves=list(map(str,gains)),events=matured,pending=pending,directional_alpha=False,
        failure_next='joint-protection-liquidity',runtime_promoted=False)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('joint','spot-market','coin-market','fx','schedule','cache','public','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--receipt-history',type=Path,nargs='*',default=[])
    p.add_argument('--inherited',type=Path,nargs='*',default=[]);p.add_argument('--etf',type=Path)
    p.add_argument('--at-ms',type=int,required=True);args=p.parse_args(argv)
    if args.out.exists():raise ValueError('preserve prior evidence')
    if args.at_ms>int(time.time()*1000):raise ValueError('future economic observation time')
    identity=data.source();spec=json.loads(SPEC.read_text());began=time.monotonic()
    schedule=json.loads(args.schedule.read_text());starts=schedule['primary']['starts_ms']
    if r.sha(json.dumps(starts,separators=(',',':')).encode())!=spec['contract']['schedule_sha256']:raise ValueError('original starts changed')
    markets,cache_receipt=data.market_cache(args.spot_market,args.coin_market,args.cache)
    bars=markets['spot'];coin=f.aggregate(markets['coin4'],f.FOUR);market_sha=r.sha(json.dumps(cache_receipt['inputs'],sort_keys=True).encode())
    book=nine_alpha.FeatureBook(args.receipt_history,args.inherited,args.etf)
    pairs=[];bindings=[]
    for item in spec['accepted_joint_inputs']:
        path=args.joint/item['file'];raw=path.read_bytes()
        if r.sha(raw)!=item['sha256']:raise ValueError('original accepted wallet changed')
        pair=json.loads(gzip.decompress(raw));pairs.append(pair);bindings.append(dict(item,sources={k:a['source'] for k,a in pair['accounts'].items()}))
    evaluated={}
    for pair in pairs:
        if pair['scenario']=='baseline':evaluated[str(pair['window'][0])]=alpha.evaluate(book,pair,bars,market_sha,args.at_ms)
    risks=[];spot_minutes,spot_bindings=data.spot_minutes(args.public)
    if 'spot' in str(Path(__file__).resolve().parents[1].name):
        from research.complete_spot import PriorFX
    else:
        from research.unified_perp import PriorFX
    fx=PriorFX(args.fx)
    for pair,binding in zip(pairs,bindings):
        result=risk.joint_risk(pair,bars,markets['mark'],fx)
        result.update(window=pair['window'],scenario=pair['scenario'],binding=binding,
            received_spot_price_sensitivity=risk.price_revaluation(pair,bars,spot_minutes,markets['mark'],fx))
        risks.append(result)
    try:calendar=data.calendar(args.public)
    except (ValueError,KeyError,TypeError):calendar=dict(status='DATA_NOT_QUALIFIED',events=[])
    pending_books=args.inherited[0] if args.inherited else None
    if pending_books is None:raise ValueError('original actual option/book receipt required')
    strategies=dict(existing_alpha=evaluated,price_discovery=discovery(bars,coin,starts,market_sha),
        price_discovery_filter=discovery_filter(pairs,bars,coin,market_sha,args.at_ms),
        announcement=macro_events(calendar,bars,starts,market_sha,args.at_ms),execution=execution(pairs,pending_books),
        drawdown_brake=brake(pairs),implied_risk=implied(book.persistent,bars,market_sha,args.at_ms),
        protection=dict(status='WAIT_CONFIRMED_NATIVE_STOPS_AND_DEPTH',account_entrant=False,
            existing_gap='.10',existing_funding_reserve='.01',no_new_uncovered_gap_proven=True,orders=0))
    result=dict(format='btc-decision-loop-screen-v1',source=identity,spec_sha256=r.sha(SPEC.read_bytes()),
        original_inputs=bindings,market_cache=cache_receipt,feature_book_sha256=book.sha256,
        spot_minute_bindings=spot_bindings,
        at_ms=args.at_ms,routes=strategies,joint_risk=risks,calendar=calendar,
        original795_replays=0,new_accounts=0,new_sessions=0,large_vault_scans=0,
        native_qualified=False,default_promoted=False,elapsed_wall_seconds=time.monotonic()-began)
    args.out.parent.mkdir(parents=True,exist_ok=True);data.new_json(args.out,result)
    print(json.dumps(dict(out=str(args.out),wall_seconds=result['elapsed_wall_seconds'],
        alpha_discovery={k:v['status'] for k,v in strategies['price_discovery'].items()},
        beta={k:strategies[k]['status'] for k in ('drawdown_brake','implied_risk','protection')},new_accounts=0)))


if __name__=='__main__':main()
