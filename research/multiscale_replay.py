"""M60 frozen research entry, using the shared SX60 account and execution chain."""
import argparse
import contextlib
import hashlib
import json
from pathlib import Path
from decimal import Decimal as D

from research.bounded_execution import ExecutionStudy
from research.bounded_execution_replay import SOURCES, digest
from research.multiscale_data import restore_inputs
from research.persistent_hold_replay import run
from research.verify_account_ledger import verify
from research.execution_risk_audit import audit, buffer_audit
from research.sustainable_validation import finite_budget_check

PROTOCOL='evidence/multiscale-core-20260923/PROTOCOL.md'
MODEL_SOURCES=(*SOURCES,'coinquant/capital.py','research/planned_exit.py',
    'research/execution_risk_audit.py','coinquant/multiscale.py',
    'research/multiscale_data.py','research/multiscale_replay.py')


def source_identity():
    return {p:digest(p) for p in MODEL_SOURCES}


def run_account(root, output, prepared, warmup=(), *, full=False, stress=False, control=False):
    cache,minutes,quotes,validation,data_id=prepared
    cfg=ExecutionStudy(True,stress,frozenset(validation['hours']),quotes,D(6),True,'sliced')
    output.parent.mkdir(parents=True,exist_ok=True)
    invocation=output.with_suffix('.invocation.json')
    if output.exists() or invocation.exists():
        raise ValueError('retain prior source/output; refusing account overwrite')
    frozen=dict(candidate='SX60-refined-control' if control else 'M60',full_window=full,
        configuration=cfg.configuration(),protocol_sha256=digest(PROTOCOL),
        source_identity=source_identity(),input_identity=data_id,minute_validation=validation,
        daily_warmup_sha256=hashlib.sha256(json.dumps(warmup,default=str).encode()).hexdigest())
    invocation.write_text(json.dumps(frozen,indent=2)+'\n')
    try:
        with output.with_suffix('.log').open('w') as log,contextlib.redirect_stdout(log):
            result=run(root/'native',root/'warmup',root/'repairs',output,
                allocation='volatility',reference='impulse_hold' if control else 'multiscale',
                lifecycle='one_campaign',entry_side='long',short_risk_scale=D(0),risk_scale=D(6),
                quantity_rules=root/'quantity/current-instrument.json',cached_inputs=cache,
                cached_minutes=minutes,execution=cfg,full_window=full,daily_warmup=() if control else warmup)
        result['candidate']=frozen['candidate'];result['complete_source_identity']=source_identity()
        result['protocol_sha256']=frozen['protocol_sha256']
        (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        for name in MODEL_SOURCES:
            dest=output/'measured_source'/name;dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(Path(name).read_bytes())
        ledger=verify(output);(output/'LEDGER_AUDIT.json').write_text(json.dumps(ledger,indent=2)+'\n')
        risk=audit(output);buffer=buffer_audit(output);budget=finite_budget_check(output)
        (output/'FINITE_BUDGET.json').write_text(json.dumps(budget,indent=2,default=str)+'\n')
        result['development_hard_checks_passed']=(risk['passed'] and buffer['original_gap_maintained']
            and not budget['seven_day_entry_violations'] and not result['counts'].get('liquidation',0))
        (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(dict(candidate=result['candidate'],cagr=result['cagr'],mdd=result['mdd_conservative_envelope'],
            final_cny=result['final_cny'],ledger_error=ledger['max_equity_error_usdt'],
            hard_checks=result['development_hard_checks_passed'],counts=result['counts']),indent=2))
        return result
    except BaseException:
        import traceback
        output.with_suffix('.failure.txt').write_text(traceback.format_exc())
        raise


def eligible_development(path, warmup):
    """No new requirement to beat SX60 or reach 150% in development."""
    result=json.loads((path/'result.json').read_text())
    frozen=json.loads(path.with_suffix('.invocation.json').read_text())
    if (result['candidate']!='M60' or result['validation_used'] or result['cagr']<=0
            or D(result['mdd_conservative_envelope'])>=D('.5')
            or not result['development_hard_checks_passed']
            or frozen['source_identity']!=source_identity()
            or frozen['daily_warmup_sha256']!=hashlib.sha256(json.dumps(warmup,default=str).encode()).hexdigest()):
        raise ValueError('development risk/identity failure; do not erase it with later years')
    verify(path)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bounded-originals',type=Path,required=True)
    p.add_argument('--sx60-originals',type=Path,required=True)
    p.add_argument('--new-data',type=Path,action='append',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--full-window',action='store_true')
    p.add_argument('--stress',action='store_true')
    p.add_argument('--development',type=Path)
    p.add_argument('--control',action='store_true',help='Only for a proven affected SX60 input path')
    a=p.parse_args()
    root,prepared,warmup,_=restore_inputs(a.bounded_originals,a.sx60_originals,a.new_data,full=a.full_window)
    if a.full_window and not a.control:
        if a.development is None:p.error('full M60 requires the saved eligible development account')
        eligible_development(a.development,warmup)
    run_account(root,a.output,prepared,warmup,full=a.full_window,stress=a.stress,control=a.control)


if __name__=='__main__':main()
