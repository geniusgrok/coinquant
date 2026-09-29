"""One account, model and bounded-session configuration; never contains secrets."""
from dataclasses import dataclass, fields
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

from .types import Blocked

ENVIRONMENTS = ('live', 'demo')


def scope(environment, uid):
    """State and intent scope: one environment, one account, one symbol."""
    return f'binance:BTCUSDT:{environment}:{uid}'


@dataclass(frozen=True)
class Config:
    account_uid: str
    state_dir: str
    session_seconds: int = 300
    poll_seconds: int = 5
    # 'demo' is Binance's virtual-balance futures environment with its own hosts,
    # credentials and state scope; it never shares state with 'live'.
    environment: str = 'live'
    # Optional ceiling on the USDT the model may size from; the rest of the
    # wallet is not trial capital. A decimal string, or None for the whole wallet.
    capital_limit_usdt: str | None = None

    def __post_init__(self):
        if (not isinstance(self.account_uid, str) or not self.account_uid.isascii()
                or not self.account_uid.isdigit() or int(self.account_uid) <= 0
                or not isinstance(self.state_dir, str) or not self.state_dir.strip()):
            raise Blocked('explicit Binance UID and persistent state_dir required')
        if not Path(self.state_dir).expanduser().is_absolute():
            # A relative directory would silently become a new empty state from another working directory.
            raise Blocked('state_dir must be an absolute path (or start with ~)')
        if (type(self.session_seconds) is not int or not 1 <= self.session_seconds <= 86400
                or type(self.poll_seconds) is not int or not 1 <= self.poll_seconds <= 60
                or self.poll_seconds > self.session_seconds):
            raise Blocked('session must be 1..86400 seconds; poll 1..60 and no longer than session')
        if self.environment not in ENVIRONMENTS:
            raise Blocked('environment must be live or demo')
        if self.capital_limit_usdt is not None:
            try:
                limit = Decimal(self.capital_limit_usdt) if isinstance(self.capital_limit_usdt, str) else None
            except InvalidOperation:
                limit = None
            if limit is None or not limit.is_finite() or limit <= 0:
                raise Blocked('capital_limit_usdt must be a positive decimal string')

    @property
    def scope(self):
        return scope(self.environment, self.account_uid)

    @property
    def capital_limit(self):
        return None if self.capital_limit_usdt is None else Decimal(self.capital_limit_usdt)


def load(path):
    try:
        data = json.loads(Path(path).read_text())
        if not isinstance(data, dict) or set(data) - {f.name for f in fields(Config)}:
            raise Blocked('unknown configuration field; no exchange/model switches')
        return Config(**data)
    except (OSError, ValueError, TypeError) as exc:
        raise Blocked('configuration cannot be read or validated') from exc
