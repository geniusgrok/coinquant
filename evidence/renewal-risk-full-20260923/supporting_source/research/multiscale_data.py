"""Incremental M60 data recovery; only verified original bars, never interpolation."""
import hashlib
import json
from pathlib import Path
from decimal import Decimal as D

from coinquant.multiscale import DAY, daily_snapshots, published_daily_key
from coinquant.research import spec, invocations, timestamp, iso
from research.bounded_execution_data import _rows, validate_hour, HOUR, MINUTE
from research.bounded_execution_replay import prepare, input_identity
from research.sustainable_replay import exit_minutes


def warmup_daily(roots):
    """Use a verified official response, or expose a genuinely cold start."""
    found = []
    identities = []
    for root in roots:
        for receipt_path in root.rglob('RECEIPT.json'):
            records = json.loads(receipt_path.read_text())
            if not isinstance(records, list):
                continue
            for record in records:
                if record.get('path') != 'warmup-daily.json' or record.get('status') != 'received':
                    continue
                path = receipt_path.parent/record['path']
                raw = path.read_bytes()
                if (len(raw) != record['bytes'] or hashlib.sha256(raw).hexdigest() != record['sha256']
                        or not record['url'].startswith('https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1d&')):
                    raise ValueError('unidentified supplemental warmup')
                rows = json.loads(raw)
                if not rows:
                    continue
                first = int(rows[0][0]); last = timestamp('2019-12-01T00:00:00Z')
                if first < timestamp('2019-10-08T00:00:00Z') or first >= last:
                    raise ValueError('official warmup response outside requested time range')
                if [int(r[0]) for r in rows] != list(range(first, last, DAY)):
                    raise ValueError('supplementary warmup is not continuous through November')
                bars = []
                for r in rows:
                    o,h,l,c = map(D, r[1:5]); end = int(r[0])+DAY
                    if (int(r[6]) != end-1 or not all(x.is_finite() for x in (o,h,l,c))
                            or not 0 < l <= min(o,c) <= max(o,c) <= h):
                        raise ValueError('invalid official daily warmup')
                    bars.append((end,h,l,c))
                if found and bars != found:
                    raise ValueError('conflicting warmup original versions')
                found = bars
                identities.append(dict(path=str(path),sha256=record['sha256'],bytes=len(raw),source=record['url']))
    return found, identities


def potential_hours(cache, extra_daily=()):
    """All causal positive calls and the next flat call; no account-return filter."""
    cfg=spec(); start=timestamp(cfg['start']); end=max(cache[0]['klines'])+HOUR
    snapshots=daily_snapshots(cache[2],cache[0]['klines'],start,end,
        D(cfg['slippage_fraction'])+D(cfg['spread_fraction'])/2,extra_daily)
    selected=[]; previous_positive=False
    for t in invocations(cfg):
        if t >= end:
            break
        snapshot=snapshots.get(published_daily_key(t))
        positive=bool(snapshot and snapshot.opportunity)
        if positive or previous_positive:
            selected.append(t)
        previous_positive=positive
    return selected, snapshots


def extend_minutes(prepared, roots, hours, warmup_identity=()):
    """Refine only requested hours; preserve the existing SX60 refinements exactly."""
    cache,(old_tables,old_identity),old_quotes,old_validation,_=prepared
    tables={k:dict(v) for k,v in old_tables.items()}
    quotes=dict(old_quotes); identities=list(old_identity)+list(warmup_identity)
    index={}
    for root in roots:
        for path in root.rglob('BTCUSDT-1m-*.zip'):
            if 'klines' not in path.parts and 'markPriceKlines' not in path.parts:
                continue
            kind='markPriceKlines' if 'markPriceKlines' in path.parts else 'klines'
            day=path.name[len('BTCUSDT-1m-'):-4]
            key=(kind,day)
            if key in index and index[key].read_bytes()!=path.read_bytes():
                raise ValueError('minute archive revision conflict: '+str(key))
            index[key]=path
    loaded={}; checks=[]
    def source(kind,day):
        path=index.get((kind,day),index.get((kind,day[:7])))
        if path is None:
            raise ValueError('missing official minute archive '+kind+' '+day)
        if path not in loaded:
            raw=path.read_bytes(); sha=hashlib.sha256(raw).hexdigest()
            if Path(str(path)+'.CHECKSUM').read_text().split()[0]!=sha:
                raise ValueError('official minute checksum mismatch')
            rows=_rows(raw); values={int(r[0]):r for r in rows}
            if len(values)!=len(rows):
                raise ValueError('duplicate minute timestamp')
            loaded[path]=values
            identities.append(dict(path=str(path),sha256=sha,bytes=len(raw),source='Binance official archive and original CHECKSUM'))
        return loaded[path]
    for t in sorted(set(hours)):
        for kind in tables:
            values=source(kind,iso(t)[:10])
            rows=[values[x] for x in range(t,t+HOUR,MINUTE) if x in values]
            checks.append(dict(validate_hour(rows,cache[0][kind][t],trade=kind=='klines'),kind=kind))
            for r in rows:
                tm=int(r[0]); value=tuple(map(D,r[1:5]))
                if tm in tables[kind] and tables[kind][tm]!=value:
                    raise ValueError('new minute differs from frozen control minute')
                tables[kind][tm]=value
                if kind=='klines':quotes[tm]=D(r[7])
        tm=t-MINUTE
        r=source('klines',iso(tm)[:10]).get(tm)
        if r is None or int(r[6])!=tm+MINUTE-1 or not D(r[7]).is_finite() or D(r[7])<0:
            raise ValueError('missing/invalid causally published minute volume')
        quotes[tm]=D(r[7])
    combined=dict(hours=sorted(set(old_validation['hours'])|set(hours)),
        original=old_validation,incremental_checks=checks,
        incremental_hours=sorted(set(hours)-{t for t in old_tables['klines'] if t%HOUR==0}))
    return cache,(tables,identities),quotes,combined,input_identity(cache[3]+identities)


def restore_inputs(bounded, sx60, new_roots, *, full=False):
    stage='full' if full else 'development'
    root=bounded/'inputs'/stage
    prepared=exit_minutes(sx60/'exit-minutes',prepare(root,bounded/'old-controls'/stage,
        bounded/'inputs/entry-minutes',bounded/'evidence/MINUTE_REQUEST.json',bounded/'inputs/mark-repair',full=full))
    warmup,identity=warmup_daily(new_roots)
    hours,snapshots=potential_hours(prepared[0],warmup)
    prepared=extend_minutes(prepared,[bounded/'inputs',sx60/'exit-minutes',*new_roots],hours,identity)
    return root,prepared,warmup,snapshots
