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
    root = Path(args.output); root.mkdir(parents=True, exist_ok=True)
    base = 'https://api.bybit.com/v5/'
    endpoints = {
        'instrument.json': base + 'market/instruments-info?category=inverse&symbol=BTCUSD',
        'risk.json': base + 'market/risk-limit?category=inverse&symbol=BTCUSD',
        'start-kline.json': base + 'market/kline?category=inverse&symbol=BTCUSD&interval=1&start=1577836800000&end=1577836919999&limit=2',
        'end-mark.json': base + 'market/mark-price-kline?category=inverse&symbol=BTCUSD&interval=1&start=1789862280000&end=1789862399999&limit=2',
        'start-funding.json': base + 'market/funding/history?category=inverse&symbol=BTCUSD&startTime=1577836800000&endTime=1577923199999&limit=10',
        'BTCUSD2020-01-01.csv.gz': 'https://public.bybit.com/trading/BTCUSD/BTCUSD2020-01-01.csv.gz',
    }
    results = []
    deadline = time.monotonic() + 60
    for name, url in endpoints.items():
        row = dict(file=name, source=url)
        temporary = root / (name + '.partial')
        try:
            if time.monotonic() >= deadline:
                raise TimeoutError('public probe deadline')
            request = Request(url, headers={'User-Agent': 'pancakequant-public-research'})
            with urlopen(request, timeout=min(8, max(.1, deadline - time.monotonic()))) as response, open(temporary, 'wb') as stream:
                count, h = 0, hashlib.sha256()
                for block in iter(lambda: response.read(65536), b''):
                    if time.monotonic() >= deadline or count + len(block) > 10_000_000:
                        raise TimeoutError('probe size or deadline bound')
                    stream.write(block); h.update(block); count += len(block)
            temporary.replace(root / name)
            row.update(status='downloaded', bytes=count, sha256=h.hexdigest())
            if name.endswith('.json'):
                document = json.loads((root / name).read_text())
                row['retCode'] = document.get('retCode')
                row['exchange_time'] = document.get('time')
                row['rows'] = len(document.get('result', {}).get('list', []))
        except (HTTPError, URLError, OSError, ValueError) as exc:
            row.update(status='unavailable', error_type=type(exc).__name__, http_status=getattr(exc, 'code', None))
        results.append(row)
    report = {'purpose': 'PUBLIC schema/coverage probe, not economic validation', 'requests': results}
    (root / 'probe.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
