"""Resumable public V5 acquisition for native BTCUSD trade/mark/funding history.

This is a research transport, not the private execution transport. It never reads
API credentials. Every HTTP page is preserved verbatim with a SHA-256 identity,
then normalized into deterministic one-minute bars. A successful fetch is still
not formal economic qualification until dated trading/risk/fee rules are supplied.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timedelta, timezone
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener

from pancakequant.rest import NoRedirect, OFFICIAL_HOSTS

SYMBOL = "BTCUSD"
CATEGORY = "inverse"
MINUTE_MS = 60_000
DAY_MS = 86_400_000
INVENTORY_VERSION = 1


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _atomic_json(path: Path, value: dict) -> None:
    _atomic_bytes(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def _day_ms(day: date) -> int:
    return int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp() * 1000)


def _parse_day(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD") from exc


def _official_live_host(host: str) -> str:
    if host not in OFFICIAL_HOSTS["live"]:
        raise ValueError("api_host is not an approved Bybit live host")
    return host


def _request_json(host: str, path: str, params: dict, raw_path: Path,
                  *, opener=None, timeout: float = 10.0) -> tuple[dict, dict]:
    host = _official_live_host(host)
    query = urlencode(sorted((key, str(value)) for key, value in params.items()))
    url = f"https://{host}{path}?{query}"
    request = Request(url, headers={"User-Agent": "pancakequant-historical-research"})
    transport = opener or build_opener(NoRedirect())
    with transport.open(request, timeout=timeout) as response:
        payload = response.read(5_000_001)
    if not payload or len(payload) > 5_000_000:
        raise ValueError("empty or oversized Bybit V5 response")
    try:
        document = json.loads(payload)
    except ValueError as exc:
        raise ValueError("Bybit V5 response is not JSON") from exc
    if (not isinstance(document, dict) or document.get("retCode") != 0
            or not isinstance(document.get("result"), dict)):
        raise ValueError("Bybit V5 response is not successful")
    _atomic_bytes(raw_path, payload)
    metadata = {
        "path": raw_path.as_posix(),
        "bytes": len(payload),
        "sha256": _digest_bytes(payload),
        "source": url,
    }
    return document["result"], metadata


def _kline_path(kind: str) -> str:
    if kind == "trade":
        return "/v5/market/kline"
    if kind == "mark":
        return "/v5/market/mark-price-kline"
    raise ValueError("unsupported kline kind")


def _parse_kline(result: dict, kind: str, start: int, end: int) -> list[tuple]:
    if result.get("symbol") != SYMBOL or result.get("category") != CATEGORY:
        raise ValueError("wrong Bybit kline contract/category")
    rows = result.get("list")
    if not isinstance(rows, list):
        raise ValueError("Bybit kline list is missing")
    parsed = []
    for row in rows:
        minimum = 7 if kind == "trade" else 5
        if not isinstance(row, list) or len(row) < minimum:
            raise ValueError("Bybit kline row schema changed")
        try:
            timestamp = int(row[0])
        except (TypeError, ValueError) as exc:
            raise ValueError("Bybit kline timestamp is invalid") from exc
        if not start <= timestamp < end or timestamp % MINUTE_MS:
            raise ValueError("Bybit kline timestamp is outside requested aligned range")
        values = tuple(str(value) for value in row[1:6] if kind == "trade") if False else None
        if kind == "trade":
            values = tuple(str(value) for value in row[1:6])
        else:
            values = tuple(str(value) for value in row[1:5])
        parsed.append((timestamp, *values))
    times = [row[0] for row in parsed]
    if times != sorted(times, reverse=True) or len(times) != len(set(times)):
        raise ValueError("Bybit kline page is not unique reverse chronological data")
    return parsed


def fetch_klines(host: str, kind: str, start: int, end: int, raw_dir: Path,
                 *, opener=None, timeout: float = 10.0) -> tuple[dict[int, tuple], list[dict]]:
    if start >= end or start % MINUTE_MS or end % MINUTE_MS:
        raise ValueError("kline range must be positive and minute aligned")
    rows: dict[int, tuple] = {}
    receipts = []
    cursor_end = end - 1
    maximum_pages = (end - start + 999 * MINUTE_MS) // (1000 * MINUTE_MS) + 2
    for page in range(maximum_pages):
        raw_path = raw_dir / f"{kind}-{page:03d}.json"
        result, receipt = _request_json(
            host, _kline_path(kind),
            dict(category=CATEGORY, symbol=SYMBOL, interval="1",
                 start=start, end=cursor_end, limit=1000),
            raw_path, opener=opener, timeout=timeout,
        )
        parsed = _parse_kline(result, kind, start, end)
        receipts.append(receipt)
        if not parsed:
            raise ValueError(f"{kind} kline page is empty before range is complete")
        for row in parsed:
            previous = rows.get(row[0])
            if previous is not None and previous != row[1:]:
                raise ValueError(f"conflicting duplicate {kind} minute")
            rows[row[0]] = row[1:]
        oldest = parsed[-1][0]
        if oldest <= start:
            break
        if oldest > cursor_end:
            raise ValueError("Bybit kline pagination did not move backward")
        cursor_end = oldest - 1
    expected = range(start, end, MINUTE_MS)
    for timestamp in expected:
        if timestamp not in rows:
            raise ValueError(f"missing native {kind} minute at {timestamp}")
    if len(rows) != (end - start) // MINUTE_MS:
        raise ValueError(f"unexpected extra native {kind} minute")
    return rows, receipts


def fetch_funding(host: str, start: int, end: int, raw_dir: Path,
                  *, opener=None, timeout: float = 10.0) -> tuple[dict[int, str], list[dict]]:
    if start >= end:
        raise ValueError("funding range must be positive")
    result, receipt = _request_json(
        host, "/v5/market/funding/history",
        dict(category=CATEGORY, symbol=SYMBOL, startTime=start, endTime=end - 1, limit=200),
        raw_dir / "funding.json", opener=opener, timeout=timeout,
    )
    if result.get("category") != CATEGORY or not isinstance(result.get("list"), list):
        raise ValueError("wrong or missing Bybit funding result")
    if len(result["list"]) >= 200:
        raise ValueError("funding page reached limit; use a smaller acquisition shard")
    values = {}
    previous = None
    for row in result["list"]:
        if not isinstance(row, dict) or row.get("symbol") != SYMBOL:
            raise ValueError("wrong Bybit funding symbol")
        try:
            timestamp = int(row["fundingRateTimestamp"])
            rate = str(row["fundingRate"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Bybit funding row schema changed") from exc
        if not start <= timestamp < end or timestamp % MINUTE_MS:
            raise ValueError("Bybit funding timestamp outside requested minute-aligned shard")
        if previous is not None and timestamp >= previous:
            raise ValueError("Bybit funding rows are not reverse chronological")
        previous = timestamp
        if timestamp in values:
            raise ValueError("duplicate funding timestamp")
        values[timestamp] = rate
    return values, [receipt]


def merge_day(trade: dict[int, tuple], mark: dict[int, tuple],
              funding: dict[int, str], start: int, end: int) -> tuple[list[tuple], list[tuple]]:
    bars = []
    for timestamp in range(start, end, MINUTE_MS):
        if timestamp not in trade or timestamp not in mark:
            raise ValueError("trade/mark minute coverage differs")
        o, h, low, close, volume = trade[timestamp]
        mo, mh, ml, mc = mark[timestamp]
        bars.append((timestamp, o, h, low, close, volume, mo, mh, ml, mc))
    funding_rows = []
    for timestamp in sorted(funding):
        if timestamp not in mark:
            raise ValueError("funding timestamp lacks native mark minute")
        # Funding settles at the boundary; use the native mark candle OPEN at
        # that exact timestamp. Never use its future close.
        funding_rows.append((timestamp, funding[timestamp], mark[timestamp][0]))
    return bars, funding_rows


def _deterministic_gzip_csv(path: Path, header: list[str], rows: list[tuple]) -> dict:
    text = io.StringIO(newline="")
    writer = csv.writer(text, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    payload = gzip.compress(text.getvalue().encode("utf-8"), compresslevel=9, mtime=0)
    _atomic_bytes(path, payload)
    return {"path": path.as_posix(), "bytes": len(payload), "sha256": _digest_bytes(payload),
            "rows": len(rows)}


def _load_inventory(path: Path, host: str, start: date, end: date) -> dict:
    identity = {
        "version": INVENTORY_VERSION,
        "api_host": host,
        "symbol": SYMBOL,
        "category": CATEGORY,
        "start": start.isoformat(),
        "end_exclusive": end.isoformat(),
    }
    if path.exists():
        value = json.loads(path.read_text(encoding="utf-8"))
        for key, expected in identity.items():
            if value.get(key) != expected:
                raise ValueError(f"existing V5 inventory {key} differs")
        if not isinstance(value.get("days"), dict):
            raise ValueError("existing V5 inventory day map is invalid")
        return value
    return dict(identity, days={})


def acquire(root: Path, host: str, start: date, end: date, *,
            opener=None, timeout: float = 10.0, pause: float = 0.0) -> dict:
    host = _official_live_host(host)
    if start >= end:
        raise ValueError("start must precede end")
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    inventory_path = root / "v5-inventory.json"
    inventory = _load_inventory(inventory_path, host, start, end)
    failures = []
    current = start
    while current < end:
        key = current.isoformat()
        prior = inventory["days"].get(key)
        if prior and prior.get("status") == "complete":
            current += timedelta(days=1)
            continue
        begin = _day_ms(current)
        finish = begin + DAY_MS
        raw_dir = root / "raw" / key
        record = {"status": "pending"}
        inventory["days"][key] = record
        _atomic_json(inventory_path, inventory)
        try:
            trade, trade_receipts = fetch_klines(
                host, "trade", begin, finish, raw_dir, opener=opener, timeout=timeout)
            mark, mark_receipts = fetch_klines(
                host, "mark", begin, finish, raw_dir, opener=opener, timeout=timeout)
            funding, funding_receipts = fetch_funding(
                host, begin, finish, raw_dir, opener=opener, timeout=timeout)
            bars, funding_rows = merge_day(trade, mark, funding, begin, finish)
            bars_receipt = _deterministic_gzip_csv(
                root / "normalized" / "bars" / f"{key}.csv.gz",
                ["time", "open", "high", "low", "close", "volume",
                 "mark_open", "mark_high", "mark_low", "mark_close"],
                bars,
            )
            funding_receipt = _deterministic_gzip_csv(
                root / "normalized" / "funding" / f"{key}.csv.gz",
                ["time", "rate", "mark"], funding_rows,
            )
            record.update(
                status="complete",
                raw_pages=trade_receipts + mark_receipts + funding_receipts,
                bars=bars_receipt,
                funding=funding_receipt,
                funding_mark_convention="native mark 1m open at settlement timestamp",
            )
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
            record.update(status="failed", error_type=type(exc).__name__, error=str(exc))
            failures.append(key)
        _atomic_json(inventory_path, inventory)
        if pause:
            time.sleep(pause)
        current += timedelta(days=1)
    completed = sum(row.get("status") == "complete" for row in inventory["days"].values())
    failed = sum(row.get("status") != "complete" for row in inventory["days"].values())
    result = {
        "status": "complete" if not failures and failed == 0 else "incomplete",
        "complete_days": completed,
        "failed_days": failed,
        "inventory": str(inventory_path),
    }
    _atomic_json(root / "v5-result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Acquire native Bybit BTCUSD V5 trade/mark/funding history with raw receipts"
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--api-host", default="api.bybit.com")
    parser.add_argument("--start", type=_parse_day, default=date(2019, 12, 11))
    parser.add_argument("--end", type=_parse_day, default=date(2026, 9, 20),
                        help="exclusive UTC day")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--pause", type=float, default=0.0)
    args = parser.parse_args()
    try:
        result = acquire(Path(args.output), args.api_host, args.start, args.end,
                         timeout=args.timeout, pause=args.pause)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "failed", "reason": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
