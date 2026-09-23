"""Read-only funding state joined to two previously executed account paths."""
import csv
import hashlib
import io
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile

CAMPAIGN_SHA = 'e150a05e257b3813ed874f3dc3d62d1e170c3344687db34c540d9d1c422f4df5'
DC10_SHA = '2ed9b042cd7000d9b3bece516ef8b47ffbf7c975d6f598faa7c3d29038442621'


def verified(path, digest):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError(f'original differs: {path}')
    return raw


def funding_rows(root):
    rows, hashes = [], []
    for year in range(2020, 2027):
        for month in range(1, 13):
            if (year, month) > (2026, 8):
                break
            name = f'BTCUSDT-fundingRate-{year}-{month:02}.zip'
            path = root / name
            raw = path.read_bytes()
            sha = hashlib.sha256(raw).hexdigest()
            checksum = (root / (name + '.CHECKSUM')).read_text().strip().split()
            if checksum != [sha, name]:
                raise ValueError(f'official funding checksum differs: {name}')
            hashes.append({'file': name, 'sha256': sha})
            with ZipFile(io.BytesIO(raw)) as archive:
                members = archive.namelist()
                if len(members) != 1 or archive.testzip() is not None:
                    raise ValueError(f'invalid funding ZIP: {name}')
                for row in csv.DictReader(io.TextIOWrapper(archive.open(members[0]))):
                    if row['funding_interval_hours'] != '8':
                        raise ValueError('funding interval changed')
                    rows.append((int(row['calc_time']), Decimal(row['last_funding_rate'])))
    rows.sort()
    if len(rows) != len({t // (8 * 3600000) for t, _ in rows}):
        raise ValueError('duplicate funding settlement')
    return rows, hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(), len(hashes)


def audit(root, campaigns, dc10):
    rates, source_sha, archive_count = funding_rows(Path(root))
    sx = json.loads(verified(campaigns, CAMPAIGN_SHA))['campaigns']
    with ZipFile(io.BytesIO(verified(dc10, DC10_SHA))) as account:
        dc = json.loads(account.read('DC10_ATTRIBUTION.json'))['segments']
    if len(sx) != 30 or len(dc) != 29:
        raise ValueError('account segment counts changed')
    groups = {}
    for name, segments in [('SX60_full', sx), ('DC10_development', dc)]:
        g = defaultdict(list)
        for segment in segments:
            first = datetime.fromisoformat(segment['start'].replace('Z', '+00:00'))
            ts = int(first.timestamp() * 1000)
            previous = [v for t, v in rates if ts - 24 * 3600000 <= t < ts]
            if len(previous) != 3:
                raise ValueError(f'incomplete previous 24h funding: {first}')
            state = 'positive' if sum(previous) > 0 else 'nonpositive'
            g[state].append((str(first.year), Decimal(segment['net_wallet_usdt'])))
        groups[name] = {
            state: {'segments': len(group), 'positive_net_segments': sum(net > 0 for _, net in group),
                    'realized_net_wallet_usdt': str(sum((net for _, net in group), Decimal(0))),
                    'by_entry_year': {year: {'segments': len(rows), 'realized_net_wallet_usdt': str(sum((n for _, n in rows), Decimal(0)))}
                                      for year in sorted({year for year, _ in group})
                                      if (rows := [(y, n) for y, n in group if y == year])}}
            for state, group in sorted(g.items())}
    return {'scope': 'Historical realized account-path stratification, no alternative filter/equity/counterfactual OI or funding strategy',
            'state': 'Sign of sum of the three strictly prior 8h funding settlements at first fill',
            'funding_monthly_zip_count': archive_count, 'funding_sha_inventory_hash': source_sha,
            'source_sha256': {'campaigns': CAMPAIGN_SHA, 'dc10_account': DC10_SHA},
            'accounts': groups}


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit('usage: realized_state_audit.py FULL_FUNDING_DIR CAMPAIGNS.json DC10_ACCOUNT.zip')
    print(json.dumps(audit(*sys.argv[1:]), ensure_ascii=False, indent=2))
