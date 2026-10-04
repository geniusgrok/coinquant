"""Call-chain checks for the 2026-09-29 review: funds gate, exits, clocks, REST errors."""
import io
import json
import signal
import tempfile
from decimal import Decimal as D
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from coinquant import cli
from coinquant.audit import allows_new_risk, income
from coinquant.binance import Binance
from coinquant.binance_safety import send_once
from coinquant.campaign import Campaign
from coinquant.config import Config
from coinquant.session import run
from coinquant.state import State
from coinquant.types import NotSent, Unknown
from tests.session_venue import Venue

SCOPE = 'binance:BTCUSDT:live:123'


class Clocked:
    def __init__(self, now, pages=()):
        self.now = now
        self.pages = list(pages)

    def clock(self):
        return self.now / 1000

    def get(self, path, params=None):
        return [row for row in self.pages if params['startTime'] <= row['time'] <= params['endTime']]


def row(tran, amount, at):
    return dict(incomeType='COMMISSION', tranId=tran, time=at, asset='USDT', income=str(amount), symbol='BTCUSDT', tradeId='')


class FundsAuditGate(TestCase):
    def test_wallet_drop_without_income_never_opens_risk_and_late_income_clears_it(self):
        with tempfile.TemporaryDirectory() as tmp, State(tmp, SCOPE) as state:
            reader = Clocked(1_000_000)
            first = income(reader, state, wallet='100')
            self.assertTrue(allows_new_risk(first, '100', flat=True))
            self.assertFalse(allows_new_risk(first, '100', flat=False))
            reader.now += 5000
            pending = income(reader, state, wallet='90')
            self.assertEqual(pending['wallet_closure'], 'pending_income')
            self.assertFalse(allows_new_risk(pending, '90', flat=False))
            reader.pages.append(row(1, '-10', reader.now - 1000))
            reader.now += 5000
            explained = income(reader, state, wallet='90')
            self.assertEqual(explained['wallet_closure'], 'explained')
            self.assertTrue(allows_new_risk(explained, '90', flat=False))

    def test_gap_that_income_never_explains_becomes_unexplained(self):
        with tempfile.TemporaryDirectory() as tmp, State(tmp, SCOPE) as state:
            reader = Clocked(1_000_000)
            income(reader, state, wallet='100')
            reader.now += 5000
            income(reader, state, wallet='90')
            reader.now += 61000
            late = income(reader, state, wallet='90')
            self.assertEqual(late['wallet_closure'], 'unexplained')
            self.assertFalse(allows_new_risk(late, '90', flat=True))

    def test_cache_is_bound_to_the_wallet_value_and_wallet_less_reads_do_not_settle(self):
        with tempfile.TemporaryDirectory() as tmp, State(tmp, SCOPE) as state:
            reader = Clocked(1_000_000)
            income(reader, state, wallet='100')
            reader.now += 1000
            self.assertTrue(allows_new_risk(income(reader, state, wallet='100'), '100', flat=True))
            changed = income(reader, state, wallet='90')
            self.assertFalse(allows_new_risk(changed, '90', flat=True))
            collected = income(reader, state)
            self.assertFalse(allows_new_risk(collected, '90', flat=True))
            self.assertFalse(allows_new_risk(collected, None, flat=True))
            self.assertFalse(allows_new_risk({}, '90', flat=True))
            self.assertEqual(state.get('income_coverage')['closure']['wallet'], '90')

    def test_unexplained_wallet_stops_top_up_but_keeps_protection(self):
        with tempfile.TemporaryDirectory() as tmp:
            venue = Venue()
            venue.seed(tmp)
            venue.fraction = D('.5')

            def wait(seconds):
                venue.wallet -= D(10)
                venue.wait(61)
            result = run(Config('123', tmp, 120, 1), venue, execute=True, monotonic=venue.monotonic, wait=wait)
            entries = [p for _, path, p in venue.sent if path.endswith('/order') and p.get('timeInForce') == 'IOC']
            self.assertEqual(len(entries), 1)
            self.assertGreater(venue.q, 0)
            self.assertEqual(result['cleanup'], 'verified')
            self.assertTrue(result['actual']['native_full_position_protected'])
            self.assertFalse(result['execution_unresolved'])

    def test_audit_failure_does_not_stop_signal_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            venue = Venue()
            venue.seed(tmp)
            run(Config('123', tmp, 1, 1), venue, execute=True, monotonic=venue.monotonic, wait=venue.wait)
            with State(tmp, SCOPE) as state:
                model = Campaign.restore(state.get('linear_campaign'))
                model.model.active = None
                state.set('linear_campaign', model.checkpoint())
            original = venue.get

            def get(path, parameters=None):
                if path.endswith('/income'):
                    raise Unknown('fixture income unavailable')
                return original(path, parameters)
            venue.get = get
            result = run(Config('123', tmp, 3, 1), venue, execute=True, monotonic=venue.monotonic, wait=venue.wait)
            self.assertEqual(venue.q, 0)
            self.assertEqual(result['cleanup'], 'verified')

    def test_final_income_audit_failure_is_reported_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            venue = Venue(-1)
            venue.seed(tmp)
            original = venue.get
            broken = []

            def get(path, parameters=None):
                if path.endswith('/income') and broken:
                    raise Unknown('fixture income unavailable')
                return original(path, parameters)
            venue.get = get

            def wait(seconds):
                broken.append(True)
                venue.wait(seconds)
            result = run(Config('123', tmp, 2, 1), venue, execute=True, monotonic=venue.monotonic, wait=wait)
            self.assertEqual(result['income_audit'], {'status': 'unresolved'})
            self.assertEqual(result['status'], 'unknown')


