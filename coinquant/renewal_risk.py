"""One reduce-only planner for a permitted H60 campaign renewal."""
from dataclasses import replace
from decimal import Decimal as D

from .capital import capital_surplus, gap_margin
from .linear_account import FEE, LOT
from .types import ZERO, floor_step
from .binance import market_quantity


def plan_renewal_reduction(account, budget, reference, mark, anchor_mark,
                           instrument, exit_price, stop_fill, *, risk_fraction):
    """Find the largest remaining long quantity meeting both frozen limits.

    Planning is read-only. `exit_price` models the immediate quantity reduction;
    `stop_fill` models the future protective exit using the same execution rules.
    """
    if risk_fraction is None:
        raise ValueError('missing campaign entry-risk fraction')
    fraction = D(risk_fraction)
    if not fraction.is_finite() or fraction <= 0:
        raise ValueError('invalid campaign entry-risk fraction')
    if account.q <= 0 or min(D(reference), D(mark), D(anchor_mark)) <= 0:
        raise ValueError('renewal sizing requires a protected long position')

    original = account.q

    def preview(remaining):
        amount = original - remaining
        trial = replace(account)
        price = D(exit_price(amount)) if amount else D(reference)
        if amount:
            trial.close(amount, price)
        if remaining:
            required, _ = gap_margin(trial, anchor_mark)
            trial.margin = max(trial.margin, required)
            capital_after = capital_surplus(trial, budget, reference, mark, anchor_mark)
            stop = D(stop_fill(remaining))
            parts = budget.reserve_components(remaining, trial.entry, reference, mark)
            funding = parts['funding']
            future_loss = max(ZERO, remaining*(D(mark)-stop) + remaining*stop*FEE + funding)
        else:
            capital_after = trial.wallet - budget.pending_reserve
            stop = ZERO
            funding = ZERO
            future_loss = ZERO
        equity_after = trial.equity(mark)
        risk_limit = fraction*equity_after
        safe = capital_after >= D('-1e-18') and future_loss <= risk_limit
        return dict(trial=trial, price=price, capital_after=capital_after,
                    equity_after=equity_after, stop_fill=stop,
                    funding_reserve=funding, future_loss=future_loss,
                    risk_limit=risk_limit, safe=safe)

    before_capital = capital_surplus(account, budget, reference, mark, anchor_mark)
    initial = preview(original)
    solver='no_change'
    if initial['safe']:
        remaining = original
        chosen = initial
    elif not budget.valid:
        remaining=ZERO
        chosen=preview(ZERO)
        if not chosen['safe']:
            raise ValueError('no payable reduce-only quantity meets capital and risk limits')
        solver='invalid_funding_budget_full_exit'
    else:
        zero = preview(ZERO)
        if not zero['safe']:
            raise ValueError('no payable reduce-only quantity meets capital and risk limits')
        solver='descending_market_quantity_scan'
        remaining=market_quantity(original,reference,instrument) if instrument else floor_step(original,LOT)
        chosen=None
        while remaining>0:
            candidate=preview(remaining)
            if candidate['safe']:
                chosen=candidate
                break
            next_max=max(ZERO,remaining-LOT)
            next_remaining=(market_quantity(next_max,reference,instrument)
                if instrument else floor_step(next_max,LOT))
            if next_remaining>=remaining:
                raise ValueError('quantity scan failed to make reduce-only progress')
            remaining=next_remaining
        if chosen is None:
            remaining=ZERO
            chosen=zero
        amount = original - remaining
        if amount and instrument and market_quantity(amount, chosen['price'], instrument) != amount:
            remaining = ZERO
            chosen = zero
    amount = original - remaining
    if amount < 0 or remaining > original:
        raise ValueError('renewal plan attempted to increase exposure')
    return dict(amount=amount, remaining=remaining, price=chosen['price'],
                capital_before=before_capital, capital_after=chosen['capital_after'],
                future_loss=chosen['future_loss'], risk_limit=chosen['risk_limit'],
                equity_after=chosen['equity_after'], stop_fill=chosen['stop_fill'],
                funding_reserve=chosen['funding_reserve'],
                margin_after=chosen['trial'].margin, feasible=chosen['safe'],solver=solver)
