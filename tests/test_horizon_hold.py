from decimal import Decimal as D
from unittest import TestCase

from coinquant.campaign import ORIGIN, Campaign
from coinquant.opportunities import FOUR_HOURS, Opportunities


class HorizonHoldTests(TestCase):
    def test_default_campaign_stays_impulse_hold(self):
        self.assertEqual(Campaign().model.mechanism, 'impulse_hold')
        self.assertFalse(hasattr(Campaign().model, 'horizon'))

    def test_forty_two_bar_move_opens_one_long(self):
        model = Opportunities('horizon_hold')
        price = D(100)
        end = ORIGIN + FOUR_HOURS
        for _ in range(42):
            model.update(end, price + 1, price - 1, price)
            end += FOUR_HOURS
        self.assertIsNone(model.active)
        jumped = price + 50
        model.update(end, jumped + 1, price - 1, jumped)
        self.assertEqual(model.active.direction, 1)
        self.assertEqual(model.active.identity, end)
        self.assertLess(model.active.stop, jumped)
        self.assertGreater(model.active.take, jumped)
