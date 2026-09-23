"""Archive-only, read-only BTCUSDT OI acquisition for the frozen development dates.

This verifies current official bytes. It does not prove those revisions existed
at the historical decision times or qualify a strategy for economic replay.
"""
import csv
import hashlib
import io
import json
import sys
import tarfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from zipfile import ZipFile

BASE = 'https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/'
START, END = date(2020, 1, 1), date(2024, 1, 1)


def get(url):
    for attempt in range(3):
        try:
            with urlopen(url, timeout=30) as response:
                return response.read(), response.headers.get('Last-Modified')
        except HTTPError as exc:
            if exc.code == 404:
                return None, None
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (TimeoutError, URLError):
            if attempt == 2:
                raise
        time.sleep(attempt + 1)


def acquire(day):
    name = f'BTCUSDT-metrics-{day}.zip'
    url = BASE + name
    checksum, _ = get(url + '.CHECKSUM')
    record = dict(day=str(day), url=url)
    if checksum is None:
        record['status'] = 'missing_checksum_404'
        return record, None, None
    raw, last_modified = get(url)
    if raw is None:
        record['status'] = 'missing_zip_404'
        return record, None, checksum
    tokens = checksum.decode('ascii').strip().split()
    if len(tokens) != 2 or tokens[1] != name or hashlib.sha256(raw).hexdigest() != tokens[0]:
        raise ValueError(f'provider checksum mismatch: {day}')
    with ZipFile(io.BytesIO(raw)) as archive:
        members = archive.namelist()
        if len(members) != 1 or archive.testzip() is not None:
            raise ValueError(f'bad ZIP: {day}')
        rows = list(csv.DictReader(io.StringIO(archive.read(members[0]).decode('utf-8-sig'))))
    required = {'create_time', 'symbol', 'sum_open_interest', 'sum_open_interest_value'}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f'unexpected OI columns: {day}')
    unique = {}
    conflicts = 0
    invalid = 0
    for row in rows:
        label = datetime.fromisoformat(row['create_time'])
        if row['symbol'] != 'BTCUSDT' or Decimal(row['sum_open_interest']) <= 0:
            invalid += 1
        if label in unique and unique[label] != row:
            conflicts += 1
        unique[label] = row
    expected = {datetime.combine(day, datetime.min.time()) + timedelta(minutes=5*i)
                for i in range(288)}
    missing = sorted(expected - unique.keys())
    extra = sorted(unique.keys() - expected)
    record.update(status='quarantined_conflict' if conflicts or invalid else
                  'verified_complete' if not missing and not extra else 'verified_incomplete',
                  zip_sha256=tokens[0], zip_bytes=len(raw), last_modified=last_modified,
                  raw_rows=len(rows), unique_labels=len(unique),
                  exact_duplicates=len(rows)-len(unique)-conflicts,
                  conflicting_duplicates=conflicts, invalid_rows=invalid,
                  missing_labels=len(missing), extra_labels=len(extra),
                  first_missing=missing[0].isoformat() if missing else None,
                  first_extra=extra[0].isoformat() if extra else None)
    return record, raw, checksum


def run(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    days = [START + timedelta(days=i) for i in range((END - START).days)]
    original_dir = destination / 'raw'
    original_dir.mkdir(exist_ok=True)
    records = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for record, raw, checksum in pool.map(acquire, days):
            records.append(record)
            if raw is not None:
                name = f'BTCUSDT-metrics-{record["day"]}.zip'
                (original_dir / name).write_bytes(raw)
                (original_dir / (name + '.CHECKSUM')).write_bytes(checksum)
    manifest = dict(start=str(START), end_exclusive=str(END), source=BASE,
                    availability='current archive bytes only; historical publication unverified',
                    days=records)
    (destination / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    with tarfile.open(destination / 'OI_DEVELOPMENT_ORIGINALS.tar.gz', 'w:gz') as archive:
        archive.add(original_dir, arcname='raw')
        archive.add(destination / 'MANIFEST.json', arcname='MANIFEST.json')
    from collections import Counter
    print(json.dumps(dict(days=len(records), status=dict(Counter(x['status'] for x in records)),
                          first_valid=next((x['day'] for x in records
                                            if x['status'] == 'verified_complete'), None),
                          manifest_sha256=hashlib.sha256((destination / 'MANIFEST.json').read_bytes()).hexdigest(),
                          archive_sha256=hashlib.sha256((destination / 'OI_DEVELOPMENT_ORIGINALS.tar.gz').read_bytes()).hexdigest(),
                          archive_bytes=(destination / 'OI_DEVELOPMENT_ORIGINALS.tar.gz').stat().st_size)))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: oi_archive_acquire.py OUTPUT_DIR')
    run(sys.argv[1])
