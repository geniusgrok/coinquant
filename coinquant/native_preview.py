"""Current native inputs for a conservatively funded entry preview.

No method here sends an order, transfers funds, or marks a campaign as filled.
"""
from decimal import Decimal as D, ROUND_CEILING
from .types import Blocked, Unknown, number, floor_step
from .binance import market_quantity

# Share of visible depth inside the IOC limit taken per order; later polls of
# the entry session may top up the rest of the committed campaign size.
BOOK_PARTICIPATION=D('.25')
# Macro parent: equity-to-stop loss ceiling for the whole campaign position.
MACRO_STOP_BUDGET=D('.03')


def _loss_per_btc(direction, entry, stop, fee, slip):
    # Exit at an adverse price beyond the stop, plus both taker fees.
    return direction*(entry-stop)+entry*fee+stop*(slip+(1+slip)*fee)


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
                quote=dict(observed_at_ms=stamp,best_bid=str(bids[0][0]),best_ask=str(asks[0][0]),
                           visible_limit_depth_btc=str(capacity/BOOK_PARTICIPATION),
                           participation_fraction=str(BOOK_PARTICIPATION)),
                capital=wallet if limit is None else min(wallet,limit),
                mark=number(fresh['mark_price'],positive=True))


def _funded_quantity(v, direction, stop, take, requested, *, q=D(0), entry=D(0), margin=D(0)):
    """Round a proposed add and fund its combined position beyond the native stop."""
    price,mark,fee,mmr=v['price'],v['mark'],v['fee'],v['mmr']
    if (direction not in (-1,1) or min(price,mark,stop,take)<=0
            or not requested.is_finite() or requested<0
            or not 0<=fee<D('.05') or not 0<=mmr<D('.05')
            or q and q*direction<=0):
        raise ValueError('invalid funded entry inputs')
    old=abs(q)
    raw=min(requested,v['cap']/max(price,mark))
    result=dict(requested=str(requested),quantity=D(0),margin=margin,reason='minimum_or_unchanged')
    # This function only sizes entries/adds. Native reductions have their own
    # reduce-only lifecycle and never pass through an account simulation.
    if raw<=old:
        return result
    delta=market_quantity(min(raw-old,v['capacity']),price,v['instrument'],order='LIMIT')
    if not delta:
        return result
    reason=('liquidity_cap' if v['capacity']<raw-old else
            'notional_cap' if raw<requested else 'target')
    if not (stop<min(price,mark)<=max(price,mark)<take if direction>0
            else take<min(price,mark)<=max(price,mark)<stop):
        result['reason']='protection';return result
    boundary=stop-direction*mark*D('.10')
    if boundary<=0:
        result['reason']='gap_boundary';return result

    def funded(amount):
        quantity=old+amount
        average=(old*entry+amount*price)/quantity
        total=direction*quantity
        entry_fee=amount*price*fee
        required=max(margin,quantity*average/20,
                     total*average-(total-quantity*(mmr+fee))*boundary)
        reserve=quantity*max(price,mark)*(D('.01')+fee)
        if required+reserve+entry_fee>v['capital']:
            return None
        liquidation=(total*average-required)/(total-quantity*(mmr+fee))
        if not (liquidation<stop<mark if direction>0 else mark<stop<liquidation):
            return None
        return required

    required=funded(delta)
    if required is None:
        low,high=D(0),delta
        for _ in range(48):
            middle=(low+high)/2
            if funded(middle) is None:high=middle
            else:low=middle
        delta=market_quantity(low,price,v['instrument'],order='LIMIT')
        required=funded(delta) if delta else None
        reason='funding_cap'
    if required is None:
        result['reason']='insufficient_funded_minimum';return result
    return dict(requested=str(requested),quantity=delta,margin=required,reason=reason)


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
    fraction=model.entry_fraction('.0011')
    target=capital*fraction/max(price,mark)
    budget=None
    loss_fraction=getattr(reader,'loss_fraction',None)
    slip_fraction=getattr(reader,'slip_fraction',None)
    if (loss_fraction is None)!=(slip_fraction is None):
        raise Blocked('loss budget and slippage configuration disagree')
    if loss_fraction is not None:
        loss_fraction=number(loss_fraction,positive=True)
        slip_fraction=number(slip_fraction,positive=True)
        if loss_fraction>=1 or slip_fraction>=1:
            raise Blocked('invalid loss budget or stop slippage')
        budget=capital*loss_fraction
    if opportunity is model.macro_opportunity:
        # The macro campaign has a 3% equity-to-stop loss ceiling.
        if price<=stop:raise Blocked('macro stop must be below executable entry')
        macro_budget=capital*MACRO_STOP_BUDGET
        budget=macro_budget if budget is None else min(budget,macro_budget)
    if budget is not None:
        per_unit=(_loss_per_btc(direction,price,stop,v['fee'],slip_fraction)
                  if slip_fraction is not None else direction*(price-stop))
        if per_unit<=0:raise Blocked('nonpositive modeled stop loss')
        target=min(target,budget/per_unit)
    result=_funded_quantity(v,direction,stop,take,target)
    return dict(quantity_btc=str(direction*result['quantity']),entry_estimate=str(price),stop=str(stop),take=str(take),
                allocated_margin_usdt=str(result['margin']),constraint=result['reason'],
                requested_btc=result['requested'],
                fee=str(v['fee']),maintenance_bound=str(v['mmr']),maintenance_deduction='0',notional_cap=str(v['cap']),
                instrument=v['instrument'],
                side='BUY' if direction>0 else 'SELL',campaign=opportunity.identity,
                observed_at=v['fresh']['mark_time'],
                quote_observation=v['quote'],
                stop_budget_usdt=None if budget is None else str(budget),
                stop_slippage_fraction=None if slip_fraction is None else str(slip_fraction),
                sizing_capital_usdt=str(capital))


