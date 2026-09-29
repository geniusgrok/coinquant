"""Outcome types and decimal helpers shared by the Binance session path."""
from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from typing import Any

D = Decimal
ZERO = D(0)


class Blocked(RuntimeError):
    """A known prerequisite is unsatisfied; no new exposure is allowed."""


class Unknown(RuntimeError):
    """An exchange write or account observation has an uncertain outcome."""


class NotSent(Unknown):
    """The request was refused locally and never reached the exchange."""


class ObservationDeadline(NotSent):
    """The bounded observation/cleanup budget ran out before a request left; no write was made."""


class Rejected(Unknown):
    """The exchange definitively refused a write; nothing was executed."""


class Missing(Unknown):
    """An ordinary-order identity query answered -2013: no such order exists now."""


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
