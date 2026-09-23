import unittest
from decimal import Decimal as D

from coinquant.capital import (CapitalBudget, GAP, FUNDING_FLOOR, capital_surplus,
                               gap_margin)
from coinquant.linear_account import Account, FEE, LOT
from coinquant.renewal_risk import (confirmed_entry_child_ids,
                                    plan_renewal_reduction)


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

    def test_plan_selects_largest_safe_quantity_on_exhaustive_small_grid(self):
        from dataclasses import replace

        a=account();a.q=D('.02');a.margin=D('.1')
        b=budget();fraction=D('.0001');reference=mark=D('105');anchor=D('100')
        plan=plan_renewal_reduction(
            a,b,reference,mark,anchor,None,lambda amount: D('104.9'),
            lambda remaining: D('89.9'),risk_fraction=fraction,
        )
        safe=[]
        steps=int(a.q/LOT)
        for index in range(steps+1):
            remaining=a.q-LOT*index
            trial=replace(a)
            amount=a.q-remaining
            if amount:
                trial.close(amount,D('104.9'))
            if remaining:
                required,_=gap_margin(trial,anchor)
                trial.margin=max(trial.margin,required)
                surplus=capital_surplus(trial,b,reference,mark,anchor)
                funding=b.reserve_components(remaining,trial.entry,reference,mark)['funding']
                future_loss=max(D(0),remaining*(mark-D('89.9'))
                    +remaining*D('89.9')*FEE+funding)
            else:
                surplus=trial.wallet-b.pending_reserve
                future_loss=D(0)
            if surplus>=D('-1e-18') and future_loss<=fraction*trial.equity(mark):
                safe.append(remaining)
        self.assertTrue(safe)
        self.assertEqual(plan['remaining'],max(safe))
        next_larger=plan['remaining']+LOT
        self.assertLessEqual(next_larger,a.q)
        self.assertNotIn(next_larger,safe)
        trial=replace(a);trial.close(a.q-next_larger,D('104.9'))
        required,_=gap_margin(trial,anchor);trial.margin=max(trial.margin,required)
        funding=b.reserve_components(next_larger,trial.entry,reference,mark)['funding']
        future_loss=next_larger*(mark-D('89.9'))+next_larger*D('89.9')*FEE+funding
        self.assertGreater(future_loss,fraction*trial.equity(mark))

    def test_confirmed_child_ledger_fails_closed_on_missing_or_mismatched_entry(self):
        children=[
            dict(parent_id='parent-a',child_id='child-1',accepted='0.4'),
            dict(parent_id='parent-a',child_id='child-2',accepted='0.6'),
        ]
        self.assertEqual(confirmed_entry_child_ids('parent-a',D('1'),False,children),
                         ['child-1','child-2'])
        self.assertIsNone(confirmed_entry_child_ids('parent-a',D('1'),True,children))
        self.assertIsNone(confirmed_entry_child_ids('parent-a',D('1'),False,[]))
        self.assertIsNone(confirmed_entry_child_ids('parent-a',D('1'),False,children[:1]))
        self.assertIsNone(confirmed_entry_child_ids('parent-a',D('1'),False,
            [dict(children[0],parent_id='parent-b'),children[1]]))
        self.assertIsNone(confirmed_entry_child_ids('parent-a',D('1'),False,
            [children[0],dict(children[1],child_id='child-1')]))

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
