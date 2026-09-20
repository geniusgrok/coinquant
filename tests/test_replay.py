"""Small synthetic mechanics fixtures. No historical economic evidence."""
import csv
from dataclasses import replace
from decimal import Decimal as D
import gzip
import json
from pathlib import Path
import tempfile
import unittest

from pancakequant.data import Dataset, HOUR, MINUTE
from pancakequant.replay import Account, _replay
from pancakequant.research import digest, invocations, iso, spec, timestamp
from pancakequant.types import Blocked, ModelConfig
from test_model import sample


def dataset_fixture(path, *, missing_funding=False, interval=MINUTE):
    frozen = spec()
    start = timestamp(frozen['start'])
    end = start + 48 * 3_600_000
    frozen['end'] = iso(end)
    frozen['gap_hours'] = [19, 31]  # TEST-ONLY; production spec is unchanged
    frozen['bar_interval_ms'] = interval  # synthetic mechanics fixture only
    frozen['liquidity_activity_basis_ms'] = MINUTE
    warmup = start - 3 * 14_400_000
    m = dict(venue='bybit', symbol='BTCUSD', contract_type='InversePerpetual', settlement_coin='BTC',
             start=iso(start), end=iso(end), warmup_start=iso(warmup), provenance='synthetic', bar_interval_ms=interval, files={})
    with gzip.open(path / 'bars.csv.gz', 'wt', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['time', 'open', 'high', 'low', 'close', 'volume', 'mark_open', 'mark_high', 'mark_low', 'mark_close'])
        for i, t in enumerate(range(warmup, end, interval)):
            p = D(20000) + D(i) / 5
            writer.writerow([t, p, p + D('.1'), p - D('.1'), p + D('.05'), 1000000,
                             p, p + D('.1'), p - D('.1'), p + D('.05')])
    with open(path / 'funding.csv', 'w', newline='') as stream:
        writer = csv.writer(stream); writer.writerow(['time', 'rate', 'mark'])
        for t in range(start, end, 8 * 3_600_000):
            if not missing_funding or t != start:
                writer.writerow([t, '.0001', 20000])
    with open(path / 'rules.csv', 'w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['time', 'launch_ms', 'funding_interval_ms', 'tick', 'step', 'minimum', 'maximum',
                         'market_maximum', 'risk_limit_btc', 'maintenance_rate', 'taker_fee', 'liquidation_fee'])
        writer.writerow([warmup, warmup, 8 * 3_600_000, '.5', 1, 1, 1000000, 1000000, 150, '.005', '.00075', '.005'])
    for key, filename in [('bars', 'bars.csv.gz'), ('funding', 'funding.csv'), ('rules', 'rules.csv')]:
        p = path / filename
        m['files'][key] = [dict(path=filename, bytes=p.stat().st_size, sha256=digest(p), source='synthetic unit-test fixture, NOT exchange data')]
    manifest = path / 'manifest.json'; manifest.write_text(json.dumps(m))
    return manifest, frozen


