"""Resumable acquisition of Bybit's public BTCUSD archive originals.

This downloader preserves source bytes; it does not normalize, synthesize mark
prices, infer funding, or create a formal replay manifest. Each completed file is
hashed and checkpointed atomically so a multi-year acquisition can resume safely.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://public.bybit.com"
SYMBOL = "BTCUSD"
KINDS = {
    "trades": (
        "trading/BTCUSD",
        "{symbol}{day}.csv.gz",
    ),
    "index": (
        "spot_index/BTCUSD",
        "{symbol}{day}_index_price.csv.gz",
    ),
    "premium": (
        "premium_index/BTCUSD",
        "{symbol}{day}_premium_index.csv.gz",
    ),
}
INVENTORY_VERSION = 1


def parse_day(text: str) -> date:
    try:
        value = date.fromisoformat(text)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD") from exc
    return value


def iso_day(value: date) -> str:
    return value.isoformat()


def days(start: date, end: date):
    current = start
    while current < end:
        yield current
        current += timedelta(days=1)


def source(kind: str, day: date) -> tuple[str, str]:
    directory, template = KINDS[kind]
    name = template.format(symbol=SYMBOL, day=iso_day(day))
    return f"{BASE}/{directory}/{name}", name


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_gzip(path: Path) -> None:
    """Read through gzip framing to verify CRC/truncation without retaining data."""
    count = 0
    with gzip.open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            count += len(block)
    if count == 0:
        raise ValueError("empty gzip payload")


def load_inventory(path: Path, start: date, end: date, kinds: tuple[str, ...]) -> dict:
    if path.exists():
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RuntimeError("inventory is unreadable; refusing to overwrite recovery state") from exc
        expected = {
            "version": INVENTORY_VERSION,
            "symbol": SYMBOL,
            "start": iso_day(start),
            "end_exclusive": iso_day(end),
            "kinds": list(kinds),
        }
        for key, item in expected.items():
            if value.get(key) != item:
                raise RuntimeError(f"inventory {key} differs from this acquisition")
        if not isinstance(value.get("files"), dict):
            raise RuntimeError("inventory file map is invalid")
        return value
    return {
        "version": INVENTORY_VERSION,
        "symbol": SYMBOL,
        "start": iso_day(start),
        "end_exclusive": iso_day(end),
        "kinds": list(kinds),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "files": {},
    }


def checkpoint(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def completed(record: dict | None, path: Path) -> bool:
    if not record or record.get("status") != "downloaded" or not path.is_file():
        return False
    if path.stat().st_size != record.get("bytes"):
        return False
    return sha256(path) == record.get("sha256")


def _open(url: str, offset: int, timeout: float):
    headers = {
        "User-Agent": "pancakequant-historical-research",
        "Accept-Encoding": "identity",
    }
    if offset:
        headers["Range"] = f"bytes={offset}-"
    request = Request(url, headers=headers)
    return urlopen(request, timeout=timeout)


def download(url: str, destination: Path, *, timeout: float, max_bytes: int) -> tuple[int, str]:
    """Resume a partial file when the origin honors Range; otherwise restart."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".partial")
    offset = partial.stat().st_size if partial.exists() else 0
    try:
        response = _open(url, offset, timeout)
    except HTTPError as exc:
        if not offset or exc.code != 416:
            raise
        # A partial may already equal the remote length but has not passed our
        # gzip/hash completion checks. Never promote it from HTTP 416 alone:
        # restart from zero and verify the complete original deterministically.
        partial.unlink(missing_ok=True)
        offset = 0
        response = _open(url, 0, timeout)
    status = getattr(response, "status", None) or response.getcode()
    if offset and status != 206:
        response.close()
        partial.unlink(missing_ok=True)
        offset = 0
        response = _open(url, 0, timeout)
        status = getattr(response, "status", None) or response.getcode()
    if status not in (200, 206):
        response.close()
        raise RuntimeError(f"unexpected HTTP status {status}")
    mode = "ab" if offset else "wb"
    written = offset
    try:
        with response, partial.open(mode) as stream:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                written += len(block)
                if written > max_bytes:
                    raise RuntimeError("source file exceeds configured safety bound")
                stream.write(block)
            stream.flush()
            os.fsync(stream.fileno())
        if written == 0:
            raise RuntimeError("empty HTTP response")
        validate_gzip(partial)
        digest = sha256(partial)
        os.replace(partial, destination)
        return written, digest
    except Exception:
        # Keep a partial response for deterministic resumption, except a corrupt
        # completed gzip: future invocation will resume/restart from that byte count.
        raise


def acquire(root: Path, start: date, end: date, kinds: tuple[str, ...],
            *, timeout: float = 30.0, max_bytes: int = 1_000_000_000) -> dict:
    if start >= end:
        raise ValueError("start must precede end")
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    inventory_path = root / "archive-inventory.json"
    inventory = load_inventory(inventory_path, start, end, kinds)
    failures = []
    for day in days(start, end):
        for kind in kinds:
            url, name = source(kind, day)
            relative = Path("raw") / kind / name
            target = root / relative
            key = f"{kind}:{iso_day(day)}"
            prior = inventory["files"].get(key)
            if completed(prior, target):
                continue
            record = {
                "kind": kind,
                "day": iso_day(day),
                "path": relative.as_posix(),
                "source": url,
                "status": "pending",
            }
            inventory["files"][key] = record
            checkpoint(inventory_path, inventory)
            try:
                size, digest = download(url, target, timeout=timeout, max_bytes=max_bytes)
            except (HTTPError, URLError, OSError, ValueError, RuntimeError) as exc:
                record.update(
                    status="unavailable",
                    error_type=type(exc).__name__,
                    http_status=getattr(exc, "code", None),
                    error=str(exc),
                )
                failures.append(key)
            else:
                record.update(status="downloaded", bytes=size, sha256=digest)
                record.pop("error_type", None)
                record.pop("http_status", None)
                record.pop("error", None)
            checkpoint(inventory_path, inventory)
    downloaded = sum(r.get("status") == "downloaded" for r in inventory["files"].values())
    unavailable = sum(r.get("status") != "downloaded" for r in inventory["files"].values())
    summary = {
        "status": "complete" if not failures and unavailable == 0 else "incomplete",
        "downloaded": downloaded,
        "unavailable": unavailable,
        "inventory": str(inventory_path),
    }
    checkpoint(root / "acquisition-result.json", summary)
    return summary


def default_window() -> tuple[date, date]:
    # 21 pre-start days safely exceed the default 120 x 4h trend warmup.
    return date(2019, 12, 11), date(2026, 9, 20)


def main() -> int:
    default_start, default_end = default_window()
    parser = argparse.ArgumentParser(
        description="Resume verified Bybit BTCUSD public archive downloads without normalization"
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--start", type=parse_day, default=default_start)
    parser.add_argument("--end", type=parse_day, default=default_end,
                        help="exclusive UTC date, default frozen research endpoint")
    parser.add_argument("--kinds", nargs="+", choices=tuple(KINDS), default=tuple(KINDS))
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--max-bytes-per-file", type=int, default=1_000_000_000)
    args = parser.parse_args()
    try:
        result = acquire(
            Path(args.output), args.start, args.end, tuple(args.kinds),
            timeout=args.timeout, max_bytes=args.max_bytes_per_file,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"status": "failed", "reason": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
