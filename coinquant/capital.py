"""Finite offline capital planning; never an exchange action or a price forecast.

Inputs must be settled and published before as_of. Seven days is a planning
horizon, not a promise of an invocation or an unlimited solvency guarantee.
"""
from dataclasses import asdict, dataclass, replace
from decimal import Decimal as D
from bisect import bisect_right
import hashlib
import json

from .linear_account import FEE, MMR, LOT
from .types import ZERO, floor_step, serial
from .binance import market_quantity

HOUR = 3_600_000
DAY = 24 * HOUR
from .linear_sizing import GAP, FUNDING_RESERVE as FUNDING_FLOOR


@dataclass(frozen=True)
class CapitalBudget:
    as_of: int
    latest_settlement: int | None
    adverse_rate: D
    history_sha256: str
    previous_hour_quote: D
    slippage: D
    spread: D
    pending_reserve: D = ZERO
    valid: bool = True
    reason: str = ''
    horizon_days: int = 7

    @classmethod
    def from_history(cls, as_of, history, previous_hour_quote, slippage, spread,
                     *, direction=1, pending_reserve=ZERO, times=None):
        if direction not in (-1, 1):
            raise ValueError('capital direction must be signed')
        cutoff = as_of - 60_000
        keys = sorted(history) if times is None else times
        begin = bisect_right(keys, cutoff - 7*DAY)
        end = bisect_right(keys, cutoff)
        selected = [(t, D(history[t])) for t in keys[begin:end]]
        if any(not r.is_finite() for _, r in selected):
            raise ValueError('nonfinite settled funding')
        latest = selected[-1][0] if selected else None
        reason = ''
        if latest is None:
            reason = 'no_published_settlement'
        elif as_of - latest > 8*HOUR + 60_000:
            reason = 'stale_funding'
        elif any(b//(8*HOUR) - a//(8*HOUR) != 1
                 for (a, _), (b, _) in zip(selected, selected[1:])):
            reason = 'funding_slot_gap'
        values = tuple(map(D, (previous_hour_quote, slippage, spread, pending_reserve)))
        if (not all(x.is_finite() for x in values) or values[0] <= 0
                or min(values[1:]) < 0):
            raise ValueError('invalid known capital/cost inputs')
        rate = max((max(ZERO, direction*r) for _, r in selected), default=ZERO)
        digest = hashlib.sha256(json.dumps([(t, str(r)) for t, r in selected]).encode()).hexdigest()
        return cls(as_of, latest, rate, digest, *values, not reason, reason)

    def reserve(self, quantity, entry, reference, mark):
        """Spendable wallet needed in addition to segregated GAP collateral."""
        quantity = abs(D(quantity))
        if not self.valid:
            return D('Infinity') if quantity else self.pending_reserve
        if min(entry, reference, mark) <= 0 or quantity < 0:
            raise ValueError('invalid capital reference')
        funding_price = max(entry, reference, mark)*(1+GAP)
        funding_fraction = max(FUNDING_FLOOR, self.adverse_rate * 3*self.horizon_days)
        capacity = self.previous_hour_quote/60 * D('.01')
        impact = self.slippage * max(D(1), quantity*reference/capacity)
        friction = impact + self.spread/2
        # Fees on the adverse higher exit notional are an explicit conservative
        # reserve; actual long exit fees still use its actual lower fill price.
        exit_cost = quantity*reference*(friction + FEE*(1+friction))
        return quantity*funding_price*funding_fraction + exit_cost + self.pending_reserve

    def record(self):
        return serial(asdict(self))

    @classmethod
    def restore(cls, value):
        values = dict(value)
        for name in ('adverse_rate', 'previous_hour_quote', 'slippage', 'spread', 'pending_reserve'):
            values[name] = D(values[name])
        result = cls(**values)
        if result.horizon_days != 7 or min(result.adverse_rate, result.slippage, result.spread, result.pending_reserve) < 0:
            raise ValueError('invalid capital state')
        return result


def gap_margin(account, anchor_mark):
    """Original confirmed-fill anchor, not the new mark or a closer stop."""
    boundary = account.sl - (1 if account.q > 0 else -1)*anchor_mark*GAP
    if boundary <= 0:
        raise ValueError('nonpositive original gap boundary')
    required = max(abs(account.q)*account.entry/20,
                   account.q*account.entry-(account.q-abs(account.q)*(MMR+FEE))*boundary)
    return required, boundary


def capital_surplus(account, budget, reference, mark, anchor_mark):
    if not account.q:
        return account.wallet-budget.pending_reserve
    required, _ = gap_margin(account, anchor_mark)
    return account.wallet-max(required, account.margin)-budget.reserve(account.q, account.entry, reference, mark)


def sustain_position(account, budget, reference, mark, anchor_mark, instrument, exit_price):
    """At a real invocation only, minimally reduce; never replenish exposure.

    exit_price is the same actual quantity-dependent price used by the caller's
    immediate exit. Partial realized PnL and fees enter this same Account.
    """
    if not account.q:
        return dict(amount=ZERO, price=ZERO, reason='flat', before=ZERO, after=ZERO)
    before = capital_surplus(account, budget, reference, mark, anchor_mark)
    if before >= 0:
        return dict(amount=ZERO, price=ZERO, reason='sufficient', before=before, after=before)
    original = abs(account.q)

    def preview(remaining):
        trial = replace(account)
        amount = original - remaining
        price = exit_price(amount if account.q > 0 else -amount) if amount else reference
        if amount:
            trial.close(amount, price)
        if remaining:
            required, _ = gap_margin(trial, anchor_mark)
            trial.margin = max(trial.margin, required)
            surplus = capital_surplus(trial, budget, reference, mark, anchor_mark)
        else:
            surplus = trial.wallet-budget.pending_reserve
        return trial, price, surplus

    low, high = ZERO, original
    if budget.valid:
        for _ in range(64):
            middle = (low+high)/2
            if preview(middle)[2] >= 0:
                low = middle
            else:
                high = middle
    remaining = market_quantity(low, reference, instrument) if instrument else floor_step(low, LOT)
    trial, price, after = preview(remaining)
    amount = original - remaining
    # A sub-minimum market reduction is rounded in the risk-reducing direction,
    # or closed entirely, never skipped to keep an unsafe position.
    if instrument and amount and market_quantity(amount, price, instrument) != amount:
        remaining = ZERO
        trial, price, after = preview(remaining)
        amount = original
    if after < D('-1e-18'):
        raise ValueError('capital reduction cannot restore payable wallet')
    account.__dict__.update(trial.__dict__)
    return dict(amount=amount, price=price, reason='capital_reduce' if remaining else 'capital_exit', before=before, after=after)
