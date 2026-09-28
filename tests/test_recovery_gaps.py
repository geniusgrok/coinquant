"""Offline reproductions of the 2026-09-28 review findings on the session path."""
import tempfile
from decimal import Decimal as D
from unittest import TestCase
from unittest.mock import patch

from coinquant.config import Config
from coinquant.campaign import Campaign
from coinquant.ownership import reconcile
from coinquant.session import run
from coinquant.state import State, client_id
from coinquant.types import Missing, Unknown
from tests.session_venue import Venue


class RecoveryGapTests(TestCase):
    def test_late_query_missing_does_not_orphan_filled_add(self):
        self.session()
        with State(self.directory,'binance:BTCUSDT:live:123') as state:
            links=state.get('entry_campaigns');campaign=next(iter(links.values()))['campaign']
            identity=client_id(state.identity,999,'entry')
            payload=dict(symbol='BTCUSDT',positionSide='BOTH',side='BUY',type='LIMIT',
                         timeInForce='IOC',quantity='.001',price=str(self.venue.mark),
                         newClientOrderId=identity,newOrderRespType='RESULT')
            state.prepare(identity,'binance_order',payload,campaign=campaign,
                          position_snapshot=self.venue.snapshot('123'),
                          result={'prepared_at_ms':self.venue.now})
            self.venue.send('POST','/fapi/v1/order',payload)
            self.venue.wait(301)
            original=self.venue.query_intent
            def missing(oid,**kwargs):
                if oid==identity:raise Missing('delayed query')
                return original(oid,**kwargs)
            self.venue.query_intent=missing
            self.assertEqual(self.venue.recover_pending(state)['pending'],1)
            self.venue.query_intent=original
            self.assertEqual(self.venue.recover_pending(state)['pending'],0)
            result=reconcile(state,self.venue,Campaign.restore(state.get('linear_campaign')),
                             self.venue.snapshot('123'))
            self.assertEqual(result['status'],'reconciled')
            self.assertEqual(result['fill_count'],2)
            self.assertEqual(len([p for _,_,p in self.venue.sent if p.get('timeInForce')=='IOC']),2)

    def setUp(self):
        self.risk=patch('coinquant.campaign.PRIMARY_RISK','6');self.risk.start()
        self.tmp=tempfile.TemporaryDirectory();self.directory=self.tmp.name
        self.venue=Venue();self.venue.seed(self.directory)
    def tearDown(self):self.tmp.cleanup();self.risk.stop()
    def session(self,seconds=3):
        return run(Config('123',self.directory,seconds,1),self.venue,execute=True,
                   monotonic=self.venue.monotonic,wait=self.venue.wait)
    def entries(self):
        return [p for _,path,p in self.venue.sent if path.endswith('/order') and p.get('timeInForce')=='IOC']
    def active(self,kind=None):
        return [a for a in self.venue.algos.values() if a['algoStatus']=='NEW' and kind in (None,a['orderType'])]

    def test_history_outage_after_owned_fill_still_installs_protection(self):
        # A fill within the default seven-day read gives the flat boundary a trade-ID cursor.
        self.venue.trades.append(dict(symbol='BTCUSDT',positionSide='BOTH',side='SELL',orderId=900,id=1,
                                      time=self.venue.now-86400000,qty='.01'))
        original=self.venue.get
        def history_down(path,p=None):
            if path.endswith('/userTrades') and 'startTime' in (p or {}):raise Unknown('fixture history outage')
            return original(path,p)
        self.venue.get=history_down
        result=self.session()
        self.assertGreater(self.venue.q,0)
        self.assertEqual(len(self.entries()),1)
        self.assertEqual({a['orderType'] for a in self.active()},{'STOP_MARKET','TAKE_PROFIT_MARKET'})
        self.assertTrue(self.venue.snapshot('123')['native_full_position_protected'])
        # The ownership audit is still required before any new risk.
        self.assertEqual(result['cleanup'],'unresolved')

    def test_protection_lost_during_margin_transfer_blocks_the_add(self):
        self.venue.fraction=D('.5');original=self.venue.send
        def cancel_stop(method,path,p):
            answer=original(method,path,p)
            if path.endswith('/positionMargin') and self.active('STOP_MARKET'):
                self.active('STOP_MARKET')[0]['algoStatus']='CANCELED'
            return answer
        self.venue.send=cancel_stop
        self.session()
        self.assertEqual(len(self.entries()),1)
