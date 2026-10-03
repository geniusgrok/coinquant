"""Collect the fixed five canonical accounts using the unchanged approved serial core."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

ART = Path(__file__).resolve().parent
FREEZE = ART / 'spot-canonical-five-launch-freeze.json'
CORE = ART / 'run-registered-recovery.py'
CORE_SHA = 'cdc8538d01b46963c12b8810b468cafd754b58303a69495cfb32f4e62d497185'


def main():
    import hashlib
    digest = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if digest(CORE) != CORE_SHA:
        raise ValueError('approved serial controller changed')
    spec = importlib.util.spec_from_file_location('canonical_serial_core', CORE)
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    frozen = json.loads(FREEZE.read_bytes())
    freeze_sha = core.sha(FREEZE)
    registry = Path(frozen['registry']['path'])
    packet = json.loads(registry.read_bytes())
    jobs = [dict(label='spot-canonical-' + item['label'], project_kind='spot',
                 cwd=item['cwd'], command=item['argv'], output=item['output'])
            for item in packet['commands']]
    if [item['label'] for item in packet['commands']] != ['base', 'fee150', 'slip2', 'outage', 'unity-risk-base']:
        raise ValueError('exact five registered accounts required')
    tmp = Path(frozen['tmpdir'])
    tmp.mkdir(parents=True, exist_ok=False)
    core.write_new(tmp / 'owner.json', dict(uid=os.getuid(), registry_sha256=frozen['registry']['sha256']))
    environment = dict(os.environ, TMPDIR=str(tmp))

    def check(job):
        if core.sha(FREEZE) != freeze_sha or core.sha(CORE) != CORE_SHA:
            raise ValueError('canonical freeze/controller changed')
        core.verify_files(frozen['bound_files'])
        core.guard(dict(project_kind='spot', cwd=frozen['original_spot']['repository']),
                   {'projects': {'spot': frozen['original_spot']}})
        actual = subprocess.run([job['command'][0], '-c',
            'import json; from research.edge_forward import source; print(json.dumps(source()))'],
            cwd=job['cwd'], check=True, capture_output=True, text=True)
        if json.loads(actual.stdout) != frozen['canonical_source']:
            raise ValueError('canonical committed source changed')
        if shutil.disk_usage(tmp).free < 4 * 1024**3:
            raise ValueError('canonical task scratch below fixed 4GiB floor')

    provenance = dict(registry_path=str(registry), registry_sha256=frozen['registry']['sha256'],
        freeze_path=str(FREEZE), freeze_sha256=freeze_sha, controller_sha256=core.sha(__file__),
        reused_controller_sha256=CORE_SHA, concurrency=1, tmpdir=str(tmp),
        uid=os.getuid(), home=os.environ.get('HOME'), environment_overrides={'TMPDIR': str(tmp)},
        original_measured_source=frozen['original_spot']['source'], canonical_source=frozen['canonical_source'],
        adoption_approved=False, native_cases=0, actual_account_days=0)
    return core.run_jobs(jobs, check, ART, 'spot', 'canonical-five', provenance, environment=environment)


if __name__ == '__main__':
    raise SystemExit(main())
