from collections import deque
import array
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal as D
import gzip
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

from coinquant import campaign, lifecycle, linear_preview, session
from coinquant.campaign import Campaign, ORIGIN
from coinquant.config import Config
from coinquant.opportunities import Opportunity
from coinquant.state import State
from coinquant.types import Blocked
from research import alpha_perp as alpha, complete_perp as meter, edge_perp as edge
from research.edge_prints import VerifiedPrints, digest
from tests.session_venue import Venue

BAR, DAY = edge.BAR, edge.DAY


class Features:
    sha256 = 'a'*64
    source = {}

    def __init__(self, funding='.0001', basis='.001'):
        self.values = {'funding': None if funding is None else D(funding),
                       'basis': None if basis is None else D(basis)}
        self.last_lookup = None

    def value(self, name, now):
        value = self.values[name]
        self.last_lookup = {'name': name, 'now_ms': now, 'value': None if value is None else str(value),
                            'artifact_sha256': self.sha256, 'cause': 'fixture_missing' if value is None else None}
        return value


class EdgeTests(unittest.TestCase):
    def binding(self, offset=0, source='fixture'):
        schedule = edge._load_frozen_schedule()['primary']
        return {'source': source, 'start_offset_ms': offset, 'original_schedule_sha256': schedule['sha256'],
                'actual_starts_sha256': meter.checksum([s+offset for s in schedule['starts_ms']])}

    def variant(self, name='quality-budget', features=None, **kwargs):
        return edge.variant(name, features=features or Features(), binding=self.binding(), **kwargs)

    def warm(self):
        model = edge.EdgeCampaign()
        for i in range(40):
            model.update(ORIGIN+(i+1)*BAR, '101', '99', '100')
        model.update(model.last+BAR, '110', '100', '108')
        model.select_macro(None, '108', model.last+1000)
        model.returns = deque([D('.02')]*20, maxlen=20)
        return model

    def engine(self, model, now=None, allowed=True):
        now = now if now is not None else model.last+1000
        return SimpleNamespace(reader=SimpleNamespace(clock=lambda: now/1000), authorized=True,
            session=now//BAR*BAR, may_enter=lambda: allowed, state=Mock())

    def snapshot(self, model, quantity='1'):
        return {'quantity_btc': quantity, 'mark_price': str(model.model.close)}

    def aged(self, days=5):
        model = edge.EdgeCampaign()
        trigger = edge._load_frozen_schedule()['primary']['starts_ms'][0]-5*DAY
        while model.last < trigger-BAR:
            model.update(model.last+BAR, '101', '99', '100')
        model.update(trigger, '110', '100', '108')
        model.filled(model.active.identity)
        for i in range(days*6):
            close = D(108)+D(i+1)/10
            model.update(model.last+BAR, close+D('.1'), close-D('.1'), close)
        return model

    def seed(self, venue, path, identity, incumbent=False):
        venue.seed(path)
        with State(path, 'binance:BTCUSDT:live:123') as state:
            base = Campaign.restore(state.get('linear_campaign'))
            model = alpha.AlphaCampaign() if incumbent else edge.EdgeCampaign()
            model.__dict__.update(base.__dict__)
            model.model.tr = deque([D(1000)]*14, maxlen=14)
            model.model.close = D(100000)
            model.model.active = replace(model.model.active, expires=model.last+7*DAY)
            model.trigger = {'identity': model.last, 'close': '100000', 'prior_atr': '1000', 'kind': 'impulse', 'direction': 1}
            if not incumbent:
                model.closes = deque([D(99000)]*19+[D(100000)], maxlen=20)
            state.set('linear_campaign', model.checkpoint())
            if identity is not None:
                state.set('edge_identity', identity)

    def run_session(self, venue, path, seconds=8):
        return session.run(Config('123', path, seconds, 1), venue, execute=True,
                           monotonic=venue.monotonic, wait=venue.wait)

    def test_quality_immutable_trigger_mark_and_completed_history_boundaries(self):
        with self.variant():
            model = self.warm()
            trigger = deepcopy(model.trigger)
            full = model.entry_fraction('.0011')
            model.decision_mark = D(107)  # equality with triggerclose-.5 priorATR
            self.assertEqual(model.evaluate()['factor'], '1')
            model.decision_mark -= D('.0001')
            self.assertEqual(model.evaluate()['factor'], '0.5')
            self.assertEqual(model.entry_fraction('.0011'), full/2)
            model.update(model.last+BAR, '109', '106', '108')
            self.assertEqual(model.trigger, trigger)
            model.closes = deque([D(108)]*20, maxlen=20)
            self.assertEqual(model.evaluate()['factor'], '0.5')
            model.closes.pop()
            self.assertTrue(model.evaluate()['blocked_primary_new_risk'])
            self.assertEqual(model.action(D(0)), 'flat')

    def test_momentum_is_six_completed_intervals_and_trend_twenty_bars(self):
        with self.variant('crowding-interaction'):
            model = self.warm()
            model.closes = deque([D(100)]*6, maxlen=20)
            self.assertIsNone(model.signals()['momentum'])
            model.closes.append(D(100))
            self.assertIs(model.signals()['momentum'], False)
            model.closes[-1] = D(101)
            self.assertIs(model.signals()['momentum'], True)
            self.assertIsNone(model.signals()['trend'])
            model.closes = deque([D(100)]*19+[D(101)], maxlen=20)
            self.assertIs(model.signals()['trend'], True)

    def test_crowding_conjunction_equality_missing_and_independence(self):
        features = Features('.0003', '.01')
        with self.variant('crowding-interaction', features):
            model = self.warm();model.closes = deque([D(108)]*20, maxlen=20)
            self.assertEqual(model.evaluate()['factor'], '1')
            features.values['funding'] += D('.0000001')
            self.assertEqual(model.evaluate()['factor'], '1')
            features.values['basis'] += D('.0000001')
            self.assertEqual(model.evaluate()['factor'], '0.5')
            features.values['funding'] = D('-.001')
            self.assertEqual(model.evaluate()['factor'], '1')
            features.values['basis'] = None
            self.assertTrue(model.evaluate()['blocked_primary_new_risk'])
            self.assertEqual(model.action(D(0)), 'flat')
            model.filled(model.active.identity)
            self.assertEqual(model.action(D(1)), 'hold')
            model.model.active = None
            self.assertEqual(model.action(D(1)), 'exit')

    def test_missing_quality_inputs_macro_and_short_are_unchanged(self):
        with self.variant('quality-budget+crowding-interaction', Features(None, None)):
            model = self.warm();model.trigger = None
            model.evaluate();self.assertEqual(model.action(D(0)), 'flat')
            model.model.active = replace(model.model.active, direction=-1)
            model.evaluate();self.assertIsNone(model.active)
            self.assertEqual(model.action(D(0)), 'flat')
            model.macro_opportunity = Opportunity(-model.last, 1, D(90), D(200), None)
            model.evaluate();self.assertEqual(model.action(D(0)), 'enter')
            baseline = Campaign();baseline.__dict__.update(model.__dict__)
            self.assertEqual(model.entry_fraction('.0011'), baseline.entry_fraction('.0011'))

    def test_combo_reductions_multiply_and_components_reject_duplicates(self):
        with self.variant('quality-budget+crowding-interaction', Features('.0004', '.02')):
            model = self.warm();model.closes = deque([D(108)]*20, maxlen=20)
            self.assertEqual(model.evaluate()['factor'], '0.25')
        for name in ('quality-budget+quality-budget', 'cost-horizon+foreign', ''):
            with self.assertRaises(ValueError): edge.components(name)
        self.assertEqual(edge.components('crowding-interaction,cost-horizon'), ('cost-horizon', 'crowding-interaction'))

    def test_cost_exit_requires_actual_legal_decision_original_exits_win(self):
        features = Features('.0004')
        with self.variant('cost-horizon', features):
            model = self.warm();model.filled(model.active.identity)
            model.closes = deque([D(108)]*20, maxlen=20)
            self.assertEqual(model.action(D(1)), 'hold')
            model.prepare_decision(self.engine(model, allowed=False), self.snapshot(model))
            self.assertEqual(model.action(D(1)), 'hold')
            features.values['funding'] = None
            model.prepare_decision(self.engine(model), self.snapshot(model))
            self.assertEqual(model.action(D(1)), 'hold')
            self.assertIn('funding', model.rules['missing'])
            features.values['funding'] = D('.0003')
            model.prepare_decision(self.engine(model), self.snapshot(model))
            self.assertEqual(model.action(D(1)), 'hold')
            features.values['funding'] += D('.0000001')
            model.prepare_decision(self.engine(model), self.snapshot(model))
            self.assertEqual(model.action(D(1)), 'exit')
            model.cost_exit = False;model.model.active = None;features.values['funding'] = None
            model.prepare_decision(self.engine(model), self.snapshot(model))
            self.assertEqual(model.action(D(1)), 'exit')

    def test_macro_cost_exit_has_no_primary_extension(self):
        with self.variant('cost-horizon', Features('.0004')):
            model = self.warm();model.model.active = None
            model.macro_opportunity = Opportunity(-model.last, 1, D(90), D(200), None)
            model.macro_epoch = -model.last;model.filled(-model.last)
            model.closes = deque([D(108)]*20, maxlen=20)
            model.prepare_decision(self.engine(model), self.snapshot(model))
            self.assertEqual(model.action(D(1)), 'exit')
            self.assertIsNone(model.extension)

    def test_extension_only_actual_five_to_seven_days_once_and_protection_unchanged(self):
        with self.variant('cost-horizon', Features('.0003'), journal=(journal := [])):
            model = self.aged()
            original = model.active
            self.assertIsNone(model.extension)
            model.prepare_decision(self.engine(model, original.identity+5*DAY-1), self.snapshot(model))
            self.assertIsNone(model.extension)
            model.prepare_decision(self.engine(model, original.identity+5*DAY), self.snapshot(model))
            self.assertEqual(model.active.expires, original.identity+10*DAY)
            self.assertEqual((model.active.stop, model.active.take), (original.stop, original.take))
            saved = model.checkpoint()
            self.assertEqual(edge.EdgeCampaign.restore(saved).checkpoint(), saved)
            model.prepare_decision(self.engine(model), self.snapshot(model))
            self.assertEqual(len([e for e in journal if e['event'] == 'horizon_extension']), 1)
            model.update(model.last+BAR, '113', '100', '111')  # original stop still wins
            self.assertIsNone(model.active)
            self.assertIsNone(model.extension)

    def test_history_catchup_expired_and_stopped_cannot_extend(self):
        with self.variant('cost-horizon'):
            for days in (5, 7, 8):
                model = self.aged(days)
                self.assertIsNone(model.extension)
                if days >= 7:
                    self.assertIsNone(model.active)
                model.prepare_decision(self.engine(model, allowed=False), self.snapshot(model))
                self.assertIsNone(model.extension)
            model = self.aged(6)
            model.prepare_decision(self.engine(model, model.active.identity+7*DAY), self.snapshot(model))
            self.assertIsNone(model.extension)

    def test_checkpoint_rejects_extension_tampering_and_source_mismatch(self):
        with self.variant('cost-horizon'):
            model = self.aged();model.prepare_decision(self.engine(model), self.snapshot(model))
            saved = model.checkpoint()
            for key, value in [('owned_campaign', 1), ('decision_at_ms', model.active.identity+7*DAY),
                ('session_ms', model.last-DAY), ('new_expiry_ms', model.active.identity+11*DAY),
                ('binding', 'bad'), ('closes', ['100']*20), ('features', {}), ('extra', True)]:
                bad = deepcopy(saved);bad['body']['edge']['extension'][key] = value
                bad['sha256'] = meter.checksum(bad['body'])
                with self.subTest(key=key), self.assertRaises(Blocked): edge.EdgeCampaign.restore(bad)
            bad = deepcopy(saved);bad['body']['edge']['extension'] = [bad['body']['edge']['extension']]*2
            bad['sha256'] = meter.checksum(bad['body'])
            with self.assertRaises(Blocked): edge.EdgeCampaign.restore(bad)
        with edge.variant('cost-horizon', features=Features(), binding=self.binding(source='changed')):
            with self.assertRaises(Blocked): edge.EdgeCampaign.restore(saved)

    def test_extension_session_is_registered_offset_bound_and_rejects_before_recovery(self):
        first = edge._load_frozen_schedule()['primary']['starts_ms'][0]
        for offset in (-60000, 0, 60000):
            with self.subTest(offset=offset), tempfile.TemporaryDirectory() as path:
                with edge.variant('cost-horizon', features=Features(), binding=self.binding(offset)) as identity:
                    model = self.aged()
                    now = max(first+1000, first+offset+1000)
                    engine = self.engine(model, now);engine.session = first+offset
                    model.prepare_decision(engine, self.snapshot(model))
                    saved = model.checkpoint()
                    self.assertEqual(model.extension['session_deadline_ms'], first+offset+300000)
                    self.assertEqual(edge.EdgeCampaign.restore(saved).checkpoint(), saved)
                    bad = deepcopy(saved)
                    event = bad['body']['edge']['extension']
                    event['session_ms'] += 999
                    event['session_deadline_ms'] += 999  # still internally coherent
                    self.assertLess(event['session_ms'], event['decision_at_ms'])
                    bad['sha256'] = meter.checksum(bad['body'])
                    venue = Venue();venue.now = now
                    with State(path, 'binance:BTCUSDT:live:123') as state:
                        state.set('edge_identity', identity)
                        state.set('linear_campaign', bad)
                    with patch.object(lifecycle.Lifecycle, 'settle') as settle, patch.object(lifecycle.Lifecycle, 'finish') as finish:
                        with self.assertRaises(Blocked): self.run_session(venue, path)
                        settle.assert_not_called();finish.assert_not_called()
                    self.assertEqual(venue.sent, [])
        for field in ('original_schedule_sha256', 'actual_starts_sha256'):
            binding = self.binding();binding[field] = '0'*64
            with self.assertRaisesRegex(ValueError, 'schedule binding mismatch'):
                with edge.variant('cost-horizon', features=Features(), binding=binding): pass

    def test_extension_crossed_bar_keeps_original_hold_and_roundtrips(self):
        first = edge._load_frozen_schedule()['primary']['starts_ms'][0]
        # A permitted minus60s session straddles the first four-hour boundary.
        with edge.variant('cost-horizon', features=Features(), binding=self.binding(-60000)):
            model = self.aged()
            # Recreate the still-causal checkpoint immediately before that boundary.
            model = edge.EdgeCampaign.restore(model.checkpoint())
            model.last -= BAR;model.model.last -= BAR
            model.model.close = model.closes[-2];model.closes.pop();model.closes.appendleft(D(108))
            original = model.active
            engine = self.engine(model, first+1000);engine.session = first-60000
            model.prepare_decision(engine, self.snapshot(model))
            self.assertIsNone(model.extension)
            self.assertEqual(model.active, original)
            self.assertEqual(model.action(D(1)), 'hold')
            engine.state.set.assert_not_called()
            self.assertEqual(edge.EdgeCampaign.restore(model.checkpoint()).checkpoint(), model.checkpoint())

    def test_identity_and_checkpoint_reject_before_recovery_or_cleanup(self):
        for corruption in ('binding', 'checkpoint', 'missing'):
            with tempfile.TemporaryDirectory() as path, self.variant() as identity:
                venue = Venue();self.seed(venue, path, identity)
                with State(path, 'binance:BTCUSDT:live:123') as state:
                    if corruption == 'binding': state.set('edge_identity', {'different': True})
                    elif corruption == 'missing': state.set('edge_identity', None)
                    else:
                        saved = state.get('linear_campaign');saved['sha256'] = '0'*64
                        state.set('linear_campaign', saved)
                with patch.object(lifecycle.Lifecycle, 'settle') as settle, patch.object(lifecycle.Lifecycle, 'finish') as finish:
                    with self.assertRaises(Blocked): self.run_session(venue, path)
                    settle.assert_not_called();finish.assert_not_called()
                self.assertEqual(venue.sent, [])

    def test_new_risk_scale_cutoff_zero_and_held_committed_topup(self):
        with self.variant(profile={'scale': '.5'}):
            model = self.warm();model.decision_ms = edge.CUTOFF-1
            full = model.entry_fraction('.0011');model.decision_ms += 1
            self.assertEqual(model.entry_fraction('.0011'), full/2)
        with self.variant(profile={'scale': '0'}):
            model = self.warm();model.decision_ms = edge.CUTOFF
            self.assertEqual(model.entry_fraction('.0011'), 0)
        with tempfile.TemporaryDirectory() as path, self.variant() as identity:
            venue = Venue();venue.fraction = D('.5');self.seed(venue, path, identity)
            topups = []
            original = lifecycle.topup_preview
            def observe(reader, model, snapshot, requested, *args, **kwargs):
                # Any recomputation of the initial fraction for an owned add is a bug.
                model.entry_fraction = Mock(side_effect=AssertionError('recomputed committed target'))
                topups.append(str(requested))
                return original(reader, model, snapshot, requested, *args, **kwargs)
            with patch.object(lifecycle, 'topup_preview', observe):
                report = self.run_session(venue, path)
            self.assertEqual(report['cleanup'], 'verified', report)
            self.assertTrue(topups)
            self.assertEqual(len(set(topups)), 1)
            self.assertTrue(report['actual']['native_full_position_protected'])
            self.assertTrue(report['actual']['stop_before_liquidation'])

    def test_incumbent_retains_original_report_calls_clock_cash_and_checkpoint(self):
        results = []
        for use_edge in (False, True):
            with tempfile.TemporaryDirectory() as path:
                venue = Venue();venue.fraction = D('.5')
                context = self.variant('incumbent') if use_edge else alpha.variant('incumbent')
                with context as identity:
                    self.seed(venue, path, identity if use_edge else None, incumbent=True)
                    report = self.run_session(venue, path)
                    with State(path, 'binance:BTCUSDT:live:123') as state:
                        checkpoint = state.get('linear_campaign')
                results.append((report, venue.now, venue.wallet, venue.q, venue.orders, venue.algos,
                                venue.trades, venue.calls, venue.sent, checkpoint))
        self.assertEqual(results[0], results[1])
        self.assertEqual(edge.decision_coverage([{'event': 'decision'}])['actual_decisions'], 1)
        self.assertEqual(edge.decision_coverage([{'event': 'decision'}])['edge_evaluations'], 0)

    def test_real_decision_journal_has_distinct_completion_clocks(self):
        with tempfile.TemporaryDirectory() as path, self.variant(journal=(journal := [])) as identity:
            venue = Venue();self.seed(venue, path, identity)
            self.assertEqual(self.run_session(venue, path)['cleanup'], 'verified')
            decisions = [e for e in journal if e['event'] == 'decision']
            self.assertTrue(decisions)
            self.assertTrue(all(e['completed_at_ms'] >= e['at_ms'] for e in decisions))
            self.assertTrue(any(e['completed_at_ms'] > e['at_ms'] for e in decisions))
            self.assertTrue(any(e['event'] == 'edge_predecision' for e in journal))
            self.assertTrue(any(e['event'] == 'entry_sizing' for e in journal))
            self.assertTrue(any(e['event'] == 'write_attempt' for e in journal))

    def test_owned_cost_exit_runs_through_real_lifecycle_with_protection(self):
        features = Features('.0001')
        with tempfile.TemporaryDirectory() as path, self.variant('cost-horizon', features, journal=(journal := [])) as identity:
            venue = Venue();self.seed(venue, path, identity)
            first = self.run_session(venue, path, 2)
            self.assertGreater(venue.q, 0)
            self.assertTrue(first['actual']['native_full_position_protected'])
            with State(path, 'binance:BTCUSDT:live:123') as state:
                model = edge.EdgeCampaign.restore(state.get('linear_campaign'))
                model.closes = deque([D(100000)]*20, maxlen=20)
                state.set('linear_campaign', model.checkpoint())
            features.values['funding'] = None
            self.assertEqual(self.run_session(venue, path, 2)['cleanup'], 'verified')
            self.assertGreater(venue.q, 0)
            features.values['funding'] = D('.0004')
            final = self.run_session(venue, path, 2)
            self.assertEqual(final['cleanup'], 'verified')
            self.assertEqual(venue.q, 0)
            self.assertTrue(any(e['event'] == 'decision' and e.get('reason') ==
                'cost_horizon_weak_momentum_high_known_funding' for e in journal))

    def test_hooks_restore_on_exception(self):
        before = campaign.Campaign, linear_preview.Campaign, lifecycle.Lifecycle.__init__, lifecycle.Lifecycle.decide
        with self.assertRaises(RuntimeError), self.variant('quality-budget+cost-horizon'):
            raise RuntimeError('fixture')
        self.assertEqual(before, (campaign.Campaign, linear_preview.Campaign, lifecycle.Lifecycle.__init__, lifecycle.Lifecycle.decide))

    def test_exact_project_calibration_schema(self):
        body = {'format': 1, 'project_kind': 'perp', 'cutoff_ms': edge.CUTOFF,
            'baseline_candidate': 'incumbent', 'spec_sha256': edge.file_hash(edge.SPEC), 'profiles': {}}
        for name in edge.CANDIDATES:
            body['profiles'][name] = {'candidate': name, 'project_kind': 'perp', 'scale': '1' if name == 'incumbent' else '0',
                'effective_from_ms': edge.CUTOFF, 'calibration_end_ms': edge.CUTOFF,
                'training_end_day_exclusive': '2022-01-01', 'baseline_candidate': 'incumbent', 'base_bundle_sha256': 'b'*64}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'profiles.json';path.write_text(json.dumps(body))
            self.assertEqual(edge.calibration(path, edge.CANDIDATES)[0], body['profiles'])
            for key, value in [('project_kind', 'spot'), ('scale', 'NaN'), ('scale', '-.1'), ('scale', '1.01'),
                ('scale', 1), ('base_bundle_sha256', 'bad'), ('effective_from_ms', edge.CUTOFF+1), ('extra', True)]:
                bad = deepcopy(body);bad['profiles']['quality-budget'][key] = value;path.write_text(json.dumps(bad))
                with self.subTest(key=key, value=value), self.assertRaises((ValueError, ArithmeticError)):
                    edge.calibration(path, edge.CANDIDATES)
            bad = deepcopy(body);bad['profiles']['incumbent']['scale'] = '.5';path.write_text(json.dumps(bad))
            with self.assertRaises(ValueError): edge.calibration(path, edge.CANDIDATES)
            for key in ('incumbent', 'quality-budget'):
                bad = deepcopy(body);del bad['profiles'][key];path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError): edge.calibration(path, ['quality-budget'])
            path.write_text(json.dumps(body).replace('"format": 1', '"format": 1, "format": 1'))
            with self.assertRaises(ValueError): edge.calibration(path, edge.CANDIDATES)

    def test_fixed_feature_artifact_pin_rejects_before_account_meter(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'different.json';path.write_text('{}')
            args = SimpleNamespace(candidate='quality-budget', combo=None, risk_calibration=None, features=path)
            with patch.object(meter, 'measure') as measured:
                with self.assertRaisesRegex(ValueError, 'artifact file hash mismatch'):
                    edge.measure(args)
                measured.assert_not_called()

    def test_cli_rejects_nonregistered_or_overwrite_before_measure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'result.json.gz'
            common = ['--features', 'unused', '--out', str(path)]
            for extra in (['--limit', '0'], ['--initial-cny', '9900'], ['--start-offset-ms', '60000'], ['--candidate', 'incumbent', '--combo', 'quality-budget,cost-horizon']):
                with self.assertRaises(SystemExit), patch.object(edge, 'measure') as measure:
                    edge.main(common+extra)
                    measure.assert_not_called()
            path.write_bytes(b'original')
            with self.assertRaises(SystemExit), patch.object(edge, 'measure') as measure:
                edge.main(common)
            measure.assert_not_called();self.assertEqual(path.read_bytes(), b'original')


class PrintTests(unittest.TestCase):
    def archive(self, root, day='2020-01-01'):
        root.mkdir(exist_ok=True)
        path = root/f'BTCUSDT-aggTrades-{day}.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr(path.stem+'.csv', '1,7000.0,0.01,1,1,1577836800000,false\n')
        Path(str(path)+'.CHECKSUM').write_text(digest(path)+'  '+path.name+'\n')
        return path

    def test_verified_vault_hash_receipt_and_eviction_leave_originals_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)/'vault';source = self.archive(vault)
            before = {p.name: p.read_bytes() for p in vault.iterdir()}
            tape = VerifiedPrints(Path(tmp)/'cache', vault)
            with patch('urllib.request.urlopen', side_effect=AssertionError('unnecessary download')):
                self.assertIsNotNone(tape._load(1577836800000))
            self.assertEqual(tape.receipts[0]['sha256'], tape.loaded[source.name])
            (tape.root/source.name).unlink();Path(str(tape.root/source.name)+'.CHECKSUM').unlink()
            self.assertEqual(before, {p.name: p.read_bytes() for p in vault.iterdir()})
            with self.assertRaises(ValueError): VerifiedPrints(vault, vault)

    def test_foreign_packed_price_and_unknown_directory_are_rejected_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)/'vault';source = self.archive(vault)
            root = Path(tmp)/'scratch';binary = Path(tmp)/'scratch-cache';binary.mkdir()
            packed = binary/(source.name+'.'+digest(source)+'.bin')
            with packed.open('wb') as stream:
                for column in ([1], [1577836800000], [1], [99900000000], [100000000]):
                    array.array('q', column).tofile(stream)
            before = packed.read_bytes()
            with self.assertRaises(FileExistsError): VerifiedPrints(root, vault)
            self.assertFalse(root.exists())
            self.assertEqual(packed.read_bytes(), before)
            self.assertEqual(list(binary.iterdir()), [packed])
            # A forged ownership/provenance document cannot establish reuse.
            (binary/'.edge-print-owner').write_text('{}')
            with self.assertRaises(FileExistsError): VerifiedPrints(root, vault)
            self.assertEqual(packed.read_bytes(), before)

    def test_owned_binary_is_verified_before_reuse_and_unknown_files_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)/'vault';source = self.archive(vault)
            tape = VerifiedPrints(Path(tmp)/'cache', vault)
            rows = tape._load(1577836800000)
            self.assertEqual(D(rows[2][0])/10**8, D(7000))
            packed = next(tape.binary_cache.glob('*.bin'))
            self.assertEqual(tape.receipts[-1]['derived_binary_sha256'], digest(packed))
            original = packed.read_bytes()
            with packed.open('wb') as stream:
                for column in ([1], [1577836800000], [1], [99900000000], [100000000]):
                    array.array('q', column).tofile(stream)
            tampered = packed.read_bytes();tape._day_ms = None
            with self.assertRaisesRegex(ValueError, 'integrity/provenance'): tape._load(1577836800000)
            self.assertEqual(packed.read_bytes(), tampered)
            packed.write_bytes(original)
            self.assertEqual(D(tape._load(1577836800000)[2][0])/10**8, D(7000))
            unknown = tape.binary_cache/'unowned.bin';unknown.write_bytes(b'do not delete')
            tape._day_ms = None
            with self.assertRaisesRegex(ValueError, 'unknown derived tape'): tape._load(1577836800000)
            self.assertEqual(unknown.read_bytes(), b'do not delete')
            with self.assertRaises(FileExistsError): VerifiedPrints(tape.root, vault)

    def test_missing_day_eviction_preserves_owned_cache_and_vault(self):
        import urllib.error
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)/'vault'
            for day in ('2020-01-01', '2020-01-02', '2020-01-03'):
                self.archive(vault, day)
            before = {p.name: p.read_bytes() for p in vault.iterdir()}
            tape = VerifiedPrints(Path(tmp)/'cache', vault)
            for i in range(3): tape._load(1577836800000+i*DAY)
            with patch('urllib.request.urlopen', side_effect=urllib.error.HTTPError('fixture', 404, 'missing', {}, None)):
                self.assertIsNone(tape._load(1577836800000+3*DAY))
            self.assertEqual(len(tape.binaries), 2)
            self.assertEqual(D(tape._load(1577836800000+DAY)[2][0])/10**8, D(7000))
            self.assertEqual(before, {p.name: p.read_bytes() for p in vault.iterdir()})

    def test_corrupt_vault_and_orphan_destination_fail_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)/'vault';source = self.archive(vault)
            tape = VerifiedPrints(Path(tmp)/'cache', vault)
            check = Path(str(tape.root/source.name)+'.CHECKSUM');check.write_text('retain')
            with self.assertRaises(ValueError): tape._load(1577836800000)
            self.assertEqual(check.read_text(), 'retain')
            check.unlink();source.write_bytes(b'corrupt')
            with self.assertRaises(ValueError): tape._load(1577836800000)
            self.assertFalse((tape.root/source.name).exists())


if __name__ == '__main__':
    unittest.main()


# These saved scenarios seed legacy SX60/DFII10 checkpoints explicitly.
from tests.legacy_policy import legacy_policy
setUpModule, tearDownModule = legacy_policy()
