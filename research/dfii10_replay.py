"""One SX60 paired account with the preregistered DFII10 flat-period overlay."""
import argparse
import contextlib
import json
from decimal import Decimal as D
from pathlib import Path

from research.bounded_execution import ExecutionStudy
from research.bounded_execution_replay import digest, prepare
from research.dfii10_asof import snapshots
from research.dfii10_overlay import potential_hours
from research.execution_risk_audit import audit, buffer_audit
from research.multiscale_data import extend_minutes
from research.persistent_hold_replay import run
from research.sustainable_replay import exit_minutes
from research.sustainable_validation import finite_budget_check
from research.verify_account_ledger import verify

PROTOCOL = 'evidence/real-yield-20260924/PROTOCOL.md'
SOURCES = ('research/dfii10_asof.py','research/dfii10_overlay.py',
           'research/dfii10_replay.py','research/persistent_hold_replay.py',
           'research/bounded_execution.py','research/planned_exit.py',
           'coinquant/capital.py','coinquant/linear_account.py',
           'coinquant/linear_sizing.py', 'coinquant/campaign.py',
           'research/multiscale_data.py','research/sustainable_replay.py',PROTOCOL)


def prepared_inputs(bounded, sx60, new_minutes, alfred, full=False, absence=False):
    stage = 'full' if full else 'development'
    root = bounded/'inputs'/stage
    initial = prepare(root,bounded/'old-controls'/stage,
                      bounded/'inputs/entry-minutes',bounded/'evidence/MINUTE_REQUEST.json',
                      bounded/'inputs/mark-repair',full=full)
    initial = exit_minutes(sx60/'exit-minutes',initial)
    calls, coverage = snapshots(alfred,full,absence)
    hours = potential_hours(calls)
    # Existing SX60 minute inputs remain present; the additional official
    # minutes are shared by both sides of the paired account comparison.
    extra_roots = [new_minutes] if isinstance(new_minutes,Path) else list(new_minutes)
    extended = extend_minutes(initial,[bounded/'inputs',sx60/'exit-minutes',*extra_roots],hours)
    return root,extended,calls,coverage


def run_account(root,prepared,calls,alfred,output,*,control=False,full=False,stress=False,absence=False):
    cache,minutes,quotes,validation,data_id = prepared
    cfg = ExecutionStudy(True,stress,frozenset(validation['hours']),quotes,D(6),True,'sliced')
    output.parent.mkdir(parents=True,exist_ok=True)
    invocation = output.with_suffix('.invocation.json')
    if output.exists() or invocation.exists():
        raise ValueError('account originals exist; refusing to overwrite')
    raw = json.loads((alfred/'RECEIPT.json').read_text())
    alfred_id = {r['path']:r['response_sha256'] for r in raw['attempts'] if r.get('path')}
    sources={p:digest(p) for p in SOURCES}
    frozen=dict(candidate='SX60-control' if control else 'DFII10-20x25bp',
                full_window=full,stress=stress,absence=absence,configuration=cfg.configuration(),
                source_identity=sources,input_identity=data_id,
                minute_validation=validation,alfred_response_identity=alfred_id,
                protocol_sha256=digest(PROTOCOL),macro_snapshots=len(calls))
    invocation.write_text(json.dumps(frozen,indent=2)+'\n')
    try:
        with output.with_suffix('.log').open('w') as log,contextlib.redirect_stdout(log):
            result=run(root/'native',root/'warmup',root/'repairs',output,
                       allocation='volatility',reference='impulse_hold',lifecycle='one_campaign',
                       entry_side='long',short_risk_scale=D(0),risk_scale=D(6),
                       quantity_rules=root/'quantity/current-instrument.json',cached_inputs=cache,
                       cached_minutes=minutes,execution=cfg,full_window=full,
                       macro_calls=None if control else {r['call_time_ms']:r for r in calls},
                       absence_stress=absence)
        result['candidate']=frozen['candidate']
        result['complete_source_identity']=sources
        result['protocol_sha256']=frozen['protocol_sha256']
        result['alfred_response_identity']=alfred_id
        source_dir=output/'measured_source'
        for name in SOURCES:
            destination=source_dir/name
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(Path(name).read_bytes())
        (output/'DFII10_CALLS.json').write_text(json.dumps(calls,indent=2)+'\n')
        ledger=verify(output)
        (output/'LEDGER_AUDIT.json').write_text(json.dumps(ledger,indent=2)+'\n')
        risk=audit(output)
        buffer=buffer_audit(output)
        budget=finite_budget_check(output)
        (output/'FINITE_BUDGET.json').write_text(json.dumps(budget,indent=2,default=str)+'\n')
        result['hard_checks_passed']=(risk['passed'] and buffer['original_gap_maintained']
            and not budget['seven_day_entry_violations'] and not result['counts'].get('liquidation',0))
        (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:result[k] for k in ('candidate','cagr','mdd_conservative_envelope',
            'final_cny','hard_checks_passed','counts')}),flush=True)
        return result
    except BaseException:
        import traceback
        output.with_suffix('.failure.txt').write_text(traceback.format_exc())
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bounded-originals',type=Path,required=True)
    p.add_argument('--sx60-originals',type=Path,required=True)
    p.add_argument('--new-minutes',type=Path,action='append',required=True)
    p.add_argument('--alfred',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--control',action='store_true')
    p.add_argument('--full-window',action='store_true')
    p.add_argument('--stress',action='store_true')
    p.add_argument('--absence',action='store_true')
    a=p.parse_args()
    root,prepared,calls,_=prepared_inputs(a.bounded_originals,a.sx60_originals,a.new_minutes,a.alfred,a.full_window,a.absence)
    run_account(root,prepared,calls,a.alfred,a.output,control=a.control,full=a.full_window,stress=a.stress,absence=a.absence)
