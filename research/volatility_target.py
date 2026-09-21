"""Research-only target inventory; no exchange writes or production promotion."""
from dataclasses import replace
from decimal import Decimal as D
from pancakequant.types import ZERO, floor_step
from pancakequant.binance import market_quantity
from research.linear_replay import FEE, MMR, LOT

GAP = D('.10')
FUNDING_RESERVE = D('.01')


def target_fraction(returns, friction, absence_days=7):
    if len(returns) < 20:
        return ZERO
    rms = (sum((r*r for r in list(returns)[-20:]), ZERO)/20).sqrt()
    return D('.20')/(D('2.33')*rms*D(absence_days).sqrt()+GAP+FUNDING_RESERVE+2*(FEE+friction))


def funded_target(account, direction, fraction, price, mark, sl, tp, capacity, instrument, intended_add=None):
    """Atomically model a filled target delta after funding/protection preflight.

    Allocation is market-volatility based, never inverse stop-distance. Capital
    constraints may shrink it. Existing allocated margin is retained on adds.
    Native write ordering remains unverified, so this is an economic diagnostic.
    """
    if direction not in (-1, 1) or min(price, mark, sl, tp) <= 0 or fraction < 0:
        raise ValueError('invalid target')
    if account.q and account.q*direction <= 0:
        raise ValueError('close opposite position first')
    old = abs(account.q)
    requested = max(ZERO, account.equity(mark)*fraction/max(price, mark))
    raw = min(requested, D('1000000')/max(price, mark))
    delta = min(abs(raw-old), capacity)
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
        fee = amount*price*FEE
        required = max(account.margin, quantity*entry/20,
                       q*entry-(q-quantity*(MMR+FEE))*boundary)
        reserve = quantity*max(price, mark)*(FUNDING_RESERVE+FEE)
        if required+reserve+fee > account.wallet:
            return None
        trial = replace(account, wallet=account.wallet-fee, q=q, entry=entry,
                        margin=required, sl=sl, tp=tp, fees=account.fees+fee)
        liq = trial.liquidation()
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
        result['reason'] = 'target' if raw == requested else 'notional_cap'
    if trial is None:
        result['reason'] = 'insufficient_funded_minimum'; return result
    account.__dict__.update(trial.__dict__)
    result.update(accepted=str(delta), event='entry' if not old else 'rebalance_add', amount=delta)
    return result


def channel_position(window):
    if len(window)<21:return 0,ZERO
    prior=list(window)[-21:-1];close=window[-1][2]
    high=max(r[0] for r in prior);low=min(r[1] for r in prior)
    if high<=low:return 0,ZERO
    score=max(D(-1),min(D(1),(2*close-high-low)/(high-low)))
    return (1 if score>0 else -1 if score<0 else 0),abs(score)
