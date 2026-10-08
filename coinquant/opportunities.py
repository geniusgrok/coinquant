"""Causal impulse-hold opportunity from completed UTC four-hour candles.

Independent definition, not a reproduction of a redacted external strategy.
No account or exchange writes.
"""
from collections import deque
from dataclasses import dataclass
from decimal import Decimal as D

FOUR_HOURS = 14400000
IMPULSE_ATR = 3
ATR_BARS = 14
TAKE_POWER = 20
LIFE_BARS = 42
# A long still this many initial risk units above its signal close at expiry
# stays open. The stop then ratchets a 5% trail under the running high.
# A wider trail raised the screened bar-path drawdown through 50%.
EXTEND_R = 6
WINNER_TRAIL = D('0.05')


@dataclass(frozen=True)
class Opportunity:
    identity: int
    direction: int
    stop: D
    take: D
    expires: int | None
    anchor: D | None = None
    risk: D | None = None
    peak: D | None = None
    extended: bool = False


class Opportunities:
    """A close more than three prior ATR(14) from the previous close opens a
    campaign in its direction, stopped at the midpoint of the two closes, with
    a 20x risk-multiple target and a 42-bar (seven-day) life. A long that is
    still at least six initial risk units above its signal close at that life
    is kept, and its stop becomes a 5% trail under the high since the signal."""

    interval = FOUR_HOURS

    def __init__(self):
        self.tr = deque(maxlen=ATR_BARS)
        self.close = None
        self.last = None
        self.active = None

    def update(self, end, high, low, close):
        if self.last is not None and end != self.last + self.interval:
            raise ValueError('incomplete model clock')
        if not 0 < low <= close <= high:
            raise ValueError('invalid completed candle')
        prior = self.close if self.close is not None else close
        prior_atr = sum(self.tr) / self.tr.maxlen if len(self.tr) == self.tr.maxlen else None
        self.tr.append(max(high - low, abs(high - prior), abs(low - prior)))
        self.close, self.last = close, end
        a = self.active
        if a is not None:
            peak = high if a.peak is None else (max(a.peak, high) if a.direction > 0 else min(a.peak, low))
            stop = a.stop
            extended = a.extended
            expires = a.expires
            if extended and a.direction > 0:
                stop = max(stop, peak * (1 - WINNER_TRAIL))
            time_up = expires is not None and end >= expires
            through = low <= stop or high >= a.take if a.direction > 0 else high >= stop or low <= a.take
            extend = (a.direction > 0 and not extended and time_up and not through
                      and a.anchor is not None and a.risk is not None and a.risk > 0
                      and close >= a.anchor + EXTEND_R * a.risk)
            if extend:
                stop = max(a.stop, peak * (1 - WINNER_TRAIL))
                through = low <= stop
                extended = not through
                expires = None if extended else expires
            if through or (time_up and not extended):
                self.active = None
            elif peak != a.peak or stop != a.stop or extended != a.extended or expires != a.expires:
                self.active = Opportunity(a.identity, a.direction, stop, a.take, expires,
                                          a.anchor, a.risk, peak, extended)
        if not self.active and prior_atr and abs(close - prior) > IMPULSE_ATR * prior_atr:
            side = 1 if close > prior else -1
            stop = (prior + close) / 2
            take = close * (close / stop) ** TAKE_POWER
            risk = abs(close - stop)
            if take > 0 and stop > 0 and risk > 0:
                self.active = Opportunity(end, side, stop, take, end + LIFE_BARS * FOUR_HOURS,
                                          close, risk, high, False)
        return self.active
