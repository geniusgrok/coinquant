"""Frozen historical public features; no adapters, requests, or financial replay.

The reader is deliberately identical in Spotquant and Coinquant. Only Spotquant
provides the market helpers used by the offline builder.
"""
from bisect import bisect_right
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

DAY = 86400000
FUNDING_LAG = 28800000
BASIS_LAG = 60000
START_MS = 1577836800000
END_MS = 1789862400000
MARKET_HASH_FIELDS = {
    'futures_market_sha256', 'spot_daily_sha256', 'warmup_trade_sha256',
    'warmup_funding_sha256', 'september_funding_archive_sha256',
    'original_futures_artifact_sha256',
}
RAW_SHA256 = '1d87be0b4c8cd8a7eacd4970a1a194e5f1ed0b2f3aa3710a43417aa9ab066ef2'
ASSUMPTIONS = {
    'funding_available_lag_ms': FUNDING_LAG,
    'funding_stale_age_gte_ms': FUNDING_LAG,
    'funding_model': 'actual settled historical rate; preserve raw settlement jitter; never predicted funding',
    'basis_available_lag_ms': BASIS_LAG,
    'basis_observation': 'completion boundary of previous matched UTC-day trade closes',
    'basis_model': 'daily futures trade close / spot trade close - 1; not instantaneous executable basis',
    'basis_publication': 'modeled 60000ms after completed UTC-day boundary, not observed publication',
    'basis_max_age_ms': DAY,
    'basis_requires_current_utc_availability_date': True,
    'lookup_window': [START_MS, END_MS],
    'lookup_end_exclusive': True,
}


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _hash(value):
    return hashlib.sha256(value).hexdigest()


def _digest(value):
    if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('invalid SHA-256 identity')
    return value


