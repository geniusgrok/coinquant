"""Read-only attribution of saved payoff comparison traces; no new candidate."""
import csv
import gzip
import json
from pathlib import Path
from decimal import Decimal as D
from datetime import datetime,timezone
from research.verify_account_ledger import verify
from pancakequant.research import spec


def audit(path):
    annual={};max_margin=D(0);max_exposure=D(0);peak=D(spec()['initial_cny'])/D(spec()['cny_per_usd']);peak_time=None;longest=0
    with gzip.open(path/'equity.csv.gz','rt') as f:
        for r in csv.DictReader(f):
            t=int(r['time']);eq=D(r['equity_usdt']);q=D(r['quantity']);mark=D(r['mark'])
            if eq>0:
                max_margin=max(max_margin,D(r['margin'])/eq);max_exposure=max(max_exposure,abs(q)*mark/eq)
            if eq>=peak:peak=eq;peak_time=t
            if peak_time is not None:longest=max(longest,t-peak_time)
            if r['event']=='close':annual[datetime.fromtimestamp((t-1)/1000,timezone.utc).year]=eq
    start=D(spec()['initial_cny'])/D(spec()['cny_per_usd']);yearly={}
    for year,end in sorted(annual.items()):yearly[year]=dict(return_fraction=str(end/start-1),end_equity_usdt=str(end));start=end
    trades=[];current=None
    with gzip.open(path/'orders.csv.gz','rt') as f:
        for r in csv.DictReader(f):
            q=D(r['quantity_btc']);p=D(r['price_or_mark'])
            if r['event']=='entry':current=dict(t=int(r['time']),q=q,p=p,net=-q*p*D('.00075'))
            elif r['event']=='funding_adverse_bound':
                target=current if current is not None else trades[-1]
                # Offset funding can be charged conservatively after the close row.
                target['net']-=q*p*D(r['funding_rate'])
            else:
                current['net']+=q*(p-current['p'])-q*p*D('.00075')
                current.update(exit=int(r['time']),event=r['event']);trades.append(current);current=None
    profits=[r['net'] for r in trades];total=sum(profits,D(0));gross=sum((v for v in profits if v>0),D(0))
    return dict(ledger=verify(path),annual=yearly,max_recorded_margin_equity=str(max_margin),max_recorded_exposure=str(max_exposure),
        longest_underwater_days=longest/86400000,closed_trades=len(trades),open_trade=current is not None,
        max_profit=str(max(profits)),max_loss=str(min(profits)),net_closed_profit=str(total),
        largest_profit_fraction_of_gross=str(max(profits)/gross) if gross else None,
        largest_profit_fraction_of_net=str(max(profits)/total) if total else None,
        trades=[{k:str(v) if isinstance(v,D) else v for k,v in r.items()} for r in trades])

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args()
    result={name:audit(a.root/name) for name in ('B0','B1')}
    (a.root/'ACCOUNT_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:{x:v for x,v in r.items() if x not in ('trades','ledger')} for k,r in result.items()},indent=2))
