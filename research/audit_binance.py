"""Verify complete frozen native archive coverage without economic evaluation."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

from pancakequant.research import spec, timestamp
from research.acquire_binance import paths
from research.linear_forecast import archive_rows

HOUR = 3600000


def repair_rows(directory):
    """Exact original official API responses; supplement gaps, never overwrite."""
    receipt=json.loads((directory/'receipt.json').read_text());result=[]
    for item in receipt:
        name=item['file']
        if Path(name).name!=name:raise ValueError('invalid repair path')
        raw=(directory/name).read_bytes()
        if len(raw)!=item['bytes'] or hashlib.sha256(raw).hexdigest()!=item['sha256']:
            raise ValueError('repair identity mismatch')
        url=urlsplit(item['url']);q=parse_qs(url.query)
        if (url.scheme!='https' or url.netloc!='fapi.binance.com'
                or url.path!='/fapi/v1/markPriceKlines' or q.get('symbol')!=['BTCUSDT']
                or q.get('interval')!=['1h']):raise ValueError('invalid native repair source')
        rows=json.loads(raw)
        expected=list(range(int(q['startTime'][0]),int(q['endTime'][0])+1,HOUR))
        if [r[0] for r in rows]!=expected:raise ValueError('incomplete native repair')
        result.extend(rows)
    return result,receipt


def audit(root, tail, output, repairs=None):
    frozen=spec();start=timestamp(frozen['start']);end=timestamp(frozen['end'])
    times={'klines':[], 'markPriceKlines':[]};funding=[];receipts=[]
    for relative in paths():
        if '2019-12' in relative:continue  # separate trade-only signal warmup API evidence
        rows=archive_rows(root,relative)
        p=root/relative
        receipts.append({'path':relative,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                         'bytes':p.stat().st_size,'rows':len(rows)})
        if '/fundingRate/' in relative:
            for row in rows:
                t=int(row[0]);hours=Decimal(row[1]);rate=Decimal(row[2])
                if hours<=0 or not hours.is_finite() or not rate.is_finite():raise ValueError('invalid funding')
                funding.append((t,hours,rate))
        else:
            kind='markPriceKlines' if '/markPriceKlines/' in relative else 'klines'
            for row in rows:
                t=int(row[0]);o,h,low,c=map(Decimal,row[1:5]);volume=Decimal(row[5])
                if not all(x.is_finite() for x in (o,h,low,c,volume)):
                    raise ValueError('nonfinite price/volume')
                if not (0<low<=min(o,c)<=max(o,c)<=h) or volume<0:
                    raise ValueError('invalid price/volume')
                if int(row[6])!=t+HOUR-1:raise ValueError('incomplete hourly close time')
                times[kind].append(t)
    repair_identity=[]
    if repairs is not None:
        restored,repair_identity=repair_rows(repairs)
        seen=set(times['markPriceKlines'])
        for row in restored:
            t=int(row[0]);o,h,low,c=map(Decimal,row[1:5]);volume=Decimal(row[5])
            if (t in seen or not start<=t<end or t%HOUR
                    or not all(x.is_finite() for x in (o,h,low,c,volume))
                    or not (0<low<=min(o,c)<=max(o,c)<=h) or volume<0
                    or int(row[6])!=t+HOUR-1):raise ValueError('invalid or overlapping mark repair')
            seen.add(t);times['markPriceKlines'].append(t)
        times['markPriceKlines'].sort()
    expected=list(range(start,end,HOUR))
    for kind,ts in times.items():
        if ts!=expected:raise ValueError(f'{kind}: missing, duplicate or out-of-window hour')
    raw=tail.read_bytes();tail_rows=json.loads(raw)
    for row in tail_rows:
        if row['symbol']!='BTCUSDT':raise ValueError('wrong funding symbol')
        t=int(row['fundingTime']);rate=Decimal(row['fundingRate'])
        if not rate.is_finite():raise ValueError('invalid tail funding')
        funding.append((t,Decimal(8),rate))
    ts=[r[0] for r in funding]
    if ts!=sorted(set(ts)) or any(not start<=t<end for t in ts):
        raise ValueError('funding duplicate, ordering or window')
    # Archive supplies historical interval. Tail observed timestamps must support
    # eight-hour slots; no fabricated zero payment or silent timestamp rounding.
    if any(r[1]!=8 for r in funding):
        raise ValueError('funding interval transition needs explicit timeline treatment')
    if [t//(8*HOUR)*(8*HOUR) for t in ts] != list(range(start,end,8*HOUR)):
        raise ValueError('funding settlement slots missing or duplicate')
    offsets=[t%(8*HOUR) for t in ts]
    report={'qualification':'NOT_QUALIFIED','market_coverage':'complete_native_Binance_BTCUSDT',
            'formal_start':frozen['start'],'formal_end_exclusive':frozen['end'],
            'trade_hours':len(times['klines']),'mark_hours':len(times['markPriceKlines']),
            'funding_events':len(funding),'maximum_funding_offset_ms':max(offsets),
            'nonzero_funding_offsets':sum(x!=0 for x in offsets),'archives':receipts,'native_mark_repairs':repair_identity,
            'tail_sha256':hashlib.sha256(raw).hexdigest(),
            'unresolved':['dated fee/risk/filter timeline','stablecoin collateral risk',
                          'exact funding price at offset timestamps','native entry protection lifecycle'],
            'note':'Coverage validation is not economic validation. Raw funding timestamps retained.'}
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='archives'},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--tail',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--repairs',type=Path)
    a=p.parse_args();audit(a.root,a.tail,a.output,a.repairs)
