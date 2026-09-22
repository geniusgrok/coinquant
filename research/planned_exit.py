"""Fixed in-invocation reduce-only execution proxy, not a native sender.

Five independent completed-minute capacities; fixed deadline and concentrated
remainder. A stop or unknown response never authorizes replacement exposure.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from decimal import Decimal as D
from pancakequant.binance import market_quantity
from pancakequant.types import ZERO, floor_step, serial
from pancakequant.linear_account import LOT
from pancakequant.state import client_id
from pancakequant.capital import CapitalBudget, capital_surplus
from research.bounded_execution import MINUTE, WINDOW, PARTICIPATION, exit_fill


@dataclass
class PlannedExit:
    call_time: int
    campaign: int
    start: int
    deadline: int
    maximum: D
    original_reference: D
    anchor_mark: D
    anchor_child: str
    previous_hour_quote: D
    slippage: D
    spread: D
    capital: dict
    sliced: bool
    filled: D = ZERO
    attempted: list[int] = field(default_factory=list)
    terminal_reason: str = ''
    unresolved: bool = False

    @property
    def identity(self):
        return client_id('research:binance:BTCUSDT', self.call_time, 'planned-exit')

    @classmethod
    def freeze(cls, account, now, campaign, reference, anchor_mark, anchor_child,
               budget, *, sliced, stress):
        if account.q <= 0 or not budget.valid:
            raise ValueError('planned exit requires a known funded long position')
        start=now+(2 if stress else 1)*MINUTE
        return cls(now,campaign,start,start+WINDOW,account.q,reference,anchor_mark,
                   anchor_child,budget.previous_hour_quote,budget.slippage,budget.spread,
                   budget.record(),sliced)

    def finish(self, reason, *, unresolved=False):
        if not self.terminal_reason:
            self.terminal_reason=reason
        self.unresolved |= unresolved

    def attempt(self, now, account, reference, mark, minute_quotes, instrument, *,
                outcome_known=True, pending_child=False, protection_confirmed=True):
        record=dict(parent_id=self.identity,child_id=client_id(self.identity,now,'reduce'),
                    call_time=self.call_time,time=now,event='',accepted='0',reason='outside_window')
        if self.terminal_reason or now < self.call_time:
            return record
        if now in self.attempted:
            record['reason']='duplicate_step';return record
        if not outcome_known or pending_child or not protection_confirmed:
            self.finish('unknown_execution_or_protection',unresolved=True)
            record['reason']=self.terminal_reason;return record
        if not account.q:
            self.finish('protection_closed');record['reason']=self.terminal_reason;return record
        if account.q != self.maximum-self.filled or account.q < 0:
            self.finish('unreconciled_position',unresolved=True)
            record['reason']=self.terminal_reason;return record
        if now > self.deadline:
            self.finish('missed_deadline_unresolved',unresolved=True)
            record['reason']=self.terminal_reason;return record
        budget=CapitalBudget.restore(self.capital)
        safe=capital_surplus(account,budget,reference,mark,self.anchor_mark)>=0
        if safe and (now<self.start or (now-self.start)%MINUTE):
            return record
        self.attempted.append(now)
        amount=account.q
        capacity_quote=self.previous_hour_quote
        event='regime_exit'
        if not safe:
            event='planned_exit_safety'
        else:
            # Both the concentrated control and every candidate child consume
            # the SAME causally known liquidity definition, including remainder.
            volume_time=now-2*MINUTE
            if volume_time not in minute_quotes:
                raise ValueError('missing causally published planned-exit minute')
            volume=D(minute_quotes[volume_time])
            if not volume.is_finite() or volume<0:
                raise ValueError('invalid planned-exit minute volume')
            capacity_quote=min(self.previous_hour_quote,volume*60)
            cap=capacity_quote/60*PARTICIPATION/reference
            record.update(volume_minute=volume_time,volume_available_at=volume_time+2*MINUTE,
                          completed_minute_quote=str(volume),capacity=str(cap))
            if not capacity_quote:
                if now==self.deadline or not self.sliced:
                    self.finish('no_confirmable_deadline_liquidity',unresolved=True)
                    record['reason']=self.terminal_reason;return record
                record['reason']='zero_executable_capacity';return record
            if self.sliced and now<self.deadline:
                amount=min(amount,market_quantity(cap,reference,instrument) if instrument else floor_step(cap,LOT))
                event='regime_exit_slice'
            elif self.sliced:
                event='regime_exit_deadline'
        if not amount:
            record['reason']='zero_executable_capacity';return record
        price,impact=exit_fill(reference,amount,capacity_quote,self.slippage,self.spread)
        # Account.close is the only ledger mutation. Native acknowledgement alone
        # cannot reach this branch: outcome/protection must be confirmed above.
        account.close(amount,price);self.filled+=amount
        record.update(impact,event=event,accepted=str(amount),quantity_after=str(account.q),
                      reason='safety' if not safe else 'deadline' if now==self.deadline else 'confirmed',
                      original_anchor=self.anchor_child,
                      delay_price_cost=str(amount*(self.original_reference-reference)))
        if not account.q:self.finish('closed')
        return record

    def record(self):
        return dict(serial(asdict(self)),parent_id=self.identity,remainder=str(self.maximum-self.filled))

    @classmethod
    def restore(cls, record):
        names=cls.__dataclass_fields__
        values={name:record[name] for name in names}
        for name in ('maximum','original_reference','anchor_mark','previous_hour_quote','slippage','spread','filled'):
            values[name]=D(values[name])
            if not values[name].is_finite():raise ValueError('nonfinite planned exit state')
        result=cls(**values)
        CapitalBudget.restore(result.capital)
        if (result.start-result.call_time not in (MINUTE,2*MINUTE)
                or result.deadline!=result.start+WINDOW or not ZERO<=result.filled<=result.maximum
                or min(result.maximum,result.original_reference,result.anchor_mark,result.previous_hour_quote)<=0
                or len(set(result.attempted))!=len(result.attempted)
                or any(type(t) is not int or t<result.call_time or t>result.deadline for t in result.attempted)
                or record['parent_id']!=result.identity):
            raise ValueError('invalid planned exit identity or deadline')
        return result
