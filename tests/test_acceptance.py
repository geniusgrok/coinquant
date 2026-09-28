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
        self.assertEqual(current['economic_qualification'],'NOT_MET')
        self.assertEqual(current['native_qualification'],'NOT_QUALIFIED')

    def test_recorded_default_matches_code_and_reproduction_command(self):
        import inspect,json
        from decimal import Decimal as D
        from pathlib import Path
        from coinquant import campaign
        from research import rebuild
        current=json.loads((Path(__file__).resolve().parents[1]/'research/spec.json').read_text())
        self.assertEqual(D(current['model']['risk_scale']),D(campaign.PRIMARY_RISK))
        basis=current['current_session_replay']['accepted_basis']['mark_gap_policy']
        self.assertEqual(inspect.signature(rebuild.trial).parameters['mark_gap'].default,basis)

    def test_authorized_exact_boundaries(self):
        frozen = spec()
        self.assertTrue(economic_limits('1.5', '0.499999999999999999', frozen))
        self.assertFalse(economic_limits('1.499999999999999999', '0.1', frozen))
        self.assertFalse(economic_limits('2', '0.5', frozen))
