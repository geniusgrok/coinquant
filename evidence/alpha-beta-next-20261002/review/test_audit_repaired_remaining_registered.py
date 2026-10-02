"""Temporary-fixture tests only: no producer/checker/network/State execution."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
SCRIPT = Path(__file__).with_name('audit_repaired_remaining_registered.py')
spec = importlib.util.spec_from_file_location('repair_audit', SCRIPT)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


class PureFixtures(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='coin-repair-audit-fixtures-')
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def put(self, name, value):
        p = self.root/name
        p.write_text(json.dumps(value))
        return p

    def original_projection(self):
        original = {'inputs': {'candidates': {n: [] if n == 'incumbent' else [n] for n in h.NAMES},
                               'risk_profiles': {n: {'scale': '1'} for n in h.NAMES}, 'source': h.COIN_SOURCE},
                    'results': {n: {'base': {'money': '12.3', 'journal': [{'quantity': '1.1'}]}} for n in h.NAMES},
                    'conditions': {'boundary': 123}}
        raw = self.put('original.json', original); receipt = self.put('original.command.json', {'output_sha256': h.sha(raw)})
        projected = copy.deepcopy(original)
        projected['results'] = {n: projected['results'][n] for n in h.RETAINED}
        projected['inputs']['candidates'] = {n: projected['inputs']['candidates'][n] for n in h.RETAINED}
        projected['derivation'] = {'kind': 'lossless-account-projection', 'original_bundle_path': str(raw),
            'original_bundle_sha256': h.sha(raw), 'original_receipt_path': str(receipt),
            'original_receipt_sha256': h.sha(receipt),
            'retained_row_sha256': {n+'/base': h.checksum(original['results'][n]['base']) for n in h.RETAINED}}
        return original, projected, raw, receipt

    def test_exact_projection_passes(self):
        args = self.original_projection()
        self.assertEqual(h.projection_check(*args), args[1]['derivation'])

    def test_projection_rejects_each_material_change(self):
        mutations = [lambda p: p['results']['atr-trail']['base'].update(money='12.4'),
                     lambda p: p['results']['atr-trail']['base']['journal'][0].update(quantity='2'),
                     lambda p: p['inputs']['candidates'].update({'atr-trail': ['hidden-component']}),
                     lambda p: p['inputs']['risk_profiles'].pop('incumbent'),
                     lambda p: p['inputs']['source'].update(dirty=True),
                     lambda p: p['conditions'].update(boundary=124),
                     lambda p: p['derivation'].update(original_bundle_sha256='0'*64),
                     lambda p: p['derivation']['retained_row_sha256'].update({'atr-trail/base': '0'*64}),
                     lambda p: p['results'].update(incumbent={'base': {}}),
                     lambda p: p.update(hidden_metadata='not allowed')]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                original, projected, raw, receipt = self.original_projection(); mutate(projected)
                with self.assertRaises(ValueError):
                    h.projection_check(original, projected, raw, receipt)

    def final(self):
        groups = dict.fromkeys(['financial', 'fills', 'daily', 'ownership', 'operating', 'remaining_original_fields'], True)
        final = {'analysis_source': copy.deepcopy(h.ANALYSIS_SOURCE), 'pending': [],
            'registered_work_pending': False, 'risk_accounts_pending': False, 'all_measured_accounts_valid': True,
            'rules_freeze_ready': True, 'actual_account_days': 0, 'native_cases': 0, 'prospective_alpha_proven': False,
            'risk_baseline_controls': {k: {'passed': True, 'rejections': [], 'evidence_checks': dict(groups)} for k in ['spot', 'perp']},
            'accounts': {}, 'sensitivity': []}
        for kind, names in [('spot', ['s'+str(i) for i in range(7)]), ('perp', sorted(h.NAMES))]:
            for name in names:
                for scene in ['base', 'fees', 'slippage', 'outage']:
                    final['accounts'][kind+'/'+name+'/'+scene] = {'candidate': name, 'scenario': scene,
                        'raw_bundle_sha256': kind+name, 'valid': True, 'rejections': []}
                final['accounts'][kind+'/risk/'+name+'/base'] = {'candidate': name, 'scenario': 'base',
                    'raw_bundle_sha256': kind+name+'risk', 'valid': True, 'rejections': []}
        for i in range(4):
            final['sensitivity'].append({'raw_sha256': str(i), 'account': {'candidate': 'incumbent', 'scenario': 'base',
                'raw_bundle_sha256': str(i), 'valid': True, 'rejections': []}})
        return final

    def test_complete_inventory_and_gates(self):
        final = self.final()
        self.assertEqual(len(h.final_gates(final, ['python', '--final'])), 16)
        self.assertEqual(len(h.identities(final, False)), 48)

    def test_final_rejects_flags_and_operating_failure(self):
        for field, value in [('pending', ['unfinished']), ('registered_work_pending', True),
                             ('risk_accounts_pending', True), ('all_measured_accounts_valid', False),
                             ('rules_freeze_ready', False), ('actual_account_days', 1),
                             ('native_cases', 1), ('prospective_alpha_proven', True)]:
            with self.subTest(field=field):
                final = self.final(); final[field] = value
                with self.assertRaises(ValueError): h.final_gates(final, ['--final'])
        for command in [[], ['--final', '--final']]:
            with self.assertRaises(ValueError): h.final_gates(self.final(), command)
        for groups in [{}, {'operating': True}, dict.fromkeys(['financial', 'fills', 'daily', 'ownership', 'operating', 'remaining_original_fields'], False)]:
            final = self.final(); final['risk_baseline_controls']['perp']['evidence_checks'] = groups
            with self.assertRaises(ValueError): h.final_gates(final, ['--final'])

    def test_inventory_rejects_invalid_duplicate_and_missing(self):
        final = self.final(); final['accounts']['perp/risk/incumbent/base']['valid'] = False
        with self.assertRaises(ValueError): h.identities(final)
        self.assertEqual(len(h.identities(final, require_valid=False)), 16)
        final = self.final(); final['sensitivity'][3] = copy.deepcopy(final['sensitivity'][0])
        with self.assertRaises(ValueError): h.identities(final)
        final = self.final(); final['accounts'].pop('perp/risk/incumbent/base')
        with self.assertRaises(ValueError): h.identities(final)
        final = self.final(); final['sensitivity'][0]['account']['raw_bundle_sha256'] = 'changed'
        with self.assertRaises(ValueError): h.identities(final)

    def test_output_exclusive_and_symlink(self):
        with patch.object(h, 'REVIEW', self.root):
            target = self.root/'new.json'; h.exclusive(target)
            target.write_text('old')
            with self.assertRaises(ValueError): h.exclusive(target)
            link = self.root/'link.json'; link.symlink_to(self.root/'missing')
            with self.assertRaises(ValueError): h.exclusive(link)
            with self.assertRaises(ValueError): h.exclusive(Path('relative.json'))
            with self.assertRaises(ValueError): h.exclusive(self.root/'subdir'/'x.json')

    def test_receipt_binds_source_output_log_and_execution(self):
        raw = self.put('raw.json', {'account': 1}); log = self.put('run.log', {'completed': True})
        receipt = {'exit_code': 0, 'source_head': h.COIN_SOURCE['git_head'], 'cwd': str(h.COIN),
            'command': ['python', '-m', 'research.alpha_perp', '--out', str(raw)],
            'output_sha256': h.sha(raw), 'log_sha256': h.sha(log),
            'started_utc': '2026-10-02T12:00:00+00:00', 'elapsed_seconds': 1}
        rp = self.put('receipt.json', receipt)
        h.receipt(raw, rp, log, h.COIN_SOURCE, h.COIN, 'research.alpha_perp')
        for key, value in [('exit_code', 1), ('source_head', 'wrong'), ('output_sha256', '0'*64),
                           ('log_sha256', '0'*64), ('elapsed_seconds', 0), ('started_utc', '2026-10-02T12:00:00')]:
            bad = dict(receipt); bad[key] = value; self.put('receipt.json', bad)
            with self.subTest(key=key), self.assertRaises(ValueError):
                h.receipt(raw, rp, log, h.COIN_SOURCE, h.COIN, 'research.alpha_perp')

    def test_audit_reuse_exact_context_and_receipt(self):
        raw = self.put('raw.json', {'money': 1}); target = self.root/'audit.json'; log = self.put('audit.run.log', {'pass': True})
        report = {'raw_path': str(raw), 'raw_sha256': h.sha(raw), 'kind': 'perp', 'all_examined_checks_passed': True,
            'all_reported_complete': True, 'accounts': {'incumbent/base': {'reported_complete': True,
                'producer_audit_passed': True, 'independent_checks_passed': True, 'errors': []}}}
        self.put('audit.json', report)
        entry = {'raw_path': str(raw), 'raw_sha256': h.sha(raw), 'audit_path': str(target), 'audit_sha256': h.sha(target),
            'kind': 'perp', 'stage': 'sensitivity', 'account_keys': ['incumbent/base'], 'accounts': 1,
            'all_checks_passed': True, 'all_reported_complete': True}
        receipt = {'exit_code': 0, 'checker_sha256': h.CHECKER_SHA, 'log_sha256': h.sha(log), 'output_sha256': h.sha(target),
            'verification_context': {}, 'command': ['python', str(h.CHECKER), '--bundle', str(raw),
                '--sha256', h.sha(raw), '--kind', 'perp', '--out', str(target)]}
        self.put('audit.command.json', receipt); self.assertEqual(len(h.verify_audit(entry)), 1)
        for key, value in [('verification_context', {'calibration': {'path': 'wrong', 'sha256': '0'*64}}),
                           ('checker_sha256', '0'*64), ('exit_code', 1), ('output_sha256', '0'*64),
                           ('command', receipt['command']+['--ignored-option'])]:
            bad = copy.deepcopy(receipt); bad[key] = value; self.put('audit.command.json', bad)
            with self.subTest(key=key), self.assertRaises(ValueError): h.verify_audit(entry)

    def test_default_main_never_runs_audit_or_writes(self):
        with patch.object(sys, 'argv', ['helper', '--final-report', '/synthetic/final.json', '--out', '/synthetic/index.json']), \
             patch.object(h, 'preflight', return_value=({}, set(), [], {}, {}, None, None)), \
             patch.object(h, 'audit_one', side_effect=AssertionError('unexpected audit')), \
             patch.object(h, 'write', side_effect=AssertionError('unexpected output')):
            h.main()


if __name__ == '__main__':
    unittest.main(verbosity=2)
