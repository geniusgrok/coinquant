from decimal import Decimal as D
import unittest

from coinquant.campaign import ORIGIN
from coinquant.opportunities import FOUR_HOURS, Opportunity
from coinquant.types import Blocked
from research.upgrade_perp import PullbackCampaign, recovery


class RecoveryTests(unittest.TestCase):
    def test_recovery_needs_completed_trend_drawdown_and_bounce(self):
        prices = [D(90)]*354+[D(110), D(111), D(112), D(111), D(105), D(106)]
        self.assertEqual(recovery(prices, [D(103)]*6, D(2)), (D(103), D(112)))
        self.assertIsNone(recovery(prices[:-1], [D(103)]*6, D(2)))
        self.assertIsNone(recovery(prices, [D(103)]*6, D(20)))
        self.assertIsNone(recovery([D(120)]*354+prices[-6:], [D(103)]*6, D(2)))

    def test_recovery_checkpoint_roundtrip_and_missing_history_rejection(self):
        value = PullbackCampaign()
        for i in range(1, 16):
            value.update(ORIGIN+i*FOUR_HOURS, D(101), D(99), D(100))
        saved = value.checkpoint()
        restored = PullbackCampaign.restore(saved)
        self.assertEqual(restored.checkpoint(), saved)
        broken = dict(saved, body=dict(saved['body']))
        broken['body'].pop('recovery')
        from research.complete_perp import checksum
        broken['sha256'] = checksum(broken['body'])
        with self.assertRaises(Blocked):
            PullbackCampaign.restore(broken)

    def test_owned_primary_is_not_replaced_by_recovery(self):
        value = PullbackCampaign()
        value.recovery_closes.extend([D(90)]*355+[D(110),D(111),D(112),D(111),D(105)])
        value.recovery_lows.extend([D(103)]*6)
        value.model.tr.extend([D(2)]*14)
        value.model.close=D(105)
        value.model.last=value.last=ORIGIN+360*FOUR_HOURS
        identity=value.last
        value.model.active=Opportunity(identity,1,D(95),D(200),identity+42*FOUR_HOURS)
        value.position_campaign=value.consumed=value.primary_consumed=identity
        value.update(value.last+FOUR_HOURS,D(107),D(104),D(106))
        self.assertEqual(value.model.active.identity,identity)
