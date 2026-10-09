"""Durable strategy state is checked before native recovery or cleanup."""
import hashlib
import json
import tempfile
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from coinquant.campaign import Campaign
from coinquant.config import Config
from coinquant.session import cycle, run
from coinquant.state import State
from coinquant.types import Blocked


def foreign_checkpoint():
    checkpoint = Campaign().checkpoint()
    checkpoint['body']['strategy'] = 'foreign'
    checkpoint['sha256'] = hashlib.sha256(json.dumps(checkpoint['body'], sort_keys=True).encode()).hexdigest()
    return checkpoint


class StrategyStateTests(TestCase):
    def test_foreign_strategy_rejects_before_exchange_access(self):
        old=Campaign().checkpoint()
        del old['body']['entry_fill']
        old['sha256']=hashlib.sha256(json.dumps(old['body'],sort_keys=True).encode()).hexdigest()
        for key, value in (('linear_campaign', foreign_checkpoint()), ('linear_campaign',old),
                           ('lifecycle_identity', 'foreign')):
            with tempfile.TemporaryDirectory() as folder, State(folder, 'binance:BTCUSDT:live:123') as state:
                state.set(key, value)
                with self.assertRaises(Blocked):
                    cycle(object(), state, '123', execute=True)

    def test_missing_checkpoint_cannot_recover_an_old_entry(self):
        with tempfile.TemporaryDirectory() as folder, State(folder, 'binance:BTCUSDT:live:123') as state:
            state.set('entry_plan', dict(campaign=10))
            with self.assertRaisesRegex(Blocked, 'lacks its strategy checkpoint'):
                cycle(object(), state, '123', execute=True)

    def test_foreign_strategy_blocks_run_before_cleanup_recovers_orders(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Config('123', folder, 300, 5)
            with State(folder, config.scope) as state:
                state.set('linear_campaign', foreign_checkpoint())
            reader = SimpleNamespace(environment='live', capital_limit=None, clock=lambda: 0)
            with patch('coinquant.session.Lifecycle') as engine:
                with self.assertRaises(Blocked):
                    run(config, reader, execute=True, monotonic=lambda: 0)
                engine.assert_not_called()
