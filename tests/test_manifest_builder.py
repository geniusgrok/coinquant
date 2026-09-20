from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from research.build_manifest import EXPECTED_RULE_COLUMNS, build


def receipt(root: Path, relative: str, payload: bytes) -> dict:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {
        "path": relative,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def fixture(root: Path):
    raw = receipt(root, "raw/2019-12-31/trade.json", b"raw")
    bars = receipt(root, "normalized/bars/2019-12-31.csv.gz", b"bars")
    funding = receipt(root, "normalized/funding/2019-12-31.csv.gz", b"funding")
    inventory = {
        "version": 1,
        "api_host": "api.bybit.com",
        "symbol": "BTCUSD",
        "category": "inverse",
        "start": "2019-12-31",
        "end_exclusive": "2020-01-01",
        "days": {
            "2019-12-31": {
                "status": "complete",
                "raw_pages": [raw],
                "bars": bars,
                "funding": funding,
                "funding_mark_convention": "native mark 1m open at settlement timestamp",
            }
        },
    }
    (root / "v5-inventory.json").write_text(json.dumps(inventory))
    rules = root / "rules.csv"
    rules.write_text(
        ",".join(EXPECTED_RULE_COLUMNS) + "\n"
        "1577750400000,1514764800000,28800000,0.5,1,1,10000,5000,150,0.005,0.00075,0.005\n"
    )
    mandate = {
        "start": "2019-12-31T00:00:00Z",
        "end": "2020-01-01T00:00:00Z",
    }
    return rules, mandate


class ManifestBuilderTests(unittest.TestCase):
    def test_native_rules_preserve_native_manifest_and_hash_chain(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            rules, mandate = fixture(root)
            manifest = build(
                root, rules, "https://example.invalid/native-rule-notice", "native",
                mandate=mandate,
            )
            self.assertEqual(manifest["provenance"], "native")
            self.assertEqual(len(manifest["files"]["bars"]), 1)
            self.assertEqual(len(manifest["files"]["funding"]), 1)
            self.assertEqual(manifest["files"]["rules"][0]["provenance"], "native")
            self.assertTrue((root / "manifest.json").is_file())

    def test_proxy_rules_force_proxy_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            rules, mandate = fixture(root)
            manifest = build(
                root, rules, "research approximation", "proxy", mandate=mandate)
            self.assertEqual(manifest["provenance"], "proxy")
            self.assertIn("cannot be formal native qualification",
                          manifest["qualification_note"])

    def test_corrupt_v5_day_refuses_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            rules, mandate = fixture(root)
            (root / "normalized/bars/2019-12-31.csv.gz").write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "incomplete or corrupt"):
                build(root, rules, "native source", "native", mandate=mandate)


if __name__ == "__main__":
    unittest.main()
