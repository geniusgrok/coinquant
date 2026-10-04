from collections import deque
from decimal import Decimal as D
import unittest

from coinquant.campaign import ORIGIN
from coinquant.opportunities import FOUR_HOURS, Opportunity
from coinquant.types import Blocked, Unknown
from research.complete_perp import checksum
from research.structure_perp import CashShort


class CashShortTests(unittest.TestCase):
    def bearish(self):
        value = CashShort()
        value.daily_closes = deque(map(D, range(165, 100, -1)), maxlen=65)
        value.returns.extend([D('.01')]*20)
        value.model.active = Opportunity(ORIGIN+FOUR_HOURS, -1, D(110), D(50), None)
        value.decision_mark = D(100)
        return value

    def test_macro_and_owned_long_keep_priority(self):
        value = self.bearish()
        macro = Opportunity(-ORIGIN, 1, D(90), D(200), None)
        value.macro_opportunity = macro
        self.assertIs(value.active, macro)
        value.position_campaign = -ORIGIN
        self.assertIs(value.active, macro)
        value.position_campaign = ORIGIN+2*FOUR_HOURS
        value.macro_opportunity = None
        self.assertIsNone(value.active)
        self.assertEqual(value.action(D('.1')), 'exit')

    def test_missing_macro_is_unknown_not_cash(self):
        value = self.bearish()
        self.assertTrue(value.macro_relevant())
        with self.assertRaises(Unknown):
            value.select_macro(None, D(100), value.last)

    def test_consumed_macro_does_not_block_a_fresh_cash_short(self):
        value = self.bearish()
        macro = Opportunity(-ORIGIN, 1, D(90), D(200), None)
        value.macro_opportunity = macro
        value.macro_consumed = macro.identity
        self.assertIs(value.active, value.model.active)
        self.assertEqual(value.action(D(0)), 'enter')
        value.position_campaign = macro.identity
        self.assertIs(value.active, macro)

    def test_consumed_short_cannot_reenter_and_owned_short_can_hold(self):
        value = self.bearish()
        identity = value.model.active.identity
        value.primary_consumed = identity
        self.assertIsNone(value.active)
        value.position_campaign = identity
        self.assertEqual(value.action(D('-.1')), 'hold')

    def test_short_funding_fee_gap_and_stop_share_one_percent_budget(self):
        value = self.bearish()
        fraction = value.entry_fraction('.0011')
        self.assertLessEqual(fraction, D('.5'))
        self.assertLessEqual(fraction*D('.2137'), D('.01'))
        value.decision_mark = D(111)
        self.assertEqual(value.entry_fraction('.0011'), 0)

    def test_checkpoint_preserves_binding_and_rejects_foreign_spec(self):
        value = CashShort()
        for i in range(1, 16):
            value.update(ORIGIN+i*FOUR_HOURS, D(101), D(99), D(100))
        value.decision_mark = D(100)
        saved = value.checkpoint()
        self.assertEqual(CashShort.restore(saved).checkpoint(), saved)
        saved['body']['structure']['spec_sha256'] = '0'*64
        saved['sha256'] = checksum(saved['body'])
        with self.assertRaises(Blocked):
            CashShort.restore(saved)
