"""Mature actual owned cash baskets into information and account decisions.

Attribution is a cheap screen. It never fabricates the candidate wallet,
resizes equity curves, or promotes a default.
"""
from collections import defaultdict, deque
from decimal import Decimal as D
import json
from pathlib import Path
import argparse
import gzip
import time

from research import nine_routes as r, continuous_routes as prior

SPEC=Path(__file__).with_name('loop-spec.json')


def spot_baskets(account):
    owners={str(json.loads(row[3])['orderId']):json.loads(row[1])
            for row in account['allocations'] if 'orderId' in json.loads(row[3])}
    books=defaultdict(deque);cohorts={}
    for fill in sorted(account['fills'],key=lambda row:(row['time'],row['id'])):
        q,quote,fee=map(r.number,(fill['qty'],fill['quote'],fill['commission']))
        if q<=0 or quote<=0 or fee<0 or fill['commission_asset'] not in ('BTC','USDT'):
            raise ValueError('invalid actual fill amount or commission asset')
        payload=owners[str(fill['order_id'])];weights={int(w):r.number(v,nonnegative=True) for w,v in payload['weights'].items()}
        total=sum(weights.values())
        if total<=0:raise ValueError('unknown sleeve allocation')
        if fill['buyer']:
            quantity=q-(fee if fill['commission_asset']=='BTC' else D(0))
            cost=quote+(fee if fill['commission_asset']=='USDT' else D(0))
            key=str(fill['order_id'])
            if key not in cohorts:cohorts[key]=dict(id=key,at_ms=fill['time'],quantity=D(0),cost=D(0),left=D(0),proceeds=D(0),settled_ms=None)
            cohort=cohorts[key];cohort['quantity']+=quantity;cohort['left']+=quantity;cohort['cost']+=cost
            for sleeve,weight in weights.items():
                if weight:books[sleeve].append(dict(cohort=cohort,left=quantity*weight/total))
        else:
            quantity=q+(fee if fill['commission_asset']=='BTC' else D(0))
            proceeds=quote-(fee if fill['commission_asset']=='USDT' else D(0))
            for sleeve,weight in weights.items():
                left=quantity*weight/total
                while left>D('1e-24'):
                    if not books[sleeve]:raise ValueError('sale exceeds this sleeve owned quantity')
                    lot=books[sleeve][0];take=min(left,lot['left']);cohort=lot['cohort']
                    cohort['left']-=take;cohort['proceeds']+=proceeds*take/quantity;cohort['settled_ms']=fill['time']
                    lot['left']-=take;left-=take
                    if lot['left']<=D('1e-24'):books[sleeve].popleft()
    for row in cohorts.values():
        sold=row['quantity']-row['left'];row['closed']=sold>=row['quantity']*D('.999')
        row['notional']=row['cost']*sold/row['quantity'];row['gain']=row['proceeds']-row['notional']
        row['residue_btc']=row['left']
    return list(cohorts.values())


def coin_baskets(account):
    rows=[];quantity=D(0);current=None
    for fill in sorted(account['trades'],key=lambda row:(row['time'],row['id'])):
        amount,price=map(r.number,(fill['qty'],fill['price']))
        if amount<=0 or price<=0 or fill['side'] not in ('BUY','SELL'):raise ValueError('invalid actual Coin fill')
        if fill['side']=='BUY':
            if not quantity:
                current=dict(id=str(fill['orderId']),at_ms=fill['time'],notional=D(0),quantity=D(0),closed=False,settled_ms=None);rows.append(current)
            current['notional']+=amount*price;current['quantity']+=amount;quantity+=amount
        else:
            if current is None or amount>quantity:raise ValueError('unowned Coin reduction')
            quantity-=amount
            if not quantity:current.update(closed=True,settled_ms=fill['time'])
    for a,b in zip(rows,rows[1:]):
        if a['settled_ms'] is None or a['settled_ms']>=b['at_ms']:
            raise ValueError('ambiguous overlapping campaign income boundary')
    for row in rows:
        end=row['settled_ms']
        row['gain']=sum((r.number(x['income']) for x in account['funding_ledger']
                         if end is not None and row['at_ms']<=x['time']<=end
                         and x['incomeType'] in ('REALIZED_PNL','COMMISSION','FUNDING_FEE')),D(0))
        row['residue_btc']=quantity if row is current and not row['closed'] else D(0)
    return rows


def nonoverlapping(rows):
    selected=[];through=-1
    for row in sorted(rows,key=lambda x:(x['at_ms'],str(x['id']))):
        if row['closed'] and row['at_ms']>through:
            selected.append(row);through=row['settled_ms']
    return selected


