"""Bounded PUBLIC-only Bybit history/coverage probe. Never uses account credentials."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

START = 1577836800000  # 2020-01-01T00:00:00Z
END_LAST_MINUTE = 1789862340000  # 2026-09-19T23:59:00Z
END_LAST_MS = 1789862399999


def endpoints():
    values = {
        'trading-directory.html': 'https://public.bybit.com/trading/BTCUSD/',
        'spot-index-directory.html': 'https://public.bybit.com/spot_index/BTCUSD/',
        'premium-index-directory.html': 'https://public.bybit.com/premium_index/BTCUSD/',
    }
    hosts = {
        'global': 'api.bybit.com',
        'bytick': 'api.bytick.com',
        'manepa': 'api.manepa.jp',
    }
    for label, host in hosts.items():
        base = f'https://{host}/v5/'
        values[f'{label}-instrument.json'] = (
            base + 'market/instruments-info?category=inverse&symbol=BTCUSD'
        )
        values[f'{label}-start-mark.json'] = (
            base + f'market/mark-price-kline?category=inverse&symbol=BTCUSD&interval=1'
            f'&start={START}&end={START + 119999}&limit=2'
        )
        values[f'{label}-start-funding.json'] = (
            base + f'market/funding/history?category=inverse&symbol=BTCUSD'
            f'&startTime={START}&endTime={START + 86399999}&limit=10'
        )
        values[f'{label}-end-mark.json'] = (
            base + f'market/mark-price-kline?category=inverse&symbol=BTCUSD&interval=1'
            f'&start={END_LAST_MINUTE}&end={END_LAST_MS}&limit=2'
        )
        values[f'{label}-end-funding.json'] = (
            base + f'market/funding/history?category=inverse&symbol=BTCUSD'
            f'&startTime={END_LAST_MINUTE - 86400000}&endTime={END_LAST_MS}&limit=10'
        )
    return values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=True)

    results = []
    deadline = time.monotonic() + 60
    for name, url in endpoints().items():
        row = {'file': name, 'source': url}
        temporary = root / (name + '.partial')
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('public probe deadline')
            request = Request(url, headers={'User-Agent': 'pancakequant-public-research'})
            with urlopen(request, timeout=min(5, max(.1, remaining))) as response, temporary.open('wb') as stream:
                count, digest = 0, hashlib.sha256()
                while True:
                    block = response.read(65536)
                    if not block:
                        break
                    if time.monotonic() >= deadline or count + len(block) > 5_000_000:
                        raise TimeoutError('probe size or deadline bound')
                    stream.write(block)
                    digest.update(block)
                    count += len(block)
            final = root / name
            temporary.replace(final)
            row.update(status='downloaded', bytes=count, sha256=digest.hexdigest())

            if name.endswith('.json'):
                document = json.loads(final.read_text(encoding='utf-8'))
                result = document.get('result')
                if not isinstance(result, dict):
                    raise ValueError('V5 result object is missing')
                rows = result.get('list')
                row['retCode'] = document.get('retCode')
                row['exchange_time'] = document.get('time')
                row['rows'] = len(rows) if isinstance(rows, list) else None
                if name.endswith('-instrument.json') and isinstance(rows, list) and rows:
                    row['launchTime'] = rows[0].get('launchTime')
                    row['fundingInterval'] = rows[0].get('fundingInterval')
                    row['instrument_status'] = rows[0].get('status')
            else:
                listing = final.read_text(encoding='utf-8')
                patterns = {
                    'trading-directory.html': r'BTCUSD(\d{4}-\d{2}-\d{2})\.csv\.gz',
                    'spot-index-directory.html': r'BTCUSD(\d{4}-\d{2}-\d{2})_index_price\.csv\.gz',
                    'premium-index-directory.html': r'BTCUSD(\d{4}-\d{2}-\d{2})_premium_index\.csv\.gz',
                }
                dates = sorted(set(re.findall(patterns[name], listing)))
                if not dates:
                    raise ValueError('archive directory contains no recognized BTCUSD dates')
                row.update(first_date=dates[0], latest_date=dates[-1], dated_files=len(dates))
        except (HTTPError, URLError, OSError, ValueError, TimeoutError) as exc:
            row.update(status='unavailable', error_type=type(exc).__name__,
                       http_status=getattr(exc, 'code', None))
            temporary.unlink(missing_ok=True)
        results.append(row)

    coverage = {
        row['file']: {key: row[key] for key in ('first_date', 'latest_date', 'dated_files')
                      if key in row}
        for row in results if row['file'].endswith('-directory.html')
    }
    report = {
        'purpose': 'PUBLIC coverage/access probe only; never economic qualification',
        'window': {'start': '2020-01-01T00:00:00Z', 'end': '2026-09-20T00:00:00Z'},
        'archive_coverage': coverage,
        'requests': results,
    }
    (root / 'probe.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
