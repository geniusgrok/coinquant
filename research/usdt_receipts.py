"""Append-only CoinGecko USDT daily observations for research, never orders.

Availability is the local receipt time, not a historical date label or the
vendor's usual 00:10 release. Old downloads cannot become earlier evidence.
"""
import argparse
from decimal import Decimal
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.request import Request, urlopen


DAY = 86_400_000
SOURCE = 'coingecko:tether:usd:market_chart:daily'
URL = 'https://api.coingecko.com/api/v3/coins/tether/market_chart?vs_currency=usd&days=14&interval=daily'


def digest(value):
    return hashlib.sha256(value).hexdigest()


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
        raise ValueError('invalid source number')
    result = Decimal(value)
    if not result.is_finite() or result <= 0:
        raise ValueError('nonpositive or nonfinite source number')
    return str(result)


def _points(raw, received_ms):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= 1_000_000:
        raise ValueError('invalid source response size')
    if type(received_ms) is not int or received_ms <= 0:
        raise ValueError('invalid receipt time')
    body = json.loads(raw.decode('utf-8'), parse_float=Decimal)
    if not isinstance(body, dict) or not isinstance(body.get('market_caps'), list) or not isinstance(body.get('prices'), list):
        raise ValueError('missing CoinGecko series')
    prices = {}
    for item in body['prices']:
        if not isinstance(item, list) or len(item) != 2 or type(item[0]) is not int:
            raise ValueError('invalid price point')
        if item[0] in prices:
            raise ValueError('duplicate price clock')
        prices[item[0]] = _number(item[1])
    points = []
    seen = set()
    for item in body['market_caps']:
        if not isinstance(item, list) or len(item) != 2 or type(item[0]) is not int:
            raise ValueError('invalid market-cap point')
        event_ms, value = item
        if event_ms % DAY:
            continue  # The API appends a drifting current intraday point.
        if event_ms in seen or event_ms not in prices or event_ms > received_ms - 600_000:
            raise ValueError('duplicate, unpaired or prematurely observed daily point')
        seen.add(event_ms)
        age_days = (received_ms // DAY) - (event_ms // DAY)
        points.append(dict(event_ms=event_ms, available_ms=received_ms,
                           received_ms=received_ms, market_cap_usd=_number(value),
                           usdt_price_usd=prices[event_ms], unit='USD',
                           data_era='first_local_receipt' if age_days <= 2 else 'late_historical_import',
                           revision_stage='settled_at_receipt' if received_ms >= event_ms + 2 * DAY + 600_000 else 'provisional'))
    if not points or points != sorted(points, key=lambda p: p['event_ms']):
        raise ValueError('missing or unordered completed daily points')
    return points


def _read(stream):
    stream.seek(0)
    records = []
    previous = None
    for line in stream:
        record = json.loads(line)
        stamp = record.pop('receipt_hash', None)
        if record.get('previous_receipt_hash') != previous or digest(json.dumps(record, sort_keys=True, separators=(',', ':')).encode()) != stamp:
            raise ValueError('receipt chain changed')
        record['receipt_hash'] = stamp
        records.append(record)
        previous = stamp
    return records


def append_response(path, raw, received_ms, *, capture='caller_supplied'):
    """Append one complete response; never replace a prior value or receipt."""
    points = _points(raw, received_ms)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(target, os.O_CREAT | os.O_RDWR | os.O_APPEND, 0o600)
    with os.fdopen(fd, 'r+', encoding='utf-8') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        records = _read(stream)
        if records and received_ms <= records[-1]['received_ms']:
            raise ValueError('receipt clock must advance')
        latest = {}
        for old in records:
            for point in old['points']:
                latest[point['event_ms']] = point
        for point in points:
            old = latest.get(point['event_ms'])
            point['revises'] = old['version_hash'] if old and (old['market_cap_usd'], old['usdt_price_usd']) != (point['market_cap_usd'], point['usdt_price_usd']) else None
            point['same_as'] = old['version_hash'] if old and point['revises'] is None else None
            point['version_hash'] = digest(json.dumps(dict(source=SOURCE, response_sha256=digest(raw), **point), sort_keys=True, separators=(',', ':')).encode())
        if capture not in ('caller_supplied', 'direct_https'):
            raise ValueError('unknown source capture method')
        record = dict(source=SOURCE, source_url=URL, capture=capture, received_ms=received_ms,
                      response_sha256=digest(raw), raw_response=raw.decode('utf-8'),
                      previous_receipt_hash=records[-1]['receipt_hash'] if records else None,
                      points=points)
        record['receipt_hash'] = digest(json.dumps(record, sort_keys=True, separators=(',', ':')).encode())
        stream.seek(0, os.SEEK_END)
        stream.write(json.dumps(record, sort_keys=True, separators=(',', ':')) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
        return record


def asof(path, decision_ms):
    """Latest *received* version per day as known at this manual decision."""
    if type(decision_ms) is not int or decision_ms <= 0:
        raise ValueError('invalid decision time')
    with open(path, encoding='utf-8') as stream:
        records = _read(stream)
    known = {}
    for record in records:
        if record['received_ms'] > decision_ms:
            break
        for point in record['points']:
            if point['event_ms'] <= decision_ms and point['available_ms'] <= decision_ms:
                known[point['event_ms']] = point
    return [known[key] for key in sorted(known)]


def signal_at(path, decision_ms):
    """One source event at an actual manual start, or no usable observation."""
    points = asof(path, decision_ms)
    latest_day = decision_ms // DAY * DAY
    expected = latest_day if decision_ms - latest_day >= 600_000 else latest_day - DAY
    if not points or points[-1]['event_ms'] != expected or len(points) < 4:
        return None
    tail = points[-4:]
    if [p['event_ms'] for p in tail] != [expected - n * DAY for n in (3, 2, 1, 0)]:
        return None
    cap = [Decimal(p['market_cap_usd']) for p in tail]
    crossed = cap[3] < cap[1] and cap[2] >= cap[0]
    return dict(event_ms=expected, crossed_negative=crossed,
                slope_fraction=str((cap[3] - cap[1]) / (2 * cap[1])),
                usdt_price_usd=tail[-1]['usdt_price_usd'],
                version_hashes=[p['version_hash'] for p in tail])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ledger', help='private append-only local JSONL receipt path')
    args = parser.parse_args()
    # Fixed public request: no account or manual-session fact leaves the host.
    request = Request(URL, headers={'User-Agent': 'coinquant-research/1'})
    with urlopen(request, timeout=15) as response:
        raw = response.read(1_000_001)
    record = append_response(args.ledger, raw, time.time_ns() // 1_000_000, capture='direct_https')
    print(json.dumps(dict(receipt_hash=record['receipt_hash'], received_ms=record['received_ms'],
                          daily_points=len(record['points'])), sort_keys=True))


if __name__ == '__main__':
    main()
