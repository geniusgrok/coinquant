"""Read-only source/reference/partial-envelope verification; no account producer."""
import json
from pathlib import Path
from research import edge_assessment as e

artifacts = Path('/workspace/btc-alpha-beta-improve/task-artifacts')
source = e.old.source_identity()
source_files = e.verify_source(source, 'spot')
references, bound = e.approved_references(e.ROOT / 'evidence/alpha-beta-next-20261002')
fx = e.old.PriorFX(e.ROOT.parent / 'starquant/data/usdcny_frankfurter.json')
checks = []
for kind, scenarios in references.items():
    for scenario, reference in scenarios.items():
        row = reference['row']
        proof = e.monetary_audit(row, kind, fx)
        daily = list(row['daily'].values()) if kind == 'spot' else row['daily']
        e.audit_daily(row, daily, kind, fx)
        if kind == 'perp':
            e.verify_coin_timing(row)
        checks.append(dict(kind=kind, scenario=scenario, raw_sha256=reference['raw_sha256'],
                           source=(reference['bundle'] if kind == 'spot' else reference['bundle']['inputs'])['source'],
                           six_groups=e.old.evidence_fingerprints(row, kind), monetary_passed=proof['passed'],
                           daily_snapshots_reconstructed=len(daily)))
env = e.environment(e.ROOT.parent / 'coinquant/research/session_schedule.json',
                    e.ROOT.parent / 'starquant/data/usdcny_frankfurter.json',
                    Path('/tmp/spotquant-market/klines'), artifacts / 'edge-features-v1.json')
env.update(coin_market='/tmp/coinquant-market', coin_prints='/workspace/scratch/alpha-beta-next/public-print-vault')
paths = {'spot': Path('/tmp/spot-edge-task3-final-crowding-interaction-base-1790988715073070248.json.gz'),
         'perp': Path('/tmp/coin-edge-task4-fix1-4924855-all.json.gz')}
accounts, files, rejected = e.ingest(paths, env, [], fx, [], [], {'spot': {}, 'perp': {}})
assert not rejected and len(accounts) == 17
assert all(a['status'] == 'pending' and a['reasons'] == ['measurement_incomplete'] for a in accounts.values())
report = dict(format='task-5-fix1-read-only-verification-v1', source=source, source_files=source_files,
              reference_bindings=bound, original_account_checks=checks, consumed_smoke_bindings=files,
              smoke_accounts={key: {k: a[k] for k in ('status', 'reasons', 'source', 'raw_sha256')} for key, a in accounts.items()},
              required_unconditional_accounts=len(e.required_matrix()), native_cases=0, actual_account_days=0,
              qualification='NOT_QUALIFIED', full_financial_producers_run=0, scope='read-only retained accepted evidence and incomplete smoke rows')
import copy
mutated = copy.deepcopy(references['spot']['base']['row'])
mutated['daily'] = [list(mutated['daily'].values())[-1]]
try:
    e.original_curve(mutated, [], fx, 'spot')
except ValueError as exc:
    report['retained_original_terminal_only_mutation'] = {'rejected': True, 'reason': str(exc),
        'original_raw_sha256': references['spot']['base']['raw_sha256'], 'mutation': 'memory only; original bytes unchanged'}
else:
    raise AssertionError('missing held daily evidence accepted')
e.write_new(artifacts / 'task-5-fix1-final-verification.json', report)
print(json.dumps({'source': source, 'verification_sha256': e.sha(artifacts / 'task-5-fix1-final-verification.json'),
                  'references': len(checks), 'partial_accounts': len(accounts), 'new_producers': 0}))
