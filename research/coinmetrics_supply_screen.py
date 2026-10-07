"""Frozen, source-specific support screen at original manual starts.

No future market bar, return, fee, funding or wallet is read by this stage.
Raw source rows and private start times never appear in stdout.
"""
import argparse
from collections import deque
import csv
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal as D
import importlib.util
import json
from pathlib import Path
import zipfile

from coinquant.dfii10 import eligible
from coinquant.opportunities import FOUR_HOURS, Opportunities
from research.coinmetrics_source_check import coinmetrics


DAY = 86_400_000
SEVEN_DAYS = 7 * DAY
WARMUP_DONE = 1578614400000  # January 10; December 2019 four-hour bars not retained
LATER_PERIOD = 1704067200000  # 2024-01-01


def completed_price(directory, starts):
    root = Path(directory)
    files = sorted(root.glob('BTCUSDT-4h-????-??.zip')) + sorted((root / 'daily').glob('BTCUSDT-4h-????-??-??.zip'))
    if len(files) != 99:
        raise ValueError('wrong original UM archive count')
    model = Opportunities()
    closes = {}
    daily21 = deque(maxlen=21)
    context = {}
    index, last = 0, None
    for archive in files:
        with zipfile.ZipFile(archive) as bundle:
            if len(bundle.namelist()) != 1:
                raise ValueError('ambiguous four-hour archive')
            with bundle.open(bundle.namelist()[0]) as stream:
                for row in csv.reader(line.decode() for line in stream):
                    if row[0] == 'open_time':
                        continue
                    end = int(row[0]) + FOUR_HOURS
                    if last is not None and end != last + FOUR_HOURS:
                        raise ValueError('incomplete four-hour futures clock')
                    while index < len(starts) and starts[index] < end:
                        start = starts[index]
                        prior = closes.get(last - 3 * DAY) if last is not None else None
                        context[start] = dict(raw_primary_long=(bool(model.active and model.active.direction > 0)
                                                                 if start >= WARMUP_DONE else None),
                                              btc_3d_return=(closes[last] / prior - 1
                                                             if prior is not None else None),
                                              btc_20d_rms=((sum(((daily21[i][1] / daily21[i-1][1] - 1) ** 2
                                                                  for i in range(1, 21)), D(0)) / 20).sqrt()
                                                           if len(daily21) == 21 else None))
                        index += 1
                    model.update(end, D(row[2]), D(row[3]), D(row[4]))
                    closes[end], last = D(row[4]), end
                    if end % DAY == 0:
                        daily21.append((end, closes[end]))
    if index != len(starts):
        raise ValueError('original start lacks completed future bar')
    return context, closes


