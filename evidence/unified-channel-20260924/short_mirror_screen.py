"""Market-only check of a mirrored UC4 state at the frozen sparse calls.

Run from repository root with the recovered originals:
PYTHONPATH=. python evidence/unified-channel-20260924/short_mirror_screen.py ../replay/bounded ../replay/sx60 ../replay/m60-development ../replay/m60-protection ../replay/m60-mark ../replay/m60-warmup
No execution, funding, account or candidate qualification is calculated.
"""
import sys
from collections import deque
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path

from coinquant.research import invocations, spec, timestamp
from research.conditional_hold_replay import prepared_inputs

HOUR = 3_600_000


def main():
    bounded, sx60, *extra = map(Path, sys.argv[1:])
    if len(extra) != 4:
        raise SystemExit('supply bounded, sx60, and four M60 original directories')
    _, prepared, _ = prepared_inputs(bounded, sx60, extra, full=True)
    trade = prepared[0][0]['klines']
    warm = prepared[0][2]
    frozen = spec()
    start, end = timestamp(frozen['start']), timestamp(frozen['end'])
    bars = deque(maxlen=21)
    active = None
    states = {}
    for t in range(min(warm), end, 4 * HOUR):
        source = warm if t < start else trade
        rows = [source[x] for x in range(t, t + 4 * HOUR, HOUR)]
        high = max(D(r[2]) for r in rows)
        low = min(D(r[3]) for r in rows)
        close = D(rows[-1][4])
        prior = list(bars)
        if active is not None and close > max(h for h, _ in prior[-10:]):
            active = None
        elif active is None and len(prior) >= 20 and close < min(l for _, l in prior[-20:]):
            active = t + 4 * HOUR
        bars.append((high, low))
        states[t + 4 * HOUR] = active

    campaign = None
    result = []
    for t in invocations(frozen):
        if t >= end:
            break
        state = states[t // (4 * HOUR) * 4 * HOUR]
        if campaign is not None and campaign[0] != state:
            first = campaign[1]
            gross_short = 1 - D(trade[t][1]) / D(trade[first][1])
            result.append((datetime.fromtimestamp(first / 1000, timezone.utc).year, gross_short))
            campaign = None
        if state is not None and campaign is None:
            campaign = (state, t)

    print('closed_campaigns', len(result), 'gross_positive', sum(v > 0 for _, v in result))
    print('unweighted_gross_short_sum_percent', 100 * sum((v for _, v in result), D(0)))
    for year in range(2020, 2027):
        values = [v for y, v in result if y == year]
        print(year, len(values), 100 * sum(values, D(0)))


if __name__ == '__main__':
    main()
