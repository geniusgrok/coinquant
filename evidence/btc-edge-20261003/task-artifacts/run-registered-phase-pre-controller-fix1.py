"""Execute a root-registered phase with immutable argv/receipts; no retries.

External delivery helper only. It cannot enable account access or change source.
At most two isolated Spot subprocesses; all Coin invocations are serialized.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


REGISTRY = Path(__file__).with_name('registered-financial-commands.json')
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
    with path.open('x') as stream:
        json.dump(body, stream, indent=2, allow_nan=False)
        stream.write('\n')


def source_at(cwd):
    code = ('import json; from research.rebuild import source_identity; '
            'print(json.dumps(source_identity()))')
    result = subprocess.run([sys.executable, '-c', code], cwd=cwd,
                            check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def guard(job, freeze):
    kind = job['project_kind']
    record = freeze['projects'][kind]
    if source_at(job['cwd']) != record['source'] or record['source']['dirty']:
        raise ValueError('producer source changed: ' + kind)
    for tree in record.get('bound_trees', []):
        actual = sorted(str(p.resolve()) for p in Path(tree['root']).rglob('*')
                        if p.is_file() and any(p.name.endswith(s) for s in tree['suffixes']))
        if actual != tree['files']:
            raise ValueError('registered public input inventory changed: ' + tree['root'])
    for item in record['bound_files']:
        if sha(item['path']) != item['sha256']:
            raise ValueError('registered input/source bytes changed: ' + item['path'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', required=True, choices=('unscaled', 'risk', 'sensitivity', 'budgets'))
    parser.add_argument('--kind', required=True, choices=('spot', 'perp'))
    parser.add_argument('--freeze', required=True, type=Path)
    args = parser.parse_args()
    if sha(REGISTRY) != REGISTRY_SHA:
        raise ValueError('registered argv bytes changed')
    registry = json.loads(REGISTRY.read_bytes())
    freeze = json.loads(args.freeze.read_bytes())
    if freeze['format'] != 'btc-edge-reviewed-source-freeze-v1':
        raise ValueError('reviewed freeze required')
    freeze_sha = sha(args.freeze)
    jobs = [v for v in registry['jobs'] if v['phase'] == args.phase and v['project_kind'] == args.kind]
    if not jobs:
        raise ValueError('no registered jobs in phase')
    max_running = 2 if args.kind == 'spot' else 1
    pending = list(jobs)
    active = []
    failed = False
    while pending or active:
        while pending and len(active) < max_running and not failed:
            job = pending.pop(0)
            try:
                guard(job, freeze)
            except Exception as exc:
                pending.insert(0, job)
                failed = True
                print(json.dumps(dict(event='launch_guard_failed', label=job['label'], error=str(exc))), flush=True)
                break
            output = Path(job['output'])
            if output.exists() or output.with_suffix('.progress.json').exists():
                raise ValueError('existing output/progress: ' + str(output))
            output.parent.mkdir(parents=True, exist_ok=True)
            start_path = output.with_name(output.name + '.command-start.json')
            finish_path = output.with_name(output.name + '.command-finish.json')
            log_path = output.with_name(output.name + '.run.log')
            if any(p.exists() for p in (start_path, finish_path, log_path)):
                raise ValueError('existing invocation receipt: ' + str(output))
            start = dict(job, registry_sha256=REGISTRY_SHA, freeze_path=str(args.freeze),
                         freeze_sha256=freeze_sha, source=freeze['projects'][args.kind]['source'],
                         started_utc=now(), controller_sha256=sha(__file__))
            write_new(start_path, start)
            log = log_path.open('xb')
            process = subprocess.Popen(job['command'], cwd=job['cwd'], stdout=log, stderr=subprocess.STDOUT)
            active.append((job, process, log, start_path, finish_path, log_path, time.monotonic()))
            print(json.dumps(dict(event='launch', label=job['label'], pid=process.pid)), flush=True)
        next_active = []
        for job, process, log, start_path, finish_path, log_path, started in active:
            code = process.poll()
            if code is None:
                next_active.append((job, process, log, start_path, finish_path, log_path, started))
                continue
            log.close()
            source_error = None
            try:
                guard(job, freeze)
                if sha(args.freeze) != freeze_sha:
                    raise ValueError('freeze bytes changed')
            except Exception as exc:
                source_error = str(exc)
            output = Path(job['output'])
            finish = dict(label=job['label'], command_start_sha256=sha(start_path),
                          finished_utc=now(), elapsed_seconds=time.monotonic()-started,
                          exit_code=code, source_guard_error=source_error,
                          log_sha256=sha(log_path), output_sha256=sha(output) if output.exists() else None)
            write_new(finish_path, finish)
            print(json.dumps(dict(event='finish', **finish)), flush=True)
            failed = failed or code != 0 or source_error is not None or not output.exists()
        active = next_active
        if failed and not active:
            print(json.dumps(dict(event='stopped_after_failure', pending_labels=[j['label'] for j in pending])), flush=True)
            return 2
        if active:
            time.sleep(1)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
