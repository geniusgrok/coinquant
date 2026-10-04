"""Finite manual BTC public evidence capture, separate from account diaries.

No daemon, trading adapter, private authentication or historical backfill.
Receiving a revised historical page today does not prove past availability.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def urls(day):
    start = int(datetime.combine(day, datetime.min.time(), timezone.utc).timestamp()*1000)
    return [('btc-oi', f'https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-{day.isoformat()}.zip'),
            ('btc-option-dvol', f'https://www.deribit.com/api/v2/public/get_volatility_index_data?currency=BTC&start_timestamp={start}&end_timestamp={start+86400000}&resolution=3600'),
            ('btc-etf-flow', 'https://farside.co.uk/btc/')]


def capture_one(item, directory):
    name, url = item
    began = time.monotonic()
    record = dict(name=name, url=url, request_utc=datetime.now(timezone.utc).isoformat(),
                  status=None, historical_publication_vintage_proven=False)
    raw = None
    try:
        with urlopen(Request(url, headers={'User-Agent':'BTC-research-public-qualification/1.0'}), timeout=5) as response:
            raw = response.read(524289)
            record.update(status=response.status, content_type=response.headers.get('Content-Type'))
        if len(raw) > 524288:
            raw = None
            raise ValueError('response exceeds512KiB bound')
    except HTTPError as exc:
        raw = exc.read(8192)
        record.update(status=exc.code, error='HTTPError')
    except Exception as exc:
        record.update(error=type(exc).__name__, detail=str(exc)[:180])
    if raw is not None:
        filename = name+'.bin'
        (directory/filename).write_bytes(raw)
        record.update(raw_file=filename, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    record.update(received_utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.monotonic()-began,
                  qualification='UNQUALIFIED_RESEARCH_RECEIPT')
    return record


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--date', type=date.fromisoformat,
                   default=datetime.now(timezone.utc).date()-timedelta(days=1))
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args(argv)
    if args.date >= datetime.now(timezone.utc).date() or args.out.exists():
        raise ValueError('choose a completed UTC day and a new evidence directory')
    args.out.mkdir(parents=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(lambda item: capture_one(item, args.out), urls(args.date)))
    (args.out/'receipts.json').write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps([dict(name=r['name'], status=r['status'], qualification=r['qualification']) for r in records]))


if __name__ == '__main__':
    main()
