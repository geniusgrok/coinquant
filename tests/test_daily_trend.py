from decimal import Decimal as D
import unittest

from coinquant.campaign import Campaign, ORIGIN, DAY


class DailyTrendTests(unittest.TestCase):
    def test_completed_prior_days_define_one_campaign(self):
        model = Campaign('daily_trend', DAY)
        end = ORIGIN
        for _ in range(20):
            end += DAY
            self.assertIsNone(model.update(end, D(101), D(99), D(100)))
        end += DAY
        opportunity = model.update(end, D(103), D(100), D(102))
        self.assertEqual((opportunity.identity, opportunity.stop, opportunity.direction),
                         (end, D(99), 1))
        restored = Campaign.restore(model.checkpoint())
        end += DAY
        self.assertEqual(restored.update(end, D(104), D(100), D(103)).identity,
                         opportunity.identity)
        end += DAY
        self.assertIsNone(restored.update(end, D(103), D(98), D(100)))


if __name__ == '__main__':
    unittest.main()
