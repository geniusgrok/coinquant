"""Exact-source five-account proof; does not relax an assessor or authorize trading."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ANALYSIS = Path('/workspace/btc-alpha-beta-analysis/spotquant')
CANONICAL = Path('/workspace/btc-alpha-beta-adoption/spotquant')
ROOT = Path('/workspace/btc-alpha-beta-next')
OUT = Path('/workspace/scratch/alpha-beta-next')
ANALYSIS_HEAD = '99fcf005d2cb15c13bb37322b65ab2863b19d65e'
ANALYSIS_PYTHON = '427f34ca3640cfa78f51173583af1d9c82f007baae155f3a992dcffb8171ad7b'
FROZEN_SPOT = dict(git_head='8ca002522fbdce531dcfbbb783ff4d152a7fd66c', dirty=False,
                   python_sources_sha256='0df8c537ee8d47db6e841778e8e37eac847e1a0c1151e379440081b9473ae026')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--expected-python-sha256', required=True)
    parser.add_argument('--final-report', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    tool_sha = sha(Path(__file__))
    sys.path.insert(0, str(ANALYSIS))
    from research import alpha_assessment as a
    current = a.source_identity()
    a.require(current == dict(git_head=ANALYSIS_HEAD, dirty=False,
                              python_sources_sha256=ANALYSIS_PYTHON), 'Immutable assessor source changed')
    a.verify_source(current, 'spot')
    final, final_sha = a.read_json(args.final_report)
    a.require(args.final_report.resolve() == OUT/'registered-final.json', 'Registered final path differs')
    final_receipt, final_receipt_sha = a.read_json(OUT/'registered-final.command.json')
    command = final_receipt['command']
    a.require(command.count('--out') == 1 and Path(command[command.index('--out')+1]).resolve()
              == args.final_report.resolve() and final_receipt['exit_code'] == 0
              and final_receipt['source_head'] == ANALYSIS_HEAD
              and final_receipt['output_sha256'] == final_sha, 'Registered final receipt differs')
    a.require(final['analysis_source'] == current and final['rules_freeze_ready'] is True
              and final['all_measured_accounts_valid'] is True and not final['pending']
              and not final['registered_work_pending'], 'Final registered study not valid/ready')
    a.require(final['native_cases'] == final['actual_account_days'] == 0
              and final['prospective_alpha_proven'] is False, 'Unexpected qualification claim')
    a.require(final['selection']['spot']['selected_research_candidate'] == 'atr-stop',
              'Exact selected candidate differs')
    inventory, inventory_sha = a.read_json(args.inventory)
    a.require(inventory['format'] == 'canonical-spot-five-v1'
              and inventory['source_head'] == args.expected_head, 'Canonical inventory/source differs')
    expected = {'base': ('base', False), 'fee150': ('fee150', False), 'slip2': ('slip2', False),
                'outage': ('outage', False), 'calibrated-base': ('base', True)}
    entries = inventory['files']
    a.require(len(entries) == 5 and {e['label'] for e in entries} == set(expected),
              'Exactly five canonical accounts required')
    for path, digest in inventory['review_bindings'].items():
        a.require(sha(Path(path)) == digest and args.expected_head in Path(path).read_text(),
                  'Canonical reviewed source evidence changed')
    a.require(len(inventory['review_bindings']) == 2, 'Two independent source reviews required')
    for path, digest in inventory['launch_bindings'].items():
        a.require(sha(Path(path)) == digest, 'Canonical launch evidence changed')
    audit_bindings = {}
    expected_audits = set()
    for key, account in final['accounts'].items():
        kind = key.split('/')[0]
        stage = ('risk' if key.startswith(kind+'/risk/') else
                 'unscaled' if account['candidate'] in a.SPEC[kind+'_candidates'] else 'combo')
        identity = (kind, stage, account['candidate']+'/'+account['scenario'], account['raw_bundle_sha256'])
        a.require(identity not in expected_audits, 'Duplicate registered audit identity')
        expected_audits.add(identity)
    for item in final['sensitivity']:
        account = item['account']
        identity = ('perp', 'sensitivity', account['candidate']+'/'+account['scenario'], item['raw_sha256'])
        a.require(identity not in expected_audits, 'Duplicate registered sensitivity identity')
        expected_audits.add(identity)
    actual_audits = set()
    for name in ('financial-audit-unscaled-index.json', 'financial-audit-remaining-index.json'):
        path = ROOT/'review'/name
        audit, audit_sha = a.read_json(path)
        if name.endswith('unscaled-index.json'):
            a.require(audit['account_count'] == 48, 'Independent unscaled inventory incomplete')
        else:
            a.require(audit['final_assessment_sha256'] == final_sha
                      and audit['final_inventory_exactly_reconciled'] is True
                      and audit['all_examined_checks_passed'] is True
                      and audit['all_reported_complete'] is True, 'Independent remaining audit incomplete')
        index_count = 0
        for entry in audit['audits']:
            report_path = Path(entry.get('audit_path', entry.get('path', '')))
            digest = entry.get('audit_sha256', entry.get('sha256'))
            report, report_sha = a.read_json(report_path)
            a.require(report_sha == digest and report['all_examined_checks_passed'] is True
                      and report['all_reported_complete'] is True
                      and report['raw_sha256'] == entry['raw_sha256'], 'Independent audit evidence changed')
            kind = report['kind']
            stage = 'unscaled' if name.endswith('unscaled-index.json') else entry['stage']
            a.require(kind in ('spot', 'perp') and stage in ('unscaled', 'risk', 'combo', 'sensitivity')
                      and (name.endswith('unscaled-index.json') or entry['kind'] == kind),
                      'Independent audit kind/stage differs')
            a.require(report['source'] == final['inputs'][kind]['metadata']['source']
                      and sha(Path(report['raw_path'])) == report['raw_sha256'], 'Audited source/raw differs')
            for key, account in report['accounts'].items():
                a.require(account['independent_checks_passed'] is True and account['reported_complete'] is True
                          and account['producer_audit_passed'] is True and not account['errors'],
                          'Independent account checks incomplete')
                identity = (kind, stage, key, report['raw_sha256'])
                a.require(identity not in actual_audits, 'Duplicate independent audit identity')
                actual_audits.add(identity)
                index_count += 1
        a.require(index_count == audit['account_count'], 'Independent audit count differs from actual coverage')
        audit_bindings[str(path)] = audit_sha
    a.require(actual_audits == expected_audits, 'Independent audit identities do not cover final study exactly')
    calibration_path = Path(inventory['calibration_path'])
    calibration, calibration_sha = a.read_json(calibration_path)
    a.require(calibration_sha == inventory['calibration_sha256']
              == final['risk_calibrations']['spot']['raw_sha256'], 'Actual project calibration differs')
    global_cal, global_sha = a.read_json(OUT/'registered-calibration.json')
    a.require(global_sha == final['calibration_sha256'], 'Global calibration raw differs')
    a.load_project_calibration(calibration_path, global_cal, 'spot')
    early_receipt_path = OUT/'spot-early-risk-completed.json'
    early, early_sha = a.read_json(early_receipt_path)
    a.require(early_sha == inventory['reference_completion_receipt_sha256'], 'Early receipt changed')
    risk_path = Path(inventory['reference_risk_path'])
    a.require(sha(risk_path) == inventory['reference_risk_sha256']
              == early['actual_risk_sha256'] == final['inputs']['risk_spot']['raw_sha256'],
              'Frozen actual risk source differs')
    env = a.environment(ROOT/'coinquant/research/session_schedule.json',
                        ROOT/'starquant/data/usdcny_frankfurter.json', Path('/tmp/spotquant-market/klines'))
    a.require(env == final['input_environment'], 'Final market/FX/schedule/spec/protocol inputs changed')
    bars = a.load_daily(Path('/tmp/spotquant-market/klines'), a.END_MS, require_through=a.END_MS)
    fx = a.PriorFX(ROOT/'starquant/data/usdcny_frankfurter.json')
    usd, cny = a.market_returns_for(bars, fx)
    unscaled_path = OUT/'spot-singletons/atr-stop.json.gz'
    unscaled = a.consume(unscaled_path, 'spot', env, bars, fx, usd, cny,
                         expected={'atr-stop/'+s for s in a.SPEC['spot_scenarios']})
    risk = a.consume(risk_path, 'spot', env, bars, fx, usd, cny, calibration=calibration,
                     calibration_sha=calibration_sha,
                     expected={name+'/base' for name in a.SPEC['spot_candidates']})
    a.require(unscaled['metadata']['source'] == risk['metadata']['source'] == FROZEN_SPOT,
              'Frozen reference executable differs')
    exact_source = dict(git_head=args.expected_head, dirty=False,
                        python_sources_sha256=args.expected_python_sha256)
    files = a.verify_source(exact_source, 'spot')
    a.require(files['research/alpha_beta_spec.json'] == env['spec_sha256']
              and files['research/alpha-beta-PROTOCOL.md'] == env['protocol_sha256'],
              'Adopted committed declaration differs')
    comparisons = []
    input_keys = ('spec_sha256', 'protocol_sha256', 'fx_sha256', 'schedule_sha256', 'market_sha256')
    for entry in entries:
        label = entry['label']
        scenario, calibrated = expected[label]
        a.require((entry['scenario'], entry['calibrated']) == (scenario, calibrated),
                  'Canonical case labeling differs')
        path = args.inventory.parent/entry['path']
        a.require(sha(path) == entry['sha256'], 'Canonical original raw changed')
        command_path = args.inventory.parent/(label+'.command.json')
        receipt, receipt_sha = a.read_json(command_path)
        compression, compression_sha = a.read_json(args.inventory.parent/(label+'.compression.json'))
        a.require(receipt['exit_code'] == 0 and receipt['source_head'] == args.expected_head
                  and receipt['review_bindings'] == inventory['review_bindings']
                  and receipt['launch_bindings'] == inventory['launch_bindings'], 'Canonical command differs')
        command = receipt['command']
        expected_command = [sys.executable, '-u', '-m', 'research.adoption_spot', '--scenario', scenario,
                            '--out', str(args.inventory.parent/(label+'.json'))]
        if calibrated:
            expected_command += ['--risk-calibration', str(calibration_path)]
        a.require(command == expected_command and receipt['cwd'] == str(CANONICAL)
                  and sha(args.inventory.parent/(label+'.run.log')) == receipt['log_sha256'],
                  'Canonical command case/log differs')
        a.require(compression['lossless_roundtrip_verified'] is True
                  and compression['original_sha256'] == receipt['output_sha256']
                  and compression['retained_sha256'] == entry['sha256'], 'Canonical compression proof differs')
        with gzip.open(path, 'rb') as stream:
            a.require(hashlib.file_digest(stream, 'sha256').hexdigest() == compression['original_sha256'],
                      'Canonical compressed bytes do not reproduce original')
        raw, raw_sha = a.read_json(path)
        a.require(raw_sha == entry['sha256'] and raw['source'] == exact_source
                  and raw['adoption']['execution'] == 'canonical_shared_session'
                  and raw['adoption']['candidate'] == 'atr-stop'
                  and raw['adoption']['rule'] == '2026-10-02-atr-stop'
                  and raw['risk_calibration_sha256'] == (calibration_sha if calibrated else None),
                  'Canonical executable/marker/calibration provenance differs')
        a.require(set(raw['results']) == {'atr-stop-'+scenario}
                  and raw['results']['atr-stop-'+scenario]['research_identity']['execution']
                  == 'canonical_shared_session', 'Canonical row execution provenance differs')
        del raw
        candidate = a.consume(path, 'spot', env, bars, fx, usd, cny,
                              expected={'atr-stop/'+scenario},
                              calibration=calibration if calibrated else None,
                              calibration_sha=calibration_sha if calibrated else None)
        a.require(candidate['metadata']['source'] == exact_source
                  and candidate['raw_sha256'] == entry['sha256'], 'Canonical executable/raw differs')
        reference = risk if calibrated else unscaled
        for key in input_keys:
            a.require(candidate['metadata'][key] == reference['metadata'][key], 'Canonical input differs: '+key)
        key = 'atr-stop/'+scenario
        measured, original = candidate['accounts'][key], reference['accounts'][key]
        report_key = 'spot/'+('risk/' if calibrated else '')+key
        registered = final['accounts'][report_key]
        a.require(original['valid'] and measured['valid'] and registered['valid'], 'Incomplete/invalid canonical/reference')
        a.require(original['raw_bundle_sha256'] == registered['raw_bundle_sha256']
                  and original['evidence_sha256'] == registered['evidence_sha256'], 'Final frozen account differs')
        a.require(measured['evidence_sha256'] == original['evidence_sha256'],
                  'Canonical six-group execution differs: '+label)
        comparisons.append(dict(label=label, scenario=scenario, calibrated=calibrated,
              canonical_raw_sha256=entry['sha256'], reference_raw_sha256=original['raw_bundle_sha256'],
              command_receipt_sha256=receipt_sha, compression_proof_sha256=compression_sha,
              six_evidence_groups=measured['evidence_sha256'], all_six_equal=True))
    names = subprocess.check_output(['git', 'diff', '--name-only', ANALYSIS_HEAD, args.expected_head],
                                    cwd=ANALYSIS, text=True).splitlines()
    changes = []
    for name in names:
        def committed(head):
            result = subprocess.run(['git', 'show', head+':'+name], cwd=ANALYSIS, capture_output=True)
            return hashlib.sha256(result.stdout).hexdigest() if result.returncode == 0 else None
        changes.append(dict(path=name, before_sha256=committed(ANALYSIS_HEAD),
                            after_sha256=committed(args.expected_head)))
    a.require(sha(Path(__file__)) == tool_sha, 'Bridge verifier changed during proof')
    a.write_new(args.out, dict(format='exact-spot-adoption-bridge-v1',
          verifier_sha256=tool_sha,
          analysis_source=current, frozen_source=FROZEN_SPOT, canonical_source=exact_source,
          final_report_sha256=final_sha, final_command_receipt_sha256=final_receipt_sha,
          independent_audit_indices=audit_bindings, canonical_inventory_sha256=inventory_sha,
          review_bindings=inventory['review_bindings'], spec_sha256=env['spec_sha256'],
          protocol_sha256=env['protocol_sha256'], input_environment=env,
          actual_calibration_sha256=calibration_sha, global_calibration_sha256=global_sha,
          changed_paths=changes, comparisons=comparisons, all_five_complete_and_six_groups_equal=True,
          assessment_source_gates_unchanged=True, independent_adoption_review_pending=True,
          adoption_approved=False, native_cases=0, actual_account_days=0,
          diary_execution='frozen research through immutable analysis99, not current canonical runtime',
          limitations=['Historical proxy equivalence, not native qualification or prospective alpha proof.']))


if __name__ == '__main__':
    main()
