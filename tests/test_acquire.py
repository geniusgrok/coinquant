from datetime import date
import gzip
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from research.acquire import acquire, checkpoint, default_window, download, source


class ArchiveAcquisitionTests(unittest.TestCase):
    def test_urls_and_default_window_are_frozen_to_btcusd_archive(self):
        start, end = default_window()
        self.assertEqual(start, date(2019, 12, 11))
        self.assertEqual(end, date(2026, 9, 20))
        day = date(2020, 1, 1)
        self.assertEqual(
            source("trades", day),
            ("https://public.bybit.com/trading/BTCUSD/BTCUSD2020-01-01.csv.gz",
             "BTCUSD2020-01-01.csv.gz"),
        )
        self.assertEqual(
            source("index", day)[0],
            "https://public.bybit.com/spot_index/BTCUSD/BTCUSD2020-01-01_index_price.csv.gz",
        )
        self.assertEqual(
            source("premium", day)[0],
            "https://public.bybit.com/premium_index/BTCUSD/BTCUSD2020-01-01_premium_index.csv.gz",
        )

    def test_verified_checkpoint_is_not_downloaded_again(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day = date(2020, 1, 1)
            relative = Path("raw/trades/BTCUSD2020-01-01.csv.gz")
            target = root / relative
            target.parent.mkdir(parents=True)
            payload = b"preserved-original"
            target.write_bytes(payload)
            inventory = {
                "version": 1,
                "symbol": "BTCUSD",
                "start": "2020-01-01",
                "end_exclusive": "2020-01-02",
                "kinds": ["trades"],
                "created_utc": "fixed",
                "files": {
                    "trades:2020-01-01": {
                        "kind": "trades",
                        "day": "2020-01-01",
                        "path": relative.as_posix(),
                        "source": source("trades", day)[0],
                        "status": "downloaded",
                        "bytes": len(payload),
                        "sha256": hashlib.sha256(payload).hexdigest(),
                    }
                },
            }
            checkpoint(root / "archive-inventory.json", inventory)
            with patch("research.acquire.download", side_effect=AssertionError("must not redownload")):
                result = acquire(root, day, date(2020, 1, 2), ("trades",))
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["downloaded"], 1)

    def test_failure_is_checkpointed_and_returns_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("research.acquire.download", side_effect=OSError("network unavailable")):
                result = acquire(root, date(2020, 1, 1), date(2020, 1, 2), ("trades",))
            self.assertEqual(result["status"], "incomplete")
            self.assertEqual(result["unavailable"], 1)
            inventory = json.loads((root / "archive-inventory.json").read_text())
            row = inventory["files"]["trades:2020-01-01"]
            self.assertEqual(row["status"], "unavailable")
            self.assertEqual(row["error_type"], "OSError")


    def test_http_416_partial_restarts_from_zero_and_reverifies(self):
        class Response(io.BytesIO):
            status = 200
            def getcode(self):
                return self.status
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.close()

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "day.csv.gz"
            partial = target.with_suffix(target.suffix + ".partial")
            partial.write_bytes(b"unverified-partial")
            payload = gzip.compress(b"timestamp,price\n1,2\n")
            exhausted = HTTPError("https://example.invalid", 416, "range", {}, None)
            with patch("research.acquire._open", side_effect=[exhausted, Response(payload)]) as opened:
                size, digest = download(
                    "https://example.invalid/day.csv.gz", target,
                    timeout=1, max_bytes=1024,
                )
            self.assertEqual(opened.call_count, 2)
            self.assertEqual(opened.call_args_list[0].args[1], len(b"unverified-partial"))
            self.assertEqual(opened.call_args_list[1].args[1], 0)
            self.assertEqual(target.read_bytes(), payload)
            self.assertEqual(size, len(payload))
            self.assertEqual(digest, hashlib.sha256(payload).hexdigest())
            self.assertFalse(partial.exists())


if __name__ == "__main__":
    unittest.main()
