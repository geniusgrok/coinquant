#!/usr/bin/env python3
"""Pure Decimal reproduction of two completed combined-v2 top-ups.

Reads completed evidence only. Does not open State, instantiate a venue, use an
account UID, acquire an execution lock, or call a network endpoint. The inferred
mark is a compatible numerical fixture, not an unrecorded native observation.
"""
import argparse
from decimal import Decimal as D, ROUND_CEILING, ROUND_FLOOR
import gzip
import hashlib
import inspect
import json
from pathlib import Path
import sys


def pinned(path, expected):
    data=path.read_bytes()
    actual=hashlib.sha256(data).hexdigest()
    if actual!=expected:
        raise ValueError(f'evidence hash mismatch: {path}')
    return data,dict(path=str(path),bytes=len(data),sha256=actual)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parent
    data,attribution_source=pinned(root/'combined-trade-attribution.json',
        '58e8e24a5ae9f22bb5609722aa8f533a3b5c6b8d7446ed8f2bdc07dbd4e8e4fd')
    attribution=json.loads(data)
    data,receipt_source=pinned(root/'replays/combined-v2/full-current-segment-003.json.gz',
        '6b1fe9dd901e933928e4148df614ff67ad94a3910fa502dfe41a17047846fc0b')
    receipt=json.loads(gzip.decompress(data))
    assert receipt['complete'] and receipt['original_window_complete'] and receipt['session_count']==795
    rules=json.loads((root/'collateral_probe_rules.json').read_text())['instrument']
    sys.path.insert(0,str(args.runtime.resolve()))
    from coinquant.native_preview import _funded_quantity
    supports_frozen='buffer_distance' in inspect.signature(_funded_quantity).parameters
    fee=D('.00075');mmr=D('.005');factor=1-mmr-fee;step=D('.00000001');slip=D('.01')
    sent=receipt['financial']['sent'];cases=[]
    for row in attribution['newly_short_exit_dates']:
        before=row['prior_complete_observation'];closed=row['closing_observation']
        actual=before['actual']
        orders=row['actual_orders'];buys=[o for o in orders if o['side']=='BUY']
        assert len(buys)==2 and all(o['status'] in ('EXPIRED','FILLED') for o in buys)
        added=buys[1];exit_order=next(o for o in orders if o['reduceOnly'])
        index=next(i for i,x in enumerate(sent) if x[2].get('newClientOrderId')==added['clientOrderId'])
        exit_index=next(i for i,x in enumerate(sent) if x[2].get('newClientOrderId')==exit_order['clientOrderId'])
        assert sent[index-1][:2]==['POST','/fapi/v1/positionMargin']
        assert exit_index==index+1
        old=D(actual['quantity_btc']);entry=D(actual['entry']);margin=D(actual['isolated_wallet_usdt'])
        wallet=D(actual['wallet_usdt']);add=D(added['executedQty']);price=D(added['price'])
        assert add==D(added['origQty'])
        stop=D(next(a['trigger'] for a in actual['protective_algos'] if a['type']=='STOP_MARKET'))
        take=D(next(a['trigger'] for a in actual['protective_algos'] if a['type']=='TAKE_PROFIT_MARKET'))
        observed_liquidation=D(actual['native_liquidation_price'])
        assert abs((old*entry-margin)/(old*factor)-observed_liquidation)<D('1e-22')
        frozen=stop-observed_liquidation
        quantity=old+add;average=(old*entry+add*price)/quantity
        post_margin=margin+D(sent[index-1][2]['amount'])+add*price/20
        post_liquidation=(quantity*average-post_margin)/(quantity*factor)
        post_gap=stop-post_liquidation
        # Native margin writes round up to 1e-8 USDT. Inverting the rounded
        # result supplies one compatible mark, not the exact preview snapshot.
        inferred_mark=post_gap/D('.10')
        v=dict(price=price,mark=inferred_mark,fee=fee,mmr=mmr,cap=D('100000000'),
               instrument=rules,capacity=D(1),wallet=wallet,available=wallet-margin,
               capital=wallet,equity=wallet+old*(inferred_mark-entry),margin_step=step)
        kwargs=dict(stop_slippage_fraction=slip,q=old,entry=entry,margin=margin)
        baseline=_funded_quantity(v,1,stop,take,quantity,**kwargs)
        assert baseline['quantity']==add and abs(baseline['margin']-post_margin)<step
        assert post_gap<frozen
        required=quantity*average-quantity*factor*(stop-frozen)
        extra=required-post_margin
        post_wallet=wallet-add*price*fee
        post_equity=v['equity']-add*price*fee+add*(inferred_mark-price)
        stop_equity=post_wallet+quantity*(stop-average)-quantity*stop*(slip+(1+slip)*fee)
        cap=(min(v['capital'],post_wallet,post_equity,stop_equity)*D('.25')).quantize(step,rounding=ROUND_FLOOR)
        rounded_transfer=(required-margin-add*price/20).quantize(step,rounding=ROUND_CEILING)
        funded_margin=margin+rounded_transfer+add*price/20
        fixed_gap=stop-(quantity*average-funded_margin)/(quantity*factor)
        assert funded_margin<=cap and fixed_gap>=frozen
        fixed=None
        if supports_frozen:
            fixed=_funded_quantity(v,1,stop,take,quantity,buffer_distance=frozen,**kwargs)
            assert fixed['quantity']==add and abs(fixed['margin']-required)<step
        cases.append(dict(entry_day=row['entry_day'],campaign=row['combined_campaign'],
            prior_observation=dict(sequence=before['sequence'],source=before['source'],actual=actual),
            closing_observation=dict(sequence=closed['sequence'],source=closed['source'],
                                     actions=closed['actions'],model_preview=closed['model_preview']),
            actual_orders=orders,actual_fills=row['actual_fills'],
            sent_indexes=list(range(index-1,exit_index+1)),sent=sent[index-1:exit_index+1],
            frozen_gap_reconstructed=frozen,post_topup_margin_reconstructed=post_margin,
            post_topup_gap_reconstructed=post_gap,gap_shrink=frozen-post_gap,
            inferred_fixture_mark=inferred_mark,fixture_mark_is_native_observation=False,
            baseline_plan=baseline,minimum_extra_margin=extra,
            extra_margin_rounded_up=extra.quantize(step,rounding=ROUND_CEILING),
            patched_plan=fixed,patched_transfer_rounded_up=rounded_transfer,
            patched_post_topup_gap=fixed_gap,patched_post_topup_margin=funded_margin,
            modeled_stop_equity=stop_equity,modeled_stop_margin_cap=cap,
            same_quantity_fits_frozen_gap_and_existing_cap=True))
    source=Path(inspect.getfile(_funded_quantity))
    result=dict(version=1,scope='two completed combined-v2 campaigns; pure Decimal probe',
        attribution=attribution_source,receipt=receipt_source,
        native_preview_source=dict(path=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest()),
        patched_function_exercised=supports_frozen,cases=cases,
        limits=['Inferred fixture marks are not native intermediate observations.',
                'The exact Blocked reason inside recovery was not persisted and is not claimed as observed.',
                'This verifies the buffer/funding invariant, not a new full-window result or native acceptance.'])
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n')
    print(json.dumps(dict(output=str(args.output),cases=len(cases),
                          patched_function_exercised=supports_frozen,passed=True)))


if __name__=='__main__':
    main()
