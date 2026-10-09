"""Freeze one source-only repair against the unchanged v2 economic producer."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
ORIGINAL = BASE / 'remeasure-evidence/evidence/2.0.0-remeasure-20261009'
TOOLING = BASE / 'coinquant-remeasure-tooling-v2'
CONTROL = '162ee7138952925ffafbc9b68be7c754c0c0a6c3'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('case', choices=('book-only', 'margin-only', 'combined'))
    p.add_argument('--runtime', type=Path, required=True)
    p.add_argument('--head', required=True)
    args = p.parse_args()
    runtime = args.runtime.resolve()
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=runtime, text=True).strip()
    if actual != args.head or subprocess.check_output(['git', 'status', '--porcelain'], cwd=runtime):
        raise ValueError('clean immutable runtime checkout required')
    out = ROOT / 'replays' / args.case
    out.mkdir(parents=True)
    load = importlib.util.spec_from_file_location('audit_helpers', ROOT / 'original_compare_arms.py')
    helpers = importlib.util.module_from_spec(load)
    load.loader.exec_module(helpers)
    files = {str(f.relative_to(runtime)): sha(f) for f in sorted((runtime / 'coinquant').glob('*.py'))}
    if len(files) != 19:
        raise ValueError('expected complete production module set')
    packet = dict(files)
    packet.update({'tooling/' + str(f.relative_to(TOOLING)): sha(f)
                   for f in sorted((TOOLING / 'research').glob('*.py'))})
    packet['tooling/driver.py'] = sha(TOOLING / 'driver.py')
    source_map = out / 'current-source-files.json'
    source_map.write_text(json.dumps(files, indent=2) + '\n')
    spec = json.loads((ORIGINAL / 'spec.json').read_text())
    spec['runtime_roots']['current'] = str(runtime)
    spec['runtime_heads']['current'] = args.head
    spec['source_files_by_arm']['current'] = str(source_map)
    spec['source_files_by_arm']['previous'] = str(ORIGINAL / 'previous-source-files.json')
    spec['source_sha256_by_arm']['current'] = helpers.digest(packet)
    spec['protocol_sha256'] = sha(ROOT / 'PROTOCOL.md')
    spec['requested_measurement'] = ('Predeclared source repair experiment: ' + args.case
        + '; compare with retained full 2.0.0 control ' + CONTROL
        + '; unchanged v2 producer, economic inputs, schedule and default risk limits.')
    (out / 'spec.json').write_text(json.dumps(spec, indent=2, sort_keys=True) + '\n')
    shutil.copy2(ORIGINAL / 'run_pair.py', out / 'run_pair.py')
    registration = dict(case=args.case, head=args.head, runtime=str(runtime),
        source_sha256=spec['source_sha256_by_arm']['current'], spec_sha256=sha(out / 'spec.json'),
        protocol_sha256=spec['protocol_sha256'], producer_sha256=sha(TOOLING / 'driver.py'),
        controller_sha256=sha(out / 'run_pair.py'), registration_script_sha256=sha(__file__),
        control_receipt=str(BASE / 'coinquant-remeasure-2.0.0-v2/full-current-segment-002.json.gz'),
        control_spec=str(ORIGINAL / 'spec.json'), fixed_risk=spec['risk_by_arm']['current'])
    (out / 'REGISTRATION.json').write_text(json.dumps(registration, indent=2) + '\n')
    print(json.dumps(registration))


if __name__ == '__main__':
    main()
