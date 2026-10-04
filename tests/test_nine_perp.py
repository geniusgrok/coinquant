import unittest

from coinquant.campaign import ORIGIN
from coinquant.opportunities import FOUR_HOURS
from coinquant.types import Blocked
from research.nine_perp import RouteCampaign, variant


class Book:
    sha256='a'*64
    def at(self,family,now,context):
        return dict(status='WAIT_NEW_INTERVAL',weak=None,release=None)


class InformationCampaignTests(unittest.TestCase):
    def test_pending_info_preserves_consumed_ownership_and_bound_checkpoint(self):
        with variant('oi-deleveraging',0,Book(),lambda now:None,[]):
            model=RouteCampaign();model.update(ORIGIN+FOUR_HOURS,'110','90','100')
            model.primary_consumed=ORIGIN+FOUR_HOURS
            saved=model.checkpoint();restored=RouteCampaign.restore(saved)
            self.assertEqual(restored.primary_consumed,model.primary_consumed)
            self.assertIsNone(restored.model.active)
            self.assertEqual(list(restored.route_lows),list(model.route_lows))
        with variant('oi-deleveraging',1,Book(),lambda now:None,[]):
            with self.assertRaises(Blocked):RouteCampaign.restore(saved)


    def test_one_received_oi_signal_cannot_reopen_after_restore(self):
        from unittest.mock import patch
        class Released(Book):
            def at(self,family,now,context):
                return dict(status='FEATURE_READY',weak=False,release=True,available_ms=ORIGIN+FOUR_HOURS)
        with variant('oi-deleveraging',0,Released(),lambda now:None,[]):
            model=RouteCampaign()
            for i in range(1,11):model.update(ORIGIN+i*FOUR_HOURS,'110','90','100')
            self.assertIsNotNone(model.model.active)
            signal=model.route_signal_ms
            saved=model.checkpoint();restored=RouteCampaign.restore(saved)
            self.assertEqual(RouteCampaign.restore(saved).route_signal_ms,signal)
            restored.model.active=None
            with patch.object(restored.model,'update',return_value=None):
                restored.update(ORIGIN+11*FOUR_HOURS,'110','90','100')
            self.assertIsNone(restored.model.active)
            self.assertEqual(restored.route_signal_ms,signal)


if __name__=='__main__':unittest.main()
