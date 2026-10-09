"""Retain observed native cashflows; never synthesize unattended account equity."""
import json

from .types import Blocked, Unknown, number

NATIVE_UNIT=number('0.00000001')


def income(reader,state,*,force=False,wallet=None,
           wallet_observed_from_ms=None,wallet_observed_until_ms=None):
    now=int(reader.clock()*1000)
    if wallet is not None:
        start_wallet = now if wallet_observed_from_ms is None else wallet_observed_from_ms
        end_wallet = now if wallet_observed_until_ms is None else wallet_observed_until_ms
        if (type(start_wallet) is not int or type(end_wallet) is not int
                or not 0 < start_wallet <= end_wallet <= now):
            raise Unknown('wallet observation interval unavailable')
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
    # First use establishes the wallet anchor.
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
                observed_transactions=0,
                # A new collection has not closed any wallet until the check
                # below succeeds. A wallet-less refresh cannot extend old proof.
                wallet_closure='collected',closure=None)
    with state.db:
        for (kind,identity),event in observed.items():
            prior=state.db.execute('SELECT payload FROM native_income WHERE kind=? AND transaction_id=?',(kind,identity)).fetchone()
            if prior and json.loads(prior[0])!=event:raise Unknown('native cashflow changed after observation')
            state.db.execute('INSERT OR IGNORE INTO native_income VALUES (?,?,?)',(kind,identity,json.dumps(event,sort_keys=True)))
        result['observed_transactions']=state.db.execute('SELECT COUNT(*) FROM native_income').fetchone()[0]
        if wallet is not None:
            state_name=_wallet_closure(state, number(wallet), now, start_wallet, end_wallet)
            result['wallet_closure']=state_name
            result['closure']=dict(state=state_name,wallet=wallet_text,at=now)
        state.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',('income_coverage',json.dumps(result,sort_keys=True)))
    return result


def funding_debit(reader,state,campaign,snapshot):
    """Verified paid BTC funding for an add; receipts never refill its budget."""
    links=state.get('entry_campaigns') or {}
    if not isinstance(links,dict) or any(not isinstance(link,dict) for link in links.values()):
        raise Unknown('campaign funding boundary unavailable')
    starts=[link.get('prepared_at') for link in links.values() if link.get('campaign')==campaign]
    if (not starts or any(type(stamp) is not int or stamp<=0 for stamp in starts)
            or any(link.get('campaign')!=campaign for link in links.values())):
        raise Unknown('campaign funding boundary unavailable')
    start=min(starts)  # Includes the existing conservative 15-second overlap.
    first=snapshot.get('wallet_observed_from_ms',snapshot.get('observed_at_ms'))
    last=snapshot.get('wallet_observed_until_ms',snapshot.get('observed_at_ms'))
    if type(first) is not int or type(last) is not int or not start<=first<=last:
        raise Unknown('campaign funding wallet boundary unavailable')
    coverage=state.get('income_coverage') or {}
    closure=coverage.get('closure') or {}
    # Equal wallet balances can hide funding offset by a receipt or realized
    # profit. Only an audit of this wallet observation may supply add costs.
    fresh=type(closure.get('at')) is int and closure['at']>=last
    proof=income(reader,state,force=not fresh,wallet=snapshot.get('wallet_usdt'),
                 wallet_observed_from_ms=first,wallet_observed_until_ms=last)
    if (not allows_new_risk(proof,snapshot.get('wallet_usdt'),flat=False)
            or type(proof.get('origin')) is not int or proof['origin']>start
            or type(proof.get('through')) is not int or proof['through']<last):
        raise Unknown('campaign funding history does not close the current wallet')
    paid=number(0)
    for payload, in state.db.execute("SELECT payload FROM native_income WHERE kind='FUNDING_FEE'"):
        row=json.loads(payload);stamp=row.get('time')
        if type(stamp) is not int:
            raise Unknown('funding observation time unavailable')
        if stamp<start:continue
        if (stamp>proof['through'] or row.get('asset')!='USDT'
                or not isinstance(row.get('symbol'),str) or not row['symbol']):
            raise Unknown('campaign funding scope unavailable')
        if row['symbol']=='BTCUSDT':paid+=max(number(0),-number(row.get('income')))
    return paid


def _wallet_closure(state, wallet, now, wallet_from=None, wallet_until=None):
    """Compare the wallet change since the previous anchor with income rows.

    The first observation only sets the anchor. A later difference that the
    saved cashflows do not explain stays unexplained and blocks new risk.
    Isolated margin moves are not income and are not treated as profit.
    """
    wallet_from=now if wallet_from is None else wallet_from
    wallet_until=now if wallet_until is None else wallet_until
    rows=[json.loads(payload) for payload, in state.db.execute('SELECT payload FROM native_income')]
    total=sum((number(row.get('income')) for row in rows), number(0))
    anchor=state.get('wallet_anchor')
    if anchor is None:
        # The two account reads straddle this interval. A cashflow during or
        # after it cannot be assigned to that wallet, even when its row arrives
        # before the audit query. Wait for a later consistent observation.
        if any(row['time'] >= wallet_from for row in rows):
            return 'pending_income'
        state.set('wallet_anchor', {'wallet':str(wallet),'income':'0','through':now,
                                    'baseline_from_ms':wallet_from,'baseline_until_ms':wallet_until})
        return 'anchored'
    if 'baseline_from_ms' in anchor:
        start,end=anchor['baseline_from_ms'],anchor['baseline_until_ms']
        if (type(start) is not int or type(end) is not int or not 0<start<=end<=anchor['through']
                or any(start <= row['time'] <= end for row in rows)):
            raise Unknown('income at the initial wallet boundary cannot be classified')
        # Late rows definitely preceding the first wallet observation were
        # already in its balance; they cannot become new income on publication.
        total=sum((number(row['income']) for row in rows if row['time']>end), number(0))
    # Older state has no durable first-observation boundary. Preserve its
    # conservative accounting instead of guessing which late rows are old.
    gap=(wallet-number(anchor['wallet']))-(total-number(anchor['income']))
    # Binance reports USDT to 1e-8; a smaller residue is arithmetic, not a cashflow.
    if abs(gap)<NATIVE_UNIT:
        state.set('wallet_anchor', {**{k:anchor[k] for k in ('baseline_from_ms','baseline_until_ms') if k in anchor},
                                    'wallet':str(wallet),'income':str(total),'through':now})
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
