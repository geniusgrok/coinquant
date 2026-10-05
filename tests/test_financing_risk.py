from copy import deepcopy
from decimal import Decimal
import unittest

from research.financing_risk import EIGHT_HOURS, evaluate


def packet(quantity='1'):
    now = 10*EIGHT_HOURS+1000
    def receipt(origin):
        return dict(origin=origin, symbol='BTCUSDT', observed_ms=now,
                    available_ms=now, source_sha256=['a'*64])
    account = receipt('native-account-observation')
    account.update(account_uid='9', owned_campaign='campaign-1', owned=True,
        one_way=True, isolated=True, auto_add_margin_off=True, exchange_leverage=20,
        pending=False, quantity_btc=quantity, owned_quantity_btc=quantity,
        protected=True, stop_before_liquidation=True, confirmed_reducible_btc='1',
        entry_price='100', unrealized_usdt='0', isolated_wallet_usdt='10',
        native_liquidation_price='91', stop_price='95')
    mark = receipt('native-mark-observation');mark['mark_price'] = '100'
    brackets = receipt('native-dated-maintenance-brackets')
    brackets.update(effective_from_ms=now-1000, effective_until_ms=now+1000,
                    tiers=[dict(notionalFloor='0', notionalCap='1000000', maintMarginRatio='.005', cum='0')])
    commission = receipt('native-account-commission');commission['taker_fee'] = '.001'
    funding = receipt('native-settled-funding')
    funding['settlements'] = [dict(time_ms=t*EIGHT_HOURS, rate='.001') for t in (8,9,10)]
    return dict(decision_ms=now, expected_account_uid='9', target_btc='1',
                account=account, mark=mark, brackets=brackets, commission=commission, funding=funding)


class FinancingRisk(unittest.TestCase):
    def test_missing_native_margin_data_blocks_without_invented_wallet(self):
        p = packet();p['brackets']['origin'] = 'historical-synthetic-brackets'
        r = evaluate(p)
        self.assertEqual(r['status'], 'BLOCK_FINANCING_INPUT')
        self.assertTrue(r['new_risk_blocked'])
        self.assertIsNone(r['next_state'])
        self.assertEqual((r['orders'], r['account_entrants']), (0,0))

    def test_actual_buffer_breach_caps_but_half_needs_supported_margin(self):
        p = packet();r = evaluate(p)
        # 10 collateral -10 shock PnL -.45 maintenance -.3 funding -.09 exit.
        self.assertEqual(Decimal(r['diagnostics']['stress_surplus_usdt']), Decimal('-0.840'))
        self.assertEqual(r['status'], 'WAIT_REDUCTION_PREVIEW')
        self.assertEqual(r['new_exposure_cap_btc'], '0.5')
        preview = deepcopy(p['mark'])
        preview.update(origin='verified-native-margin-release-bound', account_uid='9',
                       campaign='campaign-1', remaining_btc='.5', remaining_isolated_wallet_lower_usdt='5')
        p['reduction_preview'] = preview
        r = evaluate(p)
        self.assertEqual(r['status'], 'NO_SUPPORTED_MARGIN_BUFFER_IMPROVEMENT')
        self.assertEqual(r['proposed_reduction_btc'], '0')
        preview['remaining_isolated_wallet_lower_usdt'] = '6'
        r = evaluate(p)
        self.assertEqual(r['status'], 'RESEARCH_OWNED_REDUCTION')
        self.assertEqual(r['proposed_reduction_btc'], '0.5')
        self.assertFalse(r['tail_safety_proven'])
        self.assertEqual(r['orders'], 0)

    def test_cap_survives_recovery_missing_query_and_only_owned_flat_clears(self):
        p = packet();state = evaluate(p)['next_state']
        p['account']['isolated_wallet_usdt'] = '20'
        p['decision_ms'] += 100
        p['account']['observed_ms'] = p['account']['available_ms'] = p['decision_ms']
        r = evaluate(p, state)
        self.assertEqual(r['new_exposure_cap_btc'], '0.5')
        state = r['next_state']
        missing = deepcopy(p);del missing['account']
        self.assertEqual(evaluate(missing,state)['next_state'], state)
        p['account'].update(quantity_btc='0', owned_quantity_btc='0', confirmed_reducible_btc='0')
        self.assertEqual(evaluate(p,state)['status'], 'BLOCK_FINANCING_INPUT')
        p['account']['flat_confirmed_ms'] = state['last_observed_ms']-1
        self.assertEqual(evaluate(p,state)['status'], 'BLOCK_FINANCING_INPUT')
        p['account']['flat_confirmed_ms'] = p['decision_ms']
        self.assertIsNone(evaluate(p,state)['next_state'])
        p['account']['owned_campaign'] = 'different'
        self.assertEqual(evaluate(p,state)['next_state'], state)

    def test_future_funding_and_inconsistent_pnl_block(self):
        p = packet();p['funding']['settlements'][-1]['time_ms'] += EIGHT_HOURS
        self.assertEqual(evaluate(p)['status'], 'BLOCK_FINANCING_INPUT')
        p = packet();p['account']['unrealized_usdt'] = '1'
        self.assertEqual(evaluate(p)['status'], 'BLOCK_FINANCING_INPUT')

    def test_flat_expression_is_owned_reduce_only_not_an_order(self):
        p = packet();r = evaluate(p, expression='flat')
        self.assertEqual(r['status'], 'RESEARCH_OWNED_REDUCTION')
        self.assertEqual(r['new_exposure_cap_btc'], '0')
        self.assertEqual(r['proposed_reduction_btc'], '1')
        self.assertTrue(r['reduce_only'])
        p['account']['confirmed_reducible_btc'] = '.4'
        self.assertEqual(evaluate(p, expression='flat')['status'], 'BLOCK_REDUCTION_CAPACITY')

    def test_short_direction_pays_negative_funding_and_uses_actual_tiers(self):
        p = packet('-1')
        p['account'].update(native_liquidation_price='109', stop_price='105')
        for row in p['funding']['settlements']:row['rate'] = '-.001'
        p['brackets']['tiers'] = [
            dict(notionalFloor='0', notionalCap='100', maintMarginRatio='.005', cum='0'),
            dict(notionalFloor='100', notionalCap='1000', maintMarginRatio='.01', cum='.5')]
        r = evaluate(p, expression='flat')
        self.assertEqual(r['status'], 'RESEARCH_OWNED_REDUCTION')
        self.assertEqual(r['side'], 'BUY')
        self.assertEqual(r['diagnostics']['funding_stress_reserve_usdt'], '0.300')
        self.assertEqual(r['diagnostics']['stressed_maintenance_usdt'], '0.6000')
        p['brackets']['tiers'][1]['cum'] = '.6'
        self.assertEqual(evaluate(p, expression='flat')['status'], 'BLOCK_FINANCING_INPUT')