class ExitPaths(TestCase):
    def test_interrupt_and_clock_failure_are_reported_with_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            venue = Venue(-1)
            venue.seed(tmp)
            calls = []
            original = venue.begin_cycle

            def begin(seconds=120):
                calls.append(seconds)
                if len(calls) == 1:
                    raise Unknown('fixture clock alignment failed')
                return original(seconds)
            venue.begin_cycle = begin
            result = run(Config('123', tmp, 3, 1), venue, execute=True, monotonic=venue.monotonic, wait=venue.wait)
            self.assertEqual(result['errors'][0]['phase'], 'clock')
            self.assertEqual(result['errors'][0]['error_type'], 'Unknown')
            self.assertEqual(result['cleanup'], 'verified')
            self.assertEqual(venue.sent, [])

    def test_deadline_with_pending_intent_is_execution_unresolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            venue = Venue()
            venue.seed(tmp)
            venue.timeout_after_entry = True
            original = venue.get

            def get(path, parameters=None):
                if path.endswith('/order') and 'origClientOrderId' in (parameters or {}):
                    raise Unknown('fixture order query unavailable')
                return original(path, parameters)
            venue.get = get
            result = run(Config('123', tmp, 3, 1), venue, execute=True, monotonic=venue.monotonic, wait=venue.wait)
            self.assertTrue(result['execution_unresolved'])
            self.assertEqual(result['status'], 'unknown')

    def test_verified_session_is_not_unresolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            venue = Venue()
            venue.seed(tmp)
            result = run(Config('123', tmp, 3, 1), venue, execute=True, monotonic=venue.monotonic, wait=venue.wait)
            self.assertFalse(result['execution_unresolved'])
            self.assertEqual(result['observation_timeouts'], 0)

    def test_cleanup_budget_never_passes_the_hard_deadline(self):
        with tempfile.TemporaryDirectory() as tmp:
            venue = Venue()
            venue.seed(tmp)
            run(Config('123', tmp, 3, 1), venue, execute=True, monotonic=venue.monotonic, wait=venue.wait)
            self.assertLessEqual(venue.deadline, venue.hard_deadline)
            venue.set_deadline(10_000, extend_only=True)
            self.assertEqual(venue.deadline, venue.hard_deadline)


