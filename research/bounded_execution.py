"""One fixed five-minute entry proxy, sharing the existing funded account arithmetic.

No exchange sender, daemon or second account ledger exists here. Slices are
synchronous IOC-style fill/protection *assumptions*. Readiness guards and durable
client identities are testable, but are not native entry/protection qualification.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from decimal import Decimal as D
from typing import Mapping

from pancakequant.linear_account import Account, FEE
from pancakequant.linear_sizing import funded_target
from pancakequant.state import client_id
from pancakequant.types import ZERO, serial

MINUTE = 60_000
WINDOW = 5 * MINUTE
PARTICIPATION = D('.01')
RISK_SCALES = (D('3.6'), D('4.8'), D('6.0'))


def risk_scale(value) -> D:
    """Only the preregistered research budgets, never an exchange leverage setting."""
    try:
        result = D(str(value))
        if not result.is_finite() or result not in RISK_SCALES:
            raise ValueError('risk scale must be one of 3.6, 4.8, 6.0')
    except ArithmeticError as exc:
        raise ValueError('invalid research risk scale') from exc
    return result



def exit_fill(reference: D, quantity: D, previous_hour_quote: D,
              slippage: D, spread: D) -> tuple[D, dict]:
    """Pre-registered adverse capacity stress; not calibrated historical depth."""
    if min(reference, previous_hour_quote) <= 0 or quantity == 0:
        raise ValueError('positive exit price, prior volume and nonzero quantity required')
    capacity = previous_hour_quote / 60 * PARTICIPATION
    utilization = abs(quantity) * reference / capacity
    extra = slippage * max(ZERO, utilization - 1)
    cost = slippage + spread / 2 + extra
    if not ZERO <= cost < 1:
        raise ValueError('exit pressure exceeds interpretable price range')
    price = reference * (1 - cost if quantity > 0 else 1 + cost)
    return price, dict(reference=str(reference), quantity=str(quantity),
                       prior_hour_quote=str(previous_hour_quote),
                       minute_capacity_usdt=str(capacity), capacity_ratio=str(utilization),
                       base_slippage=str(slippage), spread=str(spread),
                       extra_impact_fraction=str(extra), extra_impact_usdt=str(abs(quantity)*reference*extra),
                       fill_price=str(price), fee_usdt=str(abs(quantity)*price*FEE))


@dataclass
class BoundedEntry:
    call_time: int
    campaign: int
    start: int
    deadline: int
    maximum: D
    raw_target: D
    risk_budget: D
    original_price: D
    original_quote: D
    stop: D
    take: D
    entry_limit: D | None
    previous_hour_quote: D
    slippage: D
    spread: D
    starting_fees: D
    starting_funding: D
    terminal_reason: str = ''
    finished_at: int | None = None
    unresolved: bool = False
    attempted: list[int] = field(default_factory=list)
    filled: D = ZERO
    first_fill: int | None = None
    last_fill: int | None = None
    liquidity_limited: bool = False
    risk_scale: D = D('3.6')

    @property
    def identity(self) -> str:
        return client_id(f'research:binance:BTCUSDT:L{self.risk_scale:.1f}', self.call_time, 'bounded-entry')

    @classmethod
    def freeze(cls, account: Account, call_time: int, campaign: int, fraction: D,
               quote: D, mark: D, stop: D, take: D, previous_hour_quote: D,
               instrument: dict | None, slippage: D, spread: D,
               entry_limit: D | None = None, *, stress: bool = False,
               budget: D = D('3.6')) -> BoundedEntry:
        selected_budget = risk_scale(budget)
        if account.q or account.wallet <= 0:
            raise ValueError('mother intent requires the reconciled flat account')
        price = quote * (1 + slippage + spread / 2)
        trial = replace(account)
        change = funded_target(trial, 1, fraction, price, mark, stop, take,
                               D('Infinity'), instrument, intended_add=True)
        maximum = abs(trial.q)
        original_stop_fill = stop * (1 - slippage - spread / 2)
        budget = maximum * (price - original_stop_fill + FEE*(price + original_stop_fill))
        start = call_time + MINUTE * (2 if stress else 1)
        result = cls(call_time, campaign, start, start + WINDOW, maximum,
                     D(change['requested']), budget, price, quote, stop, take, entry_limit,
                     previous_hour_quote, slippage, spread, account.fees, account.funding,
                     risk_scale=selected_budget)
        if not maximum:
            result.finish('unfunded_parent:' + change['reason'], call_time)
        return result

    def finish(self, reason: str, now: int, *, unresolved: bool = False) -> None:
        """Stop new risk. Unknown pending orders are NOT declared safely terminal."""
        if not self.terminal_reason:
            self.terminal_reason, self.finished_at = reason, now
        self.unresolved |= unresolved

    def available(self, now: int) -> bool:
        if not self.terminal_reason and now >= self.deadline:
            self.finish('deadline', self.deadline)
        return not self.terminal_reason

    def loss_at_stop(self, account: Account) -> D:
        if not account.q:
            return ZERO
        stop_price, _ = exit_fill(self.stop, account.q, self.previous_hour_quote,
                                  self.slippage, self.spread)
        return max(ZERO, account.q*(account.entry-stop_price)
                   + account.fees-self.starting_fees + abs(account.q)*stop_price*FEE
                   + account.funding-self.starting_funding)

    def attempt(self, now: int, account: Account, quote: D, mark: D,
                minute_quotes: Mapping[int, D], instrument: dict | None, *,
                balance_known: bool = True, protection_confirmed: bool = True,
                pending_child: bool = False, outcome_known: bool = True) -> dict:
        """One terminal-fill proxy step. ACK/unknown readiness never changes cash."""
        record = dict(parent_id=self.identity, child_id=client_id(self.identity, now, 'entry'),
                      call_time=self.call_time, time=now, event='', accepted='0',
                      reason='outside_window', requested=str(self.maximum),
                      raw_target=str(self.raw_target), maximum=str(self.maximum),
                      risk_budget=str(self.risk_budget))
        if not self.available(now) or now < self.start or (now-self.start) % MINUTE:
            return record
        if now in self.attempted:
            record['reason'] = 'duplicate_step'
            return record
        self.attempted.append(now)
        if not balance_known or pending_child or not outcome_known or (account.q and not protection_confirmed):
            self.finish('unresolved_readiness', now, unresolved=True)
            record['reason'] = self.terminal_reason
            return record
        if account.q < 0 or abs(account.q) != self.filled:
            self.finish('position_changed', now, unresolved=True)
            record['reason'] = self.terminal_reason
            return record
        price = quote * (1 + self.slippage + self.spread / 2)
        if not self.stop < min(price, mark) <= max(price, mark) < self.take or (self.entry_limit is not None and price >= self.entry_limit):
            self.finish('quote_invalidated', now)
            record['reason'] = self.terminal_reason
            return record
        # A minute ending at now-60s is first observable now: full 60s publication lag.
        volume_time = now - 2*MINUTE
        if volume_time not in minute_quotes:
            raise ValueError(f'missing published minute volume at {volume_time}')
        minute_quote = D(minute_quotes[volume_time])
        if not minute_quote.is_finite() or minute_quote < 0:
            raise ValueError('invalid completed minute quote volume')
        capacity = min(self.previous_hour_quote/60, minute_quote)*PARTICIPATION/price
        record.update(quote=str(quote), mark=str(mark), price=str(price),
                      volume_minute=volume_time, volume_available_at=volume_time+2*MINUTE,
                      completed_minute_quote=str(minute_quote), capacity=str(capacity))

        def preview(cap: D):
            trial = replace(account)
            change = funded_target(trial, 1, ZERO, price, mark, self.stop, self.take,
                                   cap, instrument, intended_add=True, target_quantity=self.maximum)
            return trial, change

        trial, change = preview(capacity)
        risk_limited = False
        if change['amount'] and self.loss_at_stop(trial) > self.risk_budget:
            risk_limited = True
            low, high = ZERO, D(change['amount'])
            for _ in range(48):
                middle = (low+high)/2
                test, _ = preview(middle)
                if self.loss_at_stop(test) <= self.risk_budget:
                    low = middle
                else:
                    high = middle
            trial, change = preview(low)
        self.liquidity_limited |= change['reason'] == 'liquidity_cap'
        record.update(accepted=change['accepted'], event=change['event'],
                      reason='stop_budget' if risk_limited else change['reason'],
                      stop_risk=str(self.loss_at_stop(trial)))
        amount = D(change['amount'])
        if amount:
            if (trial.q > self.maximum or self.loss_at_stop(trial) > self.risk_budget
                    or trial.q < account.q or trial.margin > trial.wallet):
                raise ValueError('child violates frozen quantity, risk or wallet bounds')
            # Same existing account object. The model assumes IOC fill + protection
            # confirmation at this boundary, NOT a native response or ACK.
            account.__dict__.update(trial.__dict__)
            self.filled = abs(account.q)
            if self.first_fill is None:
                self.first_fill = now
            self.last_fill = now
            record.update(quantity_after=str(account.q), entry_price=str(account.entry),
                          margin=str(account.margin), free_wallet=str(account.wallet-account.margin),
                          entry_fee=str(amount*price*FEE), delay_price_cost=str(amount*(price-self.original_price)))
            if self.filled == self.maximum:
                self.finish('target_filled', now)
        return record

    def record(self) -> dict:
        value = serial(asdict(self))
        value.update(parent_id=self.identity, remainder=str(self.maximum-self.filled),
                     fill_fraction=str(self.filled/self.maximum) if self.maximum else None,
                     build_ms=self.last_fill-self.start if self.last_fill is not None else None,
                     decision_to_last_fill_ms=self.last_fill-self.call_time if self.last_fill is not None else None)
        return value

    @classmethod
    def restore(cls, record: dict) -> BoundedEntry:
        """Use with the existing State meta store; never create a fresh deadline."""
        from dataclasses import fields
        values = {f.name: record[f.name] for f in fields(cls) if f.name != 'risk_scale'}
        values['risk_scale'] = risk_scale(record.get('risk_scale', '3.6'))
        for name in ('maximum', 'raw_target', 'risk_budget', 'original_price', 'original_quote',
                     'stop', 'take', 'previous_hour_quote', 'slippage', 'spread',
                     'starting_fees', 'starting_funding', 'filled'):
            values[name] = D(values[name])
            if not values[name].is_finite():
                raise ValueError('nonfinite restored entry state')
        if values['entry_limit'] is not None:
            values['entry_limit'] = D(values['entry_limit'])
            if not values['entry_limit'].is_finite() or values['entry_limit'] <= 0:
                raise ValueError('invalid restored entry limit')
        result = cls(**values)
        if (result.start-result.call_time not in (MINUTE, 2*MINUTE)
                or result.deadline != result.start+WINDOW
                or not ZERO <= result.filled <= result.maximum
                or min(result.maximum,result.risk_budget,result.slippage,result.spread)<ZERO
                or min(result.stop,result.original_quote,result.previous_hour_quote)<=0
                or result.stop>=result.take
                or len(set(result.attempted))!=len(result.attempted)
                or any(type(t) is not int or t<result.start or t>=result.deadline or (t-result.start)%MINUTE for t in result.attempted)
                or record['parent_id'] != result.identity):
            raise ValueError('invalid bounded entry identity, quantity or deadline')
        return result


@dataclass(frozen=True)
class ExecutionStudy:
    """Only the preregistered control/candidate and one adverse joint stress."""
    sliced: bool
    stress: bool
    refined_hours: frozenset[int]
    minute_quotes: Mapping[int, D]
    risk_scale: D = D('3.6')

    def __post_init__(self):
        object.__setattr__(self, 'risk_scale', risk_scale(self.risk_scale))

    def configuration(self) -> dict:
        return dict(mode='five_minute' if self.sliced else 'instant_control', risk_scale=str(self.risk_scale),
                    fixed_window_seconds=300, decision_delay_seconds=(120 if self.stress else 60) if self.sliced else 0,
                    volume_publication_lag_seconds=60, participation='0.01',
                    cost_multiplier=2 if self.stress else 1,
                    exit_impact='linear_prior_hour_capacity_proxy', native_execution_verified=False)
