"""Manually started finite sessions with bounded cleanup."""
import time

from .lifecycle import ABSOLUTE_GRACE, FINISH_SECONDS, Lifecycle, blocking
from .linear_preview import advance, preview
from .native_preview import entry_preview
from .ownership import reconcile
from .state import State
from decimal import Decimal as D

from .types import Blocked, ObservationDeadline, Unknown
from .audit import allows_new_risk, income

RECOVERABLE=(Blocked,Unknown,OSError,ValueError,KeyError,TypeError,ArithmeticError)

def _guard_strategy(state):
    """Reject foreign or missing strategy state before recovery and cleanup."""
    if state.get('lifecycle_identity') is not None:
        raise Blocked('state belongs to a different strategy; no automatic migration')
    from .campaign import Campaign
    saved = state.get('linear_campaign')
    if saved is not None:
        Campaign.restore(saved)
    elif (state.get('entry_plan') or state.get('entry_fill') or state.get('entry_campaigns')
          or state.db.execute('SELECT 1 FROM intents LIMIT 1').fetchone()):
        raise Blocked('durable execution state lacks its strategy checkpoint')


def cycle(reader, state, uid, *, execute=False, may_enter=lambda:True, session=None, actions=None):
    _guard_strategy(state)
    engine=Lifecycle(reader,state,uid,authorized=execute,may_enter=may_enter,session=session)
    if actions is not None:engine.actions=actions
    if execute:
        snapshot=engine.recover_exposure(engine.settle())
    else:
        reader.recover_pending(state)
        snapshot=reader.snapshot(uid)
    # Fill-dependent expiry must never be checkpointed before ownership closes.
    # A read-only recovery is just as durable as an executing session.
    prior=engine.reconciled
    if execute and prior and prior[0] is snapshot and prior[1]==len(engine.actions)==0:
        ownership=prior[2]
    else:
        from .campaign import Campaign
        saved=state.get('linear_campaign')
        ownership=reconcile(state,reader,Campaign.restore(saved) if saved is not None else Campaign(),snapshot)
    if blocking(state):
        raise Unknown('unsettled intents block decisions')
    quantity=D(snapshot['quantity_btc'])
    model,market,reconstructed=advance(
        state,reader,fill=snapshot['entry'] if quantity else None)
    # DFII10 is read only when it can change the decision, so its outage never
    # delays a primary exit or protection maintenance.
    row=reader.dfii10_snapshot() if model.macro_relevant() else None
    model.select_macro(row,snapshot['mark_price'],int(reader.clock()*1000),bootstrap=reconstructed)
    state.set_many({'linear_campaign':model.checkpoint(),'market_bootstrap':False})
    result=preview(model,snapshot)
    result.update(ownership=ownership,reconstructed_market_only=reconstructed)
    audit=None
    if execute:
        # A missing or open cashflow audit blocks new risk (entry and add), never
        # a verified reduction or protection. The audit is bound to this wallet.
        wallet=snapshot.get('wallet_usdt')
        wallet_window=dict(wallet_observed_from_ms=snapshot.get('wallet_observed_from_ms',snapshot.get('observed_at_ms')),
                           wallet_observed_until_ms=snapshot.get('wallet_observed_until_ms',snapshot.get('observed_at_ms')))
        if result['action']=='enter':
            audit=income(reader,state,wallet=wallet,**wallet_window)
            engine.risk_audit_ok=allows_new_risk(audit,wallet,flat=True)
        elif result['action']=='hold':
            try:
                audit=income(reader,state,wallet=wallet,**wallet_window)
                engine.risk_audit_ok=allows_new_risk(audit,wallet,flat=False)
            except RECOVERABLE:
                engine.risk_audit_ok=False
        writes=len(engine.actions)
        action,snapshot=engine.decide(model,snapshot)
        # A fill may occur in any write/read race. Reconcile again before deciding
        # on another campaign, never mark a preview or request as consumed.
        latest=engine.reconciled
        if len(engine.actions)>writes and not (latest and latest[0] is snapshot and latest[1]==len(engine.actions)):
            reconcile(state,reader,model,snapshot)
        result['action']=action
        if engine.entry_constraint is not None:
            result['entry_constraint']=engine.entry_constraint
    elif result['action']=='enter':
        result.update(entry_preview(reader,model,snapshot))
    if audit is None:
        try:audit=income(reader,state)
        except RECOVERABLE:
            # Reporting must not discard this cycle's actions after a reduction or exit.
            audit={'status':'unresolved'}
    return dict(status='executed' if execute and engine.actions else 'no_action' if execute else 'read_only',
                actual=snapshot,model_preview=result,market_through=market['complete_through'],
                actions=engine.actions,write_attempted=bool(engine.actions),income_audit=audit)


def _reason(exc,generic):
    return str(exc) if isinstance(exc,(Blocked,Unknown)) else generic


