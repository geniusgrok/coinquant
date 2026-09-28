"""Dated CNY per USD for account valuation (FRED DEXCHUS, noon New York buying rate).

A rate is used from 17:00 UTC of its observation date, the latest published rate
at or before each instant. USDT is valued at par with USD; the conversion cost
is charged separately by the caller.
"""
import bisect
import csv
import hashlib
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / 'evidence' / 'rebuild-20260927' / 'inputs' / 'DEXCHUS.csv'
SHA256 = '733c2bbccfd42448d72f8b7a7ee2cd744f1b3263ac1be88e34260b9c7b2ec874'
PUBLISHED_UTC_HOUR = 17


class DatedFX:
    def __init__(self, path=PATH):
        raw = Path(path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != SHA256:
            raise ValueError('DEXCHUS input changed')
        self.times, self.rates = [], []
        for row in csv.DictReader(raw.decode().splitlines()):
            if row['DEXCHUS'] in ('', '.'):
                continue
            day = datetime.strptime(row['observation_date'], '%Y-%m-%d').replace(
                hour=PUBLISHED_UTC_HOUR, tzinfo=timezone.utc)
            self.times.append(int(day.timestamp() * 1000))
            self.rates.append(D(row['DEXCHUS']))

    def __call__(self, now_ms):
        index = bisect.bisect_right(self.times, int(now_ms)) - 1
        if index < 0:
            raise ValueError('no published CNY rate before this instant')
        return self.rates[index]
