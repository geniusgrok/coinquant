from decimal import Decimal as D
import tempfile
import unittest

from coinquant.campaign import DAY, ORIGIN, Campaign as Default
from coinquant.state import State
from coinquant.types import Blocked
from research.return_core import Forecast, FUNDING_INTERVAL, campaign_class, configured


class ReturnCoreTests(unittest.TestCase):
    def inputs(self):
        # Synthetic protocol fixtures, not market evidence or real funding.
        bars = []
        for i in range(440):
            t = ORIGIN+(i-360)*DAY
            p = D(10000)*D('1.001')**i
            bars.append((t, p, p*D('1.002'), p*D('.998'), p*D('1.0002')))
        funding = [(t, t+FUNDING_INTERVAL, D('.0001'), None)
                   for t in range(bars[0][0], bars[-1][0]+DAY, FUNDING_INTERVAL)]
        return bars, funding

    def model(self, book):
        cls = campaign_class(book)
        model = cls()
        for i in range(1, 91):
            p = D(10000)+i
            model.update(ORIGIN+i*14400000, p, p, p)
        model.select_macro(None, D(10100), model.last+1000)
        return cls, model

    def test_future_prices_and_unmatured_funding_do_not_change_forecast(self):
        bars, funding = self.inputs()
        book = Forecast(bars, funding)
        call = bars[330][0]+DAY+59999
        self.assertEqual(book.at(call)['day_ms'], bars[329][0])
        changed_bars = bars[:331]+[(t, o*2, h*2, l*2, c*2) for t, o, h, l, c in bars[331:]]
        changed_funding = [(t, a, r if a < call else D('.1'), cause) for t, a, r, cause in funding]
        changed = Forecast(changed_bars, changed_funding)
        self.assertEqual(book.at(call), changed.at(call))
        self.assertLess(book.at(call)['latest_label_available_ms'], book.at(call)['available_ms'])

    def test_missing_settlement_is_not_a_zero_label_and_maturity_includes_funding_lag(self):
        bars, funding = self.inputs()
        book = Forecast(bars, funding)
        label = book.labels[0]
        omitted_slot = label['exit_ms']-60000
        changed = Forecast(bars, [r for r in funding if r[0] != omitted_slot])
        self.assertNotIn(label['day_ms'], [r['day_ms'] for r in changed.labels])
        self.assertEqual(label['available_ms'], omitted_slot+FUNDING_INTERVAL)
        self.assertEqual(label['net_return'], label['gross_return']-label['fees']-label['funding'])

    def test_consumed_positive_regime_does_not_reopen_after_confirmed_flat(self):
        bars, funding = self.inputs()
        book = Forecast(bars, funding)
        cls, model = self.model(book)
        self.assertIsNotNone(model.active)
        identity = model.active.identity
        model.filled(identity)
        model.position_campaign = None
        model.select_macro(None, D(10100), model.last+2000)
        self.assertEqual(model.active.identity, identity)
        self.assertEqual(model.action(D(0)), 'consumed')
        self.assertEqual(cls.restore(model.checkpoint()).checkpoint(), model.checkpoint())
        with self.assertRaises(Blocked):
            Default.restore(model.checkpoint())

    def test_foreign_input_checkpoint_and_existing_default_wallet_rejected_before_recovery(self):
        bars, funding = self.inputs()
        book = Forecast(bars, funding)
        _, model = self.model(book)
        other = Forecast(bars, [(t, a, r*2, cause) for t, a, r, cause in funding])
        with self.assertRaises(Blocked):
            campaign_class(other).restore(model.checkpoint())
        with tempfile.TemporaryDirectory() as folder, State(folder, 'test-return-core') as state:
            state.set('linear_campaign', Default().checkpoint())
            with configured(book, binding={'synthetic_fixture': 'a'*64}):
                from coinquant import session
                with self.assertRaises(Blocked):
                    session._guard_strategy(state)
            self.assertIsNone(state.get('lifecycle_identity'))

    def test_native_adapter_is_refused_before_any_clock_and_scoped_identity_restores(self):
        bars, funding = self.inputs()
        book = Forecast(bars, funding)
        from coinquant import linear_preview, session
        old = linear_preview.Campaign
        class Private:
            def clock(self):
                self.fail = True
                raise AssertionError('private clock called')
        reader = Private()
        with configured(book, binding={'synthetic_fixture': 'a'*64}) as runtime:
            with self.assertRaises(Blocked):
                runtime.run(None, reader)
        self.assertFalse(hasattr(reader, 'fail'))
        self.assertIs(linear_preview.Campaign, old)
        self.assertIsNone(session._LIFECYCLE_IDENTITY)

    def test_no_perpetual_funding_history_means_no_fit(self):
        bars, _ = self.inputs()
        book = Forecast(bars, [])
        self.assertEqual(book.labels, [])
        self.assertTrue(all(r['prediction'] is None for r in book.rows))


if __name__ == '__main__':
    unittest.main()
