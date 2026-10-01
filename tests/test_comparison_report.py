from copy import deepcopy
from decimal import Decimal as D
from unittest import TestCase

from research.comparison_report import audit


class AccountAuditTests(TestCase):
    def fixture(self):
        return {'trades': [{'side': 'BUY', 'qty': '1', 'price': '100'},
                           {'side': 'SELL', 'qty': '1', 'price': '110'}],
                'funding_ledger': [{'incomeType': 'COMMISSION', 'income': '-.1575'},
                                   {'incomeType': 'REALIZED_PNL', 'income': '10'},
                                   {'incomeType': 'FUNDING_FEE', 'income': '-2'}],
                'position': '0', 'final_usdt': '1007.8425', 'fees': '.1575', 'funding': '2'}

    def test_closed_account_matches_fills_costs_and_full_cash_ledger(self):
        row = audit(self.fixture(), D(1000))
        self.assertTrue(row['passed'])
        self.assertEqual(row['wallet_from_ledger_usdt'], '1007.8425')

    def test_missing_fill_wrong_wallet_and_external_flow_invalidate_account(self):
        for change in ('fill', 'wallet', 'flow'):
            row = deepcopy(self.fixture())
            if change == 'fill':
                row['trades'].pop()
            elif change == 'wallet':
                row['final_usdt'] = '1010'
            else:
                row['funding_ledger'].append({'incomeType': 'TRANSFER', 'income': '50'})
            with self.subTest(change=change):
                self.assertFalse(audit(row, D(1000))['passed'])
