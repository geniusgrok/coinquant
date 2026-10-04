import unittest

from research.replacement_routes import absorption, economic_gate, evaluate, expiry_basis, option_risk


class ReplacementTests(unittest.TestCase):
    def base(self):
        return dict(end_ms=1000000000,available_ms=1000000000,
                    base='BTC',quote='USDT',source_sha256=['a'*64])

    def test_future_information_cannot_admit_event(self):
        row=dict(self.base(),available_ms=1000000001)
        result=evaluate(dict(decision_ms=1000000000,absorption=row))
        self.assertEqual(result['routes']['absorption']['status'],'BLOCK_INFORMATION')
        self.assertEqual(result['account_entrants'],0)

    def test_alpha_requires_forced_flow_and_independent_spot_absorption(self):
        row=dict(self.base(),start_ms=1000000000-14400000,oi_unit='BTC',
                 oi_start_btc='100',oi_end_btc='90',spot_buy_btc='60',spot_sell_btc='40',
                 sell_liquidation_usdt='100',perp_turnover_usdt='1000')
        self.assertEqual(absorption(row,1000000000)['status'],'EVENT_CANDIDATE')
        row['spot_buy_btc']='30'
        self.assertEqual(absorption(row,1000000000)['status'],'NO_EVENT')

    def test_beta_does_not_trim_existing_positions_or_use_future_volatility(self):
        row=dict(self.base(),tenor_days='30',call_delta='.25',put_delta='-.25',
                 call_iv='.7',put_iv='.9',realized_rms20_annual='.5',
                 rv_completed_ms=1000000000,rv_available_ms=1000000000)
        result=option_risk(row,1000000000)
        self.assertEqual(result['proposed_new_risk_factor'],'.5')
        self.assertEqual(result['held_position_action'],'none')
        with self.assertRaises(ValueError):option_risk(dict(row,rv_available_ms=1000000001),1000000000)

    def test_basis_costs_depth_clocks_and_separate_margin(self):
        row=dict(self.base(),contract_type='linear-dated',settlement_currency='USDT',
                 expiry_ms=1000000000+30*86400000,spot_venue='spot',futures_venue='dated',
                 spot_book_ms=1000000000,futures_book_ms=1000000000,
                 quantity_btc='1',spot_ask='100',futures_bid='102',spot_ask_size_btc='1',futures_bid_size_btc='1',
                 spot_roundtrip_fee='.002',futures_roundtrip_fee='.0015',financing_annual='0',
                 slippage_reserve_usdt='.1',settlement_basis_reserve_usdt='.1',
                 futures_collateral_usdt='50',spot_cash_usdt='101',stress_up_fraction='.30',maintenance_margin_fraction='.01')
        self.assertEqual(expiry_basis(row,1000000000)['status'],'COST_SCREEN_POSITIVE')
        self.assertEqual(expiry_basis(dict(row,futures_bid='100.1'),1000000000)['status'],'REJECT_COST')
        for field,value in [('futures_book_ms',999999000),('futures_collateral_usdt','1'),('spot_ask_size_btc','.5'),('quote','USDC')]:
            with self.subTest(field=field),self.assertRaises(ValueError):expiry_basis(dict(row,**{field:value}),1000000000)

    def test_small_return_gain_and_return_collapse_cannot_pass_magnitude_gate(self):
        base=dict(cagr='1',mdd='.4')
        self.assertFalse(economic_gate(base,dict(cagr='1.01',mdd='.4'))['magnitude_pass'])
        self.assertFalse(economic_gate(base,dict(cagr='.5',mdd='.2'))['magnitude_pass'])
        self.assertTrue(economic_gate(base,dict(cagr='1.1',mdd='.4'))['magnitude_pass'])
        self.assertTrue(economic_gate(base,dict(cagr='.95',mdd='.32'))['magnitude_pass'])
        self.assertFalse(economic_gate(base,dict(cagr='2',mdd='.8'))['adopted'])


if __name__=='__main__':unittest.main()
