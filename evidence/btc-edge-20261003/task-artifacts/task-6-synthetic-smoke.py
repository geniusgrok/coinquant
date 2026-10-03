"""Synthetic-only fixture; mocked wall clocks and export boundary, no network."""
import copy
import json
from pathlib import Path
import shutil
import sys
from tests.test_edge_forward import ForwardTests
from research import edge_forward as f

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=False)
case = ForwardTests('test_proposal_modeled_fill_fee_net_conservation_and_checkpoint')
case.setUp()
state = case.enter()
for receipt in state['initial_receipts'] + [r for e in state['events'] for r in e['receipts']]:
    original = Path(receipt['path']); target = out / original.name
    shutil.copyfile(original, target); receipt['path'] = str(target.resolve())
state = f.seal(state)
f.audit(state)
(out / 'SYNTHETIC-diary.json').write_bytes(f.dump(state))
(out / 'receipt.json').write_bytes(f.dump(dict(synthetic=True, actual_public_observations=0, actual_account_days=0,
    qualification='NOT_QUALIFIED', mocked_boundaries=['clock', 'final reviewed export', 'HTTP acquisition'],
    strategy_adapter='actual local pure runtime', ledger_audit='actual local implementation',
    events=len(state['events']), btc=state['btc'], fees=state['fees'], diary_sha256=f.sha(f.dump(state)))))
print((out / 'receipt.json').read_text())
