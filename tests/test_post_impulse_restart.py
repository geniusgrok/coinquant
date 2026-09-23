import json
import unittest
from decimal import Decimal as D

from coinquant.campaign import Campaign, ORIGIN, disposition
from coinquant.opportunities import FOUR_HOURS, Opportunity, Opportunities


def sample_bars():
    flat = (D(101), D(99), D(100))
    return [flat] * 20 + [
        (D(120), D(99), D(115)),  # original long impulse; R=7.5
        (D(119), D(112), D(114)),  # first pullback is 8 below the prior high
        (D(121), D(113), D(120)),  # a breakout before invalidation is too early
        (D(118), D(107), D(109)),  # original midpoint stop is crossed
        (D(121), D(108), D(120)),  # later completed close confirms restart
    ]


class PostImpulseRestartTests(unittest.TestCase):
    def test_restart_needs_a_distinct_close_after_parent_stop(self):
        base = Opportunities('impulse_hold')
        candidate = Opportunities('post_impulse_restart')
        base_states = []
        candidate_states = []
        for i, row in enumerate(sample_bars()):
            end = (i + 1) * FOUR_HOURS
            base_state = base.update(end, *row)
            candidate_state = candidate.update(end, *row)
            base_states.append(base_state)
            candidate_states.append(candidate_state)
            self.assertEqual(candidate.original.__dict__, base.__dict__)
            if base_state is not None:
                self.assertEqual(candidate_state, base_state)

        parent_id = 21 * FOUR_HOURS
        self.assertEqual(candidate_states[22].identity, parent_id)
        self.assertIsNone(candidate_states[23])
        child = candidate_states[24]
        self.assertEqual((child.identity, child.direction, child.stop, child.parent_identity),
                         (25 * FOUR_HOURS, 1, D(112), parent_id))
        self.assertEqual(child.take, D(120) * (D(120) / D(112)) ** 20)
        self.assertEqual(child.expires, child.identity + 42 * FOUR_HOURS)

    def test_new_impulse_cancels_waiting_child_and_keeps_original_priority(self):
        rows = sample_bars()[:24] + [(D(140), D(108), D(135))]
        base = Opportunities('impulse_hold')
        candidate = Opportunities('post_impulse_restart')
        for i, row in enumerate(rows):
            end = (i + 1) * FOUR_HOURS
            primary = base.update(end, *row)
            state = candidate.update(end, *row)
            if primary is not None:
                self.assertEqual(state, primary)
        self.assertEqual(state.identity, 25 * FOUR_HOURS)
        self.assertIsNone(state.parent_identity)

    def test_candidate_signal_does_not_close_an_existing_same_side_campaign(self):
        child = Opportunity(100, 1, D(90), D(200), 200,
                            parent_identity=20)
        self.assertEqual(disposition(child, D(1), consumed=20), 'hold')

    def test_pending_restart_state_survives_campaign_checkpoint(self):
        campaign = Campaign('post_impulse_restart')
        rows = sample_bars()
        for row in rows[:24]:
            campaign.update(campaign.last + FOUR_HOURS, *row)
        restored = Campaign.restore(json.loads(json.dumps(campaign.checkpoint())))
        signal = restored.update(restored.last + FOUR_HOURS, *rows[24])
        self.assertEqual((signal.identity, signal.parent_identity, signal.stop),
                         (ORIGIN + 25 * FOUR_HOURS, ORIGIN + 21 * FOUR_HOURS, D(112)))

    def test_future_perturbation_cannot_change_an_earlier_child_signal(self):
        rows = sample_bars()
        full = []
        changed = []
        a = Opportunities('post_impulse_restart')
        b = Opportunities('post_impulse_restart')
        future = (D(1000), D(1), D(5))
        future_rows = [(D(101), D(99), D(100))] * 3
        for i, row in enumerate(rows + future_rows):
            end = (i + 1) * FOUR_HOURS
            full.append(a.update(end, *row))
            changed.append(b.update(end, *(row if i < 25 else future)))
        self.assertEqual(full[:25], changed[:25])
        self.assertEqual(full[24].parent_identity, 21 * FOUR_HOURS)


if __name__ == '__main__':
    unittest.main()
