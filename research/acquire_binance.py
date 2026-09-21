"""Bounded public BTCUSDT archive acquisition; no credentials or trading writes.

Preserves ZIPs and exchange CHECKSUMs. Native data is not native qualification:
dated costs/rules, USDT collateral risk and execution safety remain separate gates.
"""
import argparse
import concurrent.futures
import csv
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import zipfile

BASE = "https://data.binance.vision/data/futures/um/"


def paths():
    for year in range(2019, 2027):
        for month in range(1, 13):
            if (year, month) < (2019, 12) or (year, month) > (2026, 8):
                continue
            date = f"{year}-{month:02}"
            for kind in ("klines", "markPriceKlines"):
                yield f"monthly/{kind}/BTCUSDT/1h/BTCUSDT-1h-{date}.zip"
            yield f"monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-{date}.zip"
    for day in range(1, 20):
        for kind in ("klines", "markPriceKlines"):
            yield f"daily/{kind}/BTCUSDT/1h/BTCUSDT-1h-2026-09-{day:02}.zip"


def download(url):
    with urllib.request.urlopen(url, timeout=25) as response:
        if response.url != url:
            raise ValueError("unexpected public archive redirect")
        return response.read()


def acquire(root, path):
    record = {"path": path, "source": BASE + path}
    try:
        target = root / path
        checksum = Path(str(target) + ".CHECKSUM")
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = target.read_bytes() if target.exists() else download(BASE + path)
        expected = checksum.read_bytes() if checksum.exists() else download(BASE + path + ".CHECKSUM")
        digest = hashlib.sha256(raw).hexdigest()
        if expected.decode().split()[0] != digest:
            raise ValueError("exchange checksum mismatch")
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            if len(archive.namelist()) != 1 or archive.testzip() is not None:
                raise ValueError("archive structure/CRC")
            rows = list(csv.reader(io.StringIO(archive.read(archive.namelist()[0]).decode())))
        if rows and not rows[0][0].isdigit():
            rows = rows[1:]  # documented CSV header, not market data
        times = [int(row[0]) for row in rows]
        if not times or times != sorted(set(times)):
            raise ValueError("empty, duplicate or unordered timestamps")
        if "/fundingRate/" not in path:
            if any(b - a != 3600000 for a, b in zip(times, times[1:])):
                raise ValueError("hour gap")
            from decimal import Decimal
            for row in rows:
                o, h, low, close = map(Decimal, row[1:5])
                if not (0 < low <= min(o, close) <= max(o, close) <= h):
                    raise ValueError("invalid OHLC")
                if int(row[6]) != int(row[0]) + 3599999:
                    raise ValueError("invalid close timestamp")
        target.write_bytes(raw)
        checksum.write_bytes(expected)
        record.update(status="verified", sha256=digest, bytes=len(raw), rows=len(rows),
                      first_ts=times[0], last_ts=times[-1])
    except Exception as error:
        record.update(status="unavailable", error=f"{type(error).__name__}: {error}")
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for record in pool.map(lambda path: acquire(args.output, path), paths()):
            records.append(record)
            (args.output / "inventory.json").write_text(json.dumps({
                "qualification": "NOT_QUALIFIED", "records": records,
                "funding_tail": "separate official September API response required",
            }, indent=2) + "\n")
            if len(records) % 30 == 0 or record["status"] != "verified":
                print(len(records), record["path"], record["status"], flush=True)
    failures = sum(r["status"] != "verified" for r in records)
    print(json.dumps({"archives": len(records), "failures": failures}))
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