def _execution_unresolved(report,execute):
    """True when durable intents or exposure are not settled. A session that only
    ran out of observation time before any request left is not unresolved."""
    if not execute:
        return False
    if report.get('pending_intents') or report.get('cleanup')=='unresolved':
        return True
    actual=report.get('actual')
    if actual is None:
        return report.get('cleanup')!='verified'
    return bool(D(actual['quantity_btc'])) and not (
        actual.get('native_full_position_protected') and actual.get('stop_before_liquidation'))


def offline_report(report, state, now):
    """Describe the last verified observation, never promise protection after it."""
    actual=report.get('actual') if report.get('observation_current',True) else None
    checkpoint=(state.get('linear_campaign') or {}).get('body',{})
    if type(checkpoint.get('last')) is int:
        report['next_required_review_at_ms']=checkpoint['last']+14400000
    report['unresolved_order_ids']=[p['id'] for p in state.pending()]
    report['possible_entry_remainders']=actual.get('possible_entry_remainders') if actual else None
    unresolved=bool(report.get('execution_unresolved') or report.get('pending_intents')
                    or report.get('possible_entry_remainders')
                    or report.get('protection_replacement_pending') or actual is None)
    q=D(actual['quantity_btc']) if actual and 'quantity_btc' in actual else None
    equity=D(actual['equity_usdt']) if actual and actual.get('equity_usdt') is not None else None
    report['equity_status']='unverified' if equity is None else 'positive' if equity>0 else 'nonpositive'
    protected=bool(actual and actual.get('native_full_position_protected')
                   and actual.get('stop_before_liquidation'))
    report['native_protection_at_stop']=dict(
        status='unverified' if q is None else 'flat' if not q else 'observed' if protected else 'incomplete',
        observed_at_ms=actual.get('observed_at_ms') if actual else None,
        protective_algos=actual.get('protective_algos',[]) if actual else [])
    report['strategy_review_required']=bool(q and report.get('status') in ('blocked','unknown'))
    report['manual_takeover_required']=unresolved or report['strategy_review_required'] or bool(q and (not protected or equity is None or equity<=0))
    report['review_due_now']=(report['manual_takeover_required'] or
                             report.get('next_required_review_at_ms',now+1)<=now)
    if report['manual_takeover_required']:
        report['manual_action']=('Correct the reported configuration or state and use status to inspect current exposure; keep the original state directory.'
                                if report.get('status')=='blocked' and not report.get('write_attempted') and not report.get('pending_intents') else
                                'Keep the original state directory; inspect the position, orders and protection. Do not resend an unknown order or open new risk.')
    report['offline_boundary']='Only last-observed native exchange protection may execute; strategy expiry, new candles and macro changes require another manual run. Offline manual positions can be affected by retained close-position orders.'
    if actual and actual.get('mark_price') and q is not None:
        notional=abs(q)*D(actual['mark_price'])
        wallet=D(actual.get('wallet_usdt') or 0)
        report['exchange_leverage_setting']=20
        report['wallet_notional_ratio']=str(notional/wallet) if wallet>0 else None
        report['account_notional_leverage']=str(notional/equity) if equity is not None and equity>0 else None


