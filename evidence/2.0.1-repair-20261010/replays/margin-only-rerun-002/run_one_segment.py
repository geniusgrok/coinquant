"""Run one registered source/economic segment, preserving original safe-boundary receipts."""
import argparse
from datetime import datetime, timezone
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def admit(spec):
    manifest_path = Path(spec['input_manifest'])
    if sha(manifest_path) != spec['input_manifest_sha256']:
        raise RuntimeError('frozen input manifest changed')
    receipt = json.loads(Path(spec['download_receipt']).read_text())
    files = json.loads(manifest_path.read_text())['files']
    restored = {r['relative_path']: r for r in receipt['results']}
    if receipt['complete'] is not True or len(files) != 1164 or len(restored) != len(files):
        raise RuntimeError('complete frozen input restoration required before full replay')
    for item in files:
        actual = restored[item['relative_path']]
        path = manifest_path.parent / item['relative_path']
        if (actual['status'] not in ('downloaded-verified', 'verified-existing')
                or actual['sha256'] != item['sha256'] or actual['bytes'] != item['bytes']
                or path.stat().st_size != item['bytes']):
            raise RuntimeError('unverified raw input: ' + item['relative_path'])
    for arm, root in spec['runtime_roots'].items():
        head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
        if head != spec['runtime_heads'][arm]:
            raise RuntimeError('wrong actual Git checkout: ' + arm)
    if sha(Path(spec['tooling_root'])/'driver.py') != spec['producer_sha256']:
        raise RuntimeError('registered producer changed')


def read(path):
    with gzip.open(path, 'rt') as stream:
        return json.load(stream)


def progress(arm, receipt, row):
    path = ROOT / 'PROGRESS.json'
    current = json.loads(path.read_text()) if path.exists() else {}
    current['updated_at_utc'] = datetime.now(timezone.utc).isoformat()
    current[arm] = dict(receipt=str(receipt), session_count=row['session_count'],
        segment=row['segment'], complete=row['complete'], can_resume=row['can_resume'],
        failure=row['failure'], cumulative_wall_seconds=row['cumulative_wall_seconds'])
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(current, indent=2) + '\n')
    temp.replace(path)


def run(arm):
    spec = json.loads((ROOT / 'spec.json').read_text())
    env = os.environ.copy()
    env['CQR_RUNTIME_ROOT'] = spec['runtime_roots'][arm]
    env['CQR_RUNTIME_SHA'] = spec['runtime_heads'][arm]
    receipts = sorted(ROOT.glob(f'full-{arm}-segment-*.json.gz'))
    previous = receipts[-1] if receipts else None
    row = read(previous) if previous else None
    while row is None or not row['complete']:
        if row is not None and (row['failure'] or not row['can_resume']):
            raise RuntimeError(f'{arm} cannot resume: {row["failure"] or row["stop_reason"]}')
        segment = row['segment'] + 1 if row else 1
        receipt = ROOT / f'full-{arm}-segment-{segment:03}.json.gz'
        if receipt.exists():
            raise RuntimeError('preserve existing receipt')
        command = [sys.executable, str(Path(spec['tooling_root'])/'driver.py'),
            '--mode', 'resume' if row else 'start', '--spec', str(ROOT / 'spec.json'),
            '--scratch', str(ROOT / f'full-{arm}'), '--out', str(receipt)]
        if previous:
            command += ['--previous', str(previous)]
        launch = dict(arm=arm, segment=segment, command=command,
            runtime_root=env['CQR_RUNTIME_ROOT'], runtime_sha=env['CQR_RUNTIME_SHA'],
            controller_sha256=sha(__file__), spec_sha256=sha(ROOT/'spec.json'),
            launched_at_utc=datetime.now(timezone.utc).isoformat())
        with (ROOT / 'FULL_COMMANDS.jsonl').open('a') as stream:
            stream.write(json.dumps(launch) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        print(json.dumps(launch), flush=True)
        with (ROOT / f'full-{arm}-segment-{segment:03}.log').open('x') as log:
            process = subprocess.Popen(command, cwd=spec['tooling_root'], env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                log.write(line)
                log.flush()
                print(line, end='', flush=True)
            if process.wait() != 0:
                raise RuntimeError('runner process failed; inspect preserved log/state')
        row = read(receipt)
        if row['source']['git_head'] != spec['runtime_heads'][arm]:
            raise RuntimeError('wrong production runtime')
        progress(arm, receipt, row)
        previous = receipt
        return previous  # one completed process per original 540-second segment
    return previous


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', choices=('previous', 'current', 'both'), default='both')
    args = parser.parse_args()
    controller_lock = (ROOT/'.controller.lock').open('a')
    fcntl.flock(controller_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    admit(json.loads((ROOT/'spec.json').read_text()))
    for arm in ('previous', 'current') if args.arm == 'both' else (args.arm,):
        print(json.dumps({'segment_finished_arm': arm, 'receipt': str(run(arm))}), flush=True)
