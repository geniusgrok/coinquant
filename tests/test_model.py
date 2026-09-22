import unittest
from dataclasses import replace
from decimal import Decimal as D

from coinquant.model import bankruptcy_price, decide, liquidation_price, protected, repair_target, _reward_from_stop, _safe_new_entry_stop, validate_bars, validate_risk_increase
from coinquant.types import Bar, Blocked, INTERVAL_MS, ModelConfig, Position, Rules, Snapshot, Target, number


def sample(position=None):
    return Snapshot('12345', 150 * INTERVAL_MS, D('0.05'), D('0.04'),
                    D(30745), D(30744), D(30746), D(100000), D(100000),
                    position or Position(), Rules(D('0.5'), D(1), D(1), D(100000),
                    D(100000), D('0.005'), D('0.00075'), 1514764800000), funding_rate=D('0.0001'))


def history():
    return [Bar(i * INTERVAL_MS, D(30000 + i * 5), D(30001 + i * 5),
                D(29999 + i * 5), D(30000 + i * 5), D(1000000)) for i in range(150)]


class ModelTests(unittest.TestCase):
    def test_inverse_pnl_and_collateral_equity(self):
        p = Position(D(1000), D(10000))
        self.assertEqual(p.pnl(D(20000)), D('0.05'))
        s = replace(sample(), wallet_btc=D('0.1'), mark=D(20000), position=p)
        self.assertEqual(s.equity_usd, D(3000))
        self.assertEqual(replace(s, position=Position()).equity_usd, D(2000))

    def test_stop_risk_margin_and_discrete_contracts(self):
        s = sample()
        t = decide(history(), s, ModelConfig())
        self.assertGreater(t.quantity, 0)
        self.assertEqual(t.quantity % s.rules.step, 0)
        self.assertLessEqual(t.risk_btc, s.equity_btc * D('0.006'))
        self.assertEqual(t.initial_margin_btc, abs(t.quantity) / t.entry / 20)
        self.assertLess(t.stop_loss, s.mark)
        self.assertGreater(t.take_profit, s.mark)
        self.assertLessEqual(abs(t.quantity), s.rules.risk_limit_usd)

    def test_execution_friction_cannot_put_entry_beyond_take_profit(self):
        bars = [
            Bar(146 * INTERVAL_MS, D(20000), D(20001), D(19999), D(20000), D(1000000)),
            Bar(147 * INTERVAL_MS, D(20000), D(20001), D(19999), D(20000), D(1000000)),
            Bar(148 * INTERVAL_MS, D(20000), D(20002), D(19999), D(20001), D(1000000)),
            Bar(149 * INTERVAL_MS, D(20001), D(20003), D(20000), D(20002), D(1000000)),
        ]
        s = replace(sample(), mark=D('20003.5'), bid=D('20001.5'), ask=D('20005.5'))
        cfg = replace(ModelConfig(), trend_bars=2, channel_bars=2, atr_bars=2)
        t = decide(bars, s, cfg)
        self.assertEqual(t.trigger_price, 0)
        self.assertGreater(t.entry, s.mark)
        self.assertLess(t.stop_loss, s.mark)
        self.assertGreater(t.take_profit, t.entry)
        self.assertGreaterEqual(
            t.take_profit - t.entry,
            (t.entry - t.stop_loss) * cfg.reward_multiple,
        )
        validate_risk_increase(s, t, cfg)

    def test_new_entry_stop_rounds_inward_before_liquidation_boundary(self):
        rules = sample().rules
        reference, entry = D("7432.5"), D("7441.0")
        old_sl = D("7149.5")
        sl = _safe_new_entry_stop(reference, entry, 1, old_sl, rules)
        self.assertEqual(sl, D("7150.0"))
        tp, _ = _reward_from_stop(reference, entry, 1, sl, D(3), rules.tick)
        self.assertGreater(tp, entry)
        target = Target(0, D(1), entry, tp, sl, D(1) / entry / 20,
                        D(1) / entry / 20, D("0.0001"), "boundary")
        liq = liquidation_price(target.quantity, target.entry, target.initial_margin_btc,
                                rules.maintenance_rate, rules.taker_fee)
        self.assertGreater(sl, liq + max(rules.tick * 2, reference * D("0.003")))

    def test_shared_prewrite_validator_rejects_forged_risk(self):
        s, cfg = sample(), ModelConfig()
        t = decide(history(), s, cfg)
        validate_risk_increase(s, t, cfg, notional_limit=D(100000))
        with self.assertRaises(Blocked):
            validate_risk_increase(s, replace(t, quantity=t.quantity * 2), cfg,
                                   notional_limit=D(100000))

    def test_no_future_or_gap_candles(self):
        bars = history()
        with self.assertRaises(Blocked):
            validate_bars(bars, bars[-1].time)
        with self.assertRaises(Blocked):
            validate_bars(bars[:40] + bars[41:], sample().time)
        with self.assertRaises(Blocked):
            validate_bars(bars, sample().time + INTERVAL_MS)

    def test_causal_prefix_is_not_changed_by_future_rows(self):
        bars = history()
        target = decide(bars, sample(), ModelConfig())
        future = Bar(150 * INTERVAL_MS, D(1), D(1), D(1), D(1))
        extended = bars + [future]
        self.assertEqual(target, decide(extended[:150], sample(), ModelConfig()))
        with self.assertRaises(Blocked):
            decide(extended, sample(), ModelConfig())

    def test_mode_leverage_and_account_errors(self):
        for s in (replace(sample(), margin_mode='REGULAR_MARGIN'),
                  replace(sample(), position=Position(leverage=D(21))),
                  replace(sample(), position=Position(index=1)),
                  replace(sample(), ask=D(100))):
            with self.assertRaises(Blocked):
                decide(history(), s, ModelConfig())

    def test_bankruptcy_price_consumes_margin_after_closing_fee(self):
        r = sample().rules
        for quantity in (D(1000), D(-1000)):
            entry, margin = D(10000), D('.005')
            price = bankruptcy_price(quantity, entry, margin, r.taker_fee)
            pnl = quantity * (D(1) / entry - D(1) / price)
            close_fee = abs(quantity) * r.taker_fee / price
            self.assertAlmostEqual(margin + pnl - close_fee, D(0))

    def test_liquidation_and_repair_for_both_directions(self):
        for sign in (-1, 1):
            q, price = D(sign * 1000), D(30745)
            margin = abs(q) / price / 20
            liq = liquidation_price(q, price, margin, D('0.005'), D('0.00075'))
            p = Position(q, price, margin, liq)
            s = sample(p)
            t = repair_target(s, ModelConfig())
            self.assertTrue(protected(s, t.take_profit, t.stop_loss))
            self.assertFalse(protected(s))

    def test_authorized_notional_is_a_sizing_cap_not_a_failed_order(self):
        t = decide(history(), sample(), ModelConfig(), notional_limit=D(10))
        self.assertGreater(t.quantity, 0)
        self.assertLessEqual(t.quantity, 10)
        with self.assertRaises(Blocked):
            decide(history(), sample(), ModelConfig(), notional_limit=D('NaN'))

    def test_invalid_and_nonfinite_numbers(self):
        for text in ('NaN', 'Infinity', '-Infinity', 'not-a-number', ''):
            with self.assertRaises(Blocked):
                number(text)

    def test_single_order_max_does_not_cap_immediate_total_target(self):
        s = replace(sample(), rules=replace(sample().rules, maximum=D(5)))
        t = decide(history(), s, ModelConfig())
        self.assertGreater(abs(t.quantity), s.rules.maximum)
        self.assertLessEqual(abs(t.quantity), s.rules.risk_limit_usd)

    def test_risk_tier_bounds_total_target(self):
        s = replace(sample(), rules=replace(
            sample().rules, maximum=D(5), risk_limit_usd=D(30)))
        t = decide(history(), s, replace(ModelConfig(), risk_fraction=D('.5')))
        self.assertLessEqual(abs(t.quantity), D(30))
        with self.assertRaisesRegex(Blocked, 'total position limits'):
            validate_risk_increase(
                s, replace(t, quantity=D(31), risk_btc=D(1)),
                replace(ModelConfig(), risk_fraction=D('.5')),
                notional_limit=D(100000))

    def test_no_collateral_price_risk_is_hidden_when_flat(self):
        s = sample()
        self.assertEqual(replace(s, mark=s.mark / 2).equity_usd, s.equity_usd / 2)


if __name__ == '__main__':
    unittest.main()
