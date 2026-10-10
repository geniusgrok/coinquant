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
# Same liquidation gap the measured path funded: 10% of mark beyond the stop.
# There is no 10% loss clamp and no 25% isolated-margin clamp. Those two caps
# cut the measured campaign sizes and the return path.
LIQUIDATION_BUFFER=D('.10')


def _loss_per_btc(direction, entry, stop, fee, slip):
    # Exit at an adverse price beyond the stop, plus both taker fees.
    return direction*(entry-stop)+entry*fee+stop*(slip+(1+slip)*fee)


def _stop_budget(reader, capital):
    fraction=getattr(reader,'loss_fraction',None)
    slip=getattr(reader,'slip_fraction',None)
    if fraction is None or slip is None:
        raise Blocked('stop loss budget and slippage must be configured before new risk')
    fraction=number(fraction,positive=True);slip=number(slip,positive=True)
    if fraction>=1 or slip>=1:
        raise Blocked('invalid loss budget or stop slippage')
    return capital*fraction,slip


def commission(reader):
    """Use the current native taker rate, cached for at most one minute."""
    now=reader.monotonic()
    cached=vars(reader).get('_commission') if isinstance(now,(int,float)) else None
    if cached and 0<=now-cached[0]<60:
        return cached[1]
    observed=reader.get('/fapi/v1/commissionRate',{'symbol':'BTCUSDT'})
    if observed.get('symbol')!='BTCUSDT':raise Unknown('commission scope')
    fee=number(observed['takerCommissionRate'])
    if not 0<=fee<D('.05'):raise Unknown('unsupported current taker commission')
    if isinstance(now,(int,float)):reader._commission=(now,fee)
    return fee


def holding_risk(snapshot, protection, fill, instrument, taker_fee=None, *,
                 paid_commission_usdt=None, realized_pnl_usdt=None, paid_funding_usdt=None,
                 loss_fraction=None, slip_fraction=None, capital_limit=None):
    """Report the campaign's entry loss budget and the strategy stop.

    Profit does not tighten that stop. Missing cost evidence never means the
    check has passed. A stop already through the mark is an exit.
    """
    q=number(snapshot['quantity_btc']);entry=number(snapshot['entry'],positive=True)
    mark=number(snapshot['mark_price'],positive=True)
    wallet=number(snapshot['wallet_usdt']);equity=number(snapshot.get('equity_usdt'))
    isolated=number(snapshot['isolated_wallet_usdt'])
    if not q or isolated<0 or equity!=wallet+q*(mark-entry):
        raise Unknown('owned holding equity or collateral unavailable')
    capital=wallet if capital_limit is None else min(wallet,number(capital_limit,positive=True))
    risk=max(D(0),min(capital,equity))
    result=dict(action='hold',reason='within_budget',stop=None,loss_ceiling_usdt=None,
                modeled_stop_loss_usdt=None,current_protected_loss_usdt=None,
                current_mark_loss_usdt=None,current_stop_budget_usdt=None,frozen_stop_budget_usdt=None,
                risk_capital_usdt=str(risk))
    # A wiped account can still be reduced. A large isolated wallet is the
    # funding the measured path used; it is not by itself a reason to flatten.
    if risk<=0:
        result.update(action='exit',reason='nonpositive_risk_capital')
        return result
    if (not isinstance(fill,dict) or not isinstance(protection,dict)
            or type(fill.get('campaign')) is not int or not fill['campaign']
            or fill['campaign']!=protection.get('campaign')
            or any(fill.get(key) is None for key in ('stop_budget','sizing_capital','stop_slippage_fraction'))):
        raise Unknown('owned campaign risk budget unavailable')
    if any(value is None for value in (taker_fee,paid_commission_usdt,realized_pnl_usdt,paid_funding_usdt)):
        raise Unknown('verified campaign costs and current commission required for holding risk')
    fee=number(taker_fee);paid_fee=number(paid_commission_usdt);funding=number(paid_funding_usdt)
    realized=number(realized_pnl_usdt)
    if not 0<=fee<D('.05') or paid_fee<0 or funding<0:
        raise Unknown('unsupported campaign holding costs')
    entry_capital=number(fill['sizing_capital'],positive=True)
    frozen=number(fill['stop_budget'],positive=True)
    slip=number(fill['stop_slippage_fraction'],positive=True)
    if (loss_fraction is None)!=(slip_fraction is None):
        raise Blocked('holding loss budget and slippage must be configured together')
    fraction=frozen/entry_capital if loss_fraction is None else number(loss_fraction,positive=True)
    if slip_fraction is not None:slip=max(slip,number(slip_fraction,positive=True))
    if fraction>=1 or slip>=1:raise Blocked('invalid holding budget or stop slippage')
    budget=risk*fraction
    direction=1 if q>0 else -1;quantity=abs(q)
    costs=paid_fee+funding-realized
    marked=costs+quantity*direction*(entry-mark)
    # The entry budget stays the campaign ceiling. Mark-to-market profit must
    # not ratchet it down: that ratchet replaced the 14-day trail and sold
    # the measured path's winners.
    saved_ceiling=protection.get('loss_ceiling_usdt')
    if saved_ceiling is not None:
        number(saved_ceiling)
    ceiling=frozen
    old_stop=number(protection['stop'],positive=True)
    exit_cost=slip+(1+slip)*fee
    old_loss=costs+quantity*(direction*(entry-old_stop)+old_stop*exit_cost)
    result.update(stop=str(old_stop),loss_ceiling_usdt=str(ceiling),
                  modeled_stop_loss_usdt=str(old_loss),current_protected_loss_usdt=str(old_loss),
                  current_mark_loss_usdt=str(marked),current_stop_budget_usdt=str(budget),
                  frozen_stop_budget_usdt=str(frozen))
    if direction*(mark-old_stop)<=0:
        result.update(action='exit',reason='risk_stop_unavailable')
    return result


