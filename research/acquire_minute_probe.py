"""Native minute evidence for explicit exit dates; verified originals are reused."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import date
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import zipfile
from research.acquire_binance import BASE, download
from pancakequant.research import timestamp

DATES = ('2021-05-13', '2022-11-08', '2023-02-15', '2023-03-13', '2023-06-05', '2023-06-20')


def validate(raw, checksum, day):
    if hashlib.sha256(raw).hexdigest() != checksum.decode().split()[0]:
        raise ValueError('exchange checksum mismatch')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if len(z.namelist()) != 1 or z.testzip() is not None:
            raise ValueError('archive structure/CRC')
        rows = list(csv.reader(io.StringIO(z.read(z.namelist()[0]).decode())))
    if rows and not rows[0][0].isdigit(): rows = rows[1:]
    start = timestamp(day+'T00:00:00Z')
    if [int(r[0]) for r in rows] != list(range(start,start+86400000,60000)):
        raise ValueError('minute boundary/continuity')
    for r in rows:
        o,h,l,c = map(Decimal,r[1:5])
        if not 0 < l <= min(o,c) <= max(o,c) <= h or int(r[6]) != int(r[0])+59999:
            raise ValueError('invalid minute OHLC/close time')
    return len(rows)


def run(root, days=DATES):
    days=tuple(dict.fromkeys(days))
    if any(date.fromisoformat(day).isoformat()!=day for day in days):raise ValueError("invalid minute date")
    root.mkdir(parents=True,exist_ok=True)
    def one(item):
        day,kind=item
        path=f'daily/{kind}/BTCUSDT/1m/BTCUSDT-1m-{day}.zip'
        target=root/path; receipt=dict(path=path,source=BASE+path)
        try:
            checksum_path=Path(str(target)+'.CHECKSUM')
            raw=target.read_bytes() if target.exists() else download(BASE+path)
            checksum=checksum_path.read_bytes() if checksum_path.exists() else download(BASE+path+'.CHECKSUM')
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(raw); Path(str(target)+'.CHECKSUM').write_bytes(checksum)
            receipt.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
            receipt.update(rows=validate(raw,checksum,day),status='verified')
        except Exception as exc:
            receipt.update(status='unavailable',error=f'{type(exc).__name__}: {exc}')
        return receipt
    with ThreadPoolExecutor(max_workers=3) as pool:
        records=list(pool.map(one,[(d,k) for d in days for k in ('klines','markPriceKlines')]))
    (root/'receipt.json').write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps({'verified':sum(r['status']=='verified' for r in records),'total':len(records)}))
    return all(r['status']=='verified' for r in records)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--day',action='append',help='Explicit evidence date; defaults to original six development days')
    a=p.parse_args()
    raise SystemExit(0 if run(a.output,a.day or DATES) else 1)
