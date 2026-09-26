"""Manually started finite sessions; live and replay use this exact coordinator."""
import time

from .lifecycle import Lifecycle
from .linear_preview import advance, preview
from .native_preview import entry_preview
from .ownership import reconcile
from .state import State
from .types import Blocked, Unknown, number


def cycle(reader, state, uid, *, execute=False, may_enter=lambda:True):
    engine=Lifecycle(reader,state,uid,authorized=execute,may_enter=may_enter)
    if execute:
        snapshot=engine.recover_exposure(engine.settle())
    else:
        reader.recover_pending(state)
        snapshot=reader.snapshot(uid)
    model,market,reconstructed=advance(state,reader)
    ownership=reconcile(state,reader,model,snapshot)
    if state.pending():
        raise Unknown('unsettled intents block decisions')
    result=preview(model,snapshot,side='both')
    result.update(ownership=ownership,reconstructed_market_only=reconstructed)
    if execute:
        action,snapshot=engine.decide(model,snapshot)
        # A fill may occur in any write/read race. Reconcile again before deciding
        # on another campaign, never mark a preview or request as consumed.
        reconcile(state,reader,model,snapshot)
        result['action']=action
    elif result['action']=='enter':
        result.update(entry_preview(reader,model,snapshot,side='both'))
    return dict(status='executed' if execute and engine.actions else 'no_action' if execute else 'read_only',
                actual=snapshot,model_preview=result,market_through=market['complete_through'],
                actions=engine.actions,write_attempted=bool(engine.actions))


def run(config, reader, *, execute=False, monotonic=time.monotonic, wait=time.sleep, stopping=lambda:False):
    """Finite deadline plus bounded cleanup. No timers survive this function.

    `execute` is an explicit operation authorization, not a qualification claim.
    The public CLI rejects it before credentials until both release gates pass.
    Offline replay injects a non-network venue and virtual clock here.
    """
    started=monotonic();deadline=started+config.session_seconds
    report=dict(status='read_only',cycles=0,write_attempted=False,errors=[],
                qualification='NOT_QUALIFIED',stop_reason='deadline',cleanup='not_required')
    identity='binance:BTCUSDT:live:'+config.account_uid
    with State(config.state_dir,identity) as state:
        prior_writes=state.get('write_attempt_count') or 0
        try:
            while monotonic()<deadline and not stopping():
                reader.begin_cycle(min(120,max(1,deadline-monotonic())))
                report['cycles']+=1
                report['observation_current']=False
                try:
                    current=cycle(reader,state,config.account_uid,execute=execute,
                                  may_enter=lambda:monotonic()<deadline and not stopping())
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
                report['write_attempted'] |= bool(engine.actions)
            report['pending_intents']=len(state.pending())
            report['write_attempted']=(state.get('write_attempt_count') or 0)>prior_writes
            if report['pending_intents']:
                report.update(status='unknown',reason='Durable intents require recovery')
            report['elapsed_seconds']=max(0,monotonic()-started)
            state.report(report)
    return report
