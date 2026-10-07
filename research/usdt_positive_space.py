"""Read-only upper bound on positive USDT information at original manual starts.

Historical vendor downloads have no first-seen vintage. This emits aggregate
conditional counts only, not a signal, trade, account replay or private clock.
"""
import argparse
import csv
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal as D
import importlib.util
import json
from pathlib import Path
import zipfile

from coinquant.opportunities import FOUR_HOURS, Opportunities
from coinquant.dfii10 import eligible
from research.usdt_receipts import DAY, _points, asof


def daily_cap(path):
    with open(path, newline='', encoding='utf-8') as stream:
        return {int(datetime.strptime(row['date'], '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp() * 1000): D(row['market_cap'])
                for row in csv.DictReader(stream)}


def price_context(directory, starts):
    """Completed original UM four-hour bars; warmup cannot recover December 2019."""
    root = Path(directory)
    files = sorted(root.glob('BTCUSDT-4h-????-??.zip')) + sorted((root / 'daily').glob('BTCUSDT-4h-????-??-??.zip'))
    if len(files) != 99:
        raise ValueError('expected original 80 monthly and 19 September daily UM archives')
    model = Opportunities()
    closes = {}
    at_start = {}
    idx = 0
    last = None
    for archive in files:
        with zipfile.ZipFile(archive) as bundle:
            names = bundle.namelist()
            if len(names) != 1:
                raise ValueError('ambiguous bar archive')
            with bundle.open(names[0]) as source:
                rows = csv.reader((line.decode() for line in source))
                for row in rows:
                    if row[0] == 'open_time':
                        continue
                    end = int(row[0]) + FOUR_HOURS
                    if last is not None and end != last + FOUR_HOURS:
                        raise ValueError('incomplete UM four-hour clock')
                    while idx < len(starts) and starts[idx] < end:
                        start = starts[idx]
                        prior = closes.get(last - 3 * DAY) if last is not None else None
                        at_start[start] = dict(btc_three_day_up=bool(prior and closes[last] > prior),
                                               btc_three_day_known=prior is not None,
                                               raw_primary_long=bool(model.active and model.active.direction > 0)
                                               if last is not None and start >= 1578614400000 else None)
                        idx += 1
                    model.update(end, D(row[2]), D(row[3]), D(row[4]))
                    closes[end] = D(row[4])
                    last = end
    while idx < len(starts):
        start = starts[idx]
        prior = closes.get(last - 3 * DAY) if last is not None else None
        at_start[start] = dict(btc_three_day_up=bool(prior and closes[last] > prior),
                               btc_three_day_known=prior is not None,
                               raw_primary_long=bool(model.active and model.active.direction > 0)
                               if last is not None and start >= 1578614400000 else None)
        idx += 1
    return at_start


def macro_context(loader, archive_root, starts):
    spec = importlib.util.spec_from_file_location('original_dfii_history', loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    history = module.History(root=archive_root)
    return {start: eligible(history.snapshot(start), start) for start in starts}


def aggregate(values, starts, intervals, reports, price, macro, *, release_lag_days):
    """Positive three-point slope is a loose screen, not the external burst rule."""
    filled = {r['entry_session_start_ms']: r['kind'] for r in intervals}
    counts = Counter()
    unoccupied_days = set()
    for start, report in zip(starts, reports):
        day = start // DAY * DAY - release_lag_days * DAY
        if start < day + release_lag_days * DAY + 600_000:
            day -= DAY
        if not all(day - n * DAY in values for n in (0, 1, 2)):
            continue
        counts['conditional_source_covered_starts'] += 1
        held = any(r['first_ms'] < start < r['last_ms'] for r in intervals)
        counts['held_at_start' if held else 'flat_at_start'] += 1
        if values[day] <= values[day - 2 * DAY]:
            continue
        counts['positive_slope_starts'] += 1
        counts['positive_held' if held else 'positive_flat'] += 1
        ctx = price[start]
        if ctx['btc_three_day_known']:
            counts['positive_with_completed_perp_price'] += 1
        if not ctx['btc_three_day_up'] or not ctx['btc_three_day_known']:
            continue
        counts['positive_and_perp_three_day_up'] += 1
        counts['positive_trend_held' if held else 'positive_trend_flat'] += 1
        if held:
            continue
        if start in filled:
            counts['positive_trend_existing_first_fill_' + filled[start]] += 1
        if ctx['raw_primary_long'] is True:
            counts['positive_trend_raw_primary_long'] += 1
        elif ctx['raw_primary_long'] is False:
            counts['positive_trend_no_raw_primary'] += 1
            counts['positive_trend_no_raw_primary_macro_eligible' if macro[start]
                   else 'positive_trend_no_raw_primary_macro_ineligible'] += 1
            if not macro[start]:
                unoccupied_days.add(day)
                counts['unoccupied_development' if start < 1704067200000
                       else 'unoccupied_later'] += 1
                if report['status'] == 'no_action' and D(report['actual']['available_usdt']) > 0:
                    counts['unoccupied_terminal_available_positive'] += 1
        else:
            counts['positive_trend_raw_primary_unknown'] += 1
        if report['status'] == 'no_action' and float(report['actual']['available_usdt']) > 0:
            counts['positive_trend_flat_terminal_available_positive'] += 1
        if 'model_preview' in report:
            counts['positive_trend_flat_terminal_preview_' + report['model_preview']['action']] += 1
        else:
            counts['positive_trend_flat_terminal_preview_missing'] += 1
    counts['unoccupied_unique_source_days'] = len(unoccupied_days)
    return dict(sorted(counts.items()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('official_response')
    parser.add_argument('legacy_csv')
    parser.add_argument('schedule')
    parser.add_argument('first_fills')
    parser.add_argument('terminal_reports')
    parser.add_argument('original_um_four_hour_directory')
    parser.add_argument('private_receipt_ledger')
    parser.add_argument('original_dfii_history_loader')
    parser.add_argument('original_alfred_archive_root')
    args = parser.parse_args()
    schedule = json.loads(Path(args.schedule).read_text())
    starts = schedule['primary']['starts_ms']
    intervals = json.loads(Path(args.first_fills).read_text())
    reports = [json.loads(line) for line in open(args.terminal_reports, encoding='utf-8')]
    if len(starts) != 795 or len(reports) != 795 or len(intervals) != 50 or [r['start_ms'] for r in reports] != starts:
        raise ValueError('original session/first-fill identity mismatch')
    price = price_context(args.original_um_four_hour_directory, starts)
    macro = macro_context(args.original_dfii_history_loader, args.original_alfred_archive_root, starts)
    source = Path(args.official_response)
    official = {p['event_ms']: D(p['market_cap_usd']) for p in _points(source.read_bytes(), source.stat().st_mtime_ns // 1_000_000)
                if p['event_ms'] < 1789862400000}  # original manual schedule ends 2026-09-20
    legacy = {day: cap for day, cap in daily_cap(args.legacy_csv).items()
              if day <= 1776988800000 and day < min(official)}
    first_seen = sum(bool(asof(args.private_receipt_ledger, start)) for start in starts)
    print(json.dumps(dict(original_starts=len(starts), original_first_fills=len(intervals),
                          original_starts_with_direct_first_seen_source=first_seen,
                          official_conditional=aggregate(official, starts, intervals, reports, price, macro, release_lag_days=0),
                          legacy_conditional_one_day_late=aggregate(legacy, starts, intervals, reports, price, macro, release_lag_days=1)),
                     sort_keys=True))


if __name__ == '__main__':
    main()
