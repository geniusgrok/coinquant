"""Separate retrospective call labels from the executed DC10 account."""
import csv
import gzip
import hashlib
import io
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile

LABEL_SHA = '0146c119104846cdc4b9ca3367989f45d58c42b4d726014d275d5c69398d892a'
ACCOUNT_SHA = '2ed9b042cd7000d9b3bece516ef8b47ffbf7c975d6f598faa7c3d29038442621'


def read_verified(path, expected):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f'original changed: {path}')
    return raw


def audit(label_path, account_path):
    labels = json.loads(read_verified(label_path, LABEL_SHA))
    if len(labels['rows']) != 795 or len({r['call'] for r in labels['rows']}) != 795:
        raise ValueError('frozen full-window invocation identities changed')
    qualifying = sorted((r for r in labels['rows'] if r['past_drop_at_least_10pct']),
                        key=lambda r: r['call'])
    events = []
    for row in qualifying:
        call = datetime.fromisoformat(row['call'].replace('Z', '+00:00'))
        if not events or call >= events[-1]['last_call'] + timedelta(hours=168):
            events.append(dict(first_call=call, last_call=call, calls=1))
        else:
            events[-1]['last_call'] = call
            events[-1]['calls'] += 1

    with ZipFile(io.BytesIO(read_verified(account_path, ACCOUNT_SHA))) as archive:
        root = 'DC10-development-v1/'
        decisions = list(csv.DictReader(io.StringIO(gzip.decompress(
            archive.read(root + 'decisions.csv.gz')).decode())))
        summary = json.loads(archive.read(root + 'execution_summary.json'))
        attribution = json.loads(archive.read('DC10_ATTRIBUTION.json'))
        result = json.loads(archive.read(root + 'result.json'))
    parents = summary['parents']
    filled = [p for p in parents if Decimal(p['filled']) > 0]
    segments = attribution['segments']
    starts = {int(datetime.fromisoformat(s['start'].replace('Z', '+00:00')).timestamp() * 1000): s
              for s in segments}
    if len(decisions) != 468 or len(filled) != 29 or len(starts) != 29 or len(segments) != 29:
        raise ValueError('account identities or counts changed')
    if {p['first_fill'] for p in filled} != set(starts):
        raise ValueError('parent fills do not match closed account segments')
    net = sum((Decimal(s['net_wallet_usdt']) for s in segments), Decimal(0))
    if abs(net - sum(Decimal(x) for x in attribution['year_entry_net_wallet_usdt'].values())) > Decimal('.000001'):
        raise ValueError('segment and year account net differ')
    years = sorted({r['call'][:4] for r in qualifying})
    return {
        'scope': 'Retrospective price events and the separate executed DC10 development path; no counterfactual OI model',
        'source_sha256': {'labels': LABEL_SHA, 'account_zip': ACCOUNT_SHA},
        'event_rule': 'Join qualifying calls whose 168-hour future windows overlap; first call anchors event, no future label is used to select an event',
        'year': {y: {'qualifying_calls': sum(r['call'].startswith(y) for r in qualifying),
                     'overlap_events': sum(e['first_call'].year == int(y) for e in events)} for y in years},
        'events_2025': [{'first_call': e['first_call'].isoformat(),
                         'last_call': e['last_call'].isoformat(), 'calls': e['calls']}
                        for e in events if e['first_call'].year == 2025],
        'development_account': {
            'invocations': len(decisions), 'decision_actions': dict(Counter(d['action'] for d in decisions)),
            'created_parents': len(parents), 'filled_parents': len(filled),
            'closed_segments': len(segments),
            'positive_segments': sum(Decimal(s['net_wallet_usdt']) > 0 for s in segments),
            'negative_segments': sum(Decimal(s['net_wallet_usdt']) < 0 for s in segments),
            'net_wallet_usdt': str(net), 'cost_net_cagr': result['cagr'],
            'continuous_mdd': result['mdd_conservative_envelope'],
            'terminal_cny': result['final_cny'],
        },
    }


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: event_net_audit.py CALL_LABELS.json DC10_ACCOUNT.zip')
    print(json.dumps(audit(sys.argv[1], sys.argv[2]), ensure_ascii=False, indent=2))
