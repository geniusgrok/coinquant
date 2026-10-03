"""Read-only checks of the retained Task1 fix1 receipt and diagnostic output."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
receipt = json.loads((root / 'task-1-fix1-acceptance.json').read_text())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
assert receipt['outputs'] == {n: sha(root / 'task-1-attribution-v3' / n) for n in receipt['outputs']}
body = json.loads((root / 'task-1-attribution-v3/attribution.json').read_text())
assert all(sha(Path(x['path'])) == x['sha256'] for x in body['inputs'])
assert not body['financial_producer_executed']
summaries = {'action', 'reason', 'quantity_after', 'constraint', 'error'}
checked = 0
for offset, comparison in body['coin'].items():
    for opportunity in comparison['opportunities']:
        for trace in [opportunity['first_exact_difference']] + opportunity['first_stage_divergences']:
            if trace and trace['event'] == 'decision':
                assert not summaries.intersection(trace['operational_fields'])
                for field in summaries.intersection(trace['exact_differences']):
                    assert trace['field_provenance'][field]['available_at_ms'] is None
                checked += 1
    identity = 1602172800000 if offset == '-60000' else 1687291200000
    opportunity = next(x for x in comparison['opportunities'] if x['actual_identity_left'] == identity)
    decision = next(x for x in opportunity['first_stage_divergences'] if x['event'] == 'decision')
    sizing = next(x for x in opportunity['first_stage_divergences'] if x['event'] == 'entry_sizing')
    assert 'constraint' in decision['exact_differences'] and 'constraint' not in decision['operational_fields']
    assert 'constraint' in sizing['operational_fields']
macro = next(x for x in body['coin']['60000']['opportunities'] if x['actual_identity_left'] == -1700643602800)
write = next(x for x in macro['first_stage_divergences'] if x['event'] == 'write_attempt')
assert 'requested_size' in write['facets'] and write['upstream_cause'] == 'unknown'
assert checked == receipt['decision_trace_checks'] == 168
old = json.loads((root / 'task-1-acceptance.json').read_text())
assert old['outputs'] == {n: sha(root / 'task-1-attribution-v2' / n) for n in old['outputs']}
print('PASS: 168 decision traces, both real I1 sizing links, real M1 write, 11 input hashes, v3 outputs, unchanged v2')
