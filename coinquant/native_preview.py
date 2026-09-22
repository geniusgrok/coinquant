"""Current native inputs for a read-only, conservatively funded entry preview.

Current rules are never substituted for historical replay evidence. No method
here sends an order, transfers funds, or marks a campaign as filled.
"""
from decimal import Decimal as D
from .types import Blocked, Unknown, number, floor_step
from .linear_account import Account
from .linear_sizing import funded_target


def entry_preview(reader, model, snapshot):
    if model.action(number(snapshot['quantity_btc']))!='enter':
        raise Blocked('entry preview requires a fresh flat campaign')
    if snapshot['possible_entry_remainders']:
        raise Unknown('entry remainder must be reconciled before sizing')
    info=reader.get('/fapi/v1/exchangeInfo')
    instruments=[x for x in info['symbols'] if x.get('symbol')=='BTCUSDT']
    if len(instruments)!=1:raise Unknown('missing unique instrument')
    instrument=instruments[0]
    if instrument.get('status')!='TRADING' or instrument.get('contractType')!='PERPETUAL' or instrument.get('marginAsset')!='USDT':
        raise Blocked('unsupported current instrument')
    filters=[f for f in instrument['filters'] if f.get('filterType')=='PRICE_FILTER']
    if len(filters)!=1:raise Unknown('missing unique price rule')
    tick=number(filters[0]['tickSize'],positive=True)
    commission=reader.get('/fapi/v1/commissionRate',{'symbol':'BTCUSDT'})
    if commission.get('symbol')!='BTCUSDT':raise Unknown('commission scope')
    fee=number(commission['takerCommissionRate'])
    brackets=reader.get('/fapi/v1/leverageBracket',{'symbol':'BTCUSDT'})
    if isinstance(brackets,list):
        if len(brackets)!=1:raise Unknown('ambiguous leverage brackets')
        brackets=brackets[0]
    if brackets.get('symbol')!='BTCUSDT':raise Unknown('bracket scope')
    if number(brackets.get('notionalCoef','1'))!=1:
        raise Unknown('account-specific bracket coefficient requires explicit validation')
    tiers=brackets['brackets'];previous=D(0);eligible=[]
    for tier in tiers:
        if number(tier['initialLeverage'])<20:break
        floor=number(tier['notionalFloor']);cap=number(tier['notionalCap'],positive=True)
        mmr=number(tier['maintMarginRatio']);cum=number(tier['cum'])
        if floor!=previous or cap<=floor or not 0<=mmr<D('.05') or cum<0:
            raise Unknown('unsupported or incomplete bracket geometry')
        previous=cap
        eligible.append((cap,mmr))
    if not eligible:raise Blocked('no verified 20x bracket')
    cap=max(x[0] for x in eligible);mmr=max(x[1] for x in eligible)
    # Max eligible MMR and no maintenance deduction over-reserve collateral.
    # This is an explicitly conservative preview, not exact tier liquidation.
    book=reader.get('/fapi/v1/depth',{'symbol':'BTCUSDT','limit':100})
    stamp=book.get('E')
    if type(stamp) is not int or abs(int(reader.clock()*1000)-stamp)>15000:
        raise Unknown('stale order book')
    bids=[(number(p,positive=True),number(q,positive=True)) for p,q in book['bids']]
    asks=[(number(p,positive=True),number(q,positive=True)) for p,q in book['asks']]
    if (not bids or not asks or bids[0][0]>=asks[0][0]
            or any(a[0]>=b[0] for a,b in zip(asks,asks[1:]))
            or any(a[0]<=b[0] for a,b in zip(bids,bids[1:]))):
        raise Unknown('invalid order book ordering')
    fresh=reader.snapshot(snapshot['account_uid'])
    if fresh['mark_time']//14400000*14400000!=model.last:
        raise Unknown('a new completed candle requires model catch-up')
    if any(fresh[k]!=snapshot[k] for k in ('wallet_usdt','quantity_btc','possible_entry_remainders')):
        raise Unknown('account changed during preflight')
    available=fresh.get('available_usdt')
    if available is None:raise Unknown('available USDT balance missing')
    wallet=number(fresh['wallet_usdt']);available=number(available)
    if not 0<=available<=wallet:raise Unknown('unsupported available collateral')
    if available!=wallet:raise Unknown('unexplained reserved collateral; no new quantity')
    if abs(int(reader.clock()*1000)-stamp)>15000:raise Unknown('book expired during account refresh')
    price=asks[0][0]*D('1.001');mark=number(fresh['mark_price'],positive=True)
    capacity=sum((q for p,q in asks if p<=price),D(0))*D('.01')
    opportunity=model.model.active
    stop=floor_step(opportunity.stop,tick)
    take=floor_step(opportunity.take,tick)+tick
    if not number(filters[0]['minPrice'])<=stop<take<=number(filters[0]['maxPrice']):
        raise Blocked('protection outside current price limits')
    account=Account(wallet)
    result=funded_target(account,1,model.fraction('3.6','.0011'),price,mark,stop,take,capacity,
                         instrument,fee=fee,maintenance=mmr,notional_limit=cap)
    return dict(quantity_btc=str(account.q),entry_estimate=str(price),stop=str(stop),take=str(take),
                allocated_margin_usdt=str(account.margin),constraint=result['reason'],
                quantity_status='read-only conservative native-input preview',
                fee=str(fee),maintenance_bound=str(mmr),maintenance_deduction='0',notional_cap=str(cap),
                rule_scope='current observation only; not historical evidence',
                native_execution_verified=False)
