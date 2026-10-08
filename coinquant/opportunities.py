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
# Kept only when the actual fill, not the signal close, is this many risk
# units higher at expiry. The stop is then the prior 84-bar low, never below
# the fill. Extending from the signal close also kept later trades and pushed
# the screened drawdown through 50%.
EXTEND_R = 6
WINNER_LOW_BARS = 84


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
    a 20x risk-multiple target and a 42-bar (seven-day) life. A long is kept
    past that life only when its recorded fill is still at least six risk
    units above the stop. The stop then becomes the lowest low of the prior
    84 bars, never below that fill, and the original target is replaced."""

    interval = FOUR_HOURS

    def __init__(self):
        self.tr = deque(maxlen=ATR_BARS)
        self.close = None
        self.last = None
        self.active = None
        self.lows = deque(maxlen=WINNER_LOW_BARS)
        self.fill = None

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
            take = a.take
            extended = a.extended
            expires = a.expires
            trailed = min(self.lows) if len(self.lows) == WINNER_LOW_BARS else None
            time_up = expires is not None and end >= expires
            through = low <= stop or high >= take if a.direction > 0 else high >= stop or low <= take
            fill = self.fill
            extend = (a.direction > 0 and not extended and time_up and not through
                      and fill is not None and fill > stop
                      and close >= fill + EXTEND_R * (fill - stop))
            if extend:
                extended = True
                expires = None
                stop = max(stop, fill)
                if trailed is not None:
                    stop = max(stop, trailed)
                # Replace the original target. The exchange copies this price.
                take = peak * 5
                through = low <= stop
            elif extended:
                if trailed is not None:
                    stop = max(stop, trailed)
                if fill is not None:
                    stop = max(stop, fill)
                take = max(take, peak * 5)
                through = low <= stop
            if through or (time_up and not extended):
                self.active = None
            elif (peak != a.peak or stop != a.stop or take != a.take
                  or extended != a.extended or expires != a.expires):
                self.active = Opportunity(a.identity, a.direction, stop, take, expires,
                                          a.anchor, a.risk, peak, extended)
        if not self.active and prior_atr and abs(close - prior) > IMPULSE_ATR * prior_atr:
            side = 1 if close > prior else -1
            stop = (prior + close) / 2
            take = close * (close / stop) ** TAKE_POWER
            risk = abs(close - stop)
            if take > 0 and stop > 0 and risk > 0:
                self.active = Opportunity(end, side, stop, take, end + LIFE_BARS * FOUR_HOURS,
                                          close, risk, high, False)
        self.lows.append(low)
        return self.active
