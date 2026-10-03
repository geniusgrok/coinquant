"""Run exact registered research jobs with immutable guards and exclusive receipts.

Task-owned project reservation is inherited by children, never an account lock.
A failed/unknown owner is never automatically cleared. No retries or subset runs.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

ART = Path(__file__).resolve().parent
REGISTRY = ART / 'registered-financial-commands.json'
REGISTRY_SHA = 'e58114f25f316d237860d2d6e6859d48614a57d69065524f6c256140c575fbfa'


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4194304), b''):
            digest.update(block)
    return digest.hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def write_new(path, body):
    with Path(path).open('x') as stream:
        json.dump(body, stream, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def source_at(cwd):
    code = ('import json; from research.rebuild import source_identity; '
            'print(json.dumps(source_identity()))')
    result = subprocess.run([sys.executable, '-c', code], cwd=cwd,
                            check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def verify_files(items):
    for item in items:
        path = Path(item['path'])
        if path.is_symlink() or path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
            raise ValueError('registered input/source bytes changed: ' + str(path))


def guard(job, freeze):
    kind = job['project_kind']
    record = freeze['projects'][kind]
    if str(Path(job['cwd']).resolve()) != record['repository']:
        raise ValueError('job repository differs from frozen project')
    if source_at(job['cwd']) != record['source'] or record['source']['dirty']:
        raise ValueError('producer source changed: ' + kind)
    for tree in record['bound_trees']:
        actual = sorted(str(p.absolute()) for p in Path(tree['root']).rglob('*')
                        if p.is_file() and (tree['suffixes'] is None or
                                           any(p.name.endswith(s) for s in tree['suffixes'])))
        if actual != tree['files']:
            raise ValueError('registered public input inventory changed: ' + tree['root'])
    verify_files(record['bound_files'])


class Reservation:
    """flock covers live inherited children; durable owners cover unknown exits."""
    def __init__(self, root, kind, phase):
        self.root = Path(root) / 'controller-reservations' / kind
        self.root.mkdir(parents=True, exist_ok=True)
        self.fd = os.open(self.root / 'reservation.lock', os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            for owner in self.root.glob('*.owner.json'):
                released = owner.with_name(owner.name.replace('.owner.json', '.released.json'))
                if not released.exists():
                    raise ValueError('unknown/unfinished reservation owner: ' + str(owner))
                body = json.loads(released.read_bytes())
                if body.get('owner_sha256') != sha(owner) or body.get('all_children_reaped') is not True:
                    raise ValueError('invalid reservation release evidence: ' + str(released))
            self.owner = self.root / (uuid.uuid4().hex + '.owner.json')
            write_new(self.owner, dict(pid=os.getpid(), project_kind=kind, phase=phase, created_utc=now()))
        except BaseException:
            os.close(self.fd)
            raise

    def close(self, reaped):
        try:
            if reaped:
                write_new(self.owner.with_name(self.owner.name.replace('.owner.json', '.released.json')),
                          dict(owner_sha256=sha(self.owner), all_children_reaped=True, released_utc=now()))
        finally:
            # Do not LOCK_UN: inherited child descriptors must retain ownership.
            os.close(self.fd)


def run_jobs(jobs, check, root, kind, phase, provenance, popen=subprocess.Popen, environment=None,
             before_launch=None):
    """Approved drain core copied with cap1, child environment and launch hook."""
    reservation = Reservation(root, kind, phase)
    phase_dir = Path(root) / 'controller-receipts' / kind / (phase + '-' + provenance['registry_sha256'])
    fallback = Path(root) / 'controller-diagnostics'
    active, pending, results, errors = [], list(jobs), [], []
    all_reaped = True
    phase_ready = False
    draining = False
    handled_signals = []
    recorded_signals = 0

    def problem(stage, exc, label=None):
        error = dict(stage=stage, label=label, error=repr(exc), recorded_utc=now())
        errors.append(error)
        # Every error is durable independently of the per-output destination.
        try:
            fallback.mkdir(parents=True, exist_ok=True)
            write_new(fallback / (uuid.uuid4().hex + '.json'),
                      dict(error=error, phase=phase, project_kind=kind, provenance=provenance,
                           pending_labels=[j['label'] for j in pending],
                           active_labels=[a['job']['label'] for a in active]))
        except BaseException as diagnostic_error:
            errors.append(dict(stage='diagnostic_write', error=repr(diagnostic_error), label=label))
        print(json.dumps(dict(event='controller_error', **error)), flush=True)

    def record_signals():
        nonlocal recorded_signals
        while recorded_signals < len(handled_signals):
            signum = handled_signals[recorded_signals]
            recorded_signals += 1
            problem('handled_signal', RuntimeError('controller received signal ' + str(signum)))

    def save(path, body, stage, label=None):
        try:
            write_new(path, body)
            return True
        except BaseException as exc:
            problem(stage, exc, label)
            return False

    def finish(entry):
        nonlocal draining
        was_draining = draining
        draining = True  # A handled signal must never interrupt a child drain/reap.
        job, process = entry['job'], entry['process']
        label = job['label']
        local_errors = []
        code = None
        reaped = False
        try:
            code = process.wait()
            reaped = True
        except BaseException as exc:
            local_errors.append(dict(stage='wait', error=repr(exc)))
            problem('wait', exc, label)
        record_signals()
        try:
            entry['log'].close()
        except BaseException as exc:
            local_errors.append(dict(stage='log_close', error=repr(exc)))
            problem('log_close', exc, label)
        try:
            check(job)
        except BaseException as exc:
            local_errors.append(dict(stage='post_guard', error=repr(exc)))
            problem('post_guard', exc, label)
        hashes = {}
        for name, path in (('command_start', entry['start']), ('log', entry['log_path']), ('output', Path(job['output']))):
            try:
                hashes[name + '_sha256'] = sha(path)
            except BaseException as exc:
                hashes[name + '_sha256'] = None
                local_errors.append(dict(stage=name + '_hash', error=repr(exc)))
                problem(name + '_hash', exc, label)
        if code != 0:
            problem('child_exit', ValueError('actual exit code: ' + str(code)), label)
        body = dict(label=label, state='exited' if reaped else 'unknown', pid=process.pid,
                    exit_code=code, reaped=reaped, finished_utc=now(),
                    elapsed_seconds=time.monotonic()-entry['began'], errors=local_errors, **hashes)
        saved = save(entry['finish'], body, 'finish_receipt_write', label)
        results.append(dict(body, finish_receipt_saved=saved, finish_path=str(entry['finish'])))
        record_signals()
        draining = was_draining
        return reaped

    previous_signals = {}
    launching = False
    deferred_signal = None
    def interrupted(signum, frame):
        nonlocal deferred_signal
        handled_signals.append(signum)
        if draining:
            return
        if launching:
            deferred_signal = signum
            return
        raise RuntimeError('controller received signal ' + str(signum))

    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            previous_signals[sig] = signal.signal(sig, interrupted)
        phase_dir.mkdir(parents=True, exist_ok=False)
        phase_ready = True
        write_new(phase_dir / 'start.json', dict(provenance, phase=phase, project_kind=kind,
                  owner_path=str(reservation.owner), created_utc=now(), jobs=jobs))
        while pending or active:
            while pending and len(active) < 1 and not errors:
                job = pending[0]
                log = None
                started = False
                try:
                    check(job)
                    if before_launch is not None:
                        before_launch(job)
                    output = Path(job['output'])
                    start = output.with_name(output.name + '.command-start.json')
                    end = output.with_name(output.name + '.command-finish.json')
                    log_path = output.with_name(output.name + '.run.log')
                    if any(p.exists() for p in (output, output.with_suffix('.progress.json'), start, end, log_path)):
                        raise ValueError('existing output/progress/invocation receipt: ' + str(output))
                    output.parent.mkdir(parents=True, exist_ok=True)
                    write_new(start, dict(job, **provenance, state='launch_requested', requested_utc=now()))
                    log = log_path.open('xb')
                    entry = dict(job=job, log=log, start=start, finish=end, log_path=log_path, began=time.monotonic())
                    launching = True
                    try:
                        process = popen(job['command'], cwd=job['cwd'], stdout=log, stderr=subprocess.STDOUT,
                                        pass_fds=(reservation.fd,), env=environment)
                        entry['process'] = process
                        active.append(entry)
                        started = True
                        pending.pop(0)
                    finally:
                        launching = False
                    if deferred_signal is not None:
                        raise RuntimeError('controller received signal ' + str(deferred_signal))
                    write_new(phase_dir / (job['label'] + '.launched.json'),
                              dict(label=job['label'], pid=process.pid, launched_utc=now()))
                except BaseException as exc:
                    if not started and log is not None:
                        try:
                            log.close()
                        except BaseException as close_error:
                            problem('launch_log_close', close_error, job['label'])
                    problem('launch_bookkeeping' if started else 'launch_not_started', exc, job['label'])
                    if not started:
                        save(phase_dir / (job['label'] + '.not-started.json'),
                             dict(label=job['label'], state='not_started', error=repr(exc), recorded_utc=now()),
                             'not_started_receipt_write', job['label'])
                    break
            for entry in list(active):
                try:
                    done = bool(errors) or entry['process'].poll() is not None
                except BaseException as exc:
                    problem('poll', exc, entry['job']['label'])
                    done = True
                if done:
                    all_reaped = finish(entry) and all_reaped
                    active.remove(entry)
            if errors and not active:
                break
            if active:
                time.sleep(0.05)
    except BaseException as exc:
        problem('phase_controller', exc)
    finally:
        # Keep recording handled signals without raising throughout final drain.
        draining = True
        for entry in list(active):
            try:
                all_reaped = finish(entry) and all_reaped
            except BaseException as exc:
                all_reaped = False
                problem('unexpected_finish', exc, entry['job']['label'])
            active.remove(entry)
        record_signals()
        summary = dict(provenance, phase=phase, project_kind=kind, finished_utc=now(),
                       status='failed' if errors else 'completed', all_children_reaped=all_reaped,
                       pending_labels=[j['label'] for j in pending], results=results, errors=list(errors))
        if phase_ready:
            save(phase_dir / 'finish.json', summary, 'phase_finish_receipt_write')
        if errors:
            # Contains exact completion receipts even when their normal location failed.
            save(fallback / (uuid.uuid4().hex + '.phase-result.json'),
                 dict(summary, status='failed', errors=list(errors)), 'phase_fallback_write')
        try:
            reservation.close(all_reaped)
        except BaseException as exc:
            problem('reservation_release', exc)
            save(fallback / (uuid.uuid4().hex + '.phase-result.json'),
                 dict(summary, status='failed', errors=list(errors)), 'release_failure_result_write')
        for sig, handler in previous_signals.items():
            signal.signal(sig, handler)
    return 2 if errors else 0


# One named physical recovery. These are not caller-selectable economic inputs.
ORIGINAL_ROOT = Path('/workspace/scratch/btc-alpha-beta-edge-20261003')
RECOVERY_ROOT = ORIGINAL_ROOT / 'recovery1'
RECOVERY_REGISTRY = ART / 'registered-financial-recovery1.json'
APPROVAL = ART / 'recovery-approval.json'
FREEZE = ART / 'reviewed-source-freeze.json'
FREEZE_SHA = 'b15129a0984d3a6f2bc1be1e1bfc700f9cd30a2023d257efcd608a408efac1c9'
MIN_FREE_BYTES = 4 * 1024**3


def require(value, message):
    if not value:
        raise ValueError(message)


def no_symlinks(path):
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts, 'absolute canonical path required')
    for part in (path, *path.parents):
        require(not part.is_symlink(), 'symlink refused: ' + str(part))


def binding(path):
    path = Path(path).absolute()
    no_symlinks(path)
    return dict(path=str(path), bytes=path.stat().st_size, sha256=sha(path))


def transformed_job(original):
    job = dict(original, command=list(original['command']))
    require(job['command'].count('--out') == 1, 'exact one original output required')
    require(job['command'][job['command'].index('--out')+1] == original['output'], 'original output mismatch')
    for option in ('--out', '--prints'):
        require(job['command'].count(option) <= 1, 'duplicate path option')
        if option not in job['command']:
            continue
        index = job['command'].index(option)+1
        path = Path(job['command'][index])
        require(path.is_absolute() and '..' not in path.parts and ORIGINAL_ROOT in path.parents and
                RECOVERY_ROOT not in path.parents, 'original task path required')
        job['command'][index] = str(RECOVERY_ROOT/path.relative_to(ORIGINAL_ROOT))
    job['output'] = job['command'][job['command'].index('--out')+1]
    # Every invocation receipt carries the untouched registration alongside actual argv.
    job['original_job'] = original
    return job


def validate_registration(registration):
    require(sha(REGISTRY) == REGISTRY_SHA, 'original registry mutated')
    original = json.loads(REGISTRY.read_bytes())
    require(len(original['jobs']) == 50, 'entire original 50-job matrix required')
    require(registration['format'] == 'btc-edge-resource-recovery-v1' and
            registration['attempt'] == 'recovery1' and
            registration['parent_freeze_sha256'] == FREEZE_SHA and
            registration['parent_registry_sha256'] == REGISTRY_SHA and
            registration['root_output'] == str(RECOVERY_ROOT) and
            registration['concurrency'] == {'spot': 1, 'perp': 1} and
            registration['minimum_free_bytes'] == MIN_FREE_BYTES,
            'recovery identity differs from named physical recovery')
    require(registration['jobs'] == [transformed_job(j) for j in original['jobs']],
            'recovery must preserve all exact original economic jobs and order')
    for field in ('output', 'label'):
        require(len({j[field] for j in registration['jobs']}) == 50, 'duplicate recovery '+field)
    verify_files(registration['bound_files'])
    required = {str(p) for p in (REGISTRY, FREEZE, ART/'controller-parent-freeze.json',
                ART/'first-financial-attempt-storage-failure.json', Path(__file__).absolute(),
                ART/'run-registered-phase.py', ART/'prepare-source-freeze.py',
                ART/'bind-phase-inputs.py', ART/'task-6-controller-fix2-rereview.md')}
    require(required <= {i['path'] for i in registration['bound_files']}, 'missing recovery authority binding')
    failure = json.loads((ART/'first-financial-attempt-storage-failure.json').read_bytes())
    require(failure['parent_freeze_sha256'] == FREEZE_SHA and failure['registry_sha256'] == REGISTRY_SHA,
            'first failure parent mismatch')
    require(all(v['status'] == 'failed' and v['all_children_reaped'] is True for v in failure['phases'].values()),
            'first attempt has unknown or live children')
    require(all(item in registration['bound_files'] for item in failure['retained_files']),
            'first failed attempt evidence missing')
    for tree in registration['first_attempt_trees']:
        no_symlinks(tree['root'])
        paths = sorted(str(p) for p in Path(tree['root']).rglob('*') if p.is_file())
        require(paths == tree['files'], 'first failed attempt inventory changed')
    for path in registration['first_attempt_absent_outputs']:
        no_symlinks(path)
        require(not Path(path).exists(), 'original failed/missing raw unexpectedly appeared')


def verify_authorities(registration, registry_sha, approval_sha):
    require(sha(RECOVERY_REGISTRY) == registry_sha and sha(APPROVAL) == approval_sha,
            'recovery registry/approval bytes changed')
    validate_registration(registration)
    require(sha(FREEZE) == FREEZE_SHA, 'exclusive original freeze mutated')
    require(json.loads((ART/'controller-parent-freeze.json').read_bytes()) == binding(FREEZE),
            'exclusive original anchor differs')
    approval = json.loads(APPROVAL.read_bytes())
    require(approval['format'] == 'btc-edge-recovery-approval-v1' and
            approval['attempt'] == 'recovery1' and approval['approved'] is True,
            'fresh independent recovery approval required')
    required = [binding(RECOVERY_REGISTRY), binding(Path(__file__)), binding(ART/'task-6-recovery-report.md')]
    require(all(item in approval['bound_files'] for item in required) and
            approval['review'] in approval['bound_files'] and
            Path(approval['review']['path']).parent == ART and
            Path(approval['review']['path']).name == 'task-6-recovery-rereview.md',
            'approval must bind exact implementation, registration, report and fresh independent review')
    for item in [*registration['bound_files'], *approval['bound_files'], binding(APPROVAL)]:
        no_symlinks(item['path'])
    verify_files(approval['bound_files'])


def storage_guard(kind, registry_sha):
    """Runs under the shared project reservation, before each child starts."""
    path = RECOVERY_ROOT/'tmp'/kind
    no_symlinks(path)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    require(path.stat().st_uid == os.getuid(), 'TMPDIR not owned by current task UID')
    owner = path/'.recovery-owner.json'
    no_symlinks(owner)
    expected = dict(attempt='recovery1', project_kind=kind, registry_sha256=registry_sha)
    if not owner.exists():
        require(not list(path.iterdir()), 'unowned existing TMPDIR contents')
        write_new(owner, expected)
    require(json.loads(owner.read_bytes()) == expected, 'TMPDIR owner mismatch')
    require(set(path.iterdir()) == {owner}, 'unreaped temporary state; no cleanup or retry')
    filesystem = subprocess.run(['stat', '-f', '-c', '%T', str(path)], check=True,
                                capture_output=True, text=True).stdout.strip()
    stats = os.statvfs(path)
    available = stats.f_bavail*stats.f_frsize
    require(path.stat().st_dev == Path('/workspace').stat().st_dev and filesystem == 'overlayfs',
            'TMPDIR must physically use /workspace overlay')
    require(available >= MIN_FREE_BYTES, 'insufficient overlay free bytes for recovery launch')
    return dict(path=str(path), filesystem=filesystem, device=path.stat().st_dev,
                available_bytes=available, minimum_free_bytes=MIN_FREE_BYTES, measured_utc=now())


def fresh_paths(job):
    for option in ('--out', '--prints'):
        if option not in job['command']:
            continue
        path = Path(job['command'][job['command'].index(option)+1])
        no_symlinks(path)
        require(RECOVERY_ROOT in path.parents, 'exclusive recovery path required')
        if option == '--prints':
            for owned in (path, Path(str(path)+'-cache')):
                no_symlinks(owned)
                require(not owned.exists(), 'existing recovery print/cache owner: '+str(owned))


def main(argv=None):
    parser = argparse.ArgumentParser(description='Run ONE reviewed resource recovery, exact registered phases only.')
    parser.add_argument('--phase', required=True)
    parser.add_argument('--kind', required=True, choices=('spot', 'perp'))
    parser.add_argument('--approval-sha256', required=True)
    parser.add_argument('--phase-input', type=Path)
    parser.add_argument('--supplemental-registry', type=Path)
    parser.add_argument('--supplemental-sha256')
    args = parser.parse_args(argv)
    require(args.phase and all(c in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in args.phase),
            'unsafe phase label')
    registration = json.loads(RECOVERY_REGISTRY.read_bytes())
    registry_sha = sha(RECOVERY_REGISTRY)
    verify_authorities(registration, registry_sha, args.approval_sha256)
    freeze = json.loads(FREEZE.read_bytes())
    # Production profiles remain bound by the ORIGINAL approved helper/registry.
    input_registry_sha = REGISTRY_SHA
    supplemental = None
    if args.supplemental_registry:
        import importlib.util
        spec = importlib.util.spec_from_file_location('phase_inputs', ART/'bind-phase-inputs.py')
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        require(args.supplemental_sha256 and sha(args.supplemental_registry) == args.supplemental_sha256,
                'exact original conditional registry SHA required')
        supplemental = json.loads(args.supplemental_registry.read_bytes())
        helper.validate_supplement(supplemental, FREEZE_SHA, freeze)
        jobs = [transformed_job(j) for j in supplemental['jobs']]
        input_registry_sha = args.supplemental_sha256
    else:
        require(args.supplemental_sha256 is None and args.phase in ('unscaled','risk','sensitivity','budgets'),
                'unknown original phase')
        jobs = json.loads(json.dumps(registration['jobs']))
    jobs = [j for j in jobs if j['phase'] == args.phase and j['project_kind'] == args.kind]
    require(jobs and len({j['label'] for j in jobs}) == len(jobs) and
            len({j['output'] for j in jobs}) == len(jobs), 'complete unique registered phase required')
    require(all(j['label'] and all(c in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in j['label']) for j in jobs),
            'unsafe receipt label')
    phase_binding = None
    phase_sha = None
    if args.phase_input:
        phase_binding = json.loads(args.phase_input.read_bytes())
        phase_sha = sha(args.phase_input)
        require(phase_binding['format'] == 'btc-edge-phase-input-binding-v1' and
                phase_binding['parent_freeze_sha256'] == FREEZE_SHA and
                phase_binding['project_kind'] == args.kind and phase_binding['phase'] == args.phase and
                phase_binding['registry_sha256'] == input_registry_sha, 'original phase input identity mismatch')
        require(all(phase_binding[k] in phase_binding['bound_files'] for k in
                    ('assessor_report','original_export','production_profile')) and
                binding(FREEZE) in phase_binding['bound_files'], 'missing original derived input bindings')
    profiles = {j['command'][j['command'].index('--risk-calibration')+1] for j in jobs if '--risk-calibration' in j['command']}
    require(not profiles or (phase_binding and profiles == {phase_binding['production_profile']['path']}),
            'exact original production calibration binding required')
    provenance = dict(attempt='recovery1', registry_path=str(RECOVERY_REGISTRY), registry_sha256=registry_sha,
        parent_registry_sha256=REGISTRY_SHA, freeze_path=str(FREEZE), freeze_sha256=FREEZE_SHA,
        first_failure=registration['first_failure'], approval_path=str(APPROVAL), approval_sha256=args.approval_sha256,
        phase_input_path=str(args.phase_input) if args.phase_input else None, phase_input_sha256=phase_sha,
        supplemental_path=str(args.supplemental_registry) if supplemental else None,
        supplemental_sha256=args.supplemental_sha256, controller_sha256=sha(__file__),
        concurrency=1, tmpdir=str(RECOVERY_ROOT/'tmp'/args.kind))
    def check(job):
        verify_authorities(registration, registry_sha, args.approval_sha256)
        # Check BOTH input/source/vault trees at every launch and actual child completion.
        for kind, record in freeze['projects'].items():
            for item in record['bound_files']:
                no_symlinks(item['path'])
            guard(dict(project_kind=kind, cwd=record['repository']), freeze)
        if phase_binding:
            require(sha(args.phase_input) == phase_sha, 'phase binding bytes changed')
            verify_files(phase_binding['bound_files'])
            require(phase_binding['original_export']['sha256'] == phase_binding['production_profile']['sha256'],
                    'production profile differs from original export')
        if supplemental:
            require(sha(args.supplemental_registry) == args.supplemental_sha256, 'conditional registry mutated')
            verify_files(supplemental['bound_files'])
        for option in ('--out','--prints'):
            if option in job['command']:
                no_symlinks(job['command'][job['command'].index(option)+1])
    environment = dict(os.environ, TMPDIR=str(RECOVERY_ROOT/'tmp'/args.kind))
    def before_launch(job):
        fresh_paths(job)
        job['storage_launch'] = storage_guard(args.kind, registry_sha)
    return run_jobs(jobs, check, ART, args.kind, 'recovery1-'+args.phase, provenance,
                    environment=environment, before_launch=before_launch)


if __name__ == '__main__':
    raise SystemExit(main())
