"""One-shot serial canonical Spot evidence collection; never an adoption decision."""
import argparse
from datetime import datetime, timezone
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

REPO = Path('/workspace/btc-alpha-beta-adoption/spotquant')
OUT = Path('/workspace/scratch/alpha-beta-next')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, body):
    with path.open('x') as stream:
        json.dump(body, stream, indent=2, allow_nan=False)
        stream.write('\n')


def source(expected):
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--porcelain', '--', 'spotquant', 'research'], cwd=REPO)
    if actual != expected or dirty:
        raise ValueError('Canonical source changed or dirty')


def collect(args):
    reviews = [p.resolve() for p in (args.spec_review, args.financial_review)]
    if len(set(reviews)) != 2 or len({sha(p) for p in reviews}) != 2:
        raise ValueError('Two distinct independent reviews required')
    review_bindings = {str(p): sha(p) for p in reviews}
    for path in review_bindings:
        text = Path(path).read_text()
        if args.expected_head not in text or 'PASS' not in text or 'APPROVE' not in text:
            raise ValueError('Exact-head approved review missing')
    receipt_path = OUT / 'spot-early-risk-completed.json'
    receipt_sha = sha(receipt_path)
    receipt = json.loads(receipt_path.read_text())
    calibration = Path(receipt['actual_calibration_path']).resolve()
    risk = Path(receipt['actual_risk_path']).resolve()
    if (sha(calibration) != receipt['actual_calibration_sha256']
            or sha(risk) != receipt['actual_risk_sha256']):
        raise ValueError('Early risk/calibration original changed')
    bindings = {**review_bindings, str(receipt_path): receipt_sha,
                str(calibration): receipt['actual_calibration_sha256'],
                str(risk): receipt['actual_risk_sha256'],
                str(Path(__file__).resolve()): sha(Path(__file__))}

    def unchanged():
        source(args.expected_head)
        if any(sha(Path(path)) != digest for path, digest in bindings.items()):
            raise ValueError('Frozen canonical launch evidence changed')

    unchanged()
    # Lock spans all five children; also reject producers not using this controller.
    active = subprocess.check_output(['ps', '-eo', 'args'], text=True).splitlines()
    modules = ('research.alpha_spot', 'research.adoption_spot', 'research.complete_spot',
               'research.rebuild')
    if any(any(' -m '+module+' ' in line for module in modules) for line in active):
        raise ValueError('Existing Spot economic producer still active')
    args.output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, TMPDIR=str(OUT/'tmp'), PYTHONDONTWRITEBYTECODE='1')
    files, runs = [], []
    for label, scenario, calibrated in [('base', 'base', False), ('fee150', 'fee150', False),
                                        ('slip2', 'slip2', False), ('outage', 'outage', False),
                                        ('calibrated-base', 'base', True)]:
        unchanged()
        raw = args.output / (label+'.json')
        packed = args.output / (label+'.json.gz')
        log = args.output / (label+'.run.log')
        command = [sys.executable, '-u', '-m', 'research.adoption_spot', '--scenario', scenario,
                   '--out', str(raw)]
        if calibrated:
            command += ['--risk-calibration', str(calibration)]
        started, begin = datetime.now(timezone.utc).isoformat(), time.monotonic()
        with log.open('x') as stream:
            result = subprocess.run(command, cwd=REPO, env=env, stdout=stream, stderr=subprocess.STDOUT)
        run = dict(label=label, scenario=scenario, calibrated=calibrated, command=command,
                   cwd=str(REPO), source_head=args.expected_head, started_utc=started,
                   elapsed_seconds=time.monotonic()-begin, exit_code=result.returncode,
                   log_sha256=sha(log), review_bindings=review_bindings, launch_bindings=bindings)
        if raw.exists():
            run['output_sha256'] = sha(raw)
        write(args.output/(label+'.command.json'), run)
        if result.returncode or not raw.exists():
            raise RuntimeError('Canonical command failed; preserve all evidence: '+label)
        unchanged()
        original = sha(raw)
        with raw.open('rb') as src, packed.open('xb') as dst:
            with gzip.GzipFile(filename='', fileobj=dst, mode='wb', mtime=0) as compressed:
                shutil.copyfileobj(src, compressed, 1024*1024)
        with gzip.open(packed, 'rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != original:
                raise ValueError('Canonical compression not byte equivalent')
        write(args.output/(label+'.compression.json'), dict(original_sha256=original,
              original_bytes=raw.stat().st_size, retained_sha256=sha(packed),
              retained_bytes=packed.stat().st_size, lossless_roundtrip_verified=True))
        raw.unlink()
        run['retained_sha256'] = sha(packed)
        runs.append(run)
        files.append(dict(label=label, scenario=scenario, calibrated=calibrated,
                          path=packed.name, sha256=sha(packed)))
        print(json.dumps(run), flush=True)
    unchanged()
    write(args.output/'canonical-inventory.json', dict(format='canonical-spot-five-v1',
          source_head=args.expected_head, files=files, runs=runs, review_bindings=review_bindings,
          launch_bindings=bindings,
          calibration_path=str(calibration), calibration_sha256=receipt['actual_calibration_sha256'],
          reference_risk_path=str(risk), reference_risk_sha256=receipt['actual_risk_sha256'],
          reference_completion_receipt_sha256=receipt_sha,
          adoption_approved=False, native_cases=0, actual_account_days=0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--spec-review', type=Path, required=True)
    parser.add_argument('--financial-review', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # Persistent kernel lock, never deleted or bypassed; child failures release on exit.
    with (OUT/'.spot-canonical-collection.lock').open('a+b') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        collect(args)


if __name__ == '__main__':
    main()