class StatusClock(TestCase):
    def reader(self, *, time_ok, offset=5000):
        seen = []

        class Opener:
            def open(self, request, timeout):
                seen.append(request.full_url)
                if request.full_url.endswith('/fapi/v1/time'):
                    if not time_ok:
                        raise URLError('offline')
                    return io.BytesIO(json.dumps({'serverTime': 1_770_004_800_000 + offset}).encode())
                raise URLError('stop after the first signed read')
        reader = Binance(key='k', secret='s', opener=Opener(), clock=lambda: 1_770_004_800.0)
        reader.align_time = True
        return reader, seen

    def config(self, tmp):
        path = Path(tmp) / 'config.json'
        path.write_text(json.dumps(dict(account_uid='123', state_dir=str(Path(tmp) / 'state'))))
        return path

    def test_status_aligns_the_clock_before_the_first_signed_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            reader, seen = self.reader(time_ok=True)
            with patch('coinquant.cli.connect', return_value=reader):
                with self.assertRaises(Unknown):
                    cli.observe(self.config(tmp))
            self.assertTrue(seen[0].endswith('/fapi/v1/time'))
            signed = [u for u in seen if 'signature=' in u]
            self.assertTrue(signed)
            self.assertIn('timestamp=1770004805000', signed[0])

    def test_failed_time_read_sends_no_signed_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            reader, seen = self.reader(time_ok=False)
            with patch('coinquant.cli.connect', return_value=reader):
                with self.assertRaises(Unknown):
                    cli.observe(self.config(tmp))
            self.assertEqual(len(seen), 1)
            self.assertFalse(any('signature=' in u for u in seen))

    def test_main_reports_the_failure_and_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            reader, seen = self.reader(time_ok=False)
            with patch('coinquant.cli.connect', return_value=reader), patch('sys.stdout', new=io.StringIO()) as out:
                code = cli.main(['status', '--config', str(self.config(tmp))])
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(out.getvalue())['status'], 'unknown')


class Signals(TestCase):
    def test_first_signal_interrupts_later_ones_are_ignored_and_handlers_restore(self):
        before = signal.getsignal(signal.SIGTERM)
        with cli._FirstSignal() as guard:
            with self.assertRaises(KeyboardInterrupt):
                guard(signal.SIGTERM, None)
            guard(signal.SIGTERM, None)
            guard(signal.SIGINT, None)
        self.assertEqual(signal.getsignal(signal.SIGTERM), before)

    def test_interrupt_before_the_session_is_an_explicit_unknown_report(self):
        with patch('coinquant.cli._dispatch', side_effect=KeyboardInterrupt), patch('sys.stdout', new=io.StringIO()) as out:
            code = cli.main(['run'])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out.getvalue())['status'], 'unknown')


class RestErrors(TestCase):
    def failing(self, status, body=b'{}', headers=None):
        class Opener:
            def open(self, request, timeout):
                raise HTTPError(request.full_url, status, 'x', headers or {}, io.BytesIO(body))
        return Binance(key='k', secret='s', opener=Opener(), clock=lambda: 1_770_004_800.0, authorize_writes=True)

    def write(self, reader):
        return reader._request('POST', '/fapi/v1/order', {'symbol': 'BTCUSDT'})

    def test_rate_limits_and_server_errors_stay_unknown_with_native_evidence(self):
        for status in (418, 429, 500, 502, 503):
            reader = self.failing(status, b'{"code":-1003,"msg":"busy"}')
            with self.assertRaises(Unknown) as caught:
                self.write(reader)
            self.assertNotIsInstance(caught.exception, NotSent)
            self.assertEqual(caught.exception.http_status, status)
            self.assertEqual(caught.exception.native_code, -1003)
            if status in (418, 429):
                with self.assertRaises(NotSent):
                    self.write(reader)

    def test_unknown_status_is_recorded_on_the_intent_and_never_terminal(self):
        with tempfile.TemporaryDirectory() as tmp, State(tmp, SCOPE) as state:
            reader = self.failing(429, b'{"code":-1003,"msg":"busy"}')
            state.prepare('cq-x', 'binance_order', {'symbol': 'BTCUSDT'})
            send_once(state, 'cq-x', lambda *a: self.write(reader), 'POST', '/fapi/v1/order', {})
            status, result = state.db.execute("SELECT status,result FROM intents WHERE id='cq-x'").fetchone()
            self.assertEqual(status, 'unknown')
            self.assertEqual(json.loads(result)['unresolved']['http_status'], 429)

    def test_documented_rejection_is_terminal_and_transport_loss_is_not(self):
        reader = self.failing(503, b'{"code":-1008,"msg":"overloaded"}')
        with self.assertRaises(Unknown) as caught:
            self.write(reader)
        self.assertEqual(type(caught.exception).__name__, 'Rejected')

        class Late:
            def open(self, request, timeout):
                raise TimeoutError()
        late = Binance(key='k', secret='s', opener=Late(), clock=lambda: 1_770_004_800.0, authorize_writes=True)
        with self.assertRaises(Unknown) as caught:
            self.write(late)
        self.assertEqual(type(caught.exception).__name__, 'Unknown')
        self.assertIsNone(caught.exception.http_status)


