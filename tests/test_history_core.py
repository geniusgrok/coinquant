from decimal import Decimal as D
import tempfile
import unittest

from coinquant.campaign import DAY, ORIGIN, Campaign as Default
from coinquant.state import State
from coinquant.types import Blocked
from research.history_core import Signals, campaign_class, runtime
from tests.session_venue import Venue


class HistoryCoreTests(unittest.TestCase):
    def signals(self, source='a'*64):
        bars = []
        for i in range(140):
            t = ORIGIN+(i-100)*DAY
            p = D(120000)*D('.997')**i
            bars.append((t,p,p*D('1.002'),p*D('.998'),p))
        return Signals(bars,'ma',source),bars

    def model(self, signals):
        cls = campaign_class(signals)
        model = cls()
        for i in range(1,91):
            p = D(90000)*D('.9995')**i
            model.update(ORIGIN+i*14400000,p,p,p)
        model.select_macro(None,D(100000),model.last+1000)
        return cls,model

    def test_future_prices_do_not_change_known_forecast_or_publication_boundary(self):
        signals,bars = self.signals()
        call = bars[115][0]+DAY+59999
        self.assertEqual(signals.at(call)['day_ms'],bars[114][0])
        changed = Signals(bars[:116]+[(bars[116][0],D(1),D(1),D(1),D(1))],'ma','b'*64)
        self.assertEqual(signals.at(call),changed.at(call))

    def test_owned_short_restores_and_foreign_input_and_default_reject(self):
        signals,_ = self.signals()
        cls,model = self.model(signals)
        self.assertEqual(model.active.direction,-1)
        model.filled(model.active.identity)
        self.assertEqual(model.action(D('-.01')),'hold')
        self.assertEqual(cls.restore(model.checkpoint()).checkpoint(),model.checkpoint())
        other,_ = self.signals('b'*64)
        with self.assertRaises(Blocked):campaign_class(other).restore(model.checkpoint())
        with self.assertRaises(Blocked):Default.restore(model.checkpoint())

    def test_real_shared_cycle_funds_short_and_installs_buy_close_all_protection(self):
        signals,_ = self.signals()
        cls,model = self.model(signals)
        venue = Venue(direction=-1)
        venue.offline = True
        venue.now = venue.updated = model.last+1000
        venue.completed_market = lambda **kwargs:dict(interval_ms=14400000,complete_through=model.last,candles=[])
        with tempfile.TemporaryDirectory() as folder,State(folder,'binance:BTCUSDT:live:123') as state:
            state.set('linear_campaign',model.checkpoint())
            state.set('market_bootstrap',False)
            with runtime(signals) as session:
                report = session.cycle(venue,state,'123',execute=True,session=1)
            self.assertLess(venue.q,0)
            self.assertTrue(any(o['side']=='SELL' and not o['reduceOnly'] for o in venue.orders.values()))
            active = [a for a in venue.algos.values() if a['algoStatus']=='NEW']
            self.assertEqual(len(active),2)
            self.assertTrue(all(a['side']=='BUY' and a['closePosition'] for a in active))
            self.assertGreater(venue.liquidation(),D(state.get('position_protection')['stop']))
