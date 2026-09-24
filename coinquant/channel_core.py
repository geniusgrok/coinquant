"""Completed four-hour channel state for a single sparse-call target."""
from collections import deque
from dataclasses import dataclass
from decimal import Decimal as D

from .types import ZERO

FOUR_HOURS = 4 * 60 * 60 * 1000


@dataclass(frozen=True)
class ChannelOpportunity:
    identity: int
    stop: D
    direction: int = 1
    entry_limit: None = None


class ChannelCore:
    def __init__(self, direction=1):
        if direction not in (-1, 1):
            raise ValueError('invalid channel direction')
        self.direction = direction
        self.bars = deque(maxlen=21)
        self.last = None
        self.active_since = None

    def update(self, end, high, low, close):
        high, low, close = map(D, (high, low, close))
        if (type(end) is not int or end % FOUR_HOURS or
                self.last is not None and end != self.last + FOUR_HOURS or
                not all(v.is_finite() for v in (high, low, close)) or
                not ZERO < low <= close <= high):
            raise ValueError('invalid or missing completed four-hour bar')
        prior = list(self.bars)
        if self.active_since is not None and len(prior) >= 10 and (
            close < min(b[1] for b in prior[-10:]) if self.direction > 0
            else close > max(b[0] for b in prior[-10:]
        )):
            self.active_since = None
        elif self.active_since is None and len(prior) >= 20 and (
            close > max(b[0] for b in prior[-20:]) if self.direction > 0
            else close < min(b[1] for b in prior[-20:]
        )):
            self.active_since = end
        self.bars.append((high, low, close))
        self.last = end
        stop = (min(b[1] for b in list(self.bars)[-10:]) if self.direction > 0
                else max(b[0] for b in list(self.bars)[-10:]))
        return (ChannelOpportunity(self.active_since, stop, self.direction)
                if self.active_since is not None else None)
