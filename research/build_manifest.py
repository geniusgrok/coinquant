"""Assemble a strict replay manifest from verified native V5 history.

This step never fabricates historical exchange rules. A rules CSV and explicit
provenance/source are mandatory. Native bars/funding plus proxy rules produce a
proxy manifest, never a native one.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date
import json
from pathlib import Path
import sys

from pancakequant.research import spec
from research.acquire_v5 import _checkpoint_complete, sha256

MINUTE_MS = 60_000
HOUR_MS = 3_600_000
EXPECTED_RULE_COLUMNS = [
    "time", "launch_ms", "funding_interval_ms", "tick", "step", "minimum",
    "maximum", "market_maximum", "risk_limit_btc", "maintenance_rate",
    "taker_fee", "liquidation_fee",
]


def _relative(root: Path, path: Path) -> str:
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("manifest input must remain inside the dataset root")
    return resolved.relative_to(root).as_posix()


def _receipt_entry(root: Path, receipt: dict, source: str, **extra) -> dict:
    path = (root / receipt["path"]).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("verified normalized file is missing")
    size = path.stat().st_size
    digest = sha256(path)
    if size != receipt.get("bytes") or digest != receipt.get("sha256"):
        raise ValueError("normalized file no longer matches its V5 receipt")
    return dict(path=_relative(root, path), bytes=size, sha256=digest, source=source, **extra)


def _read_rules(root: Path, path: Path, source: str, provenance: str) -> dict:
    if provenance not in ("native", "proxy"):
        raise ValueError("rules provenance must be native or proxy")
    if not source.strip():
        raise ValueError("rules source is required")
    relative = _relative(root, path)
    if not path.is_file():
        raise ValueError("rules file is missing")
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError("rules file is empty") from exc
        if header != EXPECTED_RULE_COLUMNS:
            raise ValueError("rules CSV columns differ from the replay contract")
        rows = sum(1 for row in reader if any(cell.strip() for cell in row))
    if rows == 0:
        raise ValueError("rules file has no effective rows")
    return {
        "path": relative,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "source": source,
        "provenance": provenance,
        "rows": rows,
    }


def _load_v5(root: Path) -> dict:
    path = root / "v5-inventory.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("V5 inventory is missing or invalid") from exc
    if (value.get("version") != 2 or value.get("symbol") != "BTCUSD"
            or value.get("category") != "inverse"):
        raise ValueError("V5 inventory is not the supported BTCUSD inverse format")
    if value.get("bar_interval_ms") not in (MINUTE_MS, HOUR_MS):
        raise ValueError("V5 inventory has an unsupported replay interval")
    if not isinstance(value.get("shards"), dict):
        raise ValueError("V5 inventory shard map is invalid")
    return value


def build(root: Path, rules: Path, rules_source: str, rules_provenance: str,
          *, mandate: dict | None = None) -> dict:
    root = root.resolve()
    rules = rules.resolve()
    mandate = spec() if mandate is None else mandate
    start = date.fromisoformat(mandate["start"][:10])
    end = date.fromisoformat(mandate["end"][:10])
    if mandate["start"][10:] != "T00:00:00Z" or mandate["end"][10:] != "T00:00:00Z":
        raise ValueError("manifest builder requires UTC-midnight research boundaries")

    v5 = _load_v5(root)
    acquired_start = date.fromisoformat(v5["start"])
    acquired_end = date.fromisoformat(v5["end_exclusive"])
    if acquired_start > start or acquired_end < end:
        raise ValueError("V5 acquisition does not cover warmup through the frozen endpoint")

    bars, funding = [], []
    current = acquired_start
    ordered = sorted(
        v5["shards"].items(),
        key=lambda item: (item[1].get("start", ""), item[0]),
    )
    for key, record in ordered:
        shard_start = date.fromisoformat(record.get("start", ""))
        shard_end = date.fromisoformat(record.get("end_exclusive", ""))
        if shard_start >= end:
            break
        if shard_start != current or shard_end <= shard_start:
            raise ValueError(f"V5 shard coverage is non-contiguous at {key}")
        if shard_end > end:
            raise ValueError(f"V5 shard extends beyond the frozen endpoint: {key}")
        if not _checkpoint_complete(root, record):
            raise ValueError(f"V5 shard is incomplete or corrupt: {key}")
        raw_hashes = [receipt["sha256"] for receipt in record["raw_pages"]]
        source = f"v5:{v5['api_host']}:{key}"
        common = dict(
            raw_sha256=raw_hashes,
            funding_mark_convention=record.get("funding_mark_convention", ""),
            shard_start=record["start"],
            shard_end_exclusive=record["end_exclusive"],
        )
        bars.append(_receipt_entry(root, record["bars"], source, **common))
        funding.append(_receipt_entry(root, record["funding"], source, **common))
        current = shard_end
    if current < end:
        raise ValueError(f"V5 shard coverage ends early at {current.isoformat()}")

    rule_entry = _read_rules(root, rules, rules_source, rules_provenance)
    manifest = {
        "venue": "bybit",
        "symbol": "BTCUSD",
        "contract_type": "InversePerpetual",
        "settlement_coin": "BTC",
        "provenance": "native" if rules_provenance == "native" else "proxy",
        "bar_interval_ms": v5["bar_interval_ms"],
        "start": mandate["start"],
        "end": mandate["end"],
        "warmup_start": acquired_start.isoformat() + "T00:00:00Z",
        "files": {
            "bars": bars,
            "funding": funding,
            "rules": [rule_entry],
        },
        "source_inventory": {
            "path": "v5-inventory.json",
            "bytes": (root / "v5-inventory.json").stat().st_size,
            "sha256": sha256(root / "v5-inventory.json"),
            "api_host": v5["api_host"],
            "bar_interval_ms": v5["bar_interval_ms"],
            "shard_days": v5["shard_days"],
        },
        "qualification_note": (
            "native market/funding inputs with sourced native historical rules"
            if rules_provenance == "native"
            else "proxy historical rules; economic output cannot be formal native qualification"
        ),
    }
    output = root / "manifest.json"
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build strict Pancakequant replay manifest")
    parser.add_argument("--root", required=True)
    parser.add_argument("--rules", default="rules.csv",
                        help="rules CSV path inside --root")
    parser.add_argument("--rules-source", required=True,
                        help="precise notice/API/archive provenance for the rules timeline")
    parser.add_argument("--rules-provenance", choices=("native", "proxy"), required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    rules = Path(args.rules)
    if not rules.is_absolute():
        rules = root / rules
    try:
        manifest = build(root, rules, args.rules_source, args.rules_provenance)
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "failed", "reason": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps({
        "status": "built",
        "manifest": str(root / "manifest.json"),
        "provenance": manifest["provenance"],
        "bars_files": len(manifest["files"]["bars"]),
        "funding_files": len(manifest["files"]["funding"]),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
