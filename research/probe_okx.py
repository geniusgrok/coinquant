"""Bounded public-only OKX BTC-USDT-SWAP historical coverage probe.

No account credentials are read. The probe verifies that the same linear USDT
perpetual covers the frozen 2020 start and 2026 endpoint for trade candles,
mark-price candles and funding history before Coinquant considers changing
its production exchange/contract.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, HTTPRedirectHandler, build_opener
from decimal import Decimal, InvalidOperation

HOSTS = ("openapi.okx.com", "www.okx.com")
START = 1577836800000  # 2020-01-01T00:00:00Z
START_AFTER = 1577923200000  # 2020-01-02T00:00:00Z; API returns older rows
END = 1789862400000  # 2026-09-20T00:00:00Z exclusive
END_EXPECTED_LAST_HOUR = END - 3_600_000
INST_ID = "BTC-USDT-SWAP"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("public evidence redirect refused")


def _get(url: str, output: Path) -> tuple[dict, dict]:
    request = Request(url, headers={"User-Agent": "coinquant-public-research"})
    with build_opener(NoRedirect).open(request, timeout=8) as response:
        payload = response.read(5_000_001)
    if not payload or len(payload) > 5_000_000:
        raise ValueError("empty or oversized OKX response")
    try:
        document = json.loads(payload)
    except ValueError as exc:
        raise ValueError("OKX response is not JSON") from exc
    if not isinstance(document, dict) or document.get("code") != "0":
        raise ValueError("OKX response is not successful")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    return document, {
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "source": url,
    }


def _rows(document: dict, *, timestamp_key: str | None = None) -> dict:
    data = document.get("data")
    if not isinstance(data, list) or not data:
        raise ValueError("OKX data list is empty")
    times = []
    for row in data:
        if timestamp_key is None:
            if not isinstance(row, list) or len(row) not in (6, 9) or row[-1] != "1":
                raise ValueError("malformed or incomplete OKX candle")
            t = int(row[0])
            op, high, low, close = map(Decimal, row[1:5])
            if (any(not p.is_finite() or p <= 0 for p in (op, high, low, close))
                    or low > min(op, close) or high < max(op, close)
                    or t % 3_600_000):
                raise ValueError("invalid candle price or timestamp")
        else:
            if not isinstance(row, dict) or row.get("instId") != INST_ID:
                raise ValueError("wrong funding instrument or malformed row")
            t = int(row[timestamp_key])
            rate = Decimal(row["realizedRate"])
            if not rate.is_finite():
                raise ValueError("invalid realized funding rate")
        if t <= 0:
            raise ValueError("invalid timestamp")
        times.append(t)
    if len(set(times)) != len(times):
        raise ValueError("duplicate timestamps")
    ordered = sorted(times)
    if timestamp_key is None and any(b - a != 3_600_000 for a, b in zip(ordered, ordered[1:])):
        raise ValueError("missing hourly candle inside boundary page")
    return {
        "rows": len(times), "first_ts": min(times), "last_ts": max(times),
        "contains_start": START in times,
        "contains_end_hour": END_EXPECTED_LAST_HOUR in times,
    }


def _listed_before_start(value) -> bool:
    try:
        return 0 < int(value) <= START
    except (ValueError, TypeError):
        return False


def probe_host(root: Path, host: str) -> dict:
    base = f"https://{host}/api/v5"
    endpoints = {
        "instrument": (
            f"{base}/public/instruments?instType=SWAP&instId={INST_ID}",
            None,
        ),
        "start_trade": (
            f"{base}/market/history-candles?instId={INST_ID}&bar=1H&after={START_AFTER}&limit=100",
            "array",
        ),
        "start_mark": (
            f"{base}/market/history-mark-price-candles?instId={INST_ID}&bar=1H&after={START_AFTER}&limit=100",
            "array",
        ),
        "start_funding": (
            f"{base}/public/funding-rate-history?instId={INST_ID}&after={START_AFTER}&limit=100",
            "funding",
        ),
        "end_trade": (
            f"{base}/market/history-candles?instId={INST_ID}&bar=1H&after={END}&limit=100",
            "array",
        ),
        "end_mark": (
            f"{base}/market/history-mark-price-candles?instId={INST_ID}&bar=1H&after={END}&limit=100",
            "array",
        ),
        "end_funding": (
            f"{base}/public/funding-rate-history?instId={INST_ID}&after={END}&limit=100",
            "funding",
        ),
    }
    result = {"host": host, "requests": {}}
    for name, (url, kind) in endpoints.items():
        row = {"source": url}
        try:
            document, receipt = _get(url, root / host / f"{name}.json")
            row.update(status="downloaded", **receipt)
            data = document["data"]
            if name == "instrument":
                if len(data) != 1 or not isinstance(data[0], dict):
                    raise ValueError("unexpected OKX instrument response")
                inst = data[0]
                row["instrument"] = {
                    key: inst.get(key) for key in (
                        "instId", "instType", "ctType", "settleCcy", "ctVal",
                        "ctValCcy", "tickSz", "lotSz", "minSz", "lever",
                        "state", "listTime"
                    )
                }
            elif kind == "array":
                row.update(_rows(document))
            elif kind == "funding":
                row.update(_rows(document, timestamp_key="fundingTime"))
        except (HTTPError, URLError, OSError, ValueError, KeyError, TypeError, InvalidOperation) as exc:
            row.update(
                status="unavailable",
                error_type=type(exc).__name__,
                http_status=getattr(exc, "code", None),
                error=str(exc),
            )
        result["requests"][name] = row

    checks = []
    inst = result["requests"]["instrument"]
    if inst.get("status") == "downloaded":
        meta = inst["instrument"]
        checks.extend([
            ("instrument_id", meta.get("instId") == INST_ID),
            ("instrument_swap", meta.get("instType") == "SWAP"),
            ("instrument_linear", meta.get("ctType") == "linear"),
            ("instrument_usdt_settlement", meta.get("settleCcy") == "USDT"),
            ("listed_before_formal_start", _listed_before_start(meta.get("listTime"))),
            ("instrument_live", meta.get("state") == "live"),
        ])
    else:
        checks.append(("instrument_available", False))

    for name in ("start_trade", "start_mark"):
        row = result["requests"][name]
        checks.append((f"{name}_covers_start",
                       row.get("status") == "downloaded"
                       and row.get("contains_start") is True))
    funding = result["requests"]["start_funding"]
    checks.append(("start_funding_covers_start",
                   funding.get("status") == "downloaded"
                   and funding.get("contains_start") is True))

    for name in ("end_trade", "end_mark"):
        row = result["requests"][name]
        checks.append((f"{name}_covers_end",
                       row.get("status") == "downloaded"
                       and row.get("contains_end_hour") is True
                       and row.get("last_ts", END) < END))
    funding = result["requests"]["end_funding"]
    checks.append(("end_funding_present_before_end",
                   funding.get("status") == "downloaded"
                   and funding.get("last_ts", 0) < END
                   and funding.get("last_ts", 0) >= END - 24 * 3_600_000))

    result["checks"] = [{"name": name, "passed": passed} for name, passed in checks]
    result["passed"] = all(passed for _, passed in checks)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=True)

    attempts = []
    selected = None
    for host in HOSTS:
        result = probe_host(root, host)
        attempts.append(result)
        if result["passed"]:
            selected = host
            break
    report = {
        "purpose": "OKX BTC-USDT-SWAP 2020-2026 native-history feasibility only",
        "formal_window": {
            "start": "2020-01-01T00:00:00Z",
            "end_exclusive": "2026-09-20T00:00:00Z",
        },
        "attempts": attempts,
        "selected_host": selected,
        "passed": selected is not None,
        "qualification": "NOT_QUALIFIED",
        "scope": "boundary pages only; not full coverage, rules or execution qualification",
    }
    (root / "REPORT.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
