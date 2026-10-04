from decimal import Decimal as D
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from coinquant.core import Campaign
from coinquant.campaign import Campaign as Legacy, ORIGIN, DAY
from coinquant.target import exposure
from coinquant.types import Blocked, Unknown
from coinquant.state import State
from coinquant.lifecycle import Lifecycle
from coinquant.session import cycle


class CoreTests(unittest.TestCase):
    def model(self):
        m=Campaign()
        for i in range(1,6*80+1):
            p=D(100)*D('1.005')**(D(i)/6)
            m.update(ORIGIN+i*14400000,p,p,p)
        return m

    def test_core_restore_and_forecast_direction(self):
        m=self.model();self.assertGreater(m.target,0)
        r=Campaign.restore(m.checkpoint());self.assertEqual(r.checkpoint(),m.checkpoint())
        self.assertFalse(m.macro_relevant())
        self.assertEqual(exposure(list(reversed(m.closes)),mode='uptrend'),0)
        self.assertLess(exposure(list(reversed(m.closes)),mode='downside'),0)
        with self.assertRaises(Blocked):Campaign.restore(Legacy().checkpoint())

    def test_reconstruction_does_not_claim_a_fill_or_allow_unknown_position(self):
        m=self.model();self.assertEqual(m.action(D(0)),'enter')
        self.assertIsNone(m.position_campaign)
        with self.assertRaises(Blocked):m.action(D(1))
        m.select_macro(None,m.model.close,m.last+1000)
        m.filled(m.active.identity);self.assertEqual(m.action(D(1)),'hold')
        r=Campaign.restore(m.checkpoint());self.assertEqual(r.position_campaign,m.active.identity)

    def test_foreign_strategy_rejects_before_exchange_access(self):
        with tempfile.TemporaryDirectory() as folder,State(folder,'binance:BTCUSDT:live:123') as state:
            state.set('linear_campaign',Legacy().checkpoint())
            with self.assertRaises(Blocked):cycle(object(),state,'123',execute=True)

    def test_missing_checkpoint_cannot_recover_an_old_entry(self):
        with tempfile.TemporaryDirectory() as folder,State(folder,'binance:BTCUSDT:live:123') as state:
            state.set('entry_plan',dict(campaign=10))
            with self.assertRaisesRegex(Blocked,'lacks its BTC core checkpoint'):
                cycle(object(),state,'123',execute=True)

    def test_trim_target_is_synced_before_unknown_reduction(self):
        with tempfile.TemporaryDirectory() as folder,State(folder,'binance:BTCUSDT:live:123') as state:
            state.set('entry_fill',dict(campaign=10,requested='9',session=1))
            state.set('position_protection',dict(campaign=10))
            engine=Lifecycle(SimpleNamespace(capital_limit=None),state,'123',authorized=True,session=2)
            engine.planned_protection=lambda s:True;engine.instrument=lambda:{};engine.epoch=lambda:30
            model=SimpleNamespace(active=SimpleNamespace(identity=10),entry_fraction=lambda f:D('.5'))
            snap=dict(quantity_btc='1',mark_price='100',equity_usdt='100',possible_entry_remainders=0)
            with patch('coinquant.lifecycle.market_quantity',return_value=D('.5')),patch('coinquant.lifecycle.safety.reduce_existing',side_effect=Unknown('transport outcome unknown')):
                with self.assertRaises(Unknown):engine.rebalance(model,snap)
            self.assertEqual(state.get('entry_fill')['requested'],'0.5')
            self.assertEqual(state.get('entry_fill')['session'],2)
