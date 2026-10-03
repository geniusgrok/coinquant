"""Synthetic public bytes only. No native clients, accounts, sleeps or HOME state."""
import base64
import copy
from decimal import Decimal as D
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from research import edge_forward as f


class ForwardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.serial = 0
        self.origin = 1546300800000 if f.KIND == 'spot' else 1575158400000
        self.initial = self.origin + (410 if f.KIND == 'spot' else 210) * f.INTERVAL + 10000
        self.base = 'https://api.binance.com/api/v3/' if f.KIND == 'spot' else 'https://fapi.binance.com/fapi/v1/'
        self.binding = {'export_sha256': 'e' * 64, 'review_sha256': 'a' * 64, 'analysis_sha256': 'b' * 64,
                        'recorded_source': {}, 'current_source': {}, 'bridge': {}}
        self.export = self.root / 'export.json'; self.export.write_bytes(b'fixture')
        self.history = self.root / 'history.json'
        bars = [self.bar(t, '100') for t in range(self.origin, self.initial // f.INTERVAL * f.INTERVAL, f.INTERVAL)]
        if f.KIND == 'spot': bars[-1] = self.bar(bars[-1][0], '99')
        receipt = self.receipt('klines?symbol=BTCUSDT&interval=' + ('1d' if f.KIND == 'spot' else '4h'), bars, self.initial - 1000)
        self.history.write_bytes(f.dump([receipt]))
        self.diary = self.root / 'diary.json'

    def bar(self, start, close):
        price = D(close)
        return [start, str(price), str(price + D('.1')), str(price - D('.1')), str(price), '100',
                start + f.INTERVAL - 1, '10000', 1, '50', '5000', '0']

    def receipt(self, suffix, body, stamp, *, raw=False):
        self.serial += 1
        url = suffix if suffix.startswith('https:') else self.base + suffix
        content = body if raw else f.dump(body)
        path = self.root / f'raw-{self.serial}'
        path.write_bytes(content)
        return dict(category=f.endpoint(url), url=url, path=str(path), sha256=f.sha(content),
                    request_ms=stamp - 10, receipt_ms=stamp)

    def fx(self, stamp):
        day = f.datetime.fromtimestamp(stamp / 1000, f.timezone.utc).date() - f.timedelta(days=1)
        return self.receipt(f.FX_URL, f'observation_date,DEXCHUS\n{day},7\n'.encode(), stamp, raw=True)

    def instrument(self):
        return dict(symbol='BTCUSDT', status='TRADING', baseAsset='BTC', quoteAsset='USDT', marginAsset='USDT', contractType='PERPETUAL',
                    filters=[dict(filterType='LOT_SIZE', stepSize='0.00001', minQty='0.00001', maxQty='1000'),
                             dict(filterType='MARKET_LOT_SIZE', stepSize='0.00001', minQty='0.00001', maxQty='1000'),
                             dict(filterType='PRICE_FILTER', tickSize='0.01', minPrice='0.01', maxPrice='1000000'),
                             dict(filterType='MIN_NOTIONAL', minNotional='5', notional='5')])

    def observations(self, stamp, closes, *, missing=()):
        start = stamp // f.INTERVAL * f.INTERVAL - len(closes) * f.INTERVAL
        rows = [self.bar(start + i * f.INTERVAL, c) for i, c in enumerate(closes)]
        price = D(closes[-1]); at = stamp - 100
        result = [self.receipt('klines?symbol=BTCUSDT&interval=' + ('1d' if f.KIND == 'spot' else '4h'), rows, at), self.fx(at)]
        bodies = [('depth?symbol=BTCUSDT', dict(lastUpdateId=1, bids=[[str(price - D('.01')), '100']], asks=[[str(price + D('.01')), '100']])),
                  ('aggTrades?symbol=BTCUSDT', [dict(a=100, p=str(price), q='100', T=at - 20)]),
                  ('exchangeInfo', dict(symbols=[self.instrument()]))]
        if f.KIND == 'perp':
            bodies += [('premiumIndex?symbol=BTCUSDT', dict(symbol='BTCUSDT', markPrice=str(price), time=at)),
                       ('fundingRate?symbol=BTCUSDT', [])]
        result.extend(self.receipt(url, body, at) for url, body in bodies if f.endpoint(self.base + url) not in missing)
        return result

    def initialize(self):
        fx = self.fx(self.initial + 1)
        with patch.object(f, 'validate_export', return_value=(self.binding, b'fixture')), patch.object(f, 'now_ms', side_effect=[self.initial, self.initial + 2]), patch.object(f, 'acquire', return_value=fx):
            return f.initialize(self.diary, self.export, 'e' * 64, 'a' * 64, self.history)

    def observe(self, stamp, closes, **kwargs):
        receipts = self.observations(stamp, closes, missing=kwargs.pop('missing', ()))
        with patch.object(f, 'validate_export', return_value=(self.binding, b'fixture')), patch.object(f, 'now_ms', side_effect=[stamp - 200, stamp, stamp + 1]), patch.object(f, 'acquire', side_effect=receipts):
            return f.observe(self.diary, self.export, 'e' * 64, 'a' * 64, [r['url'] for r in receipts], **kwargs)

    def test_strict_json_numbers_and_duplicate_keys(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'{"a":1e999}'):
            with self.assertRaises(ValueError): f.strict(raw)
        for value in ('NaN', 'Infinity', True):
            with self.assertRaises(ValueError): f.number(value)

    def test_initialization_is_actual_cold_start_and_exclusive(self):
        state = self.initialize()
        self.assertEqual(state['initialized_ms'], self.initial)
        self.assertEqual(state['btc'], '0'); self.assertEqual(state['events'], [])
        self.assertEqual(state['initial_cny'], '10000')
        self.assertEqual(state['qualification'], 'NOT_QUALIFIED')
        self.assertTrue(f.audit(state))
        before = self.diary.read_bytes()
        with self.assertRaises(ValueError): self.initialize()
        self.assertEqual(before, self.diary.read_bytes())

    def test_receipt_url_future_boundary_and_raw_tamper(self):
        for url in ('https://evil.example/api/v3/depth?symbol=BTCUSDT', self.base + 'account', self.base + 'depth?symbol=ETHUSDT', self.base + 'depth?symbol=BTCUSDT&timestamp=1'):
            with self.assertRaises(ValueError): f.endpoint(url)
        r = self.receipt('klines?symbol=BTCUSDT&interval=' + ('1d' if f.KIND == 'spot' else '4h'), [self.bar(self.origin, '100')], self.origin + f.INTERVAL - 1)
        with self.assertRaises(ValueError): f.bars_from([r], self.origin + f.INTERVAL)
        Path(r['path']).write_bytes(b'[]')
        with self.assertRaises(ValueError): f.payload(r)

    def test_actual_acquisition_stamps_retained_bytes_and_rejects_redirect(self):
        class Response(io.BytesIO):
            def geturl(inner): return self.base + 'depth?symbol=BTCUSDT'
        with patch.object(f, 'urlopen', return_value=Response(b'{"lastUpdateId":1}')), patch.object(f, 'now_ms', side_effect=[100, 105]):
            r = f.acquire(self.base + 'depth?symbol=BTCUSDT', self.root / 'observations')
        self.assertEqual((r['request_ms'], r['receipt_ms']), (100, 105))
        self.assertEqual(f.payload(r), b'{"lastUpdateId":1}')

    def test_backfill_duplicate_future_and_gap_rejections_leave_bytes_unchanged(self):
        self.initialize(); before = self.diary.read_bytes()
        with self.assertRaises(ValueError): self.observe(self.initial + 1000, ['100'])
        self.assertEqual(before, self.diary.read_bytes())
        with self.assertRaises(ValueError): self.observe(self.initial + 2 * f.INTERVAL, ['100', '100'])
        self.assertEqual(before, self.diary.read_bytes())
        state = self.observe(self.initial + 2 * f.INTERVAL, ['100', '100'], declared_gap=True)
        self.assertEqual(state['events'][0]['skipped_intervals'], 1)
        self.assertTrue(f.audit(state))
        before = self.diary.read_bytes()
        with self.assertRaises(ValueError): self.observe(self.initial + 2 * f.INTERVAL, ['100'])
        self.assertEqual(before, self.diary.read_bytes())

    def enter(self):
        self.initialize()
        if f.KIND == 'spot':
            first = self.observe(self.initial + f.INTERVAL, ['110'])
            self.assertEqual(first['btc'], '0')
            return self.observe(self.initial + 2 * f.INTERVAL, ['112'])
        return self.observe(self.initial + f.INTERVAL, ['112'])

    def test_proposal_modeled_fill_fee_net_conservation_and_checkpoint(self):
        state = self.enter()
        self.assertGreater(D(state['btc']), 0)
        self.assertGreater(D(state['fees']), 0)
        event = state['events'][-1]
        self.assertEqual(event['money'][0]['kind'], 'buy')
        self.assertTrue(event['money'][0]['modeled'])
        self.assertGreater(D(event['money'][0]['price']), D('112'))
        self.assertEqual(D(event['net_pnl_cny']), D(event['equity_cny']) - 10000)
        self.assertTrue(f.audit(state))
        mutated = copy.deepcopy(state)
        mutated['wallet'] = str(D(mutated['wallet']) + 1)
        with self.assertRaises(ValueError): f.audit(f.seal(mutated))
        mutated = copy.deepcopy(state)
        if f.KIND == 'spot': next(iter(mutated['engine']['positions'].values()))['stop'] = '1'
        else: mutated['engine']['committed_target']['quantity'] = '999'
        with self.assertRaises(ValueError): f.audit(f.seal(mutated))

    def test_missing_executable_depth_blocks_new_risk(self):
        self.initialize()
        if f.KIND == 'spot': self.observe(self.initial + f.INTERVAL, ['110'])
        state = self.observe(self.initial + (2 if f.KIND == 'spot' else 1) * f.INTERVAL, ['112'], missing=('depth',))
        self.assertEqual(D(state['btc']), 0)
        self.assertEqual(state['events'][-1]['money'], [])
        self.assertIn('depth', state['events'][-1]['missing'])

    def test_protective_ohlc_is_unknown_not_a_fabricated_stop_fill(self):
        state = self.enter(); owned = state['btc']
        stamp = self.initial + (3 if f.KIND == 'spot' else 2) * f.INTERVAL
        state = self.observe(stamp, ['80'])
        self.assertEqual(state['btc'], owned)
        self.assertIn('protective_path_ambiguous_OHLC_no_exact_fill', state['unresolved'])
        self.assertFalse(state['events'][-1]['performance_qualified'])
        self.assertFalse(any(v['kind'] == 'sell' for v in state['events'][-1]['money']))
        self.assertTrue(f.audit(state))

    def test_size_minimum_rounding_depth_and_no_topup(self):
        instrument = self.instrument()
        self.assertEqual(f.quantity_limit(D('.001'), D(100), instrument), 0)
        self.assertEqual(f.quantity_limit(D('1.123456'), D(100), instrument), D('1.12345'))
        qty, price = f.execution(dict(asks=[['100', '1'], ['101', '1']]), 'BUY', D(3))
        self.assertEqual(qty, 2); self.assertEqual(price, D(101) * (1 + f.SLIP))
        state = self.enter(); owned = state['btc']
        state = self.observe(self.initial + (3 if f.KIND == 'spot' else 2) * f.INTERVAL, ['112'])
        self.assertEqual(state['btc'], owned)
        self.assertFalse(any(v['kind'] == 'buy' for v in state['events'][-1]['money']))

    def test_stale_and_nonfinite_book_rejected(self):
        receipts = self.observations(self.initial, ['100'])
        with self.assertRaises(ValueError): f.book_from(receipts, self.initial + f.MAX_AGE)
        depth = next(r for r in receipts if r['category'] == 'depth')
        raw = f.dump(dict(lastUpdateId=1, bids=[['NaN', '1']], asks=[['101', '1']]))
        Path(depth['path']).write_bytes(raw); depth['sha256'] = f.sha(raw)
        with self.assertRaises(ValueError): f.book_from(receipts, self.initial)

    def test_atomic_failure_preserves_original_and_source_change_blocks(self):
        self.initialize(); before = self.diary.read_bytes()
        with patch.object(f, 'replace_file', side_effect=OSError('synthetic pre-replace failure')):
            with self.assertRaises(OSError): self.observe(self.initial + f.INTERVAL, ['100'])
        self.assertEqual(before, self.diary.read_bytes())
        with patch.object(f, 'validate_export', side_effect=ValueError('source changed')):
            with self.assertRaises(ValueError): f.observe(self.diary, self.export, 'e' * 64, 'a' * 64, [])
        self.assertEqual(before, self.diary.read_bytes())

    @unittest.skipUnless(f.KIND == 'perp', 'perpetual-only settlement accounting')
    def test_funding_sign_no_past_cashflows_and_missing_is_not_zero(self):
        stamp = (self.initial // 28800000 + 1) * 28800000
        state = dict(initialized_ms=self.initial, events=[], btc='2')
        r = self.receipt('fundingRate?symbol=BTCUSDT', [dict(symbol='BTCUSDT', fundingTime=stamp, fundingRate='-.001', markPrice='100')], stamp + 10)
        events, causes = f.funding_entries(state, [r], stamp + 20)
        self.assertEqual(events[0]['cost'], '-0.200'); self.assertEqual(causes, [])
        state['btc'] = '0'
        self.assertEqual(f.funding_entries(state, [r], stamp + 20)[0], [])
        state['btc'] = '2'
        self.assertIn('missing_settled_funding_coverage', f.funding_entries(state, [], stamp + 20)[1])
        state['initialized_ms'] = stamp + 1
        self.assertEqual(f.funding_entries(state, [r], stamp + 20)[0], [])

    @unittest.skipUnless(f.KIND == 'spot', 'trade-triggered spot stops only')
    def test_complete_public_print_path_models_protection_with_exact_source(self):
        state = self.enter()
        stamp = self.initial + 3 * f.INTERVAL
        receipts = self.observations(stamp, ['80'])
        receipt = next(r for r in receipts if r['category'] == 'trades')
        raw = f.dump([dict(a=101, p='80', q='100', T=stamp - 120)])
        Path(receipt['path']).write_bytes(raw); receipt['sha256'] = f.sha(raw)
        with patch.object(f, 'validate_export', return_value=(self.binding, b'fixture')), patch.object(f, 'now_ms', side_effect=[stamp - 200, stamp, stamp + 1]), patch.object(f, 'acquire', side_effect=receipts):
            result = f.observe(self.diary, self.export, 'e' * 64, 'a' * 64, [r['url'] for r in receipts])
        self.assertEqual(D(result['btc']), 0)
        fills = result['events'][-1]['money']
        self.assertTrue(fills and all(v['passive'] for v in fills))
        self.assertTrue(all(v['time'] == stamp - 120 and receipt['sha256'] in v['source_sha256'] for v in fills))
        self.assertTrue(f.audit(result))

    @unittest.skipUnless(f.KIND == 'perp', 'perpetual protection preflight')
    def test_coin_unplaceable_protection_rejects_model_size(self):
        self.initialize(); stamp = self.initial + f.INTERVAL
        receipts = self.observations(stamp, ['112'])
        receipt = next(r for r in receipts if r['category'] == 'instrument')
        body = f.strict(f.payload(receipt))
        next(v for v in body['symbols'][0]['filters'] if v['filterType'] == 'PRICE_FILTER')['maxPrice'] = '113'
        raw = f.dump(body); Path(receipt['path']).write_bytes(raw); receipt['sha256'] = f.sha(raw)
        with patch.object(f, 'validate_export', return_value=(self.binding, b'fixture')), patch.object(f, 'now_ms', side_effect=[stamp - 200, stamp, stamp + 1]), patch.object(f, 'acquire', side_effect=receipts):
            state = f.observe(self.diary, self.export, 'e' * 64, 'a' * 64, [r['url'] for r in receipts])
        self.assertEqual(D(state['btc']), 0)
        self.assertEqual(state['events'][-1]['simulated'][0]['reason'], 'instrument_protection_price_bounds')

    @unittest.skipUnless(f.KIND == 'perp', 'ALFRED macro source')
    def test_raw_alfred_vintage_parsing_and_future_rejection(self):
        stamp = 1580601600000
        dates = [f.date(2020, 1, 1) + f.timedelta(days=i) for i in range(29)]
        form = ('<select id="form_selected_vintage_dates">' + ''.join('<option value="' + str(v) + '">' for v in dates) + '</select>').encode()
        form_path = self.root / 'alfred.html'; form_path.write_bytes(form)
        out = io.StringIO(); writer = f.csv.writer(out)
        writer.writerow(['observation_date'] + [v.strftime('DFII10_%Y%m%d') for v in dates])
        for i in range(21):
            observed = f.date(2020, 1, 8) + f.timedelta(days=i)
            writer.writerow([str(observed)] + [''] * 28 + [str(D('2') - D(i) / 40)])
        archive = io.BytesIO()
        with ZipFile(archive, 'w') as z: z.writestr('DFII10.csv', out.getvalue())
        receipt = self.receipt(f.DFII_URL, archive.getvalue(), stamp - 1, raw=True)
        receipt.update(form_path=str(form_path), form_sha256=f.sha(form), vintages=[str(v) for v in dates])
        row = f.dfii_from(receipt, stamp)
        self.assertEqual(row['latest_value'], '1.5'); self.assertEqual(row['prior20_value'], '2')
        from coinquant.dfii10 import eligible
        self.assertTrue(eligible(row, stamp))
        receipt['vintages'][-1] = '2020-02-02'
        with self.assertRaises(ValueError): f.dfii_from(receipt, stamp)

    def test_recomputed_checkpoint_tamper_and_missing_raw_are_rejected(self):
        state = self.initialize()
        changed = copy.deepcopy(state)
        if f.KIND == 'spot':
            changed['engine']['models']['30']['body']['need_reset'] = True
        else:
            changed['engine']['campaign']['body']['primary_consumed'] = self.initial
        with self.assertRaises(Exception): f.audit(f.seal(changed))
        receipt = state['initial_receipts'][0]
        Path(receipt['path']).unlink()
        with self.assertRaises(FileNotFoundError): f.audit(state)



class SourceAndExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        (self.repo / f.PACKAGE).mkdir(); (self.repo / 'research').mkdir()
        (self.repo / f.PACKAGE / 'rule.py').write_text('RULE = 1\n')
        for name in ('edge_spec.json', 'edge-PROTOCOL.md'): (self.repo / 'research' / name).write_text(name)
        self.git('init', '-q'); self.git('config', 'user.name', 'Synthetic'); self.git('config', 'user.email', 'synthetic@example.invalid')
        self.commit()

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.repo, check=True, capture_output=True).stdout

    def commit(self):
        self.git('add', '.'); self.git('commit', '-qm', 'synthetic fixture')

    def test_archive_metadata_equivalence_actual_protected_byte_rejection(self):
        recorded = f.source(self.repo)
        (self.repo / 'NOTES.md').write_text('metadata only\n'); self.commit()
        (self.repo / 'evidence').mkdir()
        (self.repo / 'evidence' / 'review.json').write_text('{}')
        (self.repo / 'evidence' / 'independent_proof.py').write_text('print(1)\n')
        (self.repo / 'research' / 'GUIDE.md').write_text('inert prose\n')
        self.commit()
        current = f.source(self.repo)
        self.assertNotEqual(recorded['git_head'], current['git_head'])
        f.assert_equivalent(recorded, current, self.repo)
        (self.repo / f.PACKAGE / 'rule.py').write_text('RULE = 2\n')
        with self.assertRaises(ValueError): f.source(self.repo)
        self.commit()
        with self.assertRaises(ValueError): f.assert_equivalent(recorded, f.source(self.repo), self.repo)

    def test_executable_configuration_and_protocol_are_protected(self):
        recorded = f.source(self.repo)
        (self.repo / 'config.example.json').write_text('{}')
        self.commit()
        with self.assertRaises(ValueError): f.assert_equivalent(recorded, f.source(self.repo), self.repo)
        recorded = f.source(self.repo)
        (self.repo / 'research' / 'edge-PROTOCOL.md').write_text('changed rule')
        self.commit()
        with self.assertRaises(ValueError): f.assert_equivalent(recorded, f.source(self.repo), self.repo)

    def export(self):
        source = f.source(self.repo)
        report = dict(phase='final', status='complete_reviewed', pending=[], blocking=[],
                      selected={f.KIND: f.BASE[f.KIND]}, accounts={'account': dict(status='complete', source={'measured': True}, raw_sha256='r' * 64, components=[], reasons=[])},
                      contracts={f.KIND: dict(spec_sha256=source['protected_files']['research/edge_spec.json'], protocol_sha256=source['protected_files']['research/edge-PROTOCOL.md'])})
        for field in ('inputs', 'analysis_source', 'portfolios', 'input_envelopes', 'calibration_input_documents', 'calibration_diagnostics',
                      'environment', 'combinations', 'calibration_documents', 'decisions', 'baseline_equality'): report[field] = {}
        report['required_accounts'] = ['account']
        ihash = f.sha(json.dumps(f.inventory(report), sort_keys=True).encode())
        report['inventory_sha256'] = ihash
        prior = dict(report, phase='preliminary', status='complete_pending_independent_review')
        prior_raw = f.dump(prior)
        record = dict(id='synthetic', raw_bindings={'original': 'b' * 64}, values={'mdd': '.30000000000000001'}, matches=True)
        expected = {k: {'synthetic': record} for k in f.CATEGORIES}
        checks, artifacts = {}, {}
        for category in f.CATEGORIES:
            raw = f.dump(dict(category=category, inventory_sha256=ihash, recomputations=[record]))
            checks[category] = dict(passed=True, artifact=dict(path=category, sha256=f.sha(raw)))
            artifacts[category] = base64.b64encode(raw).decode()
        proof = f.dump(dict(format='btc-edge-financial-review-v1', inventory_sha256=ihash, checks=checks,
                            preliminary=dict(path='prior.json', sha256=f.sha(prior_raw)), reviewer_source=source))
        report['financial_review'] = {'sha256': f.sha(proof)}
        bridge = dict(candidate=f.BASE[f.KIND], adapter=f.ADAPTER, components=[], scale='1', source=source, account_id='account',
                      measured_source={'measured': True}, raw_sha256='r' * 64, canonical_review_sha256='c' * 64, original_accepted_result_sha256=['o' * 64])
        canonical_raw = f.dump(dict(format='btc-edge-canonical-forward-bridge-v1', status='independently_reviewed', project=f.KIND, bridge=bridge))
        bridge['canonical_review'] = dict(path='canonical.json', sha256=f.sha(canonical_raw))
        raw, braw = f.dump(report), f.dump({f.KIND: bridge})
        return dict(format='btc-edge-forward-export-v1', analysis_raw=base64.b64encode(raw).decode(), analysis_sha256=f.sha(raw),
                    review_raw=base64.b64encode(proof).decode(), review_sha256=f.sha(proof), bridges_raw=base64.b64encode(braw).decode(), bridges_sha256=f.sha(braw),
                    expected=expected, artifacts=artifacts, preliminary_raw=base64.b64encode(prior_raw).decode(),
                    canonical_reviews={f.KIND: base64.b64encode(canonical_raw).decode()})

    def verify(self, body):
        # Fixture is outside repo to preserve a clean source checkout.
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'export.json'; raw = f.dump(body); p.write_bytes(raw)
            return f.validate_export(p, f.sha(raw), body['review_sha256'], root=self.repo)

    def test_frozen_proof_exact_categories_records_and_adapter(self):
        body = self.export(); self.assertEqual(self.verify(body)[0]['bridge']['scale'], '1')
        bad = copy.deepcopy(body); del bad['artifacts']['adoption_gates']
        with self.assertRaises(ValueError): self.verify(bad)
        bad = copy.deepcopy(body); bad['expected']['original_accounting']['synthetic']['values']['mdd'] = '.30'
        with self.assertRaises(ValueError): self.verify(bad)
        bad = copy.deepcopy(body); bridge = f.strict(f.decode(bad['bridges_raw'])); bridge[f.KIND]['candidate'] = 'unreviewed'
        raw = f.dump(bridge); bad.update(bridges_raw=base64.b64encode(raw).decode(), bridges_sha256=f.sha(raw))
        with self.assertRaises(ValueError): self.verify(bad)
        bad = copy.deepcopy(body); bad['review_sha256'] = '0' * 64
        with self.assertRaises(ValueError): self.verify(bad)


if __name__ == '__main__':
    unittest.main()
