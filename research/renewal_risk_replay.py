"""One frozen HR60 renewal-risk experiment on the continuous SX60 account."""
import argparse
import contextlib
import json
from decimal import Decimal as D
from pathlib import Path

from research.conditional_hold_replay import prepared_inputs as prepare_h60_inputs
from research.conditional_hold_replay import SOURCES_H60
from research.bounded_execution import ExecutionStudy
from research.bounded_execution_replay import digest
from research.persistent_hold_replay import run
from research.verify_account_ledger import verify
from research.execution_risk_audit import audit, buffer_audit
from research.sustainable_validation import finite_budget_check
from coinquant.campaign import Campaign
from coinquant.multiscale import daily_snapshots, published_daily_key
from coinquant.research import invocations, spec, timestamp
from research.multiscale_data import extend_minutes
from research.bounded_execution_data import HOUR

PROTOCOL='evidence/renewal-risk-20260923/PROTOCOL.md'
SOURCES_HR60=tuple(dict.fromkeys((*SOURCES_H60, 'coinquant/renewal_risk.py',
    'coinquant/capital.py', 'research/renewal_risk_replay.py', PROTOCOL)))


def full_window_hours(cache, warmup):
    """Cover possible entries/renewals and the first following exit call.

    This input-only superset never consults simulated positions or returns.
    After a call, a long can survive only with a long impulse opportunity or
    positive published renewal score. The next call also needs an exit path.
    """
    cfg=spec(); trade=cache[0]['klines']; warm=cache[2]
    start=timestamp(cfg['start']); end=timestamp(cfg['end']); interval=4*HOUR
    daily=daily_snapshots(warm,trade,start,end,
        D(cfg['slippage_fraction'])+D(cfg['spread_fraction'])/2,warmup)
    model=Campaign('impulse_hold',interval); opportunities={}
    for t in range(min(warm),end,interval):
        source=warm if t<start else trade
        rows=[source[x] for x in range(t,t+interval,HOUR)]
        opportunities[t+interval]=model.update(t+interval,
            max(D(r[2]) for r in rows),min(D(r[3]) for r in rows),D(rows[-1][4]))
    hours=[]; previous_possible=False
    for t in invocations(cfg):
        opportunity=opportunities.get(t//interval*interval)
        state=daily.get(published_daily_key(t))
        possible=bool((opportunity and opportunity.direction>0) or
            (state and state.score is not None and state.score>0))
        if possible or previous_possible:
            hours.append(t)
        previous_possible=possible
    return hours


def prepared_inputs(bounded, sx60, new_data, h60_originals, full=False):
    root, prepared, warmup=prepare_h60_inputs(bounded,sx60,new_data,full)
    if full:
        prepared=extend_minutes(prepared,
            [bounded/'inputs',sx60/'exit-minutes',*new_data],
            full_window_hours(prepared[0],warmup))
    h60_root=Path(h60_originals)
    h60_invocation=json.loads((h60_root/'results/H60-development.invocation.json').read_text())
    h60_result=json.loads((h60_root/'results/H60-development/result.json').read_text())
    if not full and prepared[4] != h60_invocation['input_identity']:
        raise ValueError('HR60 inputs differ from the saved H60 development account')
    records=[json.loads(row) for row in (h60_root/'results/H60-development/execution.jsonl').read_text().splitlines()]
    holds=[row for row in records if row.get('kind')=='conditional_hold']
    if (len(holds)!=75 or sum(bool(row['permitted']) for row in holds)!=64
            or h60_result['candidate']!='H60'):
        raise ValueError('saved H60 renewal decision inventory is incomplete or changed')
    covered=set(prepared[3]['hours'])
    missing=sorted({row['time'] for row in holds if row['time'] not in covered})
    if missing:
        prepared=extend_minutes(prepared,[Path(bounded/'inputs'),Path(sx60/'exit-minutes'),*new_data],missing)
    if any(row['time'] not in set(prepared[3]['hours']) for row in holds):
        raise ValueError('HR60 permission hour lacks verified minute protection')
    return root,prepared,warmup


def run_account(root,prepared,warmup,output,*,full=False,stress=False):
    cache,minutes,quotes,validation,data_id=prepared
    cfg=ExecutionStudy(True,stress,frozenset(validation['hours']),quotes,D(6),True,'sliced')
    output.parent.mkdir(parents=True,exist_ok=True)
    invocation=output.with_suffix('.invocation.json')
    if output.exists() or invocation.exists():
        raise ValueError('HR60 originals exist; never overwrite')
    frozen=dict(candidate='HR60',full_window=full,stress=stress,
        configuration=cfg.configuration(),source_identity={p:digest(p) for p in SOURCES_HR60},
        protocol_sha256=digest(PROTOCOL),input_identity=data_id,
        minute_validation=validation,warmup_days=len(warmup))
    invocation.write_text(json.dumps(frozen,indent=2)+'\n')
    try:
        with output.with_suffix('.log').open('w') as log,contextlib.redirect_stdout(log):
            result=run(root/'native',root/'warmup',root/'repairs',output,
                allocation='volatility',reference='impulse_hold',lifecycle='one_campaign',
                entry_side='long',short_risk_scale=D(0),risk_scale=D(6),
                quantity_rules=root/'quantity/current-instrument.json',cached_inputs=cache,
                cached_minutes=minutes,execution=cfg,full_window=full,
                conditional_hold=True,renewal_risk=True,daily_warmup=warmup)
        result['candidate']='HR60'
        result['complete_source_identity']=frozen['source_identity']
        result['protocol_sha256']=frozen['protocol_sha256']
        for name in SOURCES_HR60:
            destination=output/'measured_source'/name
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(Path(name).read_bytes())
        ledger=verify(output)
        (output/'LEDGER_AUDIT.json').write_text(json.dumps(ledger,indent=2)+'\n')
        risk=audit(output);buffer=buffer_audit(output);budget=finite_budget_check(output)
        (output/'FINITE_BUDGET.json').write_text(json.dumps(budget,indent=2,default=str)+'\n')
        events=[json.loads(line) for line in (output/'execution.jsonl').read_text().splitlines()]
        schedules=[e for e in events if e.get('kind')=='renewal_risk_scheduled']
        plans=[e for e in events if e.get('kind')=='renewal_risk_plan']
        cuts=[e for e in events if e.get('kind')=='renewal_risk_reduction']
        cancellations=[e for e in events if e.get('kind')=='renewal_risk_cancelled']
        violations=[e for e in cuts if e.get('risk_limit_violation_after_execution')
                    or D(e.get('capital_after_execution','0')) < D('-1e-18')]
        covered=set(validation['hours'])
        scheduled_keys={(e['campaign'],e['call_time']) for e in schedules}
        resolved_keys={(e['campaign'],e['call_time']) for e in plans}
        resolved_keys.update((e.get('planned',{}).get('campaign'),
            e.get('planned',{}).get('call_time')) for e in cancellations)
        resolved_keys.update((e['campaign'],e['call_time']) for e in events
            if e.get('kind')=='renewal_risk_infeasible')
        result['hr60_audit']=dict(plan_count=len(plans),reduction_count=len(cuts),
            scheduled_count=len(schedules),resolved_schedule_count=len(scheduled_keys & resolved_keys),
            all_schedules_resolved=scheduled_keys==resolved_keys,
            post_execution_violations=len(violations),all_cut_stops_unchanged=all(
                not D(e['quantity_after']) or D(e['stop_before'])==D(e['stop_after']) for e in cuts),
            reductions_only=all(D(e['quantity_after'])>=0
                and D(e['quantity_after'])<=D(e['quantity_before']) for e in cuts),
            hourly_permission_calls_covered=all(e['call_time'] in covered and
                e['execute_time']-e['call_time']==(120_000 if stress else 60_000)
                for e in schedules),
            decision_at_execution_time=all(e['decision_time']==e['execute_time']
                and e['time']==e['decision_time'] for e in plans))
        result['development_hard_checks_passed']=(risk['passed'] and buffer['original_gap_maintained']
            and not budget['seven_day_entry_violations'] and not result['counts'].get('liquidation',0)
            and result['renewal_risk_checks_passed'] and not violations
            and result['hr60_audit']['all_cut_stops_unchanged']
            and result['hr60_audit']['hourly_permission_calls_covered']
            and result['hr60_audit']['all_schedules_resolved']
            and result['hr60_audit']['decision_at_execution_time'])
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
    parser.add_argument('--h60-originals',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--full-window',action='store_true')
    parser.add_argument('--stress',action='store_true')
    args=parser.parse_args()
    root,prepared,warmup=prepared_inputs(args.bounded_originals,args.sx60_originals,
        args.new_data,args.h60_originals,args.full_window)
    result=run_account(root,prepared,warmup,args.output,full=args.full_window,stress=args.stress)
    print(json.dumps({k:result[k] for k in ('candidate','cagr','mdd_conservative_envelope',
        'final_cny','counts','renewal_risk_checks_passed','development_hard_checks_passed',
        'hr60_audit')},indent=2))


if __name__=='__main__':main()
