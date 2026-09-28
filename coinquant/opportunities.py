"""Causal impulse-hold opportunity from completed UTC four-hour candles.

Independent definition, not a reproduction of a redacted external strategy.
No account or exchange writes.
"""
from collections import deque
from dataclasses import dataclass
from decimal import Decimal as D

FOUR_HOURS = 14400000


@dataclass(frozen=True)
class Opportunity:
    identity: int
    direction: int
    stop: D
    take: D
    expires: int | None


class Opportunities:
    """A close more than three prior ATR(14) from the previous close opens a
    campaign in its direction, stopped at the midpoint of the two closes, with
    a 20x risk-multiple target and a 42-bar (seven-day) life."""

    interval = FOUR_HOURS

    def __init__(self):
        self.tr = deque(maxlen=14)
        self.close = None
        self.last = None
        self.active = None

    def update(self, end, high, low, close):
        if self.last is not None and end != self.last + self.interval:
            raise ValueError('incomplete model clock')
        if not 0 < low <= close <= high:
            raise ValueError('invalid completed candle')
        prior = self.close if self.close is not None else close
        prior_atr = sum(self.tr) / 14 if len(self.tr) == 14 else None
        self.tr.append(max(high - low, abs(high - prior), abs(low - prior)))
        self.close, self.last = close, end
        a = self.active
        if a and ((a.expires is not None and end >= a.expires) or
                  (low <= a.stop or high >= a.take if a.direction > 0 else high >= a.stop or low <= a.take)):
            self.active = None
        if not self.active and prior_atr and abs(close - prior) > 3 * prior_atr:
            side = 1 if close > prior else -1
            stop = (prior + close) / 2
            take = close * (close / stop) ** 20
            if take > 0:
                self.active = Opportunity(end, side, stop, take, end + 42 * FOUR_HOURS)
        return self.active