def fitted(rows,kind):
    columns=['selected','market_return','prior_momentum','prior_rms']+(['dfii10'] if kind=='coin' else [])
    if len(rows)<=len(columns)+1 or len({row['selected'] for row in rows})!=2:
        return dict(identifiable=False,count=len(rows),signal_coefficient=None)
    xs=[[1.0,*[float(row[col]) for col in columns]] for row in rows]
    ys=[float(row['gain']/row['notional']) for row in rows];width=len(xs[0])
    try:coefficients=prior.solve([[sum(x[i]*x[j] for x in xs) for j in range(width)] for i in range(width)],
                                 [sum(x[i]*y for x,y in zip(xs,ys)) for i in range(width)])
    except ValueError:return dict(identifiable=False,count=len(rows),signal_coefficient=None)
    return dict(identifiable=True,count=len(rows),signal_coefficient=coefficients[1],columns=['intercept',*columns],
                coefficients=coefficients,prospective_alpha_proven=False)


def information(rows,total,kind,*,primary=False):
    """An actual account entrant can be true, only after mature economics."""
    eligible=nonoverlapping(rows);split=len(eligible)//2;halves=[eligible[:split],eligible[split:]]
    selected=[row for row in eligible if row['selected']]
    fits=[fitted(part,kind) for part in halves]
    effects=[sum(((row['gain']-row['benchmark_cash']) if primary else -row['gain']*(1-row['factor'])
                  for row in part if row['selected']),D(0)) for part in halves]
    uniform=[D(0) if primary else -D('.25')*sum((row['gain'] for row in part),D(0)) for part in halves]
    gates=dict(coverage=D(len(rows))/total>=D('.9') if total else False,
               count=len(selected)>=10,each_half=all(sum(row['selected'] for row in part)>=3 for part in halves),
               information=all(fit['identifiable'] and (fit['signal_coefficient']>0 if primary else fit['signal_coefficient']<0) for fit in fits),
               net_effect=all(value>0 for value in effects),beats_simple=all(a>b for a,b in zip(effects,uniform)))
    support=gates['coverage'] and gates['count'] and gates['each_half'] and all(f['identifiable'] for f in fits)
    passed=all(gates.values())
    return dict(status='ACCOUNT_ENTRANT' if passed else 'REJECT_INFORMATION_OR_EXPRESSION' if support else 'SUPPORT_PENDING',
        account_entrant=passed,gates=gates,eligible=total,matured=len(rows),independent=len(eligible),affected=len(selected),
        half_fits=fits,avoided_cash_halves=list(map(str,effects)),uniform25_cash_halves=list(map(str,uniform)),
        account_required=passed,account_measured=False,default_adopted=False,
        meaning='Actual owned settled basket attribution. No reinvestment/candidate wallet proof; a pass admits bounded real accounts only.')


def context(bars,stamp,source_sha):
    through=(stamp-60000)//r.DAY*r.DAY
    keys=list(range(through-21*r.DAY,through,r.DAY))
    if not all(key in bars for key in keys):return None
    closes=[bars[key][3] for key in keys];returns=[b/a-1 for a,b in zip(closes,closes[1:])]
    last=bars[keys[-1]]
    return dict(completed_through_ms=through,available_ms=through+60000,source_sha256=source_sha,
        returns20=list(map(str,returns)),prior_momentum=closes[-1]/closes[0]-1,
        prior_rms=(sum(v*v for v in returns)/20).sqrt(),
        spot_quote_turnover_by_day={str(t):str(bars[t][4]) for t in keys},usd_usdt_basis_assumption='declared-parity-proxy',
        persistent_context=dict(completed_day_ms=keys[-1],available_ms=through+60000,source_sha256=source_sha,
            day_return=str(returns[-1]),spot_taker_imbalance=str(2*last[5]/last[4]-1)))


