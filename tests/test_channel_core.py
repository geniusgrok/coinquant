import unittest
from decimal import Decimal as D

from coinquant.campaign import disposition
from coinquant.channel_core import ChannelCore, FOUR_HOURS


class ChannelCoreTest(unittest.TestCase):
    def test_breakout_ownership_exit_and_gap(self):
        model = ChannelCore()
        for i in range(1, 21):
            self.assertIsNone(model.update(i*FOUR_HOURS, D(101), D(99), D(100)))
        first = model.update(21*FOUR_HOURS, D(103), D(100), D(102))
        self.assertEqual(first.identity, 21*FOUR_HOURS)
        self.assertEqual(disposition(first, D(0), first.identity), 'consumed')
        self.assertEqual(disposition(first, D(1), first.identity), 'hold')
        second = model.update(22*FOUR_HOURS, D(103), D(100), D(101))
        self.assertEqual(second.identity, first.identity)
        self.assertIsNone(model.update(23*FOUR_HOURS, D(100), D(97), D(98)))
        self.assertEqual(disposition(None, D(1), first.identity), 'exit')
        next_one = model.update(24*FOUR_HOURS, D(105), D(99), D(104))
        self.assertNotEqual(next_one.identity, first.identity)
        with self.assertRaises(ValueError):
            model.update(26*FOUR_HOURS, D(105), D(99), D(104))


if __name__ == '__main__':
    unittest.main()
