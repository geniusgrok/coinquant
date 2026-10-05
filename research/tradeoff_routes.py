"""Finite research expressions for new BTC information; never sends orders.

Caller contexts are not authenticated account state. A proposal is not an
account entrant: mature controls and actual shared-runtime evidence are still
required. Missing observations, ownership or maturity stay explicit.
"""
import argparse
import json
from pathlib import Path
from research.replacement_routes import DAY, absorption, causal, expiry_basis, number, option_risk


def owned_reduction(account, now, factor):
    if account is None:
        return dict(status='WAIT_OWNERSHIP',orders=0)
    if (account.get('symbol')!='BTCUSDT' or account.get('owned') is not True
            or account.get('protected') is not True or account.get('pending') is not False
            or type(account.get('available_ms')) is not int
            or not 0<=now-account['available_ms']<=60000
            or account.get('kind') not in ('coin','spot')):
        return dict(status='BLOCK_UNKNOWN_ACCOUNT',orders=0)
    qty=number(account['owned_btc'],nonnegative=True)
    free=number(account['confirmed_reducible_btc'],nonnegative=True)
    request=qty*(1-number(factor,nonnegative=True))
    if request<0 or request>min(qty,free):
        return dict(status='BLOCK_REDUCTION_CAPACITY',orders=0)
    return dict(status='RESEARCH_OWNED_REDUCTION' if request else 'NO_OWNED_RISK',
                quantity_btc=str(request),reduce_only=account['kind']=='coin',orders=0,
                protection='Original Lifecycle must retain/reconcile protection and confirmed remainder before any execution.')


def cross_demand(row, now):
    if row is None:
        return dict(status='WAIT_INFORMATION',reason='Complete paired signed flows and timestamped USDT conversion absent')
    causal(row,now,60000)
    if (len(set(row['venues']))!=2 or len(set(row['source_sha256']))<2
            or row['end_ms']<=row['start_ms'] or row['complete_window'] is not True
            or row['conversion_qualified'] is not True):
        return dict(status='WAIT_COMPLETE_PAIRED_WINDOW')
    if (type(row['fx_book_ms']) is not int or type(row['fx_available_ms']) is not int
            or not row['fx_book_ms']<=row['fx_available_ms']<=row['available_ms']
            or not 0<=now-row['fx_book_ms']<=1000
            or row['fx_pair']!='USDT/USD' or row['fx_source_sha256'] not in row['source_sha256']):
        raise ValueError('causal fresh USDT conversion book required')
    if not 0<number(row['fx_bid'],positive=True)<=number(row['fx_ask'],positive=True):
        raise ValueError('invalid conversion book')
    flows=[]
    for leg in row['flows']:
        buys=number(leg['buy_btc'],nonnegative=True);sells=number(leg['sell_btc'],nonnegative=True)
        if not buys+sells:raise ValueError('empty signed-flow denominator')
        flows.append((buys-sells)/(buys+sells))
    if len(flows)!=2:raise ValueError('two independent signed-flow legs required')
    if set(leg['venue'] for leg in row['flows'])!=set(row['venues']):
        raise ValueError('flow venue identities differ')
    positive=all(v>=number('.10') for v in flows)
    negative=all(v<=number('-.10') for v in flows)
    return dict(status='DEMAND_CANDIDATE' if positive or negative else 'NO_EVENT',
                positive=positive,negative=negative,imbalances=list(map(str,flows)),account_entrant=False)


def evaluate(packet):
    now=packet['decision_ms']
    if type(now) is not int:raise ValueError('explicit causal decision clock required')
    observations={}
    for name,fn in [('option-risk',option_risk),('absorption',absorption),
                    ('cross-venue',cross_demand),('expiry-basis',expiry_basis)]:
        try:observations[name]=fn(packet.get(name),now)
        except (KeyError,ValueError,TypeError,ArithmeticError) as exc:
            observations[name]=dict(status='BLOCK_INFORMATION',reason=str(exc))
    option=observations['option-risk'];event=observations['absorption'];cross=observations['cross-venue']
    expressions={
        'option-new-risk':dict(proposed_factor=option.get('proposed_new_risk_factor'),held_changes=False),
        'option-held-risk':(owned_reduction(packet.get('account'),now,'.5')
                            if option['status']=='RISK_CANDIDATE' else dict(status='NO_TRIGGER',orders=0)),
        'absorption-entry':dict(trigger=event['status']=='EVENT_CANDIDATE',direction=1,
            equity_fraction_cap='.25',topup=False,control='Same-clock momentum/DFII10 and fixed .25 risk budget'),
        'absorption-decay-exit':dict(holding_ms=7*DAY,status='WAIT_FILL_OWNED_EVENT_CLOCK',orders=0),
        'cross-demand-entry':dict(trigger=cross.get('positive',False),equity_fraction_cap='.25',
            control='Single-venue signed flow plus price momentum; no quote or aggressor inference'),
        'cross-demand-risk':dict(proposed_new_risk_factor='.5' if cross.get('negative') else None,held_changes=False),
        'expiry-net-cost':dict(status=observations['expiry-basis']['status'],
            account_entrant=False,actual_joint_margin_path_required=True),
    }
    owned_event=packet.get('owned_event')
    if owned_event is not None:
        clock=owned_event['confirmed_fill_ms']
        if (type(clock) is not int or clock>now or owned_event.get('family')!='absorption'
                or owned_event.get('source_sha256') not in (packet.get('absorption') or {}).get('source_sha256',[])):
            expressions['absorption-decay-exit']=dict(status='BLOCK_EVENT_OWNERSHIP',orders=0)
        elif now-clock>=7*DAY:
            expressions['absorption-decay-exit']=owned_reduction(packet.get('account'),now,'0')
    return dict(observations=observations,expressions=expressions,orders=0,account_entrants=0,
        maturity_status='WAIT_MATURE_NONOVERLAPPING_INFORMATION_AND_CONTROLS',
        qualification='RESEARCH_ONLY',native_authenticated=False,
        meaning='Finite proposals only; receipt shape does not authenticate funds or prove predictive/economic improvement.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--packet',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    with a.out.open('x') as stream:json.dump(evaluate(json.loads(a.packet.read_text())),stream,indent=2);stream.write('\n')


if __name__=='__main__':main()
