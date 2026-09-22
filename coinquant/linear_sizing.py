"""Shared pure target sizing. Native writes and historical rules are not qualified."""
from dataclasses import replace
from decimal import Decimal as D
from coinquant.types import ZERO, floor_step
from coinquant.binance import market_quantity
from .linear_account import FEE, MMR, LOT

GAP = D('.10')
FUNDING_RESERVE = D('.01')


def target_fraction(returns, friction, absence_days=7):
    if len(returns) < 20:
        return ZERO
    rms = (sum((r*r for r in list(returns)[-20:]), ZERO)/20).sqrt()
    return D('.20')/(D('2.33')*rms*D(absence_days).sqrt()+GAP+FUNDING_RESERVE+2*(FEE+friction))


def funded_target(account, direction, fraction, price, mark, sl, tp, capacity, instrument, intended_add=None, *, fee=FEE, maintenance=MMR, notional_limit=D('1000000'), target_quantity=None, capital=None):
    """Atomically model a filled target delta after funding/protection preflight.

    Allocation is market-volatility based, never inverse stop-distance. Capital
    constraints may shrink it. Existing allocated margin is retained on adds.
    Native write ordering remains unverified, so this is an economic diagnostic.
    """
    if direction not in (-1, 1) or min(price, mark, sl, tp) <= 0 or fraction < 0:
        raise ValueError('invalid target')
    if account.q and account.q*direction <= 0:
        raise ValueError('close opposite position first')
    fee,maintenance,notional_limit=D(fee),D(maintenance),D(notional_limit)
    if not (fee.is_finite() and maintenance.is_finite() and notional_limit.is_finite() and 0<=fee<D('.05') and 0<=maintenance<D('.05') and notional_limit>0):
        raise ValueError('invalid economic preflight')
    if account.q and fee!=FEE:raise ValueError('non-default fee requires native reduction accounting')
    old = abs(account.q)
    requested = (max(ZERO, account.equity(mark)*fraction/max(price, mark))
                 if target_quantity is None else D(target_quantity))
    if not requested.is_finite() or requested < ZERO:
        raise ValueError('invalid fixed quantity target')
    raw = min(requested, notional_limit/max(price, mark))
    delta = min(abs(raw-old), capacity)
    size_reason = ('liquidity_cap' if capacity < abs(raw-old) else
                   'notional_cap' if raw < requested else 'target')
    delta = market_quantity(delta, price, instrument) if instrument else floor_step(delta, LOT)
    result = dict(requested=str(requested), accepted='0', reason='minimum_or_unchanged', event='', amount=ZERO)
    if not delta:
        return result
    if intended_add is not None and (raw>old)!=intended_add:
        result['reason']='quote_side_changed';return result
    if raw < old:
        delta = min(delta, old)
        account.close(delta, price)
        result.update(accepted=str(delta), reason='target', event='rebalance_reduce', amount=delta)
        return result
    if not (sl < min(price, mark) <= max(price, mark) < tp if direction > 0
            else tp < min(price, mark) <= max(price, mark) < sl):
        result['reason'] = 'protection'; return result

    boundary = sl-direction*mark*GAP
    if boundary <= 0:
        result['reason'] = 'gap_boundary'; return result

    def preview(amount):
        quantity = old+amount
        entry = (old*account.entry+amount*price)/quantity
        q = direction*quantity
        entry_fee = amount*price*fee
        required = max(account.margin, quantity*entry/20,
                       q*entry-(q-quantity*(maintenance+fee))*boundary)
        reserve = (quantity*max(price, mark)*(FUNDING_RESERVE+fee) if capital is None
                   else capital.reserve(quantity, entry, price, mark))
        if required+reserve+entry_fee > account.wallet:
            return None
        trial = replace(account, wallet=account.wallet-entry_fee, q=q, entry=entry,
                        margin=required, sl=sl, tp=tp, fees=account.fees+entry_fee)
        liq = trial.liquidation(maintenance,fee)
        if not (liq < sl < mark if direction > 0 else mark < sl < liq):
            return None
        return trial

    trial = preview(delta)
    if trial is None:
        low, high = ZERO, delta
        for _ in range(48):
            middle = (low+high)/2
            if preview(middle) is None: high = middle
            else: low = middle
        delta = market_quantity(low, price, instrument) if instrument else floor_step(low, LOT)
        trial = preview(delta) if delta else None
        result['reason'] = 'funding_cap'
    else:
        result['reason'] = size_reason
    if trial is None:
        result['reason'] = 'insufficient_funded_minimum'; return result
    account.__dict__.update(trial.__dict__)
    result.update(accepted=str(delta), event='entry' if not old else 'rebalance_add', amount=delta)
    return result
