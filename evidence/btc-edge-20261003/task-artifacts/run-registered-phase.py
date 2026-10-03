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


def run_jobs(jobs, check, root, kind, phase, provenance, popen=subprocess.Popen):
    """One reusable guarded core for original and conditional registries."""
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
            while pending and len(active) < (2 if kind == 'spot' else 1) and not errors:
                job = pending[0]
                log = None
                started = False
                try:
                    check(job)
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
                                        pass_fds=(reservation.fd,))
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', required=True)
    parser.add_argument('--kind', required=True, choices=('spot', 'perp'))
    parser.add_argument('--freeze', required=True, type=Path)
    parser.add_argument('--phase-input', type=Path)
    parser.add_argument('--supplemental-registry', type=Path)
    parser.add_argument('--supplemental-sha256')
    args = parser.parse_args(argv)
    if not args.phase or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in args.phase):
        raise ValueError('unsafe registered phase label')
    if sha(REGISTRY) != REGISTRY_SHA:
        raise ValueError('original registered argv bytes changed')
    raw = args.freeze.read_bytes()
    freeze_sha = hashlib.sha256(raw).hexdigest()
    freeze = json.loads(raw)
    parent_anchor = ART / 'controller-parent-freeze.json'
    anchor = json.loads(parent_anchor.read_bytes())
    if anchor['path'] != str(args.freeze.absolute()) or anchor['sha256'] != freeze_sha:
        raise ValueError('parent freeze differs from exclusive original anchor')
    anchor_sha = sha(parent_anchor)
    if freeze['format'] != 'btc-edge-reviewed-source-freeze-v1' or freeze['controller_root'] != str(ART):
        raise ValueError('reviewed freeze/controller root required')
    registry_path = args.supplemental_registry or REGISTRY
    registry_sha = args.supplemental_sha256 if args.supplemental_registry else REGISTRY_SHA
    if not registry_sha or sha(registry_path) != registry_sha:
        raise ValueError('exact registry SHA required')
    registry = json.loads(registry_path.read_bytes())
    if args.supplemental_registry:
        import importlib.util
        spec = importlib.util.spec_from_file_location('phase_inputs', ART / 'bind-phase-inputs.py')
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        helper.validate_supplement(registry, freeze_sha, freeze)
    elif args.phase not in ('unscaled', 'risk', 'sensitivity', 'budgets'):
        raise ValueError('unknown original phase')
    jobs = [j for j in registry['jobs'] if j['phase'] == args.phase and j['project_kind'] == args.kind]
    if not jobs:
        raise ValueError('no registered jobs in phase')
    if any(not j['label'] or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in j['label']) for j in jobs):
        raise ValueError('unsafe registered receipt label')
    if len({j['label'] for j in jobs}) != len(jobs) or len({j['output'] for j in jobs}) != len(jobs):
        raise ValueError('duplicate job label/output')
    phase_binding = None
    if args.phase_input:
        phase_binding = json.loads(args.phase_input.read_bytes())
        phase_sha = sha(args.phase_input)
        if (phase_binding['parent_freeze_sha256'] != freeze_sha or phase_binding['project_kind'] != args.kind or
            phase_binding['phase'] != args.phase or phase_binding['registry_sha256'] != registry_sha):
            raise ValueError('phase input parent/project/phase/registry mismatch')
    profiles = {j['command'][j['command'].index('--risk-calibration')+1] for j in jobs if '--risk-calibration' in j['command']}
    if phase_binding:
        if phase_binding['format'] != 'btc-edge-phase-input-binding-v1':
            raise ValueError('actual derived phase schema required')
        for item in (phase_binding['assessor_report'], phase_binding['original_export'], phase_binding['production_profile']):
            if item not in phase_binding['bound_files']:
                raise ValueError('missing original derived input byte binding')
        if not any(v['path'] == str(args.freeze.absolute()) and v['sha256'] == freeze_sha for v in phase_binding['bound_files']):
            raise ValueError('missing original parent freeze binding')
    if profiles and (phase_binding is None or profiles != {phase_binding['production_profile']['path']}):
        raise ValueError('exact derived phase binding required for every risk profile')
    provenance = dict(registry_path=str(registry_path), registry_sha256=registry_sha,
                      parent_registry_sha256=REGISTRY_SHA, freeze_path=str(args.freeze), freeze_sha256=freeze_sha,
                      phase_input_path=str(args.phase_input) if args.phase_input else None,
                      phase_input_sha256=phase_sha if phase_binding else None, controller_sha256=sha(__file__))
    def check(job):
        if sha(parent_anchor) != anchor_sha or sha(args.freeze) != freeze_sha or sha(REGISTRY) != REGISTRY_SHA or sha(registry_path) != registry_sha:
            raise ValueError('parent freeze/registry bytes changed')
        guard(job, freeze)
        for other_kind, record in freeze['projects'].items():
            if other_kind != job['project_kind'] and source_at(record['repository']) != record['source']:
                raise ValueError('other frozen producer/evaluator source changed: ' + other_kind)
        if phase_binding:
            if sha(args.phase_input) != phase_sha:
                raise ValueError('phase binding bytes changed')
            verify_files(phase_binding['bound_files'])
            if phase_binding['original_export']['sha256'] != phase_binding['production_profile']['sha256']:
                raise ValueError('production profile differs from original export')
        if args.supplemental_registry:
            verify_files(registry['bound_files'])
    return run_jobs(jobs, check, ART, args.kind, args.phase, provenance)


if __name__ == '__main__':
    raise SystemExit(main())
