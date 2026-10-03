"""Invoke the existing assessor once with actual completed receipts and retained exits."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import time

ART = Path(__file__).resolve().parent
FIN = Path('/workspace/scratch/btc-alpha-beta-edge-20261003/assessment')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--invocation', type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('assessment_receipts', ART / 'run-registered-recovery.py')
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    invocation_sha = core.sha(args.invocation)
    body = json.loads(args.invocation.read_bytes())
    job = body['job']
    phase = job['command'][job['command'].index('--phase') + 1]
    freeze = json.loads((ART / 'reviewed-source-freeze.json').read_bytes())
    files = {'spot': [], 'perp': []}
    count = 0
    for measured in body['completed_jobs']:
        path = Path(measured['output'])
        receipt = json.loads(path.with_name(path.name + '.command-finish.json').read_bytes())
        if (receipt['exit_code'] != 0 or receipt['reaped'] is not True or
                receipt['state'] != 'exited' or receipt['errors'] or not path.is_file()):
            raise ValueError('incomplete measured account: ' + measured['label'])
        files[measured['project_kind']].append({'path': str(path), 'sha256': receipt['output_sha256']})
        count += measured['expected_accounts']
    if count != 71 or sum(map(len, files.values())) != 53:
        raise ValueError('complete registered inventory required')
    for kind in files:
        manifest = {'format': 'btc-edge-account-manifest-v1', 'files': files[kind]}
        for name in ('complete-preliminary', 'complete-final'):
            path = FIN / (name + '-' + kind + '-manifest.json')
            if phase == 'preliminary':
                core.write_new(path, manifest)
            elif json.loads(path.read_bytes()) != manifest:
                raise ValueError('completed account manifest changed')

    def sources():
        actual = {kind: core.source_at(record['repository']) for kind, record in freeze['projects'].items()}
        if any(actual[kind] != record['source'] for kind, record in freeze['projects'].items()):
            raise ValueError('frozen evaluator/producer source changed')
        return actual

    out = Path(job['command'][job['command'].index('--out') + 1])
    start = out.with_name(out.name + '.command-start.json')
    finish = out.with_name(out.name + '.command-finish.json')
    log = out.with_name(out.name + '.run.log')
    before = sources()
    core.write_new(start, dict(state='launch_requested', requested_utc=core.now(), job=job,
        invocation_sha256=invocation_sha, source_before=before, actual_accounts=count,
        raw_files=sum(map(len, files.values())), driver_sha256=core.sha(__file__)))
    began = time.monotonic()
    with log.open('xb') as stream:
        process = subprocess.Popen(job['command'], cwd=job['cwd'], stdout=stream, stderr=subprocess.STDOUT)
        code = process.wait()
    errors = []
    try:
        after = sources()
        if core.sha(args.invocation) != invocation_sha:
            raise ValueError('actual invocation changed')
    except Exception as exc:
        after = None
        errors.append(repr(exc))
    outputs = {}
    for option in ('--out', '--csv', '--markdown'):
        path = Path(job['command'][job['command'].index(option) + 1])
        outputs[str(path)] = core.sha(path) if path.is_file() else None
    core.write_new(finish, dict(state='exited', pid=process.pid, exit_code=code, reaped=True,
        finished_utc=core.now(), elapsed_seconds=time.monotonic() - began, errors=errors,
        source_after=after, command_start_sha256=core.sha(start), log_sha256=core.sha(log), outputs=outputs))
    print(json.dumps(dict(actual_exit_code=code, errors=errors, outputs=outputs)), flush=True)
    return code if code else (2 if errors else 0)


if __name__ == '__main__':
    raise SystemExit(main())
