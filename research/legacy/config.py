"""Strict single current configuration; no credential values in this file."""
from dataclasses import dataclass, field, fields
from pathlib import Path
import json

from coinquant.types import Blocked, D, ModelConfig, number


@dataclass(frozen=True)
class Config:
    environment: str = 'testnet'
    api_host: str = ''
    account_uid: str = ''
    max_position_usd: D = D(0)
    state_dir: str = '~/.coinquant/testnet'
    model: ModelConfig = field(default_factory=ModelConfig)

    def __post_init__(self):
        if self.environment not in ('testnet', 'live'):
            raise Blocked('environment must explicitly be testnet or live')
        if not isinstance(self.api_host, str) or not isinstance(self.account_uid, str) or not isinstance(self.state_dir, str):
            raise Blocked('api_host, account_uid and state_dir must be strings')
        if '://' in self.api_host or '/' in self.api_host:
            raise Blocked('api_host must be an approved hostname, not a URL')
        if number(self.max_position_usd) < 0:
            raise Blocked('negative authorized position limit')

    def authorize(self, actual_uid: str, execute: bool) -> None:
        if not execute:
            raise Blocked('read-only invocation cannot send exchange writes')
        if not self.account_uid or self.account_uid != actual_uid:
            raise Blocked('explicit configured account UID does not match the exchange')
        if self.max_position_usd <= 0:
            raise Blocked('a positive account exposure authorization limit is required')


def load(path: str | Path) -> Config:
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        allowed = {f.name for f in fields(Config)}
        if not isinstance(data, dict) or set(data) - allowed:
            raise Blocked('unknown configuration field; no aliases or profile overrides')
        raw_model = data.pop('model', {})
        defaults = ModelConfig()
        names = {f.name for f in fields(ModelConfig)}
        if not isinstance(raw_model, dict) or set(raw_model) - names:
            raise Blocked('unknown model parameter')
        converted = {}
        for key, value in raw_model.items():
            if isinstance(getattr(defaults, key), int):
                if type(value) is not int:
                    raise Blocked('indicator periods must be integers')
                converted[key] = value
            else:
                converted[key] = number(value, key)
        if 'max_position_usd' in data:
            data['max_position_usd'] = number(data['max_position_usd'])
        return Config(**data, model=ModelConfig(**converted))
    except (OSError, ValueError, TypeError) as exc:
        raise Blocked('configuration cannot be read or validated') from exc
