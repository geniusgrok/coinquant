"""Small immutable market caches and bounded new public calendar/minute receipts."""
import argparse
from datetime import datetime,timezone
from decimal import Decimal as D
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import Request,urlopen
import zipfile
from zoneinfo import ZoneInfo

from research import nine_routes as r, flow_risk as f

SPEC=Path(__file__).with_name('loop-spec.json')


def new_json(path,value):
    with Path(path).open('x') as stream:json.dump(r.serial(value),stream,indent=2);stream.write('\n')


def source():
    from research.rebuild import source_identity
    identity=source_identity()
    if identity['dirty']:raise ValueError('freeze source before producing evidence')
    return identity


def capture(out):
    out.mkdir(parents=True,exist_ok=False);identity=source();receipts=[]
    requests=[]
    for month in ('2020-01','2022-01'):
        name=f'BTCUSDT-1m-{month}.zip';url='https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1m/'+name
        requests.extend([(name,url,16777216),(name+'.CHECKSUM',url+'.CHECKSUM',1048576)])
    requests.append(('cpi.ics','https://www.bls.gov/schedule/news_release/cpi.ics',1048576))
    for name,url,bound in requests:
        row=dict(name=name,url=url,request_ms=int(time.time()*1000),status=None)
        try:
            with urlopen(Request(url,headers={'User-Agent':'btc-personal-research/1.0'}),timeout=5) as response:
                row['status']=response.status;raw=response.read(bound+1)
            if len(raw)>bound:raise ValueError('registered response size exceeded')
            with (out/name).open('xb') as stream:stream.write(raw)
            row.update(raw_file=name,bytes=len(raw),sha256=r.sha(raw))
        except HTTPError as error:
            raw=error.read(min(bound,1048576)+1);row.update(status=error.code,error=str(error))
            if len(raw)<=min(bound,1048576):
                filename=name+'-error.bin';(out/filename).write_bytes(raw)
                row.update(raw_file=filename,bytes=len(raw),sha256=r.sha(raw))
        except (OSError,ValueError) as error:row['error']=type(error).__name__+': '+str(error)
        row['receipt_ms']=int(time.time()*1000);receipts.append(row)
    new_json(out/'receipts.json',dict(format='btc-loop-public-v1',source=identity,receipts=receipts,
        requests=len(receipts),retries=0,private_requests=0,orders=0,spec_sha256=r.sha(SPEC.read_bytes())))
    return receipts


def market_cache(spot_root,coin_root,cache):
    """Market only; never account state. Fixed raw metadata binds parsed bytes."""
    groups={'spot':sorted((spot_root/'klines/1d').glob('**/BTCUSDT-*.zip')),
            'coin4':sorted((coin_root/'klines/4h').glob('**/BTCUSDT-*.zip')),
            'mark':sorted((coin_root/'mark/1m').glob('BTCUSDT-1m-202[02]-0[123].zip'))}
    groups['mark']=[p for p in groups['mark'] if p.name[11:18] in ('2020-01','2020-02','2020-03','2022-01','2022-02','2022-03')]
    if not groups['spot'] or not groups['coin4']:raise ValueError('original small market inputs missing')
    fingerprints=[]
    for paths in groups.values():
        for path in paths:
            checksum=Path(str(path)+'.CHECKSUM')
            for candidate in (path,checksum):
                stat=candidate.stat();fingerprints.append([str(candidate.resolve()),stat.st_size,stat.st_mtime_ns,stat.st_ino])
    receipt=Path(str(cache)+'.receipt.json')
    parser_sha=r.sha(Path(__file__).read_bytes()+Path(f.__file__).read_bytes()+Path(r.__file__).read_bytes())
    if cache.exists() and receipt.exists():
        saved=json.loads(receipt.read_text());raw=cache.read_bytes()
        if saved['fingerprints']==fingerprints and saved['parser_sha256']==parser_sha and saved['parsed_sha256']==r.sha(raw):
            packet=json.loads(gzip.decompress(raw));return decode_market(packet),saved
        raise ValueError('immutable market cache dependency changed; use a new explicit cache path')
    inputs=[];data={}
    for name,paths in groups.items():
        bars={};interval=60000 if name=='mark' else r.DAY if name=='spot' else f.FOUR
        for path in paths:
            raw=path.read_bytes();digest=r.sha(raw)
            if Path(str(path)+'.CHECKSUM').read_text().split()[0]!=digest:raise ValueError('selected market checksum mismatch')
            inputs.append(dict(path=str(path),sha256=digest,bytes=len(raw)))
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                members=[n for n in z.namelist() if not n.endswith('/')]
                if len(members)!=1:raise ValueError('ambiguous market archive')
                for line in z.read(members[0]).decode().splitlines():
                    row=line.split(',')
                    if not row[0].isdigit():continue
                    if name!='mark':stamp,bar=f.kline(row,interval)
                    else:
                        stamp=f.millis(row[0]);bar=tuple(map(r.number,row[1:5]))
                        if stamp%interval or f.millis(row[6])!=stamp+interval-1 or min(bar)<=0 or not bar[2]<=min(bar[0],bar[3])<=max(bar[0],bar[3])<=bar[1]:
                            raise ValueError('invalid completed mark minute')
                    if stamp in bars and bars[stamp]!=bar:raise ValueError('conflicting completed bars')
                    bars[stamp]=bar
        data[name]=bars
    packet=r.serial(data);packed=gzip.compress(json.dumps(packet,separators=(',',':')).encode(),mtime=0)
    cache.parent.mkdir(parents=True,exist_ok=True)
    with cache.open('xb') as stream:stream.write(packed)
    saved=dict(format='btc-loop-immutable-market-cache-v1',fingerprints=fingerprints,parser_sha256=parser_sha,
        parsed_sha256=r.sha(packed),inputs=inputs,large_vault_scans=0,accounts_shared=False)
    new_json(receipt,saved);return data,saved


