import json
import tempfile
import unittest

from coinquant.state import State, client_id
from coinquant.types import Blocked, Unknown
from research.legacy.config import Config


class StateTests(unittest.TestCase):
    def test_exclusion_survives_database_commits(self):
        with tempfile.TemporaryDirectory() as directory:
            with State(directory, 'testnet:123') as first:
                first.set('candle', 123)
                with self.assertRaises(Blocked):
                    with State(directory, 'testnet:123'):
                        pass
            with State(directory, 'testnet:123') as next_run:
                self.assertEqual(next_run.get('candle'), 123)

    def test_identity_and_default_authorization(self):
        with tempfile.TemporaryDirectory() as directory:
            with State(directory, 'live:123'):
                pass
            with self.assertRaises(Blocked):
                with State(directory, 'testnet:123'):
                    pass
        with self.assertRaises(Blocked):
            Config().authorize('123', True)
        with self.assertRaises(Blocked):
            Config(account_uid='123', max_position_usd=10).authorize('123', False)

    def test_crash_recovery_does_not_duplicate_or_overwrite_intents(self):
        with tempfile.TemporaryDirectory() as directory:
            identity = client_id('live:123', 123, 'increase')
            with State(directory, 'live:123') as state:
                state.prepare(identity, 'order', {'quantity': 5})
            with State(directory, 'live:123') as state:
                self.assertEqual(state.pending()[0]['status'], 'unknown')
                with self.assertRaises(Unknown):
                    state.prepare(identity, 'order', {'quantity': 7})
                state.finish(identity, 'partial', {'filled': 2})
                self.assertEqual(len(state.pending()), 1)
                state.finish(identity, 'confirmed', {'filled': 2, 'cancelled_rest': True})
                self.assertEqual(state.pending(), [])
                with self.assertRaises(Unknown):
                    state.prepare(identity, 'order', {'quantity': 5})

    def test_atomic_report(self):
        with tempfile.TemporaryDirectory() as directory:
            with State(directory, 'testnet:123') as state:
                state.report({'status': 'unknown'})
                with open(state.directory / 'latest.json') as stream:
                    self.assertEqual(json.load(stream)['status'], 'unknown')

    def test_deterministic_id_scope(self):
        self.assertTrue(client_id('live:123', 123, 'increase').startswith('cq-'))
        self.assertEqual(client_id('live:123', 123, 'increase'), client_id('live:123', 123, 'increase'))
        self.assertNotEqual(client_id('live:123', 123, 'increase'), client_id('testnet:123', 123, 'increase'))
        self.assertLessEqual(len(client_id('live:123', 123, 'increase')), 36)
