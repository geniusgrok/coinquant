"""DFII10 availability must only gate decisions it can change."""
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from decimal import Decimal as D
from unittest import TestCase
from unittest.mock import patch

from coinquant.campaign import Campaign
from coinquant.config import Config
from coinquant.dfii10 import Source
from coinquant.session import run
from coinquant.state import State
from coinquant.types import Unknown
from tests.session_venue import Venue


class MacroInputTests(TestCase):
    def setUp(self):
        self.risk=patch('coinquant.campaign.PRIMARY_RISK','6');self.risk.start()
        self.tmp=tempfile.TemporaryDirectory();self.directory=self.tmp.name
        self.venue=Venue();self.venue.seed(self.directory)
    def tearDown(self):self.tmp.cleanup();self.risk.stop()
    def session(self,seconds=1):
        return run(Config('123',self.directory,seconds,1),self.venue,execute=True,
                   monotonic=self.venue.monotonic,wait=self.venue.wait)
    def edit(self,change):
        with State(self.directory,'binance:BTCUSDT:live:123') as state:
            model=Campaign.restore(state.get('linear_campaign'));change(model,state)
            state.set('linear_campaign',model.checkpoint())
    def macro_down(self):
        def down():raise Unknown('fixture ALFRED outage')
        self.venue.dfii10_snapshot=down
    def eligible_row(self):
        return dict(missing_reason=None,latest_value='1',prior20_value='1.3',
                    latest_observation_date=datetime.fromtimestamp(self.venue.now/1000,timezone.utc).date().isoformat(),
                    latest_value_available_ms=self.venue.now-1000,prior20_value_available_ms=self.venue.now-1000)

    def test_primary_exit_does_not_wait_for_dfii10(self):
        self.session();self.assertGreater(self.venue.q,0)
        self.edit(lambda model,state:setattr(model.model,'active',None))
        self.macro_down()
        result=self.session()
        self.assertEqual(self.venue.q,0)
        self.assertEqual(result['cleanup'],'verified',result)

    def test_macro_position_keeps_protection_without_dfii10(self):
        def macro(model,state):
            model.model.active=None;model.daily_lows.extend([D(90000)]*10)
        self.edit(macro);self.venue.dfii10_snapshot=self.eligible_row
        self.session();self.assertGreater(self.venue.q,0)
        before=len(self.venue.sent);self.macro_down()
        result=self.session()
        self.assertGreater(self.venue.q,0)
        self.assertEqual(len(self.venue.sent),before)
        self.assertTrue(result['actual']['native_full_position_protected'])
        self.assertTrue(any('DFII10' in e['reason'] or 'ALFRED' in e['reason'] for e in result['errors']),result['errors'])

    def test_interrupted_cold_start_still_consumes_the_macro_state(self):
        def cold(model,state):
            model.daily_lows.extend([D(90000)]*10);state.set('market_bootstrap',True)
        self.edit(cold);self.macro_down()
        self.session()
        with State(self.directory,'binance:BTCUSDT:live:123') as state:
            self.assertTrue(state.get('market_bootstrap'))
        self.venue.dfii10_snapshot=self.eligible_row
        result=self.session()
        self.assertEqual(self.venue.sent,[])
        self.assertEqual(result['model_preview']['action'],'consumed')
        with State(self.directory,'binance:BTCUSDT:live:123') as state:
            self.assertFalse(state.get('market_bootstrap'))


class SourceBudgetTests(TestCase):
    def test_reads_share_the_budget_and_failures_are_not_repeated_each_poll(self):
        timeouts=[]
        class Opener:
            def open(self,request,timeout):
                timeouts.append(timeout);raise TimeoutError()
        source=Source()
        with patch('coinquant.dfii10.build_opener',return_value=Opener()):
            with self.assertRaises(Unknown):source.snapshot(1_000_000,budget=4)
            with self.assertRaises(Unknown):source.snapshot(1_030_000,budget=4)
            self.assertEqual(len(timeouts),1)
            with self.assertRaises(Unknown):source.snapshot(1_061_000,budget=4)
        self.assertEqual(len(timeouts),2)
        self.assertLessEqual(max(timeouts),4)

    def test_missing_time_zone_data_fails_with_an_actionable_error(self):
        code=('import coinquant.dfii10 as m\n'
              'try:m.eastern()\n'
              'except m.Blocked as e:print(e)\n')
        env=dict(os.environ,PYTHONTZPATH='',PYTHONPATH=os.getcwd())
        done=subprocess.run([sys.executable,'-S','-c',code],capture_output=True,text=True,env=env,timeout=10)
        self.assertEqual(done.returncode,0,done.stderr)
        self.assertIn('tzdata',done.stdout)


# These saved scenarios seed legacy SX60/DFII10 checkpoints explicitly.
from tests.legacy_policy import legacy_policy
setUpModule, tearDownModule = legacy_policy()
