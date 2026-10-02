"""One-shot controller orchestration; economic rules live in the frozen producer."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--tmpdir', type=Path, required=True)
    parser.add_argument('--calibration', type=Path)
    args = parser.parse_args()
    spec = json.loads((args.repo / 'research/alpha_beta_spec.json').read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    args.tmpdir.mkdir(parents=True, exist_ok=True)
    files, runs = [], []
    for name in spec['spot_candidates']:
        head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=args.repo, text=True).strip()
        if head != args.expected_head:
            raise ValueError('controller source head changed during measurement')
        raw = args.output / (name + '.json')
        packed = args.output / (name + '.json.gz')
        log = args.output / (name + '.run.log')
        if any(p.exists() for p in (raw, packed, log)):
            raise ValueError('never overwrite account evidence or logs')
        command = [sys.executable, '-m', 'research.alpha_spot', '--candidate', name,
                   '--workers', '2', '--out', str(raw)]
        if args.calibration:
            command += ['--scenario', 'base', '--risk-calibration', str(args.calibration)]
        started = datetime.now(timezone.utc).isoformat()
        begin = time.monotonic()
        environment = dict(os.environ, TMPDIR=str(args.tmpdir))
        with log.open('x') as stream:
            result = subprocess.run(command, cwd=args.repo, env=environment, stdout=stream, stderr=subprocess.STDOUT)
        run = {'candidate': name, 'command': command, 'started_utc': started,
               'elapsed_seconds': time.monotonic() - begin, 'exit_code': result.returncode,
               'cumulative_child_max_rss_kib': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss}
        runs.append(run)
        print(json.dumps(run), flush=True)
        if result.returncode or not raw.exists():
            with (args.output / 'controller-failure.json').open('x') as stream:
                json.dump({'runs': runs, 'completed_files': files}, stream, indent=2)
            return result.returncode or 1
        raw_sha = sha(raw)
        with raw.open('rb') as source, packed.open('xb') as target:
            with gzip.GzipFile(filename='', mode='wb', fileobj=target, mtime=0) as compressed:
                shutil.copyfileobj(source, compressed, 1024 * 1024)
        with gzip.open(packed, 'rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != raw_sha:
                raise ValueError('compressed evidence does not exactly reproduce original bytes')
        run.update(raw_sha256=raw_sha, raw_bytes=raw.stat().st_size,
                   retained_sha256=sha(packed), retained_bytes=packed.stat().st_size)
        files.append({'path': packed.name, 'sha256': run['retained_sha256']})
        # The lossless compressed original is retained and roundtrip-verified.
        raw.unlink()
    with (args.output / 'accounts-manifest.json').open('x') as stream:
        json.dump({'format': 'alpha-account-manifest-v1', 'kind': 'spot', 'files': files}, stream, indent=2)
        stream.write('\n')
    with (args.output / 'controller-runs.json').open('x') as stream:
        json.dump({'runs': runs, 'expected_source_head': args.expected_head}, stream, indent=2)
        stream.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
