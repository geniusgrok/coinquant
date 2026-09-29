import inspect
import json
import unittest
from decimal import Decimal as D
from pathlib import Path

from coinquant import campaign
from research import rebuild, session_schedule

ROOT = Path(__file__).resolve().parents[1]


def targets_met(spec, cagr, mdd):
    return D(cagr) >= D(spec['cagr_minimum_inclusive']) and 0 <= D(mdd) < D(spec['mdd_maximum_exclusive'])


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads((ROOT / 'research/spec.json').read_text())

    def test_contract_identity_and_gates(self):
        spec = self.spec
        self.assertEqual((spec['venue'], spec['symbol'], spec['leverage']), ('binance', 'BTCUSDT', 20))
        self.assertEqual((spec['start'], spec['end'], spec['initial_cny']),
                         ('2020-01-01T00:00:00Z', '2026-09-20T00:00:00Z', '10000'))
        self.assertEqual(spec['economic_qualification'], 'NOT_MET')
        self.assertEqual(spec['native_qualification'], 'NOT_QUALIFIED')

    def test_recorded_default_matches_code_and_reproduction_command(self):
        replay = self.spec['current_session_replay']
        self.assertEqual(D(self.spec['model']['risk_scale']), D(campaign.PRIMARY_RISK))
        self.assertEqual(inspect.signature(rebuild.trial).parameters['mark_gap'].default,
                         replay['accepted_basis']['mark_gap_policy'])
        self.assertEqual(session_schedule.load()['primary']['sha256'], replay['schedule_sha256'])
        for entry in [replay['accepted_basis']['result'], *replay['accepted_basis']['stresses'].values()]:
            self.assertTrue((ROOT / entry['evidence']).exists(), entry['evidence'])

    def test_recorded_numbers_are_the_ones_in_their_evidence_files(self):
        replay = self.spec['current_session_replay']
        entries = [replay['accepted_basis']['result'], *replay['accepted_basis']['stresses'].values()]
        if 'current_code_regression' in replay:
            entries.append(replay['current_code_regression'])
        for entry in entries:
            measured = json.loads((ROOT / entry['evidence']).read_text())
            self.assertEqual(str(round(D(measured['final_cny']))), entry['final_cny'], entry['evidence'])
            self.assertEqual(f"{D(measured['cagr']) * 100:.2f}", entry['cost_net_cagr_percent'], entry['evidence'])
            self.assertEqual(f"{D(measured['mdd_envelope']) * 100:.2f}", entry['continuous_mdd_envelope_percent'],
                             entry['evidence'])

    def test_exact_target_boundaries(self):
        self.assertTrue(targets_met(self.spec, '1.5', '0.499999999999999999'))
        self.assertFalse(targets_met(self.spec, '1.499999999999999999', '0.1'))
        self.assertFalse(targets_met(self.spec, '2', '0.5'))


if __name__ == '__main__':
    unittest.main()