def evaluate(book,pair,bars,source_sha,now):
    output={};proposals=pair['proposal_ledger']
    for kind,account in pair['accounts'].items():
        if not account['finished'] or not account['audit']['passed']:raise ValueError('complete audited actual account required')
        baskets=spot_baskets(account) if kind=='spot' else coin_baskets(account)
        families=('etf-demand','option-insurance','old-coin-supply') if kind=='spot' else ('oi-deleveraging','option-insurance','dollar-financing')
        opportunities=[];seen=set()
        for event in proposals:
            p=event['proposal']
            if p['kind']!=kind or p['id'] in seen:continue
            snapshot=next(a for a in event['accounts'] if a['kind']==kind)
            if not (snapshot['owned'] and snapshot['protected'] and not snapshot['pending'] and p['feasible']):continue
            seen.add(p['id']);opportunities.append(event)
        for family in families:
            for expression in (0,1):
                rows=[];pending={};eligible=0
                for event in opportunities:
                    p=event['proposal'];stamp=p['at_ms'];ctx=context(bars,stamp,source_sha)
                    if ctx is None:pending['WAIT_CAUSAL_MARKET']=pending.get('WAIT_CAUSAL_MARKET',0)+1;continue
                    feature=book.at(family,stamp,ctx)
                    if feature['status']!='FEATURE_READY':pending[feature['status']]=pending.get(feature['status'],0)+1;continue
                    effect=r.alpha_expression(family,expression,feature,p)
                    if family=='oi-deleveraging' and expression==0:
                        # Idle new signals need their actual protected-session journal.
                        # Ordinary historical BUYs are never relabelled as new OI trades.
                        pending['WAIT_ACTUAL_NEW_PRIMARY_JOURNAL']=pending.get('WAIT_ACTUAL_NEW_PRIMARY_JOURNAL',0)+1;continue
                    matches=[b for b in baskets if 0<=b['at_ms']-stamp<=15000]
                    if len(matches)!=1:pending['WAIT_ACTUAL_OWNED_FILL']=pending.get('WAIT_ACTUAL_OWNED_FILL',0)+1;continue
                    eligible+=1;b=matches[0]
                    if not b['closed'] or b['settled_ms']>now:continue
                    begin=(b['at_ms']//r.DAY-1)*r.DAY;end=(b['settled_ms']//r.DAY-1)*r.DAY
                    if begin not in bars or end not in bars:continue
                    macro=(event.get('context') or {}).get('dfii10')
                    if kind=='coin' and (not macro or macro['available_ms']>stamp):
                        pending['WAIT_ACTUAL_CAUSAL_DFII10']=pending.get('WAIT_ACTUAL_CAUSAL_DFII10',0)+1;continue
                    row=dict(b,selected=effect.get('factor') is not None and D(effect['factor'])<1,
                        factor=D(effect['factor'] or 1),market_return=bars[end][3]/bars[begin][3]-1,
                        prior_momentum=ctx['prior_momentum'],prior_rms=ctx['prior_rms'])
                    if kind=='coin':row['dfii10']=r.number(macro['value'])
                    rows.append(row)
                result=information(rows,eligible,kind);result.update(kind=kind,family=family,expression=expression,pending=pending,
                    feature_book_sha256=book.sha256,spec_sha256=r.sha(SPEC.read_bytes()),events=r.serial(rows),
                    failure_route=r.failure_route('REJECT_INFORMATION' if result['status'].startswith('REJECT') else result['status']))
                if pending and not rows:result['status']='WAIT_QUALIFIED_DATA_OR_MATURE_OUTCOME'
                output[f'{kind}:{family}:{expression}']=result
        if kind=='coin' and account.get('opportunity_ledger'):
            output['coin:oi-deleveraging:0']=primary_evaluation(book,account,baskets,bars,source_sha,now)
    return output


def verify_account_packet(pair,now):
    """Check an explicit future input; a hash/audit flag alone proves no money."""
    if pair.get('format')!='btc-nine-joint-account-v1' or set(pair['accounts'])!={'spot','coin'}:
        raise ValueError('actual independent paired account packet required')
    begin,end=pair['window']
    if not 0<=begin<end<=now or pair.get('transfers')!=0:raise ValueError('future/unfunded account period')
    from research.loop_risk import Wallets
    for kind,a in pair['accounts'].items():
        if a['kind']!=kind or D(a['initial_cny'])!=5000 or not a['finished'] or not a['audit']['passed']:
            raise ValueError('finished independently funded original-size account required')
        if not a['source'].get('git_head') or a['source'].get('dirty'):raise ValueError('original frozen producer required')
        ids=set()
        for fill in a['fills' if kind=='spot' else 'trades']:
            if fill['id'] in ids or not begin<=fill['time']<=end:raise ValueError('duplicate or out-of-window fill')
            ids.add(fill['id'])
        if any(not s['archive_or_backup_verified'] or s['execution_unresolved'] for s in a['sessions']):
            raise ValueError('archive/cleanup support absent')
        if kind=='coin':
            income_ids=set()
            for row in a['funding_ledger']:
                if row['tranId'] in income_ids or row['incomeType'] not in ('COMMISSION','REALIZED_PNL','FUNDING_FEE') or not begin<=row['time']<=end:
                    raise ValueError('duplicate/foreign income or implicit transfer')
                income_ids.add(row['tranId'])
    wallet=Wallets(pair);wallet.advance(end);a=pair['accounts']
    residual=[wallet.spot_cash-D(a['spot']['cash_usdt']),wallet.spot_q-D(a['spot']['btc']),
        wallet.coin_q-D(a['coin']['position']),
        wallet.coin_cash+wallet.coin_q*(D(a['coin']['final_mark'])-wallet.entry)-D(a['coin']['final_usdt'])]
    if any(abs(v)>D('1e-8') for v in residual):raise ValueError('account does not reconcile to actual fills and income')
    for a in pair['accounts'].values():
        snap=a['final_snapshot'];computed=D(a['final_usdt'])*D(snap['fx'])*D('.999')
        if abs(computed-D(a['final_cny']))>D('1e-8') or abs(D(snap['equity_usdt'])-D(a['final_usdt']))>D('1e-8'):
            raise ValueError('final FX/equity does not reconcile')
    if abs(sum((D(a['final_cny']) for a in pair['accounts'].values()),D(0))-D(pair['final_cny']))>D('1e-8'):
        raise ValueError('joint final wealth does not reconcile')


def main(argv=None):
    """Evaluate later mature account periods without backfilling the old window."""
    from research import loop_data as data, nine_alpha
    p=argparse.ArgumentParser(description=main.__doc__)
    for name in ('manifest','spot-market','coin-market','cache','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--history',type=Path,nargs='*',default=[]);p.add_argument('--inherited',type=Path,nargs='*',default=[])
    p.add_argument('--etf',type=Path);p.add_argument('--at-ms',type=int,required=True);args=p.parse_args(argv)
    if args.at_ms>int(time.time()*1000):raise ValueError('future economic observation time')
    identity=data.source();manifest_raw=args.manifest.read_bytes();manifest=json.loads(manifest_raw)
    if manifest['spec_sha256']!=r.sha(SPEC.read_bytes()):raise ValueError('foreign evaluation contract')
    if len(manifest['accounts'])>12:raise ValueError('bounded paired account inventory exceeded')
    markets,receipt=data.market_cache(args.spot_market,args.coin_market,args.cache)
    book=nine_alpha.FeatureBook(args.history,args.inherited,args.etf);outputs=[]
    market_sha=r.sha(json.dumps(receipt['inputs'],sort_keys=True).encode())
    for item in manifest['accounts']:
        path=args.manifest.parent/item['file'];raw=path.read_bytes()
        if r.sha(raw)!=item['sha256']:raise ValueError('actual input bytes changed')
        pair=json.loads(gzip.decompress(raw));verify_account_packet(pair,args.at_ms)
        outputs.append(dict(input=item,window=pair['window'],original_sources={k:a['source'] for k,a in pair['accounts'].items()},
            evaluation=evaluate(book,pair,markets['spot'],market_sha,args.at_ms)))
    data.new_json(args.out,dict(format='btc-loop-mature-alpha-v1',source=identity,at_ms=args.at_ms,
        input_manifest_sha256=r.sha(manifest_raw),spec_sha256=r.sha(SPEC.read_bytes()),market_cache=receipt,
        feature_book_sha256=book.sha256,rows=outputs,new_accounts=0,orders=0,default_adopted=False))
    print(json.dumps(dict(out=str(args.out),paired_periods=len(outputs),orders=0)))


def primary_evaluation(book,account,baskets,bars,source_sha,now):
    rows=[];eligible=0;pending=0;seen=set()
    for event in account['opportunity_ledger']:
        if event.get('event')!='decision' or event.get('action')!='enter' or event.get('opportunity') in seen:continue
        seen.add(event['opportunity']);stamp=event['at_ms'];ctx=context(bars,stamp,source_sha)
        if ctx is None:pending+=1;continue
        feature=book.at('oi-deleveraging',stamp,ctx)
        trigger=event.get('trigger') or {};selected=trigger.get('signal_family')=='oi-deleveraging'
        if selected and (feature['status']!='FEATURE_READY' or not feature['release']):
            pending+=1;continue
        matches=[b for b in baskets if 0<=b['at_ms']-stamp<=15000]
        if len(matches)!=1:pending+=1;continue
        eligible+=1;b=matches[0]
        macro=event.get('causal_dfii10')
        if not b['closed'] or b['settled_ms']>now or not macro or macro['available_ms']>stamp:continue
        begin=(b['at_ms']//r.DAY-1)*r.DAY;end=(b['settled_ms']//r.DAY-1)*r.DAY
        if begin not in bars or end not in bars:continue
        market=bars[end][3]/bars[begin][3]-1
        rows.append(dict(b,selected=selected,factor=D(1),market_return=market,
            benchmark_cash=b['notional']*(market-D('.0037')),prior_momentum=ctx['prior_momentum'],
            prior_rms=ctx['prior_rms'],dfii10=r.number(macro['value'])))
    result=information(rows,eligible,'coin',primary=True)
    result.update(kind='coin',family='oi-deleveraging',expression=0,pending_journals_or_controls=pending,
                  feature_book_sha256=book.sha256,events=r.serial(rows),spec_sha256=r.sha(SPEC.read_bytes()),
                  benchmark='Same actual interval and notional BTC long minus registered costs; attribution only, actual idle baseline still required.')
    return result


if __name__=='__main__':main()
