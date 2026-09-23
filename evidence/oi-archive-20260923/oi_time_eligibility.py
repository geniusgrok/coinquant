"""Necessary archive-version timing screen, never an OI strategy or fill model."""
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zipfile import ZipFile

MANIFEST_SHA = 'abc9a7bde759f23598f31b7ea40e9f197be8efcb29cb1ac964058537c2f30bc6'
LABEL_SHA = '0146c119104846cdc4b9ca3367989f45d58c42b4d726014d275d5c69398d892a'
ACCOUNT_SHA = '2ed9b042cd7000d9b3bece516ef8b47ffbf7c975d6f598faa7c3d29038442621'


def verified(path, digest):
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f'original digest mismatch: {path}')
    return data


def run(manifest_path, labels_path, account_path):
    manifest = json.loads(verified(manifest_path, MANIFEST_SHA))
    labels = json.loads(verified(labels_path, LABEL_SHA))['rows']
    with ZipFile(account_path) as account:
        if hashlib.sha256(Path(account_path).read_bytes()).hexdigest() != ACCOUNT_SHA:
            raise ValueError('account original digest mismatch')
        segments = json.loads(account.read('DC10_ATTRIBUTION.json'))['segments']
    if len(manifest['days']) != 1461 or len(labels) != 795 or len(segments) != 29:
        raise ValueError('frozen evidence count changed')
    days = {x['day']: x for x in manifest['days']}
    by_call = {x['call']: x for x in labels}
    if len(by_call) != 795:
        raise ValueError('duplicate invocation labels')
    counts = Counter()
    valid_calls = set()
    drop_calls = []
    for row in labels:
        call = datetime.fromisoformat(row['call'].replace('Z', '+00:00'))
        if call >= datetime(2024, 1, 1, tzinfo=timezone.utc):
            continue
        year = str(call.year)
        counts[(year, 'calls')] += 1
        # Previous two *finished* UTC days, giving the newer archive at least one
        # whole calendar day to appear. No within-day value or price is consulted.
        earlier = [days.get(str(call.date() - timedelta(days=offset))) for offset in (2, 3)]
        complete = all(x is not None and x['status'] == 'verified_complete' for x in earlier)
        counts[(year, 'two_complete_days')] += complete
        # Last-Modified before call is a necessary check on today's bytes;
        # it is NOT a point-in-time archive of old revisions or publication proof.
        prior = complete and all(datetime.strptime(x['last_modified'],
                         '%a, %d %b %Y %H:%M:%S GMT').replace(tzinfo=timezone.utc) <= call
                         for x in earlier)
        counts[(year, 'current_bytes_modified_before_call')] += prior
        if prior:
            valid_calls.add(row['call'])
            if row['past_drop_at_least_10pct']:
                drop_calls.append(row['call'])
    if sum(counts[(str(y), 'calls')] for y in range(2020, 2024)) != 468:
        raise ValueError('development calls changed')
    matches = []
    for segment in segments:
        first_fill = datetime.fromisoformat(segment['start'].replace('Z', '+00:00'))
        call = first_fill.replace(minute=0, second=0, microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')
        if call not in by_call:
            raise ValueError('segment could not join an original invocation')
        if call in valid_calls:
            matches.append({'call': call, 'first_fill': segment['start'],
                            'existing_dc10_net_wallet_usdt': segment['net_wallet_usdt']})
    return {
        'scope': 'Necessary current-archive version-timing screen only; NOT sufficient historical publication evidence or a counterfactual OI strategy',
        'input_sha256': {'manifest': MANIFEST_SHA, 'call_labels': LABEL_SHA, 'existing_account': ACCOUNT_SHA},
        'two_earlier_utc_days': [2, 3],
        'by_year': {str(y): {field: counts[(str(y), field)] for field in
                   ('calls', 'two_complete_days', 'current_bytes_modified_before_call')}
                   for y in range(2020, 2024)},
        'necessary_condition_calls': len(valid_calls),
        'price_drop_10pct_intersection': drop_calls,
        'existing_dc10_filled_segments_intersection': matches,
    }


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit('usage: oi_time_eligibility.py MANIFEST.json CALL_LABELS.json DC10_ACCOUNT.zip')
    print(json.dumps(run(*sys.argv[1:]), ensure_ascii=False, indent=2))
