"""Fast screening account on the frozen session starts. NOT a formal measurement.

Decisions happen only at session starts, from completed data. Between sessions
only resting native protection (mark-triggered close-all stop / take), funding
and isolated liquidation act. Fills use the last completed trade close plus an
explicit adverse slippage; stop fills take the worse of trigger and minute
open/low. Constant FX. Results rank ideas; the production-path meter decides.
"""
from dataclasses import dataclass, field
import json
from pathlib import Path

import numpy as np

from research.market_arrays import START, END, MINUTE, load

ROOT = Path(__file__).resolve().parents[1]
SCHEDULE = ROOT / 'evidence' / 'session-b0-20260927' / 'SCHEDULE.json'
FX = 6.9762
YEAR_MS = 31_556_952_000
FOUR = 14_400_000


@dataclass
class Costs:
    fee: float = 0.00075
    slip: float = 0.0005
    stop_slip: float = 0.001
    conversion: float = 0.001
    maintenance: float = 0.005
    liquidation_fee: float = 0.0125


@dataclass
class Order:
    """Target at a session: signed quantity multiple of equity plus protection."""
    exposure: float            # signed notional / equity
    stop: float | None = None  # absolute price, mark-triggered close-all
    take: float | None = None
    keep: bool = False         # keep current position and protection unchanged


