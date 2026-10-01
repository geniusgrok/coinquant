"""Restore official daily prints on demand into a task-owned bounded cache."""
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import urllib.error
import urllib.request

from research.session_market import TradePrints


class RollingPrints(TradePrints):
    def __init__(self, root):
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        marker = root / '.unified-perp-cache'
        if not marker.exists():
            if any(root.iterdir()):
                raise ValueError('rolling cache requires an empty task-owned directory')
            marker.write_text('BTC-third-round-20261001\n')
        if marker.read_text() != 'BTC-third-round-20261001\n':
            raise ValueError('rolling cache belongs to another task')
        super().__init__(root)
        self.missing = set()
        self.used = []

    def _load(self, day_ms):
        name = f'BTCUSDT-aggTrades-{datetime.fromtimestamp(day_ms / 1000, timezone.utc):%Y-%m-%d}.zip'
        path = self.root / name
        if not path.exists() and name not in self.missing:
            base = 'https://data.binance.vision/data/futures/um/daily/aggTrades/BTCUSDT/' + name
            try:
                with urllib.request.urlopen(base + '.CHECKSUM', timeout=30) as response:
                    checksum = response.read()
                expected = checksum.decode().split()[0]
                temporary = path.with_suffix('.downloading')
                digest = hashlib.sha256()
                with urllib.request.urlopen(base, timeout=60) as response, temporary.open('wb') as stream:
                    while block := response.read(1024 * 1024):
                        digest.update(block)
                        stream.write(block)
                if digest.hexdigest() != expected:
                    raise ValueError('official print checksum mismatch: ' + name)
                temporary.replace(path)
                Path(str(path) + '.CHECKSUM').write_bytes(checksum)
                print('restored ' + name, flush=True)
            except urllib.error.HTTPError as exc:
                if exc.code != 404:
                    raise
                self.missing.add(name)
        if name in self.used:
            self.used.remove(name)
        self.used.append(name)
        rows = super()._load(day_ms)
        # Only files created in this marked scratch cache are removed. Their official
        # SHA remains in the measured input manifest and allows exact restoration.
        for old in self.used[:-3]:
            old_path = self.root / old
            for candidate in (old_path, Path(str(old_path) + '.CHECKSUM')):
                candidate.unlink(missing_ok=True)
            cache = self.root.parent / (self.root.name + '-cache')
            for candidate in cache.glob(old + '.*.bin'):
                candidate.unlink()
        self.used = self.used[-3:]
        return rows
