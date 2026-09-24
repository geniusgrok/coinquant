"""Read the preserved SX60 account. Never infer unfilled trade PnL."""

import csv
import gzip
import hashlib
import io
import json
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).parent
ACCOUNT = ROOT / "sx60-account"


def rows(name):
    with gzip.open(io.BytesIO(original(name)), "rt", newline="") as source:
        yield from csv.DictReader(source)


def year(row):
    return datetime.fromtimestamp(int(row["time"]) / 1000, timezone.utc).year


def original(name):
    expected = json.loads((ROOT / "ORIGINALS.json").read_text())["files"][name]
    if "parts" in expected:
        chunks = []
        offset = 0
        for part in expected["parts"]:
            data = (ACCOUNT / part["file"]).read_bytes()
            assert part["offset"] == offset and len(data) == part["bytes"]
            assert hashlib.sha256(data).hexdigest() == part["sha256"]
            assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == part["git_blob_sha1"]
            chunks.append(data)
            offset += len(data)
        data = b"".join(chunks)
    else:
        data = (ACCOUNT / name).read_bytes()
    assert len(data) == expected["bytes"]
    assert hashlib.sha256(data).hexdigest() == expected["sha256"]
    return data


def main():
    manifest = json.loads((ROOT / "ORIGINALS.json").read_text())
    for name in manifest["files"]:
        original(name)

    result = json.loads((ACCOUNT / "result.json").read_text())
    annual = {}
    close_hours = 0
    flat_close_hours = 0
    for row in rows("equity.csv.gz"):
        if row["event"] != "close":
            continue
        close_hours += 1
        flat_close_hours += Decimal(row["quantity"]) == 0
        annual[str(year(row))] = {
            "last_close_time": row["time"],
            "equity_usdt": row["equity_usdt"],
            "cumulative_fees_usdt": row["fees"],
            "cumulative_funding_usdt": row["funding"],
        }
    orders = Counter(row["event"] for row in rows("orders.csv.gz"))
    decisions = Counter(row["action"] for row in rows("decisions.csv.gz"))
    assert close_hours == 58896 and sum(decisions.values()) == 795
    assert orders["entry"] == 30
    assert Decimal(annual["2026"]["cumulative_fees_usdt"]) == Decimal(result["fees_usdt"])
    assert Decimal(annual["2026"]["cumulative_funding_usdt"]) == Decimal(result["funding_bound_paid_usdt"])

    start = Decimal("1432.011696912359164014793153")
    previous = start
    previous_fees = previous_funding = Decimal(0)
    for record in annual.values():
        equity = Decimal(record["equity_usdt"])
        fees = Decimal(record["cumulative_fees_usdt"])
        funding = Decimal(record["cumulative_funding_usdt"])
        record["net_change_usdt"] = str(equity - previous)
        record["fees_usdt"] = str(fees - previous_fees)
        record["funding_usdt"] = str(funding - previous_funding)
        previous, previous_fees, previous_funding = equity, fees, funding
    assert abs(previous - start - sum((Decimal(x["net_change_usdt"]) for x in annual.values()), Decimal(0))) < Decimal("1e-15")
    return {
        "source_archive_sha256": manifest["source_archive_sha256"],
        "final_cny": result["final_cny"],
        "cagr": result["cagr"],
        "mdd_conservative_envelope": result["mdd_conservative_envelope"],
        "annual": annual,
        "close_hours": close_hours,
        "flat_close_hours": flat_close_hours,
        "orders": dict(sorted(orders.items())),
        "decisions": dict(sorted(decisions.items())),
    }


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, ensure_ascii=False))
