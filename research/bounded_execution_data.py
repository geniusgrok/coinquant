"""Verify only the frozen entry hours and their causally usable minute volume.

Daily/monthly archive hashes are checked against their original exchange checksum.
A missing daily mark archive may use the saved official monthly archive or exact
public REST response, never a synthetic/interpolated minute.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path
import zipfile

from coinquant.research import iso
from research.acquire_minute_probe import validate
from research.linear_forecast import archive_rows

MINUTE = 60_000
HOUR = 60*MINUTE
VOLUME_ROUNDING_TOLERANCE = D('.000001')


def _rows(raw: bytes) -> list[list[str]]:
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if len(z.namelist()) != 1 or z.testzip() is not None:
            raise ValueError('invalid minute archive')
        rows = list(csv.reader(io.StringIO(z.read(z.namelist()[0]).decode())))
    return rows[1:] if rows and not rows[0][0].isdigit() else rows


def validate_hour(rows: list, hourly: list, *, trade: bool) -> dict:
    start = int(hourly[0])
    if [int(r[0]) for r in rows] != list(range(start, start+HOUR, MINUTE)):
        raise ValueError(f'incomplete minute hour {start}')
    for r in rows:
        o,h,l,c = map(D, r[1:5])
        if (not all(x.is_finite() for x in (o,h,l,c)) or
                not 0 < l <= min(o,c) <= max(o,c) <= h or int(r[6]) != int(r[0])+MINUTE-1):
            raise ValueError('invalid native minute price/time')
    rebuilt = (D(rows[0][1]), max(D(r[2]) for r in rows),
               min(D(r[3]) for r in rows), D(rows[-1][4]))
    if rebuilt != tuple(map(D, hourly[1:5])):
        raise ValueError(f'minute/hour OHLC mismatch {start}: {rebuilt} != {hourly[1:5]}')
    deltas = {}
    if trade:
        for column, label in ((5,'base'), (7,'quote')):
            delta = sum((D(r[column]) for r in rows), D(0))-D(hourly[column])
            deltas[label] = str(delta)
            if abs(delta) > VOLUME_ROUNDING_TOLERANCE:
                raise ValueError(f'minute/hour volume mismatch {label} {start}: {delta}')
        if sum(int(r[8]) for r in rows) != int(hourly[8]):
            raise ValueError('minute/hour trade count mismatch')
    return dict(time=start, ohlc_exact=True, volume_difference=deltas)


def _mark_repair(root: Path) -> tuple[dict[int,list],dict]:
    receipt = json.loads((root/'RECEIPT.json').read_text())
    for record in receipt['records']:
        if not record.get('complete_required_hour'):
            continue
        source = record['source']
        if source.startswith('https://data.binance.vision/data/futures/um/monthly/markPriceKlines/'):
            path = root/'monthly.zip'; raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != (root/'monthly.zip.CHECKSUM').read_text().split()[0]:
                raise ValueError('mark repair exchange checksum mismatch')
            rows = _rows(raw)
        elif source.startswith('https://fapi.binance.com/fapi/v1/markPriceKlines?'):
            path = root/'required-hour.json'; raw = path.read_bytes(); rows = json.loads(raw)
        else:
            raise ValueError('unrecognized mark repair source')
        if len(raw) != record['bytes'] or hashlib.sha256(raw).hexdigest() != record['sha256']:
            raise ValueError('mark repair receipt mismatch')
        if len({int(r[0]) for r in rows}) != len(rows):
            raise ValueError('duplicate mark repair minute')
        return {int(r[0]):r for r in rows}, dict(path=str(path),source=source,bytes=len(raw),sha256=record['sha256'])
    raise ValueError('no verified repair for required mark minutes')


def load_entry_minutes(root: Path, hourly: dict, entry_hours: list[int], *, repair: Path | None = None):
    """Return refinements, known volume, original identities and reconstruction proof."""
    hours = sorted(set(t for t in entry_hours if t in hourly['klines']))
    tables = {k:{} for k in ('klines','markPriceKlines')}
    quotes = {}; identity = []; checks = []
    repair_rows = None
    required = defaultdict(list)
    for t in hours:
        required[iso(t)[:10]].append(t)
    for day, times in required.items():
        for kind in tables:
            relative = f'daily/{kind}/BTCUSDT/1m/BTCUSDT-1m-{day}.zip'
            path = root/relative
            if path.exists():
                raw = path.read_bytes(); checksum = Path(str(path)+'.CHECKSUM').read_bytes()
                validate(raw,checksum,day)
                rows = archive_rows(root,relative)
                source = {int(r[0]):r for r in rows}
                identity.append(dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
                                     source='https://data.binance.vision/data/futures/um/'+relative))
                if kind == 'klines':
                    quotes.update({int(r[0]):D(r[7]) for r in rows})
            elif kind == 'markPriceKlines' and repair is not None:
                if repair_rows is None:
                    repair_rows, source_identity = _mark_repair(repair); identity.append(source_identity)
                source = repair_rows
            else:
                raise ValueError(f'missing native minute original: {path}')
            for t in times:
                rows = [source[x] for x in range(t,t+HOUR,MINUTE) if x in source]
                check = validate_hour(rows,hourly[kind][t],trade=kind=='klines')
                check['kind'] = kind; checks.append(check)
                tables[kind].update({int(r[0]):tuple(map(D,r[1:5])) for r in rows})
    # Earliest child reads the previous minute, including across a UTC date boundary.
    for t in hours:
        needed = t-MINUTE
        if needed not in quotes:
            day = iso(needed)[:10]
            relative = f'daily/klines/BTCUSDT/1m/BTCUSDT-1m-{day}.zip'
            path = root/relative;raw = path.read_bytes();checksum = Path(str(path)+'.CHECKSUM').read_bytes()
            validate(raw,checksum,day)
            rows = archive_rows(root,relative);quotes.update({int(r[0]):D(r[7]) for r in rows})
            identity.append(dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
                                 source='https://data.binance.vision/data/futures/um/'+relative))
    return tables,quotes,identity,dict(hours=hours,checks=checks,volume_rounding_tolerance=str(VOLUME_ROUNDING_TOLERANCE))
