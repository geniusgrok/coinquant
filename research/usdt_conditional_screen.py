"""Source/action-space counts only. Historical joins are NOT point-in-time.

Inputs are existing local original manual schedule and first-fill attribution.
No account wallet, order change, network request or exact timeline output.
"""
import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path

from research.usdt_receipts import DAY, _points


def negative_events(values):
    dates = sorted(values)
    out = set()
    for i in range(3, len(dates)):
        day = dates[i]
        if dates[i-3:i+1] != [day-3*DAY, day-2*DAY, day-DAY, day]:
            continue
        a, b, c, d = (values[date] for date in dates[i-3:i+1])
        if d < b and c >= a:
            out.add(day)
    return out


def count(events, starts, macro_starts):
    matched = {(day, start) for day in events for start in starts if day + 600_000 <= start < day + DAY}
    return dict(events=len(events), event_days_with_manual_start=len({day for day, _ in matched}),
                matched_manual_starts=len(matched), macro_first_fills=sum(start in macro_starts for _, start in matched))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_response', help='local official CoinGecko JSON, fetched now')
    parser.add_argument('reference_csv', help='unqualified public historical CSV; conditional only')
    parser.add_argument('schedule', help='original local frozen manual schedule')
    parser.add_argument('first_fills', help='original local verified 50-interval attribution')
    args = parser.parse_args()
    schedule = json.loads(Path(args.schedule).read_text())
    starts = schedule['primary']['starts_ms']
    if len(starts) != 795 or schedule['primary']['count'] != 795:
        raise ValueError('wrong original manual schedule')
    intervals = json.loads(Path(args.first_fills).read_text())
    if len(intervals) != 50:
        raise ValueError('wrong original first-fill cohort')
    macro = {r['entry_session_start_ms'] for r in intervals if r['kind'] == 'macro'}
    source = Path(args.source_response)
    points = _points(source.read_bytes(), source.stat().st_mtime_ns // 1_000_000)
    original_end = 1789862400000
    official = {p['event_ms']: Decimal(p['market_cap_usd']) for p in points if p['event_ms'] < original_end}
    recent = count(negative_events(official), starts, macro)
    recent.update(source='official_current_backfill', historical_pit=False,
                  macro_first_fills_in_covered_era=sum(min(official) <= t < original_end for t in macro))
    old = {}
    with open(args.reference_csv, newline='', encoding='utf-8') as stream:
        for row in csv.DictReader(stream):
            day = int(datetime.strptime(row['date'], '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp() * 1000)
            if day <= 1776988800000:  # 2026-04-24: reference's legacy downloader seam
                old[day] = Decimal(row['market_cap'])
    legacy = count(negative_events(old), starts, macro)
    legacy.update(source='reference_legacy_intraday_mean_csv', historical_pit=False,
                  macro_first_fills_in_covered_era=sum(min(old) <= t <= max(old) for t in macro),
                  usdt_price_control_present=False)
    print(json.dumps(dict(official=recent, legacy=legacy), sort_keys=True))


if __name__ == '__main__':
    main()