class Data:
    def __init__(self, cache='/data/coinquant-cache', schedule=SCHEDULE):
        arrays = load(cache)
        self.trade, self.mark = arrays['trade'], arrays['mark']
        self.h4 = arrays['h4']
        self.funding = arrays['funding']
        body = json.loads(Path(schedule).read_text())
        self.starts = np.array(body['starts_ms'], dtype=np.int64)
        self.absence = np.array(body['absence_starts_ms'], dtype=np.int64)
        # mark gaps: bounded by trade minute widened by the observed spread tail
        gap = np.isnan(self.mark[:, 0])
        self.mark_low = np.where(gap, self.trade[:, 2] * (1 - 0.0045), self.mark[:, 2])
        self.mark_high = np.where(gap, self.trade[:, 1] * (1 + 0.0102), self.mark[:, 1])
        self.mark_open = np.where(gap, self.trade[:, 0], self.mark[:, 0])
        self.mark_close = np.where(gap, self.trade[:, 3], self.mark[:, 3])
        self.h4_time = self.h4[:, 0].astype(np.int64)
        f = self.funding
        self.f_time = f[:, 0].astype(np.int64)
        self.f_rate = f[:, 1]

    def index(self, ms):
        return int((ms - START) // MINUTE)

    def completed_h4(self, ms):
        """Rows of 4h bars whose close time <= ms (open + 4h <= ms)."""
        return int(np.searchsorted(self.h4_time, ms - FOUR, side='right'))


@dataclass
class Result:
    final_cny: float
    cagr: float
    mdd: float
    mdd_at: int
    trades: int
    stops: int
    takes: int
    liquidations: int
    fees: float
    funding: float
    exposure_time: float
    yearly: dict = field(default_factory=dict)
    log: list = field(default_factory=list)


def run(data, strategy, costs=Costs(), starts=None, record=False):
    starts = data.starts if starts is None else starts
    wallet = 10000 / FX * (1 - costs.conversion)
    q = 0.0
    entry = 0.0
    margin = 0.0
    stop = take = None
    peak = 10000.0
    mdd = 0.0
    mdd_at = START
    fees = funding = 0.0
    trades = stops = takes = liqs = 0
    held_minutes = 0
    yearly = {}
    log = []
    state = {}
    now = int(starts[0])

    def equity_at(price):
        return wallet + q * (price - entry)

    def note(cny_close_series_peak, trough_cny, at):
        nonlocal peak, mdd, mdd_at
        if cny_close_series_peak > peak:
            peak = cny_close_series_peak
        dd = 1 - trough_cny / peak
        if dd > mdd:
            mdd, mdd_at = dd, at

    def liq_price():
        if not q:
            return None
        return (q * entry - margin) / (q - abs(q) * (costs.maintenance + costs.fee))

    def close_all(price, why):
        nonlocal wallet, q, entry, margin, fees, stop, take
        fee = abs(q) * price * costs.fee
        wallet += q * (price - entry) - fee
        fees += fee
        if record:
            log.append((why, now, q, entry, price))
        q = entry = margin = 0.0
        stop = take = None

    def hold(until):
        """Advance exchange time with resting protection only."""
        nonlocal now, wallet, funding, stops, takes, liqs, held_minutes, margin, peak, mdd, mdd_at
        nonlocal q, entry, stop, take
        if not q:
            peak_c = wallet * FX
            note(peak_c, peak_c, now)
            now = until
            return
        a, b = data.index(now), data.index(until)
        if b <= a:
            now = until
            return
        lo, hi = data.mark_low[a:b], data.mark_high[a:b]
        op = data.mark_open[a:b]
        long = q > 0
        liq = liq_price()
        hit = np.zeros(b - a, dtype=bool)
        if stop is not None:
            hit |= (lo <= stop) if long else (hi >= stop)
        if take is not None:
            hit |= (hi >= take) if long else (lo <= take)
        hit |= (lo <= liq) if long else (hi >= liq)
        where = np.flatnonzero(hit)
        end = a + (where[0] if len(where) else b - a)
        # funding up to exit minute
        exit_ms = START + end * MINUTE + (MINUTE if len(where) else 0)
        fi = np.searchsorted(data.f_time, now, side='right')
        fj = np.searchsorted(data.f_time, min(exit_ms, until), side='right')
        for k in range(fi, fj):
            mi = data.index(int(data.f_time[k])) - 1
            mk = data.mark_close[mi] if mi >= 0 else entry
            pay = q * mk * data.f_rate[k]
            wallet -= pay
            funding += pay
            margin = min(margin, wallet) if margin > wallet else margin
        seg_end = end + (1 if len(where) else 0)
        closes = data.mark_close[a:seg_end]
        adverse = (data.mark_low if long else data.mark_high)[a:seg_end]
        if len(closes):
            eq_close = wallet + q * (closes - entry)
            eq_adv = wallet + q * (adverse - entry)
            run_peak = np.maximum.accumulate(np.concatenate([[peak / FX], eq_close]))[:-1]
            dd = 1 - eq_adv / run_peak
            k = int(np.argmax(dd))
            if dd[k] > mdd:
                mdd, mdd_at = float(dd[k]), START + (a + k) * MINUTE
            peak = max(peak, float(eq_close.max()) * FX)
        held_minutes += seg_end - a
        if len(where):
            i = end
            o, l, h = data.mark_open[i], data.mark_low[i], data.mark_high[i]
            kinds = []
            if stop is not None and ((l <= stop) if long else (h >= stop)):
                kinds.append('stop')
            if take is not None and ((h >= take) if long else (l <= take)):
                kinds.append('take')
            if (l <= liq) if long else (h >= liq):
                kinds.append('liq')
            tprice = data.trade[i]
            if 'liq' in kinds and ('stop' not in kinds or ((liq >= stop) if long else (liq <= stop))):
                # isolated: the posted margin is lost, the rest of the wallet is not
                lost = margin
                if record:
                    log.append(('liq', now, q, entry, liq))
                q = entry = 0.0
                stop = take = None
                wallet -= lost
                margin = 0.0
                liqs += 1
            elif 'stop' in kinds:
                # take the worse of trigger or opening gap, then slippage; trade low bound too
                base = min(stop, o) if long else max(stop, o)
                price = base * (1 - costs.stop_slip) if long else base * (1 + costs.stop_slip)
                close_all(price, 'stop')
                stops += 1
            else:
                base = take
                price = base * (1 - costs.stop_slip) if long else base * (1 + costs.stop_slip)
                close_all(price, 'take')
                takes += 1
            note(wallet * FX, wallet * FX, START + i * MINUTE)
        now = until

    for n, start in enumerate(starts):
        start = int(start)
        hold(start)
        i = data.index(start) - 1  # last completed trade minute
        if i < 0:
            continue  # no completed official minute before the first session
        price = data.trade[i, 3]
        mark_now = data.mark_close[i]
        eq = equity_at(mark_now)
        if eq <= 0:
            break
        view = dict(time=start, price=price, mark=mark_now, equity=eq, q=q, entry=entry,
                    stop=stop, take=take, h4_rows=data.completed_h4(start), n=n)
        order = strategy(data, view, state)
        if order is not None and not order.keep:
            target = order.exposure * eq / price
            change = target - q
            if abs(change) * price > 5 and (abs(change) > 1e-9):
                if q and (np.sign(target) != np.sign(q) or abs(target) < abs(q)):
                    # reduce/close at trade close with slippage
                    px = price * (1 - costs.slip) if q > 0 else price * (1 + costs.slip)
                    cut = q if np.sign(target) != np.sign(q) or target == 0 else q - target
                    if abs(cut - q) < 1e-12:
                        close_all(px, 'session')
                    else:
                        fee = abs(cut) * px * costs.fee
                        wallet += cut * (px - entry) - fee
                        fees += fee
                        margin *= (q - cut) / q
                        q -= cut
                    trades += 1
                if target and (not q or np.sign(target) == np.sign(q)) and abs(target) > abs(q):
                    add = target - q
                    px = price * (1 + costs.slip) if add > 0 else price * (1 - costs.slip)
                    fee = abs(add) * px * costs.fee
                    wallet -= fee
                    fees += fee
                    entry = (q * entry + add * px) / (q + add) if q else px
                    q += add
                    trades += 1
            if q:
                stop, take = order.stop, order.take
                # isolated margin: at least notional/20; enough to put liq beyond the stop
                need = abs(q) * entry / 20
                if stop is None:
                    need = wallet
                else:
                    loss = abs(q) * abs(entry - stop) * 1.02 + abs(q) * stop * (costs.maintenance + costs.fee)
                    need = max(need, loss)
                margin = min(max(need, margin), max(wallet, 0))
            else:
                stop = take = None
        year = str(np.datetime64(start, 'ms').astype('datetime64[Y]'))
        yearly[year] = equity_at(mark_now) * FX
    hold(END)
    final_usdt = wallet + (q * (data.mark_close[data.index(END) - 1] - entry) if q else 0)
    final_cny = final_usdt * FX
    years = (END - START) / YEAR_MS
    cagr = (final_cny / 10000) ** (1 / years) - 1 if final_cny > 0 else -1.0
    total = data.index(END) - data.index(int(starts[0]))
    return Result(final_cny, cagr, mdd, mdd_at, trades, stops, takes, liqs, fees, funding,
                  held_minutes / total, yearly, log)


def summary(result):
    return (f'CNY {result.final_cny:,.0f}  CAGR {result.cagr*100:6.1f}%  MDD {result.mdd*100:5.1f}%  '
            f'trades {result.trades} stops {result.stops} takes {result.takes} liq {result.liquidations} '
            f'fees {result.fees:,.0f} funding {result.funding:,.0f} held {result.exposure_time*100:.0f}%')
