"""Resumable public V5 acquisition for native BTCUSD trade/mark/funding history.

Public-only research transport: no account credentials are read. Raw V5 pages
are preserved byte-for-byte with SHA-256 identities before deterministic
normalization. Formal acquisition defaults to 60-minute trade/mark candles in
30-day shards; the 4-hour production signal is rebuilt from four verified hourly
bars while each hourly high/low retains the exchange-reported intrahour extrema.
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

from coinquant.rest import NoRedirect, OFFICIAL_HOSTS

SYMBOL = "BTCUSD"
CATEGORY = "inverse"
MINUTE_MS = 60_000
HOUR_MS = 3_600_000
DAY_MS = 86_400_000
DEFAULT_INTERVAL_MINUTES = 60
DEFAULT_SHARD_DAYS = 30
SUPPORTED_INTERVAL_MINUTES = (1, 60)
INVENTORY_VERSION = 2


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


def _interval_ms(interval_minutes: int) -> int:
    if type(interval_minutes) is not int or interval_minutes not in SUPPORTED_INTERVAL_MINUTES:
        raise ValueError("historical interval must be exactly 1 or 60 minutes")
    return interval_minutes * MINUTE_MS


def _request_json(host: str, path: str, params: dict, raw_path: Path,
                  *, opener=None, timeout: float = 10.0) -> tuple[dict, dict]:
    host = _official_live_host(host)
    query = urlencode(sorted((key, str(value)) for key, value in params.items()))
    url = f"https://{host}{path}?{query}"
    request = Request(url, headers={"User-Agent": "coinquant-historical-research"})
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


def _parse_kline(result: dict, kind: str, start: int, end: int,
                 interval_ms: int) -> list[tuple]:
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
        if not start <= timestamp < end or timestamp % interval_ms:
            raise ValueError("Bybit kline timestamp is outside requested aligned range")
        values = (tuple(str(value) for value in row[1:6]) if kind == "trade"
                  else tuple(str(value) for value in row[1:5]))
        parsed.append((timestamp, *values))
    times = [row[0] for row in parsed]
    if times != sorted(times, reverse=True) or len(times) != len(set(times)):
        raise ValueError("Bybit kline page is not unique reverse chronological data")
    return parsed


def fetch_klines(host: str, kind: str, start: int, end: int, raw_dir: Path,
                 *, interval_minutes: int = 1, opener=None,
                 timeout: float = 10.0) -> tuple[dict[int, tuple], list[dict]]:
    step = _interval_ms(interval_minutes)
    if start >= end or start % step or end % step:
        raise ValueError("kline range must be positive and aligned to its interval")
    rows: dict[int, tuple] = {}
    receipts = []
    cursor_end = end - 1
    expected_count = (end - start) // step
    maximum_pages = (expected_count + 999) // 1000 + 2
    for page in range(maximum_pages):
        raw_path = raw_dir / f"{kind}-{page:03d}.json"
        result, receipt = _request_json(
            host, _kline_path(kind),
            dict(category=CATEGORY, symbol=SYMBOL, interval=str(interval_minutes),
                 start=start, end=cursor_end, limit=1000),
            raw_path, opener=opener, timeout=timeout,
        )
        parsed = _parse_kline(result, kind, start, end, step)
        receipts.append(receipt)
        if not parsed:
            raise ValueError(f"{kind} kline page is empty before range is complete")
        for row in parsed:
            previous = rows.get(row[0])
            if previous is not None and previous != row[1:]:
                raise ValueError(f"conflicting duplicate {kind} bar")
            rows[row[0]] = row[1:]
        oldest = parsed[-1][0]
        if oldest <= start:
            break
        if oldest > cursor_end:
            raise ValueError("Bybit kline pagination did not move backward")
        cursor_end = oldest - 1
    for timestamp in range(start, end, step):
        if timestamp not in rows:
            raise ValueError(f"missing native {kind} bar at {timestamp}")
    if len(rows) != expected_count:
        raise ValueError(f"unexpected extra native {kind} bar")
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
            raise ValueError("Bybit funding timestamp outside requested aligned shard")
        if previous is not None and timestamp >= previous:
            raise ValueError("Bybit funding rows are not reverse chronological")
        previous = timestamp
        if timestamp in values:
            raise ValueError("duplicate funding timestamp")
        values[timestamp] = rate
    return values, [receipt]


def merge_bars(trade: dict[int, tuple], mark: dict[int, tuple],
               funding: dict[int, str], start: int, end: int,
               *, interval_minutes: int = 1) -> tuple[list[tuple], list[tuple]]:
    step = _interval_ms(interval_minutes)
    bars = []
    for timestamp in range(start, end, step):
        if timestamp not in trade or timestamp not in mark:
            raise ValueError("trade/mark base-bar coverage differs")
        o, h, low, close, volume = trade[timestamp]
        mo, mh, ml, mc = mark[timestamp]
        bars.append((timestamp, o, h, low, close, volume, mo, mh, ml, mc))
    funding_rows = []
    for timestamp in sorted(funding):
        if timestamp not in mark:
            raise ValueError("funding timestamp lacks a native mark bar boundary")
        # Funding settles at the boundary: use that native bar's OPEN, never its
        # later close or any future observation from the bar.
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


def _receipt_ok(root: Path, receipt: dict) -> bool:
    try:
        path = (root / receipt["path"]).resolve()
        return (
            path.is_relative_to(root)
            and path.is_file()
            and path.stat().st_size == int(receipt["bytes"])
            and sha256(path) == receipt["sha256"]
        )
    except (KeyError, TypeError, ValueError, OSError):
        return False


def _checkpoint_complete(root: Path, record: dict | None) -> bool:
    if not record or record.get("status") != "complete":
        return False
    raw_pages = record.get("raw_pages")
    if not isinstance(raw_pages, list) or not raw_pages:
        return False
    return (
        all(_receipt_ok(root, receipt) for receipt in raw_pages)
        and _receipt_ok(root, record.get("bars", {}))
        and _receipt_ok(root, record.get("funding", {}))
    )


def _load_inventory(path: Path, host: str, start: date, end: date,
                    interval_minutes: int, shard_days: int) -> dict:
    identity = {
        "version": INVENTORY_VERSION,
        "api_host": host,
        "symbol": SYMBOL,
        "category": CATEGORY,
        "start": start.isoformat(),
        "end_exclusive": end.isoformat(),
        "interval_minutes": interval_minutes,
        "bar_interval_ms": _interval_ms(interval_minutes),
        "shard_days": shard_days,
    }
    if path.exists():
        value = json.loads(path.read_text(encoding="utf-8"))
        for key, expected in identity.items():
            if value.get(key) != expected:
                raise ValueError(f"existing V5 inventory {key} differs")
        if not isinstance(value.get("shards"), dict):
            raise ValueError("existing V5 inventory shard map is invalid")
        return value
    return dict(identity, shards={})


def acquire(root: Path, host: str, start: date, end: date, *,
            interval_minutes: int = DEFAULT_INTERVAL_MINUTES,
            shard_days: int = DEFAULT_SHARD_DAYS,
            opener=None, timeout: float = 10.0, pause: float = 0.0) -> dict:
    host = _official_live_host(host)
    step = _interval_ms(interval_minutes)
    if start >= end:
        raise ValueError("start must precede end")
    if type(shard_days) is not int or not 1 <= shard_days <= 60:
        raise ValueError("shard_days must be an integer in [1, 60]")
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    inventory_path = root / "v5-inventory.json"
    inventory = _load_inventory(
        inventory_path, host, start, end, interval_minutes, shard_days)
    failures = []
    current = start
    while current < end:
        shard_end = min(current + timedelta(days=shard_days), end)
        key = f"{current.isoformat()}_{shard_end.isoformat()}"
        prior = inventory["shards"].get(key)
        if _checkpoint_complete(root, prior):
            current = shard_end
            continue
        begin, finish = _day_ms(current), _day_ms(shard_end)
        raw_dir = root / "raw" / key
        record = {
            "status": "pending",
            "start": current.isoformat(),
            "end_exclusive": shard_end.isoformat(),
        }
        inventory["shards"][key] = record
        _atomic_json(inventory_path, inventory)
        try:
            trade, trade_receipts = fetch_klines(
                host, "trade", begin, finish, raw_dir,
                interval_minutes=interval_minutes, opener=opener, timeout=timeout)
            mark, mark_receipts = fetch_klines(
                host, "mark", begin, finish, raw_dir,
                interval_minutes=interval_minutes, opener=opener, timeout=timeout)
            funding, funding_receipts = fetch_funding(
                host, begin, finish, raw_dir, opener=opener, timeout=timeout)
            bars, funding_rows = merge_bars(
                trade, mark, funding, begin, finish,
                interval_minutes=interval_minutes)
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
            receipts = trade_receipts + mark_receipts + funding_receipts
            for receipt in receipts:
                raw_path = Path(receipt["path"]).resolve()
                if not raw_path.is_relative_to(root):
                    raise ValueError("raw receipt escaped acquisition root")
                receipt["path"] = raw_path.relative_to(root).as_posix()
            for receipt in (bars_receipt, funding_receipt):
                derived_path = Path(receipt["path"]).resolve()
                if not derived_path.is_relative_to(root):
                    raise ValueError("normalized receipt escaped acquisition root")
                receipt["path"] = derived_path.relative_to(root).as_posix()
            record.update(
                status="complete",
                raw_pages=receipts,
                bars=bars_receipt,
                funding=funding_receipt,
                funding_mark_convention=(
                    f"native mark {interval_minutes}m open at settlement timestamp"),
            )
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
            record.update(status="failed", error_type=type(exc).__name__, error=str(exc))
            failures.append(key)
        _atomic_json(inventory_path, inventory)
        if pause:
            time.sleep(pause)
        current = shard_end
    completed = sum(
        row.get("status") == "complete" for row in inventory["shards"].values())
    failed = sum(
        row.get("status") != "complete" for row in inventory["shards"].values())
    result = {
        "status": "complete" if not failures and failed == 0 else "incomplete",
        "complete_shards": completed,
        "failed_shards": failed,
        "bar_interval_ms": step,
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
    parser.add_argument("--interval-minutes", type=int, choices=SUPPORTED_INTERVAL_MINUTES,
                        default=DEFAULT_INTERVAL_MINUTES)
    parser.add_argument("--shard-days", type=int, default=DEFAULT_SHARD_DAYS)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--pause", type=float, default=0.0)
    args = parser.parse_args()
    try:
        result = acquire(
            Path(args.output), args.api_host, args.start, args.end,
            interval_minutes=args.interval_minutes, shard_days=args.shard_days,
            timeout=args.timeout, pause=args.pause)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "failed", "reason": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
