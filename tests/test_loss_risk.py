"""Financial-loss regressions with pure inputs and in-memory lifecycle doubles."""
from decimal import Decimal as D
from datetime import datetime, timezone
import json
from unittest import TestCase
from unittest.mock import Mock, patch

from coinquant.campaign import Campaign
from coinquant.lifecycle import Lifecycle
from coinquant.native_preview import limit_matches
from coinquant.state import client_id
from coinquant.types import Blocked


class EntryRecoveryMarginTests(TestCase):
    def fixture(self, mark):
        rules = dict(symbol='BTCUSDT', marginAsset='USDT', quotePrecision=8, filters=[
            dict(filterType='PRICE_FILTER', tickSize='.1', minPrice='.1', maxPrice='1000000'),
            dict(filterType='LOT_SIZE', stepSize='.001', minQty='.001', maxQty='1000'),
            dict(filterType='MIN_NOTIONAL', notional='100')])
        # A durable entry plan made before stop-scenario collateral headroom
        # was required. Recovery must still reject its now-excessive target.
        original_margin = D('249.701775')
        # The opening commission is already paid; only 20x initial margin moved
        # before the process stopped. A 0.2% price move remains above liquidation.
        wallet = D('999.25')
        snapshot = dict(account_uid='offline', quantity_btc='.015', entry='100000',
                        wallet_usdt=str(wallet), equity_usdt=str(wallet + D('.015') * (D(mark) - 100000)),
                        mark_price=str(mark), isolated_wallet_usdt='75', available_usdt='924.25',
                        native_liquidation_price='95381.52610442', possible_entry_remainders=0,
                        last_fill_id=10)
        state = Mock()
        state.identity = 'offline'
        state.get.return_value = None
        state.pending.return_value = []
        reader = Mock()
        reader.clock.return_value = 1700000000
        reader.capital_limit = None
        reader.snapshot.return_value = snapshot
        engine = Lifecycle(reader, state, 'offline', authorized=True)
        engine.entry_fill_proven = Mock(return_value=True)
        engine.close = Mock(return_value={**snapshot, 'quantity_btc': '0'})
        engine._save_protection = Mock()
        plan = dict(id='entry', epoch=1, campaign=14400000, quantity_btc='.015',
                    stop='93730', take='200000', allocated_margin_usdt=str(original_margin),
                    observed_at=1700000000000, instrument=rules)
        return engine, snapshot, plan, rules

    def test_recovery_cannot_transfer_old_target_above_current_equity_cap(self):
        engine, snapshot, plan, rules = self.fixture('99800')
        self.assertEqual(D(snapshot['equity_usdt']) * D('.25'), D('249.0625'))
        with patch('coinquant.lifecycle.safety.protect_existing', return_value=snapshot), \
             patch('coinquant.lifecycle.safety.replace_protection', return_value=snapshot), \
             patch('coinquant.lifecycle.safety.add_margin', return_value=snapshot) as transfer:
            with self.assertRaises(Blocked):
                engine.protect_entry(snapshot, plan, proven_order={'executedQty': '.015'})
        transfer.assert_not_called()
        engine.entry_fill_proven.assert_called_once_with(plan, snapshot)
        engine.close.assert_called_once_with(snapshot, rules)
        engine._save_protection.assert_not_called()

    def test_currently_funded_recovery_keeps_the_owned_entry(self):
        engine, snapshot, plan, _ = self.fixture('100000')
        self.assertLess(D(plan['allocated_margin_usdt']), D(snapshot['equity_usdt']) * D('.25'))
        funded = {**snapshot, 'isolated_wallet_usdt': plan['allocated_margin_usdt']}
        with patch('coinquant.lifecycle.safety.protect_existing', return_value=snapshot), \
             patch('coinquant.lifecycle.safety.replace_protection', return_value=funded), \
             patch('coinquant.lifecycle.safety.add_margin', return_value=funded) as transfer:
            result = engine.protect_entry(snapshot, plan, proven_order={'executedQty': '.015'})
        self.assertIs(result, funded)
        transfer.assert_called_once()
        self.assertEqual(transfer.call_args.args[5], D(plan['allocated_margin_usdt']))
        engine.close.assert_not_called()
        engine._save_protection.assert_called_once()

    def resumed_fixture(self, mark, *, withdrawn=D(0)):
        engine, snapshot, plan, rules = self.fixture(mark)
        target = D(plan['allocated_margin_usdt'])
        margin = target - withdrawn
        snapshot.update(isolated_wallet_usdt=str(margin),
                        available_usdt=str(D(snapshot['wallet_usdt']) - margin),
                        native_liquidation_price=str(((D('.015') * 100000 - margin)
                            / (D('.015') * (1 - D('.004')))).quantize(D('.00000001'))))
        plan.update(guard_epoch=2, guard_stop='95381.6', guard_take=plan['take'])
        journal = dict(done=True, epoch=plan['epoch'], request=dict(
            old_ids=[client_id(engine.state.identity, 2, kind)
                     for kind in ('STOP_MARKET', 'TAKE_PROFIT_MARKET')],
            new_ids=[client_id(engine.state.identity, plan['epoch'], kind)
                     for kind in ('STOP_MARKET', 'TAKE_PROFIT_MARKET')],
            stop=plan['stop'], take=plan['take']))
        engine.state.get.side_effect = {'binance_protection_replacement': journal}.get
        return engine, snapshot, plan, rules

    def assert_resumed_owned_exit(self, engine, snapshot, plan, rules, reason):
        with patch('coinquant.lifecycle.safety.protect_existing', return_value=snapshot) as protect, \
             patch('coinquant.lifecycle.safety.replace_protection', return_value=snapshot) as replace, \
             patch('coinquant.lifecycle.safety.add_margin') as transfer:
            with self.assertRaisesRegex(Blocked, reason):
                engine.protect_entry(snapshot, plan, proven_order={'executedQty': '.015'})
        # The existing replacement is resumed and its successor confirmed; no
        # old margin operation is replayed and no smaller baseline is saved.
        replace.assert_called_once()
        protect.assert_called_once()
        self.assertEqual(protect.call_args.args[4], plan['epoch'])
        transfer.assert_not_called()
        engine.entry_fill_proven.assert_called_once_with(plan, snapshot)
        engine.close.assert_called_once_with(snapshot, rules)
        engine._save_protection.assert_not_called()

    def test_resumed_guard_cannot_freeze_margin_removed_during_the_interruption(self):
        engine, snapshot, plan, rules = self.resumed_fixture('100000', withdrawn=D(1))
        # A native isolated-margin withdrawal changes available funds, not the
        # total wallet. This is not a funding-fee debit from available balance.
        self.assertEqual(snapshot['wallet_usdt'], '999.25')
        self.assertEqual(D(snapshot['isolated_wallet_usdt']), D('248.701775'))
        self.assertLess(D(plan['allocated_margin_usdt']), D(snapshot['equity_usdt']) * D('.25'))
        self.assertLess(D(plan['stop']) - D(snapshot['native_liquidation_price']), D(10000))
        self.assert_resumed_owned_exit(engine, snapshot, plan, rules, 'original protection buffer')

    def test_resumed_guard_rechecks_current_cap_even_when_original_margin_is_present(self):
        engine, snapshot, plan, rules = self.resumed_fixture('99800')
        self.assertEqual(D(snapshot['isolated_wallet_usdt']), D(plan['allocated_margin_usdt']))
        self.assertEqual(D(snapshot['equity_usdt']) * D('.25'), D('249.0625'))
        self.assertGreater(D(plan['allocated_margin_usdt']), D(snapshot['equity_usdt']) * D('.25'))
        self.assert_resumed_owned_exit(engine, snapshot, plan, rules, 'current collateral limit')


