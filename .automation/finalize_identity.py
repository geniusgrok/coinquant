"""Finalize Coinquant contracts and current stored-file integrity metadata."""
from pathlib import Path
import hashlib
import json

root = Path.cwd()
p = root / 'evidence/linear-feasibility-20260921.md'
p.write_text(p.read_text().replace('reacquired. \n', 'reacquired.\n'))
p = root / 'coinquant/cli.py'
s = p.read_text().replace('argparse.ArgumentParser(description=', "argparse.ArgumentParser(prog='coinquant', description=")
p.write_text(s)

for name, old, new in (
    ('evidence/binance-linear-feasibility-20260921.md', 'Binance-only migration, verified read surface', 'Binance-only execution, verified read surface'),
    ('evidence/mechanisms-20260921/EXECUTION_STATUS.md', 'Binance 执行迁移', 'Binance 执行能力'),
    ('research/persistent_impulse_protocol.md', 'stop migration', 'stop adjustment'),
):
    p = root / name
    p.write_text(p.read_text().replace(old, new))

p = root / 'research/persistent_hold_replay.py'
s = p.read_text().replace("Path('research/spec.json'),", "Path('research/spec.json'),Path('research/invocation_draws.json'),")
p.write_text(s)
p = root / 'research/bounded_execution_replay.py'
s = p.read_text().replace("'research/spec.json')", "'research/spec.json', 'research/invocation_draws.json')")
p.write_text(s)

p = root / 'tests/test_frequency_schedule.py'
s = p.read_text().replace('import unittest\n', 'import unittest\nimport hashlib\nimport json\nfrom unittest.mock import patch\nfrom coinquant.types import Blocked\n')
s += '''

class FrozenInvocationTests(unittest.TestCase):
    def test_complete_normal_and_absence_sequences_are_fixed(self):
        expected = (
            (False, 795, 'f8fb73bebf142ddcc3ed4a3e6b12b4dd7abed1e27bcd8a4ff1c93aec4fe0b32a'),
            (True, 787, '7e368f55152e59d5e42a1288201d318994bb9854ffcdb397188cc2df1c256f0c'),
        )
        for stress, count, digest in expected:
            with self.subTest(stress=stress):
                calls = list(invocations(spec(), stress=stress))
                self.assertEqual(len(calls), count)
                raw = json.dumps(calls, separators=(',', ':')).encode()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)

    def test_sequence_identity_mismatch_blocks_replay(self):
        value = dict(spec(), invocation_draws_sha256='0' * 64)
        with self.assertRaisesRegex(Blocked, 'identity invalid'):
            list(invocations(value))

    def test_missing_sequence_blocks_replay(self):
        value = spec()
        with patch('coinquant.research.Path.read_bytes', side_effect=OSError('missing')):
            with self.assertRaisesRegex(Blocked, 'sequence unavailable'):
                list(invocations(value))
'''
p.write_text(s)

p = root / 'tests/test_binance_cli.py'
s = p.read_text()
s += '''

    def test_missing_named_credentials_blocks_before_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'config.json'
            config.write_text(json.dumps(dict(account_uid='123', state_dir=str(Path(tmp)/'state'))))
            with patch.dict('os.environ', {}, clear=True), patch('coinquant.cli.BinanceReadOnly') as venue:
                with self.assertRaisesRegex(Blocked, 'read credentials required'):
                    observe(config)
                venue.assert_not_called()
'''
p.write_text(s)

# This operational index describes stored files, not newly measured strategy results.
p = root / 'evidence/attention-lag7-account-20260922/multipart-manifest.json'
index = json.loads(p.read_text())
index['measurement_commit'] = index.pop('source_commit')
index['measurement_tree'] = index.pop('source_tree')
index['file_index_scope'] = 'Current stored file bytes; economic result source identities refer to their recorded measurements.'
for row in index['files']:
    file = root / row['path']
    if file.is_file():
        data = file.read_bytes()
        row['size'] = len(data)
        row['sha256'] = hashlib.sha256(data).hexdigest()
        row['git_blob'] = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
p.write_text(json.dumps(index, indent=2) + '\n')
