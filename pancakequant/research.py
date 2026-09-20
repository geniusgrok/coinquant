"""Frozen, market-independent invocation assumptions and evidence identities."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .types import Blocked, number

SPEC_PATH = Path(__file__).resolve().parent.parent / 'research' / 'spec.json'


def timestamp(text):
    try:
        value = datetime.fromisoformat(text.replace('Z', '+00:00'))
    except (ValueError, AttributeError) as exc:
        raise Blocked('timestamp must be ISO 8601 with UTC offset') from exc
    if value.tzinfo is None or value.utcoffset().total_seconds() != 0:
        raise Blocked('explicit UTC timestamps are required')
    return int(value.timestamp() * 1000)


def iso(value):
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat().replace('+00:00', 'Z')


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def spec():
    value = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    if (value['start'] != '2020-01-01T00:00:00Z' or value['initial_cny'] != '10000'
            or value['leverage'] != 20 or value['symbol'] != 'BTCUSD'
            or value.get('bar_interval_ms') != 3_600_000
            or value.get('liquidity_activity_basis_ms') != 60_000
            or value['cagr_minimum_exclusive'] != '2' or value['mdd_maximum_exclusive'] != '0.20'):
        raise Blocked('formal economic mandate changed; do not silently qualify')
    if timestamp(value['end']) > int(datetime.now(timezone.utc).timestamp() * 1000):
        raise Blocked('research endpoint is in the future')
    for name in ('spread_fraction', 'slippage_fraction', 'volume_participation',
                 'book_proxy_fraction', 'initial_conversion_cost'):
        if not 0 < number(value[name]) < 1:
            raise Blocked('invalid nonzero frozen cost or liquidity assumption')
    return value


def invocations(value, *, stress=False):
    """No price, signal, profit, local PRNG state or parameter search is consulted."""
    start, end = timestamp(value['start']), timestamp(value['end'])
    current, index, skip_until = start, 0, -1
    while current < end:
        if stress and index == value['stress_skip_after_trigger']:
            skip_until = current + value['stress_absence_days'] * 86_400_000
        if current >= skip_until:
            yield current
        draw = int.from_bytes(hashlib.sha256(f'{value["seed"]}|{index}'.encode()).digest()[:8], 'big')
        current += value['gap_hours'][draw % len(value['gap_hours'])] * 3_600_000
        index += 1


def source_identity():
    root = Path(__file__).resolve().parent
    return {p.name: digest(p) for p in sorted(root.glob('*.py'))}
