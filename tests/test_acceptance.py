import unittest
from coinquant.research import economic_limits, spec

class AcceptanceTests(unittest.TestCase):
    def test_current_contract_separates_unchanged_historical_benchmark(self):
        import hashlib,json
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        current=json.loads((root/'research/spec.json').read_text())
        historical=(root/current['legacy_benchmark']['path']).read_bytes()
        self.assertEqual(hashlib.sha256(historical).hexdigest(),current['legacy_benchmark']['sha256'])
        self.assertEqual(json.loads(historical),spec())
        self.assertEqual((current['venue'],current['symbol'],current['leverage']),('binance','BTCUSDT',20))
        self.assertEqual(current['economic_qualification'],'NOT_MEASURED_FOR_CURRENT_SESSION')

    def test_authorized_exact_boundaries(self):
        frozen = spec()
        self.assertTrue(economic_limits('1.5', '0.499999999999999999', frozen))
        self.assertFalse(economic_limits('1.499999999999999999', '0.1', frozen))
        self.assertFalse(economic_limits('2', '0.5', frozen))
