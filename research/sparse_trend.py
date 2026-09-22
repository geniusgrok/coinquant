"""L2 research-only signal; never imported by the production trading path.

A single self-normalized 20-day log trend supplies signed conviction. Decisions
consume only complete UTC 4h candles at the frozen manual invocation times.
This is a signal hypothesis, not a calibrated return forecast or qualified
strategy. Venue sizing/protection and a native linear replay remain required.
"""
from dataclasses import dataclass
from decimal import Decimal as D

from coinquant.model import validate_bars
from coinquant.types import Bar, Blocked, INTERVAL_MS, ZERO

LOOKBACK = 120  # 20 days of complete 4h returns, frozen before measurement


@dataclass(frozen=True)
class Signal:
    candle: int
    score: D
    conviction: D
    direction: int
    daily_rms: D


def signal(bars: list[Bar], now: int) -> Signal:
    validate_bars(bars, now)
    if len(bars) < LOOKBACK + 1:
        raise Blocked('L2 needs 121 complete 4h candles')
    window = bars[-LOOKBACK - 1:]
    returns = [(b.close / a.close).ln() for a, b in zip(window, window[1:])]
    energy = sum((r * r for r in returns), ZERO)
    score = sum(returns, ZERO) / energy.sqrt() if energy else ZERO
    # Continuous participation; magnitude scales risk down without a hard entry gate.
    conviction = abs(score) / (1 + abs(score))
    direction = (1 if score > 0 else -1) if conviction else 0
    daily_rms = (energy / LOOKBACK * (86_400_000 // INTERVAL_MS)).sqrt()
    return Signal(bars[-1].time, score, conviction, direction, daily_rms)
