"""Copy closed registered evidence without rewriting receipts or making adoption claims.

Run only after finance, controllers, audits and the public-vault observer have stopped.
Required artifacts and PATH=SHA256 pins identify the operator's separately reviewed
final bridge, adoption decision and zero-event diaries; this copier does not review
those decisions. Supply each with both flags. Only scratch/review files are accepted.
The manifest excludes itself; the copied tool is included with its unchanged hash.
A failure after copying starts leaves an incomplete directory without a manifest.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile

SCRATCH = Path('/workspace/scratch/alpha-beta-next')
REVIEW = Path('/workspace/btc-alpha-beta-next/review')
LIMIT = 100 * 1024 * 1024
PARTIALS = {'perp-singletons.json.progress.json',
            'sensitivity-incumbent-9900-0.json.progress.json',
            'retry-observed-session288-progress.json'}
DOC_PINS = {'SPOT-RESULT.md': '6f8f348efd8eee53d7dba22c2fbd3e64ecacd52464daabddceead0d1bd74bb27',
            'COIN-RESULT.md': '9caa563c2c282c32ba19dd28071813e0a4d0decd7036ab89d74d30e80ddfd937'}
CANDIDATES = {'spot': ('consensus', 'trend-reentry', 'target-participation', 'atr-close',
                       'atr-stop', 'core-permanent', 'core-slow'),
              'perp': ('incumbent', 'fresh-entry', 'atr-trail', 'compression-breakout', 'single-topup')}
SCENARIOS = {'spot': ('base', 'fee150', 'slip2', 'outage'),
             'perp': ('base', 'fees-x1.5', 'read-400ms', 'trigger-slip')}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def absolute(path):
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts, 'absolute non-escaping path required: ' + str(path))
    for parent in (path, *path.parents):
        require(not parent.is_symlink(), 'symlink forbidden: ' + str(parent))
    return path


def regular(path):
    absolute(path)
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_size < LIMIT, 'special or >=100MiB file: ' + str(path))
    return info


def signature(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def fingerprint(path):
    before = signature(regular(path))
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        require(signature(os.fstat(stream.fileno())) == before, 'file changed before reading: ' + str(path))
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    require(signature(path.stat()) == before, 'file changed while reading: ' + str(path))
    return {'sha256': digest.hexdigest(), 'size': before[3]}


def read(path):
    regular(path)
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key in ' + str(path))
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=pairs)


def stopped():
    """Fail closed on relevant live processes; zombies have already exited."""
    blocked = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        try:
            status = (proc / 'stat').read_text().rsplit(')', 1)[1].split()[0]
            if status == 'Z':
                continue
            args = (proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
            relevant = re.search(r'research\.(alpha_|complete_|adoption_)|(?:run_registered_|run_spot_registered|audit_remaining_|audit_singles_|independent_financial_audit|public_print_vault\.py)', args)
            # Python audit helpers and controllers launched from the evidence roots.
            cwd = (proc / 'cwd').resolve()
            local_python = 'python' in (proc / 'comm').read_text().lower() and any(
                cwd.is_relative_to(root) or str(root) + '/' in args
                for root in (SCRATCH, REVIEW, REVIEW.parent / 'spotquant', REVIEW.parent / 'coinquant'))
            if relevant or local_python:
                blocked.append(int(proc.name))
        except (FileNotFoundError, ProcessLookupError):
            continue
    require(not blocked, 'active financial/controller/audit/watch processes: ' + str(blocked))


def excluded(relative):
    lower = [part.lower() for part in relative.parts]
    return (any(part in ('__pycache__', 'cache', '.cache', '.pytest_cache', 'tmp', 'state', '.git') for part in lower)
            or relative.suffix.lower() in ('.zip', '.bin', '.pyc', '.tmp')
            or relative.name.lower().endswith('.zip.checksum')
            or ('progress' in relative.name.lower() and relative.as_posix() not in PARTIALS))


def inventory(required):
    files = {}
    def add(path, root, prefix):
        relative = path.relative_to(root)
        require(not excluded(relative), 'excluded required evidence: ' + str(path))
        regular(path)
        target = (Path(prefix) / relative).as_posix()
        require(target not in files, 'duplicate archive path: ' + target)
        files[target] = path
    def walk(folder, root, prefix, flat=False, json_only=False):
        absolute(folder)
        require(folder.is_dir(), 'missing evidence directory: ' + str(folder))
        for path in sorted(folder.iterdir()):
            rel = path.relative_to(root)
            if excluded(rel):
                continue
            absolute(path)
            if path.is_dir():
                if not flat:
                    walk(path, root, prefix)
            elif not json_only or path.suffix == '.json':
                add(path, root, prefix)
    for path in sorted(SCRATCH.iterdir()):
        if excluded(path.relative_to(SCRATCH)):
            continue
        absolute(path)
        if not path.is_dir() and path.suffix in ('.json', '.gz', '.csv', '.md', '.log'):
            require(path.suffix != '.gz' or path.name.endswith('.json.gz'), 'non-JSON gzip input')
            add(path, SCRATCH, 'scratch')
    for name in ('spot-singletons', 'spot-canonical'):
        walk(SCRATCH / name, SCRATCH, 'scratch', flat=True)
    if (SCRATCH / 'figures').exists():
        walk(SCRATCH / 'figures', SCRATCH, 'scratch')
    walk(SCRATCH / 'public-print-vault' / 'records', SCRATCH, 'scratch', flat=True, json_only=True)
    walk(REVIEW, REVIEW, 'review')
    for path in required:
        root = next((root for root in (SCRATCH, REVIEW) if path.is_relative_to(root)), None)
        require(root is not None, 'required artifact outside evidence roots')
        target = ('scratch/' if root == SCRATCH else 'review/') + path.relative_to(root).as_posix()
        if target not in files:
            add(path, root, 'scratch' if root == SCRATCH else 'review')
    for name in PARTIALS:
        require('scratch/' + name in files, 'missing operational-incomplete evidence: ' + name)
    require(any(key.startswith('scratch/public-print-vault/records/') for key in files), 'missing public vault records')
    require('scratch/public-print-vault-watch.log' in files, 'missing observer log')
    return files


def validate(files, snapshots, required, pins):
    by_source = {str(path): snapshots[target] for target, path in files.items()}
    def bound(path, digest):
        require(str(path) in by_source and by_source[str(path)]['sha256'] == digest,
                'missing or changed bound evidence: ' + str(path))
    for path in required:
        require(str(path) in pins, 'required artifact missing reviewed SHA256: ' + str(path))
    require(set(pins) == {str(p) for p in required}, 'pins must exactly cover required artifacts')
    for path, digest in pins.items():
        bound(path, digest)
    for name, digest in DOC_PINS.items():
        bound(REVIEW / name, digest)
    require(by_source[str(REVIEW / 'pack_completed_evidence.py')] == fingerprint(Path(__file__).absolute()),
            'copied tool differs from executing tool')
    canonical = read(SCRATCH / 'spot-canonical' / 'canonical-inventory.json')
    require(len(canonical['files']) == 5 and {entry['label'] for entry in canonical['files']} ==
            {'base', 'fee150', 'slip2', 'outage', 'calibrated-base'}, 'missing canonical five')
    for entry in canonical['files']:
        child = Path(entry['path'])
        label = entry['label']
        require(entry['path'] == label + '.json.gz', 'canonical label/path mismatch')
        require(entry['calibrated'] is (label == 'calibrated-base') and
                entry['scenario'] == ('base' if label == 'calibrated-base' else label),
                'canonical scenario/calibration mismatch')
        bound(SCRATCH / 'spot-canonical' / child, entry['sha256'])
    final_path = SCRATCH / 'registered-final.json'
    final = read(final_path)
    receipt = read(SCRATCH / 'registered-final.command.json')
    require(type(receipt['exit_code']) is int and receipt['exit_code'] == 0, 'final command did not exit zero')
    command = receipt['command']
    require(command.count('--out') == 1 and command[command.index('--out') + 1] == str(final_path)
            and '--final' in command, 'wrong final command output or missing --final')
    bound(final_path, receipt['output_sha256'])
    bound(SCRATCH / 'registered-final.run.log', receipt['log_sha256'])
    require(all(final[key] is True for key in ('rules_freeze_ready', 'all_measured_accounts_valid')),
            'final is not valid and freeze-ready')
    require(final['pending'] == [] and final['sensitivity_missing'] == [] and
            all(final[key] is False for key in ('registered_work_pending', 'risk_accounts_pending')),
            'final still pending')
    require(all(type(final[key]) is int and final[key] == 0 for key in ('native_cases', 'actual_account_days')),
            'nonzero or missing native/account-day claims')
    require(len(final['accounts']) == 60 and len(final['sensitivity']) == 4, 'expected 60 accounts plus 4 sensitivities')
    for entry in final['inputs'].values():
        bound(entry['path'], entry['raw_sha256'])
    expected = set()
    unscaled = {(kind, 'unscaled', candidate + '/' + scene) for kind in CANDIDATES
                for candidate in CANDIDATES[kind] for scene in SCENARIOS[kind]}
    for key, account in final['accounts'].items():
        require(account['valid'] is True, 'invalid final account')
        parts = key.split('/')
        kind, stage = parts[0], 'risk' if len(parts) == 4 and parts[1] == 'risk' else 'unscaled'
        identity = (kind, stage, account['candidate'] + '/' + account['scenario'])
        require(key == kind + ('/risk/' if stage == 'risk' else '/') + identity[2], 'account identity mismatch')
        expected.add((*identity, account['raw_bundle_sha256']))
    require({row[:3] for row in expected if row[1] == 'unscaled'} == unscaled, 'not the registered unscaled 48')
    require({row[:3] for row in expected if row[1] == 'risk'} ==
            {(kind, 'risk', candidate + '/base') for kind in CANDIDATES for candidate in CANDIDATES[kind]},
            'not all 12 registered risk accounts')
    for item in final['sensitivity']:
        account = item['account']
        require(account['valid'] is True and account['raw_bundle_sha256'] == item['raw_sha256'], 'invalid sensitivity')
        expected.add(('perp', 'sensitivity', account['candidate'] + '/' + account['scenario'], item['raw_sha256']))
    require(len(expected) == 64, 'duplicate final audit identities')
    actual = set()
    for stage, name, count in [('unscaled', 'financial-audit-unscaled-index.json', 48),
                               ('remaining', 'financial-audit-remaining-index.json', 16)]:
        index = read(REVIEW / name)
        require(index['account_count'] == count, 'incomplete independent audit count')
        if stage == 'remaining':
            bound(final_path, index['final_assessment_sha256'])
            require(all(index[k] is True for k in ('final_inventory_exactly_reconciled', 'all_examined_checks_passed', 'all_reported_complete')), 'remaining audits not closed')
        stage_count = 0
        for entry in index['audits']:
            path = Path(entry['path'] if stage == 'unscaled' else entry['audit_path'])
            bound(path, entry['sha256'] if stage == 'unscaled' else entry['audit_sha256'])
            audit = read(path)
            require(audit['all_examined_checks_passed'] is True and audit['all_reported_complete'] is True, 'audit not complete/pass')
            require(audit['raw_sha256'] == entry['raw_sha256'], 'audit raw identity mismatch')
            bound(audit['raw_path'], audit['raw_sha256'])
            kind, actual_stage = audit['kind'], 'unscaled' if stage == 'unscaled' else entry['stage']
            if stage == 'remaining':
                require(entry['kind'] == kind and entry['raw_path'] == audit['raw_path'] and
                        entry['account_keys'] == sorted(audit['accounts']) and entry['accounts'] == len(audit['accounts']) and
                        entry['all_checks_passed'] is True and entry['all_reported_complete'] is True, 'remaining index mismatch')
            for key, account in audit['accounts'].items():
                require(account['reported_complete'] is True and account['independent_checks_passed'] is True and not account['errors'], 'failed audited account')
                identity = (kind, actual_stage, key, audit['raw_sha256'])
                require(identity not in actual, 'duplicate audit identity')
                actual.add(identity)
                stage_count += 1
        require(stage_count == count, 'audit count differs from index')
    require(actual == expected, 'independent audited identities differ from final accounts/raw SHAs')
    return by_source[str(final_path)]['sha256']


def pack(output, required, pins):
    output = absolute(output)
    require(not output.exists(), 'output must be NEW')
    require(output.parent.is_dir() and not any(output.is_relative_to(root) for root in (SCRATCH, REVIEW)), 'output needs existing parent outside evidence roots')
    required = [absolute(path) for path in required]
    require(required and len(set(required)) == len(required), 'unique explicit required artifacts needed')
    stopped()
    files = inventory(required)
    snapshots = {target: fingerprint(path) for target, path in files.items()}
    final_sha = validate(files, snapshots, required, pins)
    stopped()
    output.mkdir()
    entries = []
    for target, source in files.items():
        destination = output / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        require(fingerprint(source) == snapshots[target], 'source changed before copy')
        digest = hashlib.sha256()
        with source.open('rb') as src, destination.open('xb') as dst:
            for block in iter(lambda: src.read(1024 * 1024), b''):
                dst.write(block)
                digest.update(block)
        after = fingerprint(source)
        copied = fingerprint(destination)
        require(after == copied == snapshots[target] and digest.hexdigest() == copied['sha256'], 'source/copy changed')
        entries.append({'original_absolute_path': str(source), 'archive_path': target,
                        **copied, 'source_before': snapshots[target], 'source_after': after,
                        'classification': 'operational-incomplete evidence; not a monetary account' if target in
                        {'scratch/' + name for name in PARTIALS} else 'preserved evidence'})
    stopped()
    require(files == inventory(required), 'evidence inventory changed during copy')
    for target, source in files.items():
        require(fingerprint(source) == fingerprint(output / target) == snapshots[target], 'evidence changed before manifest')
    manifest = {'format': 'completed-evidence-byte-copy-v1', 'final_assessment_sha256': final_sha,
                'required_reviewed_artifacts': pins, 'operator_requirement': 'Separately reviewed final bridge, adoption decision and zero-event diaries supplied explicitly; semantic review is outside this copier.',
                'adoption_inferred_by_copier': False, 'manifest_excludes_itself': True, 'tool_sha256': fingerprint(Path(__file__).absolute())['sha256'], 'files': entries}
    publish_manifest(output, manifest)
    return manifest


def publish_manifest(output, manifest):
    descriptor, name = tempfile.mkstemp(prefix='.MANIFEST.', suffix='.tmp', dir=output)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            json.dump(manifest, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        # A hard link publishes complete bytes atomically and fails if the target exists.
        os.link(temporary, output / 'MANIFEST.json')
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--required-artifact', action='append', required=True, type=Path)
    parser.add_argument('--required-sha256', action='append', required=True, metavar='ABSOLUTE_PATH=SHA256')
    args = parser.parse_args()
    pins = {}
    for text in args.required_sha256:
        path, digest = text.rsplit('=', 1)
        require(path not in pins and re.fullmatch('[0-9a-f]{64}', digest), 'duplicate/invalid required SHA256')
        pins[path] = digest
    result = pack(args.out, args.required_artifact, pins)
    print(json.dumps({'output': str(args.out), 'files': len(result['files']), 'adoption_inferred': False}))


if __name__ == '__main__':
    main()
