"""Fetch only the official days listed by an executable-opportunity request file."""
import argparse
import calendar
import csv
import hashlib
import io
import json
from datetime import date, datetime, timezone
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.request import urlopen
from zipfile import ZipFile

BASE = 'https://data.binance.vision/data/futures/um/'
KINDS = ('klines', 'markPriceKlines')


def fetch(relative):
    with urlopen(BASE + relative, timeout=45) as response:
        return response.read()


def check_zip(raw, kind, period):
    with ZipFile(io.BytesIO(raw)) as archive:
        if archive.testzip() is not None:
            raise ValueError('ZIP CRC mismatch')
        files = [name for name in archive.namelist() if name.endswith('.csv')]
        if len(files) != 1:
            raise ValueError('expected one CSV in official ZIP')
        rows = csv.reader(io.TextIOWrapper(archive.open(files[0]), encoding='utf-8'))
        previous = None
        count = 0
        for row in rows:
            if row[0].lower().startswith('open_time'):
                continue
            t = int(row[0]); count += 1
            if previous is not None and t != previous + 60_000:
                raise ValueError('duplicate or missing minute')
            previous = t
            if len(row) < (8 if kind == 'klines' else 5):
                raise ValueError('incomplete minute row')
            for value in row[1:5]:
                float(value)
            if count == 1:
                first = t
        if not count:
            raise ValueError('empty minute archive')
        year, month, *day = map(int, period.split('-'))
        expected = (date(year, month, day[0]) if day else date(year, month, 1))
        start = int(datetime(expected.year, expected.month, expected.day, tzinfo=timezone.utc).timestamp() * 1000)
        minutes = 1440 if day else calendar.monthrange(year, month)[1] * 1440
        if first != start or count != minutes:
            raise ValueError(f'incomplete UTC archive: {first}, {count} of {minutes}')
        return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('requests', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    days = [item['day'] for item in json.loads(args.requests.read_text())['requests']]
    if len(set(days)) != len(days) or len(days) > 90 or any(not re.fullmatch(r'20\d\d-\d\d-\d\d', d) for d in days):
        raise ValueError('invalid or duplicate frozen dates')
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'REQUEST.json').write_bytes(args.requests.read_bytes())
    receipts = []
    for day in days:
        for kind in KINDS:
            attempts = [f'daily/{kind}/BTCUSDT/1m/BTCUSDT-1m-{day}.zip',
                        f'monthly/{kind}/BTCUSDT/1m/BTCUSDT-1m-{day[:7]}.zip']
            for path in attempts:
                target = args.output/'data/futures/um'/path
                try:
                    if target.exists() and Path(str(target)+'.CHECKSUM').exists():
                        raw = target.read_bytes(); checksum = Path(str(target)+'.CHECKSUM').read_bytes()
                    else:
                        raw = fetch(path); checksum = fetch(path+'.CHECKSUM')
                    sha = hashlib.sha256(raw).hexdigest()
                    if sha.lower() != checksum.decode().split()[0].lower():
                        raise ValueError('official SHA-256 mismatch')
                    count = check_zip(raw, kind, day if path.startswith('daily/') else day[:7])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(raw); Path(str(target)+'.CHECKSUM').write_bytes(checksum)
                    receipts.append(dict(day=day, kind=kind, path=path, status='verified', bytes=len(raw),
                                         sha256=sha, minutes=count, retrieved_at=datetime.now(timezone.utc).isoformat()))
                    break
                except HTTPError as exc:
                    if exc.code != 404 or path.startswith('monthly/'):
                        receipts.append(dict(day=day, kind=kind, path=path, status=f'HTTP {exc.code}'))
                        break
                except Exception as exc:
                    receipts.append(dict(day=day, kind=kind, path=path, status='failed', error=str(exc)))
                    break
            else:
                receipts.append(dict(day=day, kind=kind, status='daily and monthly unavailable'))
            (args.output/'RECEIPT.json').write_text(json.dumps(receipts, indent=2)+'\n')
            print(day, kind, receipts[-1]['status'], flush=True)
    if sum(x['status'] == 'verified' for x in receipts) < 2*len(days):
        raise SystemExit('some official archives remain unavailable; see RECEIPT.json')


if __name__ == '__main__':
    main()