class FirstFillToProtection(TestCase):
    def session(self, venue, tmp, seconds=3):
        venue.seed(tmp)
        return run(Config('123', tmp, seconds, 1), venue, execute=True, monotonic=venue.monotonic, wait=venue.wait)

    def test_stop_accepted_take_rejected_never_leaves_a_one_leg_position(self):
        with tempfile.TemporaryDirectory() as tmp:
            venue = Venue()
            original = venue.send

            def send(method, path, p):
                if path.endswith('/algoOrder') and method == 'POST' and p['type'] == 'TAKE_PROFIT_MARKET':
                    raise Unknown('fixture take-profit rejection')
                return original(method, path, p)
            venue.send = send
            result = self.session(venue, tmp)
            kinds = [(m, p.get('type')) for m, path, p in venue.sent if path.endswith('/algoOrder')]
            self.assertEqual(kinds[0], ('POST', 'STOP_MARKET'))
            self.assertEqual(kinds.count(('POST', 'TAKE_PROFIT_MARKET')), 0)
            self.assertEqual(venue.q, 0)
            self.assertTrue(any(p.get('reduceOnly') == 'true' for _, _, p in venue.sent))
            self.assertEqual(result['status'], 'unknown')

    def test_unknown_margin_transfer_is_not_resent_and_position_stays_protected(self):
        with tempfile.TemporaryDirectory() as tmp:
            venue = Venue()
            venue.fraction = D('.5')
            original = venue.send

            def send(method, path, p):
                answer = original(method, path, p)
                if path.endswith('/positionMargin'):
                    raise TimeoutError()
                return answer
            venue.send = send
            result = self.session(venue, tmp, seconds=5)
            self.assertEqual(len([1 for _, path, _ in venue.sent if path.endswith('/positionMargin')]), 1)
            entries = [p for _, path, p in venue.sent if path.endswith('/order') and p.get('timeInForce') == 'IOC']
            self.assertEqual(len(entries), 1)
            self.assertEqual(result['status'], 'unknown')
            self.assertEqual(result['errors'][0]['reason'], 'margin outcome unknown; no automatic retry')
            live = [a for a in venue.algos.values() if a['algoStatus'] == 'NEW']
            self.assertEqual({a['orderType'] for a in live}, {'STOP_MARKET', 'TAKE_PROFIT_MARKET'})
            reduce = [p for _, _, p in venue.sent if p.get('reduceOnly') == 'true']
            self.assertTrue(all(D(p['quantity']) <= D(entries[0]['quantity']) / 2 for p in reduce))

    def test_entry_reply_lost_after_fill_is_found_by_identity_and_protected(self):
        with tempfile.TemporaryDirectory() as tmp:
            venue = Venue()
            venue.timeout_after_entry = True
            result = self.session(venue, tmp)
            entries = [p for _, path, p in venue.sent if path.endswith('/order') and p.get('timeInForce') == 'IOC']
            self.assertEqual(len(entries), 1)
            self.assertTrue(result['actual']['native_full_position_protected'])
            self.assertEqual(result['pending_intents'], 0)


