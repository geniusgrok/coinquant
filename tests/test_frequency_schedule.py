import unittest
from pancakequant.research import spec, invocations, timestamp
from research.persistent_hold_replay import decision_times, HOUR, channel_state

class FrequencyTests(unittest.TestCase):
    def test_sparse_schedule_unchanged_and_hourly_contains_it(self):
        frozen=spec();end=timestamp(frozen['development_end'])
        sparse=decision_times(frozen,end,'sparse');hourly=decision_times(frozen,end,'hourly')
        self.assertEqual(sparse,set(t for t in invocations(frozen) if t<end))
        self.assertEqual(len(sparse),468)
        self.assertEqual(len(hourly),35064)
        self.assertTrue(sparse<=hourly)
        self.assertNotIn(end,hourly)
        with self.assertRaises(ValueError):decision_times(frozen,end,'unknown')

    def test_daily_signal_requires_completed_prior_channel(self):
        bars=[(100,90,95)]*20
        self.assertEqual(channel_state(bars,0),0)
        self.assertEqual(channel_state(bars+[(102,94,101)],0),1)
        self.assertEqual(channel_state(bars+[(99,88,89)],1),-1)
        self.assertEqual(channel_state(bars+[(100,90,95)],1),1)
