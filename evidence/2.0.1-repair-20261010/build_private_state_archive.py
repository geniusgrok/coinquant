"""Prepare the final private archive of twelve simulated-account state directories.

Run only after every replay process has stopped and all four final full cases
have completed 795 sessions with paired independent audits. Merely importing
this module has no side effects. This script does not run a replay, open SQLite,
checkpoint WAL, repair state, invoke account code, or contact any service.

Root's final execution command:
    python diagnosis/build_private_state_archive.py --execute-after-replays-stop

The archive and PRIVATE_ARCHIVE.json are private artifacts, not public evidence.
Existing output files are never overwritten. Compression is deterministic XZ
preset 1 with canonical tar headers, sorted members, and a per-file manifest.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import fcntl
import gzip
import hashlib
import io
import json
import lzma
import os
from pathlib import Path
import re
import stat
import tarfile


ROOT = Path(__file__).resolve().parent
REPLAYS = ROOT / 'replays'
ARCHIVE_STEM = 'coinquant-2.0.1-simulated-state-20261010'
STATE_FILES = frozenset({
    'intents.sqlite', 'intents.sqlite-wal', 'intents.sqlite-shm',
    'intents.sqlite-journal', 'observations-archive.jsonl', 'latest.json',
    'execution.lock',
})
REQUIRED_STATE_FILES = frozenset({'intents.sqlite', 'latest.json', 'execution.lock'})
# The failed first retry is preserved separately. Only retry 002 is a final arm.
RUNS = (
    ('margin-only', 'smoke-current', 'smoke'),
    ('margin-only', 'full-current', 'interrupted_incomplete'),
    ('margin-only-rerun-001', 'full-current', 'restore_failed_incomplete'),
    ('margin-only-rerun-002', 'full-current', 'final_full'),
    ('combined', 'smoke-current', 'retired_v1_smoke'),
    ('combined-v2', 'smoke-current', 'smoke'),
    ('combined-v2', 'full-current', 'final_full'),
    ('book-only', 'smoke-current', 'retired_v1_smoke'),
    ('book-v2-only', 'smoke-current', 'smoke'),
    ('book-v2-only', 'full-current', 'final_full'),
    ('combined-v3', 'smoke-current', 'smoke'),
    ('combined-v3', 'full-current', 'final_full'),
)
FINAL_CASES = frozenset({'margin-only-rerun-002', 'book-v2-only', 'combined-v2', 'combined-v3'})
BLOCK = 1024 * 1024


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def relative(path):
    return str(Path(path).relative_to(ROOT))


def regular_open(path):
    """Open a pre-existing regular file without following a leaf symlink."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        require(stat.S_ISREG(os.fstat(descriptor).st_mode), f'Not a regular file: {relative(path)}')
        return os.fdopen(descriptor, 'rb')
    except BaseException:
        os.close(descriptor)
        raise


