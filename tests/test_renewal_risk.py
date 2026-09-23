import unittest
from decimal import Decimal as D

from coinquant.capital import CapitalBudget, GAP, FUNDING_FLOOR
from coinquant.linear_account import Account
from coinquant.renewal_risk import plan_renewal_reduction


def budget(*, valid=True):
    return CapitalBudget(
        as_of=1000, latest_settlement=1000, adverse_rate=D('.0001'),
        history_sha256='0'*64, previous_hour_quote=D('10000000'),
        slippage=D('.001'), spread=D('.0005'), pending_reserve=D('2'),
        valid=valid, horizon_days=7,
    )


def account():
    return Account(wallet=D('1000'), q=D('1'), entry=D('100'),
                   margin=D('5'), sl=D('90'), tp=D('120'))


class RenewalRiskTests(unittest.TestCase):
    def test_funding_reserve_is_separate_and_reconstructs_old_reserve(self):
        b = budget()
        parts = b.reserve_components(D('1'), D('100'), D('105'), D('105'))
        self.assertEqual(parts['funding'], D('105')*(1+GAP)*max(FUNDING_FLOOR, D('.0001')*21))
        self.assertEqual(sum(parts.values()), b.reserve(D('1'), D('100'), D('105'), D('105')))

    def test_plan_reduces_to_largest_quantity_within_entry_risk_fraction(self):
        a = account()
        original_stop = a.sl
        plan = plan_renewal_reduction(
            a, budget(), D('105'), D('105'), D('100'), None,
            lambda amount: D('105'), lambda remaining: D('90'),
            risk_fraction=D('.005'),
        )
        self.assertGreater(plan['amount'], 0)
        self.assertLess(plan['remaining'], D('1'))
        self.assertLessEqual(plan['future_loss'], plan['risk_limit'])
        self.assertEqual(a.q, D('1'))  # planning does not mutate the shared ledger
        self.assertEqual(a.sl, original_stop)

    def test_missing_entry_risk_basis_fails_closed(self):
        with self.assertRaises(ValueError):
            plan_renewal_reduction(
                account(), budget(), D('105'), D('105'), D('100'), None,
                lambda amount: D('105'), lambda remaining: D('90'),
                risk_fraction=None,
            )

    def test_invalid_funding_budget_cannot_leave_a_position_open(self):
        plan = plan_renewal_reduction(
            account(), budget(valid=False), D('105'), D('105'), D('100'), None,
            lambda amount: D('105'), lambda remaining: D('90'),
            risk_fraction=D('1'),
        )
        self.assertEqual(plan['remaining'], D('0'))
        self.assertEqual(plan['amount'], D('1'))


if __name__ == '__main__':
    unittest.main()
