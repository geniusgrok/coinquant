"""The full input superset must include impulse-only entry and later exit calls."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from research import renewal_risk_replay as replay


class FullCoverageTests(unittest.TestCase):
    def test_impulse_entry_renewal_and_first_flat_exit_are_covered(self):
        hour=replay.HOUR
        row=[0,'1','1','1','1']
        warm={t:row for t in range(-4*hour,0,hour)}
        trade={t:row for t in range(0,16*hour,hour)}
        cache=({'klines':trade},None,warm)
        cfg={'start':'1970-01-01T00:00:00Z','end':'1970-01-01T16:00:00Z',
             'slippage_fraction':'0.001','spread_fraction':'0.0002'}
        calls=[0,4*hour,8*hour,12*hour]
        daily={t:SimpleNamespace(score=1 if t==4*hour else 0) for t in calls}
        with patch.object(replay,'spec',return_value=cfg), \
             patch.object(replay,'invocations',return_value=iter(calls)), \
             patch.object(replay,'daily_snapshots',return_value=daily), \
             patch.object(replay,'published_daily_key',side_effect=lambda t:t), \
             patch.object(replay,'Campaign') as campaign:
            campaign.return_value.update.side_effect=[
                SimpleNamespace(direction=1),None,None,None,None]
            self.assertEqual(replay.full_window_hours(cache,()),calls[:3])


if __name__=='__main__':
    unittest.main()
