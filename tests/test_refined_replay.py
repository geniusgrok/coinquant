from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from pancakequant.data import Dataset, Tick, HOUR, MINUTE
from pancakequant.replay import _replay
from pancakequant.types import ModelConfig, Target, ZERO, Blocked
from test_replay import dataset_fixture


class RefinedReplayTests(unittest.TestCase):
    def test_mixed_resolution_retains_four_hour_signal_and_invocations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);manifest,frozen=dataset_fixture(root,interval=HOUR)
            ds=Dataset(manifest,frozen,warmup_bars=3);coarse=list(ds.ticks())
            minute=[]
            for tick in coarse:
                if tick.trade.time==ds.start+18*HOUR:
                    for offset in range(0,HOUR,MINUTE):
                        minute.append(Tick(replace(tick.trade,time=tick.trade.time+offset,volume=(tick.trade.volume//60 if offset<59*MINUTE else tick.trade.volume-(tick.trade.volume//60)*59)),
                                           replace(tick.mark,time=tick.mark.time+offset),MINUTE))
                else:minute.append(tick)
            seen=[]
            for name,rows in [('coarse',coarse),('mixed',minute)]:
                calls=[];out=root/name;out.mkdir()
                def decide(bars,snapshot,cfg,**kw):
                    calls.append((snapshot.time,bars.copy()))
                    return Target(bars[-1].time,ZERO,snapshot.mark,ZERO,ZERO,ZERO,ZERO,ZERO,'test flat')
                with patch.object(ds,'ticks',lambda:iter(rows)),patch('pancakequant.replay.decide',side_effect=decide):
                    result=_replay(ds,ModelConfig(),frozen,out)
                seen.append(calls)
                self.assertEqual(result['invocations'],len(calls))
            self.assertEqual(seen[0],seen[1])

    def test_missing_refined_tick_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);manifest,frozen=dataset_fixture(root,interval=HOUR)
            ds=Dataset(manifest,frozen,warmup_bars=3);rows=list(ds.ticks());rows.pop(1)
            out=root/'out';out.mkdir()
            with patch.object(ds,'ticks',lambda:iter(rows)),self.assertRaisesRegex(Blocked,'continuity'):
                _replay(ds,ModelConfig(),frozen,out)
