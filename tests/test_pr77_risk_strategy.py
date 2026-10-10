from decimal import Decimal as D
import hashlib
import json
from unittest import TestCase

from coinquant.campaign import Campaign, ORIGIN
from coinquant.native_preview import commission, entry_preview, holding_risk, limit_matches, topup_preview
from coinquant.opportunities import FOUR_HOURS, Opportunity
from coinquant.types import Blocked, Unknown
from tests import test_native_preview


class TrialSizingTests(TestCase):
    def fixture(self):
        return test_native_preview.NativePreviewTests().fixture()

    def test_configured_fraction_is_the_entry_loss_budget(self):
        model, reader, snapshot, _, _ = self.fixture()
        reader.loss_fraction = D('.99')
        plan = entry_preview(reader, model, snapshot)
        self.assertEqual(D(plan['stop_budget_usdt']), D(990))
        q, price, stop, fee = (D(plan[k]) for k in ('quantity_btc', 'entry_estimate', 'stop', 'fee'))
        loss = q * (price - stop + price * fee + stop * (D('.01') + D('1.01') * fee))
        self.assertLessEqual(loss, 990)
        self.assertLessEqual(D(plan['allocated_margin_usdt']), D(snapshot['wallet_usdt']))

    def test_add_counts_automatic_initial_margin_on_top_of_existing_collateral(self):
        model, reader, snapshot, _, _ = self.fixture()
        held = dict(snapshot, quantity_btc='1', entry='100', isolated_wallet_usdt='249', available_usdt='751')
        reader.snapshot.return_value = dict(held)
        plan = topup_preview(reader, model, held, '5', '90', '200.1', '30', '1000', '.01',
                             paid_commission_usdt='.05', realized_pnl_usdt='0', paid_funding_usdt='0')
        add = D(plan['quantity_btc'])
        self.assertGreater(add, 0)
        actual_margin = D(249) + add * D(plan['entry_estimate']) / 20
        self.assertLessEqual(actual_margin, D(plan['allocated_margin_usdt']))
        self.assertLessEqual(D(plan['allocated_margin_usdt']), D(held['wallet_usdt']))

    def test_new_position_leaves_margin_room_for_its_paid_fee_and_mark_loss(self):
        model, reader, snapshot, _, _ = self.fixture()
        model.model.active = Opportunity(model.last, 1, D(99), D(200), model.last + FOUR_HOURS)
        plan = entry_preview(reader, model, snapshot)
        self.assertIn(plan['constraint'], ('target', 'margin_or_funding_cap', 'liquidity_cap', 'notional_cap'))
        q, price, fee = (D(plan[key]) for key in ('quantity_btc', 'entry_estimate', 'fee'))
        self.assertGreater(q, 0)
        self.assertLessEqual(D(plan['allocated_margin_usdt']), D(snapshot['wallet_usdt']))

    def test_add_cash_requirement_uses_available_balance(self):
        model, reader, snapshot, _, _ = self.fixture()
        held = dict(snapshot, quantity_btc='1', entry='100', isolated_wallet_usdt='200', available_usdt='5')
        reader.snapshot.return_value = dict(held)
        plan = topup_preview(reader, model, held, '5', '90', '200.1', '30', '1000', '.01',
                             paid_commission_usdt='.05', realized_pnl_usdt='0', paid_funding_usdt='0')
        add, price = D(plan['quantity_btc']), D(plan['entry_estimate'])
        self.assertGreater(add, 0)
        cash = D(plan['allocated_margin_usdt']) - 200 + add * price * D('.0005')
        cash += (1 + add) * price * D('.0105')
        self.assertLessEqual(cash, 5)

    def test_old_large_frozen_budget_cannot_erase_realized_losses_on_an_add(self):
        model, reader, snapshot, _, _ = self.fixture()
        reader.loss_fraction = D('.99')
        held = dict(snapshot, quantity_btc='.2', entry='100', wallet_usdt='904.99',
                    equity_usdt='904.99', isolated_wallet_usdt='10', available_usdt='894.99')
        reader.snapshot.return_value = dict(held)
        plan = topup_preview(reader, model, held, '100', '90', '200.1', '490', '1000', '.01',
                             paid_commission_usdt='.01', realized_pnl_usdt='-95', paid_funding_usdt='0')
        add, price = D(plan['quantity_btc']), D(plan['entry_estimate'])
        self.assertEqual(D(plan['stop_budget_usdt']), 490)
        loss = D('95.01') + D('.2') * 10 + add * (price - 90) + add * price * D('.0005')
        loss += (D('.2') + add) * 90 * (D('.01') + D('1.01') * D('.0005'))
        self.assertLessEqual(loss, 490)

    def test_add_funds_the_open_loss_when_the_book_diverges_from_mark(self):
        model, reader, snapshot, values, _ = self.fixture()
        held = dict(snapshot, quantity_btc='1', entry='100', isolated_wallet_usdt='200', available_usdt='5')
        reader.snapshot.return_value = dict(held)
        values['/fapi/v1/depth'].update(bids=[['109.9', '1000']], asks=[['110', '1000']])
        plan = topup_preview(reader, model, held, '5', '90', '200.1', '30', '1000', '.01',
                             paid_commission_usdt='.05', realized_pnl_usdt='0', paid_funding_usdt='0')
        add, price = D(plan['quantity_btc']), D(plan['entry_estimate'])
        self.assertGreater(add, 0)
        cash = D(plan['allocated_margin_usdt']) - 200 + add * price * D('.0005')
        cash += (1 + add) * price * D('.0105') + add * (price - 100)
        self.assertLessEqual(cash, 5)

    def test_collateral_change_during_preflight_requires_a_new_plan(self):
        model, reader, snapshot, _, _ = self.fixture()
        held = dict(snapshot, quantity_btc='1', entry='100', isolated_wallet_usdt='200', available_usdt='800')
        reader.snapshot.return_value = dict(held, isolated_wallet_usdt='249', available_usdt='751')
        with self.assertRaises(Unknown):
            topup_preview(reader, model, held, '5', '90', '200.1', '30', '1000', '.01',
                          paid_commission_usdt='.05', realized_pnl_usdt='0', paid_funding_usdt='0')

    def test_paid_funding_cannot_be_spent_again_after_wallet_and_margin_checks_pass(self):
        model, reader, snapshot, values, _ = self.fixture()
        # A partial fill paid .4004 commission, then 1 USDT funding. Its raw
        # committed target still allows another native .001 BTC without the debit.
        held = dict(snapshot, quantity_btc='.008', entry='100100', mark_price='100100',
                    wallet_usdt='998.5996', equity_usdt='998.5996',
                    isolated_wallet_usdt='165', available_usdt='833.5996')
        reader.snapshot.return_value = dict(held)
        values['/fapi/v1/depth'].update(bids=[['99999.9', '1000']], asks=[['100000', '1000']])
        requested = D(100) / D('11095.5')
        args = (reader, model, held, requested, '90000', '200000', '100', '1000', '.01')
        costs = dict(paid_commission_usdt='.4004', realized_pnl_usdt='0')
        omitted = topup_preview(*args, paid_funding_usdt='0', **costs)
        self.assertEqual(D(omitted['quantity_btc']), D('.001'))
        self.assertLess(D(omitted['allocated_margin_usdt']), D(held['wallet_usdt']) * D('.25'))
        modeled_loss = (D('.008') + D(omitted['quantity_btc'])) * D('11095.5')
        self.assertEqual(modeled_loss + 1, D('100.8595'))
        bounded = topup_preview(*args, paid_funding_usdt='1', **costs)
        self.assertEqual(D(bounded['quantity_btc']), 0)
        self.assertLessEqual((D('.008') + D(bounded['quantity_btc'])) * D('11095.5') + 1, 100)
        for unknown in (None, '-1', 'NaN'):
            with self.subTest(funding=unknown), self.assertRaises((Blocked, Unknown)):
                topup_preview(*args, paid_funding_usdt=unknown, **costs)

    def test_final_book_checks_depth_and_price_inside_the_same_tick(self):
        model, reader, snapshot, values, _ = self.fixture()
        plan = entry_preview(reader, model, snapshot)
        args = dict(quote_observation=plan['quote_observation'], quantity=plan['quantity_btc'])
        self.assertTrue(limit_matches(reader, 1, plan['entry_estimate'], '.1', **args))
        values['/fapi/v1/depth']['asks'] = [['100', '10']]
        self.assertFalse(limit_matches(reader, 1, plan['entry_estimate'], '.1', **args))
        # A one-tick ask move that still leaves the funded limit inside the fresh
        # 0.1% allowance is executable. A lower ask that puts the limit outside is not.
        values['/fapi/v1/depth']['asks'] = [['100.1', '1000']]
        self.assertTrue(limit_matches(reader, 1, plan['entry_estimate'], '.1', **args))
        values['/fapi/v1/depth'].update(bids=[['99.7', '1000']], asks=[['99.9', '1000']])
        self.assertFalse(limit_matches(reader, 1, plan['entry_estimate'], '.1', **args))
        values['/fapi/v1/depth'].update(bids=[['99.9', '1000']], asks=[['100', '1000']])
        self.assertFalse(limit_matches(reader, 1, plan['entry_estimate'], '.1',
                                       quote_observation=plan['quote_observation'], quantity='251'))

    def test_add_cannot_spend_an_already_locked_campaign_profit(self):
        model, reader, snapshot, values, _ = self.fixture()
        held = dict(snapshot, quantity_btc='1', entry='100', mark_price='300',
                    wallet_usdt='999.95', equity_usdt='1199.95', isolated_wallet_usdt='150', available_usdt='849.95')
        reader.snapshot.return_value = dict(held)
        values['/fapi/v1/depth'].update(bids=[['299.9', '1000']], asks=[['300', '1000']])
        args = (reader, model, held, '5', '250', '1000', '100', '1000', '.01')
        costs = dict(paid_commission_usdt='.05', realized_pnl_usdt='0', paid_funding_usdt='0')
        loose = topup_preview(*args, **costs)
        locked = topup_preview(*args, loss_ceiling_usdt='-140', **costs)
        self.assertEqual(locked['quantity_btc'], loose['quantity_btc'])
        self.assertEqual(D(locked['stop_budget_usdt']), 100)
        self.assertEqual(D(locked['loss_ceiling_usdt']), 100)


