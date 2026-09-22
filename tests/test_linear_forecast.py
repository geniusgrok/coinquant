import unittest

from research.linear_forecast import forecast


class CausalForecastTests(unittest.TestCase):
    def test_unmatured_label_cannot_change_coefficients(self):
        past = [(10, [1., .2, -.1, .3], .7)]
        expected = forecast(past, 10)
        self.assertEqual(expected, forecast(past + [(11, [float('nan')]*4, float('nan'))], 10))

    def test_label_enters_only_at_maturity(self):
        observations = [(10, [1., 0., 0., 0.], 11.)]
        self.assertEqual(forecast(observations, 9), ([0., 0., 0., 0.], 0))
        self.assertEqual(forecast(observations, 10), ([1., 0., 0., 0.], 1))
