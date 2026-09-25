"""Preregistered A/B development and single-selected formal account runner."""
import argparse
import contextlib
import json
import traceback
from decimal import Decimal as D
from pathlib import Path

from coinquant.campaign import Campaign
from coinquant.research import invocations, spec, timestamp
from research.bounded_execution import ExecutionStudy
from research.bounded_execution_replay import SOURCES, digest
from research.execution_risk_audit import audit, buffer_audit
from research.multiscale_data import restore_inputs, extend_minutes
from research.persistent_hold_replay import HOUR, run
from research.sustainable_validation import finite_budget_check
from research.verify_account_ledger import verify

PROTOCOL = 'evidence/active-core-20260925/PROTOCOL.md'
SOURCES_ACTIVE = tuple(dict.fromkeys((*SOURCES, 'coinquant/active_core.py',
    'coinquant/multiscale.py', 'coinquant/capital.py', 'research/planned_exit.py',
    'research/sustainable_replay.py', 'research/multiscale_data.py',
    'research/active_core_replay.py', 'research/execution_risk_audit.py',
    'research/sustainable_validation.py', PROTOCOL)))
CONFIGS = {'A36': ('coherent_trend','multiscale',D('3.6')),
           'A48': ('coherent_trend','multiscale',D('4.8')),
           'B48': ('restart_budget','post_impulse_restart',D('4.8')),
           'B60': ('restart_budget','post_impulse_restart',D(6))}


def restart_hours(cache, full=False, absence=False):
    """Market-only superset of all positive PIR1 calls and first flat exits."""
    cfg=spec();start=timestamp(cfg['start']);end=timestamp(cfg['end' if full else 'development_end'])
    model=Campaign('post_impulse_restart')
    opportunity={}
    for t in range(min(cache[2]),end,4*HOUR):
        source=cache[2] if t<start else cache[0]['klines']
        bars=[source[x] for x in range(t,t+4*HOUR,HOUR)]
        opportunity[t+4*HOUR]=model.update(t+4*HOUR,
            max(D(r[2]) for r in bars),min(D(r[3]) for r in bars),D(bars[-1][4]))
    hours=[];prev=False
    for t in invocations(cfg,stress=absence):
        if t>=end:break
        op=opportunity.get(t//(4*HOUR)*(4*HOUR))
        active=bool(op and op.direction>0)
        if active or prev:hours.append(t)
        prev=active
    return hours


def prepared_inputs(bounded,sx60,extra,*,full=False,absence=False,config='A36'):
    root,prepared,warmup,_=restore_inputs(bounded,sx60,extra,full=full)
    if config.startswith('B'):
        hours=restart_hours(prepared[0],full,absence)
        prepared=extend_minutes(prepared,[bounded/'inputs',sx60/'exit-minutes',*extra],hours)
    return root,prepared,warmup


def run_account(root,prepared,warmup,output,config,*,full=False,stress=False,absence=False):
    if config not in CONFIGS:raise ValueError('unregistered configuration')
    family,reference,scale=CONFIGS[config]
    cache,minutes,quotes,validation,data_id=prepared
    settings=ExecutionStudy(True,stress,frozenset(validation['hours']),quotes,scale,True,'sliced')
    output.parent.mkdir(parents=True,exist_ok=True)
    invocation=output.with_suffix('.invocation.json')
    if output.exists() or invocation.exists():raise ValueError('account originals already exist')
    sources={name:digest(name) for name in SOURCES_ACTIVE}
    frozen=dict(config=config,family=family,reference=reference,full=full,stress=stress,
        absence=absence,source_identity=sources,protocol_sha256=digest(PROTOCOL),
        configuration=settings.configuration(),input_identity=data_id,
        daily_warmup=[[str(x) for x in row] for row in warmup],
        minute_validation=validation)
    invocation.write_text(json.dumps(frozen,indent=2)+'\n')
    try:
        with output.with_suffix('.log').open('w') as log,contextlib.redirect_stdout(log):
            result=run(root/'native',root/'warmup',root/'repairs',output,
                allocation='volatility',reference=reference,lifecycle='one_campaign',
                entry_side='long',short_risk_scale=D(0),risk_scale=scale,
                quantity_rules=root/'quantity/current-instrument.json',cached_inputs=cache,
                cached_minutes=minutes,execution=settings,full_window=full,
                absence_stress=absence,daily_warmup=warmup if config.startswith('A') else (),
                active_core=family)
        result.update(candidate=config,complete_source_identity=sources,
            protocol_sha256=frozen['protocol_sha256'],input_identity=data_id)
        for name in SOURCES_ACTIVE:
            dest=output/'measured_source'/name
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(Path(name).read_bytes())
        checks={'LEDGER_AUDIT':verify(output),'RISK_AUDIT':audit(output),
                'BUFFER_AUDIT':buffer_audit(output),'FINITE_BUDGET':finite_budget_check(output)}
        for name,value in checks.items():
            (output/(name+'.json')).write_text(json.dumps(value,indent=2,default=str)+'\n')
        result['hard_checks_passed']=(checks['RISK_AUDIT']['passed']
            and checks['BUFFER_AUDIT']['original_gap_maintained']
            and not checks['FINITE_BUDGET']['seven_day_entry_violations']
            and not result['counts'].get('liquidation',0))
        (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        return result
    except BaseException:
        output.with_suffix('.failure.txt').write_text(traceback.format_exc())
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bounded-originals',type=Path,required=True)
    p.add_argument('--sx60-originals',type=Path,required=True)
    p.add_argument('--new-data',type=Path,action='append',required=True)
    p.add_argument('--config',choices=CONFIGS,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--full-window',action='store_true')
    p.add_argument('--stress',action='store_true')
    p.add_argument('--absence',action='store_true')
    p.add_argument('--selection',type=Path)
    a=p.parse_args()
    if (a.full_window or a.stress or a.absence):
        if not a.selection: p.error('formal or stress replay requires frozen development selection')
        selected=json.loads(a.selection.read_text())
        if selected['config']!=a.config or selected['protocol_sha256']!=digest(PROTOCOL):
            p.error('selected source/protocol/config differs')
        if selected['source_identity']!={name:digest(name) for name in SOURCES_ACTIVE}:
            p.error('measured source differs from development selection')
    root,prepared,warmup=prepared_inputs(a.bounded_originals,a.sx60_originals,a.new_data,
        full=a.full_window,absence=a.absence,config=a.config)
    if a.selection and not a.absence and a.full_window:
        prefix=prepared_inputs(a.bounded_originals,a.sx60_originals,a.new_data,config=a.config)
        selected=json.loads(a.selection.read_text())
        if prefix[1][-1]!=selected['development_input_identity']:
            p.error('formal development input prefix differs')
    result=run_account(root,prepared,warmup,a.output,a.config,full=a.full_window,
        stress=a.stress,absence=a.absence)
    print(json.dumps({k:result[k] for k in ('candidate','cagr','mdd_conservative_envelope',
        'final_cny','hard_checks_passed','counts')},indent=2))


if __name__=='__main__':main()