def original_macro(loader, archive_root, starts):
    spec = importlib.util.spec_from_file_location('original_dfii_history', loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    history = module.History(root=archive_root)
    return {start: eligible(history.snapshot(start), start) for start in starts}


def candidates(cm, starts, reports, intervals, price, macro):
    """One first real start per source day, exactly 72 hours after its label."""
    first_start = {}
    for start in starts:
        label = datetime.fromtimestamp(start / 1000, timezone.utc).date() - timedelta(days=3)
        first_start.setdefault(label, start)
    q = {day: values[2] for day, values in cm.items()}
    event_days = {day for day in q if all(day - timedelta(days=n) in q for n in (1, 2, 3))
                  and q[day] > q[day - timedelta(days=2)]
                  and q[day - timedelta(days=1)] <= q[day - timedelta(days=3)]}
    reports_by_start = {report['start_ms']: report for report in reports}
    events, controls = [], []
    counts = {'source_event_dates': len(event_days), 'source_event_dates_with_manual_start': len(event_days & first_start.keys()),
              'manual_source_dates': len(first_start), 'flat_source_event_starts': 0,
              'event_starts_with_positive_completed_btc_3d': 0,
              'event_starts_no_incumbent': 0}
    for day, start in sorted(first_start.items()):
        if day not in q or any(day - timedelta(days=n) not in q for n in (1, 2, 3)):
            continue
        held = any(r['first_ms'] < start < r['last_ms'] for r in intervals)
        event = day in event_days
        if event and not held:
            counts['flat_source_event_starts'] += 1
        context = price[start]
        if (context['btc_3d_return'] is None or context['btc_3d_return'] <= 0 or
                context['btc_20d_rms'] is None):
            continue
        if event:
            counts['event_starts_with_positive_completed_btc_3d'] += 1
        if held or context['raw_primary_long'] is not False or macro[start]:
            continue
        report = reports_by_start[start]
        if event:
            counts['event_starts_no_incumbent'] += 1
        item = dict(start=start, source_day=day, btc_3d_return=context['btc_3d_return'],
                    btc_20d_rms=context['btc_20d_rms'],
                    source_price=cm[day][1], terminal_available_positive=D(report['actual']['available_usdt']) > 0,
                    cleanup_verified=report['cleanup'] == 'verified', terminal_status=report['status'])
        (events if event else controls).append(item)
    retained = []
    for item in events:
        if not retained or item['start'] - retained[-1]['start'] >= SEVEN_DAYS:
            retained.append(item)
    period = lambda item: 'development' if item['start'] < LATER_PERIOD else 'later'
    counts.update(eligible_events=len(events), eligible_non_event_controls=len(controls),
                  nonoverlapping_events=len(retained),
                  nonoverlapping_development=sum(period(x) == 'development' for x in retained),
                  nonoverlapping_later=sum(period(x) == 'later' for x in retained),
                  retained_with_positive_terminal_available=sum(x['terminal_available_positive'] for x in retained),
                  retained_with_verified_cleanup=sum(x['cleanup_verified'] for x in retained),
                  retained_terminal_no_action=sum(x['terminal_status'] == 'no_action' for x in retained),
                  retained_with_same_year_control=sum(any(y['source_day'].year == x['source_day'].year and
                                                          abs(y['start'] - x['start']) >= SEVEN_DAYS
                                                          for y in controls) for x in retained))
    pairs = match_events(retained, controls)
    counts['matched_pairs_before_outcomes'] = len(pairs)
    counts['support_gate_pass'] = (counts['nonoverlapping_events'] >= 10 and
                                   counts['nonoverlapping_development'] >= 3 and
                                   counts['nonoverlapping_later'] >= 3 and
                                   len(pairs) == len(retained))
    return counts, retained, controls, pairs


def match_events(events, controls):
    """Deterministic same-year matching on ranks of pre-start facts only."""
    names = ('btc_3d_return', 'btc_20d_rms', 'source_price')
    ranks = {}
    for year in {item['source_day'].year for item in events}:
        cohort = [item for item in events + controls if item['source_day'].year == year]
        values = {name: sorted({item[name] - (1 if name == 'source_price' else 0)
                                for item in cohort}) for name in names}
        for item in cohort:
            ranks[item['start']] = tuple(D(values[name].index(item[name] - (1 if name == 'source_price' else 0))) /
                                         max(1, len(values[name]) - 1) for name in names)
    pairs, used = [], []
    for event in events:
        eligible_controls = [item for item in controls if item['source_day'].year == event['source_day'].year
                             and all(abs(item['start'] - other['start']) >= SEVEN_DAYS
                                     for other in events + used)]
        if not eligible_controls:
            continue
        control = min(eligible_controls, key=lambda item: (
            sum(abs(a - b) for a, b in zip(ranks[event['start']], ranks[item['start']])), item['start']))
        used.append(control)
        pairs.append((event, control))
    return pairs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('coinmetrics_raw')
    parser.add_argument('coinmetrics_receipt')
    parser.add_argument('original_schedule')
    parser.add_argument('verified_first_fills')
    parser.add_argument('terminal_reports')
    parser.add_argument('original_um_four_hour_directory')
    parser.add_argument('original_dfii_history_loader')
    parser.add_argument('original_alfred_archive_root')
    args = parser.parse_args()
    raw = Path(args.coinmetrics_raw).read_bytes()
    receipt = json.loads(Path(args.coinmetrics_receipt).read_text())
    cm = coinmetrics(raw, receipt)
    starts = json.loads(Path(args.original_schedule).read_text())['primary']['starts_ms']
    intervals = json.loads(Path(args.verified_first_fills).read_text())
    reports = [json.loads(line) for line in open(args.terminal_reports, encoding='utf-8')]
    if len(starts) != 795 or len(intervals) != 50 or [r['start_ms'] for r in reports] != starts:
        raise ValueError('wrong original path identity')
    price, _ = completed_price(args.original_um_four_hour_directory, starts)
    macro = original_macro(args.original_dfii_history_loader, args.original_alfred_archive_root, starts)
    result, _, _, _ = candidates(cm, starts, reports, intervals, price, macro)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
