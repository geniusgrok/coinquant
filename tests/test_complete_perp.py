from collections import deque
from decimal import Decimal as D
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from coinquant.campaign import Campaign, ORIGIN
from coinquant.linear_sizing import funded_target
from coinquant.linear_account import Account
from coinquant.opportunities import Opportunity
from coinquant.types import Blocked
from research.complete_perp import Crowding, ResearchCampaign, ResearchExchange, variant, DAY, EIGHT_HOURS


class CompletePerpTests(unittest.TestCase):
    def test_features_ignore_future_and_expire(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'features.json'
            path.write_text(json.dumps({'funding': [[0, '.0001'], [EIGHT_HOURS, '.0004']],
                'basis': [[60000, '.001'], [DAY+60000, '.02']], 'source': {}}))
            c = Crowding(path)
            self.assertIsNone(c.value('funding', EIGHT_HOURS-1))
            self.assertEqual(c.value('funding', EIGHT_HOURS), D('.0001'))
            self.assertEqual(c.value('funding', 2*EIGHT_HOURS-1), D('.0001'))
            self.assertEqual(c.value('funding', 2*EIGHT_HOURS), D('.0004'))
            self.assertIsNone(c.value('funding', 3*EIGHT_HOURS))
            self.assertIsNone(c.value('basis', 59999))
            self.assertEqual(c.value('basis', DAY-1), D('.001'))
            self.assertIsNone(c.value('basis', DAY))
            self.assertIsNone(c.value('basis', DAY+59999))
            self.assertEqual(c.value('basis', DAY+60000), D('.02'))
            self.assertIsNone(c.value('basis', 2*DAY+60000))

    def warmed(self):
        m = ResearchCampaign()
        for i in range(70*6):
            close = D(100)+D(i//6)
            m.update(ORIGIN+(i+1)*14400000, close+1, close-1, close)
        return m

    def test_checkpoint_daily_state_and_candidate_identity(self):
        with variant('slow-trend', None):
            m = self.warmed()
            restored = ResearchCampaign.restore(json.loads(json.dumps(m.checkpoint())))
            self.assertEqual(restored.daily_closes, m.daily_closes)
            self.assertTrue(restored.trend(1))
            checkpoint = m.checkpoint()
        with variant('incumbent', None):
            with self.assertRaises(Blocked):
                ResearchCampaign.restore(checkpoint)
        self.assertIs(Campaign, __import__('coinquant.campaign', fromlist=['Campaign']).Campaign)

    def test_slow_trend_primary_priority_owned_stop_and_break(self):
        with variant('slow-trend', None):
            m = self.warmed()
            m.model.active = Opportunity(m.last, 1, D(160), D(200), m.last+14400000)
            m.select_macro(None, '170', m.last+1000)
            self.assertIs(m.active, m.model.active)
            self.assertIsNone(m.macro_opportunity)
            m.primary_consumed = m.last
            m.select_macro(None, '170', m.last+1001)
            identity, stop = m.active.identity, m.active.stop
            self.assertLess(identity, 0)
            self.assertEqual(stop, min(m.daily_lows))
            m.filled(identity)
            m.model.active = None
            m.select_macro(None, '180', m.last+2000)
            self.assertEqual(m.action(D(1)), 'hold')
            self.assertEqual(m.active.stop, stop)
            m.daily_closes[-1] = D(1)
            m.select_macro(None, '170', m.last+2001)
            self.assertEqual(m.action(D(1)), 'exit')

    def test_conditional_short_requires_decline_and_one_way_ownership(self):
        with variant('conditional-short', None):
            m = self.warmed()
            short = Opportunity(m.last, -1, D(180), D(100), m.last+14400000)
            m.model.active = short
            self.assertFalse(m.short_active())
            m.daily_closes = deque((D(200-i) for i in range(65)), maxlen=65)
            self.assertTrue(m.short_active())
            m.select_macro(None, '135', m.last+1000)
            self.assertEqual(m.action(D(0)), 'enter')
            m.filled(m.last)
            self.assertEqual(m.action(D(-1)), 'hold')
            long = Opportunity(m.last+14400000, 1, D(120), D(180), m.last+28800000)
            m.model.active = long
            self.assertEqual(m.action(D(-1)), 'exit')
            self.assertEqual(m.active.direction, 1)
            account = Account(D(1000), q=D(-1), entry=D(135), margin=D(100))
            with self.assertRaisesRegex(ValueError, 'close opposite'):
                funded_target(account, 1, D(1), D(135), D(135), D(120), D(180), D(1), None)

    def test_filters_only_block_new_longs_not_hold_or_reduction(self):
        c = Mock(); c.value.return_value = None
        with variant('funding-filter', c):
            m = self.warmed()
            m.model.active = Opportunity(m.last, 1, D(160), D(200), m.last+14400000)
            m.select_macro(None, '170', m.last+1000)
            self.assertEqual(m.action(D(0)), 'flat')
            c.value.return_value = D('.0003')
            self.assertEqual(m.action(D(0)), 'enter')
            m.filled(m.last)
            c.value.return_value = D('.01')
            self.assertEqual(m.action(D(1)), 'hold')
            m.model.active = None
            self.assertEqual(m.action(D(1)), 'exit')

    def test_tail_recent_shock_reduces_fraction_without_other_knobs(self):
        with variant('tail-sizing', None):
            m = ResearchCampaign()
            m.returns = deque([D('.01')]*15+[D('.10')]*5, maxlen=20)
            baseline = Campaign(); baseline.returns = m.returns.copy()
            self.assertLess(m.fraction('7.5', '.0011'), baseline.fraction('7.5', '.0011'))
            m.returns = deque([D('.10')]*15+[D('.01')]*5, maxlen=20)
            baseline.returns = m.returns.copy()
            self.assertEqual(m.fraction('7.5', '.0011'), baseline.fraction('7.5', '.0011'))

    def test_initial_fx_precedes_metric_and_daily_boundary_uses_boundary_fx(self):
        fx = Mock(side_effect=lambda stamp: D(7) if stamp < 2*DAY else D(8))
        e = ResearchExchange(Mock(), DAY, D(10000)/7*D('.999'), fx=fx)
        self.assertEqual(e.peak_envelope_cny, D(10000))
        self.assertLess(abs(e.mdd_envelope-D('.001999')), D('1e-25'))
        e.capture(2*DAY)
        self.assertEqual(e.daily[1]['equity_cny'], str(e.wallet*8*D('.999')))
        self.assertEqual(e.daily[1]['stamp_ms'], 2*DAY)


if __name__ == '__main__':
    unittest.main()
