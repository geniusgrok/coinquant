"""Reproduce the one preregistered entry-execution comparison from saved originals.

All inputs are local. No exchange request, order sender, training or parameter
search is performed. Full-window use requires the saved development comparison.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
from decimal import Decimal as D
from pathlib import Path

from research.bounded_execution import ExecutionStudy
from research.bounded_execution_data import load_entry_minutes
from research.minute_evidence import load as load_original_minutes
from research.persistent_hold_replay import inputs, run
from research.verify_account_ledger import verify


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-root',type=Path,required=True)
    parser.add_argument('--baseline',type=Path,required=True,help='Preserved original account directory, including inputs.json')
    parser.add_argument('--entry-minutes',type=Path,required=True)
    parser.add_argument('--mark-repair',type=Path)
    parser.add_argument('--request',type=Path,default=Path('evidence/bounded-execution-20260922/MINUTE_REQUEST.json'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--full-window',action='store_true')
    parser.add_argument('--development-root',type=Path)
    parser.add_argument('--stress',action='store_true')
    parser.add_argument('--mode',choices=('both','instant','five-minute'),default='both')
    args=parser.parse_args()
    if args.full_window:
        if args.stress or args.development_root is None:
            parser.error('full window requires the frozen development result and is not a new stress grid')
        control=json.loads((args.development_root/'development-instant/result.json').read_text())
        candidate=json.loads((args.development_root/'development-five-minute/result.json').read_text())
        if (candidate['cagr']<=control['cagr'] or D(candidate['mdd_conservative_envelope'])>=D('.5')
                or candidate['schedule_sha256']!=control['schedule_sha256']):
            parser.error('saved development comparison does not satisfy the continuation rule')
    root=args.input_root
    cache=inputs(root/'native',root/'warmup',root/'repairs',full_window=args.full_window)
    original=json.loads((args.baseline/'inputs.json').read_text())
    days=sorted({r['path'][-14:-4] for r in original if '/1m/' in r.get('path','')})
    minute_tables,identity=load_original_minutes(root/'minutes',cache[0],days)
    request=json.loads(args.request.read_text())
    added,quotes,extra,validation=load_entry_minutes(args.entry_minutes,cache[0],request['entry_hours_ms'],repair=args.mark_repair)
    for kind in minute_tables:minute_tables[kind].update(added[kind])
    identity.extend(extra)
    args.output.mkdir(parents=True,exist_ok=True)
    stage='full' if args.full_window else 'stress' if args.stress else 'development'
    frozen=args.output/(stage+'-invocation.json')
    if frozen.exists():
        parser.error('invocation already exists; retain prior outputs and choose another output directory')
    sources=['research/persistent_hold_replay.py','research/bounded_execution.py','research/bounded_execution_data.py',
             'research/bounded_execution_replay.py','pancakequant/linear_sizing.py','research/verify_account_ledger.py']
    frozen.write_text(json.dumps(dict(arguments={k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()},
        request_sha256=hashlib.sha256(args.request.read_bytes()).hexdigest(),minute_validation=validation,
        source_sha256={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in sources}),indent=2)+'\n')
    for sliced in (False,True):
        mode='five-minute' if sliced else 'instant'
        if args.mode not in ('both',mode):continue
        name=stage+'-'+mode;output=args.output/name
        execution=ExecutionStudy(sliced,args.stress,frozenset(validation['hours']),quotes)
        with (args.output/(name+'.log')).open('w') as log,contextlib.redirect_stdout(log):
            result=run(root/'native',root/'warmup',root/'repairs',output,allocation='volatility',reference='impulse_hold',
                lifecycle='one_campaign',entry_side='long',short_risk_scale=D(0),risk_scale=D('3.6'),
                quantity_rules=root/'quantity/current-instrument.json',cached_inputs=cache,
                cached_minutes=(minute_tables,identity),execution=execution,full_window=args.full_window)
        audit=verify(output);(output/'LEDGER_AUDIT.json').write_text(json.dumps(audit,indent=2)+'\n')
        print(json.dumps(dict(account=name,cagr=result['cagr'],mdd=result['mdd_conservative_envelope'],
                              final_cny=result['final_cny'],ledger_error=audit['max_equity_error_usdt'])))


if __name__=='__main__':
    main()
