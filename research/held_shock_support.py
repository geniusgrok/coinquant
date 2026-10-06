"""Count frozen held-shock support from archived simulation, without wallet replay.

Requires local anonymized intervals from entry_path_reconstruct.py and the
original, SHA-matched Binance UM 4h monthly ZIPs. No network or account calls.
"""

import argparse
import csv
import datetime as dt
import hashlib
import json
import subprocess
import zipfile
from collections import Counter
from decimal import Decimal as D
from pathlib import Path

ARCHIVE = "c6223a5d1bd6ae46fd192668335cee31630ff33e"
DAY = 86400000
FOUR = 14400000


def archived(path):
    return subprocess.check_output(["git", "show", f"{ARCHIVE}:{path}"])


def daily_closes(directory):
    files = json.loads(archived("backtest-source/data/qualified-market-metadata.json"))[
        "qualification_maps"]["files"]
    digests = {key.split("/")[-1]: value["original_content_sha256"]
               for key, value in files.items() if "/klines/4h/" in key}
    closes = {}
    for year in range(2020, 2027):
        for month in range(1, 13):
            if (year, month) > (2026, 8):
                break
            name = f"BTCUSDT-4h-{year:04d}-{month:02d}.zip"
            path = directory / name
            if hashlib.sha256(path.read_bytes()).hexdigest() != digests[name]:
                raise ValueError(f"original 4h source digest mismatch: {name}")
            with zipfile.ZipFile(path) as source:
                for row in csv.reader(source.read(source.namelist()[0]).decode().splitlines()):
                    if not row[0].isdigit():
                        continue
                    end = int(row[0]) + FOUR
                    if end % DAY == 0:
                        close = D(row[4])
                        if end in closes and closes[end] != close:
                            raise ValueError("conflicting complete daily close")
                        closes[end] = close
    if len(closes) != 2435 or (max(closes) - min(closes)) // DAY + 1 != len(closes):
        raise ValueError("incomplete public market series")
    return closes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("intervals", type=Path)
    parser.add_argument("h4_dir", type=Path)
    args = parser.parse_args()
    intervals = json.loads(args.intervals.read_text())
    reports = [json.loads(line) for line in archived(
        "backtest-source/private/coin/reports.jsonl").splitlines()]
    assert len(intervals) == 50 and len(reports) == 795
    close = daily_closes(args.h4_dir)
    summary = Counter()
    hits = set()
    inferred_hits = set()
    missing = set()

    def evaluate(interval, report, phase):
        preview = report.get("model_preview") or {}
        actual = report.get("actual") or {}
        if not (report["status"] in ("no_action", "executed") and preview.get("action") == "hold"
                and actual.get("native_full_position_protected")
                and actual.get("stop_before_liquidation")):
            return
        # A terminal report can describe the NEXT campaign if this one exited
        # and a fresh entry filled in the same manual session.
        if interval["last_ms"] <= report["start_ms"] + 300000:
            return
        identity = interval["identity_ms"]
        if identity is None or preview.get("position_campaign") != identity:
            return
        summary[f"confirmed_{phase}_hold"] += 1
        end = report["market_through"] // DAY * DAY
        dates = [end - i * DAY for i in range(20, -1, -1)]
        if not all(date in close for date in dates):
            missing.add(interval["n"])
            summary["missing_20day_history"] += 1
            return
        returns = [close[b] / close[a] - 1 for a, b in zip(dates, dates[1:])]
        short = sum((min(value, D(0)) ** 2 for value in returns[-5:]), D(0)) / 5
        long = sum((min(value, D(0)) ** 2 for value in returns), D(0)) / 20
        summary[f"qualified_{phase}_hold"] += 1
        if long and short > D("2.25") * long:
            summary["trigger_sessions"] += 1
            hits.add(interval["n"])

    for interval in intervals:
        for report in reports:
            start = report["start_ms"]
            if not interval["first_ms"] < start < interval["last_ms"]:
                continue
            summary["held_at_start"] += 1
            evaluate(interval, report, "start")
        entry = reports[interval["entry_session_index"]]
        if entry["start_ms"] <= interval["first_ms"] < entry["start_ms"] + 300000:
            summary["entry_sessions"] += 1
            evaluate(interval, entry, "same_session_entry")
            # The terminal report discards its preview if its final poll times
            # out. Successful earlier cycles can still establish a protected
            # post-entry hold, but keep these separate from preserved previews.
            timing = entry.get("entry_timing") or {}
            errors = entry.get("errors") or []
            actual = entry.get("actual") or {}
            inferred = (entry["status"] == "executed" and not entry.get("model_preview")
                        and interval["last_ms"] > entry["start_ms"] + 300000
                        and actual.get("native_full_position_protected")
                        and actual.get("stop_before_liquidation")
                        and entry["cycles"] >= 3 and len(errors) == 1
                        and errors[0].get("cycle") == entry["cycles"]
                        and errors[0].get("error_type") == "ObservationDeadline"
                        and timing.get("stop_account_readback_at_ms", 10**20)
                        < entry["start_ms"] + 300000)
            if inferred:
                summary["inferred_postentry_hold"] += 1
                end = entry["market_through"] // DAY * DAY
                dates = [end - i * DAY for i in range(20, -1, -1)]
                if all(date in close for date in dates):
                    returns = [close[b] / close[a] - 1 for a, b in zip(dates, dates[1:])]
                    short = sum((min(v, D(0)) ** 2 for v in returns[-5:]), D(0)) / 5
                    long = sum((min(v, D(0)) ** 2 for v in returns), D(0)) / 20
                    if long and short > D("2.25") * long:
                        inferred_hits.add(interval["n"])
    by_number = {interval["n"]: interval for interval in intervals}
    years = Counter(str(dt.datetime.fromtimestamp(
        by_number[n]["entry_session_start_ms"] / 1000, dt.timezone.utc).year) for n in hits)
    kinds = Counter(by_number[n]["kind"] for n in hits)
    print(json.dumps({"counts": dict(summary), "independent_campaigns": len(hits),
                      "independent_campaigns_by_year": dict(years),
                      "independent_campaigns_by_kind": dict(kinds),
                      "additional_inferred_campaigns": len(inferred_hits - hits),
                      "missing_campaigns_upper_bound": len(missing),
                      "maximum_campaigns_if_all_missing_trigger": len(hits | inferred_hits | missing)}, indent=2))


if __name__ == "__main__":
    main()
