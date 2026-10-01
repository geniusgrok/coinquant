"""Restore exact original minute archives needed by the existing M10 account."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.request

from research.rebuild import ROOT


def restore(root):
    manifest = json.loads((ROOT / 'evidence/remeasure-20260929-m10/M10-r75.json').read_text())
    files = manifest['market_identity']['loaded_minute_files']
    def one(item):
        name, expected = item
        path = root / name
        if path.exists():
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError('existing immutable input differs: ' + name)
            return None
        parts = name.split('/')
        category = 'klines' if parts[0] == 'klines' else 'markPriceKlines'
        period = 'daily' if 'daily' in parts else 'monthly'
        url = f'https://data.binance.vision/data/futures/um/{period}/{category}/BTCUSDT/1m/{parts[-1]}'
        with urllib.request.urlopen(url + '.CHECKSUM', timeout=30) as response:
            checksum = response.read()
        if checksum.decode().split()[0] != expected:
            raise ValueError('official checksum differs from frozen original: ' + name)
        with urllib.request.urlopen(url, timeout=60) as response:
            raw = response.read()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('restored input digest differs: ' + name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
        Path(str(path) + '.CHECKSUM').write_bytes(checksum)
        return name
    with ThreadPoolExecutor(max_workers=8) as pool:
        restored = [name for name in pool.map(one, files.items()) if name]
    return {'restored': restored, 'frozen_files_verified': len(files),
            'manifest_sha256': hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--market', type=Path, default=Path('/tmp/coinquant-market'))
    args = parser.parse_args()
    print(json.dumps(restore(args.market), indent=2))
