"""One causal trend/volatility model shared by run-once and historical replay.

BTC collateral remains price-exposed even when the derivative position is flat.
Risk sizing below budgets incremental derivative loss in BTC; replay additionally
marks the complete wallet to USD/CNY. It does NOT claim to bound fiat drawdown.
"""
from decimal import Decimal as D, ROUND_CEILING

from .types import (INTERVAL_MS, ZERO, Bar, Blocked, ModelConfig, Snapshot,
                    Target, floor_step, number)


def validate_bars(bars: list[Bar], now: int) -> None:
    if not bars or bars[-1].time + INTERVAL_MS > now:
        raise Blocked("complete candles are required")
    if bars[-1].time + 2 * INTERVAL_MS <= now:
        raise Blocked("latest complete candle is missing")
    for previous, current in zip(bars, bars[1:]):
        if current.time - previous.time != INTERVAL_MS:
            raise Blocked("duplicate or missing signal candle")
    if any(bar.time % INTERVAL_MS for bar in bars):
        raise Blocked("signal candles are not UTC-aligned")


def liquidation_price(quantity: D, entry: D, margin_btc: D,
                      maintenance_rate: D, fee: D) -> D:
    """Conservative inverse isolated liquidation estimate; no MM deduction.

    margin + q*(1/entry - 1/price) = abs(q)*(MMR+closing_fee)/price.
    Live execution also checks the actual exchange-reported liquidation price.
    """
    if not quantity:
        return ZERO
    if entry <= 0 or margin_btc <= 0:
        raise Blocked("invalid liquidation inputs")
    denominator = margin_btc + quantity / entry
    numerator = quantity + abs(quantity) * (maintenance_rate + fee)
    if denominator == 0 or numerator / denominator <= 0:
        raise Blocked("unsupported liquidation geometry")
    return numerator / denominator


def protected(snapshot: Snapshot, tp: D | None = None, sl: D | None = None) -> bool:
    p = snapshot.position
    if not p.quantity:
        return True
    tp = p.take_profit if tp is None else tp
    sl = p.stop_loss if sl is None else sl
    cushion = max(snapshot.rules.tick * 2, snapshot.mark * D("0.003"))
    if p.quantity > 0:
        return p.liquidation + cushion < sl < snapshot.mark < tp
    return ZERO < tp < snapshot.mark < sl < p.liquidation - cushion


def _prices(mark: D, direction: int, distance: D, reward: D, tick: D) -> tuple[D, D]:
    # Round toward the market for the stop and away for take profit.
    if direction > 0:
        sl = ((mark - distance) / tick).to_integral_value(rounding=ROUND_CEILING) * tick
        tp = ((mark + distance * reward) / tick).to_integral_value(rounding=ROUND_CEILING) * tick
    else:
        sl = floor_step(mark + distance, tick)
        tp = floor_step(mark - distance * reward, tick)
    if min(sl, tp) <= 0 or sl == mark or tp == mark:
        raise Blocked("invalid rounded protection")
    return tp, sl


def repair_target(snapshot: Snapshot, cfg: ModelConfig, candle: int = -1) -> Target:
    """Protection-only decision remains possible without a new signal candle."""
    p, mark, tick = snapshot.position, snapshot.mark, snapshot.rules.tick
    if not p.quantity:
        return Target(candle, ZERO, mark, ZERO, ZERO, ZERO, ZERO, ZERO, "flat")
    if p.liquidation <= 0:
        raise Blocked("cannot repair protection with unknown liquidation")
    if ((p.quantity > 0 and p.liquidation >= mark) or
            (p.quantity < 0 and p.liquidation <= mark)):
        raise Blocked("position at or beyond liquidation")
    distance = min(mark * D("0.02"), abs(mark - p.liquidation) / 2)
    tp, sl = _prices(mark, 1 if p.quantity > 0 else -1, distance, cfg.reward_multiple, tick)
    if not protected(snapshot, tp, sl):
        raise Blocked("no safe protection price before liquidation")
    risk = abs(p.quantity * (1 / mark - 1 / sl))
    return Target(candle, p.quantity, mark, tp, sl, abs(p.quantity) / mark / 20,
                  p.margin_btc, risk, "repair full-position exchange protection")


