"""Scoped reviewer probes only; temporary harmless child, never a producer."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

ART = Path(__file__).resolve().parent
OUT = ART / 'task-6-controller-fix1-rereview-probes'
OUT.mkdir(exist_ok=False)

def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ART / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

runner = load('reviewed_runner', 'run-registered-phase.py')
phase = load('reviewed_phase', 'bind-phase-inputs.py')
evidence = {'scope': 'Synthetic reviewer evidence; no actual freeze/queue/account operation',
            'helper_sha256': {n: runner.sha(ART / n) for n in (
                'prepare-source-freeze.py', 'run-registered-phase.py', 'bind-phase-inputs.py')}}

with tempfile.TemporaryDirectory(prefix='controller-scoped-reap-') as tmp:
    root = Path(tmp)
    output, occupied = root / 'harmless-child.json', root / 'occupied.json'
    occupied.write_text('synthetic existing output')
    jobs = [dict(label='first', project_kind='spot', phase='probe', cwd=tmp,
                 command=[sys.executable, '-c', 'import time;from pathlib import Path;time.sleep(.6);Path('
                          + repr(str(output)) + ').write_text("done")'], output=str(output)),
            dict(label='second', project_kind='spot', phase='probe', cwd=tmp,
                 command=['never-launched'], output=str(occupied))]
    children, threads = [], []
    def popen(*args, **kwargs):
        child = subprocess.Popen(*args, **kwargs)
        children.append(child)
        thread = threading.Thread(target=lambda: (time.sleep(.1), os.kill(os.getpid(), signal.SIGTERM)))
        thread.start()
        threads.append(thread)
        return child
    stream = io.StringIO()
    began = time.monotonic()
    with contextlib.redirect_stdout(stream):
        code = runner.run_jobs(jobs, lambda job: None, root, 'spot', 'probe',
                               dict(registry_sha256='a' * 64), popen=popen)
    summary = json.loads(next((root / 'controller-receipts').rglob('finish.json')).read_text())
    observed = dict(controller_exit=code, elapsed_seconds=time.monotonic() - began,
                    child_still_running=children[0].poll() is None,
                    all_children_reaped=summary['all_children_reaped'],
                    recorded_result=summary['results'][0])
    for thread in threads:
        thread.join()
    for child in children:
        child.wait(timeout=3)
    observed.update(reviewer_cleanup_actual_child_exit=children[0].returncode,
                    actual_output_after_reviewer_wait=output.read_text())
    evidence['signal_during_failure_wait'] = observed
    with (OUT / 'signal-probe-controller-stdout.txt').open('x') as file:
        file.write(stream.getvalue())
    for directory in ('controller-receipts', 'controller-diagnostics', 'controller-reservations'):
        shutil.copytree(root / directory, OUT / directory, ignore=shutil.ignore_patterns('reservation.lock'))
    for file in root.glob('*.command-*.json'):
        shutil.copyfile(file, OUT / file.name)

sys.path.insert(0, str(ART.parent / 'spotquant'))
from research import edge_assessment as api
with tempfile.TemporaryDirectory(prefix='controller-scoped-audit-') as tmp:
    root = Path(tmp)
    sources = {k: dict(dirty=False, git_head='synthetic-' + k) for k in api.BASE}
    freeze = {'projects': {k: {'source': v} for k, v in sources.items()}}
    report = dict(format='btc-edge-assessment-v1', blocking=[], rejected_files=[],
                  analysis_source=sources['spot'], contracts={k: dict(spec_sha256=api.SPEC_HASH[k],
                  protocol_sha256=api.PROTOCOL_HASH[k]) for k in api.BASE}, accounts={}, inputs={})
    for i, key in enumerate(sorted(api.required_matrix())):
        if not key.endswith('|0|unscaled') or key.split('|')[3] != '1E+4':
            continue
        kind = key.split('|')[0]
        raw = root / (str(i) + '.raw')
        raw.write_text('synthetic controller-only raw ' + key)
        digest = runner.sha(raw)
        report['accounts'][key] = dict(kind=kind, status='complete', reasons=[],
            monetary_audit={'passed': False}, source=sources[kind], path=str(raw), raw_sha256=digest)
        report['inputs'][str(raw)] = digest
    accepted = phase.validate_report(report, freeze, api)
    evidence['explicit_failed_audits'] = dict(failed_audits=len(report['accounts']),
                                             accepted_raw_bindings=len(accepted))
    with (OUT / 'failed-audit-synthetic-report.json').open('x') as file:
        json.dump(report, file, indent=2, allow_nan=False)

with (OUT / 'probe-results.json').open('x') as file:
    json.dump(evidence, file, indent=2, allow_nan=False)
manifest = {str(p.relative_to(OUT)): {'bytes': p.stat().st_size,
            'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(OUT.rglob('*')) if p.is_file()}
with (OUT / 'manifest.json').open('x') as file:
    json.dump(manifest, file, indent=2)
print(json.dumps({'probe_results': str(OUT / 'probe-results.json'),
                  'sha256': runner.sha(OUT / 'probe-results.json'),
                  'manifest_sha256': runner.sha(OUT / 'manifest.json'),
                  'retained_files': len(manifest)}))