class SmallFundBoundaries(TestCase):
    def partial(self, tmp):
        venue = Venue()
        venue.fraction = D('.5')
        venue.seed(tmp)
        result = run(Config('123', tmp, 1, 1), venue, execute=True, monotonic=venue.monotonic, wait=venue.wait)
        return venue, result

    def preview(self, venue, tmp, **kwargs):
        from coinquant.native_preview import topup_preview
        with State(tmp, SCOPE) as state:
            model = Campaign.restore(state.get('linear_campaign'))
            fill, protection = state.get('entry_fill'), state.get('position_protection')
        venue.begin_cycle(60)
        snapshot = venue.snapshot('123')
        return topup_preview(venue, model, snapshot, fill['requested'], protection['stop'], protection['take'], None, **kwargs)

    def test_lowered_capital_never_grows_the_position_back_to_the_old_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            venue, _ = self.partial(tmp)
            self.assertGreater(D(self.preview(venue, tmp)['quantity_btc']), 0)
            venue.capital_limit = D(100)
            self.assertEqual(D(self.preview(venue, tmp, entry_capital='1000')['quantity_btc']), 0)

    def test_entry_records_its_sizing_capital_and_top_up_reports_current_capital(self):
        with tempfile.TemporaryDirectory() as tmp:
            venue, _ = self.partial(tmp)
            with State(tmp, SCOPE) as state:
                self.assertLessEqual(D(state.get('entry_fill')['sizing_capital']), D(1000))
                self.assertGreater(D(state.get('entry_fill')['sizing_capital']), D(990))
            self.assertEqual(D(self.preview(venue, tmp)['sizing_capital_usdt']), venue.wallet)

    def test_session_reports_exchange_leverage_apart_from_account_notional(self):
        with tempfile.TemporaryDirectory() as tmp:
            venue = Venue()
            venue.seed(tmp)
            result = run(Config('123', tmp, 2, 1), venue, execute=True, monotonic=venue.monotonic, wait=venue.wait)
            self.assertEqual(result['exchange_leverage_setting'], 20)
            self.assertGreater(D(result['account_notional_leverage']), 0)
            self.assertLessEqual(D(result['account_notional_leverage']), 20)


class MacroFailurePolicy(TestCase):
    def broken(self, venue):
        calls = []

        def snapshot():
            calls.append(True)
            raise Unknown('fixture ALFRED outage')
        venue.dfii10_snapshot = snapshot
        return calls

    def test_outage_does_not_touch_a_primary_position_or_its_protection(self):
        with tempfile.TemporaryDirectory() as tmp:
            venue = Venue()
            venue.seed(tmp)
            run(Config('123', tmp, 1, 1), venue, execute=True, monotonic=venue.monotonic, wait=venue.wait)
            calls = self.broken(venue)
            before = len(venue.sent)
            result = run(Config('123', tmp, 3, 1), venue, execute=True, monotonic=venue.monotonic, wait=venue.wait)
            self.assertEqual(calls, [])
            self.assertEqual(len(venue.sent), before)
            self.assertTrue(result['actual']['native_full_position_protected'])
            self.assertEqual(result['cleanup'], 'verified')

    def test_outage_on_a_flat_account_stops_new_risk_without_hiding_the_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            venue = Venue(-1)
            venue.seed(tmp)
            calls = self.broken(venue)
            result = run(Config('123', tmp, 2, 1), venue, execute=True, monotonic=venue.monotonic, wait=venue.wait)
            self.assertTrue(calls)
            self.assertEqual(venue.sent, [])
            self.assertEqual(result['status'], 'unknown')
            self.assertIn('ALFRED', result['errors'][-1]['reason'])


