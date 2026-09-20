"""Streaming native-contract input validation; missing funding is never zero.

A manifest identifies complete original files and their provenance. A matching
hash proves byte identity, not authenticity. Synthetic/proxy provenance remains
visible in every replay result and cannot be upgraded by favorable metrics.
"""
from dataclasses import dataclass
import csv
import gzip
import json
from pathlib import Path

from .research import digest, timestamp
from .types import Bar, Blocked, D, INTERVAL_MS, Rules, number

MINUTE = 60_000
HOUR = 3_600_000
SUPPORTED_INTERVALS = (MINUTE, HOUR)


@dataclass(frozen=True)
class Tick:
    trade: Bar
    mark: Bar


class Dataset:
    def __init__(self, path, mandate, *, warmup_bars=120):
        self.path = Path(path).resolve()
        try:
            self.manifest = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            raise Blocked('dataset manifest is missing or invalid; no synthetic fallback') from exc
        m = self.manifest
        self.start, self.end = timestamp(m['start']), timestamp(m['end'])
        self.warmup_start = timestamp(m['warmup_start'])
        if (self.start, self.end) != (timestamp(mandate['start']), timestamp(mandate['end'])):
            raise Blocked('dataset window differs from the frozen research window')
        for key, expected in (('venue', 'bybit'), ('symbol', 'BTCUSD'),
                              ('contract_type', 'InversePerpetual'), ('settlement_coin', 'BTC')):
            if m.get(key) != expected:
                raise Blocked('different venue/contract/settlement data cannot be spliced')
        self.interval = m.get('bar_interval_ms')
        if (m.get('provenance') not in ('native', 'proxy', 'synthetic')
                or type(self.interval) is not int or self.interval not in SUPPORTED_INTERVALS
                or INTERVAL_MS % self.interval):
            raise Blocked('explicit provenance and a supported aligned trade/mark interval are required')
        if self.warmup_start > self.start - warmup_bars * 14_400_000 or self.warmup_start % 14_400_000:
            raise Blocked('insufficient complete pre-start signal warmup bars')
        self.files = {}
        for kind in ('bars', 'funding', 'rules'):
            entries = m['files'][kind]
            if not entries:
                raise Blocked(f'{kind} input is missing; do not assume zero or use another contract')
            self.files[kind] = []
            for entry in entries:
                p = (self.path.parent / entry['path']).resolve()
                if not p.is_relative_to(self.path.parent) or not p.is_file():
                    raise Blocked('data file path is invalid')
                if not entry.get('source') or p.stat().st_size != entry['bytes'] or digest(p) != entry['sha256']:
                    raise Blocked('raw data length/hash/provenance check failed')
                self.files[kind].append(p)
        self.funding = {}
        previous = -1
        for row in self.rows('funding'):
            t = int(row['time'])
            if t <= previous or t % self.interval:
                raise Blocked('funding timestamps duplicate, unordered or unaligned')
            previous = t
            self.funding[t] = (number(row['rate']), number(row['mark'], positive=True))
        self.tiers = []
        previous = -1
        for row in self.rows('rules'):
            row = {k: (int(v) if k in ('time', 'launch_ms', 'funding_interval_ms') else number(v)) for k, v in row.items()}
            if row['time'] <= previous or row['funding_interval_ms'] <= 0 or row['funding_interval_ms'] % self.interval:
                raise Blocked('historical rule timeline is invalid')
            if row['launch_ms'] > self.warmup_start:
                raise Blocked('claimed contract listing cannot cover required warmup')
            previous = row['time']
            self.tiers.append(row)
        if not self.tiers or self.tiers[0]['time'] > self.warmup_start:
            raise Blocked('initial historical margin/cost rules are missing')
        # Funding schedule changes must be dated in the same authoritative rules.
        index = 0
        for t in range(self.start, self.end, self.interval):
            while index + 1 < len(self.tiers) and self.tiers[index + 1]['time'] <= t:
                index += 1
            expected = t % self.tiers[index]['funding_interval_ms'] == 0
            if expected != (t in self.funding):
                raise Blocked(f'missing or unexpected funding event at {t}')

    def rows(self, kind):
        for path in self.files[kind]:
            opener = gzip.open if path.suffix == '.gz' else open
            with opener(path, 'rt', encoding='utf-8', newline='') as stream:
                yield from csv.DictReader(stream)

    def ticks(self):
        expected = self.warmup_start
        for r in self.rows('bars'):
            try:
                t = int(r['time'])
                if t != expected:
                    raise Blocked(f'missing, overlapping or unordered base bar at {expected}')
                trade = Bar(t, *(number(r[k]) for k in ('open', 'high', 'low', 'close', 'volume')))
                mark = Bar(t, *(number(r['mark_' + k]) for k in ('open', 'high', 'low', 'close')))
            except (KeyError, ValueError, TypeError) as exc:
                raise Blocked('invalid native trade/mark base-bar schema') from exc
            expected += self.interval
            if t >= self.end:
                raise Blocked('input extends beyond frozen endpoint')
            yield Tick(trade, mark)
        if expected != self.end:
            raise Blocked(f'incomplete history: ends at {expected}, required {self.end}')

    @staticmethod
    def venue_rules(row, mark):
        if not 0 < row['liquidation_fee'] < D('0.10'):
            raise Blocked('nonzero historical liquidation cost is required')
        return Rules(row['tick'], row['step'], row['minimum'],
                     min(row['maximum'], row['market_maximum']), row['risk_limit_btc'] * mark,
                     row['maintenance_rate'], row['taker_fee'], row['launch_ms'])