def _venue(reader, model, snapshot, direction):
    info=reader.get('/fapi/v1/exchangeInfo')
    instruments=[x for x in info['symbols'] if x.get('symbol')=='BTCUSDT']
    if len(instruments)!=1:raise Unknown('missing unique instrument')
    instrument=instruments[0]
    if instrument.get('status')!='TRADING' or instrument.get('contractType')!='PERPETUAL' or instrument.get('marginAsset')!='USDT':
        raise Blocked('unsupported current instrument')
    places=instrument.get('quotePrecision')
    if type(places) is not int or not 0<=places<=8:
        raise Unknown('settlement amount precision unavailable')
    filters=[f for f in instrument['filters'] if f.get('filterType')=='PRICE_FILTER']
    if len(filters)!=1:raise Unknown('missing unique price rule')
    tick=number(filters[0]['tickSize'],positive=True)
    fee=commission(reader)
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
    if (any(fresh[k]!=snapshot[k] for k in ('wallet_usdt','quantity_btc','entry','possible_entry_remainders'))
            or fresh.get('last_fill_id')!=snapshot.get('last_fill_id')
            or any(fresh.get(k)!=snapshot.get(k) for k in ('available_usdt','isolated_wallet_usdt'))):
        raise Unknown('account changed during preflight')
    available=fresh.get('available_usdt')
    if available is None:raise Unknown('available USDT balance missing')
    wallet=number(fresh['wallet_usdt']);available=number(available)
    if not 0<=available<=wallet:raise Unknown('unsupported available collateral')
    equity=fresh.get('equity_usdt')
    if equity is None:raise Unknown('account equity missing for stop budget')
    equity=number(equity,positive=True)
    mark=number(fresh['mark_price'],positive=True)
    if equity!=wallet+number(fresh['quantity_btc'])*(mark-number(fresh['entry'])):
        raise Unknown('account equity disagrees with the observed position')
    if abs(int(reader.clock()*1000)-stamp)>15000:raise Unknown('book expired during account refresh')
    raw_price=(asks[0][0]*D('1.001') if direction>0 else bids[0][0]*D('.999'))
    price=(floor_step(raw_price,tick) if direction>0 else (raw_price/tick).to_integral_value(rounding=ROUND_CEILING)*tick)
    capacity=sum((q for p,q in (asks if direction>0 else bids) if (p<=price if direction>0 else p>=price)),D(0))*BOOK_PARTICIPATION
    limit=getattr(reader,'capital_limit',None)
    capital=wallet if limit is None else min(wallet,limit)
    return dict(instrument=instrument,rule=filters[0],tick=tick,fee=fee,cap=cap,mmr=mmr,fresh=fresh,
                wallet=wallet,available=available,price=price,capacity=capacity,
                quote=dict(observed_at_ms=stamp,best_bid=str(bids[0][0]),best_ask=str(asks[0][0]),
                           visible_limit_depth_btc=str(capacity/BOOK_PARTICIPATION),
                           participation_fraction=str(BOOK_PARTICIPATION)),
                capital=capital,equity=equity,risk_capital=min(capital,equity),mark=mark,
                margin_step=D(1).scaleb(-places))


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
    boundary=stop-direction*mark*LIQUIDATION_BUFFER
    if boundary<=0:
        result['reason']='gap_boundary';return result

    def funded(amount):
        quantity=old+amount
        average=(old*entry+amount*price)/quantity
        total=direction*quantity
        entry_fee=amount*price*fee
        # The exchange also moves the add's initial margin on its fill. Existing
        # excess collateral cannot replace that automatic additional transfer.
        required=max(margin+amount*price/20,quantity*average/20,
                     total*average-(total-quantity*(mmr+fee))*boundary)
        reserve=quantity*max(price,mark)*(D('.01')+fee)
        # Binance's order-cost check also reserves an adverse entry-to-mark
        # difference; the IOC limit may diverge from mark in a dislocated book.
        open_loss=amount*max(D(0),direction*(price-mark))
        # Entry commissions and the new fill's mark-to-entry loss immediately
        # reduce the capital the holding guard will observe after this fill.
        # Fund the liquidation gap from the wallet. Do not refuse the order
        # because isolated margin would exceed a quarter of capital: that cap
        # was what cut the measured positions down.
        if (required+reserve+entry_fee+open_loss>v['capital']
                or required-margin+reserve+entry_fee+open_loss>v['available']):
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
        reason='margin_or_funding_cap'
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
    # Flat entry equity equals the wallet. A trial capital ceiling applies to
    # both cash funding and the equity amount from which loss may be budgeted.
    budget,slip_fraction=_stop_budget(reader,v['risk_capital'])
    if opportunity is model.macro_opportunity:
        # The macro campaign has a 3% equity-to-stop loss ceiling.
        if price<=stop:raise Blocked('macro stop must be below executable entry')
        budget=min(budget,v['risk_capital']*MACRO_STOP_BUDGET)
    per_unit=_loss_per_btc(direction,price,stop,v['fee'],slip_fraction)
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
                stop_budget_usdt=str(budget),stop_slippage_fraction=str(slip_fraction),
                account_equity_usdt=str(v['equity']),stop_budget_capital_usdt=str(v['risk_capital']),
                sizing_capital_usdt=str(capital))


