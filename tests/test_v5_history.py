import json
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from research.acquire_v5 import MINUTE_MS, acquire, fetch_funding, fetch_klines, merge_day


class Response(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class FakeOpener:
    def __init__(self, *, skip=None):
        self.skip = skip
        self.calls = []

    def open(self, request, timeout):
        self.calls.append(request.full_url)
        parsed = urlparse(request.full_url)
        query = {key: values[0] for key, values in parse_qs(parsed.query).items()}
        start = int(query.get("start", query.get("startTime", "0")))
        end = int(query.get("end", query.get("endTime", "0")))
        if parsed.path.endswith("/funding/history"):
            rows = [{
                "symbol": "BTCUSD",
                "fundingRate": "0.0001",
                "fundingRateTimestamp": str(start),
            }]
            result = {"category": "inverse", "list": rows}
        else:
            aligned_end = end // MINUTE_MS * MINUTE_MS
            times = [
                timestamp for timestamp in range(aligned_end, start - 1, -MINUTE_MS)
                if timestamp != self.skip
            ][:2]  # force pagination even though the real endpoint allows 1000
            if parsed.path.endswith("/market/kline"):
                rows = [[str(t), "100", "102", "99", "101", "10", "0.1"] for t in times]
            else:
                rows = [[str(t), "200", "202", "199", "201"] for t in times]
            result = {"category": "inverse", "symbol": "BTCUSD", "list": rows}
        payload = json.dumps({
            "retCode": 0,
            "retMsg": "OK",
            "result": result,
            "retExtInfo": {},
            "time": 1,
        }).encode()
        return Response(payload)


class V5HistoryTests(unittest.TestCase):
    def test_kline_pagination_is_complete_and_reverse_pages_are_preserved(self):
        start = 1_000_000 * MINUTE_MS
        end = start + 3 * MINUTE_MS
        with tempfile.TemporaryDirectory() as directory:
            opener = FakeOpener()
            rows, receipts = fetch_klines(
                "api.bybit.com", "trade", start, end, Path(directory),
                opener=opener,
            )
        self.assertEqual(sorted(rows), [start, start + MINUTE_MS, start + 2 * MINUTE_MS])
        self.assertEqual(len(receipts), 2)
        self.assertEqual(rows[start][-1], "10")
        self.assertEqual(len(opener.calls), 2)

    def test_missing_native_mark_minute_is_rejected(self):
        start = 1_000_000 * MINUTE_MS
        end = start + 3 * MINUTE_MS
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "missing native mark minute"):
                fetch_klines(
                    "api.bybit.com", "mark", start, end, Path(directory),
                    opener=FakeOpener(skip=start + MINUTE_MS),
                )

    def test_funding_uses_boundary_mark_open_not_future_close(self):
        start = 1_000_000 * MINUTE_MS
        end = start + 2 * MINUTE_MS
        trade = {
            start: ("100", "102", "99", "101", "10"),
            start + MINUTE_MS: ("101", "103", "100", "102", "11"),
        }
        mark = {
            start: ("200", "202", "199", "999"),
            start + MINUTE_MS: ("201", "203", "200", "998"),
        }
        bars, funding = merge_day(trade, mark, {start: "0.0001"}, start, end)
        self.assertEqual(len(bars), 2)
        self.assertEqual(funding, [(start, "0.0001", "200")])

    def test_acquisition_receipts_are_portable_relative_paths(self):
        from datetime import date, datetime, timezone

        day = date(2020, 1, 1)
        start = int(datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
        trade = {
            t: ("100", "102", "99", "101", "10")
            for t in range(start, start + 86_400_000, MINUTE_MS)
        }
        mark = {
            t: ("200", "202", "199", "201")
            for t in range(start, start + 86_400_000, MINUTE_MS)
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trade_receipt = {
                "path": str(root / "raw/2020-01-01/trade-000.json"),
                "bytes": 1, "sha256": "a", "source": "https://api.bybit.com/trade",
            }
            mark_receipt = {
                "path": str(root / "raw/2020-01-01/mark-000.json"),
                "bytes": 1, "sha256": "b", "source": "https://api.bybit.com/mark",
            }
            funding_receipt = {
                "path": str(root / "raw/2020-01-01/funding.json"),
                "bytes": 1, "sha256": "c", "source": "https://api.bybit.com/funding",
            }
            with patch("research.acquire_v5.fetch_klines",
                       side_effect=[(trade, [trade_receipt]), (mark, [mark_receipt])]), \
                 patch("research.acquire_v5.fetch_funding",
                       return_value=({}, [funding_receipt])):
                result = acquire(root, "api.bybit.com", day, date(2020, 1, 2))
            self.assertEqual(result["status"], "complete")
            inventory = json.loads((root / "v5-inventory.json").read_text())
            record = inventory["days"]["2020-01-01"]
            self.assertEqual(
                [row["path"] for row in record["raw_pages"]],
                ["raw/2020-01-01/trade-000.json",
                 "raw/2020-01-01/mark-000.json",
                 "raw/2020-01-01/funding.json"],
            )
            self.assertEqual(record["bars"]["path"], "normalized/bars/2020-01-01.csv.gz")
            self.assertEqual(record["funding"]["path"], "normalized/funding/2020-01-01.csv.gz")

    def test_funding_schema_and_host_allowlist(self):
        start = 1_000_000 * MINUTE_MS
        end = start + 2 * MINUTE_MS
        with tempfile.TemporaryDirectory() as directory:
            values, receipts = fetch_funding(
                "api.bybit.com", start, end, Path(directory), opener=FakeOpener())
            self.assertEqual(values, {start: "0.0001"})
            self.assertEqual(len(receipts), 1)
            with self.assertRaisesRegex(ValueError, "approved Bybit live host"):
                fetch_funding("example.com", start, end, Path(directory), opener=FakeOpener())


if __name__ == "__main__":
    unittest.main()
