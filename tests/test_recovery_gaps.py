"""Offline reproductions of the 2026-09-28 review findings on the session path."""
import tempfile
from decimal import Decimal as D
from unittest import TestCase
from unittest.mock import patch

from coinquant.config import Config
from coinquant.session import run
from coinquant.types import Unknown
from tests.session_venue import Venue


class RecoveryGapTests(TestCase):
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
