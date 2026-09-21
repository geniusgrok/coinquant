from decimal import Decimal as D
import json
import unittest
import tempfile
from unittest.mock import Mock
from pancakequant.campaign import Campaign, ORIGIN
from pancakequant.opportunities import Opportunity
from pancakequant.types import Blocked
from pancakequant.state import State
from pancakequant.linear_preview import advance, preview


class CampaignTests(unittest.TestCase):
    def test_read_only_resume_and_unknown_ownership(self):
        with tempfile.TemporaryDirectory() as tmp, State(tmp,'test') as state:
            m=Campaign()
            for i in range(30):m.update(ORIGIN+(i+1)*14400000,D(101),D(99),D(100))
            m.model.active=Opportunity(m.last,1,D(90),D(200),m.last+14400000)
            state.set('linear_campaign',m.checkpoint())
            venue=Mock();venue.completed_market.return_value={'interval_ms':14400000,'complete_through':m.last,'candles':[]}
            restored,_,cold=advance(state,venue)
            self.assertFalse(cold);venue.completed_market.assert_called_once_with(start=m.last)
            self.assertEqual(preview(restored,{'quantity_btc':'0'})['action'],'enter')
            self.assertIsNone(restored.consumed)
            with self.assertRaises(Blocked):preview(restored,{'quantity_btc':'1'})

    def test_every_prefix_survives_serialized_restart(self):
        continuous=Campaign();restarted=Campaign()
        for i in range(240):
            close=D(100)+D(i%27)
            end=ORIGIN+(i+1)*14400000
            continuous.update(end,close+1,close-1,close)
            restarted.update(end,close+1,close-1,close)
            self.assertEqual(continuous.checkpoint(),restarted.checkpoint())
            self.assertEqual(continuous.fraction('3.6','.0011'),restarted.fraction('3.6','.0011'))
            restarted=Campaign.restore(json.loads(json.dumps(restarted.checkpoint())))

    def test_consumption_and_unknown_position(self):
        m=Campaign();m.last=ORIGIN+14400000;m.model.last=m.last
        m.model.active=Opportunity(m.last,1,D(90),D(200),m.last+14400000)
        self.assertEqual(m.action(D(0)),'enter')
        with self.assertRaises(Blocked):m.action(D(1))
        m.filled(m.last)
        m=Campaign.restore(json.loads(json.dumps(m.checkpoint())))
        self.assertEqual(m.action(D(1)),'hold')
        self.assertEqual(m.action(D(0)),'consumed')
        m.model.active=None
        self.assertEqual(m.action(D(1)),'exit')

    def test_missing_history_and_corrupt_checkpoint_block(self):
        m=Campaign()
        with self.assertRaises(Blocked):m.update(ORIGIN+28800000,D(101),D(99),D(100))
        state=m.checkpoint();state['body']['consumed']=123
        with self.assertRaises(Blocked):Campaign.restore(state)

    def test_swing_accumulates_without_single_bar_shock(self):
        m=Campaign('swing',86400000)
        for i in range(30):
            close=D(100)+D(i)/2
            m.update(ORIGIN+(i+1)*86400000,close+1,close-1,close)
        self.assertEqual(m.model.swing_direction,1)
        self.assertIsNotNone(m.model.active)
        self.assertIsNone(m.model.active.expires)
