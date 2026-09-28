from decimal import Decimal as D
from unittest import TestCase

from coinquant.campaign import ORIGIN, Campaign
from coinquant.opportunities import FOUR_HOURS, Opportunities


class AverageHoldTests(TestCase):
    def test_default_campaign_stays_the_one_bar_jump(self):
        self.assertEqual(Campaign().model.mechanism, 'impulse_hold')

    def test_a_small_step_above_the_average_opens_one_long(self):
        average = Opportunities('average_hold')
        impulse = Opportunities('impulse_hold')
        end = ORIGIN + FOUR_HOURS
        price = D(100)
        for _ in range(20):
            average.update(end, price + 1, price - 1, price)
            impulse.update(end, price + 1, price - 1, price)
            end += FOUR_HOURS
        self.assertIsNone(average.active)
        close = price + 3
        average.update(end, close + 1, close - 1, close)
        impulse.update(end, close + 1, close - 1, close)
        self.assertEqual(average.active.direction, 1)
        self.assertEqual(average.active.stop, close - D(2))
        self.assertGreater(average.active.take, close)
        self.assertIsNone(impulse.active)
        opened = average.active.identity
        end += FOUR_HOURS
        average.update(end, close + 4, close + 2, close + 3)
        self.assertEqual(average.active.identity, opened)

    def test_a_small_step_below_the_average_opens_one_short(self):
        model = Opportunities('average_hold')
        end = ORIGIN + FOUR_HOURS
        price = D(100)
        for _ in range(20):
            model.update(end, price + 1, price - 1, price)
            end += FOUR_HOURS
        close = price - 3
        model.update(end, close + 1, close - 1, close)
        self.assertEqual(model.active.direction, -1)
        self.assertEqual(model.active.stop, close + D(2))
