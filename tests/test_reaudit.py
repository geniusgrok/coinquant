"""Offline reproductions of the 7c9b2b7 re-audit findings on the real session path."""
import tempfile
from unittest import TestCase
from unittest.mock import patch

from coinquant.config import Config
from coinquant.session import run
from coinquant.state import State
from coinquant.types import Unknown
from tests.session_venue import Venue


class ReauditTests(TestCase):
    def setUp(self):
        self.risk=patch('coinquant.campaign.PRIMARY_RISK','6');self.risk.start()
        self.tmp=tempfile.TemporaryDirectory();self.directory=self.tmp.name
        self.venue=Venue();self.venue.seed(self.directory)
    def tearDown(self):self.tmp.cleanup();self.risk.stop()
    def session(self,seconds=3):
        return run(Config('123',self.directory,seconds,1),self.venue,execute=True,
                   monotonic=self.venue.monotonic,wait=self.venue.wait)
    def posts(self,kind=None):
        return [p for m,path,p in self.venue.sent if m=='POST' and path.endswith('/algoOrder') and kind in (None,p['type'])]
    def reductions(self):
        return [p for m,path,p in self.venue.sent if path.endswith('/order') and p.get('reduceOnly')=='true']
    def intents(self):
        with State(self.directory,'binance:BTCUSDT:live:123') as state:
            return state.db.execute('SELECT kind,status FROM intents ORDER BY updated').fetchall()

    def test_unknown_protection_does_not_block_a_later_safe_reduction(self):
        original=self.venue.send
        def lost_stop(method,path,p):
            if method=='POST' and path.endswith('/algoOrder') and p['type']=='STOP_MARKET' and not self.posts():
                self.venue.sent.append((method,path,p))
                self.venue.fail_reads=True  # transient outage right after the lost request
                raise TimeoutError()
            return original(method,path,p)
        self.venue.send=lost_stop
        first=self.session()
        self.assertGreater(self.venue.q,0)
        self.assertEqual(first['cleanup'],'unresolved')
        self.assertEqual(self.reductions(),[])
        self.venue.fail_reads=False
        second=self.session()
        self.assertEqual(self.venue.q,0)
        self.assertEqual(len(self.reductions()),1)
        self.assertEqual(len(self.posts('STOP_MARKET')),1)
        self.assertEqual(self.posts('TAKE_PROFIT_MARKET'),[])
        # The never-observed stop still blocks new risk until it can be retired.
        self.assertEqual(second['pending_intents'],1)
        self.venue.wait(301)
        third=self.session()
        self.assertEqual(third['pending_intents'],0)
        self.assertEqual(third['cleanup'],'verified')
        self.assertIn(('binance_algo','void'),self.intents())
        self.assertEqual(len(self.posts('STOP_MARKET')),1)
