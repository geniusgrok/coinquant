"""Descriptive risk from saved independent wallets; never reruns a session or scales a curve."""
import argparse
from decimal import Decimal as D
import gzip
import hashlib
import json
from pathlib import Path

DAY=86400000


def risk(equities,benchmark):
    points=sorted(equities.items());returns=[];peak=None;mdd=0
    for t,v in points:
        peak=max(v,peak or v);mdd=max(mdd,1-v/peak)
    for (a,v),(b,w) in zip(points,points[1:]):
        if b-a==DAY and a in benchmark and b in benchmark and v>0:
            returns.append((w/v-1,benchmark[b]/benchmark[a]-1))
    if len(returns)<2:return dict(matched_daily_returns=len(returns),mdd_matched_daily=mdd)
    def regression(rows):
        if len(rows)<2:return None,None
        y=sum(a for a,b in rows)/len(rows);x=sum(b for a,b in rows)/len(rows)
        variance=sum((b-x)**2 for a,b in rows)
        beta=sum((a-y)*(b-x) for a,b in rows)/variance if variance else None
        return beta,365*(y-beta*x) if beta is not None else None
    beta,alpha=regression(returns);down,_=regression([(a,b) for a,b in returns if b<0])
    mean=sum(a for a,b in returns)/len(returns)
    vol=(365*sum((a-mean)**2 for a,b in returns)/(len(returns)-1))**.5
    up=[(a,b) for a,b in returns if b>0];loss=[(a,b) for a,b in returns if b<0]
    return dict(matched_daily_returns=len(returns),mdd_matched_daily=mdd,
        beta_to_btc_usdt=beta,beta_on_btc_down_days=down,annual_arithmetic_intercept=alpha,
        realized_vol_annual=vol,up_capture=sum(a for a,b in up)/sum(b for a,b in up) if up else None,
        down_capture=sum(a for a,b in loss)/sum(b for a,b in loss) if loss else None,
        interpretation='Descriptive contaminated historical sample; intercept is not validated alpha/OOS return')


def daily(row,kind):
    rows=row['daily'].values() if isinstance(row['daily'],dict) else row['daily']
    result={}
    for r in rows:
        t=r.get('timestamp_ms',r.get('stamp_ms'))
        if t%DAY==0:result[t]={k:float(r[k]) for k in ('equity_usdt','equity_cny')}
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--cache',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('preserve old report')
    packet=json.loads(gzip.decompress(a.cache.read_bytes()))
    bench={int(t)+DAY:float(v[3]) for t,v in packet['spot'].items()};receipts=[];cases={}
    for kind,folders in [('spot',('spot-accounts','spot-baseline-recovery')),('coin',('coin-accounts-recovery',))]:
        for folder in folders:
            for path in sorted((a.root/folder).glob('20*.json')):
                r=json.loads(path.read_text())
                if not r.get('complete_finite'):continue
                cases[kind+':'+r['case']]=r
                receipts.append(dict(kind=kind,path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),source=r['identity']))
    recovered=a.root/'coin-terminal-recovery.json';r=json.loads(recovered.read_text())
    cases['coin:'+r['case']]=r;receipts.append(dict(kind='coin',path=str(recovered),sha256=hashlib.sha256(recovered.read_bytes()).hexdigest(),source=r['identity']))
    diagnostics={};table=[];series={}
    for key,row in cases.items():
        kind=key.split(':')[0];values=daily(row,kind);series[key]=values
        diagnostics[key]=risk({t:v['equity_usdt'] for t,v in values.items()},bench)
        table.append(dict(case=key,return_cny=float(row['return_cny']),mdd_path_proxy=float(row['mdd']),
            fills=len(row.get('fills',row.get('trades',[]))),session_count=row['session_count'],audit_passed=row['audit']['passed']))
    joint={}
    for name in sorted({k.split(':',1)[1] for k in cases}):
        x=series.get('spot:'+name,{});y=series.get('coin:'+name,{})
        # Sum real ledgers of two actual10000-CNY wallets; no5000 curve scaling.
        points={t:x[t]['equity_cny']+y[t]['equity_cny'] for t in x.keys()&y.keys()}
        joint[name]=risk({t:x[t]['equity_usdt']+y[t]['equity_usdt'] for t in points},bench)
        peak=None;cny_mdd=0
        for t,value in sorted(points.items()):
            peak=max(value,peak or value);cny_mdd=max(cny_mdd,1-value/peak)
        joint[name]['mdd_cny_matched_daily']=cny_mdd
        joint[name]['regression_currency']='USDT equity versus BTCUSDT; CNY drawdown separately' 
        joint[name]['funding_basis']='actual10000CNY+actual10000CNY independent wallets, matched real midnight ledger points'
    out=dict(cases=table,diagnostics=diagnostics,joint=joint,receipts=receipts,
        complete_finite_count=len(cases),actual_account_sessions=sum(r['session_count'] for r in cases.values()),
        qualification='NOT_QUALIFIED',economic_goals='new full-history CAGR unknown; old goals historical reference only',
        mdd_warning='Spot OHLC and Coin minute envelope proxies differ; matched daily joint MDD is not continuous/native risk')
    a.out.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(complete_wallets=len(cases),sessions=out['actual_account_sessions'],audits=all(r['audit']['passed'] for r in cases.values()))))

if __name__=='__main__':main()