def _time(value):
    if type(value) is not int or value < 0:
        raise ValueError('timestamps must be nonnegative integer milliseconds')
    return value


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _read(raw):
    try:
        return json.loads(raw, object_pairs_hook=_unique_object,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON number')))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('invalid feature JSON') from exc


class FeatureBook:
    """Validate an immutable artifact once; query only information available now.

    ``last_lookup`` records the raw and artifact identities, selected observation,
    availability, age and explicit missing cause for an optional decision journal.
    No historical lookups outside the frozen economic window are permitted.
    """

    def __init__(self, path, expected_sha256=None):
        self._load(Path(path).read_bytes(), expected_sha256)

    def _load(self, raw, expected_sha256=None):
        # The builder uses the same validator before exclusive output creation.
        self.sha256 = _hash(raw)
        if expected_sha256 is not None and self.sha256 != _digest(expected_sha256):
            raise ValueError('artifact file hash mismatch')
        artifact = _read(raw)
        if not isinstance(artifact, dict) or artifact.get('format') != 'edge-features-v1':
            raise ValueError('unsupported feature format')
        payload = {key: value for key, value in artifact.items() if key != 'content_sha256'}
        if _hash(_canonical(payload)) != _digest(artifact.get('content_sha256')):
            raise ValueError('artifact content hash mismatch')
        self.source = artifact.get('source')
        if not isinstance(self.source, dict) or _digest(self.source.get('raw_sha256')) != RAW_SHA256:
            raise ValueError('unregistered raw identity')
        if self.source.get('availability_assumptions') != ASSUMPTIONS:
            raise ValueError('unregistered availability assumptions')
        identities = self.source.get('market_identities')
        if not isinstance(identities, dict) or set(identities) != MARKET_HASH_FIELDS:
            raise ValueError('missing market identities')
        for value in identities.values():
            _digest(value)
        if not isinstance(artifact.get('coverage'), dict):
            raise ValueError('missing feature coverage')
        self.records = {}
        self.times = {}
        for name in ('funding', 'basis'):
            rows = artifact.get(name)
            if not isinstance(rows, list):
                raise ValueError('feature records must be lists')
            previous_observation = previous_available = -1
            parsed = []
            for row in rows:
                if not isinstance(row, dict):
                    raise ValueError('invalid feature record')
                observation = _time(row.get('observation_ms'))
                available = _time(row.get('available_ms'))
                lag = FUNDING_LAG if name == 'funding' else BASIS_LAG
                if available != observation + lag:
                    raise ValueError('incorrect feature availability')
                if name == 'basis' and observation % DAY:
                    raise ValueError('basis observation is not a UTC-day completion boundary')
                if observation <= previous_observation or available <= previous_available:
                    raise ValueError('feature timestamps must be strictly sorted and unique')
                previous_observation, previous_available = observation, available
                value = row.get('value')
                cause = row.get('cause')
                if value is None:
                    if not isinstance(cause, str) or not cause:
                        raise ValueError('missing value requires an explicit cause')
                    parsed.append((observation, available, None, cause))
                else:
                    if not isinstance(value, str):
                        raise ValueError('feature values must be decimal strings')
                    try:
                        number = Decimal(value)
                    except InvalidOperation as exc:
                        raise ValueError('invalid decimal feature') from exc
                    if not number.is_finite():
                        raise ValueError('nonfinite feature value')
                    if cause is not None:
                        raise ValueError('known value cannot carry a missing cause')
                    parsed.append((observation, available, number, None))
            self.records[name] = parsed
            self.times[name] = [row[1] for row in parsed]
        coverage = artifact['coverage']
        if coverage.get('window') != [START_MS, END_MS] or coverage.get('end_exclusive') is not True:
            raise ValueError('invalid frozen coverage window')
        for name in ('funding', 'basis'):
            if coverage.get(name) != _coverage(artifact[name], name):
                raise ValueError('feature coverage does not match records')
        self.last_lookup = None

    def value(self, name, now_ms):
        if name not in self.records:
            raise ValueError('unknown feature name')
        now_ms = _time(now_ms)
        record = None
        cause = None
        if not START_MS <= now_ms < END_MS:
            cause = 'outside_frozen_window'
        else:
            index = bisect_right(self.times[name], now_ms) - 1
            if index < 0:
                cause = 'not_yet_available'
            else:
                record = self.records[name][index]
                age = now_ms - record[1]
                if name == 'funding' and age >= FUNDING_LAG:
                    cause = 'stale_funding'
                elif name == 'basis' and age > DAY:
                    cause = 'stale_basis'
                elif name == 'basis' and record[1] // DAY != now_ms // DAY:
                    cause = 'basis_availability_date_mismatch'
                else:
                    cause = record[3]
        value = None if cause is not None else record[2]
        self.last_lookup = {
            'name': name, 'now_ms': now_ms, 'value': None if value is None else str(value),
            'cause': cause, 'artifact_sha256': self.sha256,
            'raw_sha256': self.source['raw_sha256'],
            'market_identities': dict(self.source['market_identities']),
            'observation_ms': None if record is None else record[0],
            'available_ms': None if record is None else record[1],
            'age_ms': None if record is None else now_ms - record[1],
        }
        return value


def _coverage(rows, name):
    """Exact integer-ms availability intervals, clipped to the frozen window."""
    valid_ms = 0
    gaps = []
    cursor = START_MS
    for index, row in enumerate(rows):
        start = max(START_MS, row['available_ms'])
        next_time = rows[index + 1]['available_ms'] if index + 1 < len(rows) else END_MS
        expiry = (row['available_ms'] + FUNDING_LAG if name == 'funding'
                  else min(row['available_ms'] + DAY + 1, (row['available_ms'] // DAY + 1) * DAY))
        end = min(END_MS, next_time, expiry)
        if row['value'] is None or end <= start:
            continue
        if start > cursor:
            gaps.append([cursor, start])
        valid_ms += end - start
        cursor = max(cursor, end)
    if cursor < END_MS:
        gaps.append([cursor, END_MS])
    return {
        'raw_records': len(rows),
        'first_observation_ms': rows[0]['observation_ms'] if rows else None,
        'last_observation_ms': rows[-1]['observation_ms'] if rows else None,
        'records_available_in_window': sum(START_MS <= row['available_ms'] < END_MS for row in rows),
        'negative_records': sum(row['value'] is not None and Decimal(row['value']) < 0 for row in rows),
        'null_records': sum(row['value'] is None for row in rows),
        'known_duration_ms': valid_ms,
        'missing_duration_ms': END_MS - START_MS - valid_ms,
        'missing_intervals_ms': gaps,
    }

