"""Validated value objects for the single Bybit BTCUSD inverse contract."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from typing import Any

D = Decimal
ZERO = D(0)
SYMBOL = "BTCUSD"
CATEGORY = "inverse"
INTERVAL_MS = 4 * 60 * 60 * 1000


class Blocked(RuntimeError):
    """A known prerequisite is unsatisfied; no new exposure is allowed."""


class Unknown(RuntimeError):
    """An exchange write or account observation has an uncertain outcome."""


def number(value: Any, name: str = "number", *, positive: bool = False) -> D:
    try:
        result = D(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise Blocked(f"invalid {name}") from exc
    if not result.is_finite() or (positive and result <= 0):
        raise Blocked(f"invalid {name}")
    return result


def floor_step(value: D, step: D) -> D:
    if step <= 0 or value < 0:
        raise Blocked("invalid quantity or step")
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step


def serial(value: Any) -> Any:
    if isinstance(value, D):
        return str(value)
    if hasattr(value, "__dataclass_fields__"):
        return serial(asdict(value))
    if isinstance(value, dict):
        return {str(k): serial(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [serial(v) for v in value]
    return value


@dataclass(frozen=True)
class Bar:
    time: int  # open time in UTC milliseconds; [time, time + interval)
    open: D
    high: D
    low: D
    close: D
    volume: D = ZERO  # inverse contract volume is USD contracts, NOT BTC

    def __post_init__(self) -> None:
        if self.time < 0 or any(not x.is_finite() or x <= 0 for x in
                                (self.open, self.high, self.low, self.close)):
            raise Blocked("invalid OHLC")
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close):
            raise Blocked("inconsistent OHLC")
        if self.high < self.low or not self.volume.is_finite() or self.volume < 0:
            raise Blocked("invalid range or volume")


@dataclass(frozen=True)
class Rules:
    tick: D
    step: D
    minimum: D
    maximum: D  # capped at the venue's market-close maximum as well
    risk_limit_usd: D
    maintenance_rate: D
    taker_fee: D
    launch_ms: int
    status: str = "Trading"

    def __post_init__(self) -> None:
        for key in ("tick", "step", "minimum", "maximum", "risk_limit_usd"):
            number(getattr(self, key), key, positive=True)
        if not ZERO < self.maintenance_rate < D("0.05"):
            raise Blocked("unsupported maintenance tier at 20x")
        if not ZERO <= self.taker_fee < D("0.01"):
            raise Blocked("invalid taker fee")
        if self.minimum > self.maximum or self.launch_ms < 0:
            raise Blocked("inconsistent trading rules")


@dataclass(frozen=True)
class Position:
    quantity: D = ZERO  # signed USD contracts; negative = short
    entry: D = ZERO
    margin_btc: D = ZERO
    liquidation: D = ZERO
    take_profit: D = ZERO
    stop_loss: D = ZERO
    leverage: D = D(20)
    index: int = 0

    def pnl(self, mark: D) -> D:
        if self.quantity == 0:
            return ZERO
        if self.entry <= 0 or mark <= 0:
            raise Blocked("non-flat position lacks entry or mark")
        return self.quantity * (1 / self.entry - 1 / mark)


@dataclass(frozen=True)
class Snapshot:
    account_id: str
    time: int
    wallet_btc: D
    available_btc: D
    mark: D
    bid: D
    ask: D
    buy_depth_usd: D
    sell_depth_usd: D
    position: Position
    rules: Rules
    orders: tuple[dict, ...] = ()
    fills: tuple[dict, ...] = ()
    margin_mode: str = "ISOLATED_MARGIN"
    funding_rate: D = ZERO

    @property
    def equity_btc(self) -> D:
        return self.wallet_btc + self.position.pnl(self.mark)

    @property
    def equity_usd(self) -> D:
        return self.equity_btc * self.mark

    def validate(self) -> None:
        for key in ("mark", "bid", "ask", "wallet_btc"):
            number(getattr(self, key), key, positive=True)
        for key in ("available_btc", "buy_depth_usd", "sell_depth_usd"):
            if number(getattr(self, key), key) < 0:
                raise Blocked(f"negative {key}")
        if self.bid > self.ask or self.equity_btc <= 0 or not self.account_id:
            raise Blocked("inconsistent account or quotation")
        if self.margin_mode != "ISOLATED_MARGIN":
            raise Blocked("account is not isolated; no automatic mode change")
        if self.position.index != 0 or self.position.leverage != 20:
            raise Blocked("one-way BTC position with leverage 20 is required")
        if self.position.quantity and (self.position.entry <= 0 or self.position.liquidation <= 0):
            raise Blocked("position entry or liquidation is unknown")
        if self.rules.status != "Trading":
            raise Blocked("instrument is not trading")
        if any(o.get("symbol") != SYMBOL for o in self.orders):
            raise Blocked("out-of-scope order in BTC snapshot")


@dataclass(frozen=True)
class Target:
    candle: int
    quantity: D  # signed USD contracts, not BTC
    entry: D
    take_profit: D
    stop_loss: D
    initial_margin_btc: D
    allocated_margin_btc: D
    risk_btc: D
    reason: str

    @property
    def direction(self) -> str:
        return "long" if self.quantity > 0 else "short" if self.quantity < 0 else "flat"


@dataclass(frozen=True)
class ModelConfig:
    trend_bars: int = 120
    channel_bars: int = 24
    atr_bars: int = 24
    risk_fraction: D = D("0.006")
    atr_multiple: D = D("2")
    reward_multiple: D = D("3")
    max_effective_leverage: D = D("2")
    liquidity_fraction: D = D("0.05")
    slippage_fraction: D = D("0.001")

    def __post_init__(self) -> None:
        if not 2 <= self.atr_bars <= self.trend_bars <= 500 or not 2 <= self.channel_bars <= 500:
            raise Blocked("invalid indicator periods")
        for name in ("risk_fraction", "liquidity_fraction", "slippage_fraction"):
            if not ZERO < getattr(self, name) < 1:
                raise Blocked(f"invalid {name}")
        if not ZERO < self.max_effective_leverage <= 20:
            raise Blocked("effective leverage must be in (0,20]")
        if self.atr_multiple <= 0 or self.reward_multiple <= 0:
            raise Blocked("invalid protection multiples")
