"""Package completed research evidence; no market or production execution."""
import gzip
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
DIST = ROOT / 'dist'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    with (gzip.open(path, 'rt') if path.suffix == '.gz' else path.open()) as stream:
        return json.load(stream)


def describe(paths):
    return [{'path': str(path.relative_to(BASE)), 'bytes': path.stat().st_size,
             'sha256': sha(path)} for path in sorted(set(paths))]


def archive(path, files, inventory_name):
    inventory = describe(files)
    inventory_path = ROOT / inventory_name
    with inventory_path.open('x') as stream:
        json.dump({'files': inventory}, stream, indent=2)
        stream.write('\n')
    with tarfile.open(path, 'x:xz', preset=3) as target:
        for source in sorted(set(files + [inventory_path])):
            if source.is_symlink() or not source.is_file():
                raise ValueError('Only explicitly selected regular evidence files may be packaged')
            target.add(source, arcname=str(source.relative_to(BASE)), recursive=False)
    return {'name': path.name, 'path': str(path), 'bytes': path.stat().st_size,
            'sha256': sha(path), 'inventory': str(inventory_path), 'files': len(inventory) + 1}


def main():
    metrics = read(ROOT / 'metrics.json')
    audit = read(ROOT / 'full-audit-summary.json')
    if not metrics['economic_results_ready'] or not audit['passed'] or not audit['full795']:
        raise ValueError('Complete independently audited economic evidence is required')
    progress = read(ROOT / 'PROGRESS.json')
    for arm in ('previous', 'current'):
        receipt = read(Path(progress[arm]['receipt']))
        state = read(ROOT / f'state-audit-{arm}.json')
        if not (receipt['complete'] and receipt['original_window_complete'] and not receipt['failure']
                and receipt['session_count'] == 795 and state['passed']
                and state['receipt_sha256'] == sha(Path(progress[arm]['receipt']))):
            raise ValueError('Incomplete or unaudited arm: ' + arm)
    DIST.mkdir(exist_ok=False)
    names = ('PROTOCOL.md', 'ATTEMPTS.json', 'TRACE_FAILURE_DIAGNOSIS.json',
             'FIRST_ATTEMPT_PREFIX_COMPARISON.json', 'POSTPROCESSING_FIX.json', 'spec.json', 'PROGRESS.json',
             'FULL_COMMANDS.jsonl', 'full-audit.json', 'full-audit-summary.json',
             'state-audit-previous.json', 'state-audit-current.json', 'metrics.json', 'report-errors.json',
             'results-comparison.md', 'smoke-previous.json.gz', 'smoke-current.json.gz',
             'smoke-audit.json', 'smoke-audit-summary.json')
    public = [ROOT / name for name in names]
    public += list(ROOT.glob('full-*-segment-*.json.gz')) + list(ROOT.glob('full-*-segment-*.log'))
    for arm in ('previous', 'current'):
        run = ROOT / f'full-{arm}'
        public += [run / 'reports.jsonl', run / 'production-calls.jsonl']
        public += list((run / 'path-traces').glob('*.jsonl.gz'))
        public += list((run / 'checkpoints').glob('*.json.gz'))
        smoke = ROOT / f'smoke-{arm}'
        public += [smoke / 'reports.jsonl', smoke / 'production-calls.jsonl']
        public += list((smoke / 'path-traces').glob('*.jsonl.gz'))
    if any('state' in path.relative_to(ROOT).parts or 'sqlite' in path.name for path in public):
        raise ValueError('Account databases are excluded from public evidence')
    result = {'public': archive(DIST / 'coinquant-2.0.0-remeasurement-evidence-20261009.tar.xz',
                                public, 'EVIDENCE_FILES.json')}
    failed = BASE / 'coinquant-remeasure-2.0.0'
    private = list((failed / 'full-previous/state').rglob('*'))
    private += list((failed / 'full-previous/path-traces').glob('*.jsonl.gz'))
    private += list((failed / 'full-previous/checkpoints').glob('*.json.gz'))
    private += [failed / name for name in ('spec.json', 'PROTOCOL.md', 'FULL_COMMANDS.jsonl',
                 'run_pair.py', 'restored-input-identity.json', 'previous-source-files.json', 'current-source-files.json')]
    private += [path for path in (BASE / 'coinquant-remeasure-tooling').rglob('*')
                if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc']
    private += list(failed.glob('full-previous-segment-*.json.gz'))
    private += list(failed.glob('full-previous-segment-*.log'))
    private += [failed / 'full-previous/reports.jsonl', failed / 'full-previous/production-calls.jsonl',
                ROOT / 'ATTEMPTS.json', ROOT / 'TRACE_FAILURE_DIAGNOSIS.json']
    for arm in ('previous', 'current'):
        private += list((ROOT / f'full-{arm}/state').rglob('*'))
        private += [ROOT / f'state-audit-{arm}.json']
    private = [path for path in private if path.is_file() and not path.is_symlink()]
    result['private'] = archive(DIST / 'coinquant-2.0.0-simulated-state-20261009.tar.xz',
                                private, 'PRIVATE_STATE_FILES.json')
    (ROOT / 'PACKAGES.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
