"""Deterministically derive complete one-minute trade OHLCV shards from Bybit BTCUSD originals.

The input remains the hashed public archive inventory produced by acquire.py.
This script never creates mark prices, funding, or a formal qualified dataset.
A day with a missing trade minute is rejected instead of being forward-filled.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys

SYMBOL = "BTCUSD"
MINUTE_MS = 60_000
DAY_MS = 86_400_000
OUTPUT_VERSION = 1
REQUIRED_COLUMNS = {
    "timestamp", "symbol", "side", "size", "price",
    "tickDirection", "trdMatchID", "grossValue", "homeNotional", "foreignNotional",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def midnight_ms(day: date) -> int:
    return int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp() * 1000)


def checkpoint(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _number(text: str, name: str) -> Decimal:
    try:
        value = Decimal(text)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"invalid {name}") from exc
    if not value.is_finite():
        raise ValueError(f"invalid {name}")
    return value


def _trade_ms(text: str) -> int:
    value = _number(text, "timestamp")
    if value < 0:
        raise ValueError("negative timestamp")
    return int((value * 1000).to_integral_value(rounding=ROUND_FLOOR))


def _complete(record: dict | None, path: Path) -> bool:
    return bool(
        record
        and record.get("status") == "built"
        and path.is_file()
        and path.stat().st_size == record.get("bytes")
        and sha256(path) == record.get("sha256")
    )


def _source_record(archive: dict, day: date) -> dict:
    key = f"trades:{day.isoformat()}"
    record = archive.get("files", {}).get(key)
    if not record or record.get("status") != "downloaded":
        raise ValueError(f"verified trade original is missing for {day.isoformat()}")
    return record


def _verify_original(archive_root: Path, record: dict) -> Path:
    path = (archive_root / record["path"]).resolve()
    if not path.is_relative_to(archive_root.resolve()) or not path.is_file():
        raise ValueError("trade original path is invalid")
    if path.stat().st_size != record.get("bytes") or sha256(path) != record.get("sha256"):
        raise ValueError("trade original length/hash mismatch")
    return path


def aggregate_day(original: Path, day: date) -> list[tuple]:
    """Read one reverse-chronological Bybit trade file and return ascending 1m bars."""
    begin = midnight_ms(day)
    end = begin + DAY_MS
    bars: dict[int, list[Decimal]] = {}
    previous_trade_ms: int | None = None
    with gzip.open(original, "rt", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            raise ValueError("unexpected Bybit trade CSV schema")
        seen = 0
        for row in reader:
            trade_ms = _trade_ms(row["timestamp"])
            if not begin <= trade_ms < end:
                raise ValueError("trade timestamp falls outside source UTC day")
            if previous_trade_ms is not None and trade_ms > previous_trade_ms:
                raise ValueError("Bybit trade archive is not reverse chronological")
            previous_trade_ms = trade_ms
            if row["symbol"] != SYMBOL or row["side"] not in ("Buy", "Sell"):
                raise ValueError("unexpected symbol or side")
            price = _number(row["price"], "price")
            size = _number(row["size"], "size")
            if price <= 0 or size <= 0:
                raise ValueError("non-positive trade price or size")
            minute = trade_ms // MINUTE_MS * MINUTE_MS
            current = bars.get(minute)
            # Reverse input: first price seen is chronological close; each later
            # row is earlier, so update open while preserving that close.
            if current is None:
                bars[minute] = [price, price, price, price, size]
            else:
                current[0] = price
                current[1] = max(current[1], price)
                current[2] = min(current[2], price)
                current[4] += size
            seen += 1
    if not seen:
        raise ValueError("empty trade original")
    expected = list(range(begin, end, MINUTE_MS))
    missing = [minute for minute in expected if minute not in bars]
    if missing:
        raise ValueError(
            f"native trade archive has {len(missing)} missing minute(s); "
            f"first={missing[0]}"
        )
    return [
        (minute, *(str(value) for value in bars[minute]))
        for minute in expected
    ]


def write_day(path: Path, rows: list[tuple]) -> tuple[int, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wt", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["time", "open", "high", "low", "close", "volume"])
        writer.writerows(rows)
    os.replace(temporary, path)
    return path.stat().st_size, sha256(path)


def build(archive_root: Path, output_root: Path) -> dict:
    archive_root = archive_root.resolve()
    output_root = output_root.resolve()
    try:
        archive = json.loads((archive_root / "archive-inventory.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("archive inventory is missing or invalid") from exc
    if archive.get("symbol") != SYMBOL or "trades" not in archive.get("kinds", []):
        raise ValueError("archive inventory is not BTCUSD trade data")
    start = date.fromisoformat(archive["start"])
    end = date.fromisoformat(archive["end_exclusive"])
    inventory_path = output_root / "trade-bars-inventory.json"
    if inventory_path.exists():
        result = json.loads(inventory_path.read_text(encoding="utf-8"))
        identity = (result.get("version"), result.get("symbol"), result.get("start"), result.get("end_exclusive"))
        if identity != (OUTPUT_VERSION, SYMBOL, start.isoformat(), end.isoformat()):
            raise ValueError("existing trade-bar inventory belongs to a different source window")
    else:
        result = {
            "version": OUTPUT_VERSION,
            "symbol": SYMBOL,
            "start": start.isoformat(),
            "end_exclusive": end.isoformat(),
            "source_inventory_sha256": sha256(archive_root / "archive-inventory.json"),
            "provenance": "derived_from_native_trades",
            "files": {},
        }
    current = start
    failures = []
    while current < end:
        key = current.isoformat()
        relative = Path("daily") / f"BTCUSD{key}.trade-1m.csv.gz"
        target = output_root / relative
        prior = result["files"].get(key)
        if _complete(prior, target):
            current += timedelta(days=1)
            continue
        try:
            source_record = _source_record(archive, current)
            original = _verify_original(archive_root, source_record)
            rows = aggregate_day(original, current)
            size, digest = write_day(target, rows)
            result["files"][key] = {
                "status": "built",
                "path": relative.as_posix(),
                "bytes": size,
                "sha256": digest,
                "rows": len(rows),
                "first_time": rows[0][0],
                "last_time": rows[-1][0],
                "source_path": source_record["path"],
                "source_bytes": source_record["bytes"],
                "source_sha256": source_record["sha256"],
                "source": source_record["source"],
            }
        except (OSError, ValueError, KeyError) as exc:
            result["files"][key] = {
                "status": "failed",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            failures.append(key)
        checkpoint(inventory_path, result)
        current += timedelta(days=1)
    built = sum(row.get("status") == "built" for row in result["files"].values())
    failed = sum(row.get("status") != "built" for row in result["files"].values())
    summary = {
        "status": "complete" if not failures and failed == 0 else "incomplete",
        "built_days": built,
        "failed_days": failed,
        "inventory": str(inventory_path),
    }
    checkpoint(output_root / "trade-bars-result.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Build strict one-minute BTCUSD trade OHLCV shards")
    parser.add_argument("--archive", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        result = build(Path(args.archive), Path(args.output))
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "failed", "reason": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
