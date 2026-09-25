"""Verify ALFRED sparse vintage originals and reconstruct call-time DFII10 snapshots."""
import csv
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from io import TextIOWrapper
import json
from pathlib import Path
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
from zipfile import ZipFile

from coinquant.research import invocations, iso, spec, timestamp

EASTERN = ZoneInfo('America/New_York')
COMMON = [('form[units]', 'lin'), ('form[obs_start_date]', '2019-01-01'),
          ('form[obs_end_date]', '2026-09-19'), ('form[entered_vintage_dates]', ''),
          ('form[file_type]', '3'), ('form[file_format]', 'csv'),
          ('form[download_data]', 'Download data')]


def available(vintage):
    # No intraday ALFRED publication timestamp is asserted. Delay the *end*
    # of its US Eastern vintage date by 48 elapsed hours before any UTC call.
    local_end = datetime.combine(vintage, time.max, EASTERN)
    utc_available = local_end.astimezone(timezone.utc) + timedelta(hours=48)
    return int(utc_available.timestamp() * 1000)


def load(root):
    root = Path(root)
    receipt = json.loads((root/'RECEIPT.json').read_text())
    assert receipt['observation_start'] == '2019-01-01'
    assert receipt['observation_end'] == '2026-09-19'
    updates = {}
    selected_dates = []
    counts = {'vintage_dates': 0, 'updates': 0, 'revisions': 0}
    for attempt in receipt['attempts']:
        if attempt['label'] == 'single':
            continue  # acquisition probe duplicates an included batch vintage
        path = root/attempt['path']
        raw = path.read_bytes()
        assert len(raw) == attempt['response_bytes']
        assert sha256(raw).hexdigest() == attempt['response_sha256']
        assert attempt['http_status'] == 200 and attempt['content_type'] == 'application/zip'
        with ZipFile(path) as archive:
            assert archive.namelist() == attempt['members']
            names = [n for n in archive.namelist() if n.endswith('.csv')]
            assert len(names) == 1
            with archive.open(names[0]) as stream:
                reader = csv.reader(TextIOWrapper(stream, encoding='utf-8-sig', newline=''))
                header = next(reader)
                assert header[0] == 'observation_date'
                dates = [datetime.strptime(name, 'DFII10_%Y%m%d').date() for name in header[1:]]
                assert dates == sorted(set(dates))
                assert len(dates) == attempt['selected_count']
                selected_dates.extend(dates)
                batch = {v: [] for v in dates}
                for row in reader:
                    assert len(row) == len(header)
                    observation = datetime.strptime(row[0], '%Y-%m-%d').date()
                    for vintage, value in zip(dates, row[1:]):
                        if value:
                            assert observation <= vintage
                            number = Decimal(value)
                            assert number.is_finite()
                            batch[vintage].append((observation, number))
                            counts['updates'] += 1
                for vintage in dates:
                    assert vintage not in updates
                    updates[vintage] = batch[vintage]
        body = urlencode(COMMON + [('form[selected_vintage_dates][]', str(v)) for v in dates]).encode()
        assert len(body) == attempt['request_bytes']
        assert sha256(body).hexdigest() == attempt['request_sha256']
    assert selected_dates == sorted(set(selected_dates))
    assert len(selected_dates) == receipt['vintages']['count'] == 1914
    assert [str(selected_dates[0]), str(selected_dates[-1])] == [receipt['vintages']['first'], receipt['vintages']['last']]
    assert sha256(' '.join(map(str, selected_dates)).encode()).hexdigest() == receipt['vintages']['sha256']
    assert counts['updates'] == 1929
    counts['vintage_dates'] = len(selected_dates)
    return updates, counts


def snapshots(root, full=False, absence=False):
    if absence and not full:
        raise ValueError('frozen absence is a formal-period stress only')
    updates, counts = load(root)
    dates = sorted(updates)
    calls = [t for t in invocations(spec(),stress=absence)
             if t < timestamp(spec()['end' if full else 'development_end'])]
    current = {}
    index = 0
    rows = []
    for call in calls:
        asof = None
        while index < len(dates) and available(dates[index]) < call:
            vintage = dates[index]
            for observation, value in updates[vintage]:
                if observation in current:
                    counts['revisions'] += 1
                current[observation] = (value, vintage)
            asof = vintage
            index += 1
        observations = sorted(current)
        latest = observations[-1] if observations else None
        latest_value, latest_vintage = current[latest] if latest else (None, None)
        prior20 = observations[-21] if len(observations) >= 21 else None
        prior_value, prior_vintage = current[prior20] if prior20 else (None, None)
        call_date = datetime.fromtimestamp(call/1000, timezone.utc).date()
        reason = ('no_historical_vintage' if latest is None else
                  'insufficient_20_prior_observations' if prior20 is None else
                  'stale_observation_over_7_calendar_days' if (call_date-latest).days > 7 else None)
        rows.append(dict(call_time_ms=call, call_utc=iso(call),
                         asof_vintage_date=str(dates[index-1]) if index else None,
                         latest_observation_date=str(latest) if latest else None,
                         latest_value=str(latest_value) if latest else None,
                         latest_value_vintage_date=str(latest_vintage) if latest else None,
                         latest_value_available_utc=iso(available(latest_vintage)) if latest else None,
                         prior20_observation_date=str(prior20) if prior20 else None,
                         prior20_value=str(prior_value) if prior20 else None,
                         prior20_value_vintage_date=str(prior_vintage) if prior20 else None,
                         prior20_value_available_utc=iso(available(prior_vintage)) if prior20 else None,
                         missing_reason=reason))
    return rows, counts


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--full', action='store_true')
    parser.add_argument('--absence', action='store_true')
    args = parser.parse_args()
    rows, counts = snapshots(args.root, args.full, args.absence)
    args.output.write_text(json.dumps(dict(counts=counts, calls=rows), indent=2)+'\n')
    print(json.dumps(dict(counts=counts, call_count=len(rows), missing=sum(bool(r['missing_reason']) for r in rows))))
