"""Register the second cold margin-only retry; never execute a replay or account command."""
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
ORIGINAL = ROOT / 'replays/margin-only'
FAILED = ROOT / 'replays/margin-only-rerun-001'
OUT = ROOT / 'replays/margin-only-rerun-002'
HEAD = '06206ac0c5383fb009df8bac20601cd9e2d9b004'
SOURCE = '55f044e1294f52d7c4f06800552e96e22a2af52c3c393f57eed04ec6d47f6f04'
PRODUCER = '9b5ee3aea3a4f977b0b20c7b25e4a81ecdc5b7b188d9f26a3e119e03101f5413'
FROZEN = {
    ORIGINAL / 'REGISTRATION.json': '1a27b8913631fd1c73d212a34bd1386afdbb1ae9db83c429c314eb8dc1895e09',
    ORIGINAL / 'spec.json': 'c900615a50ac8d455a1386a607b86f82b46b1037c1a7894de6ca93d03512308a',
    ORIGINAL / 'current-source-files.json': 'e00c0ce304db64ede4608d2a004429b578f51c3c65509626f88a5a797d66919c',
    ORIGINAL / 'smoke-audit-summary.json': '7deefa51ce7af8fb463bdf6e3c887aaf16a9cb6bf42657566f2976680c179bb3',
    ORIGINAL / 'smoke-audit.json': '24c4cee3e04dbbe1eeca3527b03ec3cac4a62fc968f872c2cddd2d51f71a4226',
    ORIGINAL / 'smoke-current.json.gz': 'ca54f680f2f82a5f70d200b0e4bcb34e674d3808aaa589def77efa90cd42909d',
    ORIGINAL / 'INTERRUPTION_20261010.json': '186e11fc64dae35874520ae4d4df199d01f66ce8a4dc1fcbe8e18dc2d1523e9c',
    FAILED / 'INTERRUPTION_20261010.json': '1c88fff48a13576cecbe8b461e7ee3d6f04f3d9ec4eca5e114b78740f08b274c',
    FAILED / 'spec.json': '4dedd6e2a306511007feacbb054dea129cb92855f4b7ff170ee3f977c65b16e2',
    FAILED / 'run_one_segment.py': 'b7b1043a40dfc2b098b3110ebb108a9d4c61df7f65b48358cba8a0dd17b4c4e4',
    BASE / 'remeasure-evidence/evidence/2.0.0-remeasure-20261009/run_pair.py':
        '04c1d75e44596eee9c600bb6e1ab6a33e35e41df82bccae6a0bddb51f5cda40f',
    ROOT / 'ONE_SEGMENT_LAUNCHER.md': 'a9e736d8946cf8318d9fd6839305d78895fe744c8fa046228bab8987325fba0c',
    ROOT / 'original_compare_arms.py': 'b8d097a60f390da0cc95f5424ff2f8649c7250045fa82ba5e3c7f7acffd3145e',
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def artifact(path):
    return dict(path=str(path), bytes=Path(path).stat().st_size, sha256=sha(path))


def read(path):
    return json.loads(Path(path).read_text())


def write(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def main():
    require(not OUT.exists(), 'preserve any existing retry directory')
    for path, expected in FROZEN.items():
        require(path.is_file() and not path.is_symlink() and sha(path) == expected,
                'frozen input changed: ' + str(path))
    prior = read(ORIGINAL / 'REGISTRATION.json')
    original_spec = read(ORIGINAL / 'spec.json')
    runtime = Path(prior['runtime'])
    tooling = Path(original_spec['tooling_root'])
    require(prior['case'] == 'margin-only' and prior['head'] == HEAD
            and prior['source_sha256'] == SOURCE and prior['producer_sha256'] == PRODUCER,
            'unexpected original source identity')
    require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=runtime, text=True).strip() == HEAD
            and not subprocess.check_output(['git', 'status', '--porcelain'], cwd=runtime),
            'clean immutable margin-only checkout required')
    require(sha(tooling / 'driver.py') == PRODUCER
            and sha(ROOT / 'PROTOCOL.md') == prior['protocol_sha256'],
            'producer or original protocol changed')
    files = {str(p.relative_to(runtime)): sha(p) for p in sorted((runtime / 'coinquant').glob('*.py'))}
    research = {str(p.relative_to(tooling)): sha(p) for p in sorted((tooling / 'research').glob('*.py'))}
    require(len(files) == 19 and files == read(ORIGINAL / 'current-source-files.json'),
            'production source inventory changed')
    sys.dont_write_bytecode = True
    loader = importlib.util.spec_from_file_location('retry_audit_helpers', ROOT / 'original_compare_arms.py')
    helper = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(helper)
    packet = dict(files)
    packet.update({'tooling/' + key: value for key, value in research.items()})
    packet['tooling/driver.py'] = PRODUCER
    require(helper.digest(packet) == SOURCE == original_spec['source_sha256_by_arm']['current'],
            'source packet differs from the audited smoke')
    audit = read(ORIGINAL / 'smoke-audit-summary.json')
    with gzip.open(ORIGINAL / 'smoke-current.json.gz', 'rt') as stream:
        smoke = json.load(stream)
    require(audit['passed'] is True and audit['full795'] is False
            and all(audit[arm]['sessions'] == 6 and audit[arm]['financial']['passed'] is True
                    and audit[arm]['path_audit']['passed'] is True for arm in ('main', 'candidate'))
            and audit['candidate']['receipt_sha256'] == sha(ORIGINAL / 'smoke-current.json.gz')
            and audit['detail']['sha256'] == sha(ORIGINAL / 'smoke-audit.json')
            and smoke['complete'] is True and smoke['failure'] is None and smoke['session_count'] == 6
            and smoke['source']['git_head'] == HEAD and smoke['source']['files'] == files
            and smoke['source']['tooling_files'] == research and smoke['binding']['source_sha256'] == SOURCE,
            'exact passed source-level smoke required; this is not full-window admission')
    spec = deepcopy(original_spec)
    spec['source_files_by_arm']['current'] = str(OUT / 'current-source-files.json')
    spec['requested_measurement'] += (
        ' Cold retry margin-only-rerun-002 after two preserved incomplete runs; '
        'no checkpoint or account state is imported from either failed run.')
    differences = {}
    for name, before in [('original_margin', original_spec), ('failed_retry_001', read(FAILED / 'spec.json'))]:
        rows = helper.exact_differences(before, spec, path='spec')
        require({row['path'] for row in rows}
                == {'spec["requested_measurement"]', 'spec["source_files_by_arm"]["current"]'},
                'retry changes more than the two declared metadata fields')
        differences[name] = rows
    incidents = [artifact(path / 'INTERRUPTION_20261010.json') for path in (ORIGINAL, FAILED)]
    created = datetime.now(timezone.utc).isoformat()
    OUT.mkdir()
    copies = [(ORIGINAL / 'current-source-files.json', OUT / 'current-source-files.json'),
              (BASE / 'remeasure-evidence/evidence/2.0.0-remeasure-20261009/run_pair.py', OUT / 'run_pair.py'),
              (FAILED / 'run_one_segment.py', OUT / 'run_one_segment.py')]
    for source, target in copies:
        shutil.copy2(source, target)
        require(source.read_bytes() == target.read_bytes(), 'copied frozen file changed')
    write('spec.json', spec)
    reuse = dict(source_head=HEAD, source_sha256=SOURCE, passed=True,
        basis='Exact prior six-session smoke for unchanged production, producer, strategy, default risk and economic inputs.',
        prior_smoke_receipt=artifact(ORIGINAL / 'smoke-current.json.gz'),
        prior_smoke_audit=artifact(ORIGINAL / 'smoke-audit-summary.json'),
        prior_smoke_audit_detail=artifact(ORIGINAL / 'smoke-audit.json'),
        original_spec=artifact(ORIGINAL / 'spec.json'), new_spec=artifact(OUT / 'spec.json'),
        spec_differences=differences, full_window_admitted=False, new_smoke_executed=False)
    write('SMOKE_REUSE.json', reuse)
    registration = dict(prior)
    registration.update(spec_sha256=sha(OUT / 'spec.json'), registration_script_sha256=sha(__file__),
        prior_registration=artifact(ORIGINAL / 'REGISTRATION.json'),
        retry_of=str(FAILED), original_run=str(ORIGINAL), cold_start=True, created_at_utc=created,
        retry_reason='Retry 001 restore correctly refused a 711-session checkpoint with only 709 durable reports/calls. '
                     'Both failed directories are preserved; no partial result or reconstructed state is admitted.',
        preserved_incidents=incidents, smoke_reuse=artifact(OUT / 'SMOKE_REUSE.json'))
    write('REGISTRATION.json', registration)
    write('EXECUTION_METHOD.json', dict(method='one original registered 540-second segment per external process',
        source_producer_changed=False, original_controller_sha256=sha(OUT / 'run_pair.py'),
        actual_launcher_sha256=sha(OUT / 'run_one_segment.py'),
        registration_sha256=sha(OUT / 'REGISTRATION.json'),
        amendment_sha256=sha(ROOT / 'ONE_SEGMENT_LAUNCHER.md'), preserved_incidents=incidents,
        cold_start=True, imported_account_state=False, created_at_utc=created))
    require(all(sha(path) == expected for path, expected in FROZEN.items()), 'prior evidence changed during registration')
    outputs = [artifact(path) for path in sorted(OUT.iterdir())]
    verification = dict(passed=True, case='margin-only', directory=str(OUT), head=HEAD, source_sha256=SOURCE,
        producer_sha256=PRODUCER, registration_script=artifact(Path(__file__)),
        prior_frozen_inputs=[artifact(path) for path in FROZEN], spec_differences=differences,
        copied_files=[dict(source=artifact(source), target=artifact(target), bytes_identical=True)
                      for source, target in copies], outputs=outputs,
        replay_started=False, full_window_admitted=False, no_account_commands=True,
        retained_failed_directories=[str(ORIGINAL), str(FAILED)], created_at_utc=created)
    write('REGISTRATION_VERIFICATION.json', verification)
    print(json.dumps(dict(directory=str(OUT), verification=artifact(OUT / 'REGISTRATION_VERIFICATION.json'),
                          files=[artifact(path) for path in sorted(OUT.iterdir())], replay_started=False)))


if __name__ == '__main__':
    main()