def fingerprint(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def digest_file(path):
    with regular_open(path) as stream:
        before = fingerprint(os.fstat(stream.fileno()))
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        require(fingerprint(os.fstat(stream.fileno())) == before,
                f'File changed while hashing: {relative(path)}')
    return dict(path=relative(path), bytes=before[2], sha256=digest), before


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def load_json(path):
    with regular_open(path) as stream:
        return json.load(stream)


def load_receipt(path):
    with regular_open(path) as raw:
        with gzip.GzipFile(fileobj=raw, mode='rb') as decoded:
            return json.load(decoded)


def state_inventory():
    inventory = []
    for case, run, role in RUNS:
        directory = REPLAYS / case / run / 'state'
        require(directory.is_dir(), f'Required state directory missing: {relative(directory)}')
        require(directory.resolve() == directory,
                f'Symlinked state path is not permitted: {relative(directory)}')
        paths = sorted(directory.iterdir())
        names = {path.name for path in paths}
        require(REQUIRED_STATE_FILES <= names, f'Missing required state files: {relative(directory)}')
        require(names <= STATE_FILES, f'Unexpected files in state directory: {relative(directory)}')
        require(all(stat.S_ISREG(path.lstat().st_mode) for path in paths),
                f'Non-regular file or symlink in state directory: {relative(directory)}')
        inventory.append(dict(case=case, run=run, role=role, directory=directory, paths=paths))
    require(len(inventory) == 12, 'The registered archive must contain twelve state directories')
    return inventory


def assert_no_replay_or_writer(state_directories):
    """Read-only Linux process inspection; never print arguments or environments."""
    proc = Path('/proc')
    require(proc.is_dir(), 'Linux /proc is required to verify replay quiescence')
    failures = []
    runners = {'run_pair.py', 'run_one_segment.py', 'run_remaining.py', 'driver.py'}
    for process in sorted(proc.iterdir(), key=lambda p: p.name):
        if not process.name.isdigit() or int(process.name) == os.getpid():
            continue
        try:
            command = (process / 'cmdline').read_bytes().split(b'\0')
            arguments = [part.decode(errors='replace') for part in command if part]
            if not arguments:
                continue  # Reaped/zombie or kernel process, no userspace writer.
            cwd = os.readlink(process / 'cwd')
            related = str(ROOT.parent) in cwd or any(str(ROOT.parent) in arg for arg in arguments)
            runner = any(Path(arg).name in runners for arg in arguments)
            account_module = any(arg in ('coinquant', 'coinquant.cli', 'coinquant.__main__')
                                 for arg in arguments)
            if related and (runner or account_module):
                failures.append(dict(pid=int(process.name), reason='replay_or_account_process'))
            for descriptor in (process / 'fd').iterdir():
                try:
                    target = os.readlink(descriptor).removesuffix(' (deleted)')
                    if not any(target == str(path) or target.startswith(str(path) + '/')
                               for path in state_directories):
                        continue
                    info = (process / 'fdinfo' / descriptor.name).read_text()
                    flags = next(line.split()[1] for line in info.splitlines() if line.startswith('flags:'))
                    if int(flags, 8) & os.O_ACCMODE != os.O_RDONLY:
                        failures.append(dict(pid=int(process.name), reason='writable_state_descriptor'))
                except FileNotFoundError:
                    continue
        except (FileNotFoundError, ProcessLookupError):
            continue
        except PermissionError as error:
            raise RuntimeError(f'Cannot verify process {process.name}; no archive created') from error
    require(not failures, 'Replay quiescence failed: ' + json.dumps(failures, sort_keys=True))


def hold_existing_locks(stack, inventory):
    paths = {row['directory'] / 'execution.lock' for row in inventory}
    paths.update(path for case in {row['case'] for row in inventory}
                 if (path := REPLAYS / case / '.controller.lock').exists())
    for path in sorted(paths):
        stream = stack.enter_context(regular_open(path))
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError(f'Runtime lock is held: {relative(path)}') from error
    return len(paths)


def verify_registration(case, remember):
    directory = REPLAYS / case
    registration_path, spec_path = directory / 'REGISTRATION.json', directory / 'spec.json'
    registration, spec = load_json(registration_path), load_json(spec_path)
    registration_meta, spec_meta = remember(registration_path), remember(spec_path)
    expected_case = 'margin-only' if case.startswith('margin-only-rerun-') else case
    require(registration['case'] == expected_case, f'Registration case mismatch: {case}')
    require(re.fullmatch(r'[0-9a-f]{40}', registration['head']) is not None,
            f'Invalid registered head: {case}')
    require(spec_meta['sha256'] == registration['spec_sha256'], f'Spec hash mismatch: {case}')
    require(spec['uid'] == '12000' and spec['session_count'] == 795
            and spec['initial_cny'] == '10000', f'Not the registered simulation spec: {case}')
    require(spec['runtime_heads']['current'] == registration['head']
            and spec['source_sha256_by_arm']['current'] == registration['source_sha256'],
            f'Source registration mismatch: {case}')
    return registration, spec, dict(registration=registration_meta, specification=spec_meta)


def verify_receipt_identity(receipt, registration, spec, case):
    require(receipt.get('no_live_account') is True and receipt.get('native_verified') is False,
            f'Receipt is not the registered simulated account: {case}')
    require(receipt['source']['git_head'] == registration['head']
            and receipt['source']['source_sha256'] == registration['source_sha256']
            and receipt['source']['producer_sha256'] == registration['producer_sha256'],
            f'Receipt source mismatch: {case}')
    require(receipt['inputs']['specification_sha256'] == registration['spec_sha256']
            and receipt['terminal_ms'] == spec['terminal_ms'], f'Receipt spec mismatch: {case}')


def checked_local_path(value, directory, description):
    path = Path(value)
    if not path.is_absolute():
        path = directory / path
    require(path.resolve().parent == directory.resolve() and path.resolve() == path,
            f'{description} must refer to a regular file inside its case directory')
    return path


def audit_and_receipt(case, run, full, registration, spec, remember):
    directory = REPLAYS / case
    audit_path = directory / ('full-audit-summary.json' if full else 'smoke-audit-summary.json')
    audit = load_json(audit_path)
    expected_count = 795 if full else 6
    require(audit.get('passed') is True and audit.get('full795') is full,
            f'Required independent audit did not pass: {case}/{run}')
    candidate = audit['candidate']
    require(candidate['sessions'] == expected_count and candidate['financial']['passed'] is True
            and candidate['path_audit']['passed'] is True, f'Incomplete audit: {case}/{run}')
    require(audit['auditor_sha256'] == remember(ROOT / 'independent_financial_audit.py')['sha256']
            and audit['helper_sha256'] == remember(ROOT / 'original_compare_arms.py')['sha256'],
            f'Auditor identity mismatch: {case}/{run}')
    detail_path = checked_local_path(audit['detail']['path'], directory, 'Audit detail')
    detail_meta = remember(detail_path)
    require(detail_meta['sha256'] == audit['detail']['sha256']
            and detail_meta['bytes'] == audit['detail']['bytes'], f'Audit detail hash mismatch: {case}/{run}')
    detail = load_json(detail_path)
    require(all(detail.get(key) == audit.get(key) for key in
                ('passed', 'full795', 'auditor_sha256', 'helper_sha256', 'main', 'candidate')),
            f'Audit summary does not match its detail: {case}/{run}')
    receipt_path = checked_local_path(candidate['receipt'], directory, 'Audited receipt')
    expected_name = (r'full-current-segment-[0-9]+\.json\.gz' if full else r'smoke-current\.json\.gz')
    require(re.fullmatch(expected_name, receipt_path.name) is not None, f'Wrong receipt scope: {case}/{run}')
    receipt_meta = remember(receipt_path)
    require(receipt_meta['sha256'] == candidate['receipt_sha256'], f'Unpaired receipt hash: {case}/{run}')
    receipt = load_receipt(receipt_path)
    verify_receipt_identity(receipt, registration, spec, case)
    require(receipt['complete'] is True and receipt['failure'] is None
            and receipt['session_count'] == expected_count, f'Incomplete receipt: {case}/{run}')
    if full:
        require(receipt['at_ms'] == receipt['terminal_ms']
                and len(receipt['financial']['daily']) == 2455,
                f'Full window has not reached its terminal valuation: {case}')
    reports_path = directory / run / 'reports.jsonl'
    require(Path(receipt['reports']['path']).resolve() == reports_path,
            f'Receipt points to a different run: {case}/{run}')
    reports_meta = remember(reports_path)
    with regular_open(reports_path) as stream:
        reports_count = sum(1 for _ in stream)
    require(receipt['reports']['count'] == reports_count == expected_count
            and reports_meta['sha256'] == receipt['reports']['sha256'] == candidate['reports_sha256'],
            f'Final reports changed or incomplete: {case}/{run}')
    calls_meta = remember(directory / run / 'production-calls.jsonl')
    require(calls_meta['sha256'] == candidate['production_calls_sha256'],
            f'Production-call evidence changed: {case}/{run}')
    return dict(status='complete_795' if full else 'smoke_complete_6',
                complete_full795=full, observed_report_count=reports_count,
                source_head=registration['head'], receipt=receipt_meta,
                receipt_session_count=receipt['session_count'], failure=None,
                audit_summary=remember(audit_path), audit_detail=detail_meta,
                reports=reports_meta, production_calls=calls_meta)


def incomplete_run(case, role, registration, spec, remember):
    directory = REPLAYS / case
    reports_path = directory / 'full-current/reports.jsonl'
    reports_meta = remember(reports_path)
    with regular_open(reports_path) as stream:
        actual_count = sum(1 for _ in stream)
    require(0 < actual_count < 795, f'Expected an incomplete report stream: {case}')
    records = []
    for path in sorted(directory.glob('full-current-segment-*.json.gz')):
        receipt = load_receipt(path)
        verify_receipt_identity(receipt, registration, spec, case)
        require(receipt.get('complete') is not True,
                f'An incomplete archive role now has a complete receipt: {case}')
        records.append(dict(receipt=remember(path),
            session_count=receipt.get('session_count'), failure=receipt.get('failure'),
            complete=receipt.get('complete'), can_resume=receipt.get('can_resume'),
            claimed_reports=receipt.get('reports'), stop_reason=receipt.get('stop_reason')))
    require(records, f'No preserved partial receipts: {case}')
    safe_records = [row for row in records if row['failure'] is None and row['session_count']]
    require(safe_records, f'No preserved safe-boundary receipt: {case}')
    latest_safe = max(safe_records, key=lambda row: row['session_count'])
    expected_disk, expected_safe = (788, 726) if case == 'margin-only' else (709, 711)
    require(actual_count == expected_disk and latest_safe['session_count'] == expected_safe,
            f'Interrupted-run evidence changed; review its classification: {case}')
    if case == 'margin-only-rerun-001':
        require(any(isinstance(row['failure'], dict)
                    and row['failure'].get('phase') == 'restore'
                    and row['can_resume'] is False for row in records),
                'The first retry restore-failure receipt must be preserved')
    if (directory / 'full-audit-summary.json').exists():
        audit = load_json(directory / 'full-audit-summary.json')
        require(not (audit.get('passed') is True and audit.get('full795') is True),
                f'An incomplete archive role has a successful full audit: {case}')
        remember(directory / 'full-audit-summary.json')
    reason = ('Original process disappeared after 788 reports; last safe segment 002 claimed 726. '
              'No final segment 003 receipt; state preserved as incomplete.' if case == 'margin-only' else
              'First cold retry failed restoration: the safe checkpoint claimed 711 reports while '
              'the preserved disk report stream contained 709. Segment 003 restore failure and all '
              'original state are retained. This archive does not repair or declare them restorable.')
    return dict(status=role, complete_full795=False, source_head=registration['head'],
                observed_report_count=actual_count, reports=reports_meta,
                latest_safe_receipt=latest_safe['receipt'],
                latest_safe_receipt_session_count=latest_safe['session_count'],
                safe_receipt_minus_disk_reports=latest_safe['session_count'] - actual_count,
                preserved_segment_receipts=records, incomplete_explanation=reason,
                restores_verified=False, metrics_accepted=False)


def make_manifest(inventory):
    watched = {}

    def remember(path):
        path = Path(path)
        if path not in watched:
            watched[path] = digest_file(path)
        return watched[path][0]

    registrations = {}
    for case in sorted({row['case'] for row in inventory}):
        registrations[case] = verify_registration(case, remember)
    states = []
    completed = set()
    for row in inventory:
        case, run, role = row['case'], row['run'], row['role']
        registration, spec, registration_meta = registrations[case]
        if role.endswith('_incomplete'):
            completion = incomplete_run(case, role, registration, spec, remember)
        else:
            completion = audit_and_receipt(case, run, role == 'final_full', registration, spec, remember)
            if role == 'final_full':
                completed.add(case)
        states.append(dict(state_path=relative(row['directory']), case_directory=case,
            registered_case=registration['case'], role=role, registration_binding=registration_meta,
            completion=completion, files=[remember(path) for path in row['paths']]))
    require(completed == FINAL_CASES, 'All four final full cases must pass before archiving')
    manifest = dict(version='coinquant-private-simulation-state-v1',
        archive_root=ARCHIVE_STEM, privacy='private simulated state; never public/GitHub',
        scope='Exactly twelve registered simulation state directories; no raw data, caches, source code, configs, environments or credentials collected.',
        simulation_uid='12000', state_directory_count=12,
        final_full_cases=sorted(completed), states=states,
        deterministic_format=dict(tar_format='USTAR', xz_preset=1, xz_check='CRC64',
            normalized_mtime=0, normalized_uid=0, normalized_gid=0,
            regular_mode_octal='0600', directory_mode_octal='0700', member_order='sorted'),
        sqlite_policy='Raw SQLite, WAL, SHM and rollback journal bytes are preserved together when present. No SQLite open, checkpoint, backup API, recovery or WAL merge is performed.',
        script=remember(Path(__file__)),
    )
    return manifest, watched


def tar_header(name, size=0, directory=False):
    item = tarfile.TarInfo(name)
    item.type = tarfile.DIRTYPE if directory else tarfile.REGTYPE
    item.mode = 0o700 if directory else 0o600
    item.size = 0 if directory else size
    item.uid = item.gid = item.mtime = 0
    item.uname = item.gname = ''
    return item


def archive_members(manifest):
    files = {f'{ARCHIVE_STEM}/{file["path"]}': file
             for state in manifest['states'] for file in state['files']}
    directories = {ARCHIVE_STEM}
    for name in files:
        parent = Path(name).parent
        while str(parent) != '.':
            directories.add(str(parent))
            parent = parent.parent
    return files, directories


def write_archive(path, manifest, watched, created):
    payload = json_bytes(manifest)
    files, directories = archive_members(manifest)
    manifest_name = f'{ARCHIVE_STEM}/MANIFEST.json'
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    created.append(path)
    with os.fdopen(descriptor, 'wb') as raw:
        with lzma.LZMAFile(raw, 'wb', format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64, preset=1) as compressed:
            with tarfile.open(fileobj=compressed, mode='w|', format=tarfile.USTAR_FORMAT) as archive:
                for name in sorted(set(files) | directories | {manifest_name}):
                    if name in directories:
                        archive.addfile(tar_header(name, directory=True))
                    elif name == manifest_name:
                        archive.addfile(tar_header(name, len(payload)), io.BytesIO(payload))
                    else:
                        meta = files[name]
                        source = ROOT / meta['path']
                        with regular_open(source) as stream:
                            require(fingerprint(os.fstat(stream.fileno())) == watched[source][1],
                                    f'State changed before archival read: {relative(source)}')
                            archive.addfile(tar_header(name, meta['bytes']), stream)
                            require(fingerprint(os.fstat(stream.fileno())) == watched[source][1],
                                    f'State changed during archival read: {relative(source)}')
        raw.flush()
        os.fsync(raw.fileno())


def readback(path, manifest):
    files, directories = archive_members(manifest)
    expected_payload = json_bytes(manifest)
    manifest_name = f'{ARCHIVE_STEM}/MANIFEST.json'
    expected = set(files) | directories | {manifest_name}
    seen, payload_bytes = set(), 0
    with lzma.open(path, 'rb') as decoded:
        with tarfile.open(fileobj=decoded, mode='r:') as archive:
            for member in archive:
                require(member.name in expected and member.name not in seen,
                        'Unexpected or duplicate tar member')
                seen.add(member.name)
                require(member.uid == member.gid == member.mtime == 0
                        and member.uname == member.gname == '' and not member.pax_headers,
                        'Noncanonical tar header')
                if member.name in directories:
                    require(member.isdir() and member.mode == 0o700 and member.size == 0,
                            'Noncanonical directory header')
                    continue
                require(member.isfile() and member.mode == 0o600, 'Non-regular archive payload')
                with archive.extractfile(member) as stream:
                    if member.name == manifest_name:
                        require(stream.read() == expected_payload, 'Embedded manifest differs')
                        require(member.size == len(expected_payload), 'Manifest size differs')
                    else:
                        digest, count = hashlib.sha256(), 0
                        while block := stream.read(BLOCK):
                            digest.update(block)
                            count += len(block)
                        meta = files[member.name]
                        require(count == member.size == meta['bytes']
                                and digest.hexdigest() == meta['sha256'],
                                f'Archive readback mismatch: {meta["path"]}')
                        payload_bytes += count
        # Consume the XZ stream through its checksum/footer, including tar padding.
        while block := decoded.read(BLOCK):
            require(not block.strip(b'\0'), 'Unexpected data after the tar end marker')
    require(seen == expected, 'Archive members are missing')
    return dict(passed=True, member_count=len(seen), state_file_count=len(files),
                state_payload_bytes=payload_bytes,
                manifest_sha256=hashlib.sha256(expected_payload).hexdigest(),
                all_state_file_hashes_verified=True, xz_stream_fully_read=True)


def publish(archive_temp, archive_path, receipt_temp, receipt_path):
    """Commit two verified private files without replacing any existing output."""
    linked = []
    try:
        for temporary, final in ((archive_temp, archive_path), (receipt_temp, receipt_path)):
            os.link(temporary, final)
            linked.append(final)
        for parent in {archive_path.parent, receipt_path.parent}:
            descriptor = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    except BaseException:
        for path in linked:
            path.unlink()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-after-replays-stop', action='store_true')
    parser.add_argument('--archive', type=Path, default=ROOT / f'{ARCHIVE_STEM}.tar.xz')
    parser.add_argument('--receipt', type=Path, default=ROOT / 'PRIVATE_ARCHIVE.json')
    args = parser.parse_args()
    require(args.execute_after_replays_stop,
            'Preparation only: root must explicitly execute after all account replays stop')
    archive_path, receipt_path = args.archive.absolute(), args.receipt.absolute()
    require(archive_path != receipt_path and archive_path.parent.is_dir() and receipt_path.parent.is_dir(),
            'Output paths must be distinct and have existing parent directories')
    require(not archive_path.exists() and not receipt_path.exists(), 'Refusing to overwrite private outputs')
    archive_temp = archive_path.with_name(archive_path.name + '.partial')
    receipt_temp = receipt_path.with_name(receipt_path.name + '.partial')
    require(not archive_temp.exists() and not receipt_temp.exists(), 'Preserve existing partial output files')
    inventory = state_inventory()
    directories = [row['directory'] for row in inventory]
    for output in (archive_path, receipt_path):
        require(not any(output.resolve().is_relative_to(directory) for directory in directories),
                'Outputs cannot be placed inside source state')
    assert_no_replay_or_writer(directories)
    created = []
    try:
        with ExitStack() as stack:
            lock_count = hold_existing_locks(stack, inventory)
            assert_no_replay_or_writer(directories)
            manifest, watched = make_manifest(inventory)
            write_archive(archive_temp, manifest, watched, created)
            verification = readback(archive_temp, manifest)
            # Compare every payload and every receipt/audit/spec dependency again.
            require(state_inventory() == inventory, 'State file inventory changed')
            for path, (expected_meta, expected_signature) in watched.items():
                actual_meta, actual_signature = digest_file(path)
                require(actual_meta == expected_meta and actual_signature == expected_signature,
                        f'Source changed before final publication: {relative(path)}')
            assert_no_replay_or_writer(directories)
            with archive_temp.open('rb') as stream:
                archive_sha = hashlib.file_digest(stream, 'sha256').hexdigest()
            receipt = dict(version='coinquant-private-simulation-state-archive-v1',
                privacy='private; no public/GitHub upload performed',
                archive=dict(filename=archive_path.name, bytes=archive_temp.stat().st_size, sha256=archive_sha),
                manifest=manifest, readback_verification=verification,
                quiescence=dict(replay_processes_absent=True, writable_state_descriptors_absent=True,
                    existing_runtime_locks_held=lock_count, input_hashes_rechecked=True),
                account_or_replay_actions_performed=False, sqlite_opened_or_checkpointed=False,
                archived_state_restore_validated=False)
            descriptor = os.open(receipt_temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            created.append(receipt_temp)
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(json_bytes(receipt))
                stream.flush()
                os.fsync(stream.fileno())
            publish(archive_temp, archive_path, receipt_temp, receipt_path)
        print(json.dumps(dict(archive=str(archive_path), receipt=str(receipt_path),
                              archive_sha256=archive_sha, archive_bytes=receipt['archive']['bytes'],
                              state_directories=12, verified_state_files=verification['state_file_count']),
                         ensure_ascii=False))
    finally:
        for path in created:
            path.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
