"""Read-only state proof for one completed 795-session receipt; never run a strategy."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from decimal import Decimal

source = Path(__file__).with_name('original_compare_arms.py')
assert hashlib.sha256(source.read_bytes()).hexdigest() == 'b8d097a60f390da0cc95f5424ff2f8649c7250045fa82ba5e3c7f7acffd3145e'
from original_compare_arms import read, sha, sqlite_check

if sys.flags.optimize:
    raise RuntimeError('State auditing requires assertions enabled')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--receipt', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
assert not args.out.exists(), 'Preserve previous audit output'
row = read(args.receipt)
assert row['complete'] and row['failure'] is None and not row['can_resume'] and row['original_window_complete']
assert row['scope'] == {'kind': 'original-full', 'planned_sessions': 795} and not row['sqlite']['pending']
report_path = Path(row['reports']['path'])
assert sha(report_path) == row['reports']['sha256']
reports = [json.loads(line) for line in report_path.read_text().splitlines()]
assert len(reports) == row['session_count'] == row['reports']['count'] == 795
before = sha(Path(row['state_directory']) / 'intents.sqlite')
canonical, proof = sqlite_check(row, reports)
assert before == proof['database_sha256'], 'Completed state changed during read-only audit'
tables = canonical['tables']
assert tables['native_fills']['columns'] == ['trade_id', 'entry_id', 'payload']
assert tables['native_income']['columns'] == ['kind', 'transaction_id', 'payload']
fills = {identity: json.loads(payload) for identity, owner, payload in tables['native_fills']['rows']}
income = {(kind, identity): json.loads(payload) for kind, identity, payload in tables['native_income']['rows']}
venue_fills = {event['id']: event for event in row['financial']['trades']}
venue_income = {(event['incomeType'], event['tranId']): event for event in row['financial']['funding_ledger']}
assert len(venue_fills) == len(row['financial']['trades']) and len(venue_income) == len(row['financial']['funding_ledger'])
assert all(identity == event['id'] and event == venue_fills[identity] for identity, event in fills.items())
numeric_income = lambda event: dict(event, income=Decimal(event['income']))
assert all(identity == (event['incomeType'], event['tranId']) and numeric_income(event) == numeric_income(venue_income[identity]) for identity, event in income.items())
meta = {key: json.loads(value) for key, value in tables['meta']['rows']}
native = dict(archived_fills=len(fills), venue_fills=len(venue_fills), archived_income=len(income), venue_income=len(venue_income), fills_exact_payload_match=True, income_exact_decimal_match=True,
              ownership_coverage=meta.get('ownership_coverage'), income_coverage=meta.get('income_coverage'), venue_fills_not_archived=[event for identity, event in venue_fills.items() if identity not in fills], venue_income_not_archived=[event for identity, event in venue_income.items() if identity not in income],
              boundary='Matches every locally archived native row only. Venue events outside the local archive, including unattended terminal events after the last observation, remain explicitly unarchived; no full-venue archive claim.')
result = dict(passed=True, scope='completed-original795-state-only', receipt=str(args.receipt.resolve()), receipt_sha256=sha(args.receipt), reports_sha256=sha(report_path), production_head=row['source']['git_head'], validator_sha256=sha(__file__), original_validator_sha256=sha(source), sqlite=proof, native_archive=native)
args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
print(json.dumps(dict(passed=True, out=str(args.out.resolve()), sha256=sha(args.out), table_counts=proof['table_counts'], archived_fills=len(fills), venue_fills=len(venue_fills), archived_income=len(income), venue_income=len(venue_income))))
