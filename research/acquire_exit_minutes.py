"""Read-only acquisition of the fixed planned-exit minutes; no account replay."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import time
import urllib.request
import zipfile

from coinquant.research import iso

BASE = 'https://data.binance.vision/data/futures/um/'


def acquire(output, request):
    hours = json.loads(request.read_text())['exit_hours_ms']
    days = sorted({iso(t)[:10] for t in hours})
    output.mkdir(parents=True, exist_ok=False)

    def fetch(relative):
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(3):
            try:
                with urllib.request.urlopen(BASE + relative, timeout=25) as response:
                    raw = response.read()
                path.write_bytes(raw)
                return raw
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(attempt + 1)

    def one(item):
        kind, day = item
        errors = []
        for frequency, stamp in (('daily', day), ('monthly', day[:7])):
            relative = f'{frequency}/{kind}/BTCUSDT/1m/BTCUSDT-1m-{stamp}.zip'
            try:
                raw = fetch(relative)
                checksum = fetch(relative + '.CHECKSUM')
                sha = hashlib.sha256(raw).hexdigest()
                if checksum.decode().split()[0] != sha:
                    raise ValueError('exchange checksum mismatch')
                with zipfile.ZipFile(output / relative) as archive:
                    if archive.testzip() is not None:
                        raise ValueError('archive CRC mismatch')
                return dict(day=day, kind=kind, path=relative, bytes=len(raw),
                            sha256=sha, source=BASE+relative, prior_errors=errors)
            except Exception as exc:
                errors.append(dict(source=BASE+relative, error=repr(exc)))
        return dict(day=day, kind=kind, failed=True, errors=errors)

    # Avoid concurrent writes to a shared monthly fallback archive.
    records = []
    for kind in ('klines', 'markPriceKlines'):
        with ThreadPoolExecutor(max_workers=1) as pool:
            records.extend(pool.map(one, [(kind, day) for day in days]))
    receipt = dict(request=json.loads(request.read_text()), records=records,
                   complete=all(not r.get('failed') for r in records))
    (output/'RECEIPT.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(dict(days=len(days), complete=receipt['complete'])))
    if not receipt['complete']:
        raise SystemExit('incomplete originals; retain failures, do not synthesize prices')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--request', type=Path, default=Path('evidence/sustainable-capital-exit-20260922/EXIT_MINUTE_REQUEST.json'))
    args = parser.parse_args()
    acquire(args.output, args.request)
