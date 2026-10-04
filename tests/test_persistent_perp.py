import copy
import unittest

from coinquant.campaign import ORIGIN
from coinquant.opportunities import FOUR_HOURS
from coinquant.types import Blocked
from research import persistent_perp as p, complete_perp as meter


class PersistentCampaignTests(unittest.TestCase):
    def test_restore_binds_candidate_and_preserves_consumed_identity(self):
        with p.variant('state-trend',{},[]):
            model=p.StateCampaign()
            model.update(ORIGIN+FOUR_HOURS,101,99,100)
            model.primary_consumed=ORIGIN
            saved=model.checkpoint()
            restored=p.StateCampaign.restore(saved)
            self.assertEqual(restored.primary_consumed,ORIGIN)
            foreign=copy.deepcopy(saved)
            foreign['body']['persistent']['name']='state-range'
            foreign['sha256']=meter.checksum(foreign['body'])
            with self.assertRaises(Blocked):p.StateCampaign.restore(foreign)

    def test_uniform_control_applies_once_before_and_after_cutoff(self):
        model=p.UniformCampaign()
        model.returns.extend([p.D('.01')]*20)
        base=p.alpha.BaseCampaign.entry_fraction(model,'.0011')
        self.assertEqual(model.entry_fraction('.0011'),base*p.D('.75'))
        model.decision_ms=p.alpha.CUTOFF+1
        self.assertEqual(model.entry_fraction('.0011'),base*p.D('.75'))
