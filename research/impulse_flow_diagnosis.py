"""Development-only new information screen; no fitted threshold or account PnL."""
import argparse,csv,hashlib,io,json,zipfile
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path

def run(native,paired,output):
    rows={};identity=[]
    for year in range(2020,2024):
        for month in range(1,13):
            p=native/f'monthly/klines/BTCUSDT/1h/BTCUSDT-1h-{year}-{month:02}.zip'
            identity.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
            with zipfile.ZipFile(p) as z:
                for r in csv.reader(io.StringIO(z.read(z.namelist()[0]).decode())):
                    if not r[0].isdigit():continue
                    t=int(r[0]);total,buy=D(r[7]),D(r[10])
                    assert t not in rows and int(r[6])==t+3599999 and total>0 and 0<=buy<=total
                    rows[t]=(total,buy)
    assert len(rows)==35064 and max(rows)-min(rows)==(len(rows)-1)*3600000
    groups=defaultdict(list);records=[]
    for pair in json.loads(paired.read_text()):
        for mode in ('normal','sparse'):
            trade=pair.get(mode)
            if not trade or trade.get('next24h_diagnostic_return') is None:continue
            times=[trade['entry']-i*3600000 for i in range(1,5)]
            if any(t not in rows for t in times):continue
            total=sum(rows[t][0] for t in times);buy=sum(rows[t][1] for t in times)
            score=D(trade['side'])*(2*buy/total-1)
            outcome=D(trade['next24h_diagnostic_return'])
            key=f"{mode}:{trade['side']}:{'aligned' if score>0 else 'opposed'}"
            groups[key].append(outcome)
            records.append(dict(event=pair['event']['identity'],mode=mode,latest_available=max(times)+3600000,
                                entry=trade['entry'],aligned_flow=str(score),net24h=str(outcome)))
    result=dict(qualification='DESCRIPTIVE_ONLY',coverage_hours=len(rows),input_identity=identity,
                groups={k:dict(n=len(v),mean_net24h=str(sum(v)/len(v)),positive=sum(x>0 for x in v)) for k,v in groups.items()},
                records=records,limitations=['Small dependent selected events, not independent validation','No account filter or causal treatment effect','2024+ deliberately not screened'])
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['groups'],indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('native','paired','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();run(a.native,a.paired,a.output)
