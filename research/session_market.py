"""Official Binance UM files for the session account. No network inside loaders.

December 2019 perpetual hours are the already verified warmup file. Vision's
monthly futures archive begins 2020-01-01. Later months are not interpolated.
"""
from datetime import datetime, timezone
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import zipfile

from coinquant.campaign import ORIGIN


WARMUP_TRADE = Path('evidence/binance-boundary-20260921/warmup-trade.json')
WARMUP_TRADE_SHA = '62e9a9ecddccac737f99032a224f7a2a1932756cf200db34fb5c5641b72c4094'
WARMUP_FUNDING = Path('evidence/binance-boundary-20260921/warmup-funding.json')
WARMUP_FUNDING_SHA = '25a949a83bc5305727fb86f0d6e3e297235a03990d6404a3f160a2ce82bd82b3'
HOUR = 3_600_000
FOUR = 14_400_000
MINUTE = 60_000
# Vision has no 2026-09 funding object yet. Settlements in that gap stay unknown.
FUNDING_GAP_FROM = int(datetime(2026, 9, 1, tzinfo=timezone.utc).timestamp() * 1000)


def _sha(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _require(path, expected):
    digest = _sha(path)
    if digest != expected:
        raise ValueError(f'warmup identity mismatch {path}')
    return digest


def four_hour_from_hours(rows):
    """Aggregate verified one-hour trade klines. Four hours, no remainder."""
    if len(rows) % 4:
        raise ValueError('hourly warmup is not a whole number of four-hour bars')
    bars = {}
    for index in range(0, len(rows), 4):
        chunk = rows[index:index + 4]
        opens = [int(row[0]) for row in chunk]
        if any(opens[offset] != opens[0] + offset * HOUR for offset in range(4)):
            raise ValueError('hourly warmup is not contiguous')
        if opens[0] % FOUR:
            raise ValueError('four-hour bar is not aligned')
        high = max(D(row[2]) for row in chunk)
        low = min(D(row[3]) for row in chunk)
        volume = sum((D(row[5]) for row in chunk), D(0))
        bars[opens[0]] = (D(chunk[0][1]), high, low, D(chunk[-1][4]), volume)
    return bars


def _kline_row(row):
    open_time = int(row[0])
    close_time = int(row[6])
    return open_time, close_time, (D(row[1]), D(row[2]), D(row[3]), D(row[4]), D(row[5]))


def _read_zip_rows(path):
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if not name.endswith('/')]
        if len(names) != 1:
            raise ValueError(f'unexpected archive members in {path}')
        raw = archive.read(names[0]).decode('utf-8')
    rows = []
    for line in raw.splitlines():
        if not line or line.startswith('calc_time') or line.startswith('open_time'):
            continue
        rows.append(line.split(','))
    return rows


def _checksum(path):
    text = Path(str(path) + '.CHECKSUM').read_text(encoding='utf-8').split()
    digest = text[0]
    if len(digest) != 64 or _sha(path) != digest:
        raise ValueError(f'checksum mismatch {path}')
    return digest


class Market:
    """Four-hour bars stay in memory. One-minute months load when touched."""

    def __init__(self, h4, funding, root=None, identity=None):
        self.h4 = h4
        self.funding = funding  # sorted (time_ms, rate)
        self.root = None if root is None else Path(root)
        self.identity = identity or {}
        self._months = {}
        self._order = []

    def bar4(self, open_ms):
        return self.h4.get(int(open_ms))

    def minute(self, kind, open_ms):
        open_ms = int(open_ms)
        if self.root is None:
            table = self.identity.get(kind) or {}
            return table.get(open_ms)
        stamp = datetime.fromtimestamp(open_ms / 1000, timezone.utc)
        key = (kind, stamp.year, stamp.month)
        table = self._months.get(key)
        if table is None:
            table = self._load_month(kind, stamp.year, stamp.month)
            self._months[key] = table
            self._order.append(key)
            while len(self._order) > 3:
                self._months.pop(self._order.pop(0), None)
        return table.get(open_ms)

    def _load_month(self, kind, year, month):
        folder = 'klines' if kind == 'trade' else 'mark'
        name = f'BTCUSDT-1m-{year:04d}-{month:02d}.zip'
        path = self.root / folder / '1m' / name
        table = {}
        if path.exists():
            _checksum(path)
            for row in _read_zip_rows(path):
                open_time, close_time, values = _kline_row(row)
                if close_time != open_time + MINUTE - 1 or open_time % MINUTE:
                    raise ValueError(f'minute alignment {path} {open_time}')
                table[open_time] = values
        daily = self.root / folder / '1m' / 'daily'
        if daily.exists():
            prefix = f'BTCUSDT-1m-{year:04d}-{month:02d}-'
            for path in sorted(daily.glob(prefix + '*.zip')):
                _checksum(path)
                for row in _read_zip_rows(path):
                    open_time, close_time, values = _kline_row(row)
                    if close_time != open_time + MINUTE - 1:
                        raise ValueError(f'minute alignment {path} {open_time}')
                    if open_time in table and table[open_time] != values:
                        raise ValueError(f'minute conflict {open_time}')
                    table[open_time] = values
        return table

    def funding_between(self, start_ms, end_ms):
        """Settlements with start < time <= end. A missing official rate is a gap."""
        events = []
        gap = False
        for stamp, rate in self.funding:
            if stamp <= start_ms:
                continue
            if stamp > end_ms:
                break
            events.append((stamp, rate))
        if end_ms > FUNDING_GAP_FROM and start_ms < end_ms:
            # Any open position that crosses September 2026 lacks an official file.
            if any(stamp >= FUNDING_GAP_FROM for stamp, _ in events) or end_ms >= FUNDING_GAP_FROM:
                known = {stamp for stamp, _ in self.funding if start_ms < stamp <= end_ms}
                # The archive simply has no September file. Callers decide.
                gap = end_ms >= FUNDING_GAP_FROM and not any(stamp >= FUNDING_GAP_FROM for stamp in known)
        return events, gap


