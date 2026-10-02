"""Read-only audits of completed original risk/combination/sensitivity artifacts."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

REVIEW = Path('/workspace/btc-alpha-beta-next/review')
OUT = Path('/workspace/scratch/alpha-beta-next')
CHECKER = REVIEW/'independent_financial_audit.py'
CHECKER_SHA = '492d46ff9bbff72f1291ad77988fbf8478b35fd880c818e1d3979a6215f1897c'
INDEX = []

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def read(path):
    return json.loads(path.read_text())

def write(path, body):
    with path.open('x') as stream:
        json.dump(body, stream, indent=2); stream.write('\n')

def wait(path):
    while not path.exists():
        time.sleep(10)

def command_receipt(label):
    path = OUT/(label+'.command.json')
    wait(path)
    receipt = read(path)
    if receipt['exit_code'] != 0:
        raise RuntimeError('No completed financial input for failed command: '+label)
    command = receipt['command']
    if command.count('--out') != 1:
        raise ValueError('Ambiguous completed command output')
    output = Path(command[command.index('--out')+1])
    if output != OUT/(label+'.json') or sha(output) != receipt['output_sha256']:
        raise ValueError('Completed report bytes differ from command receipt')
    return receipt

def audit_one(raw, kind, label, stage, calibration=None, baseline=None, unscaled=None):
    digest = sha(raw)
    target = REVIEW/('financial-audit-'+label+'.json')
    if target.exists():
        raise ValueError('Never reuse an audit with potentially different verification context')
    else:
        if sha(CHECKER) != CHECKER_SHA:
            raise ValueError('Independent checker changed; new review required')
        command = [sys.executable, str(CHECKER), '--bundle', str(raw), '--sha256', digest,
                   '--kind', kind, '--out', str(target)]
        for flag, path in [('calibration', calibration), ('baseline-audit', baseline), ('unscaled-audit', unscaled)]:
            if path is not None:
                command += ['--'+flag, str(path)]
        log = target.with_suffix('.run.log')
        started = time.monotonic()
        with log.open('x') as stream:
            result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT,
                                    env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        write(target.with_suffix('.command.json'), {'command': command, 'checker_sha256': CHECKER_SHA,
              'elapsed_seconds': time.monotonic()-started, 'exit_code': result.returncode,
              'log_sha256': sha(log), 'output_sha256': sha(target) if target.exists() else None,
              'verification_context': {name: {'path': str(path), 'sha256': sha(path)} for name, path in
                   [('calibration', calibration), ('baseline_audit', baseline), ('unscaled_audit', unscaled)]
                   if path is not None}})
        if result.returncode:
            raise RuntimeError('Independent audit failed; originals retained: '+label)
        if sha(CHECKER) != CHECKER_SHA:
            raise ValueError('Independent checker changed while auditing')
        report = read(target)
    INDEX.append({'label': label, 'raw_path': str(raw), 'raw_sha256': digest,
                  'audit_path': str(target), 'audit_sha256': sha(target),
                  'kind': kind, 'stage': stage, 'account_keys': sorted(report['accounts']),
                  'accounts': len(report['accounts']),
                  'all_checks_passed': report['all_examined_checks_passed'],
                  'all_reported_complete': report['all_reported_complete']})
    print(json.dumps(INDEX[-1]), flush=True)
    return set(report['accounts'])

def audit_path(path, kind, label, expected_sha, expected_keys, **kwargs):
    if sha(path) != expected_sha:
        raise ValueError('Audit input differs from assessment original bytes')
    seen = set()
    if path.suffix == '.json' and read(path).get('format') == 'alpha-account-manifest-v1':
        manifest = read(path)
        if manifest['kind'] != kind:
            raise ValueError('Wrong audit manifest kind')
        for i, entry in enumerate(manifest['files']):
            child = path.parent/entry['path']
            if sha(child) != entry['sha256']:
                raise ValueError('Audit manifest differs from original child bytes')
            keys = audit_one(child, kind, label+'-'+str(i), **kwargs)
            if seen & keys:
                raise ValueError('Duplicate audited manifest accounts')
            seen.update(keys)
    else:
        seen = audit_one(path, kind, label, **kwargs)
    if seen != set(expected_keys):
        raise ValueError('Audited account inventory differs from assessment')

def stage_keys(report, kind, stage):
    prefix = kind+'/risk/' if stage=='risk' else kind+'/'
    if stage=='risk':
        return {key[len(prefix):] for key in report['accounts'] if key.startswith(prefix)}
    return {account['candidate']+'/'+account['scenario'] for key, account in report['accounts'].items()
            if key.startswith(prefix) and '/risk/' not in key and account['candidate'] not in
               ('consensus', 'trend-reentry', 'target-participation', 'atr-close', 'atr-stop',
                'core-permanent', 'core-slow', 'incumbent', 'fresh-entry', 'atr-trail',
                'compression-breakout', 'single-topup')}

def verify_final_inventory(final):
    actual = {}
    for entry in INDEX:
        if sha(Path(entry['audit_path'])) != entry['audit_sha256'] or sha(Path(entry['raw_path'])) != entry['raw_sha256']:
            raise ValueError('Audited evidence changed before final reconciliation')
        for key in entry['account_keys']:
            identity = (entry['kind'], entry['stage'], key, entry['raw_sha256'])
            if identity in actual:
                raise ValueError('Duplicate final audit identity')
            actual[identity] = True
    expected = set()
    for kind in ('spot', 'perp'):
        for stage in ('risk', 'combo'):
            for key in stage_keys(final, kind, stage):
                account = final['accounts'][kind+('/risk/' if stage=='risk' else '/')+key]
                expected.add((kind, stage, key, account['raw_bundle_sha256']))
    for item in final['sensitivity']:
        account = item['account']
        expected.add(('perp', 'sensitivity', account['candidate']+'/'+account['scenario'], item['raw_sha256']))
    if set(actual) != expected:
        raise ValueError('Final risk/combo/sensitivity inventory differs from audited originals')

def main():
    spot_unscaled = REVIEW/'financial-audit-spot-unscaled-comparison.json'
    wait(spot_unscaled)
    done = OUT/'spot-early-risk-completed.json'
    wait(done)
    receipt = read(done)
    if receipt['actual_risk_path']:
        raw = Path(receipt['actual_risk_path'])
        calibration = Path(receipt['actual_calibration_path'])
        if sha(raw) != receipt['actual_risk_sha256'] or sha(calibration) != receipt['actual_calibration_sha256']:
            raise ValueError('Early Spot receipt original hash differs')
        profiles = read(calibration)['profiles']
        audit_path(raw, 'spot', 'risk-spot-project-early', receipt['actual_risk_sha256'],
                   {name+'/base' for name in profiles}, stage='risk', calibration=calibration,
                   baseline=spot_unscaled, unscaled=spot_unscaled)
    command_receipt('registered-risk')
    report = read(OUT/'registered-risk.json')
    perp_unscaled = REVIEW/'financial-audit-perp-singletons.json'
    wait(perp_unscaled)
    risk = report['inputs'].get('risk_perp')
    if risk:
        audit_path(Path(risk['path']), 'perp', 'risk-perp', risk['raw_sha256'],
                   stage_keys(report, 'perp', 'risk'), stage='risk', calibration=OUT/'registered-calibration.json',
                   baseline=perp_unscaled, unscaled=perp_unscaled)
    command_receipt('registered-combinations')
    combined = read(OUT/'registered-combinations.json')
    for kind in ('spot', 'perp'):
        combo = combined['inputs'].get('combo_'+kind)
        if combo:
            audit_path(Path(combo['path']), kind, 'combo-'+kind, combo['raw_sha256'],
                       stage_keys(combined, kind, 'combo'), stage='combo')
    command_receipt('registered-final')
    final = read(OUT/'registered-final.json')
    command = read(OUT/'registered-final.command.json')['command']
    paths = [Path(command[i+1]) for i, token in enumerate(command) if token=='--sensitivity-perp']
    expected_sensitivity = {item['raw_sha256']: item for item in final['sensitivity']}
    if len(expected_sensitivity)!=len(final['sensitivity']) or len(paths)!=len(expected_sensitivity):
        raise ValueError('Sensitivity command/report inventory differs')
    for i, path in enumerate(paths):
        digest = sha(path)
        if digest not in expected_sensitivity:
            raise ValueError('Sensitivity path differs from final measured bytes')
        item = expected_sensitivity.pop(digest)
        audit_path(path, 'perp', 'sensitivity-perp-'+str(i), digest,
                   {item['candidate']+'/base'}, stage='sensitivity')
    if expected_sensitivity:
        raise ValueError('Missing final sensitivity audits')
    if final['pending']:
        raise ValueError('Final declared registered inventory still pending')
    verify_final_inventory(final)
    write(REVIEW/'financial-audit-remaining-index.json', {
        'scope': 'Actual risk, applicable combination and sensitivity originals; unscaled index is separate.',
        'final_assessment_sha256': sha(OUT/'registered-final.json'), 'audits': INDEX,
        'final_inventory_exactly_reconciled': True,
        'account_count': sum(row['accounts'] for row in INDEX),
        'all_examined_checks_passed': all(row['all_checks_passed'] for row in INDEX),
        'all_reported_complete': all(row['all_reported_complete'] for row in INDEX),
        'adoption_approval': False, 'continuous_proxy_independently_replayed': False})

if __name__ == '__main__':
    main()