def run(config, reader, *, execute=False, monotonic=time.monotonic, wait=time.sleep, stopping=lambda:False,
        trial_mode=None, source_digest=None):
    """Finite deadline plus bounded cleanup. No timers survive this function.

    `execute` is an explicit operation authorization.
    The public CLI requires an explicit bounded trial gate before credentials.

    Budgets: trading ends at `deadline`; protection, bounded reduction and the final
    verification each keep their own budget, but none may renew the adapter past
    `hard_deadline`. Every failure, including clock alignment, is recorded in the
    final report; a first interrupt starts the same cleanup and later ones do not
    abort it.
    """
    started=monotonic();deadline=started+config.session_seconds
    report=dict(status='read_only',cycles=0,write_attempted=False,errors=[],observation_timeouts=0,
                stop_reason='deadline',cleanup='not_required',
                session_started_at_ms=int(reader.clock()*1000))
    if trial_mode is not None:report['trial_mode']=trial_mode
    if source_digest is not None:report['source_digest']=source_digest
    if (getattr(reader,'environment','live')!=config.environment
            or getattr(reader,'capital_limit',None)!=config.capital_limit
            or getattr(reader,'loss_fraction',None)!=config.loss_fraction
            or getattr(reader,'slip_fraction',None)!=config.slip_fraction):
        raise Blocked('exchange adapter and configuration differ in environment or risk limits')
    if hasattr(reader,'hard_deadline'):reader.hard_deadline=deadline+ABSOLUTE_GRACE
    with State(config.state_dir,config.scope) as state:
        _guard_strategy(state)
        prior_writes=state.get('write_attempt_count') or 0
        last_failure=None
        try:
            while monotonic()<deadline and not stopping():
                report['cycles']+=1
                report['observation_current']=False
                report.pop('actual',None)
                report.pop('model_preview',None)
                report['actions']=[]
                phase='clock'
                try:
                    reader.begin_cycle(min(120,max(1,deadline-monotonic())))
                    phase='cycle'
                    current=cycle(reader,state,config.account_uid,execute=execute,
                                  may_enter=lambda:monotonic()<deadline and not stopping(),
                                  session=report['session_started_at_ms'],actions=report['actions'])
                    report.update(current,write_attempted=report['write_attempted'] or current['write_attempted'])
                    report['observation_current']=True
                    report.pop('reason',None)
                    last_failure=None
                except RECOVERABLE as exc:
                    # No same-identity writes are retried; subsequent rounds may
                    # only proceed after durable recovery and a fresh observation.
                    timeout=isinstance(exc,ObservationDeadline)
                    last_failure='deadline' if timeout else 'other'
                    report['observation_timeouts']+=timeout
                    report.update(status='blocked' if isinstance(exc,Blocked) else 'unknown',
                                  reason=_reason(exc,'Invalid observation or state'))
                    report['errors']=(report['errors']+[dict(cycle=report['cycles'],phase=phase,
                                                             error_type=type(exc).__name__,reason=report['reason'])])[-10:]
                report['write_attempted']=(state.get('write_attempt_count') or 0)>prior_writes
                state.report(report)
                remaining=deadline-monotonic()
                if remaining>0 and not stopping():
                    wait(min(config.poll_seconds,remaining))
            if stopping():report['stop_reason']='requested'
        except KeyboardInterrupt:
            report['stop_reason']='interrupted'
        finally:
            if execute:
                # No new entry is permitted here. Native protection remains at process exit.
                engine=Lifecycle(reader,state,config.account_uid,authorized=True)
                cleanup_deadline=min(deadline+ABSOLUTE_GRACE,monotonic()+ABSOLUTE_GRACE)
                if hasattr(reader,'hard_deadline'):reader.hard_deadline=cleanup_deadline
                interrupted=False
                report['cleanup']='unresolved'
                while monotonic()<cleanup_deadline:
                    progress=engine.exit_progress
                    try:
                        try:
                            reader.begin_cycle(min(FINISH_SECONDS,cleanup_deadline-monotonic()))
                        except RECOVERABLE as exc:
                            # Signed reads align the clock again; a failed sample must not skip verification.
                            report['errors']=(report['errors']+[dict(cycle=report['cycles'],phase='cleanup_clock',
                                                                     error_type=type(exc).__name__,
                                                                     reason=_reason(exc,'Clock alignment failed'))])[-10:]
                        report['actual']=engine.finish()
                        report['cleanup']='verified'
                        report['observation_current']=True
                        break
                    except KeyboardInterrupt:
                        # The first signal may have landed inside this cleanup; the handler ignores later ones.
                        if not interrupted:
                            interrupted=True
                            continue
                        report.update(status='unknown',cleanup='unresolved',reason='Interrupted again during cleanup; state is recoverable')
                        report['observation_current']=False
                        report.pop('actual',None)
                        report.pop('model_preview',None)
                        break
                    except RECOVERABLE as exc:
                        report.update(status='unknown',cleanup='unresolved',reason=_reason(exc,'Cleanup could not be verified'))
                        report['errors']=(report['errors']+[dict(cycle=report['cycles'],phase='cleanup',
                                                                 error_type=type(exc).__name__,reason=report['reason'])])[-10:]
                        report['observation_current']=False
                        report.pop('actual',None)
                        report.pop('model_preview',None)
                        # Only a freshly reconciled terminal owned reduction may
                        # advance to a new identity, within the original hard end.
                        if engine.exit_progress<=progress:
                            break
                report['write_attempted'] |= bool(engine.actions)
                if engine.actions:report['cleanup_actions']=engine.actions
                if report['cleanup']=='verified':
                    try:report['income_audit']=income(reader,state,force=True)
                    except KeyboardInterrupt:
                        report.update(status='unknown',income_audit={'status':'unresolved'},
                                      reason='Interrupted during the final income audit')
                    except RECOVERABLE as exc:
                        report.update(status='unknown',income_audit={'status':'unresolved'},
                                      reason=_reason(exc,'Income audit unavailable'))
            report['pending_intents']=len(state.pending())
            report['protection_replacement_pending']=bool(state.get('session_replacement'))
            if config.capital_limit is not None:
                report['sizing_capital_usdt']=str(config.capital_limit)
            if execute:report['entry_timing']=state.get('entry_timing')
            report['write_attempted']=(state.get('write_attempt_count') or 0)>prior_writes
            if report['pending_intents']:
                report.update(status='unknown',reason='Durable intents require recovery')
            report['execution_unresolved']=_execution_unresolved(report,execute)
            if (execute and last_failure=='deadline' and report['status']=='unknown' and report['cleanup']=='verified'
                    and not report['execution_unresolved'] and report.get('income_audit',{}).get('status')!='unresolved'):
                # The last poll ran out of observation time before any request left, and the
                # closing verification found the account settled: report that, not a failure.
                report.update(status='executed' if report['write_attempted'] else 'no_action',
                              reason='Last poll ended at the observation deadline; closing verification settled')
            offline_report(report,state,int(reader.clock()*1000))
            report['elapsed_seconds']=max(0,monotonic()-started)
            state.report(report)
    return report
