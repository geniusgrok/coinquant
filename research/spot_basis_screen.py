"""Causal cost-scale screen for new spot/perpetual information, no account."""
import argparse,csv,io,json,zipfile,hashlib
from pathlib import Path
from decimal import Decimal as D
from research.persistent_hold_replay import inputs,HOUR
from pancakequant.research import invocations,spec,timestamp

def run(native,spot,output):
    manifest=json.loads((spot/'manifest.json').read_text())
    if not manifest['complete']:raise ValueError('spot coverage incomplete')
    prices={};rejected=[]
    for item in manifest['records']:
        raw=(spot/item['file']).read_bytes();assert hashlib.sha256(raw).hexdigest()==item['sha256']
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            for row in csv.reader(io.StringIO(z.read(z.namelist()[0]).decode())):
                t=int(row[0]);assert t not in prices
                if int(row[6])!=t+HOUR-1:
                    rejected.append(dict(file=item['file'],open=t,close=int(row[6]),reason='nonstandard_hour_close'));continue
                prices[t]=D(row[4])
    series,_,_,identity=inputs(native,Path('evidence/binance-boundary-20260921'),Path('evidence/binance-mark-repair-20260921'))
    future=series['klines'];assert set(prices)<=set(future)
    limit=D('.0037');signals={};episodes=[];active=None;excess=0;max_basis=D(0)
    for t in sorted(future):
        if t not in prices:
            active=None;continue
        basis=D(future[t][4])/prices[t]-1
        max_basis=max(max_basis,abs(basis));side=-1 if basis>limit else 1 if basis < -limit else 0
        if side:
            excess+=1
            if active is None or active['side']!=side:
                active=dict(known_at=t+HOUR,side=side,hours=0);episodes.append(active)
            active['hours']+=1;signals[t+HOUR]=dict(event=active['known_at'],side=side,basis=str(basis))
        else:active=None
    end=timestamp(spec()['development_end']);triggers=[t for t in invocations(spec()) if t<end]
    selected=[];used=set()
    for t in triggers:
        signal=signals.get(t)
        if signal and signal['event'] not in used:
            used.add(signal['event']);selected.append(dict(time=t,**signal))
    result=dict(qualification='INFORMATION_SCREEN_NOT_ACCOUNT',spot_manifest=manifest,future_input_identity=identity,
                completed_hours=len(prices),missing_or_rejected_spot_hours=len(future)-len(prices),rejected_candles=rejected,cost_scale=str(limit),excess_hours=excess,episodes=episodes,
                sparse_visible_unique_episodes=selected,max_absolute_close_basis=str(max_basis),
                limitations=['Close-to-close relative price is not simultaneous executable bid/ask','Convergence is not guaranteed; unhedged BTC market risk remains','No account returns, protection, funding, margin or liquidation inferred','Only development used'])
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k in ('completed_hours','cost_scale','excess_hours','max_absolute_close_basis','sparse_visible_unique_episodes')}))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('native','spot','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();run(a.native,a.spot,a.output)