class CliSmoke(TestCase):
    def config(self, tmp, **extra):
        path = Path(tmp) / 'config.json'
        path.write_text(json.dumps(dict(account_uid='123', state_dir=str(Path(tmp) / 'state'),
                                        session_seconds=1, poll_seconds=1, **extra)))
        return path

    def test_run_defaults_to_observation_and_sends_no_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            venue = Venue()
            venue.seed(str(Path(tmp) / 'state'))
            with patch('coinquant.cli.connect', return_value=venue), patch('sys.stdout', new=io.StringIO()) as out:
                code = cli.main(['run', '--config', str(self.config(tmp))])
            report = json.loads(out.getvalue())
            self.assertEqual(code, 0)
            self.assertEqual(report['status'], 'read_only')
            self.assertFalse(report['write_attempted'])
            self.assertEqual(venue.sent, [])

    def test_execute_needs_trial_and_uid_before_credentials(self):
        with tempfile.TemporaryDirectory() as tmp, patch('coinquant.cli.connect') as connect, \
                patch('sys.stdout', new=io.StringIO()) as out:
            code = cli.main(['run', '--config', str(self.config(tmp)), '--execute'])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out.getvalue())['status'], 'blocked')
        connect.assert_not_called()

    def test_trial_options_without_execute_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp, patch('coinquant.cli.connect') as connect, \
                patch('sys.stdout', new=io.StringIO()):
            code = cli.main(['run', '--config', str(self.config(tmp)), '--trial', 'demo'])
        self.assertEqual(code, 2)
        connect.assert_not_called()


class NativePrecision(TestCase):
    def test_sub_unit_residue_is_arithmetic_but_one_native_unit_is_a_gap(self):
        with tempfile.TemporaryDirectory() as tmp, State(tmp, SCOPE) as state:
            reader = Clocked(1_000_000)
            income(reader, state, wallet='100')
            reader.pages.append(row(1, '-10.0000000000000000000000001', reader.now + 500))
            reader.now += 1000
            self.assertEqual(income(reader, state, wallet='90')['wallet_closure'], 'explained')
            reader.pages.append(row(2, '-1', reader.now + 500))
            reader.now += 1000
            self.assertEqual(income(reader, state, wallet='88.99999999')['wallet_closure'], 'pending_income')


class ReplacementFallback(TestCase):
    def test_unprotected_position_with_a_failing_replacement_is_reduced_not_left_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            venue = Venue()
            venue.seed(tmp)
            run(Config('123', tmp, 1, 1), venue, execute=True, monotonic=venue.monotonic, wait=venue.wait)
            for algo in venue.algos.values():
                algo['algoStatus'] = 'CANCELED'
            with State(tmp, SCOPE) as state:
                protection = state.get('position_protection')
                state.set('session_replacement', dict(protection, old_epoch=1, epoch=2))
                state.set('position_protection', None)
            before = len(venue.sent)
            result = run(Config('123', tmp, 2, 1), venue, execute=True, monotonic=venue.monotonic, wait=venue.wait)
            reductions = [p for _, _, p in venue.sent[before:] if p.get('reduceOnly') == 'true']
            self.assertTrue(reductions)
            self.assertEqual(venue.q, 0)
            self.assertTrue(any('ownership' in e['reason'] for e in result['errors']), result['errors'])
            self.assertEqual(result['cleanup'], 'verified')

    def test_a_healthy_native_leg_keeps_the_block_without_reducing(self):
        with tempfile.TemporaryDirectory() as tmp:
            venue = Venue()
            venue.seed(tmp)
            run(Config('123', tmp, 1, 1), venue, execute=True, monotonic=venue.monotonic, wait=venue.wait)
            with State(tmp, SCOPE) as state:
                protection = state.get('position_protection')
                state.set('session_replacement', dict(protection, old_epoch=1, epoch=2))
            before = len(venue.sent)
            run(Config('123', tmp, 2, 1), venue, execute=True, monotonic=venue.monotonic, wait=venue.wait)
            self.assertFalse([p for _, _, p in venue.sent[before:] if p.get('reduceOnly') == 'true'])
            self.assertGreater(venue.q, 0)


# These saved scenarios seed legacy SX60/DFII10 checkpoints explicitly.
from tests.legacy_policy import legacy_policy
setUpModule, tearDownModule = legacy_policy()
