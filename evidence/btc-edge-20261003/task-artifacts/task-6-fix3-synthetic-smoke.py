"""SYNTHETIC: mocked clock, final-export trust and HTTP; actual local pure adapter/audit."""
import copy
from pathlib import Path
import shutil
import sys
sys.path.insert(0, str(Path.cwd()))
from tests.test_edge_forward import ForwardTests
from research import edge_forward as f

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=False)
results = []
def retain(label, state):
    state = copy.deepcopy(state); directory = out / label; directory.mkdir()
    receipts = state['initial_receipts'] + [r for e in state['events'] for r in e['receipts']]
    for receipt in f.receipt_chain(receipts):
        original = Path(receipt['path']); target = directory / original.name
        shutil.copyfile(original, target); receipt['path'] = str(target.resolve())
        if 'form_path' in receipt:
            form = Path(receipt['form_path']); retained = directory / form.name
            shutil.copyfile(form, retained); receipt['form_path'] = str(retained.resolve())
    state = f.seal(state); f.audit(state)
    diary = directory / 'SYNTHETIC-diary.json'; diary.write_bytes(f.dump(state))
    results.append(dict(label=label, diary=str(diary), diary_sha256=f.sha(diary.read_bytes()),
                        market_ready=state['market_ready'], market_bootstrap=state['engine'].get('market_bootstrap'), events=len(state['events']),
                        event_kinds=[e['kind'] for e in state['events']], btc=state['btc'], fees=state['fees']))

normal = ForwardTests('test_proposal_modeled_fill_fee_net_conservation_and_checkpoint'); normal.setUp()
retain('normal', normal.enter())
pending = ForwardTests('test_deferred_init_is_empty_source_bound_paper_cash'); pending.setUp()
initial = pending.initialize_deferred(); retain('pending', initial)
stamp = pending.initial + 1000
warmed = pending.append_receipts(stamp, pending.warmup_receipts(stamp)); retain('warmup', warmed)
assert all(initial[k] == warmed[k] for k in ('wallet', 'btc', 'fees', 'funding'))
receipt = dict(synthetic=True, actual_public_observations=0, actual_account_days=0, native_cases=0,
               qualification='NOT_QUALIFIED', mocked_boundaries=['clock', 'final reviewed export', 'HTTP acquisition'],
               strategy_adapter='actual local pure runtime', ledger_audit='actual local implementation', states=results)
(out / 'receipt.json').write_bytes(f.dump(receipt)); print(f.dump(receipt).decode())
