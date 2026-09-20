"""Bounded PUBLIC-only contract/schema probe. Never uses account credentials."""
import argparse
import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=True)
    base = 'https://api.bybit.com/v5/'
    # Frozen research window: 2020-01-01T00:00:00Z .. 2026-09-20T00:00:00Z.
    start = 1577836800000
    end_last_minute = 1789862280000  # 2026-09-19T23:58:00Z
    end_last_ms = 1789862399999      # 2026-09-19T23:59:59.999Z
    endpoints = {
        'instrument.json': base + 'market/instruments-info?category=inverse&symbol=BTCUSD',
        'risk.json': base + 'market/risk-limit?category=inverse&symbol=BTCUSD',
        'start-kline.json': base + f'market/kline?category=inverse&symbol=BTCUSD&interval=1&start={start}&end={start + 119999}&limit=2',
        'start-mark.json': base + f'market/mark-price-kline?category=inverse&symbol=BTCUSD&interval=1&start={start}&end={start + 119999}&limit=2',
        'start-funding.json': base + f'market/funding/history?category=inverse&symbol=BTCUSD&startTime={start}&endTime={start + 86399999}&limit=10',
        'end-kline.json': base + f'market/kline?category=inverse&symbol=BTCUSD&interval=1&start={end_last_minute}&end={end_last_ms}&limit=2',
        'end-mark.json': base + f'market/mark-price-kline?category=inverse&symbol=BTCUSD&interval=1&start={end_last_minute}&end={end_last_ms}&limit=2',
        'end-funding.json': base + f'market/funding/history?category=inverse&symbol=BTCUSD&startTime={end_last_minute - 86400000}&endTime={end_last_ms}&limit=10',
        'BTCUSD2020-01-01.csv.gz': 'https://public.bybit.com/trading/BTCUSD/BTCUSD2020-01-01.csv.gz',
        'BTCUSD2020-01-01_index_price.csv.gz': 'https://public.bybit.com/spot_index/BTCUSD/BTCUSD2020-01-01_index_price.csv.gz',
        'BTCUSD2020-01-01_premium_index.csv.gz': 'https://public.bybit.com/premium_index/BTCUSD/BTCUSD2020-01-01_premium_index.csv.gz',
        'BTCUSD2026-09-19.csv.gz': 'https://public.bybit.com/trading/BTCUSD/BTCUSD2026-09-19.csv.gz',
        'BTCUSD2026-09-19_index_price.csv.gz': 'https://public.bybit.com/spot_index/BTCUSD/BTCUSD2026-09-19_index_price.csv.gz',
        'BTCUSD2026-09-19_premium_index.csv.gz': 'https://public.bybit.com/premium_index/BTCUSD/BTCUSD2026-09-19_premium_index.csv.gz',
        'candidate-kline-start.csv.gz': 'https://public.bybit.com/kline/BTCUSD/2020-01-01/1min.csv.gz',
        'candidate-kline-end.csv.gz': 'https://public.bybit.com/kline/BTCUSD/2026-09-19/1min.csv.gz',
        'candidate-price-quote-start.csv.gz': 'https://public.bybit.com/price_quote/BTCUSD/2020-01-01/1min.csv.gz',
        'candidate-price-quote-end.csv.gz': 'https://public.bybit.com/price_quote/BTCUSD/2026-09-19/1min.csv.gz',
        'candidate-premium-quote-start.csv.gz': 'https://public.bybit.com/premium_quote/BTCUSD/2020-01-01/1min.csv.gz',
        'candidate-premium-quote-end.csv.gz': 'https://public.bybit.com/premium_quote/BTCUSD/2026-09-19/1min.csv.gz',
    }
    results = []
    deadline = time.monotonic() + 90
    for name, url in endpoints.items():
        row = dict(file=name, source=url)
        temporary = root / (name + '.partial')
        try:
            if time.monotonic() >= deadline:
                raise TimeoutError('public probe deadline')
            request = Request(url, headers={'User-Agent': 'pancakequant-public-research'})
            with urlopen(request, timeout=min(10, max(.1, deadline - time.monotonic()))) as response, open(temporary, 'wb') as stream:
                count, h = 0, hashlib.sha256()
                for block in iter(lambda: response.read(65536), b''):
                    if time.monotonic() >= deadline or count + len(block) > 10_000_000:
                        raise TimeoutError('probe size or deadline bound')
                    stream.write(block)
                    h.update(block)
                    count += len(block)
            temporary.replace(root / name)
            row.update(status='downloaded', bytes=count, sha256=h.hexdigest())
            if name.endswith('.json'):
                document = json.loads((root / name).read_text())
                result = document.get('result', {})
                rows = result.get('list', [])
                row['retCode'] = document.get('retCode')
                row['exchange_time'] = document.get('time')
                row['rows'] = len(rows)
                if name == 'instrument.json' and rows:
                    row['launchTime'] = rows[0].get('launchTime')
                    row['fundingInterval'] = rows[0].get('fundingInterval')
                    row['status'] = rows[0].get('status')
                elif name == 'risk.json' and rows:
                    row['risk_tiers'] = len(rows)
        except (HTTPError, URLError, OSError, ValueError, TimeoutError) as exc:
            row.update(status='unavailable', error_type=type(exc).__name__,
                       http_status=getattr(exc, 'code', None))
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
        results.append(row)
    report = {
        'purpose': 'PUBLIC schema/coverage probe, not economic validation',
        'window': {'start': '2020-01-01T00:00:00Z', 'end': '2026-09-20T00:00:00Z'},
        'requests': results,
    }
    (root / 'probe.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