class OwnedMacroRecoveryTests(TestCase):
    def fixture(self):
        model = Campaign()
        for _ in range(60):
            model.update(model.last + model.model.interval, '100010', '90000', '100000')
        call = model.last + 1000
        row = dict(missing_reason=None, latest_value='1', prior20_value='1.3',
                   latest_observation_date=datetime.fromtimestamp(call / 1000, timezone.utc).date().isoformat(),
                   latest_value_available_ms=call - 1, prior20_value_available_ms=call - 1)
        model.select_macro(row, '100000', call)
        model.filled(model.active.identity)
        return model, row, call

    def test_readonly_macro_exit_retains_geometry_for_a_later_valid_observation(self):
        model, row, call = self.fixture()
        owned = model.macro_opportunity
        model.select_macro({**row, 'missing_reason': 'stale_observation_over_7_calendar_days'}, '100000', call + 1)
        self.assertEqual(model.action(D('.003')), 'exit')
        self.assertEqual(model.exit_cause, 'macro')
        self.assertEqual(model.exit_campaign, owned.identity)
        self.assertEqual(model.macro_opportunity, owned)
        self.assertEqual(model.macro_epoch, owned.identity)
        model = Campaign.restore(json.loads(json.dumps(model.checkpoint())))
        self.assertEqual(model.action(D('.003')), 'exit')
        model.select_macro(row, '100000', call + 2)
        self.assertEqual(model.macro_opportunity, owned)
        self.assertEqual(model.action(D('.003')), 'hold')
        self.assertIsNone(model.exit_cause)

    def test_macro_recovery_does_not_cancel_a_different_owned_exit(self):
        for cause in ('price', 'time', 'take'):
            with self.subTest(cause=cause):
                model, row, call = self.fixture()
                model.exit_cause = cause
                model.exit_campaign = model.position_campaign
                model.exit_stop = '95000' if cause == 'price' else None
                model.select_macro({**row, 'missing_reason': 'stale'}, '100000', call + 1)
                model.select_macro(row, '100000', call + 2)
                self.assertEqual(model.exit_cause, cause)
                self.assertEqual(model.action(D('.003')), 'exit')

    def test_flat_macro_ineligibility_still_retires_the_old_signal(self):
        model, row, call = self.fixture()
        previous = model.position_campaign
        model.position_campaign = None
        model.select_macro({**row, 'missing_reason': 'stale'}, '100000', call + 1)
        self.assertIsNone(model.macro_opportunity)
        self.assertIsNone(model.macro_epoch)
        model.select_macro(row, '100000', call + 2)
        self.assertNotEqual(model.active.identity, previous)
        self.assertEqual(model.action(D(0)), 'enter')


class FinalQuoteClockTests(TestCase):
    def test_unchanged_recent_book_after_next_close_cannot_authorize_old_model(self):
        completed = 1575158400000
        reader = Mock()
        # A venue clock two seconds ahead is permitted by quote freshness. Its
        # final book nonetheless proves the next four-hour candle has closed.
        reader.clock.return_value = (completed + 14400000 - 1000) / 1000
        reader.get.return_value = dict(E=completed + 14400000 + 1000,
                                       bids=[['100000', '1']], asks=[['100001', '1']])
        self.assertTrue(limit_matches(reader, 1, '100101.0', '.1',
                                      quantity='.01'))
        self.assertFalse(limit_matches(reader, 1, '100101.0', '.1',
                                       quantity='.01',
                                       completed_through=completed))

    def test_current_bar_final_book_keeps_the_existing_entry_gate(self):
        completed = 1575158400000
        reader = Mock()
        reader.clock.return_value = (completed + 14400000 - 1000) / 1000
        reader.get.return_value = dict(E=completed + 14400000 - 1000,
                                       bids=[['100000', '1']], asks=[['100001', '1']])
        self.assertTrue(limit_matches(reader, 1, '100101.0', '.1', quantity='.01',
                                      completed_through=completed))
