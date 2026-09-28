"""Manually started finite sessions; live and replay use this exact coordinator."""
import time

from .lifecycle import Lifecycle, blocking
from .linear_preview import advance, preview
from .native_preview import entry_preview
from .ownership import reconcile
from .state import State
from .types import Blocked, Unknown
from .audit import income


def cycle(reader, state, uid, *, execute=False, may_enter=lambda:True, session=None):
    engine=Lifecycle(reader,state,uid,authorized=execute,may_enter=may_enter,session=session)
    if execute:
        snapshot=engine.recover_exposure(engine.settle())
    else:
        reader.recover_pending(state)
        snapshot=reader.snapshot(uid)
    model,market,reconstructed=advance(state,reader)
    # DFII10 is read only when it can change the decision, so its outage never
    # delays a primary exit or protection maintenance.
    row=reader.dfii10_snapshot() if model.macro_relevant() else None
    model.select_macro(row,snapshot['mark_price'],int(reader.clock()*1000),bootstrap=reconstructed)
    state.set_many({'linear_campaign':model.checkpoint(),'market_bootstrap':False})
    # Recovery already reconciled this exact observation when it wrote nothing.
    prior=engine.reconciled
    if execute and prior and prior[0] is snapshot and prior[1]==len(engine.actions)==0:
        ownership=prior[2]
    else:
        ownership=reconcile(state,reader,model,snapshot)
    if blocking(state):
        raise Unknown('unsettled intents block decisions')
    result=preview(model,snapshot)
    result.update(ownership=ownership,reconstructed_market_only=reconstructed)
    audit=None
    if execute:
        # Missing cashflow audit blocks new risk, never a verified reduction.
        if result['action']=='enter':audit=income(reader,state)
        elif result['action']=='hold':
            # A hold may add to the position; the add needs the same prior audit.
            # Maintaining existing protection does not.
            try:
                audit=income(reader,state)
                engine.may_add=True
            except (Blocked,Unknown,OSError,ValueError,KeyError,TypeError,ArithmeticError):
                engine.may_add=False
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
    if audit is None:audit=income(reader,state)
    return dict(status='executed' if execute and engine.actions else 'no_action' if execute else 'read_only',
                actual=snapshot,model_preview=result,market_through=market['complete_through'],
                actions=engine.actions,write_attempted=bool(engine.actions),income_audit=audit)


def run(config, reader, *, execute=False, monotonic=time.monotonic, wait=time.sleep, stopping=lambda:False,
        trial_mode=None, source_digest=None):
    """Finite deadline plus bounded cleanup. No timers survive this function.

    `execute` is an explicit operation authorization, not a qualification claim.
    The public CLI requires an explicit bounded trial gate before credentials.
    Offline replay injects a non-network venue and virtual clock here.
    """
    started=monotonic();deadline=started+config.session_seconds
    report=dict(status='read_only',cycles=0,write_attempted=False,errors=[],
                qualification='NOT_QUALIFIED',stop_reason='deadline',cleanup='not_required',
                session_started_at_ms=int(reader.clock()*1000))
    if trial_mode is not None:report['trial_mode']=trial_mode
    if source_digest is not None:report['source_digest']=source_digest
    if (getattr(reader,'environment','live')!=config.environment
            or getattr(reader,'capital_limit',None)!=config.capital_limit):
        raise Blocked('exchange adapter and configuration differ in environment or capital limit')
    with State(config.state_dir,config.scope) as state:
        prior_writes=state.get('write_attempt_count') or 0
        try:
            while monotonic()<deadline and not stopping():
                reader.begin_cycle(min(120,max(1,deadline-monotonic())))
                report['cycles']+=1
                report['observation_current']=False
                report.pop('actual',None)
                report.pop('model_preview',None)
                report['actions']=[]
                try:
                    current=cycle(reader,state,config.account_uid,execute=execute,
                                  may_enter=lambda:monotonic()<deadline and not stopping(),
                                  session=report['session_started_at_ms'])
                    report.update(current,write_attempted=report['write_attempted'] or current['write_attempted'])
                    report['observation_current']=True
                    report.pop('reason',None)
                except (Blocked,Unknown,OSError,ValueError,KeyError,TypeError,ArithmeticError) as exc:
                    # No same-identity writes are retried; subsequent rounds may
                    # only proceed after durable recovery and a fresh observation.
                    report.update(status='unknown',reason=str(exc) if isinstance(exc,(Blocked,Unknown)) else 'Invalid observation or state')
                    report['errors']=(report['errors']+[dict(cycle=report['cycles'],reason=report['reason'])])[-10:]
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
                # A cleanup budget is separate from the deadline; no new entry is
                # permitted here. Native protection remains at process exit.
                reader.begin_cycle(120)
                engine=Lifecycle(reader,state,config.account_uid,authorized=True)
                try:
                    report['actual']=engine.finish()
                    report['cleanup']='verified'
                    report['observation_current']=True
                except (Blocked,Unknown,OSError,ValueError,KeyError,TypeError,ArithmeticError) as exc:
                    report.update(status='unknown',cleanup='unresolved',reason=str(exc) if isinstance(exc,(Blocked,Unknown)) else 'Cleanup could not be verified')
                    report['observation_current']=False
                    report.pop('actual',None)
                    report.pop('model_preview',None)
                report['write_attempted'] |= bool(engine.actions)
                if report['cleanup']=='verified':
                    try:report['income_audit']=income(reader,state,force=True)
                    except (Blocked,Unknown,OSError,ValueError,KeyError,TypeError,ArithmeticError) as exc:
                        report.update(status='unknown',income_audit={'status':'unresolved'},
                                      reason=str(exc) if isinstance(exc,(Blocked,Unknown)) else 'Income audit unavailable')
            report['pending_intents']=len(state.pending())
            if execute:report['entry_timing']=state.get('entry_timing')
            report['write_attempted']=(state.get('write_attempt_count') or 0)>prior_writes
            if report['pending_intents']:
                report.update(status='unknown',reason='Durable intents require recovery')
            report['elapsed_seconds']=max(0,monotonic()-started)
            state.report(report)
    return report
