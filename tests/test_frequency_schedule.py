import unittest
import hashlib
import json
from unittest.mock import patch
from coinquant.types import Blocked
from coinquant.research import spec, invocations, timestamp
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


class FrozenInvocationTests(unittest.TestCase):
    def test_complete_normal_and_absence_sequences_are_fixed(self):
        expected = (
            (False, 795, 'f8fb73bebf142ddcc3ed4a3e6b12b4dd7abed1e27bcd8a4ff1c93aec4fe0b32a'),
            (True, 787, '7e368f55152e59d5e42a1288201d318994bb9854ffcdb397188cc2df1c256f0c'),
        )
        for stress, count, digest in expected:
            with self.subTest(stress=stress):
                calls = list(invocations(spec(), stress=stress))
                self.assertEqual(len(calls), count)
                raw = json.dumps(calls, separators=(',', ':')).encode()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)

    def test_sequence_identity_mismatch_blocks_replay(self):
        value = dict(spec(), invocation_draws_sha256='0' * 64)
        with self.assertRaisesRegex(Blocked, 'identity invalid'):
            list(invocations(value))

    def test_missing_sequence_blocks_replay(self):
        value = spec()
        with patch('coinquant.research.Path.read_bytes', side_effect=OSError('missing')):
            with self.assertRaisesRegex(Blocked, 'sequence unavailable'):
                list(invocations(value))
