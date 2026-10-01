"""Derive the exclusive terminal account without rewriting its original replay.

Only a terminal funding debit can be removed. No terminal trade or other cash
flow is allowed; removing a debit raises terminal wealth. Recorded worst
continuous drawdowns must strictly predate this boundary and stay unchanged.
"""
import argparse
import copy
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path

from research import rebuild
from research.comparison_report import audit
from research.complete_perp import DAY, select
from research.unified_perp import PriorFX


def exclude_row(row, fx, end, initial_wallet, initial_cny=D(10000)):
    if any(t['time'] >= end for t in row['trades']):
        raise ValueError('terminal execution cannot be derived')
    terminal = [i for i in row['funding_ledger'] if i['time'] >= end]
    if not terminal:
        return None
    if any(i['time'] != end or i['incomeType'] != 'FUNDING_FEE' or D(i['income']) >= 0 for i in terminal):
        raise ValueError('only exact-terminal funding debits supported')
    if D(row['position']) <= 0 or any(row[k] is None or row[k] >= end for k in ('mdd_envelope_at','mdd_close_at')):
        raise ValueError('terminal debit/drawdown proof unavailable')
    payment = sum((D(i['income']) for i in terminal), D(0))
    before = {k: row[k] for k in ('final_usdt','final_cny','funding','cagr')}
    row['funding_ledger'] = [i for i in row['funding_ledger'] if i['time'] < end]
    row['final_usdt'] = str(D(row['final_usdt'])-payment)
    row['final_cny'] = str(D(row['final_usdt'])*fx(end)*D('.999'))
    row['funding'] = str(D(row['funding'])+payment)
    row['cagr'] = float(D(row['final_cny'])/initial_cny)**(rebuild.YEAR_MS/(end-rebuild.timestamp(rebuild.START)))-1
    row['funnel']['funding'] -= len(terminal)
    point = row['daily'][-1]
    if point['stamp_ms'] != end:
        raise ValueError('missing actual terminal daily snapshot')
    point.update(equity_usdt=row['final_usdt'],equity_cny=row['final_cny'],
                 wallet_usdt=str(D(point['wallet_usdt'])-payment),
                 funding_paid_usdt=str(D(point['funding_paid_usdt'])+payment))
    row['daily_cny'] = [[day,str(D(value)-payment*fx(end)*D('.999')) if day == end//DAY else value]
                        for day,value in row['daily_cny']]
    row['audit'] = audit(row,initial_wallet,D(row['final_mark']))
    if not row['audit']['passed']:
        raise ValueError('exclusive terminal cash audit failed')
    return {'removed_funding':terminal,'before':before,
            'after':{k:row[k] for k in before},'audit':row['audit'],
            'no_terminal_execution':True,'mdd_unchanged':True,
            'proof':'debit removed after all execution; terminal wealth increases; worst MDD timestamps precede END'}


def derive(body, raw_sha, fx):
    identity = rebuild.source_identity()
    if identity['dirty'] or fx.sha256 != body['inputs']['fx_sha256']:
        raise ValueError('clean derivation source and matching FX required')
    result = copy.deepcopy(body)
    end = rebuild.timestamp(rebuild.END)
    initial_cny = D(body['conditions']['start_cny'])
    initial = initial_cny/fx(rebuild.timestamp(rebuild.START))*D('.999')
    changes, bindings = {}, {}
    for name,scenarios in result['results'].items():
        for scenario,row in scenarios.items():
            key = name+'/'+scenario
            bindings[key] = hashlib.sha256(json.dumps(row,sort_keys=True).encode()).hexdigest()
            row.update(candidate=name,scenario=scenario,initial_cny=str(initial_cny),
                       original_row_sha256=bindings[key])
            proof = exclude_row(row,fx,end,initial,initial_cny)
            if proof:
                changes[name+'/'+scenario] = proof
    result['selection'] = select(result['results'])
    result['conditions']['terminal_funding_exclusive_ms'] = end
    result['inputs']['derivation_source'] = identity
    result['derivation'] = {'original_accounts_sha256':raw_sha,'execution_source':body['inputs']['source'],
        'changed_accounts':changes,'row_bindings_sha256':bindings,'method':'remove only exact END funding debit; no curve scaling or replay relabelling'}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--accounts',type=Path,required=True)
    parser.add_argument('--fx',type=Path,default=Path('/workspace/starquant/data/usdcny_frankfurter.json'))
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error('never overwrite original or derived evidence')
    raw = args.accounts.read_bytes()
    result = derive(json.loads(raw),hashlib.sha256(raw).hexdigest(),PriorFX(args.fx))
    with args.out.open('x') as stream:
        json.dump(result,stream,allow_nan=False);stream.write('\n')
    print(json.dumps({'changed_accounts':list(result['derivation']['changed_accounts']),
                      'selection':result['selection']['selected_research_candidate']}))


if __name__ == '__main__':
    main()
