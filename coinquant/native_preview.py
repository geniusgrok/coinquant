"""Current native inputs for a conservatively funded entry preview.

Current rules are never substituted for historical replay evidence. No method
here sends an order, transfers funds, or marks a campaign as filled.
"""
from decimal import Decimal as D, ROUND_CEILING
from .types import Blocked, Unknown, number, floor_step
from .linear_account import Account
from .linear_sizing import funded_target

# Share of visible depth inside the IOC limit taken per order; later polls of
# the entry session may top up the rest of the committed campaign size.
BOOK_PARTICIPATION=D('.25')
# Macro parent: equity-to-stop loss ceiling for the whole campaign position.
MACRO_STOP_BUDGET=D('.03')


def _venue(reader, model, snapshot, direction):
    info=reader.get('/fapi/v1/exchangeInfo')
    instruments=[x for x in info['symbols'] if x.get('symbol')=='BTCUSDT']
    if len(instruments)!=1:raise Unknown('missing unique instrument')
    instrument=instruments[0]
    if instrument.get('status')!='TRADING' or instrument.get('contractType')!='PERPETUAL' or instrument.get('marginAsset')!='USDT':
        raise Blocked('unsupported current instrument')
    filters=[f for f in instrument['filters'] if f.get('filterType')=='PRICE_FILTER']
    if len(filters)!=1:raise Unknown('missing unique price rule')
    tick=number(filters[0]['tickSize'],positive=True)
    # Weight 20 per read; one reader keeps the account rate for at most a minute.
    now=reader.monotonic()
    cached=vars(reader).get('_commission') if isinstance(now,(int,float)) else None
    if cached and 0<=now-cached[0]<60:
        fee=cached[1]
    else:
        commission=reader.get('/fapi/v1/commissionRate',{'symbol':'BTCUSDT'})
        if commission.get('symbol')!='BTCUSDT':raise Unknown('commission scope')
        fee=number(commission['takerCommissionRate'])
        if isinstance(now,(int,float)):reader._commission=(now,fee)
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
    if abs(int(reader.clock()*1000)-stamp)>15000:raise Unknown('book expired during account refresh')
    raw_price=(asks[0][0]*D('1.001') if direction>0 else bids[0][0]*D('.999'))
    price=(floor_step(raw_price,tick) if direction>0 else (raw_price/tick).to_integral_value(rounding=ROUND_CEILING)*tick)
    capacity=sum((q for p,q in (asks if direction>0 else bids) if (p<=price if direction>0 else p>=price)),D(0))*BOOK_PARTICIPATION
    limit=getattr(reader,'capital_limit',None)
    return dict(instrument=instrument,rule=filters[0],tick=tick,fee=fee,cap=cap,mmr=mmr,fresh=fresh,
                wallet=wallet,available=available,price=price,capacity=capacity,
                capital=wallet if limit is None else min(wallet,limit),
                mark=number(fresh['mark_price'],positive=True))


def entry_preview(reader, model, snapshot):
    if model.action(number(snapshot['quantity_btc']))!='enter':
        raise Blocked('entry preview requires a fresh flat campaign')
    if snapshot['possible_entry_remainders']:
        raise Unknown('entry remainder must be reconciled before sizing')
    opportunity=model.active
    direction=opportunity.direction
    v=_venue(reader,model,snapshot,direction)
    if v['available']!=v['wallet']:raise Unknown('unexplained reserved collateral; no new quantity')
    tick,price,mark,capital=v['tick'],v['price'],v['mark'],v['capital']
    stop=(floor_step(opportunity.stop,tick) if direction>0 else (opportunity.stop/tick).to_integral_value(rounding=ROUND_CEILING)*tick)
    take=(floor_step(opportunity.take,tick)+tick if direction>0 else floor_step(opportunity.take,tick))
    if not all(number(v['rule']['minPrice'])<=p<=number(v['rule']['maxPrice']) for p in (stop,take,price)):
        raise Blocked('protection outside current price limits')
    account=Account(capital)
    fraction=model.entry_fraction('.0011')
    target=budget=None
    if opportunity is model.macro_opportunity:
        # The macro parent has the historical 3% equity-to-stop loss ceiling.
        if price<=stop:raise Blocked('macro stop must be below executable entry')
        budget=capital*MACRO_STOP_BUDGET
        target=min(capital*fraction/max(price,mark),budget/(price-stop))
    result=funded_target(account,direction,fraction,price,mark,stop,take,v['capacity'],
                         v['instrument'],fee=v['fee'],maintenance=v['mmr'],notional_limit=v['cap'],
                         target_quantity=target)
    return dict(quantity_btc=str(account.q),entry_estimate=str(price),stop=str(stop),take=str(take),
                allocated_margin_usdt=str(account.margin),constraint=result['reason'],
                requested_btc=result['requested'],
                quantity_status='read-only conservative native-input preview',
                fee=str(v['fee']),maintenance_bound=str(v['mmr']),maintenance_deduction='0',notional_cap=str(v['cap']),
                rule_scope='current observation only; not historical evidence',
                native_execution_verified=False,instrument=v['instrument'],
                side='BUY' if direction>0 else 'SELL',campaign=opportunity.identity,
                observed_at=v['fresh']['mark_time'],
                stop_budget_usdt=None if budget is None else str(budget),
                sizing_capital_usdt=str(capital))


def topup_preview(reader, model, snapshot, requested, stop, take, stop_budget=None):
    """Size an IOC add toward the committed campaign quantity under owned protection.

    The existing close-all stop and take stay in force; the add is funded so the
    combined isolated position still liquidates beyond that stop.
    """
    q=number(snapshot['quantity_btc'])
    if not q or snapshot['possible_entry_remainders']:
        raise Unknown('top-up requires a reconciled position without remainders')
    direction=1 if q>0 else -1
    v=_venue(reader,model,snapshot,direction)
    tick,price,mark=v['tick'],v['price'],v['mark']
    stop,take=number(stop,positive=True),number(take,positive=True)
    if not all(number(v['rule']['minPrice'])<=p<=number(v['rule']['maxPrice']) for p in (stop,take,price)):
        raise Blocked('protection outside current price limits')
    entry=number(snapshot['entry'],positive=True)
    target=number(requested)
    if stop_budget is not None:
        # The whole position, not only the add, must stay inside the entry's stop budget.
        room=number(stop_budget)-abs(q)*direction*(entry-stop)
        per_unit=direction*(price-stop)
        if per_unit<=0 or room<=0:
            target=abs(q)
        else:
            target=min(target,abs(q)+room/per_unit)
    account=Account(v['capital'],q=q,entry=entry,margin=number(snapshot['isolated_wallet_usdt']))
    if target<=abs(q):
        return dict(quantity_btc='0',entry_estimate=str(price),stop=str(stop),take=str(take),
                    allocated_margin_usdt=str(account.margin),constraint='stop_budget',
                    side='BUY' if direction>0 else 'SELL',observed_at=v['fresh']['mark_time'],tick=str(tick))
    result=funded_target(account,direction,D(0),price,mark,stop,take,v['capacity'],
                         v['instrument'],fee=v['fee'],maintenance=v['mmr'],notional_limit=v['cap'],
                         target_quantity=target,intended_add=True)
    added=number(result['accepted']) if result['event']=='rebalance_add' else D(0)
    return dict(quantity_btc=str(added),entry_estimate=str(price),stop=str(stop),take=str(take),
                allocated_margin_usdt=str(account.margin),constraint=result['reason'],
                side='BUY' if direction>0 else 'SELL',observed_at=v['fresh']['mark_time'],
                tick=str(tick))
