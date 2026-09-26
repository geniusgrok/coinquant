"""Use verified native minute days while retaining the original signal clock.

No synthetic interpolation. Each refined hour must reproduce the original
hourly OHLC and volume exactly. Refinement changes execution precision, never
manual invocation timing or four-hour OHLC signal inputs. Native liquidity
resolution changes on the refined days and remains explicit in the evidence. Full-day coverage avoids selecting
only favorable minutes from an event.
"""
import argparse
from datetime import datetime, timezone
import csv
import gzip
import json
from pathlib import Path
from unittest.mock import patch

from research.legacy import replay
from research.legacy.config import load
from coinquant.data import Dataset, Tick, MINUTE
from coinquant.research import digest, iso
from coinquant.types import Bar, Blocked, D


class RefinedDataset(Dataset):
    def __init__(self, *args, minutes, **kwargs):
        super().__init__(*args, **kwargs)
        self.minute_days = {}
        root = Path(minutes)
        summary = json.loads((root / 'SUMMARY.json').read_text())
        for record in summary:
            base = root / record['day']; inventory = base / 'v5-inventory.json'
            if digest(inventory) != record['inventory_sha256']:
                raise Blocked('refinement inventory changed')
            inv = json.loads(inventory.read_text())
            if inv['symbol'] != 'BTCUSD' or inv['category'] != 'inverse' or inv['bar_interval_ms'] != MINUTE:
                raise Blocked('different contract or resolution in refinement')
            entry = next(iter(inv['shards'].values()))['bars']; path = base / entry['path']
            if path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']:
                raise Blocked('refinement bytes/hash changed')
            with gzip.open(path,'rt') as f:
                rows = list(csv.DictReader(f))
            day = []
            for r in rows:
                t=int(r['time'])
                trade=Bar(t,*(D(r[k]) for k in ('open','high','low','close','volume')))
                mark=Bar(t,*(D(r['mark_'+k]) for k in ('open','high','low','close')))
                day.append(Tick(trade,mark,MINUTE))
            start=int(datetime.fromisoformat(record['day']).replace(tzinfo=timezone.utc).timestamp()*1000)
            if [x.trade.time for x in day] != list(range(start,start+86400000,MINUTE)):
                raise Blocked('refinement day incomplete')
            self.minute_days[record['day']]=day
        self.manifest = {**self.manifest,'execution_refinement':{
            'days':summary,'summary_sha256':digest(root/'SUMMARY.json'),
            'scope':'verified native minute days; hourly elsewhere; no new invocations'}}

    def ticks(self):
        for tick in super().ticks():
            day=self.minute_days.get(iso(tick.trade.time)[:10])
            if day is None:
                yield tick
                continue
            index=(tick.trade.time % 86400000)//MINUTE
            hour=day[index:index+60]
            if replay.aggregate([x.trade for x in hour]) != tick.trade or replay.aggregate([x.mark for x in hour]) != tick.mark:
                raise Blocked('native minute/hour OHLC or volume disagreement')
            yield from hour


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True)
    p.add_argument('--minutes',required=True);p.add_argument('--output',required=True)
    a=p.parse_args()
    def dataset(*args,**kwargs):return RefinedDataset(*args,minutes=a.minutes,**kwargs)
    with patch.object(replay,'Dataset',dataset):
        result=replay.run(a.manifest,a.output,load('config.example.json'))
    print(json.dumps(result))
