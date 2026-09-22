from collections import deque
from decimal import Decimal as D
import unittest
from research.native_channel_replay import channel_state


class ChannelState(unittest.TestCase):
    def test_state_persists_between_breakouts_and_reverses_on_opposite_break(self):
        window=deque([(D(2),D(1),D('1.5'))]*21,maxlen=21)
        self.assertEqual(channel_state(window,1),1)
        self.assertEqual(channel_state(window,-1),-1)
        window.append((D('1.2'),D('.4'),D('.5')))
        self.assertEqual(channel_state(window,1),-1)
        window.append((D(4),D('1.5'),D(3)))
        self.assertEqual(channel_state(window,-1),1)
