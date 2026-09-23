"""One frozen H60 conditional-expiry experiment on the shared SX60 account."""
import argparse
import contextlib
import json
from decimal import Decimal as D
from pathlib import Path

from research.bounded_execution import ExecutionStudy
from research.bounded_execution_replay import SOURCES, digest, prepare
from research.sustainable_replay import exit_minutes
from research.multiscale_data import extend_minutes, warmup_daily, potential_hours
from research.persistent_hold_replay import run
from research.verify_account_ledger import verify
from research.execution_risk_audit import audit, buffer_audit
from research.sustainable_validation import finite_budget_check

PROTOCOL = 'evidence/conditional-hold-20260923/PROTOCOL.md'
SOURCES_H60 = (*SOURCES, 'coinquant/capital.py', 'coinquant/multiscale.py',
               'coinquant/conditional_hold.py', 'research/planned_exit.py',
               'research/execution_risk_audit.py', 'research/persistent_hold_replay.py',
               'research/conditional_hold_replay.py', PROTOCOL)


def prepared_inputs(bounded, sx60, new_data, full=False):
    stage = 'full' if full else 'development'
    root = bounded/'inputs'/stage
    prepared = exit_minutes(sx60/'exit-minutes', prepare(root,
        bounded/'old-controls'/stage, bounded/'inputs/entry-minutes',
        bounded/'evidence/MINUTE_REQUEST.json', bounded/'inputs/mark-repair', full=full))
    warmup, warmup_identity = warmup_daily(new_data)
    if not full:
        # Exact verified minute bars already collected for the M60 development
        # period; adding them never changes the frozen entry algorithm.
        hours, _ = potential_hours(prepared[0], warmup)
        prepared = extend_minutes(prepared, [bounded/'inputs', sx60/'exit-minutes', *new_data],
                                  hours, warmup_identity)
    return root, prepared, warmup


def run_account(root, prepared, warmup, output, control=False, full=False, stress=False):
    cache, minutes, quotes, validation, data_id = prepared
    cfg = ExecutionStudy(True, stress, frozenset(validation['hours']), quotes, D(6), True, 'sliced')
    output.parent.mkdir(parents=True, exist_ok=True)
    invocation = output.with_suffix('.invocation.json')
    if output.exists() or invocation.exists():
        raise ValueError('account originals exist; never overwrite')
    frozen = dict(candidate='SX60-control' if control else 'H60', full_window=full,
                  configuration=cfg.configuration(), source_identity={p:digest(p) for p in SOURCES_H60},
                  protocol_sha256=digest(PROTOCOL), input_identity=data_id,
                  minute_validation=validation, warmup_days=len(warmup))
    invocation.write_text(json.dumps(frozen, indent=2)+'\n')
    try:
        with output.with_suffix('.log').open('w') as log, contextlib.redirect_stdout(log):
            result = run(root/'native', root/'warmup', root/'repairs', output,
                allocation='volatility', reference='impulse_hold', lifecycle='one_campaign',
                entry_side='long', short_risk_scale=D(0), risk_scale=D(6),
                quantity_rules=root/'quantity/current-instrument.json', cached_inputs=cache,
                cached_minutes=minutes, execution=cfg, full_window=full,
                conditional_hold=not control, daily_warmup=() if control else warmup)
        result['candidate']=frozen['candidate']
        result['complete_source_identity']=frozen['source_identity']
        result['protocol_sha256']=frozen['protocol_sha256']
        for name in SOURCES_H60:
            destination=output/'measured_source'/name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(Path(name).read_bytes())
        ledger=verify(output)
        (output/'LEDGER_AUDIT.json').write_text(json.dumps(ledger,indent=2)+'\n')
        risk=audit(output);buffer=buffer_audit(output);budget=finite_budget_check(output)
        (output/'FINITE_BUDGET.json').write_text(json.dumps(budget,indent=2,default=str)+'\n')
        result['development_hard_checks_passed']=(risk['passed'] and buffer['original_gap_maintained']
            and not budget['seven_day_entry_violations'] and not result['counts'].get('liquidation',0))
        (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        return result
    except BaseException:
        import traceback
        output.with_suffix('.failure.txt').write_text(traceback.format_exc())
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bounded-originals',type=Path,required=True)
    parser.add_argument('--sx60-originals',type=Path,required=True)
    parser.add_argument('--new-data',type=Path,action='append',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--control',action='store_true')
    parser.add_argument('--full-window',action='store_true')
    parser.add_argument('--stress',action='store_true')
    args=parser.parse_args()
    root,prepared,warmup=prepared_inputs(args.bounded_originals,args.sx60_originals,args.new_data,args.full_window)
    result=run_account(root,prepared,warmup,args.output,args.control,args.full_window,args.stress)
    print(json.dumps({k:result[k] for k in ('candidate','cagr','mdd_conservative_envelope','final_cny','counts','development_hard_checks_passed')},indent=2))


if __name__=='__main__':main()
