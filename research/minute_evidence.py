"""Verify native minute originals and exact reconstruction before path refinement."""
from decimal import Decimal as D
import hashlib
from pathlib import Path
from research.acquire_minute_probe import DATES, validate
from research.linear_forecast import archive_rows
from pancakequant.research import timestamp

HOUR=3600000

def load(root, hourly, extra_days=()):
    tables={k:{} for k in ('klines','markPriceKlines')};identity=[]
    for day in dict.fromkeys((*DATES, *extra_days)):
        begin=timestamp(day+'T00:00:00Z')
        for kind in tables:
            path=f'daily/{kind}/BTCUSDT/1m/BTCUSDT-1m-{day}.zip'
            raw=(root/path).read_bytes();checksum=Path(str(root/path)+'.CHECKSUM').read_bytes()
            validate(raw,checksum,day)
            rows={int(r[0]):tuple(D(v) for v in r[1:5]) for r in archive_rows(root,path)}
            for t in range(begin,begin+86400000,HOUR):
                bars=[rows[x] for x in range(t,t+HOUR,60000)]
                rebuilt=(bars[0][0],max(b[1] for b in bars),min(b[2] for b in bars),bars[-1][3])
                if rebuilt != tuple(D(v) for v in hourly[kind][t][1:5]):
                    raise ValueError(f'minute/hour reconstruction mismatch {kind} {t}')
            tables[kind].update(rows)
            identity.append(dict(path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    return tables,identity

def steps(t, trade, mark, minutes):
    if not minutes or t not in minutes['klines']:
        return [(t,trade,mark)]
    return [(s,minutes['klines'][s],minutes['markPriceKlines'][s])
            for s in range(t,t+HOUR,60000)]