def decode_market(packet):return {name:{int(t):tuple(map(D,row)) for t,row in rows.items()} for name,rows in packet.items()}


def calendar(folder):
    packet=json.loads((folder/'receipts.json').read_text());receipt=next(x for x in packet['receipts'] if x['name']=='cpi.ics')
    if receipt.get('status')!=200 or not receipt.get('raw_file'):return dict(status='SOURCE_UNAVAILABLE',events=[],receipt=receipt)
    raw=(folder/receipt['raw_file']).read_bytes()
    if r.sha(raw)!=receipt['sha256']:raise ValueError('calendar bytes changed')
    text=raw.decode().replace('\r\n ','').replace('\n ','');events=[]
    for block in text.split('BEGIN:VEVENT')[1:]:
        fields=dict(line.split(':',1) for line in block.split('END:VEVENT')[0].splitlines() if ':' in line)
        if any(key.startswith('RRULE') for key in fields):raise ValueError('unsupported recurring calendar')
        keys=[key for key in fields if key.startswith('DTSTART')]
        if len(keys)!=1:raise ValueError('missing announcement time')
        key=keys[0];value=fields[key];zone=timezone.utc if value.endswith('Z') else ZoneInfo('America/New_York')
        if 'TZID=' in key:zone=ZoneInfo(key.split('TZID=',1)[1])
        stamp=int(datetime.strptime(value.rstrip('Z'),'%Y%m%dT%H%M%S').replace(tzinfo=zone).timestamp()*1000)
        summary=fields.get('SUMMARY','')
        if 'consumer price' not in summary.lower() and 'cpi' not in summary.lower():continue
        # Today's calendar cannot establish a past preannouncement vintage.
        if stamp<=receipt['receipt_ms']:continue
        events.append(dict(at_ms=stamp,known_ms=receipt['receipt_ms'],summary=summary,source_sha256=receipt['sha256']))
    return dict(status='FORWARD_KNOWN_CALENDAR' if events else 'WAIT_FUTURE_KNOWN_EVENTS',events=events,receipt=receipt,
                old_event_availability_proven=False)


def spot_minutes(folder):
    packet=json.loads((folder/'receipts.json').read_text());receipts={row['name']:row for row in packet['receipts']};result={};bindings=[]
    for month in ('2020-01','2022-01'):
        name=f'BTCUSDT-1m-{month}.zip';ziprow=receipts[name];check=receipts[name+'.CHECKSUM']
        if ziprow.get('status')!=200 or check.get('status')!=200:continue
        raw=(folder/ziprow['raw_file']).read_bytes();checksum=(folder/check['raw_file']).read_bytes()
        if r.sha(raw)!=ziprow['sha256'] or r.sha(checksum)!=check['sha256'] or checksum.decode().split()[0]!=r.sha(raw):
            raise ValueError('public selected minute provenance changed')
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            for line in z.read(z.namelist()[0]).decode().splitlines():
                parts=line.split(',')
                if parts[0].isdigit():
                    stamp,bar=f.kline(parts,60000);result[stamp]=bar
        bindings.append(dict(month=month,zip_sha256=ziprow['sha256'],receipt_ms=ziprow['receipt_ms']))
    return result,bindings


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);args=p.parse_args(argv)
    result=capture(args.out);print(json.dumps(dict(requests=len(result),status=[x['status'] for x in result],orders=0)))


if __name__=='__main__':main()
