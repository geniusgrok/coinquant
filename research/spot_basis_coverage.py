"""File-backed official SPOT input acquisition, checksums before parsing."""
import argparse,concurrent.futures,hashlib,json,zipfile,io,csv,calendar
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import urlopen

def acquire(output):
    output.mkdir(parents=True,exist_ok=True)
    def get(month):
        name=f'BTCUSDT-1h-{month}.zip';url=f'https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1h/{name}'
        receipt=output/(name+'.CHECKSUM')
        if not receipt.exists():
            with urlopen(url+'.CHECKSUM',timeout=30) as response:raw=response.read(1024)
            receipt.write_bytes(raw)
        fields=receipt.read_text().strip().split()
        if len(fields)!=2 or fields[1]!=name or len(fields[0])!=64:raise ValueError('invalid checksum receipt')
        p=output/name
        if not p.exists():
            tmp=p.with_suffix('.partial')
            with urlopen(url,timeout=30) as response,tmp.open('wb') as f:
                while block:=response.read(65536):f.write(block)
            if hashlib.sha256(tmp.read_bytes()).hexdigest()!=fields[0]:raise ValueError('download checksum mismatch')
            tmp.replace(p)
        raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==fields[0]
        with zipfile.ZipFile(p) as z:rows=list(csv.reader(io.StringIO(z.read(z.namelist()[0]).decode())))
        times=[int(r[0]) for r in rows]
        year,m=map(int,month.split('-'));start=int(datetime(year,m,1,tzinfo=timezone.utc).timestamp()*1000)
        expected=set(range(start,start+calendar.monthrange(year,m)[1]*86400000,3600000))
        if len(times)!=len(set(times)) or not set(times)<=expected:raise ValueError('invalid spot clock')
        return dict(file=name,url=url,bytes=len(raw),sha256=fields[0],rows=len(rows),first=times[0],last=times[-1],missing_hours=sorted(expected-set(times)))
    months=[f'{year}-{month:02}' for year in range(2020,2024) for month in range(1,13)]
    receipts=[];errors=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(get,m):m for m in months}
        for f in concurrent.futures.as_completed(futures):
            try:receipts.append(f.result())
            except Exception as e:errors.append(dict(month=futures[f],error=type(e).__name__,detail=str(e)))
    receipts.sort(key=lambda r:r['file'])
    if not errors:
        assert sum(r['rows']+len(r['missing_hours']) for r in receipts)==35064
        assert all(a['last']+3600000==b['first'] for a,b in zip(receipts,receipts[1:]))
    result=dict(complete=not errors,continuous=not errors and not any(r['missing_hours'] for r in receipts),records=receipts,errors=errors,scope='2020-2023 development only')
    (output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'complete':not errors,'months':len(receipts),'errors':errors}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();acquire(a.output)