class ReplayTests(unittest.TestCase):
    def test_fixed_schedule_and_absence_are_market_independent(self):
        frozen = spec()
        first = list(invocations(frozen))
        self.assertEqual(first, list(invocations(frozen)))
        self.assertEqual(first[0], timestamp('2020-01-01T00:00:00Z'))
        self.assertLess(first[-1], timestamp(frozen['end']))
        self.assertLessEqual(max(b - a for a, b in zip(first, first[1:])), 151 * 3_600_000)
        stressed = list(invocations(frozen, stress=True))
        self.assertTrue(set(stressed).issubset(first))
        self.assertGreater(max(b - a for a, b in zip(stressed, stressed[1:])), 21 * 86_400_000)

    def test_real_cost_and_partial_inverse_position_arithmetic(self):
        r = sample().rules
        a = Account(D('0.1'))
        a.fill(D(1000), D(10000), r, D(12000), D(9800))
        self.assertEqual(a.wallet, D('.1') - D(1000) * r.taker_fee / 10000)
        a.pay_funding(D('.0001'), D(10000), r)
        self.assertEqual(a.funding, D('.00001'))
        before = a.wallet
        a.fill(D(-500), D(11000), r)
        self.assertEqual(a.position.quantity, 500)
        self.assertEqual(a.position.stop_loss, 9800)
        self.assertAlmostEqual(a.wallet, before + D(500) * (D(1) / 10000 - D(1) / 11000) - D(500) * r.taker_fee / 11000)
        a.fill(D(-500), D(11000), r)
        self.assertEqual(a.position.quantity, 0)

    def test_hourly_input_rejects_mid_hour_rule_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            manifest, frozen = dataset_fixture(path, interval=HOUR)
            rules = path / 'rules.csv'
            rows = list(csv.reader(rules.open()))
            rows.append([
                str(timestamp(frozen['start']) + 30 * MINUTE), str(timestamp(frozen['start'])),
                str(8 * HOUR), '.5', '1', '1', '1000000', '1000000',
                '150', '.005', '.00075', '.005'])
            with rules.open('w', newline='') as stream:
                csv.writer(stream).writerows(rows)
            value = json.loads(manifest.read_text())
            value['files']['rules'][0]['bytes'] = rules.stat().st_size
            value['files']['rules'][0]['sha256'] = digest(rules)
            manifest.write_text(json.dumps(value))
            with self.assertRaisesRegex(Blocked, 'not representable'):
                Dataset(manifest, frozen, warmup_bars=3)

    def test_missing_funding_and_bad_hash_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            manifest, frozen = dataset_fixture(path, missing_funding=True)
            with self.assertRaisesRegex(Blocked, 'funding event'):
                Dataset(manifest, frozen, warmup_bars=3)
            manifest, frozen = dataset_fixture(path)
            with open(path / 'funding.csv', 'a') as stream:
                stream.write('corruption')
            with self.assertRaisesRegex(Blocked, 'hash'):
                Dataset(manifest, frozen, warmup_bars=3)

    def test_hourly_base_bars_rebuild_the_same_four_hour_signal_clock(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            manifest, frozen = dataset_fixture(path, interval=HOUR)
            dataset = Dataset(manifest, frozen, warmup_bars=3)
            self.assertEqual(dataset.interval, HOUR)
            output = path / 'hourly-output'; output.mkdir()
            config = replace(ModelConfig(), trend_bars=2, channel_bars=2, atr_bars=2)
            result = _replay(dataset, config, frozen, output)
            self.assertEqual(result['decisions'], len(set(invocations(frozen))))
            with gzip.open(output / 'equity.csv.gz', 'rt') as stream:
                equity = list(csv.DictReader(stream))
            self.assertEqual(int(equity[-1]['time']), timestamp(frozen['end']))

    def test_unsupported_two_hour_base_interval_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            manifest, frozen = dataset_fixture(path, interval=HOUR)
            value = json.loads(manifest.read_text())
            value['bar_interval_ms'] = 2 * HOUR
            manifest.write_text(json.dumps(value))
            with self.assertRaisesRegex(Blocked, 'supported aligned'):
                Dataset(manifest, frozen, warmup_bars=3)

    def test_sparse_replay_and_artifacts_on_synthetic_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            manifest, frozen = dataset_fixture(path)
            dataset = Dataset(manifest, frozen, warmup_bars=3)
            output = path / 'output'; output.mkdir()
            config = replace(ModelConfig(), trend_bars=2, channel_bars=2, atr_bars=2)
            result = _replay(dataset, config, frozen, output)
            expected = set(invocations(frozen))
            self.assertEqual(result['decisions'], len(expected))
            self.assertEqual(result['qualification'], 'NOT_QUALIFIED')
            with gzip.open(output / 'orders.csv.gz', 'rt') as stream:
                records = list(csv.DictReader(stream))
            self.assertTrue(records)
            self.assertTrue(all(int(r['time']) in expected for r in records if r['event'].startswith('manual_')))
            self.assertTrue(all(r['event'] == 'native_exit' for r in records if int(r['time']) not in expected))
            with gzip.open(output / 'equity.csv.gz', 'rt') as stream:
                equity = list(csv.DictReader(stream))
            self.assertAlmostEqual(D(equity[0]['equity_cny']), D(10000), places=18)
            self.assertEqual(int(equity[-1]['time']), timestamp(frozen['end']))
            self.assertIn('intraminute_envelope', {r['event'] for r in equity})
