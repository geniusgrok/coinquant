"""Isolated read-only acquisition of official BTCUSDT USDT-perpetual minute archives."""

import argparse
import csv
import hashlib
import json
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from io import TextIOWrapper
from pathlib import Path

BASE = "https://data.binance.vision/data/futures/um/"


def fetch(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=90) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 404) or attempt == 2:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(1 + attempt)


def acquire(root, kind, day):
    for period, stamp in (("daily", day), ("monthly", day[:7])):
        relative = f"{period}/{kind}/BTCUSDT/1m/BTCUSDT-1m-{stamp}.zip"
        try:
            checksum = fetch(BASE + relative + ".CHECKSUM")
            archive = fetch(BASE + relative)
        except urllib.error.HTTPError as exc:
            if exc.code == 404 and period == "daily":
                continue
            raise
        digest = hashlib.sha256(archive).hexdigest()
        if checksum.decode("utf-8").split()[0].lower() != digest:
            raise ValueError(f"official checksum mismatch: {relative}")
        dest = root / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(archive)
        Path(str(dest) + ".CHECKSUM").write_bytes(checksum)
        lo = int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp() * 1000)
        with zipfile.ZipFile(dest) as z:
            if z.testzip() is not None or len(z.namelist()) != 1:
                raise ValueError(f"ZIP CRC/member failure: {relative}")
            with z.open(z.namelist()[0]) as handle:
                times = [int(row[0]) for row in csv.reader(TextIOWrapper(handle, encoding="utf-8-sig"))
                         if row and row[0].isdigit() and lo <= int(row[0]) < lo + 86400000]
        if times != list(range(lo, lo + 86400000, 60000)):
            raise ValueError(f"minute continuity failure: {relative}, day={day}, rows={len(times)}")
        return dict(kind=kind, day=day, path=relative, bytes=len(archive), sha256=digest,
                    day_rows=len(times), source=BASE + relative)
    raise FileNotFoundError(f"no official daily or monthly archive: {kind} {day}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    request = json.loads(args.request.read_text())
    days = [day for day in request["dates"] if day.startswith(args.year + "-")]
    tasks = [(kind, day) for day in days for kind in ("klines", "markPriceKlines")]
    args.output.mkdir(parents=True, exist_ok=False)

    def one(task):
        kind, day = task
        try:
            return acquire(args.output, kind, day)
        except Exception as exc:
            return dict(kind=kind, day=day, failed=True, error=repr(exc))

    with ThreadPoolExecutor(max_workers=8) as pool:
        records = list(pool.map(one, tasks))
    receipt = dict(request_sha256=hashlib.sha256(args.request.read_bytes()).hexdigest(),
                   year=args.year, requested_days=days, records=records,
                   complete=all(not r.get("failed") for r in records))
    (args.output / "RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(dict(year=args.year, days=len(days), complete=receipt["complete"],
                          failed=[r for r in records if r.get("failed")])), flush=True)
    if not receipt["complete"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
