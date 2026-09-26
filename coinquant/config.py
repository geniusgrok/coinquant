"""One account, model and bounded-session configuration; never contains secrets."""
from dataclasses import dataclass, fields
import json
from pathlib import Path

from .types import Blocked


@dataclass(frozen=True)
class Config:
    account_uid: str
    state_dir: str
    session_seconds: int = 300
    poll_seconds: int = 5

    def __post_init__(self):
        if (not isinstance(self.account_uid, str) or not self.account_uid.isascii()
                or not self.account_uid.isdigit() or int(self.account_uid) <= 0
                or not isinstance(self.state_dir, str) or not self.state_dir.strip()):
            raise Blocked('explicit Binance UID and persistent state_dir required')
        if (type(self.session_seconds) is not int or not 1 <= self.session_seconds <= 86400
                or type(self.poll_seconds) is not int or not 1 <= self.poll_seconds <= 60
                or self.poll_seconds > self.session_seconds):
            raise Blocked('session must be 1..86400 seconds; poll 1..60 and no longer than session')


def load(path):
    try:
        data = json.loads(Path(path).read_text())
        if not isinstance(data, dict) or set(data) - {f.name for f in fields(Config)}:
            raise Blocked('unknown configuration field; no exchange/model switches')
        return Config(**data)
    except (OSError, ValueError, TypeError) as exc:
        raise Blocked('configuration cannot be read or validated') from exc