class HoldingRiskTests(TestCase):
    def fixture(self, quantity='8', mark='100'):
        model, _, snapshot, _, instrument = test_native_preview.NativePreviewTests().fixture()
        q, price = D(quantity), D(mark)
        paid = abs(q) * 100 * D('.0005')
        wallet = 1000 - paid
        snapshot.update(quantity_btc=quantity, entry='100', mark_price=mark,
                        wallet_usdt=str(wallet), equity_usdt=str(wallet + q * (price - 100)),
                        isolated_wallet_usdt='50', available_usdt=str(wallet - 50))
        protection = dict(campaign=model.last, stop='90' if q > 0 else '110')
        fill = dict(campaign=model.last, stop_budget='100', sizing_capital='1000', stop_slippage_fraction='.01')
        costs = dict(paid_commission_usdt=str(paid), realized_pnl_usdt='0', paid_funding_usdt='0',
                     loss_fraction='.10', slip_fraction='.01')
        return snapshot, protection, fill, instrument, costs

    def test_paid_funding_tightens_an_existing_over_budget_position(self):
        snapshot, protection, fill, instrument, costs = self.fixture()
        before = holding_risk(snapshot, protection, fill, instrument, '.0005', **costs)
        self.assertEqual(before['action'], 'hold')
        protection['loss_ceiling_usdt'] = before['loss_ceiling_usdt']
        snapshot.update(wallet_usdt='979.6', equity_usdt='979.6')
        costs['paid_funding_usdt'] = '20'
        plan = holding_risk(snapshot, protection, fill, instrument, '.0005', **costs)
        self.assertEqual(plan['action'], 'hold')
        self.assertEqual(plan['stop'], '90')
        self.assertEqual(D(plan['loss_ceiling_usdt']), 100)
        self.assertGreater(D(plan['current_protected_loss_usdt']), 100)

    def test_observed_profit_lock_survives_funding_price_retreat_and_deposits(self):
        snapshot, protection, fill, instrument, costs = self.fixture('1', '300')
        peak = holding_risk(snapshot, protection, fill, instrument, '.0005', **costs)
        self.assertEqual(peak['action'], 'hold')
        self.assertEqual(peak['stop'], protection['stop'])
        self.assertEqual(D(peak['loss_ceiling_usdt']), 100)
        snapshot.update(mark_price='250', wallet_usdt='994.95', equity_usdt='1144.95')
        costs['paid_funding_usdt'] = '5'
        funded = holding_risk(snapshot, protection, fill, instrument, '.0005', **costs)
        self.assertEqual(funded['action'], 'hold')
        self.assertEqual(funded['stop'], protection['stop'])
        self.assertEqual(funded['loss_ceiling_usdt'], peak['loss_ceiling_usdt'])
        snapshot.update(wallet_usdt='1994.95', equity_usdt='2144.95')
        deposited = holding_risk(snapshot, protection, fill, instrument, '.0005', **costs)
        self.assertEqual(deposited['action'], 'hold')
        self.assertEqual(deposited['stop'], protection['stop'])

    def test_partial_reduction_keeps_realized_profit_fees_and_the_old_stop(self):
        snapshot, protection, fill, instrument, costs = self.fixture('1', '300')
        peak = holding_risk(snapshot, protection, fill, instrument, '.0005', **costs)
        protection.update(stop=peak['stop'], loss_ceiling_usdt=peak['loss_ceiling_usdt'])
        snapshot.update(quantity_btc='.5', mark_price='250', wallet_usdt='1074.8875', equity_usdt='1149.8875')
        costs.update(paid_commission_usdt='.1125', realized_pnl_usdt='75')
        plan = holding_risk(snapshot, protection, fill, instrument, '.0005', **costs)
        self.assertEqual(D(plan['current_mark_loss_usdt']), D('-149.8875'))
        self.assertLessEqual(D(plan['loss_ceiling_usdt']), D(peak['loss_ceiling_usdt']))
        self.assertGreaterEqual(D(plan['stop']), D(peak['stop']))
        self.assertLessEqual(D(plan['modeled_stop_loss_usdt']), D(plan['loss_ceiling_usdt']))

    def test_manage_only_uses_frozen_parameters_and_lowered_capital_still_tightens(self):
        snapshot, protection, fill, instrument, costs = self.fixture()
        fill.update(stop_budget='20', stop_slippage_fraction='.02')
        costs.update(loss_fraction=None, slip_fraction=None)
        plan = holding_risk(snapshot, protection, fill, instrument, '.0005', **costs)
        self.assertEqual(plan['action'], 'hold')
        self.assertEqual(plan['stop'], '90')
        self.assertEqual(D(plan['loss_ceiling_usdt']), 20)
        snapshot, protection, fill, instrument, costs = self.fixture('1')
        snapshot['isolated_wallet_usdt'] = '20'
        lowered = holding_risk(snapshot, protection, fill, instrument, '.0005', capital_limit='100', **costs)
        self.assertEqual(lowered['action'], 'hold')
        self.assertEqual(lowered['stop'], '90')
        self.assertEqual(D(lowered['current_stop_budget_usdt']), 10)
        self.assertEqual(D(lowered['loss_ceiling_usdt']), 100)

    def test_known_collateral_breach_exits_even_without_budget_or_cost_sources(self):
        snapshot, _, _, instrument, _ = self.fixture('1')
        instrument['quotePrecision'] = 2
        snapshot['isolated_wallet_usdt'] = '249.99'
        with self.assertRaises(Unknown):
            holding_risk(snapshot, None, None, instrument)
        snapshot.update(quantity_btc='20', mark_price='10', wallet_usdt='1000', equity_usdt='-800')
        plan = holding_risk(snapshot, None, None, instrument)
        self.assertEqual((plan['action'], plan['reason']), ('exit', 'nonpositive_risk_capital'))

    def test_unknown_costs_or_frozen_geometry_cannot_be_reported_as_safe_hold(self):
        for missing in ('paid_commission_usdt', 'realized_pnl_usdt', 'paid_funding_usdt', 'taker_fee',
                        'frozen_budget', 'campaign', 'ceiling'):
            with self.subTest(missing=missing):
                snapshot, protection, fill, instrument, costs = self.fixture('1')
                fee = '.0005'
                if missing in costs: costs[missing] = None
                elif missing == 'taker_fee': fee = None
                elif missing == 'frozen_budget': fill.pop('stop_budget')
                elif missing == 'campaign': protection['campaign'] += 1
                else: protection['loss_ceiling_usdt'] = 'NaN'
                with self.assertRaises((Blocked, Unknown)):
                    holding_risk(snapshot, protection, fill, instrument, fee, **costs)

    def test_no_legal_stop_remaining_requires_an_owned_exit(self):
        snapshot, protection, fill, instrument, costs = self.fixture()
        snapshot.update(wallet_usdt='904.6', equity_usdt='904.6')
        costs['paid_funding_usdt'] = '95'
        plan = holding_risk(snapshot, protection, fill, instrument, '.0005', **costs)
        self.assertEqual(plan['action'], 'hold')
        self.assertEqual(plan['stop'], '90')

    def test_short_recovery_rounds_its_risk_stop_down(self):
        snapshot, protection, fill, instrument, costs = self.fixture('-8')
        costs['loss_fraction'] = '.01'
        plan = holding_risk(snapshot, protection, fill, instrument, '.0005', **costs)
        self.assertEqual(plan['action'], 'hold')
        self.assertEqual(plan['stop'], '110')

    def test_guard_commission_read_reuses_the_existing_one_minute_cache(self):
        _, reader, _, values, _ = test_native_preview.NativePreviewTests().fixture()
        reader.monotonic.return_value = 0
        self.assertEqual(commission(reader), D('.0005'))
        values['/fapi/v1/commissionRate']['takerCommissionRate'] = '.0009'
        reader.monotonic.return_value = 59
        self.assertEqual(commission(reader), D('.0005'))
        reader.monotonic.return_value = 60
        self.assertEqual(commission(reader), D('.0009'))
        self.assertEqual(reader.get.call_count, 2)
        self.assertTrue(all(call.args[0] == '/fapi/v1/commissionRate' for call in reader.get.call_args_list))


