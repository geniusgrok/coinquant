"""New-risk defaults and explicit management-only configuration."""
from decimal import Decimal as D
from unittest import TestCase

from coinquant.config import Config
from coinquant.types import Blocked


class StopBudgetConfigTests(TestCase):
    def test_default_and_explicit_budget_are_decimal_fractions(self):
        config=Config('123','/tmp/coinquant-config-test')
        self.assertEqual(config.loss_fraction,D('.10'))
        self.assertEqual(config.slip_fraction,D('.01'))
        smaller=Config('123','/tmp/coinquant-config-test',max_stop_loss_fraction='.02',stop_slippage_fraction='.005')
        self.assertEqual(smaller.loss_fraction,D('.02'))
        self.assertEqual(smaller.slip_fraction,D('.005'))

    def test_mismatched_budget_is_invalid(self):
        with self.assertRaises(Blocked):
            Config('123','/tmp/coinquant-config-test',max_stop_loss_fraction=None)

    def test_invalid_budget_is_never_accepted(self):
        for value in ('0','1','NaN','.Infinity',.49):
            with self.subTest(value=value),self.assertRaises(Blocked):
                Config('123','/tmp/coinquant-config-test',max_stop_loss_fraction=value)
