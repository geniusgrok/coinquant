"""Point-in-time DFII10 rows for any historical instant, in the production row format.

Reuses the verified ALFRED originals and the frozen availability rule. Only
vintages whose delayed availability is before `now` are visible, exactly as
`coinquant.dfii10.Source.snapshot` filters live vintage dates.
"""
from datetime import datetime, timezone
from pathlib import Path

from coinquant.dfii10 import available
from research.dfii10_asof import load

ROOT = Path(__file__).resolve().parents[1] / 'evidence' / 'real-yield-20260924' / 'alfred'


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
