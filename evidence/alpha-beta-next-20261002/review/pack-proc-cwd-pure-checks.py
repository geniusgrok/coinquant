"""Pure /proc mocks only: no real process enumeration, packing or frozen imports."""
import hashlib
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

TOOL = Path(__file__).with_name('pack_completed_evidence.py')
spec = importlib.util.spec_from_file_location('copier', TOOL)
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


class MockPath:
    def __init__(self, record, field=None):
        self.record, self.field = record, field
        self.name = str(record['pid'])

    def __truediv__(self, field):
        return MockPath(self.record, field)

    def value(self):
        self.record['calls'].append(self.field)
        value = self.record[self.field]
        if isinstance(value, Exception):
            raise value
        return value

    def read_text(self):
        return self.value()

    def read_bytes(self):
        return self.value()

    def resolve(self):
        return self.value()


class MockProc:
    def __init__(self, records):
        self.records = records

    def iterdir(self):
        return iter(MockPath(record) for record in self.records)


def process(pid=200, comm='dockerd', args=b'/usr/bin/dockerd\0', cwd=None, status='S'):
    return {'pid': pid, 'stat': f'{pid} ({comm}) {status} 1 2 3', 'comm': comm,
            'cmdline': args, 'cwd': cwd if cwd is not None else PermissionError('cwd denied'), 'calls': []}


checks = []

def check(name, record, expected=None, untouched_cwd=False, untouched_all=False):
    def fake_path(path):
        assert path == '/proc', path
        return MockProc([record])
    with patch.object(a, 'Path', fake_path), patch.object(a.os, 'getpid', return_value=999):
        try:
            a.stopped()
        except Exception as error:
            assert expected is not None and isinstance(error, expected), (name, error)
        else:
            assert expected is None, name
    if untouched_cwd:
        assert 'cwd' not in record['calls'], (name, record['calls'])
    if untouched_all:
        assert record['calls'] == [], (name, record['calls'])
    checks.append(name)


check('inaccessible-nonpython-dockerd-ignored-without-cwd', process(), untouched_cwd=True)
check('relevant-nonpython-shell-blocked-without-cwd',
      process(comm='bash', args=b'/bin/bash\0-lc\0python -m research.alpha_perp\0'), ValueError, untouched_cwd=True)
check('local-python-blocked', process(comm='python3', args=b'python\0worker.py\0', cwd=a.REVIEW), ValueError)
check('inaccessible-python-cwd-fails-closed', process(comm='python3', args=b'python\0worker.py\0'), PermissionError)
check('relevant-python-inaccessible-cwd-fails-closed',
      process(comm='python3', args=b'python\0-m\0research.alpha_perp\0'), PermissionError)
record = process(comm='bash', args=PermissionError('cmdline denied'))
check('unreadable-command-fails-closed', record, PermissionError, untouched_cwd=True)
check('zombie-ignored-without-cwd', process(status='Z'), untouched_cwd=True)
check('current-process-ignored-without-metadata', process(pid=999), untouched_all=True)
check('unrelated-readable-python-unchanged', process(comm='python3', args=b'python\0worker.py\0', cwd=Path('/unrelated')))
print(json.dumps({'checks_passed': checks, 'helper_sha256': hashlib.sha256(TOOL.read_bytes()).hexdigest(),
                  'real_proc_reads': False, 'pack_executed': False, 'frozen_imports': False}))
