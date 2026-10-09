import unittest
from decimal import Decimal as D

from coinquant.opportunities import Opportunities, Opportunity, FOUR_HOURS


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

    def winner(self, *, extended=False, lows=None):
        m = Opportunities()
        m.last = FOUR_HOURS
        m.close = D(180)
        m.active = Opportunity(FOUR_HOURS, 1, D(110 if extended else 100), D(500),
                               None if extended else 2 * FOUR_HOURS,
                               D(115), D(15), D(190), extended)
        m.fill = D(110)
        m.lows.extend([D(130)] * 84 if lows is None else map(D, lows))
        return m

    def test_expiry_trail_only_applies_after_the_completed_candle(self):
        m = self.winner()
        held = m.update(2 * FOUR_HOURS, D(190), D(105), D(180))
        self.assertTrue(held.extended)
        self.assertEqual(held.stop, D(130))
        self.assertIsNone(m.update(3 * FOUR_HOURS, D(190), D(129), D(180)))

    def test_expiry_cannot_replace_a_stop_or_target_already_hit(self):
        for high, low in ((190, 100), (500, 150), (500, 100)):
            with self.subTest(high=high, low=low):
                m = self.winner()
                self.assertIsNone(m.update(2 * FOUR_HOURS, D(high), D(low), D(180)))

    def test_extension_uses_recorded_fill_risk_at_the_exact_expiry(self):
        for fill, close, extended in ((110, 170, True), (110, 169, False),
                                      (115, 170, False), (100, 180, False)):
            with self.subTest(fill=fill, close=close):
                m = self.winner()
                m.fill = D(fill)
                held = m.update(2 * FOUR_HOURS, D(190), D(150), D(close))
                if extended:
                    self.assertTrue(held.extended)
                else:
                    self.assertIsNone(held)

    def test_existing_trail_and_target_are_settled_before_a_new_trail(self):
        m = self.winner(extended=True)
        held = m.update(2 * FOUR_HOURS, D(190), D(120), D(180))
        self.assertEqual(held.stop, D(130))
        self.assertIsNone(m.update(3 * FOUR_HOURS, D(190), D(129), D(180)))
        m = self.winner(extended=True)
        self.assertIsNone(m.update(2 * FOUR_HOURS, D(500), D(150), D(180)))

    def test_trail_requires_84_preceding_lows_and_excludes_current_low(self):
        m = self.winner(lows=[130] * 83)
        first = m.update(2 * FOUR_HOURS, D(190), D(120), D(180))
        self.assertEqual(first.stop, D(110))
        next_bar = m.update(3 * FOUR_HOURS, D(190), D(118), D(180))
        self.assertEqual(next_bar.stop, D(120))
        self.assertIsNone(m.update(4 * FOUR_HOURS, D(190), D(119), D(180)))

    def test_trail_moves_up_when_the_oldest_of_84_lows_leaves(self):
        m = self.winner(lows=[105] + [130] * 83)
        first = m.update(2 * FOUR_HOURS, D(190), D(120), D(180))
        self.assertEqual(first.stop, D(110))
        next_bar = m.update(3 * FOUR_HOURS, D(190), D(115), D(180))
        self.assertEqual(next_bar.stop, D(120))

    def test_offline_replay_uses_confirmed_protection_instead_of_proposed_trail(self):
        m = self.winner()
        confirmed = dict(campaign=FOUR_HOURS, stop='100', take='500', accepted_at_ms=FOUR_HOURS)
        first = m.update(2 * FOUR_HOURS, D(190), D(105), D(180), effective_protection=confirmed)
        second = m.update(3 * FOUR_HOURS, D(190), D(120), D(180), effective_protection=confirmed)
        self.assertEqual((first.stop, second.stop), (D(130), D(130)))
        self.assertIsNone(m.update(4 * FOUR_HOURS, D(190), D(100), D(180),
                                  effective_protection=confirmed))

    def test_protection_is_not_backdated_to_a_candle_before_acceptance(self):
        for accepted in (None, FOUR_HOURS + 1):
            with self.subTest(accepted=accepted):
                m = self.winner(extended=True)
                confirmed = dict(campaign=FOUR_HOURS, stop='130', take='500', accepted_at_ms=accepted)
                held = m.update(2 * FOUR_HOURS, D(190), D(120), D(180), effective_protection=confirmed)
                self.assertEqual(held.stop, D(130))
                if accepted is not None:
                    self.assertIsNone(m.update(3 * FOUR_HOURS, D(190), D(120), D(180),
                                              effective_protection=confirmed))


if __name__ == '__main__':
    unittest.main()
