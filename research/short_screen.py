"""Screening-only short rule families (round S1). NOT a formal measurement.

Each rule decides only at session starts from completed 4h bars. Size risks a
fixed share of equity to the stop, capped by an exposure multiple.
"""
import itertools
import json
import sys

import numpy as np

from research.screen import Data, Order, Costs, run, FOUR

DEV_END = 1704067200000  # 2024-01-01


def _ema(values, span):
    out = np.empty_like(values)
    alpha = 2 / (span + 1)
    acc = values[0]
    for i, v in enumerate(values):
        acc = alpha * v + (1 - alpha) * acc
        out[i] = acc
    return out


class Breakdown:
    """Short a completed close under the prior N-day low and a slow EMA."""

    def __init__(self, data, low_days, ema_days, stop_days, exit_days, risk=0.03, cap=3.0, macro=None):
        self.c = data.h4[:, 4]
        self.h = data.h4[:, 2]
        self.l = data.h4[:, 3]
        self.ema = _ema(self.c, ema_days * 6)
        self.exit_ema = _ema(self.c, exit_days * 6)
        self.n, self.s = low_days * 6, stop_days * 6
        self.risk, self.cap = risk, cap
        self.macro = macro
        self.used = None

    def __call__(self, data, view, state):
        k = view['h4_rows'] - 1
        if k < self.n + 1:
            return None
        close = self.c[k]
        if view['q'] < 0:
            if close > self.exit_ema[k]:
                return Order(0.0)
            return Order(0, keep=True)
        if view['q']:
            return None
        if self.used == k:
            return None
        if not (close < self.l[k - self.n:k].min() and close < self.ema[k]):
            return None
        if self.macro is not None and not self.macro(view['time']):
            return None
        stop = self.h[k - self.s + 1:k + 1].max()
        price = view['price']
        if stop <= price:
            return None
        self.used = k
        exposure = min(self.cap, self.risk * price / (stop - price))
        return Order(-exposure, stop=float(stop), take=None)


def dfii10_rising():
    from research.dfii10_history import History
    history = History()
    cache = {}

    def check(now):
        day = now // 86_400_000
        if day not in cache:
            row = history.snapshot(now)
            ok = (row['missing_reason'] is None and
                  float(row['latest_value']) >= float(row['prior20_value']) + 0.25)
            cache[day] = ok
        return cache[day]
    return check


def split(data, strategy_factory):
    whole = run(data, strategy_factory(), Costs())
    dev = run(data, strategy_factory(), Costs(), starts=data.starts[data.starts < DEV_END])
    hold = run(data, strategy_factory(), Costs(), starts=data.starts[data.starts >= DEV_END])
    return whole, dev, hold


def main():
    data = Data()
    grid = list(itertools.product((10, 20, 40), (50, 100, 200), (5, 10), (10, 20), (None, 'dfii10')))
    rows = []
    for low, ema, stop, exit_, macro in grid:
        gate = dfii10_rising() if macro else None
        whole, dev, hold = split(data, lambda: Breakdown(data, low, ema, stop, exit_, macro=gate))
        row = dict(low=low, ema=ema, stop=stop, exit=exit_, macro=macro,
                   cagr=whole.cagr, mdd=whole.mdd, trades=whole.trades,
                   dev_cagr=dev.cagr, hold_cagr=hold.cagr, final=whole.final_cny)
        rows.append(row)
        print(json.dumps(row), flush=True)
    return rows


if __name__ == '__main__':
    sys.exit(main() and 0)
