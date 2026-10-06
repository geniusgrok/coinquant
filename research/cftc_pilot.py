"""Read-only, targeted CFTC check against anonymized historical simulation intervals."""

import argparse
import datetime as dt
import json
import urllib.parse
import urllib.request
from collections import defaultdict


API = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
UTC = dt.timezone.utc


def public_reports():
    # Fixed public source range: no local session time or account fact leaves this process.
    query = {
        "$select": ":created_at,:updated_at,report_date_as_yyyy_mm_dd,"
        "lev_money_positions_long,lev_money_positions_short,open_interest_all",
        "$where": "cftc_contract_market_code='133741' "
        "AND report_date_as_yyyy_mm_dd >= '2022-09-13T00:00:00' "
        "AND report_date_as_yyyy_mm_dd < '2026-10-01T00:00:00'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": "250",
    }
    with urllib.request.urlopen(API + "?" + urllib.parse.urlencode(query), timeout=20) as response:
        rows = json.load(response)
    if len(rows) >= 250:
        raise ValueError("Public source query hit row limit")
    return rows


def ratio(row):
    return (int(row["lev_money_positions_long"]) - int(row["lev_money_positions_short"])) / int(row["open_interest_all"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("intervals", help="Local anonymized 50-interval JSON from entry_path_reconstruct.py")
    args = parser.parse_args()
    intervals = json.load(open(args.intervals, encoding="utf-8"))
    source = public_reports()
    print("fixed public BTC rows", len(source), "unchanged", sum(r[":created_at"] == r[":updated_at"] for r in source))
    groups = defaultdict(list)
    for interval in intervals:
        if interval["kind"] != "primary" or interval["first_ms"] < 1663350000000:
            continue
        start = dt.datetime.fromtimestamp(interval["entry_session_start_ms"] / 1000, UTC)
        rows = [row for row in source if
                dt.datetime.fromisoformat(row[":created_at"].replace("Z", "+00:00")) < start
                and row[":updated_at"] == row[":created_at"]][:2]
        if len(rows) < 2:
            groups["missing"].append(interval)
            continue
        latest, previous = rows
        report_date = dt.datetime.fromisoformat(latest["report_date_as_yyyy_mm_dd"].replace("Z", "+00:00"))
        if report_date.tzinfo is None:
            report_date = report_date.replace(tzinfo=UTC)
        age = (start - report_date).days
        interval = dict(interval, source_age_days=age, source_report=latest["report_date_as_yyyy_mm_dd"][:10])
        groups["negative" if ratio(latest) < ratio(previous) else "nonnegative"].append(interval)
    for name in ("negative", "nonnegative", "missing"):
        rows = groups[name]
        print(name, "n", len(rows), "wins", sum(float(r["net_usdt"]) > 0 for r in rows),
              "net", round(sum(float(r["net_usdt"]) for r in rows), 2),
              "winning net", round(sum(max(float(r["net_usdt"]), 0) for r in rows), 2),
              "losing net", round(sum(min(float(r["net_usdt"]), 0) for r in rows), 2),
              "fees", round(sum(float(r["fees_usdt"]) for r in rows), 2),
              "funding", round(sum(float(r["funding_usdt"]) for r in rows), 2))
        for label, subset in (("2022-24", [r for r in rows if r["first_ms"] < 1735689600000]),
                              ("2025-26", [r for r in rows if r["first_ms"] >= 1735689600000])):
            print(" ", label, "n", len(subset), "wins", sum(float(r["net_usdt"]) > 0 for r in subset),
                  "net", round(sum(float(r["net_usdt"]) for r in subset), 2))
        if rows and name != "missing":
            print("  source age days", min(r["source_age_days"] for r in rows),
                  max(r["source_age_days"] for r in rows),
                  "signal age hours", min(r["signal_age_hours"] for r in rows),
                  max(r["signal_age_hours"] for r in rows))


if __name__ == "__main__":
    main()