def load_base(root):
    """Four-hour trade bars and funding. Minute files stay on disk."""
    root = Path(root)
    _require(WARMUP_TRADE, WARMUP_TRADE_SHA)
    hours = json.loads(WARMUP_TRADE.read_text(encoding='utf-8'))
    bars = four_hour_from_hours(hours)
    if min(bars) != ORIGIN:
        raise ValueError('warmup does not start at the model origin')
    digests = {'warmup_trade_sha256': WARMUP_TRADE_SHA, 'vision': []}
    folder = root / 'klines' / '4h'
    for path in sorted(folder.glob('BTCUSDT-4h-*.zip')):
        digest = _checksum(path)
        digests['vision'].append({'path': str(path.relative_to(root)), 'sha256': digest, 'bytes': path.stat().st_size})
        for row in _read_zip_rows(path):
            open_time, close_time, values = _kline_row(row)
            if close_time != open_time + FOUR - 1 or open_time % FOUR:
                raise ValueError(f'four-hour alignment {path} {open_time}')
            if open_time in bars and bars[open_time] != values:
                raise ValueError(f'four-hour conflict at {open_time}')
            bars[open_time] = values
    daily = folder / 'daily'
    if daily.exists():
        for path in sorted(daily.glob('BTCUSDT-4h-*.zip')):
            digest = _checksum(path)
            digests['vision'].append({'path': str(path.relative_to(root)), 'sha256': digest, 'bytes': path.stat().st_size})
            for row in _read_zip_rows(path):
                open_time, close_time, values = _kline_row(row)
                if close_time != open_time + FOUR - 1 or open_time % FOUR:
                    raise ValueError(f'four-hour alignment {path} {open_time}')
                if open_time in bars and bars[open_time] != values:
                    raise ValueError(f'four-hour conflict at {open_time}')
                bars[open_time] = values
    end = int(datetime(2026, 9, 20, tzinfo=timezone.utc).timestamp() * 1000)
    cursor = ORIGIN
    missing = []
    while cursor + FOUR <= end:
        if cursor not in bars:
            missing.append(cursor)
            if len(missing) > 8:
                break
        cursor += FOUR
    if missing:
        raise ValueError('missing four-hour bars at ' + ','.join(str(item) for item in missing[:8]))
    _require(WARMUP_FUNDING, WARMUP_FUNDING_SHA)
    funding = {}
    for row in json.loads(WARMUP_FUNDING.read_text(encoding='utf-8')):
        if row.get('symbol') != 'BTCUSDT':
            raise ValueError('warmup funding symbol')
        funding[int(row['fundingTime'])] = D(row['fundingRate'])
    fund_dir = root / 'funding'
    if fund_dir.exists():
        for path in sorted(fund_dir.glob('BTCUSDT-fundingRate-*.zip')):
            digest = _checksum(path)
            digests['vision'].append({'path': str(path.relative_to(root)), 'sha256': digest, 'bytes': path.stat().st_size})
            for row in _read_zip_rows(path):
                stamp, rate = int(row[0]), D(row[-1])
                if stamp in funding and funding[stamp] != rate:
                    raise ValueError(f'funding conflict at {stamp}')
                funding[stamp] = rate
    series = tuple(sorted(funding.items()))
    digests['warmup_funding_sha256'] = WARMUP_FUNDING_SHA
    digests['four_hour_bars'] = len(bars)
    digests['funding_points'] = len(series)
    digests['funding_gap_from'] = FUNDING_GAP_FROM
    return Market(bars, series, root, digests)