class OwnedExitTests(TestCase):
    def campaign(self, expiry_bars=4):
        model = Campaign()
        model.last = model.model.last = ORIGIN + FOUR_HOURS
        model.model.close = D(110)
        model.model.active = Opportunity(model.last, 1, D(100), D(500), ORIGIN + expiry_bars * FOUR_HOURS,
                                         D(110), D(10), D(120), False)
        model.entry_fill = D(110)
        model.filled(model.last)
        protection = dict(campaign=model.last, stop='100', take='500', accepted_at_ms=model.last)
        return model, protection

    def test_owned_stop_rebound_keeps_expiry_and_checkpoint_recovery(self):
        model, protection = self.campaign()
        identity = model.position_campaign
        model.update(ORIGIN + 2 * FOUR_HOURS, D(111), D(99), D(101), effective_protection=protection)
        self.assertEqual(model.exit_cause, 'price')
        self.assertEqual(model.action(D(1)), 'exit')
        self.assertEqual(model.model.active.identity, identity)
        model = Campaign.restore(json.loads(json.dumps(model.checkpoint())))
        model.update(ORIGIN + 3 * FOUR_HOURS, D(111), D('100.5'), D(101), effective_protection=protection)
        self.assertIsNone(model.exit_cause)
        self.assertEqual(model.action(D(1)), 'hold')
        model.update(ORIGIN + 4 * FOUR_HOURS, D(111), D('100.5'), D(101), effective_protection=protection)
        self.assertEqual(model.exit_cause, 'time')
        self.assertEqual(model.action(D(1)), 'exit')

    def test_same_candle_stop_touch_cannot_cancel_unconditional_expiry(self):
        model, protection = self.campaign(expiry_bars=2)
        model.update(ORIGIN + 2 * FOUR_HOURS, D(111), D(99), D(101), effective_protection=protection)
        self.assertEqual(model.exit_cause, 'time')
        self.assertIsNone(model.exit_stop)
        self.assertIsNone(model.model.active)
        self.assertEqual(model.action(D(1)), 'exit')

    def test_old_price_exit_without_owned_geometry_is_not_silently_restored(self):
        model, protection = self.campaign()
        model.update(ORIGIN + 2 * FOUR_HOURS, D(111), D(99), D(101), effective_protection=protection)
        for missing in ('geometry', 'finite_stop'):
            saved = model.checkpoint()
            if missing == 'geometry':
                saved['body']['model']['active'] = None
            else:
                saved['body']['exit_stop'] = 'Infinity'
            saved['sha256'] = hashlib.sha256(json.dumps(saved['body'], sort_keys=True).encode()).hexdigest()
            with self.subTest(missing=missing), self.assertRaises(Blocked):
                Campaign.restore(saved)

    def test_take_hit_does_not_turn_into_a_stop_price_condition(self):
        model, protection = self.campaign()
        model.update(ORIGIN + 2 * FOUR_HOURS, D(501), D(110), D(490), effective_protection=protection)
        self.assertEqual(model.exit_cause, 'take')
        self.assertIsNone(model.exit_stop)
        self.assertEqual(Campaign.restore(json.loads(json.dumps(model.checkpoint()))).exit_cause, 'take')
        self.assertEqual(model.action(D(1)), 'exit')

    def test_unowned_signal_still_retires_on_the_completed_bar_stop(self):
        model, _ = self.campaign()
        model.position_campaign = model.consumed = model.primary_consumed = None
        self.assertIsNone(model.update(ORIGIN + 2 * FOUR_HOURS, D(111), D(99), D(101)))
        self.assertIsNone(model.exit_cause)