def topup_preview(reader, model, snapshot, requested, stop, take, stop_budget=None, entry_capital=None,
                  stop_slippage_fraction=None):
    """Size an IOC add toward the committed campaign quantity under owned protection.

    The existing close-all stop and take stay in force; the add is funded so the
    combined isolated position still liquidates beyond that stop.
    """
    q=number(snapshot['quantity_btc'])
    if not q or snapshot['possible_entry_remainders']:
        raise Unknown('top-up requires a reconciled position without remainders')
    direction=1 if q>0 else -1
    v=_venue(reader,model,snapshot,direction)
    tick,price=v['tick'],v['price']
    stop,take=number(stop,positive=True),number(take,positive=True)
    if not all(number(v['rule']['minPrice'])<=p<=number(v['rule']['maxPrice']) for p in (stop,take,price)):
        raise Blocked('protection outside current price limits')
    entry=number(snapshot['entry'],positive=True)
    target=number(requested)
    if stop_budget is not None:
        # The whole position, not only the add, must stay inside the entry's stop budget.
        slip=number(stop_slippage_fraction) if stop_slippage_fraction is not None else None
        if slip is not None and not 0<slip<1:raise Blocked('invalid committed stop slippage')
        old_loss=(_loss_per_btc(direction,entry,stop,v['fee'],slip)
                  if slip is not None else direction*(entry-stop))
        per_unit=(_loss_per_btc(direction,price,stop,v['fee'],slip)
                  if slip is not None else direction*(price-stop))
        room=number(stop_budget)-abs(q)*old_loss
        if per_unit<=0 or room<=0:
            target=abs(q)
        else:
            target=min(target,abs(q)+room/per_unit)
    if entry_capital is not None and v['capital']<number(entry_capital):
        # A lowered budget never grows the position back toward the earlier, larger plan.
        target=min(target,number(requested)*v['capital']/number(entry_capital))
    margin=number(snapshot['isolated_wallet_usdt'])
    if target<=abs(q):
        result=dict(quantity='0',margin=margin,reason='stop_budget')
    else:
        result=_funded_quantity(v,direction,stop,take,target,q=q,entry=entry,margin=margin)
    return dict(quantity_btc=str(result['quantity']),entry_estimate=str(price),stop=str(stop),take=str(take),
                allocated_margin_usdt=str(result['margin']),constraint=result['reason'],
                side='BUY' if direction>0 else 'SELL',observed_at=v['fresh']['mark_time'],
                quote_observation=v['quote'],
                tick=str(tick),sizing_capital_usdt=str(v['capital']))
