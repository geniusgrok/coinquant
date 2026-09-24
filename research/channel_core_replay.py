"""UC4 continuous account, sharing the SX60 cash, funding and execution engine."""
import argparse
import contextlib
import json
from decimal import Decimal as D
from pathlib import Path

from coinquant.channel_core import ChannelCore
from coinquant.research import invocations, spec, timestamp
from research.bounded_execution import ExecutionStudy
from research.bounded_execution_replay import SOURCES, digest
from research.conditional_hold_replay import prepared_inputs
from research.multiscale_data import extend_minutes
from research.persistent_hold_replay import HOUR, run
from research.verify_account_ledger import verify
from research.execution_risk_audit import audit, buffer_audit
from research.sustainable_validation import finite_budget_check

PROTOCOL = 'evidence/unified-channel-20260924/PROTOCOL.md'
RISK_CONTROL = 'evidence/unified-channel-20260924/RISK_CONTROL_PROTOCOL.md'
RECOVERABLE = 'evidence/recoverable-risk-20260924/PROTOCOL.md'
SOURCES_UC4 = tuple(dict.fromkeys((*SOURCES, 'coinquant/channel_core.py',
    'coinquant/capital.py', 'research/planned_exit.py', 'research/channel_core_replay.py', PROTOCOL)))


def possible_hours(cache, full=False):
    """Market-only superset: positive state and its first subsequent exit call."""
    frozen = spec()
    start = timestamp(frozen['start'])
    end = timestamp(frozen['end' if full else 'development_end'])
    warm, trade = cache[2], cache[0]['klines']
    model = ChannelCore()
    states = {}
    for t in range(min(warm), end, 4*HOUR):
        source = warm if t < start else trade
        bars = [source[x] for x in range(t,t+4*HOUR,HOUR)]
        states[t+4*HOUR] = model.update(t+4*HOUR,
            max(D(r[2]) for r in bars), min(D(r[3]) for r in bars), D(bars[-1][4]))
    hours = []
    previous = False
    for t in invocations(frozen):
        if t >= end:
            break
        active = bool(states[t//(4*HOUR)*4*HOUR])
        if active or previous:
            hours.append(t)
        previous = active
    return hours


def prepared(bounded, sx60, more, full=False, extra_hours=()):
    root, base, _ = prepared_inputs(bounded, sx60, more, full=full)
    hours = sorted(set(possible_hours(base[0], full)) | set(extra_hours))
    completed = extend_minutes(base,
        [bounded/'inputs', sx60/'exit-minutes', *more], hours)
    return root, completed, hours


def run_account(root, prepared, output, *, full=False, stress=False, risk_scale=D(6), recoverable_risk=False):
    cache, minutes, quotes, validation, data_id = prepared
    if risk_scale not in (D(6), D('3.6')):
        raise ValueError('UC4 predeclared risk scales only')
    if recoverable_risk and risk_scale != D('3.6'):
        raise ValueError('recoverable risk is frozen to UC4 3.6')
    cfg = ExecutionStudy(True, stress, frozenset(validation['hours']), quotes, risk_scale, True, 'sliced')
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() or output.with_name(output.name+'.invocation.json').exists():
        raise ValueError('existing original account; refusing overwrite')
    protocol = RECOVERABLE if recoverable_risk else RISK_CONTROL if risk_scale == D('3.6') else PROTOCOL
    sources = SOURCES_UC4 + ('research/persistent_hold_replay.py',protocol)
    frozen = dict(candidate='UC4-recoverable' if recoverable_risk else 'UC4-risk-control' if risk_scale == D('3.6') else 'UC4',
        full_window=full, stress=stress, risk_scale=str(risk_scale),
        configuration=cfg.configuration(), input_identity=data_id,
        source_identity={p:digest(p) for p in sources},
        protocol_sha256=digest(protocol), minute_validation=validation)
    output.with_name(output.name+'.invocation.json').write_text(json.dumps(frozen,indent=2)+'\n')
    try:
        with output.with_name(output.name+'.log').open('w') as log, contextlib.redirect_stdout(log):
            result = run(root/'native',root/'warmup',root/'repairs',output,
                allocation='volatility',reference='channel_core',lifecycle='one_campaign',
                entry_side='long',short_risk_scale=D(0),risk_scale=risk_scale,
                quantity_rules=root/'quantity/current-instrument.json',cached_inputs=cache,
                cached_minutes=minutes,execution=cfg,full_window=full,
                recoverable_risk=recoverable_risk)
        result['candidate']=frozen['candidate']
        result['complete_source_identity']=frozen['source_identity']
        result['protocol_sha256']=frozen['protocol_sha256']
        ledger=verify(output)
        risk=audit(output)
        buffer=buffer_audit(output)
        budget=finite_budget_check(output)
        for name, obj in (('LEDGER_AUDIT',ledger),('RISK_AUDIT',risk),
                          ('BUFFER_AUDIT',buffer),('FINITE_BUDGET',budget)):
            (output/(name+'.json')).write_text(json.dumps(obj,indent=2,default=str)+'\n')
        result['development_hard_checks_passed']=(risk['passed'] and buffer['original_gap_maintained']
            and not budget['seven_day_entry_violations'] and not result['counts'].get('liquidation',0))
        (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        return result
    except BaseException:
        import traceback
        output.with_name(output.name+'.failure.txt').write_text(traceback.format_exc())
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bounded-originals',type=Path,required=True)
    p.add_argument('--sx60-originals',type=Path,required=True)
    p.add_argument('--new-data',type=Path,action='append',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--full-window',action='store_true')
    p.add_argument('--stress',action='store_true')
    p.add_argument('--risk-control-3.6',dest='risk_control_36',action='store_true',help='one prespecified risk attribution control')
    p.add_argument('--recoverable-risk',action='store_true',help='frozen dynamic per-mother drawdown allocation')
    p.add_argument('--coverage-hours',type=Path,help='held protection crossings found in a previous account')
    a=p.parse_args()
    extra_hours=json.loads(a.coverage_hours.read_text())['hours'] if a.coverage_hours else ()
    root, data, hours=prepared(a.bounded_originals,a.sx60_originals,a.new_data,a.full_window,extra_hours)
    if a.risk_control_36 and a.recoverable_risk:
        p.error('select one risk variant')
    result=run_account(root,data,a.output,full=a.full_window,stress=a.stress,
                       risk_scale=D('3.6') if a.risk_control_36 or a.recoverable_risk else D(6),
                       recoverable_risk=a.recoverable_risk)
    print(json.dumps({k:result[k] for k in ('candidate','cagr','mdd_conservative_envelope',
                                            'final_cny','counts','development_hard_checks_passed')},indent=2))


if __name__=='__main__':main()