def _iter_zip_rows(path):
    """Stream one CSV member. Callers that need random access keep their own rows."""
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if not name.endswith('/')]
        if len(names) != 1:
            raise ValueError(f'unexpected archive members in {path}')
        with archive.open(names[0]) as raw:
            for line in raw:
                text = line.decode('utf-8').strip()
                if not text or text.startswith('calc_time') or text.startswith('open_time'):
                    continue
                yield text.split(',')


def _scaled_int(text, places):
    """Exact integer of a decimal string times 10**places. Extra digits fail closed."""
    negative = text.startswith('-')
    body = text[1:] if negative else text
    if '.' in body:
        whole, frac = body.split('.')
        if not frac.isdigit() or (whole and not whole.isdigit()):
            raise ValueError(f'print scale {text}')
        frac = frac.rstrip('0')
        if len(frac) > places:
            raise ValueError(f'print scale {text}')
        frac = frac.ljust(places, '0')
    else:
        if not body.isdigit():
            raise ValueError(f'print scale {text}')
        whole, frac = body, '0' * places
    value = int((whole or '0') + frac)
    return -value if negative else value


class TradePrints:
    """Daily aggTrades. One cached day. Missing files are unknown, not empty.

    Rows stay as integers: transact time, agg id, and price/quantity scaled by
    1e8. Historical prints are finer than the current 0.1 tick. The public
    window still returns Decimals, in (time, agg id) order.
    """

    def __init__(self, root):
        self.root = Path(root)
        self._day_ms = None
        self._rows = None

    def window(self, start_ms, end_ms):
        rows = self.timed(start_ms, end_ms)
        return None if rows is None else [(price, qty) for _t, price, qty in rows]

    def timed(self, start_ms, end_ms):
        """(time, price, quantity) Decimals in [start, end), or None if a day is unavailable."""
        rows = self.raw(start_ms, end_ms)
        if rows is None:
            return None
        scale = D(10) ** 8
        return [(t, D(p) / scale, D(q) / scale) for t, p, q in rows]

    def raw(self, start_ms, end_ms):
        """(time, price*1e8, quantity*1e8) integers in [start, end), or None."""
        if end_ms <= start_ms:
            return []
        import bisect
        matched = []
        day = (start_ms // 86_400_000) * 86_400_000
        last = ((end_ms - 1) // 86_400_000) * 86_400_000
        while day <= last:
            rows = self._load(day)
            if rows is None:
                return None
            times, _ids, prices, qtys = rows
            index = bisect.bisect_left(times, start_ms)
            stop = bisect.bisect_left(times, end_ms)
            matched.extend(zip(times[index:stop], prices[index:stop], qtys[index:stop]))
            day += 86_400_000
        return matched

    def last(self, at_ms):
        """(time, price) of the last print at or before at_ms, or None if unavailable."""
        import bisect
        day = (at_ms // 86_400_000) * 86_400_000
        for candidate in (day, day - 86_400_000):
            rows = self._load(candidate)
            if rows is None:
                return None
            times, _ids, prices, _qtys = rows
            index = bisect.bisect_right(times, at_ms) - 1
            if index >= 0:
                return times[index], D(prices[index]) / D(10) ** 8
        return None

    def _load(self, day_ms):
        if self._day_ms == day_ms:
            return self._rows
        stamp = datetime.fromtimestamp(day_ms / 1000, timezone.utc)
        name = f"BTCUSDT-aggTrades-{stamp:%Y-%m-%d}.zip"
        path = self.root / name
        if not path.exists():
            self._day_ms, self._rows = day_ms, None
            return None
        digest = _checksum(path)
        import array
        import os
        cache = self.root.parent / (self.root.name + '-cache') / f'{name}.{digest}.bin'
        if cache.exists():
            with cache.open('rb') as handle:
                count = array.array('q')
                count.fromfile(handle, 1)
                packed = tuple(array.array('q') for _ in range(4))
                for column in packed:
                    column.fromfile(handle, count[0])
            self._day_ms, self._rows = day_ms, packed
            return packed
        times, ids, prices, qtys = (array.array('q') for _ in range(4))
        ordered = True
        previous = None
        for row in _iter_zip_rows(path):
            if row[0] in ('agg_trade_id', 'a'):
                continue
            stamp_ms, identity = int(row[5]), int(row[0])
            key = (stamp_ms, identity)
            if previous is not None and key < previous:
                ordered = False
            previous = key
            times.append(stamp_ms)
            ids.append(identity)
            prices.append(_scaled_int(row[1], 8))
            qtys.append(_scaled_int(row[2], 8))
        if not ordered:
            order = sorted(range(len(times)), key=lambda index: (times[index], ids[index]))
            times = array.array('q', (times[index] for index in order))
            ids = array.array('q', (ids[index] for index in order))
            prices = array.array('q', (prices[index] for index in order))
            qtys = array.array('q', (qtys[index] for index in order))
        packed = (times, ids, prices, qtys)
        cache.parent.mkdir(parents=True, exist_ok=True)
        temporary = cache.with_suffix(f'.{os.getpid()}.tmp')
        with temporary.open('wb') as handle:
            array.array('q', [len(times)]).tofile(handle)
            for column in packed:
                column.tofile(handle)
        os.replace(temporary, cache)
        self._day_ms, self._rows = day_ms, packed
        return packed


def fetch(root, workers=8):
    """Download vision zips and their official checksums. Safe to repeat."""
    import subprocess
    from concurrent.futures import ThreadPoolExecutor

    root = Path(root)
    base = 'https://data.binance.vision/data/futures/um'
    jobs = []

    def add(url, dest):
        jobs.append((url, dest))
        jobs.append((url + '.CHECKSUM', Path(str(dest) + '.CHECKSUM')))

    months = []
    year, month = 2020, 1
    while (year, month) <= (2026, 8):
        months.append(f'{year:04d}-{month:02d}')
        month += 1
        if month == 13:
            year, month = year + 1, 1
    for stamp in months:
        add(f'{base}/monthly/klines/BTCUSDT/4h/BTCUSDT-4h-{stamp}.zip', root / 'klines' / '4h' / f'BTCUSDT-4h-{stamp}.zip')
        add(f'{base}/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-{stamp}.zip', root / 'klines' / '1m' / f'BTCUSDT-1m-{stamp}.zip')
        add(f'{base}/monthly/markPriceKlines/BTCUSDT/1m/BTCUSDT-1m-{stamp}.zip', root / 'mark' / '1m' / f'BTCUSDT-1m-{stamp}.zip')
        add(f'{base}/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-{stamp}.zip', root / 'funding' / f'BTCUSDT-fundingRate-{stamp}.zip')
    for day in range(1, 20):
        stamp = f'2026-09-{day:02d}'
        add(f'{base}/daily/klines/BTCUSDT/4h/BTCUSDT-4h-{stamp}.zip', root / 'klines' / '4h' / 'daily' / f'BTCUSDT-4h-{stamp}.zip')
        add(f'{base}/daily/klines/BTCUSDT/1m/BTCUSDT-1m-{stamp}.zip', root / 'klines' / '1m' / 'daily' / f'BTCUSDT-1m-{stamp}.zip')
        add(f'{base}/daily/markPriceKlines/BTCUSDT/1m/BTCUSDT-1m-{stamp}.zip', root / 'mark' / '1m' / 'daily' / f'BTCUSDT-1m-{stamp}.zip')

    def one(job):
        url, dest = job
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and dest.stat().st_size > 0 and not str(dest).endswith('.CHECKSUM'):
            checksum = Path(str(dest) + '.CHECKSUM')
            if checksum.exists():
                try:
                    _checksum(dest)
                    return 'cached', str(dest)
                except ValueError:
                    pass
        temporary = dest.with_suffix(dest.suffix + '.partial')
        result = subprocess.run(['curl', '-fsSL', '--retry', '4', '--retry-delay', '2', '-o', str(temporary), url],
                                capture_output=True, text=True)
        if result.returncode != 0:
            temporary.unlink(missing_ok=True)
            return 'missing', url + ' ' + (result.stderr or '')[-200:]
        temporary.replace(dest)
        return 'ok', str(dest)

    missing = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for status, detail in pool.map(one, jobs):
            if status == 'missing':
                missing.append(detail)
    manifest = root / 'FETCH.json'
    manifest.write_text(json.dumps({'missing': missing, 'jobs': len(jobs)}, indent=2) + '\n', encoding='utf-8')
    if missing:
        raise SystemExit('missing vision files:\n' + '\n'.join(missing[:30]))
    return root


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Download the frozen vision set')
    parser.add_argument('--root', type=Path, default=Path('/tmp/coinquant-session-market'))
    args = parser.parse_args()
    fetch(args.root)
    market = load_base(args.root)
    print(json.dumps({k: market.identity[k] for k in ('four_hour_bars', 'funding_points', 'funding_gap_from')}))
