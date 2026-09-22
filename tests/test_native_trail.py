from unittest import TestCase
from decimal import Decimal as D
from research.native_trail import step

class NativeTrailTests(TestCase):
    def test_low_before_high_cannot_use_future_high(self):
        bar=tuple(map(D,('100','120','95','115')))
        self.assertEqual(step(D(100),bar,D(80),'low_first'),(D(120),None))
        self.assertEqual(step(D(100),bar,D(80),'high_first'),(D(120),D(108)))

    def test_gap_is_filled_beyond_stop_and_fixed_stop_is_retained(self):
        self.assertEqual(step(D(120),tuple(map(D,('90','100','85','95'))),D(80),'low_first'),(D(120),D(90)))
        self.assertEqual(step(D(100),tuple(map(D,('100','101','94','99'))),D(95),'low_first'),(D(100),D(95)))