def topup_preview(reader, model, snapshot, requested, stop, take, stop_budget=None, entry_capital=None,
                  stop_slippage_fraction=None, *, paid_commission_usdt=None, realized_pnl_usdt=None,
                  paid_funding_usdt=None, loss_ceiling_usdt=None):
    """Size an IOC add toward the committed campaign quantity under owned protection.

    The existing close-all stop and take stay in force; the add is funded so the
    combined isolated position still liquidates beyond that stop.
    """
    q=number(snapshot['quantity_btc'])
    if not q or snapshot['possible_entry_remainders']:
        raise Unknown('top-up requires a reconciled position without remainders')
    if stop_budget is None or stop_slippage_fraction is None:
        raise Blocked('committed stop budget and slippage required before an add')
    if paid_commission_usdt is None or realized_pnl_usdt is None or paid_funding_usdt is None:
        raise Unknown('verified campaign commissions, realized PnL and paid funding required before an add')
    paid_fee=number(paid_commission_usdt);realized_pnl=number(realized_pnl_usdt)
    funding=number(paid_funding_usdt)
    if paid_fee<0 or funding<0:raise Unknown('unsupported negative campaign cost')
    direction=1 if q>0 else -1
    v=_venue(reader,model,snapshot,direction)
    tick,price=v['tick'],v['price']
    stop,take=number(stop,positive=True),number(take,positive=True)
    if not all(number(v['rule']['minPrice'])<=p<=number(v['rule']['maxPrice']) for p in (stop,take,price)):
        raise Blocked('protection outside current price limits')
    entry=number(snapshot['entry'],positive=True)
    target=number(requested)
    current_budget,current_slip=_stop_budget(reader,v['risk_capital'])
    budget=number(stop_budget,positive=True)
    # A saved profit-lock ceiling must not shrink later adds. The entry budget
    # is the campaign limit; the strategy stop, not a ratcheted ceiling, exits.
    ceiling=budget
    slip=number(stop_slippage_fraction,positive=True)
    if slip>=1:raise Blocked('invalid committed stop slippage')
    slip=max(slip,current_slip)
    # Native commissions and realized PnL remain cumulative after reductions.
    # Only the still-unpaid exit is estimated at today's commission rate.
    exit_cost=stop*(slip+(1+slip)*v['fee'])
    old_loss=direction*(entry-stop)+exit_cost
    per_unit=_loss_per_btc(direction,price,stop,v['fee'],slip)
    # Fresh equity already includes paid costs, realized and unrealized PnL.
    # Its remaining risk is mark-to-stop plus the still-unpaid exit cost.
    marked_loss=direction*(v['mark']-stop)+exit_cost
    room=min(ceiling-paid_fee-funding+realized_pnl-abs(q)*old_loss,
             current_budget-abs(q)*marked_loss)
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
                stop_budget_usdt=str(budget),stop_slippage_fraction=str(slip),
                loss_ceiling_usdt=str(ceiling),
                paid_funding_usdt=str(funding),
                current_equity_stop_budget_usdt=str(current_budget),
                account_equity_usdt=str(v['equity']),stop_budget_capital_usdt=str(v['risk_capital']),
                tick=str(tick),sizing_capital_usdt=str(v['capital']))


