import unittest
from decimal import Decimal as D

from coinquant.opportunities import Opportunities, FOUR_HOURS


class OpportunityTests(unittest.TestCase):
    def feed(self, model, rows):
        return [model.update((i + 1) * FOUR_HOURS, *map(D, row)) for i, row in enumerate(rows)]

    def test_impulse_uses_prior_volatility_and_midpoint_stop(self):
        rows = [(101, 99, 100)] * 20 + [(120, 99, 115)]
        out = self.feed(Opportunities(), rows)
        self.assertTrue(all(x is None for x in out[:-1]))
        a = out[-1]
        self.assertEqual((a.identity, a.direction, a.stop), (21 * FOUR_HOURS, 1, D('107.5')))
        self.assertEqual(a.take, D(115) * (D(115) / D('107.5')) ** 20)
        self.assertEqual(a.expires - a.identity, 42 * FOUR_HOURS)

    def test_downward_impulse_is_symmetric(self):
        a = self.feed(Opportunities(), [(101, 99, 100)] * 20 + [(101, 80, 85)])[-1]
        self.assertEqual((a.direction, a.stop), (-1, D('92.5')))

    def test_stop_and_expiry_retire_the_campaign(self):
        m = Opportunities()
        a = self.feed(m, [(101, 99, 100)] * 20 + [(120, 99, 115)])[-1]
        self.assertEqual(m.update(22 * FOUR_HOURS, D(116), D(108), D(115)), a)
        self.assertIsNone(m.update(23 * FOUR_HOURS, D(116), D(107), D(110)))
        m = Opportunities()
        a = self.feed(m, [(101, 99, 100)] * 20 + [(120, 99, 115)])[-1]
        for i in range(22, 21 + 42):
            self.assertEqual(m.update(i * FOUR_HOURS, D(116), D(114), D(115)), a)
        self.assertIsNone(m.update((21 + 42) * FOUR_HOURS, D(116), D(114), D(115)))

    def test_prefix_cannot_depend_on_future_or_rewrite_objects(self):
        rows = [(101, 99, 100)] * 20 + [(120, 99, 115)] + [(116, 114, 115)] * 10
        full = self.feed(Opportunities(), rows)
        prefix = self.feed(Opportunities(), rows[:23])
        changed = self.feed(Opportunities(), rows[:23] + [(1000, 1, 5)] * 8)
        self.assertEqual(full[:23], prefix)
        self.assertEqual(changed[:23], prefix)

    def test_a_long_up_six_risk_units_at_expiry_trails_instead_of_ending(self):
        m = Opportunities()
        signal = self.feed(m, [(101, 99, 100)] * 20 + [(120, 99, 115)])[-1]
        for i in range(22, 21 + 42):
            self.assertEqual(m.update(i * FOUR_HOURS, D(150), D(140), D(145)).identity, signal.identity)
        # No recorded fill: the seven-day life still ends the campaign.
        self.assertIsNone(m.update((21 + 42) * FOUR_HOURS, D(170), D(162), D(165)))
        m = Opportunities()
        signal = self.feed(m, [(101, 99, 100)] * 20 + [(120, 99, 115)])[-1]
        m.fill = D(110)
        for i in range(22, 21 + 42):
            self.assertEqual(m.update(i * FOUR_HOURS, D(150), D(140), D(145)).identity, signal.identity)
        held = m.update((21 + 42) * FOUR_HOURS, D(170), D(162), D(165))
        self.assertTrue(held.extended)
        self.assertIsNone(held.expires)
        self.assertGreaterEqual(held.stop, m.fill)
        self.assertEqual(held.take, D(170) * 5)
        self.assertIsNone(m.update((22 + 42) * FOUR_HOURS, D(170), m.fill - 1, D(160)))

    def test_missing_bar_fails_closed(self):
        m = Opportunities()
        m.update(FOUR_HOURS, D(101), D(99), D(100))
        with self.assertRaises(ValueError):
            m.update(3 * FOUR_HOURS, D(101), D(99), D(100))


if __name__ == '__main__':
    unittest.main()
