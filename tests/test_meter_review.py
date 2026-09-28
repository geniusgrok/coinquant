"""Meter accounting: funding order, funding coverage, flat FX valuation, trial hygiene."""
import json
import tempfile
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from coinquant import campaign, native_preview
from research import rebuild
from research.session_exchange import SessionExchange
from research.session_market import FUNDING_INTERVAL, Market

MINUTE = 60_000
GRID = int(datetime(2020, 1, 3, 8, tzinfo=timezone.utc).timestamp() * 1000)


def _minute(low):
    return (D(10000), D(10000), D(low), D(10000), D(1))


def _held(low, funding):
    open_ms = GRID - MINUTE
    rows = {open_ms - MINUTE: _minute(9990), open_ms: _minute(low)}
    market = Market({}, funding, identity={'trade': dict(rows), 'mark': dict(rows)})
    exchange = SessionExchange(market, open_ms, D(10000))
    exchange.q, exchange.entry, exchange.margin = D(1), D(10000), D(2000)
    exchange.held_from = open_ms
    exchange.algos['cq-stop'] = dict(algoStatus='NEW', orderType='STOP_MARKET', triggerPrice='9000')
    return exchange


class FundingOrderTests(TestCase):
    def test_stop_inside_the_minute_is_not_charged_the_boundary_settlement(self):
        exchange = _held(8500, [(GRID, D('0.01'))])
        exchange.wait(60)
        self.assertEqual(exchange.q, 0)
        self.assertEqual(exchange.funnel['funding'], 0)
        self.assertTrue(exchange.known_path)

    def test_position_held_through_the_boundary_pays_it(self):
        exchange = _held(9500, [(GRID, D('0.01'))])
        exchange.wait(60)
        self.assertEqual(exchange.q, 1)
        self.assertEqual(exchange.funnel['funding'], 1)
        self.assertEqual(exchange.funding_paid, D(100))


class FundingCoverageTests(TestCase):
    def test_uncovered_settlement_time_is_a_gap_anywhere(self):
        market = Market({}, [(GRID - FUNDING_INTERVAL, D(0)), (GRID + FUNDING_INTERVAL + 3, D(0))])
        self.assertFalse(market.funding_between(GRID - FUNDING_INTERVAL - 1, GRID - 1)[1])
        self.assertTrue(market.funding_between(GRID - 1, GRID)[1])
        events, gap = market.funding_between(GRID, GRID + FUNDING_INTERVAL + 10)
        self.assertEqual((events, gap), ([(GRID + FUNDING_INTERVAL + 3, D(0))], False))

    def test_hold_across_a_missing_rate_loses_the_known_path(self):
        exchange = _held(9500, [])
        exchange.wait(60)
        self.assertFalse(exchange.known_path)


class StepFX:
    times = (1000, 2000)

    def __call__(self, now_ms):
        return D(7) if now_ms < 1000 or now_ms >= 2000 else D(6)

    def changes(self, start_ms, end_ms):
        return [stamp for stamp in self.times if start_ms < stamp <= end_ms]


class FlatValuationTests(TestCase):
    def test_flat_cash_drawdown_between_session_starts_is_recorded(self):
        exchange = SessionExchange(Market({}, ()), 0, D(1000))
        exchange.fx = StepFX()
        exchange.peak_cny = exchange.peak_envelope_cny = D(7000)
        exchange.mdd_close = exchange.mdd_envelope = D(0)
        exchange.advance_unattended(5000)
        self.assertEqual(exchange.mdd_close, 1 - D(6) / D(7))
        self.assertEqual(exchange.mdd_close_at, 1000)


class TrialHygieneTests(TestCase):
    def _run(self, **kwargs):
        base = SimpleNamespace(identity={'market': 'fake'}, loaded={'mark/1m/x.zip': 'aa'})
        exchange = SimpleNamespace(prints=SimpleNamespace(loaded={'p.zip': 'bb'}))
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(rebuild, 'OUT', Path(tmp) / 'official'), \
                patch.object(rebuild, 'PARTIAL', Path(tmp) / 'partial'), \
                patch.object(rebuild, 'load_base', return_value=base), \
                patch.object(rebuild, 'run_account', return_value=({}, exchange)) as account:
            result = rebuild.trial('T', state=Path(tmp) / 'state', **kwargs)
            written = sorted(str(path.relative_to(tmp)) for path in Path(tmp).rglob('T.json'))
            return result, written, account, json.loads((Path(tmp) / written[0]).read_text()) if written else None

    def test_partial_run_never_writes_the_official_name(self):
        result, written, account, saved = self._run(limit=2)
        self.assertEqual(len(account.call_args.args[1]), 2)
        self.assertEqual(written, ['partial/T.json'])
        self.assertFalse(result['complete'])
        self.assertEqual((result['sessions_executed'], result['sessions_requested']), (2, 795))
        self.assertEqual(saved['market_identity']['loaded_print_files'], {'p.zip': 'bb'})
        self.assertEqual(len(saved['source']['git_head']), 40)
        self.assertEqual(len(saved['source']['python_sources_sha256']), 64)

    def test_complete_run_writes_the_official_name(self):
        result, written, _account, _saved = self._run()
        self.assertEqual(written, ['official/T.json'])
        self.assertTrue(result['complete'])

    def test_research_knobs_are_restored(self):
        before = native_preview.BOOK_PARTICIPATION, campaign.PRIMARY_RISK
        result, _written, _account, _saved = self._run(limit=1, participation='0.5', primary_risk='9')
        self.assertEqual((result['book_participation'], result['primary_risk']), ('0.5', '9'))
        self.assertEqual((native_preview.BOOK_PARTICIPATION, campaign.PRIMARY_RISK), before)
        with patch.object(rebuild, 'load_base', side_effect=RuntimeError('boom')), \
                tempfile.TemporaryDirectory() as tmp, self.assertRaises(RuntimeError):
            rebuild.trial('T', state=Path(tmp) / 's', participation='0.5', primary_risk='9', out=tmp)
        self.assertEqual((native_preview.BOOK_PARTICIPATION, campaign.PRIMARY_RISK), before)