def decide(bars: list[Bar], snapshot: Snapshot, cfg: ModelConfig, *, notional_limit: D | None = None) -> Target:
    snapshot.validate()
    cap = snapshot.rules.maximum if notional_limit is None else number(notional_limit, "authorized notional", positive=True)
    validate_bars(bars, snapshot.time)
    required = max(cfg.trend_bars, cfg.channel_bars + 1, cfg.atr_bars + 1)
    if len(bars) < required:
        raise Blocked("insufficient causal indicator warmup")
    mark, p, rules = snapshot.mark, snapshot.position, snapshot.rules
    candle = bars[-1].time
    close = bars[-1].close
    mean = sum(b.close for b in bars[-cfg.trend_bars:]) / cfg.trend_bars
    channel = bars[-cfg.channel_bars - 1:-1]  # exclude the signal candle
    previous = bars[-cfg.atr_bars - 1:-1]
    current = bars[-cfg.atr_bars:]
    atr = sum(max(b.high - b.low, abs(b.high - a.close), abs(b.low - a.close))
              for a, b in zip(previous, current)) / cfg.atr_bars
    direction = 1 if close > mean else -1 if close < mean else 0
    if not direction or (p.quantity and direction * p.quantity < 0):
        return Target(candle, ZERO, mark, ZERO, ZERO, ZERO, ZERO, ZERO,
                      "trend no longer supports holding; BTC collateral remains exposed")
    trigger = ZERO
    if not p.quantity:
        boundary = (((max(b.high for b in channel) / rules.tick).to_integral_value(rounding=ROUND_CEILING) + 1) * rules.tick if direction > 0
                    else floor_step(min(b.low for b in channel), rules.tick) - rules.tick)
        if direction * (mark - boundary) < 0:
            trigger = boundary
    reference = trigger or mark
    distance = max(atr * cfg.atr_multiple, rules.tick * 4)
    # Initial 20x margin must cover the attached stop BEFORE any manual addition.
    if distance >= reference * (D("0.05") - rules.maintenance_rate - rules.taker_fee - D("0.005")):
        if p.quantity:
            return repair_target(snapshot, cfg, candle)
        return Target(candle, ZERO, mark, ZERO, ZERO, ZERO, ZERO, ZERO,
                      "ATR stop cannot precede initial 20x liquidation with safety margin")
    tp, sl = _prices(reference, direction, distance, cfg.reward_multiple, rules.tick)
    quote = reference if trigger else snapshot.ask if direction > 0 else snapshot.bid
    price = quote * (1 + cfg.slippage_fraction) if direction > 0 else quote * (1 - cfg.slippage_fraction)
    price = (price / rules.tick).to_integral_value(rounding=ROUND_CEILING) * rules.tick if direction > 0 else floor_step(price, rules.tick)
    unit_loss = abs(1 / price - 1 / sl)
    unit_cost = rules.taker_fee * (1 / price + 1 / sl) + cfg.slippage_fraction / sl
    unit_cost += abs(snapshot.funding_rate) / mark
    risk_budget = snapshot.equity_btc * cfg.risk_fraction
    # Existing same-direction margin can be released/reused; opposite exposure
    # is first closed and the target recomputed from the resulting real account.
    reusable = p.margin_btc if direction * p.quantity > 0 else ZERO
    available = max(ZERO, snapshot.available_btc + reusable)
    depth = snapshot.buy_depth_usd if direction > 0 else snapshot.sell_depth_usd
    quantity = floor_step(min(risk_budget / (unit_loss + unit_cost),
                              snapshot.equity_usd * cfg.max_effective_leverage,
                              available / (1 / price / 20 + 2 * rules.taker_fee / price),
                              rules.maximum, cap, rules.risk_limit_usd * min(D(1), sl / mark),
                              depth * cfg.liquidity_fraction), rules.step)
    if quantity < rules.minimum:
        return Target(candle, ZERO, mark, ZERO, ZERO, ZERO, ZERO, ZERO,
                      "executable size below venue minimum")
    signed = direction * quantity
    initial = quantity / price / 20
    allocated = initial + quantity * rules.taker_fee / price
    estimate = liquidation_price(signed, price, initial, rules.maintenance_rate, rules.taker_fee)
    cushion = reference * D("0.003")
    if (direction > 0 and sl <= estimate + cushion) or (direction < 0 and sl >= estimate - cushion):
        raise Blocked("stop does not precede conservative liquidation estimate")
    # Do not loosen an existing valid stop merely because a new candle arrived.
    if p.quantity * signed > 0 and protected(snapshot):
        sl = max(sl, p.stop_loss) if signed > 0 else min(sl, p.stop_loss)
    return Target(candle, signed, price, tp, sl, initial, allocated,
                  quantity * (unit_loss + unit_cost),
                  "trend-filtered native FOK breakout" if trigger else "causal channel trend with inverse volatility risk sizing",
                  trigger)
