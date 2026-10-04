from collections import deque
from copy import deepcopy
from decimal import Decimal as D
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from coinquant import campaign, lifecycle, session
from coinquant.campaign import Campaign, ORIGIN
from coinquant.config import Config
from coinquant.opportunities import Opportunity, FOUR_HOURS as BAR
from coinquant.state import State
from coinquant.types import Blocked, ObservationDeadline
from research import alpha_perp as alpha
from research import complete_perp as meter
from tests.session_venue import Venue


class AlphaTests(unittest.TestCase):
    def warm(self):
        model = alpha.AlphaCampaign()
        for i in range(40):
            model.update(ORIGIN+(i+1)*BAR, '101', '99', '100')
        return model

    def signal(self, model):
        model.update(model.last+BAR, '110', '100', '108')
        model.select_macro(None, '108', model.last+1000)
        return model

    def test_fresh_entry_age_chase_boundaries_owned_and_macro_unchanged(self):
        with alpha.variant('fresh-entry'):
            m = self.signal(self.warm())
            trigger = deepcopy(m.trigger)
            m.decision_ms = m.active.identity+86400000
            m.decision_mark = D(110)
            self.assertEqual(m.action(D(0)), 'enter')
            m.decision_ms += 1
            self.assertEqual(m.action(D(0)), 'flat')
            self.assertEqual(m.reason, 'stale_primary')
            m.decision_ms -= 1
            m.decision_mark += D('.01')
            self.assertEqual(m.action(D(0)), 'flat')
            self.assertEqual(m.reason, 'chased_primary')
            m.filled(m.active.identity)
            self.assertEqual(m.action(D(1)), 'hold')
            self.assertEqual(m.trigger, trigger)
            m.position_campaign = -m.last
            m.macro_opportunity = Opportunity(-m.last, 1, D(90), D(200), None)
            self.assertEqual(m.action(D(1)), 'hold')
            m.position_campaign = None
            m.model.active = None
            self.assertEqual(m.action(D(0)), 'enter')

    def test_compression_uses_prior_high_atr_and_median_with_original_priority(self):
        with alpha.variant('compression-breakout'):
            m = self.warm()
            m.atrs = deque([D(4)]*20, maxlen=20)
            # Trigger range is huge, but neither it nor its ATR enters rolling inputs.
            m.update(m.last+BAR, '140', '80', '102')
            self.assertEqual(m.active.stop, D(98))
            self.assertEqual(m.active.take, D(102)*(D(102)/98)**20)
            self.assertEqual(m.active.expires, m.last+42*BAR)
            self.assertEqual(m.trigger['prior_atr'], '2')
            self.assertEqual(m.trigger['kind'], 'compression-breakout')
            self.assertEqual(m.trigger['close'], '102')
            m = self.warm();m.atrs = deque([D(4)]*20, maxlen=20)
            m.update(m.last+BAR, '110', '100', '108')
            self.assertEqual(m.active.stop, D(104))  # original impulse takes priority
            self.assertEqual(m.trigger['kind'], 'impulse')
            m = self.warm();m.atrs = deque([D(2)]*20, maxlen=20)
            m.update(m.last+BAR, '103', '100', '102')
            self.assertIsNone(m.active)
            m = self.warm();m.atrs = deque([D(4)]*20, maxlen=20)
            m.model.active = Opportunity(m.last, -1, D(120), D(50), m.last+10*BAR)
            m.update(m.last+BAR, '103', '100', '102')
            self.assertEqual(m.model.active.direction, -1)  # no second opportunity

    def test_checkpoint_roundtrip_identity_digest_and_provenance(self):
        with alpha.variant('fresh-entry', binding={'capital': '10000'}):
            m = self.signal(self.warm())
            saved = m.checkpoint()
            restored = alpha.AlphaCampaign.restore(json.loads(json.dumps(saved)))
            self.assertEqual(restored.checkpoint(), saved)
            damaged = deepcopy(saved);damaged['body']['alpha']['trigger']['close'] = '1'
            with self.assertRaises(Blocked): alpha.AlphaCampaign.restore(damaged)
            damaged['sha256'] = meter.checksum(damaged['body'])
            damaged['body']['alpha']['trigger']['identity'] += BAR
            damaged['sha256'] = meter.checksum(damaged['body'])
            with self.assertRaises(Blocked): alpha.AlphaCampaign.restore(damaged)
        for name, binding in [('atr-trail', {'capital': '10000'}), ('fresh-entry', {'capital': '9900'})]:
            with alpha.variant(name, binding=binding):
                with self.assertRaises(Blocked): alpha.AlphaCampaign.restore(saved)

    def test_trail_bar_state_excludes_entry_bar_and_makes_no_unattended_stop_change(self):
        with alpha.variant('atr-trail'):
            m = self.signal(self.warm())
            m.filled(m.active.identity)
            old_stop = m.active.stop
            m.trail = {'campaign': m.position_campaign, 'confirmed_at_ms': m.last+1000, 'high': '108'}
            m.update(m.last+BAR, '150', '106', '108')
            self.assertEqual(m.trail['high'], '108')
            m.update(m.last+BAR, '120', '106', '108')
            self.assertEqual(m.trail['high'], '120')
            self.assertEqual(m.active.stop, old_stop)
            m.decision_mark = D(110)
            m.decision_stop = D(111)
            self.assertEqual(m.action(D(1)), 'exit')
            self.assertEqual(m.reason, 'atr_trail_through_mark')
            self.assertEqual(m.model.active.stop, old_stop)

    def seed(self, venue, directory):
        venue.seed(directory)
        with State(directory, 'binance:BTCUSDT:live:123') as state:
            base = Campaign.restore(state.get('linear_campaign'))
            m = alpha.AlphaCampaign();m.__dict__.update(base.__dict__)
            m.model.tr = deque([D(1000)]*14, maxlen=14)
            m.trigger = {'identity': m.last, 'close': '100000', 'prior_atr': '1000', 'kind': 'impulse', 'direction': 1}
            state.set('linear_campaign', m.checkpoint())

    def run_session(self, venue, directory, seconds=8):
        return session.run(Config('123', directory, seconds, 1), venue, execute=True,
                           monotonic=venue.monotonic, wait=venue.wait)

    def test_single_topup_partial_and_unknown_fills_recover_once_and_keep_protection(self):
        for timeout in (False, True):
            with self.subTest(timeout=timeout), tempfile.TemporaryDirectory() as tmp, alpha.variant('single-topup'):
                venue = Venue();venue.fraction = D('.5');venue.timeout_after_entry = timeout
                self.seed(venue, tmp)
                r = self.run_session(venue, tmp)
                entries = [p for _, path, p in venue.sent if path.endswith('/order') and p.get('timeInForce') == 'IOC']
                self.assertEqual(r['cleanup'], 'verified', r)
                self.assertEqual(len(entries), 2)
                self.assertTrue(r['actual']['native_full_position_protected'])
                self.assertTrue(r['actual']['stop_before_liquidation'])
                self.assertEqual(r['pending_intents'], 0)
                self.run_session(venue, tmp)
                self.assertEqual(len(venue.orders), 2)  # another session cannot add

    def test_unknown_unaccepted_topup_is_not_resent(self):
        with tempfile.TemporaryDirectory() as tmp, alpha.variant('single-topup'):
            venue = Venue();venue.fraction = D('.5');self.seed(venue, tmp)
            original = venue.send
            def send(method, path, payload):
                if path.endswith('/order') and venue.orders:
                    venue.timeout_before_entry = True
                return original(method, path, payload)
            venue.send = send
            report = self.run_session(venue, tmp)
            self.assertTrue(report['execution_unresolved'])
            entries = [p for _, path, p in venue.sent if path.endswith('/order')]
            self.assertEqual(len(entries), 2)
            self.run_session(venue, tmp)
            self.assertEqual(len([p for _, path, p in venue.sent if path.endswith('/order')]), 2)

    def test_real_lifecycle_trail_tightens_and_through_mark_reduces_without_macro_change(self):
        for through, macro in ((False, False), (True, False), (False, True)):
            with self.subTest(through=through, macro=macro), tempfile.TemporaryDirectory() as tmp, alpha.variant('atr-trail'):
                venue = Venue();self.seed(venue, tmp)
                self.assertEqual(self.run_session(venue, tmp, 1)['cleanup'], 'verified')
                with State(tmp, 'binance:BTCUSDT:live:123') as state:
                    m = alpha.AlphaCampaign.restore(state.get('linear_campaign'))
                    self.assertIsNotNone(m.trail)
                    m.trail['high'] = '104000' if through else '101000'
                    state.set('linear_campaign', m.checkpoint())
                if macro:
                    # Pure decision seam: owned macro never gets the primary trail.
                    m.position_campaign = -m.last
                    m.macro_opportunity = Opportunity(-m.last, 1, D(90000), D(200000), None)
                    m.decision_stop = None
                    self.assertEqual(m.active.stop, D(90000))
                    continue
                report = self.run_session(venue, tmp, 2)
                self.assertEqual(report['cleanup'], 'verified', report)
                if through:
                    self.assertEqual(venue.q, 0)
                else:
                    live = [a for a in venue.algos.values() if a['algoStatus'] == 'NEW' and a['orderType'] == 'STOP_MARKET']
                    self.assertEqual(D(live[0]['triggerPrice']), D(98000))
                    with State(tmp, 'binance:BTCUSDT:live:123') as state:
                        m = alpha.AlphaCampaign.restore(state.get('linear_campaign'))
                        m.trail['high'] = '100000';state.set('linear_campaign', m.checkpoint())
                    self.run_session(venue, tmp, 2)
                    live = [a for a in venue.algos.values() if a['algoStatus'] == 'NEW' and a['orderType'] == 'STOP_MARKET']
                    self.assertEqual(D(live[0]['triggerPrice']), D(98000))

    def test_incumbent_noop_preserves_calls_clock_cash_fills_and_requests(self):
        outputs = []
        for research in (False, True):
            with tempfile.TemporaryDirectory() as tmp:
                venue = Venue();venue.fraction = D('.5')
                if research:
                    with alpha.variant('incumbent'):
                        self.seed(venue, tmp);report = self.run_session(venue, tmp)
                else:
                    venue.seed(tmp);report = self.run_session(venue, tmp)
                outputs.append((venue.calls, venue.sent, venue.now, venue.wallet, venue.q, venue.trades,
                                report['cleanup'], report['cycles']))
        self.assertEqual(outputs[0], outputs[1])

    def test_cycle_failures_are_distinct_once_and_keep_actual_chronology(self):
        with tempfile.TemporaryDirectory() as tmp:
            venue = Venue();venue.seed(tmp)
            journal = []
            original_cycle = session.cycle
            attempted = 0
            def intermittent(reader, state, uid, **kwargs):
                nonlocal attempted
                attempted += 1
                if attempted in (1, 3):
                    reader.wait(.1)
                    raise ObservationDeadline('same deadline on different cycles')
                return original_cycle(reader, state, uid, **kwargs)
            with patch.object(session, 'cycle', intermittent), alpha.variant('incumbent', journal=journal):
                self.seed(venue, tmp)
                report = self.run_session(venue, tmp, 5)
            alpha.record_session_phases(journal, report, venue.now)
            failures = [e for e in journal if e['event'] == 'cycle_blocked']
            self.assertEqual(len(failures), 2)
            self.assertEqual([e['cycle_sequence'] for e in failures], [1, 3])
            self.assertTrue(all(e['session_ms'] == report['session_started_at_ms'] for e in failures))
            self.assertLess(report['session_started_at_ms'], failures[0]['at_ms'])
            self.assertLess(failures[0]['at_ms'], failures[1]['at_ms'])
            self.assertTrue(any(e['event'] == 'decision' and failures[0]['at_ms'] < e['at_ms'] < failures[1]['at_ms'] for e in journal))
            self.assertFalse(any(e['event'] in ('session_error', 'session_phase_summary') for e in journal))
            self.assertEqual([e['at_ms'] for e in journal], sorted(e['at_ms'] for e in journal))
            self.assertEqual(report['cleanup'], 'verified')
            # A non-cycle report summary is retained at report time, never backdated.
            alpha.record_session_phases(journal, {**report, 'errors': report['errors']+[
                {'phase': 'backup', 'reason': 'fixture backup failure', 'error_type': 'OSError'}]}, venue.now)
            self.assertEqual(journal[-1]['event'], 'session_phase_summary')
            self.assertEqual(journal[-1]['at_ms'], venue.now)
            self.assertEqual(journal[-1]['timestamp_basis'], 'session_report_completed')
            self.assertEqual(len([e for e in journal if e['event'] == 'cycle_blocked']), 2)

    def test_macro_creation_provenance_survives_polls_checkpoint_and_owned_decisions(self):
        with tempfile.TemporaryDirectory() as tmp, alpha.variant('incumbent', journal=(journal := [])):
            venue = Venue();self.seed(venue, tmp)
            with State(tmp, 'binance:BTCUSDT:live:123') as state:
                model = alpha.AlphaCampaign.restore(state.get('linear_campaign'))
                model.model.active = model.trigger = None
                model.daily_lows.extend([D(90000)]*10)
                state.set('linear_campaign', model.checkpoint())
            row = dict(missing_reason=None, latest_value='1', prior20_value='1.3',
                       latest_observation_date=datetime.fromtimestamp(venue.now/1000, timezone.utc).date().isoformat(),
                       latest_value_available_ms=venue.now-1000, prior20_value_available_ms=venue.now-1000)
            venue.dfii10_snapshot = lambda: row
            original_row, original_mark = deepcopy(row), str(venue.mark)
            report = self.run_session(venue, tmp, 3)
            self.assertEqual(report['cleanup'], 'verified', report)
            created = [e for e in journal if e['event'] == 'opportunity' and e['kind'] == 'macro']
            self.assertEqual(len(created), 1)
            creation = created[0]
            self.assertEqual(creation['at_ms'], -creation['identity'])
            self.assertEqual(creation['created_at_ms'], creation['at_ms'])
            self.assertEqual(creation['decision_mark'], original_mark)
            self.assertEqual(creation['dfii10'], original_row)
            with State(tmp, 'binance:BTCUSDT:live:123') as state:
                saved = state.get('linear_campaign')
                restored = alpha.AlphaCampaign.restore(saved)
                provenance = deepcopy(restored.macro_trigger)
                self.assertEqual(restored.checkpoint(), saved)
                broken = deepcopy(saved)
                broken['body']['alpha']['macro_trigger']['identity'] -= 1
                broken['sha256'] = meter.checksum(broken['body'])
                with self.assertRaises(Blocked): alpha.AlphaCampaign.restore(broken)
            row['latest_value'] = '.9';venue.mark += 10
            self.assertEqual(self.run_session(venue, tmp, 3)['cleanup'], 'verified')
            self.assertEqual(len([e for e in journal if e['event'] == 'opportunity' and e['kind'] == 'macro']), 1)
            decisions = [e for e in journal if e['event'] == 'decision' and e['opportunity'] == creation['identity']]
            self.assertGreater(len(decisions), 2)
            self.assertGreater(decisions[-1]['age_ms'], decisions[0]['age_ms'])
            self.assertTrue(all(e['trigger'] == provenance for e in decisions))
            self.assertEqual(creation['dfii10'], original_row)
            self.assertEqual(decisions[-1]['trigger']['decision_mark'], original_mark)
            self.assertEqual(decisions[-1]['decision_mark'], str(venue.mark))
            self.assertTrue(all(e['age_ms'] == e['at_ms']-creation['created_at_ms'] for e in decisions))

    def test_macro_diagnostic_closes_are_attached_only_after_execution(self):
        finished = False
        created_at = ORIGIN+41*BAR+1000
        def bar4(opened):
            self.assertTrue(finished)
            self.assertEqual(opened % BAR, 0)
            return (D(100), D(101), D(99), D(100), D(1))
        exchange = SimpleNamespace(uid=12000, clock=lambda: created_at/1000, orders={}, algos={}, trades=[],
                                   market=SimpleNamespace(bar4=bar4))
        def run(config, reader):
            model = self.warm()
            model.update(model.last+BAR, '101', '99', '100')
            model.daily_lows.extend([D(90)]*10)
            row = dict(missing_reason=None, latest_value='1', prior20_value='1.3',
                       latest_observation_date=datetime.fromtimestamp(created_at/1000, timezone.utc).date().isoformat(),
                       latest_value_available_ms=created_at-1000, prior20_value_available_ms=created_at-1000)
            model.select_macro(row, '100', created_at)
            return {'session_started_at_ms': created_at, 'errors': []}
        def measure(args):
            nonlocal finished
            with meter.variant('incumbent', None):
                meter.run(None, exchange)
            finished = True
            return {'inputs': {'protocol_sha256': 'original'}, 'conditions': {},
                    'results': {'incumbent': {'base': {}}}}
        args = SimpleNamespace(candidate='incumbent', combo=None, risk_calibration=None,
                               scenario='base', start_offset_ms=0, initial_cny=D(10000))
        with patch.object(meter, 'run', run), patch.object(meter, 'measure', measure):
            result = alpha.measure(args)
        event, = result['results']['incumbent']['base']['opportunity_ledger']
        self.assertEqual(event['kind'], 'macro')
        for days in (5, 20):
            diagnostic = event['post_run_diagnostic_closes'][str(days)]
            self.assertEqual(diagnostic['horizon_ms'], created_at+days*86400000)
            self.assertEqual(diagnostic['at_ms'], (created_at+days*86400000)//BAR*BAR)
            self.assertEqual(diagnostic['close'], '100')

    def test_hooks_restore_on_exception(self):
        prior = (campaign.Campaign, lifecycle.Lifecycle.decide, lifecycle.Lifecycle.top_up, session.reconcile)
        with self.assertRaises(RuntimeError):
            with alpha.variant('fresh-entry+single-topup'):
                raise RuntimeError('fixture')
        self.assertEqual(prior, (campaign.Campaign, lifecycle.Lifecycle.decide, lifecycle.Lifecycle.top_up, session.reconcile))

    def test_calibration_binding_rejects_future_mismatch_nonfinite_and_scales_only_new_sizing(self):
        profile = {'scale': '.5', 'effective_from_ms': alpha.CUTOFF, 'calibration_end_ms': alpha.CUTOFF,
                   'training_end_day_exclusive': '2022-01-01', 'base_bundle_sha256': 'a'*64,
                   'baseline_candidate': 'incumbent'}
        body = {'format': 1, 'cutoff_ms': alpha.CUTOFF, 'spec_sha256': alpha.file_hash(alpha.SPEC),
                'profiles': {'fresh-entry': profile}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'risk.json';path.write_text(json.dumps(body))
            self.assertEqual(alpha.calibration(path, ['fresh-entry'])[0]['fresh-entry']['scale'], '.5')
            for key, value in [('scale', 'NaN'), ('scale', '1.1'), ('calibration_end_ms', alpha.CUTOFF+1),
                               ('base_bundle_sha256', 'bad'), ('training_end_day_exclusive', '2023-01-01')]:
                bad = deepcopy(body);bad['profiles']['fresh-entry'][key] = value
                path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError): alpha.calibration(path, ['fresh-entry'])
        with alpha.variant('fresh-entry', profile=profile):
            m = self.signal(self.warm());m.returns = deque([D('.02')]*20, maxlen=20)
            m.decision_ms = alpha.CUTOFF-1
            before = m.entry_fraction('.0011')
            m.decision_ms += 1
            self.assertEqual(m.entry_fraction('.0011'), before/2)


if __name__ == '__main__':
    unittest.main()


# These saved scenarios seed legacy SX60/DFII10 checkpoints explicitly.
from tests.legacy_policy import legacy_policy
setUpModule, tearDownModule = legacy_policy()
