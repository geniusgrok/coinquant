"""Point-in-time DFII10 rows for any historical instant, in the production row format.

Reuses the verified ALFRED originals and the frozen availability rule. Only
vintages whose delayed availability is before `now` are visible, exactly as
`coinquant.dfii10.Source.snapshot` filters live vintage dates.
"""
import csv
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from io import TextIOWrapper
import json
from pathlib import Path
from urllib.parse import urlencode
from zipfile import ZipFile

from coinquant.dfii10 import available

ROOT = Path(__file__).resolve().parents[1] / 'evidence' / 'real-yield-20260924' / 'alfred'

COMMON = [('form[units]', 'lin'), ('form[obs_start_date]', '2019-01-01'),
          ('form[obs_end_date]', '2026-09-19'), ('form[entered_vintage_dates]', ''),
          ('form[file_type]', '3'), ('form[file_format]', 'csv'),
          ('form[download_data]', 'Download data')]


def load(root):
    root = Path(root)
    receipt = json.loads((root/'RECEIPT.json').read_text())
    assert receipt['observation_start'] == '2019-01-01'
    assert receipt['observation_end'] == '2026-09-19'
    updates = {}
    selected_dates = []
    counts = {'vintage_dates': 0, 'updates': 0, 'revisions': 0}
    for attempt in receipt['attempts']:
        if attempt['label'] == 'single':
            continue  # acquisition probe duplicates an included batch vintage
        path = root/attempt['path']
        raw = path.read_bytes()
        assert len(raw) == attempt['response_bytes']
        assert sha256(raw).hexdigest() == attempt['response_sha256']
        assert attempt['http_status'] == 200 and attempt['content_type'] == 'application/zip'
        with ZipFile(path) as archive:
            assert archive.namelist() == attempt['members']
            names = [n for n in archive.namelist() if n.endswith('.csv')]
            assert len(names) == 1
            with archive.open(names[0]) as stream:
                reader = csv.reader(TextIOWrapper(stream, encoding='utf-8-sig', newline=''))
                header = next(reader)
                assert header[0] == 'observation_date'
                dates = [datetime.strptime(name, 'DFII10_%Y%m%d').date() for name in header[1:]]
                assert dates == sorted(set(dates))
                assert len(dates) == attempt['selected_count']
                selected_dates.extend(dates)
                batch = {v: [] for v in dates}
                for row in reader:
                    assert len(row) == len(header)
                    observation = datetime.strptime(row[0], '%Y-%m-%d').date()
                    for vintage, value in zip(dates, row[1:]):
                        if value:
                            assert observation <= vintage
                            number = Decimal(value)
                            assert number.is_finite()
                            batch[vintage].append((observation, number))
                            counts['updates'] += 1
                for vintage in dates:
                    assert vintage not in updates
                    updates[vintage] = batch[vintage]
        body = urlencode(COMMON + [('form[selected_vintage_dates][]', str(v)) for v in dates]).encode()
        assert len(body) == attempt['request_bytes']
        assert sha256(body).hexdigest() == attempt['request_sha256']
    assert selected_dates == sorted(set(selected_dates))
    assert len(selected_dates) == receipt['vintages']['count'] == 1914
    assert [str(selected_dates[0]), str(selected_dates[-1])] == [receipt['vintages']['first'], receipt['vintages']['last']]
    assert sha256(' '.join(map(str, selected_dates)).encode()).hexdigest() == receipt['vintages']['sha256']
    assert counts['updates'] == 1929
    counts['vintage_dates'] = len(selected_dates)
    return updates, counts


class History:
    def __init__(self, root=ROOT):
        updates, self.counts = load(root)
        self.dates = sorted(updates)
        self.updates = updates
        self.times = [available(v) for v in self.dates]
        self.current = {}
        self.index = 0
        self.last_now = None
        self.cached = None

    def snapshot(self, now):
        now = int(now)
        if self.last_now is not None and now < self.last_now:
            raise ValueError('history snapshots must be requested in time order')
        moved = False
        while self.index < len(self.dates) and self.times[self.index] < now:
            vintage = self.dates[self.index]
            for observation, value in self.updates[vintage]:
                self.current[observation] = (value, vintage)
            self.index += 1
            moved = True
        day = datetime.fromtimestamp(now / 1000, timezone.utc).date()
        if not moved and self.cached is not None and self.cached[0] == day:
            self.last_now = now
            return dict(self.cached[1])
        self.last_now = now
        observations = sorted(self.current)
        latest = observations[-1] if observations else None
        prior = observations[-21] if len(observations) >= 21 else None
        reason = ('no_historical_vintage' if latest is None else
                  'insufficient_20_prior_observations' if prior is None else
                  'stale_observation_over_7_calendar_days' if (day - latest).days > 7 else None)
        row = dict(latest_value=str(self.current[latest][0]) if latest else None,
                   prior20_value=str(self.current[prior][0]) if prior else None,
                   latest_observation_date=str(latest) if latest else None,
                   prior20_observation_date=str(prior) if prior else None,
                   latest_value_available_ms=available(self.current[latest][1]) if latest else None,
                   prior20_value_available_ms=available(self.current[prior][1]) if prior else None,
                   asof_vintage_date=str(self.dates[self.index - 1]) if self.index else None,
                   missing_reason=reason, response_sha256='historical-alfred-originals')
        self.cached = (day, row)
        return dict(row)
