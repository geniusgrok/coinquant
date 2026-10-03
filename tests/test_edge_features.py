from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from research import edge_features as edge


def row(name, observation, value, cause=None):
    result = {'observation_ms': observation,
              'available_ms': observation + (edge.FUNDING_LAG if name == 'funding' else edge.BASIS_LAG),
              'value': value}
    if cause is not None:
        result['cause'] = cause
    return result


def artifact(funding=None, basis=None):
    a = {'format': 'edge-features-v1', 'funding': funding or [], 'basis': basis or [],
         'source': {'raw_sha256': edge.RAW_SHA256,
                    'market_identities': {key: 'a' * 64 for key in edge.MARKET_HASH_FIELDS},
                    'availability_assumptions': deepcopy(edge.ASSUMPTIONS)},
         'coverage': {'window': [edge.START_MS, edge.END_MS], 'end_exclusive': True}}
    return seal(a)


def seal(a):
    for name in ('funding', 'basis'):
        a['coverage'][name] = edge._coverage(a[name], name)
    a['content_sha256'] = edge._hash(edge._canonical({k: v for k, v in a.items() if k != 'content_sha256'}))
    return a


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'features.json'

    def book(self, a, reseal=False):
        if reseal:
            seal(a)
        self.path.write_bytes(edge._canonical(a) + b'\n')
        return edge.FeatureBook(self.path)

    def valid(self):
        return artifact([row('funding', edge.START_MS, '-.0002')],
                        [row('basis', edge.START_MS, '.011')])

    def test_funding_before_at_and_exact_expiry_with_negative_rate(self):
        book = self.book(self.valid())
        available = edge.START_MS + edge.FUNDING_LAG
        self.assertIsNone(book.value('funding', available - 1))
        self.assertEqual(book.last_lookup['cause'], 'not_yet_available')
        self.assertEqual(book.value('funding', available), Decimal('-.0002'))
        self.assertEqual(book.value('funding', available + edge.FUNDING_LAG - 1), Decimal('-.0002'))
        self.assertIsNone(book.value('funding', available + edge.FUNDING_LAG))
        self.assertEqual(book.last_lookup['cause'], 'stale_funding')
        self.assertEqual(book.last_lookup['age_ms'], edge.FUNDING_LAG)

    def test_settlement_jitter_is_not_repaired_or_tolerated(self):
        a = artifact([row('funding', edge.START_MS, '.0001'),
                      row('funding', edge.START_MS + edge.FUNDING_LAG + 3, '-.0004')])
        book = self.book(a)
        expiry = edge.START_MS + 2 * edge.FUNDING_LAG
        for stamp in range(expiry, expiry + 3):
            self.assertIsNone(book.value('funding', stamp))
            self.assertEqual(book.last_lookup['cause'], 'stale_funding')
        self.assertEqual(book.value('funding', expiry + 3), Decimal('-.0004'))
        self.assertEqual(book.last_lookup['observation_ms'], edge.START_MS + edge.FUNDING_LAG + 3)

    def test_basis_before_at_and_current_utc_availability_date(self):
        book = self.book(self.valid())
        self.assertIsNone(book.value('basis', edge.START_MS + 59999))
        self.assertEqual(book.value('basis', edge.START_MS + 60000), Decimal('.011'))
        self.assertEqual(book.last_lookup['observation_ms'], edge.START_MS)
        self.assertEqual(book.value('basis', edge.START_MS + edge.DAY - 1), Decimal('.011'))
        self.assertIsNone(book.value('basis', edge.START_MS + edge.DAY))
        self.assertEqual(book.last_lookup['cause'], 'basis_availability_date_mismatch')
        self.assertIsNone(book.value('basis', edge.START_MS + edge.DAY + 60001))
        self.assertEqual(book.last_lookup['cause'], 'stale_basis')

    def test_missing_day_is_explicit_and_cannot_carry_yesterdays_basis(self):
        a = artifact(basis=[row('basis', edge.START_MS, '.01'),
                            row('basis', edge.START_MS + edge.DAY, None, 'no_matched_trade_close'),
                            row('basis', edge.START_MS + 2 * edge.DAY, '-.02')])
        book = self.book(a)
        stamp = edge.START_MS + edge.DAY + 60000
        self.assertIsNone(book.value('basis', stamp))
        self.assertEqual(book.last_lookup['cause'], 'no_matched_trade_close')
        self.assertEqual(book.value('basis', stamp + edge.DAY), Decimal('-.02'))

    def test_empty_features_are_missing_never_zero(self):
        book = self.book(artifact())
        for name in ('funding', 'basis'):
            self.assertIsNone(book.value(name, edge.START_MS))
            self.assertEqual(book.last_lookup['cause'], 'not_yet_available')

    def test_frozen_window_blocks_valid_tail_and_before_window(self):
        a = artifact([row('funding', edge.START_MS - edge.FUNDING_LAG, '.01'),
                      row('funding', edge.END_MS - edge.FUNDING_LAG, '.02')],
                     [row('basis', edge.END_MS, '.03')])
        book = self.book(a)
        self.assertEqual(book.value('funding', edge.START_MS), Decimal('.01'))
        for name in ('funding', 'basis'):
            for stamp in (edge.START_MS - 1, edge.END_MS, edge.END_MS + edge.DAY):
                self.assertIsNone(book.value(name, stamp))
                self.assertEqual(book.last_lookup['cause'], 'outside_frozen_window')

    def test_future_tail_perturbation_cannot_change_prior_decisions(self):
        a = self.valid()
        a['funding'].append(row('funding', edge.START_MS + edge.DAY, '.04'))
        a['basis'].append(row('basis', edge.START_MS + edge.DAY, '.05'))
        b = deepcopy(a)
        b['funding'][1]['value'] = '-999.1'
        b['basis'][1]['value'] = '999.2'
        b['funding'].append(row('funding', edge.END_MS + edge.DAY, '.07'))
        first = self.book(a, True)
        second = self.book(b, True)
        for stamp in (edge.START_MS, edge.START_MS + 60000, edge.START_MS + edge.FUNDING_LAG,
                      edge.START_MS + 2 * edge.FUNDING_LAG, edge.START_MS + edge.DAY):
            for name in ('funding', 'basis'):
                self.assertEqual(first.value(name, stamp), second.value(name, stamp))
                for key in ('observation_ms', 'available_ms', 'value', 'cause', 'age_ms'):
                    self.assertEqual(first.last_lookup[key], second.last_lookup[key])

    def test_file_content_and_source_identity_checks(self):
        book = self.book(self.valid())
        self.assertEqual(edge.FeatureBook(self.path, book.sha256).sha256, book.sha256)
        with self.assertRaisesRegex(ValueError, 'file hash'):
            edge.FeatureBook(self.path, 'b' * 64)
        for mutate in (lambda a: a.update(format='future-v2'),
                       lambda a: a['source'].update(raw_sha256='b' * 64),
                       lambda a: a['source']['availability_assumptions'].update(funding_stale_age_gte_ms=1),
                       lambda a: a['source']['market_identities'].pop('warmup_trade_sha256'),
                       lambda a: a['source']['market_identities'].update(spot_daily_sha256='bad')):
            a = self.valid(); mutate(a)
            with self.assertRaises(ValueError):
                self.book(a, True)
        a = self.valid(); a['basis'][0]['value'] = '.012'
        with self.assertRaisesRegex(ValueError, 'content hash'):
            self.book(a)

    def test_invalid_time_lag_boundary_and_order_records(self):
        for name in ('funding', 'basis'):
            for field, value in [('observation_ms', True), ('available_ms', -1),
                                 ('observation_ms', 1.5), ('available_ms', '123'),
                                 ('available_ms', edge.START_MS + 1)]:
                a = self.valid(); a[name][0][field] = value
                a['content_sha256'] = edge._hash(edge._canonical({k:v for k,v in a.items() if k!='content_sha256'}))
                with self.subTest(name=name, field=field, value=value), self.assertRaises(ValueError):
                    self.book(a)
            a = self.valid(); a[name].append(deepcopy(a[name][0]))
            with self.subTest(name=name, duplicate=True), self.assertRaisesRegex(ValueError, 'sorted'):
                self.book(a, True)
            a = self.valid(); a[name].insert(0, row(name, edge.START_MS + edge.DAY, '.01'))
            with self.subTest(name=name, unsorted=True), self.assertRaisesRegex(ValueError, 'sorted'):
                self.book(a, True)
        a = self.valid(); a['basis'] = [row('basis', edge.START_MS + 1, '.1')]
        with self.assertRaisesRegex(ValueError, 'completion boundary'):
            self.book(a, True)

    def test_invalid_and_nonfinite_decimal_values(self):
        for value in ('NaN', 'Infinity', '-Infinity', 'sNaN', 'not-a-decimal', 0.01, True):
            a = self.valid(); a['funding'][0]['value'] = value
            # Recompute content only: invalid input must reach reader validation, not helper Decimal parsing.
            a['content_sha256'] = edge._hash(edge._canonical({k:v for k,v in a.items() if k!='content_sha256'}))
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.book(a)

    def test_null_requires_cause_and_known_value_cannot_have_one(self):
        for value, cause in [(None, None), (None, ''), (None, 1), ('.01', 'missing')]:
            a = self.valid(); a['funding'] = [row('funding', edge.START_MS, value, cause)]
            with self.subTest(value=value, cause=cause), self.assertRaises(ValueError):
                self.book(a, True)

    def test_duplicate_json_keys_and_nonfinite_json_numbers_reject(self):
        for data in (b'{"format":"edge-features-v1","format":"edge-features-v1"}',
                     b'{"funding":NaN}', b'{"funding":Infinity}', b'{broken', b'\xff'):
            self.path.write_bytes(data)
            with self.subTest(data=data), self.assertRaises(ValueError):
                edge.FeatureBook(self.path)

    def test_invalid_container_shapes_reject(self):
        for mutate in (lambda a: a.update(funding={}), lambda a: a.update(basis=[123]),
                       lambda a: a.update(source=[]), lambda a: a.update(coverage=[])):
            a = self.valid(); mutate(a)
            a['content_sha256'] = edge._hash(edge._canonical({k:v for k,v in a.items() if k!='content_sha256'}))
            with self.assertRaises(ValueError):
                self.book(a)

    def test_coverage_is_recomputed_and_tracks_exact_jitter_gap(self):
        a = artifact([row('funding', edge.START_MS - edge.FUNDING_LAG, '.01'),
                      row('funding', edge.START_MS + 3, '-.02')])
        self.assertEqual(a['coverage']['funding']['missing_intervals_ms'][0],
                         [edge.START_MS + edge.FUNDING_LAG, edge.START_MS + edge.FUNDING_LAG + 3])
        self.assertEqual(a['coverage']['funding']['negative_records'], 1)
        self.assertEqual(a['coverage']['funding']['known_duration_ms'], 2 * edge.FUNDING_LAG)
        self.book(a)
        for mutate in (lambda a: a['coverage'].update(window=[0, edge.END_MS]),
                       lambda a: a['coverage']['funding'].update(known_duration_ms=0)):
            b = deepcopy(a); mutate(b)
            b['content_sha256'] = edge._hash(edge._canonical({k:v for k,v in b.items() if k!='content_sha256'}))
            with self.assertRaisesRegex(ValueError, 'coverage'):
                self.book(b)

    def test_lookup_journal_binds_input_sources_and_missing_cause(self):
        book = self.book(self.valid())
        book.value('funding', edge.START_MS + edge.FUNDING_LAG)
        self.assertEqual(book.last_lookup['artifact_sha256'], hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual(book.last_lookup['raw_sha256'], edge.RAW_SHA256)
        self.assertEqual(set(book.last_lookup['market_identities']), edge.MARKET_HASH_FIELDS)
        self.assertIsNone(book.last_lookup['cause'])
        self.assertEqual(book.last_lookup['value'], '-0.0002')
        self.assertEqual(book.last_lookup['age_ms'], 0)

    def test_invalid_lookup_names_and_times_reject(self):
        book = self.book(self.valid())
        for name, stamp in [('unknown',edge.START_MS),('basis',True),('basis',-1),('funding',1.0)]:
            with self.assertRaises(ValueError):
                book.value(name, stamp)

    def test_registered_rules_are_finite_and_project_bound(self):
        spec = json.loads((Path(__file__).resolve().parents[1] / 'research/edge_spec.json').read_text())
        expected = {'spot': ('atr-stop', ['exit-confirm','stop-budget','crowding-interaction']),
                    'perp': ('incumbent', ['quality-budget','cost-horizon','crowding-interaction'])}
        baseline, candidates = expected[spec['project_kind']]
        self.assertEqual(spec['baseline_candidate'], baseline)
        self.assertEqual(spec['candidate_order'], candidates)
        self.assertEqual([c['name'] for c in spec['candidates']], candidates)
        self.assertEqual(len(spec['stresses']), 4)
        self.assertEqual(spec['features']['raw_sha256'], edge.RAW_SHA256)
        self.assertEqual(spec['features']['funding']['stale_age_gte_ms'], edge.FUNDING_LAG)
        self.assertFalse(spec['research_constraints']['parameter_search'])
        self.assertFalse(spec['research_constraints']['subset_search'])
        self.assertEqual(spec['risk_calibration']['cutoff_ms'], 1640995200000)
        self.assertIn('no outer .01 scale floor', spec['risk_calibration']['scale_range'])
        self.assertEqual(spec['baseline_equality']['groups'][4], 'remaining_original_fields')
        self.assertIn('actual unity baseline', spec['adoption']['risk_only_alternative'])
        if spec['project_kind'] == 'spot':
            self.assertIn('waits until BOTH', spec['candidates'][0]['rule'])
            self.assertIn('preserves original ordinary exit', spec['candidates'][0]['missing'])


if __name__ == '__main__':
    unittest.main()
