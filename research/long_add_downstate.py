"""Aggregate the public simulated account's add-only mark coverage; no trading."""

import bisect
import gzip
import json
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path


def positive(value):
    return Decimal(str(value)) > 0


def main(account_file, reports_file):
    account = json.loads(gzip.decompress(Path(account_file).read_bytes()))
    assert account["complete"] and account["session_count"] == 795
    assert account["no_live_account"] is True and account["native_verified"] is False
    financial = account["financial"]
    assert financial["audit"]["passed"]
    daily = sorted(financial["daily"], key=lambda row: row["stamp_ms"])
    day_times = [row["stamp_ms"] for row in daily]

    reports = [json.loads(line) for line in Path(reports_file).open()]
    assert len(reports) == 795
    held_reports = []
    for report in reports:
        actual = report["actual"]
        if (positive(actual["quantity_btc"]) and positive(actual["mark_price"])
                and actual["mark_time"] <= actual["observed_at_ms"]):
            held_reports.append((actual["mark_time"], actual["observed_at_ms"]))
    held_reports.sort()
    report_times = [row[0] for row in held_reports]

    fills = sorted(financial["trades"], key=lambda row: (row["time"], row["id"]))
    position = Decimal(0)
    campaign = 0
    seen_orders = set()
    signaled = {"2020-2022": set(), "2023-2026": set()}
    counts = Counter()
    for fill in fills:
        if fill["side"] == "BUY" and fill["orderId"] not in seen_orders:
            seen_orders.add(fill["orderId"])
            if position > 0:
                era = "2020-2022" if fill["time"] < 1672531200000 else "2023-2026"
                counts[f"topups_{era}"] += 1
                i = bisect.bisect_left(day_times, fill["time"])
                if i < 2:
                    label = "missing"
                else:
                    earlier, later = daily[i - 2], daily[i - 1]
                    if not all(positive(row["quantity_btc"]) and positive(row["mark_usdt"])
                               for row in (earlier, later)):
                        label = "missing"
                    elif (later["stamp_ms"] - earlier["stamp_ms"] > 48 * 3600 * 1000
                          or fill["time"] - later["stamp_ms"] > 24 * 3600 * 1000):
                        label = "stale"
                    else:
                        label = "decline" if Decimal(later["mark_usdt"]) < Decimal(earlier["mark_usdt"]) else "nondecline"
                counts[f"{label}_{era}"] += 1
                if label == "decline":
                    signaled[era].add(campaign)

                j = bisect.bisect_left(report_times, fill["time"])
                if (j >= 2 and all(row[1] < fill["time"] for row in held_reports[j - 2:j])
                        and fill["time"] - report_times[j - 1] <= 24 * 3600 * 1000
                        and report_times[j - 1] - report_times[j - 2] <= 48 * 3600 * 1000):
                    counts["topups_with_two_fresh_prior_report_marks"] += 1
        quantity = Decimal(fill["qty"])
        if fill["side"] == "BUY":
            if position == 0:
                campaign += 1
            position += quantity
        else:
            assert fill["side"] == "SELL" and quantity <= position
            position -= quantity
    assert position == 0 and len(fills) == 1561
    total = sum(len(ids) for ids in signaled.values())
    result = {
        "daily_held_marks": sum(positive(row["quantity_btc"]) and positive(row["mark_usdt"]) for row in daily),
        "report_held_marks": len(held_reports),
        "counts": dict(sorted(counts.items())),
        "signaled_campaigns_by_era": {era: len(ids) for era, ids in signaled.items()},
        "support_gate_passed": total >= 10 and all(len(ids) >= 3 for ids in signaled.values()),
    }
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:])
