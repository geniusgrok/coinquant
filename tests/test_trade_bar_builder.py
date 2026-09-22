import csv
from datetime import date
from decimal import Decimal
import gzip
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from research.build_trade_bars import aggregate_day, build, midnight_ms, write_day


HEADER = [
    "timestamp", "symbol", "side", "size", "price", "tickDirection",
    "trdMatchID", "grossValue", "homeNotional", "foreignNotional",
]


def trade_payload(day: date, *, missing_minute: int | None = None) -> bytes:
    base = midnight_ms(day) // 1000
    text = io.StringIO(newline="")
    writer = csv.writer(text, lineterminator="\n")
    writer.writerow(HEADER)
    for minute in reversed(range(1440)):
        if minute == missing_minute:
            continue
        latest = Decimal(base) + Decimal(minute * 60 + 50)
        price = Decimal("7000") + minute
        writer.writerow([
            str(latest), "BTCUSD", "Buy", "2", str(price + 1), "PlusTick",
            f"latest-{minute}", "1", "2", "3",
        ])
        if minute == 0:
            earliest = Decimal(base) + Decimal(10)
            writer.writerow([
                str(earliest), "BTCUSD", "Sell", "3", str(price - 1), "MinusTick",
                "earliest-0", "1", "3", "4",
            ])
    return gzip.compress(text.getvalue().encode(), mtime=0)


class TradeBarBuilderTests(unittest.TestCase):
    def test_reverse_native_trades_become_complete_ascending_minutes(self):
        day = date(2020, 1, 1)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "day.csv.gz"
            source.write_bytes(trade_payload(day))
            rows = aggregate_day(source, day)
        self.assertEqual(len(rows), 1440)
        self.assertEqual(rows[0][0], midnight_ms(day))
        self.assertEqual(rows[-1][0], midnight_ms(day) + 1439 * 60_000)
        self.assertEqual(rows[0][1:6], ("6999", "7001", "6999", "7001", "5"))

    def test_missing_native_trade_minute_is_rejected_not_forward_filled(self):
        day = date(2020, 1, 1)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "day.csv.gz"
            source.write_bytes(trade_payload(day, missing_minute=123))
            with self.assertRaisesRegex(ValueError, "missing minute"):
                aggregate_day(source, day)

    def test_normalized_gzip_is_byte_reproducible(self):
        rows = [(0, "1", "2", "1", "2", "3")]
        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory) / "a.gz", Path(directory) / "b.gz"
            _, sha_a = write_day(first, rows)
            _, sha_b = write_day(second, rows)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(sha_a, sha_b)

    def test_build_binds_output_to_verified_original(self):
        day = date(2020, 1, 1)
        payload = trade_payload(day)
        digest = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "archive"
            raw = archive / "raw/trades"
            raw.mkdir(parents=True)
            source = raw / "BTCUSD2020-01-01.csv.gz"
            source.write_bytes(payload)
            inventory = {
                "version": 1,
                "symbol": "BTCUSD",
                "start": "2020-01-01",
                "end_exclusive": "2020-01-02",
                "kinds": ["trades"],
                "files": {
                    "trades:2020-01-01": {
                        "status": "downloaded",
                        "path": "raw/trades/BTCUSD2020-01-01.csv.gz",
                        "bytes": len(payload),
                        "sha256": digest,
                        "source": "https://public.bybit.com/trading/BTCUSD/BTCUSD2020-01-01.csv.gz",
                    }
                },
            }
            (archive / "archive-inventory.json").write_text(json.dumps(inventory))
            output = root / "bars"
            result = build(archive, output)
            self.assertEqual(result["status"], "complete")
            built = json.loads((output / "trade-bars-inventory.json").read_text())
            row = built["files"]["2020-01-01"]
            self.assertEqual(row["rows"], 1440)
            self.assertEqual(row["source_sha256"], digest)
            self.assertEqual(row["status"], "built")


if __name__ == "__main__":
    unittest.main()
