"""Retain observed native cashflows; never synthesize unattended account equity."""
import json

from .types import Blocked, Unknown, number


def income(reader,state,*,force=False,wallet=None):
    now=int(reader.clock()*1000)
    coverage=state.get('income_coverage')
    if coverage and now<coverage['through']:
        raise Unknown('income observation clock regressed')
    wallet_text=None if wallet is None else str(number(wallet))
    # A closure binds one wallet value. A cached answer is reused for a minute only
    # for that same value and only when it was settled; anything else is re-read.
    if coverage and not force and now-coverage['through']<60000:
        closure=coverage.get('closure')
        if wallet_text is None:
            return {**coverage,'wallet_closure':'collected'}
        if (isinstance(closure,dict) and closure.get('wallet')==wallet_text
                and closure.get('state') in ('explained','anchored')):
            return {**coverage,'wallet_closure':closure['state']}
    # Re-read an overlap for late publication and deduplicate by native identity.
    # First use only establishes a recent audit origin, never past qualification.
    start=max(0,(coverage['through'] if coverage else now)-86400000)
    if now-start>89*86400000:
        raise Unknown('income retention gap requires native archive; no continuity inferred')
    page_number=1;observed={}
    while True:
        page=reader.get('/fapi/v1/income',{'startTime':start,'endTime':now,'page':page_number,'limit':1000})
        if not isinstance(page,list) or len(page)>1000:raise Unknown('invalid native income page')
        for event in page:
            kind=event.get('incomeType');identity=event.get('tranId');stamp=event.get('time')
            if (not isinstance(kind,str) or not kind or type(identity) is not int or identity<0
                    or type(stamp) is not int or not start<=stamp<=now or event.get('asset')!='USDT'):
                raise Unknown('unsupported native income identity or currency')
            amount=number(event.get('income'))
            row=dict(incomeType=kind,tranId=identity,time=stamp,asset='USDT',income=str(amount),
                     symbol=event.get('symbol',''),tradeId=str(event.get('tradeId','')))
            key=(kind,identity)
            if key in observed:raise Unknown('native income pagination repeated a transaction')
            observed[key]=row
        if len(page)<1000:break
        page_number+=1
    result=dict(origin=coverage['origin'] if coverage else start,through=now,
                observed_transactions=0,continuous_equity_verified=False,
                wallet_closure='collected',closure=coverage.get('closure') if coverage else None,
                scope='native cashflows only; observation gaps are not interpolated')
    with state.db:
        for (kind,identity),event in observed.items():
            prior=state.db.execute('SELECT payload FROM native_income WHERE kind=? AND transaction_id=?',(kind,identity)).fetchone()
            if prior and json.loads(prior[0])!=event:raise Unknown('native cashflow changed after observation')
            state.db.execute('INSERT OR IGNORE INTO native_income VALUES (?,?,?)',(kind,identity,json.dumps(event,sort_keys=True)))
        result['observed_transactions']=state.db.execute('SELECT COUNT(*) FROM native_income').fetchone()[0]
        if wallet is not None:
            state_name=_wallet_closure(state, number(wallet), now)
            result['wallet_closure']=state_name
            result['closure']=dict(state=state_name,wallet=wallet_text,at=now)
        state.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',('income_coverage',json.dumps(result,sort_keys=True)))
    return result


def _wallet_closure(state, wallet, now):
    """Compare the wallet change since the previous anchor with income rows.

    The first observation only sets the anchor. A later difference that the
    saved cashflows do not explain stays unexplained and blocks new risk.
    Isolated margin moves are not income and are not treated as profit.
    """
    total=sum((number(json.loads(payload).get('income'))
               for payload, in state.db.execute('SELECT payload FROM native_income')), number(0))
    anchor=state.get('wallet_anchor')
    if anchor is None:
        state.set('wallet_anchor', {'wallet':str(wallet),'income':str(total),'through':now})
        return 'anchored'
    gap=(wallet-number(anchor['wallet']))-(total-number(anchor['income']))
    if gap==0:
        state.set('wallet_anchor', {'wallet':str(wallet),'income':str(total),'through':now})
        return 'explained'
    # Income can be published after the wallet already moved. One quiet minute
    # is waiting, not a reason to stop adds. A gap that is still there after
    # that minute blocks new risk.
    seen=anchor.get('gap_since')
    if type(seen) is not int or now-seen<60000:
        state.set('wallet_anchor', {**anchor, 'gap_since': now if type(seen) is not int else seen, 'gap': str(gap)})
        return 'pending_income'
    return 'unexplained'


def allows_new_risk(audit, wallet, *, flat):
    """Whether a completed cashflow audit permits opening or adding exposure.

    Only a closure bound to this exact wallet value counts. `pending_income`,
    `unexplained`, `collected`, a stale or missing audit never open risk. The
    first-ever baseline is accepted only on a flat account; with a position
    it says nothing about the earlier wallet history.
    """
    closure=audit.get('closure') if isinstance(audit,dict) else None
    try:
        if wallet is None or not isinstance(closure,dict) or closure.get('wallet')!=str(number(wallet)):
            return False
    except Blocked:
        return False
    return closure.get('state')=='explained' or (closure.get('state')=='anchored' and flat)
