"""Retain observed native cashflows; never synthesize unattended account equity."""
import json

from .types import Unknown, number


def income(reader,state,*,force=False):
    now=int(reader.clock()*1000)
    coverage=state.get('income_coverage')
    if coverage and now<coverage['through']:
        raise Unknown('income observation clock regressed')
    if coverage and not force and now-coverage['through']<60000:
        return coverage
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
                scope='native cashflows only; observation gaps are not interpolated')
    with state.db:
        for (kind,identity),event in observed.items():
            prior=state.db.execute('SELECT payload FROM native_income WHERE kind=? AND transaction_id=?',(kind,identity)).fetchone()
            if prior and json.loads(prior[0])!=event:raise Unknown('native cashflow changed after observation')
            state.db.execute('INSERT OR IGNORE INTO native_income VALUES (?,?,?)',(kind,identity,json.dumps(event,sort_keys=True)))
        result['observed_transactions']=state.db.execute('SELECT COUNT(*) FROM native_income').fetchone()[0]
        state.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',('income_coverage',json.dumps(result,sort_keys=True)))
    return result
