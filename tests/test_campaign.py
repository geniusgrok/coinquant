from decimal import Decimal as D
from datetime import datetime, timezone
import hashlib
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
    def test_macro_priority_consumption_and_restart(self):
        m=Campaign()
        for i in range(11*6):
            m.update(ORIGIN+(i+1)*14400000,D(101),D(90),D(100))
        self.assertEqual(len(m.daily_lows),10)
        m.model.active=Opportunity(m.last,1,D(90),D(200),m.last+14400000)
        m.primary_consumed=m.model.active.identity
        true=dict(missing_reason=None,latest_value='1',prior20_value='1.3',
                  latest_value_available_ms=m.last-1000,prior20_value_available_ms=m.last-1000,
                  latest_observation_date=datetime.fromtimestamp(m.last/1000,timezone.utc).date().isoformat())
        t=m.last+1000;m.select_macro(true,'100',t)
        self.assertEqual(m.active.identity,-t)
        self.assertEqual(m.action(D(0)),'enter')
        m.filled(-t)
        m=Campaign.restore(json.loads(json.dumps(m.checkpoint())))
        m.select_macro(true,'100',t+2000)
        self.assertEqual(m.action(D(1)),'hold')
        m.select_macro(dict(true,missing_reason='stale'),'100',t+2500)
        self.assertEqual(m.action(D(1)),'exit')
        m=Campaign.restore(json.loads(json.dumps(m.checkpoint())))
        m.position_campaign=None
        self.assertEqual(m.action(D(0)),'flat')
        m.select_macro(dict(true,missing_reason='stale'), '100',t+3000)
        self.assertIsNone(m.macro_epoch)
        m.select_macro(true,'100',t+4000)
        self.assertEqual(m.action(D(0)),'enter')
        self.assertNotEqual(m.active.identity,-t)

    def test_macro_cold_start_does_not_infer_old_unseen_campaign(self):
        m=Campaign()
        for i in range(11*6):m.update(ORIGIN+(i+1)*14400000,D(101),D(90),D(100))
        now=m.last+1000
        row=dict(missing_reason=None,latest_value='1',prior20_value='1.3',
                 latest_value_available_ms=m.last-1,prior20_value_available_ms=m.last-1,
                 latest_observation_date=datetime.fromtimestamp(m.last/1000,timezone.utc).date().isoformat())
        m.select_macro(row,'100',now,bootstrap=True)
        self.assertEqual(m.action(D(0)),'consumed')


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

    def test_entry_fill_is_checkpointed_and_extends_only_the_owned_campaign(self):
        end=ORIGIN+50*14400000
        ident=ORIGIN+14400000
        def prepared():
            m=Campaign()
            m.last=end-14400000
            m.model.last=m.last
            m.model.close=D(100)
            m.model.active=Opportunity(ident,1,D(100),D(500),end,D(115),D(15),D(140),False)
            m.model.lows.extend([D(130)]*84)
            m.entry_fill=D(110)
            return m
        missed=prepared()
        self.assertIsNone(missed.update(end,D(190),D(150),D(180)))
        owned=prepared()
        owned.filled(ident)
        held=owned.update(end,D(190),D(150),D(180))
        self.assertTrue(held.extended)
        self.assertGreaterEqual(held.stop,D(130))
        self.assertEqual(held.take,D(190)*5)
        restored=Campaign.restore(json.loads(json.dumps(owned.checkpoint())))
        self.assertEqual(restored.entry_fill,D(110))
        self.assertTrue(restored.model.active.extended)
        bad=owned.checkpoint()
        bad['body']['entry_fill']='0'
        bad['sha256']=hashlib.sha256(json.dumps(bad['body'],sort_keys=True).encode()).hexdigest()
        with self.assertRaises(Blocked):Campaign.restore(bad)

    def test_missing_history_and_corrupt_checkpoint_block(self):
        m=Campaign()
        with self.assertRaises(Blocked):m.update(ORIGIN+28800000,D(101),D(99),D(100))
        state=m.checkpoint();state['body']['consumed']=123
        with self.assertRaises(Blocked):Campaign.restore(state)

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
            self.assertTrue(cold);self.assertTrue(state.get('market_bootstrap'))