def limit_matches(reader, direction, limit_price, tick, *, quote_observation=None, quantity=None,
                  completed_through=None):
    """Recheck the priced book and its executable depth immediately before send."""
    book=reader.get('/fapi/v1/depth',{'symbol':'BTCUSDT','limit':100})
    stamp=book.get('E')
    if type(stamp) is not int or abs(int(reader.clock()*1000)-stamp)>15000:
        raise Unknown('stale order book')
    if completed_through is not None:
        if type(completed_through) is not int or completed_through%14400000:
            raise Unknown('completed model time unavailable for final quote')
        if stamp//14400000*14400000!=completed_through:
            return False
    try:
        bids=[(number(p,positive=True),number(q,positive=True)) for p,q in book['bids']]
        asks=[(number(p,positive=True),number(q,positive=True)) for p,q in book['asks']]
    except (TypeError,KeyError):
        raise Unknown('invalid order book') from None
    if (not bids or not asks or bids[0][0]>=asks[0][0]
            or any(a[0]>=b[0] for a,b in zip(asks,asks[1:]))
            or any(a[0]<=b[0] for a,b in zip(bids,bids[1:]))):
        raise Unknown('invalid order book ordering')
    tick=number(tick,positive=True)
    limit=number(limit_price,positive=True)
    if floor_step(limit,tick)!=limit:return False
    raw=(asks[0][0]*D('1.001') if direction>0 else bids[0][0]*D('.999'))
    price=(floor_step(raw,tick) if direction>0 else (raw/tick).to_integral_value(rounding=ROUND_CEILING)*tick)
    # A moved book can still fill the funded limit. Reject only when that
    # limit is outside the fresh allowance. Do not reprice, and do not count
    # depth beyond the original limit.
    if (limit>price if direction>0 else limit<price):return False
    depth=sum((q for p,q in (asks if direction>0 else bids)
               if (p<=limit if direction>0 else p>=limit)),D(0))
    return quantity is None or number(quantity,positive=True)<=depth*BOOK_PARTICIPATION
