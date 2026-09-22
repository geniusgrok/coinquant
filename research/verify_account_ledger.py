"""Independent cash ledger verification of already-saved account trajectories."""
import argparse,csv,gzip,json,hashlib
from decimal import Decimal as D
from pathlib import Path


def verify(path):
    with gzip.open(path/'equity.csv.gz','rt') as f:
        first=next(csv.DictReader(f));wallet=D(first['equity_usdt'])
    with gzip.open(path/'orders.csv.gz','rt') as f:orders=iter(list(csv.DictReader(f)));pending=next(orders,None)
    q=entry=fees=funding=D(0);count=0;worst=D(0)
    with gzip.open(path/'equity.csv.gz','rt') as f:
        for r in csv.DictReader(f):
            if r['event']!='close':continue
            while pending is not None and int(pending['time'])<int(r['time']):
                a=pending;amount=D(a['quantity_btc']);price=D(a['price_or_mark']);event=a['event']
                if event=='entry':
                    assert q==0
                    q=amount;entry=price;cost=abs(amount)*price*D('.00075');wallet-=cost;fees+=cost
                elif event=='rebalance_add':
                    assert amount*q>0
                    entry=(abs(q)*entry+abs(amount)*price)/abs(q+amount)
                    q+=amount;cost=abs(amount)*price*D('.00075');wallet-=cost;fees+=cost
                elif event=='funding_adverse_bound':
                    cost=amount*price*D(a['funding_rate']);wallet-=cost;funding+=cost
                else:
                    assert amount*q>0 and abs(amount)<=abs(q)
                    cost=abs(amount)*price*D('.00075');wallet+=amount*(price-entry)-cost;fees+=cost;q-=amount
                    if not q:entry=D(0)
                assert q==D(a['quantity_after'])
                pending=next(orders,None)
            error=abs(wallet+q*(D(r['mark'])-entry)-D(r['equity_usdt']));worst=max(worst,error)
            assert q==D(r['quantity']) and error<=D('1e-18'),r
            assert abs(fees-D(r['fees']))<=D('1e-18') and abs(funding-D(r['funding']))<=D('1e-18'),r
            count+=1
    return dict(close_points=count,max_equity_error_usdt=str(worst),fees=str(fees),funding=str(funding),
        input_sha256={name:hashlib.sha256((path/name).read_bytes()).hexdigest() for name in ('orders.csv.gz','equity.csv.gz')})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--path',type=Path,action='append',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();result={str(path):verify(path) for path in a.path};a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
