"""Local source qualification only; never a trading signal or historical PIT feed.

Inputs are private raw responses and the original manual schedule. Output is
aggregate metadata, with no source rows or exact manual starts.
"""
import argparse
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal as D
from hashlib import sha256
import json
from pathlib import Path
from statistics import median


SOURCE_ID = 'coinmetrics_community_usdt_capest_price_v1'
URL = ('https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?'
       'assets=usdt&metrics=CapMrktEstUSD,PriceUSD&frequency=1d&'
       'start_time=2020-01-01&end_time=2026-09-30&page_size=10000')
DAY_MS = 86_400_000
FIRST = date(2020, 1, 1)
LAST = date(2026, 9, 30)


def _positive(value):
    if not isinstance(value, str):
        raise ValueError('source decimal is not its original string')
    number = D(value)
    if not number.is_finite() or number <= 0:
        raise ValueError('invalid source decimal')
    return number


def coinmetrics(raw, receipt):
    if (receipt.get('source_id') != SOURCE_ID or receipt.get('url') != URL or
            receipt.get('http_status') != 200 or receipt.get('response_bytes') != len(raw) or
            receipt.get('response_sha256') != sha256(raw).hexdigest() or
            receipt.get('historical_first_receipt') is not None or receipt.get('historical_pit') is not False):
        raise ValueError('receipt/source identity mismatch')
    received = datetime.fromisoformat(receipt['observed_at_utc'])
    if received.tzinfo is None or received.astimezone(timezone.utc).date() <= LAST:
        raise ValueError('historical response misrepresented as original receipt')
    body = json.loads(raw)
    if set(body) != {'data'} or not isinstance(body['data'], list):
        raise ValueError('missing data or another page of source rows')
    rows = {}
    for row in body['data']:
        if set(row) != {'asset', 'time', 'CapMrktEstUSD', 'PriceUSD'} or row['asset'] != 'usdt':
            raise ValueError('wrong asset or fields')
        stamp = row['time']
        if not isinstance(stamp, str) or not stamp.endswith('T00:00:00.000000000Z'):
            raise ValueError('wrong UTC daily label')
        day = date.fromisoformat(stamp[:10])
        if day in rows:
            raise ValueError('duplicate source date')
        cap, price = _positive(row['CapMrktEstUSD']), _positive(row['PriceUSD'])
        rows[day] = (cap, price, cap / price)  # estimated circulating USDT, not chain supply
    expected = [FIRST + timedelta(days=i) for i in range((LAST - FIRST).days + 1)]
    if sorted(rows) != expected:
        raise ValueError('incomplete fixed daily series')
    return rows


def coingecko(raw):
    body = json.loads(raw, parse_float=D)
    prices = {}
    for stamp, value in body['prices']:
        if stamp % DAY_MS == 0:
            if stamp in prices:
                raise ValueError('duplicate comparison price date')
            prices[stamp] = value
    rows = {}
    for stamp, value in body['market_caps']:
        if stamp % DAY_MS:
            continue  # current intraday value is not a completed daily point
        if stamp not in prices:
            raise ValueError('unpaired CoinGecko price/cap')
        day = datetime.fromtimestamp(stamp / 1000, timezone.utc).date()
        if day in rows:
            raise ValueError('duplicate comparison date')
        cap, price = D(value), D(prices[stamp])
        if cap <= 0 or price <= 0:
            raise ValueError('invalid comparison number')
        rows[day] = (cap, price, cap / price)
    if sorted(rows) != [min(rows) + timedelta(days=i) for i in range(len(rows))]:
        raise ValueError('incomplete comparison daily grid')
    return rows


def _percent(values):
    ordered = sorted(values)
    return {'median': str(median(ordered) * 100),
            'p95_nearest_rank': str(ordered[(95 * len(ordered) + 99) // 100 - 1] * 100)}


def compare(cm, cg, starts):
    common = sorted(set(cm) & set(cg))
    if not common:
        raise ValueError('no common daily labels')
    deviations = {}
    for label, i in (('market_cap_usd', 0), ('price_usd', 1), ('estimated_units', 2)):
        deviations[label] = _percent([abs(cm[day][i] - cg[day][i]) / cg[day][i] for day in common])
    offsets = {}
    for shift in (-1, 0, 1):
        pairs = [(cm[day][0], cg[day + timedelta(days=shift)][0]) for day in common
                 if day + timedelta(days=shift) in cg]
        offsets[str(shift)] = {'pairs': len(pairs), 'median_abs_cap_gap_pct':
                               str(median(abs(a - b) / b for a, b in pairs) * 100)}
    direction = [day for day in common if day - timedelta(days=2) in cm and day - timedelta(days=2) in cg]
    discordant = sum((cm[day][0] > cm[day - timedelta(days=2)][0]) !=
                     (cg[day][0] > cg[day - timedelta(days=2)][0]) for day in direction)
    supply_discordant = sum((cm[day][2] > cm[day - timedelta(days=2)][2]) !=
                            (cg[day][2] > cg[day - timedelta(days=2)][2]) for day in direction)
    cm_cap_supply_discordant = sum((cm[day][0] > cm[day - timedelta(days=2)][0]) !=
                                    (cm[day][2] > cm[day - timedelta(days=2)][2]) for day in direction)
    return {'source_id': SOURCE_ID, 'historical_pit': False,
            'coinmetrics_daily_rows': len(cm), 'coingecko_completed_daily_rows': len(cg),
            'common_daily_labels': len(common), 'common_first': str(common[0]),
            'common_last': str(common[-1]), 'same_label_abs_gap_pct': deviations,
            'coinmetrics_cap_vs_coingecko_cap_label_shift_days': offsets,
            'two_day_cap_rise_direction_comparable_days': len(direction),
            'two_day_cap_rise_direction_disagreements': discordant,
            'two_day_estimated_units_direction_disagreements': supply_discordant,
            'coinmetrics_cap_vs_units_two_day_direction_disagreements': cm_cap_supply_discordant,
            'estimated_units_near_equal_days_1e_minus_10_relative':
                sum(abs(cm[day][2] - cg[day][2]) / cg[day][2] < D('1e-10') for day in common),
            'original_starts_in_coinmetrics_calendar': sum(FIRST <= day <= LAST for day in starts),
            'original_starts_in_comparison_calendar': sum(common[0] <= day <= common[-1] for day in starts),
            'original_starts_with_historical_first_receipt': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('coinmetrics_raw')
    parser.add_argument('coinmetrics_receipt')
    parser.add_argument('coingecko_raw')
    parser.add_argument('original_schedule')
    args = parser.parse_args()
    receipt = json.loads(Path(args.coinmetrics_receipt).read_text())
    cm = coinmetrics(Path(args.coinmetrics_raw).read_bytes(), receipt)
    cg = coingecko(Path(args.coingecko_raw).read_bytes())
    schedule = json.loads(Path(args.original_schedule).read_text())
    starts = schedule['primary']['starts_ms']
    if len(starts) != 795:
        raise ValueError('wrong original manual schedule')
    days = [datetime.fromtimestamp(ms / 1000, timezone.utc).date() for ms in starts]
    print(json.dumps(compare(cm, cg, days), sort_keys=True))


if __name__ == '__main__':
    main()
