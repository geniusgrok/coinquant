from decimal import Decimal as D
import json
import unittest
import tempfile
from unittest.mock import Mock
from coinquant.campaign import Campaign, ORIGIN
from coinquant.opportunities import Opportunity
from coinquant.types import Blocked
from coinquant.state import State
from coinquant.linear_preview import advance, preview


class CampaignTests(unittest.TestCase):
    def test_read_only_resume_and_unknown_ownership(self):
        with tempfile.TemporaryDirectory() as tmp, State(tmp,'test') as state:
            m=Campaign()
            for i in range(30):m.update(ORIGIN+(i+1)*14400000,D(101),D(99),D(100))
            m.model.active=Opportunity(m.last,1,D(90),D(200),m.last+14400000)
            state.set('linear_campaign',m.checkpoint())
            venue=Mock();venue.completed_market.return_value={'interval_ms':14400000,'complete_through':m.last,'candles':[]}
            restored,_,cold=advance(state,venue)
            self.assertFalse(cold);self.assertEqual(venue.completed_market.call_args.kwargs['start'],m.last)
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

    def test_interrupted_bootstrap_resumes_only_verified_page(self):
        from coinquant.types import Unknown
        interval=14400000
        bar=dict(time=ORIGIN,high='101',low='99',close='100')
        with tempfile.TemporaryDirectory() as tmp,State(tmp,'test') as state:
            venue=Mock()
            def interrupted(start,on_page):
                on_page([bar]);raise Unknown('next page disconnected')
            venue.completed_market.side_effect=interrupted
            with self.assertRaises(Unknown):advance(state,venue)
            self.assertEqual(Campaign.restore(state.get('linear_campaign')).last,ORIGIN+interval)
            self.assertTrue(state.get('market_bootstrap'))
            def resumed(start,on_page):
                self.assertEqual(start,ORIGIN+interval)
                return dict(interval_ms=interval,complete_through=start,candles=[])
            venue.completed_market.side_effect=resumed
            model,_,cold=advance(state,venue)
            self.assertTrue(cold);self.assertFalse(state.get('market_bootstrap'))
