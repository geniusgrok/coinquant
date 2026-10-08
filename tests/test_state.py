import json
import tempfile
import unittest
import unittest.mock

from coinquant.state import State, client_id
from coinquant.types import Blocked, Unknown


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

    def test_state_directory_keeps_its_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            with State(directory, 'live:123'):
                pass
            with self.assertRaises(Blocked):
                with State(directory, 'testnet:123'):
                    pass

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

    def test_deterministic_id_scope(self):
        self.assertTrue(client_id('live:123', 123, 'increase').startswith('cq-'))
        self.assertEqual(client_id('live:123', 123, 'increase'), client_id('live:123', 123, 'increase'))
        self.assertNotEqual(client_id('live:123', 123, 'increase'), client_id('testnet:123', 123, 'increase'))
        self.assertLessEqual(len(client_id('live:123', 123, 'increase')), 36)


class StateIntegrityTests(unittest.TestCase):

    def test_fresh_directory_needs_no_backup_and_newer_state_blocks(self):
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            with State(directory, 'live:123') as state:
                state.set('schema_version', 99)
            self.assertFalse(Path(directory, 'backups').exists())
            with self.assertRaises(Blocked):
                State(directory, 'live:123').__enter__()

    def test_damaged_database_blocks_instead_of_starting_empty(self):
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            with State(directory, 'live:123') as state:
                state.set('x', 1)
            Path(directory, 'intents.sqlite').write_bytes(b'not a database' * 100)
            with self.assertRaises(Blocked):
                State(directory, 'live:123').__enter__()

    def test_old_observations_move_to_an_archive_before_deletion(self):
        from pathlib import Path
        from coinquant import state as module
        with tempfile.TemporaryDirectory() as directory, unittest.mock.patch.object(module, 'OBSERVATION_KEEP', 5), \
                unittest.mock.patch.object(module, 'OBSERVATION_BATCH', 3):
            with State(directory, 'live:123') as state:
                for index in range(12):
                    state.report({'status': 'read_only', 'index': index})
                kept = state.db.execute('SELECT COUNT(*) FROM observations').fetchone()[0]
            archived = [json.loads(line) for line in Path(directory, 'observations-archive.jsonl').read_text().splitlines()]
            self.assertEqual(kept + len(archived), 12)
            self.assertLessEqual(kept, 8)
            self.assertEqual([a['report']['index'] for a in archived], list(range(len(archived))))
