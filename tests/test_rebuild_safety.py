"""Research writer safety: ownership, validation before mutation, and evidence protection."""
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from research import rebuild


class Harness:
    def call(self, tmp, **kwargs):
        base = SimpleNamespace(identity={'market': 'fake'}, loaded={})
        exchange = SimpleNamespace(prints=SimpleNamespace(loaded={}))
        options = dict(state=Path(tmp) / 'state')
        options.update(kwargs)
        with patch.object(rebuild, 'OUT', Path(tmp) / 'official'), \
                patch.object(rebuild, 'PARTIAL', Path(tmp) / 'partial'), \
                patch.object(rebuild, 'load_base', return_value=base), \
                patch.object(rebuild, 'run_account', return_value=({}, exchange)) as account:
            result = rebuild.trial('T', **options)
        return result, account


class StateOwnership(Harness, TestCase):
    def test_unmarked_directories_are_refused_and_left_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            foreign = Path(tmp) / 'foreign'
            foreign.mkdir()
            (foreign / 'keep.txt').write_text('mine')
            account = Path(tmp) / 'account'
            account.mkdir()
            (account / 'intents.sqlite').write_bytes(b'live account state')
            for target in (foreign, account):
                with self.assertRaises(ValueError):
                    self.call(tmp, state=target, limit=1)
            self.assertEqual((foreign / 'keep.txt').read_text(), 'mine')
            self.assertEqual((account / 'intents.sqlite').read_bytes(), b'live account state')

    def test_symbolic_links_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            real = Path(tmp) / 'real'
            real.mkdir()
            (real / 'keep.txt').write_text('mine')
            link = Path(tmp) / 'link'
            link.symlink_to(real, target_is_directory=True)
            with self.assertRaises(ValueError):
                self.call(tmp, state=link, limit=1)
            with self.assertRaises(ValueError):
                self.call(tmp, state=link / 'child', limit=1)
            self.assertEqual((real / 'keep.txt').read_text(), 'mine')

    def test_own_stale_directory_is_replaced_but_a_live_owner_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / 'state'
            state.mkdir()
            (state / rebuild.OWNER_MARKER).write_text(json.dumps(dict(run_id='old', pid=2 ** 22 + 12345)))
            (state / 'old.txt').write_text('old')
            self.call(tmp, limit=1)
            self.assertFalse((state / 'old.txt').exists())
            self.assertTrue((state / rebuild.OWNER_MARKER).is_file())
            (state / rebuild.OWNER_MARKER).write_text(json.dumps(dict(run_id='live', pid=os.getppid())))
            (state / 'live.txt').write_text('live')
            with self.assertRaises(ValueError):
                self.call(tmp, limit=1)
            self.assertTrue((state / 'live.txt').exists())

    def test_default_state_is_unique_per_run(self):
        first = rebuild.scratch_dir('T', 'a' * 8)
        second = rebuild.scratch_dir('T', 'b' * 8)
        self.assertNotEqual(first, second)
        self.assertEqual(first.parent, second.parent)

    def test_invalid_name_with_explicit_state_removes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / 'state'
            state.mkdir()
            (state / rebuild.OWNER_MARKER).write_text(json.dumps(dict(run_id='old', pid=2 ** 22 + 12345)))
            (state / 'keep.txt').write_text('kept')
            with self.assertRaises(ValueError):
                with patch.object(rebuild, 'load_base'):
                    rebuild.trial('../bad', state=state, limit=1)
            self.assertTrue((state / 'keep.txt').exists())


class EvidenceProtection(Harness, TestCase):
    def test_partial_results_never_enter_the_evidence_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            official = Path(tmp) / 'official'
            with self.assertRaises(ValueError):
                self.call(tmp, limit=2, out=official)
            self.assertFalse(official.exists())

    def test_same_name_needs_explicit_overwrite_and_keeps_the_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            official = Path(tmp) / 'official'
            first, _ = self.call(tmp)
            target = official / 'T.json'
            original = target.read_bytes()
            with self.assertRaises(ValueError):
                self.call(tmp)
            self.assertEqual(target.read_bytes(), original)
            second, account = self.call(tmp, overwrite=True)
            self.assertNotEqual(first['run_id'], second['run_id'])
            kept = [p for p in official.iterdir() if '.superseded-' in p.name]
            self.assertEqual(len(kept), 1)
            self.assertEqual(kept[0].read_bytes(), original)
            self.assertEqual(json.loads(target.read_text())['run_id'], second['run_id'])

    def test_refusal_happens_before_the_meter_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.call(tmp)
            with self.assertRaises(ValueError):
                _, account = self.call(tmp)
            self.assertFalse(list(Path(tmp).glob('official/*.partial')))

    def test_interrupted_publication_leaves_no_partial_result_named_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            official = Path(tmp) / 'official'
            self.call(tmp)
            original = (official / 'T.json').read_bytes()
            real = os.replace
            calls = []

            def failing(source, target):
                calls.append(target)
                if len(calls) == 2:
                    raise OSError('interrupted')
                return real(source, target)
            with patch('os.replace', failing):
                with self.assertRaises(OSError):
                    self.call(tmp, overwrite=True)
            survivors = [p.read_bytes() for p in official.iterdir() if p.suffix == '.json']
            self.assertIn(original, survivors)

    def test_unresolved_count_uses_the_session_report_field(self):
        rows = [dict(execution_unresolved=False, observation_timeouts=2),
                dict(execution_unresolved=True, observation_timeouts=0),
                dict(cleanup='unresolved', report_status='unknown')]
        base = SimpleNamespace(identity={'market': 'fake'}, loaded={})
        exchange = SimpleNamespace(prints=SimpleNamespace(loaded={}))
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(rebuild, 'OUT', Path(tmp) / 'official'), \
                patch.object(rebuild, 'PARTIAL', Path(tmp) / 'partial'), \
                patch.object(rebuild, 'load_base', return_value=base), \
                patch.object(rebuild, 'run_account', return_value=(dict(session_rows=rows), exchange)):
            result = rebuild.trial('T', state=Path(tmp) / 'state', limit=3)
        self.assertEqual(result['execution_unresolved'], 1)
        self.assertEqual(result['observation_timeouts'], 2)
