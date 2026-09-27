"""Dense minute arrays built from the checksum-verified vision set.

Screening only. Arrays are a cache of the official zips; the cache key binds
every source file digest. Missing minutes stay NaN and are never filled.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

from research.session_market import _checksum, _read_zip_rows, load_base

START = int(datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
END = int(datetime(2026, 9, 20, tzinfo=timezone.utc).timestamp() * 1000)
MINUTE = 60_000
COUNT = (END - START) // MINUTE


def _sources(root, kind):
    folder = Path(root) / ('klines' if kind == 'trade' else 'mark') / '1m'
    return sorted(folder.glob('BTCUSDT-1m-*.zip')) + sorted((folder / 'daily').glob('BTCUSDT-1m-*.zip'))


def build(root, cache):
    root, cache = Path(root), Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    identity = {}
    for kind in ('trade', 'mark'):
        paths = _sources(root, kind)
        identity[kind] = [(str(p.relative_to(root)), _checksum(p)) for p in paths]
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    manifest = cache / 'MANIFEST.json'
    if manifest.exists() and json.loads(manifest.read_text()).get('key') == key:
        return key
    for kind, columns in (('trade', 5), ('mark', 4)):
        data = np.full((COUNT, columns), np.nan)
        for path in _sources(root, kind):
            for row in _read_zip_rows(path):
                index = (int(row[0]) - START) // MINUTE
                if 0 <= index < COUNT:
                    data[index] = [float(v) for v in row[1:1 + columns]]
        np.save(cache / f'{kind}.npy', data)
    market = load_base(root)
    h4 = sorted(market.h4.items())
    np.save(cache / 'h4.npy', np.array([[t] + [float(v) for v in values] for t, values in h4]))
    np.save(cache / 'funding.npy', np.array([[t, float(r)] for t, r in market.funding]))
    manifest.write_text(json.dumps({'key': key, 'start': START, 'end': END, 'minutes': COUNT,
                                    'sources': identity}) + '\n')
    return key


def load(cache):
    cache = Path(cache)
    return {name: np.load(cache / f'{name}.npy') for name in ('trade', 'mark', 'h4', 'funding')}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='/data/coinquant-market')
    parser.add_argument('--cache', default='/data/coinquant-cache')
    args = parser.parse_args()
    print(build(args.root, args.cache))
    arrays = load(args.cache)
    for kind in ('trade', 'mark'):
        missing = np.isnan(arrays[kind][:, 0])
        print(kind, int(missing.sum()), 'missing minutes')
