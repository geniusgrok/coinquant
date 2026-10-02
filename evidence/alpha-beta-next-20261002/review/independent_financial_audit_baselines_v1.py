"""Independent read-only evidence audit. Writes only explicitly named external report.
No producer imports, replays, network, cache mutation, or account access.
"""
import argparse,bisect,csv,gzip,hashlib,io,json,math,statistics,zipfile
from pathlib import Path
from decimal import Decimal as D, getcontext
from datetime import datetime,timezone
import numpy as np
getcontext().prec=40
START=1577836800000; END=1789862400000; DAY=86400000; CUT=1640995200000
ROOT=Path('/workspace/btc-alpha-beta-next')
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):
 with (gzip.open(p,'rt') if str(p).endswith('.gz') else open(p)) as f:return json.load(f)
def ziprows(p):
 with zipfile.ZipFile(p) as z:
  for name in z.namelist():
   with z.open(name) as f:
    for r in csv.reader(io.TextIOWrapper(f)):
     if r and r[0].isdigit(): yield r
FXPATH=ROOT/'starquant/data/usdcny_frankfurter.json'
fxdata=read(FXPATH)['rates'];fxdays=sorted(fxdata)
def fx(t):
 i=bisect.bisect_left(fxdays,datetime.fromtimestamp(t/1000,timezone.utc).date().isoformat())-1
 return D(str(fxdata[fxdays[i]]['CNY'])) if i>=0 else D('6.9615')
def bars():
 out={}
 for p in sorted(Path('/tmp/spotquant-market/klines/1d').rglob('*.zip')):
  for r in ziprows(p):
   t=int(r[0]);t=t//1000 if t>10**14 else t
   if START<=t<END:
    value=[D(x) for x in r[1:5]]
    assert t not in out or out[t]==value
    out[t]=value
 assert sorted(out)==list(range(START,END,DAY))
 return out
BARS=bars();DAYS=sorted(BARS)
def stats(values,initial,market):
 v=np.asarray(values,float); ret=v/np.r_[initial,v[:-1]]-1; x=np.asarray(market,float)
 X=np.column_stack([np.ones(len(x)),x]); inv=np.linalg.inv(X.T@X); coef=inv@X.T@ret
 score=X*(ret-X@coef)[:,None]; meat=score.T@score
 for lag in range(1,8):
  cross=score[lag:].T@score[:-lag]; meat+=(1-lag/8)*(cross+cross.T)
 covariance=inv@meat@inv*len(x)/(len(x)-2);se=math.sqrt(max(0,covariance[0,0]))
 peak=np.maximum.accumulate(np.r_[initial,v])[1:];dd=1-v/peak
 capture={}
 for name,mask in [('up',x>0),('down',x<0)]:
  xx=x[mask];yy=ret[mask]
  capture[name]={'days':int(mask.sum()),'arithmetic_capture':float(yy.sum()/xx.sum()),'beta':float(np.cov(xx,yy,ddof=1)[0,1]/np.var(xx,ddof=1))}
 return {'days':len(x),'beta':float(coef[1]),'alpha_daily':float(coef[0]),'hac7_se_daily':se,'alpha_annual_arithmetic':float(coef[0]*365.25),'alpha_annual_normal95':[float((coef[0]-1.96*se)*365.25),float((coef[0]+1.96*se)*365.25)],'annual_vol':float(ret.std(ddof=1)*math.sqrt(365.25)),'es5_loss':float(-np.sort(ret)[:math.ceil(.05*len(ret))].mean()),'mdd_daily':float(dd.max()),'cagr':float((v[-1]/initial)**(365.25/len(v))-1),'capture':capture},ret

def curves(row,kind):
 raw=list(row['daily'].values()) if kind=='spot' else row['daily'];tk='timestamp_ms' if kind=='spot' else 'stamp_ms'
 raw=sorted(raw,key=lambda r:r[tk]);idx=0;initial=D(row['initial_cny'])/fx(START)*D('.999');last=None;usd=[];cny=[]
 for day in DAYS:
  while idx<len(raw) and raw[idx][tk]<=day+DAY:last=raw[idx];idx+=1
  assert last is not None
  q=D(last['btc' if kind=='spot' else 'quantity_btc']);assert not q or last[tk]==day+DAY
  u=D(last['equity_usdt']) if q else D(last['cash_usdt' if kind=='spot' else 'wallet_usdt'])
  usd.append(float(u));cny.append(float(u*fx(day+DAY)*D('.999')))
 close=np.array([float(BARS[d][3]) for d in DAYS]);initialprice=float(BARS[START][0]);btc=close/np.r_[initialprice,close[:-1]]-1
 cp=close*np.array([float(fx(d+DAY)) for d in DAYS]);cb=cp/np.r_[initialprice*float(fx(START)),cp[:-1]]-1
 fullu,ret=stats(usd,float(initial),btc);fullc,_=stats(cny,float(row['initial_cny']),cb)
 cut=DAYS.index(CUT);vu,_=stats(usd[cut:],usd[cut-1],btc[cut:]);vc,_=stats(cny[cut:],cny[cut-1],cb[cut:])
 years={}
 for d,r in zip(DAYS,ret):
  year=str(datetime.fromtimestamp(d/1000,timezone.utc).year);years[year]=years.get(year,0)+math.log1p(float(r))
 return {'full_usdt':fullu,'full_cny':fullc,'validation_usdt':vu,'validation_cny':vc,'calendar_usdt_log_returns':years,'reported_continuous_proxy_mdd':row['mdd'],'final_cny_delta':str(D(str(cny[-1]))-D(row['final_cny']))}

def spot(row):
 cash=D(row['initial_cny'])/fx(START)*D('.999');qty=D(0);fees=D(0);casherr=qtyerr=eqerr=fxerr=D(0);fills=sorted(row['fills'],key=lambda r:(r['time'],r['id']));i=0
 assert len({r['id'] for r in fills})==len(fills)
 for point in sorted(row['daily'].values(),key=lambda r:r['timestamp_ms']):
  while i<len(fills) and fills[i]['time']<=point['timestamp_ms']:
   f=fills[i]; assert START<=f['time']<END; q=D(f['qty']);quote=D(f['quote']);fee=D(f['commission']);a=f['commission_asset'];assert a in ('BTC','USDT')
   cash+=(-quote if f['buyer'] else quote)-(fee if a=='USDT' else 0);qty+=(q if f['buyer'] else -q)-(fee if a=='BTC' else 0);fees+=fee*(D(f['price']) if a=='BTC' else 1);i+=1
  casherr=max(casherr,abs(cash-D(point['cash_usdt'])));qtyerr=max(qtyerr,abs(qty-D(point['btc'])));u=cash+qty*D(point['price_usdt']);eqerr=max(eqerr,abs(u-D(point['equity_usdt'])));fxerr=max(fxerr,abs(u*fx(point['timestamp_ms'])*D('.999')-D(point['equity_cny'])))
 assert i==len(fills)
 return {'fills':len(fills),'cash':str(cash),'btc':str(qty),'fees_usdt':str(fees),'fees_vs_audit_delta':str(fees-D(row['audit']['fees_usdt'])),'max_daily_cash_delta':str(casherr),'max_daily_btc_delta':str(qtyerr),'max_daily_usdt_equity_delta':str(eqerr),'max_daily_cny_delta':str(fxerr),'terminal_cash_delta':str(cash-D(row['cash_usdt'])),'terminal_btc_delta':str(qty-D(row['btc']))}

def funding_inputs(rows):
 wanted={int(r['time']) for row in rows for r in row['funding_ledger'] if r['incomeType']=='FUNDING_FEE'};rates={};marks={};used={}
 for p in sorted(Path('/tmp/coinquant-market/funding').glob('*.zip')):
  used[str(p)]=sha(p)
  for r in ziprows(p):rates[int(r[0])]=D(r[-1])
 minutes={t//60000*60000-60000 for t in wanted};months={datetime.fromtimestamp(t/1000,timezone.utc).strftime('%Y-%m') for t in minutes}
 for p in sorted(Path('/tmp/coinquant-market/mark/1m').rglob('*.zip')):
  if not any(m in p.name for m in months):continue
  used[str(p)]=sha(p)
  for r in ziprows(p):
   t=int(r[0]);t=t//1000 if t>10**14 else t
   if t in minutes:
    mark=D(r[4]);assert t not in marks or marks[t]==mark;marks[t]=mark
 return rates,marks,used

def perp(row,rates,marks):
 q=entry=realized=fees=D(0);trades=sorted(row['trades'],key=lambda r:(r['time'],r['id']));history=[];rate=D('.00075')*(D('1.5') if row['scenario']=='fees-x1.5' else 1)
 assert len({t['id'] for t in trades})==len(trades)
 for t in trades:
  assert START<=t['time']<END;qty=D(t['qty']);p=D(t['price']);change=qty if t['side']=='BUY' else -qty;fees+=qty*p*rate
  if q*change>=0:entry=(abs(q)*entry+qty*p)/(abs(q)+qty)
  else:
   realized+=min(qty,abs(q))*(p-entry)*(1 if q>0 else -1)
   if qty>abs(q):entry=p
  q+=change
  if not q:entry=D(0)
  history.append((t['time'],q,entry,realized,fees))
 totals={};max_fund=D(0);fundcount=0;times=[h[0] for h in history]
 for x in row['funding_ledger']:
  assert START<=x['time']<END;typ=x['incomeType'];assert typ in ('REALIZED_PNL','COMMISSION','FUNDING_FEE','INSURANCE_CLEAR');totals[typ]=totals.get(typ,D(0))+D(x['income'])
  if typ=='FUNDING_FEE':
   i=bisect.bisect_left(times,x['time'])-1;quantity=history[i][1] if i>=0 else D(0);t=x['time'];pay=-quantity*rates[t]*marks[t//60000*60000-60000];max_fund=max(max_fund,abs(pay-D(x['income'])));fundcount+=1
 expected_funding={t for t in rates if START<t<END and bisect.bisect_left(times,t)>0 and history[bisect.bisect_left(times,t)-1][1]!=0};recorded_funding={x['time'] for x in row['funding_ledger'] if x['incomeType']=='FUNDING_FEE'}
 assert expected_funding==recorded_funding, ('funding event inventory mismatch',sorted(expected_funding-recorded_funding)[:10],sorted(recorded_funding-expected_funding)[:10])
 initial=D(row['initial_cny'])/fx(START)*D('.999');wallet=initial+realized-fees+totals.get('FUNDING_FEE',D(0))+totals.get('INSURANCE_CLEAR',D(0));equity=wallet+q*(D(row['final_mark'])-entry)
 maxwallet=maxquantity=maxequity=D(0)
 income=sorted(row['funding_ledger'],key=lambda r:r['time']);ii=0;dailywallet=initial
 for point in row['daily']:
  stamp=point['stamp_ms'];i=(bisect.bisect_left(times,stamp) if stamp%DAY==0 else bisect.bisect_right(times,stamp))-1;quantity,ep=(history[i][1:3] if i>=0 else (D(0),D(0)))
  while ii<len(income) and (income[ii]['time']<stamp or income[ii]['time']==stamp and (stamp%DAY!=0 or income[ii]['incomeType']=='FUNDING_FEE')):dailywallet+=D(income[ii]['income']);ii+=1
  maxwallet=max(maxwallet,abs(dailywallet-D(point['wallet_usdt'])));maxquantity=max(maxquantity,abs(quantity-D(point['quantity_btc'])));maxequity=max(maxequity,abs(dailywallet+quantity*(D(point['mark_usdt'])-ep)-D(point['equity_usdt'])))
 return {'trades':len(trades),'funding_events':fundcount,'realized_wac_pnl':str(realized),'commission':str(fees),'funding_paid':str(-totals.get('FUNDING_FEE',D(0))),'realized_vs_income_delta':str(realized-totals.get('REALIZED_PNL',D(0))),'fees_vs_income_delta':str(fees+totals.get('COMMISSION',D(0))),'funding_public_max_delta':str(max_fund),'position_delta':str(q-D(row['position'])),'terminal_usdt_delta':str(equity-D(row['final_usdt'])),'terminal_cny_delta':str(equity*fx(END)*D('.999')-D(row['final_cny'])),'max_daily_wallet_delta':str(maxwallet),'max_daily_quantity_delta':str(maxquantity),'max_daily_equity_delta':str(maxequity)}

def normalize(row):
 ids={}
 for e in row['client_events']:ids.setdefault(e['client_id'],f'client-{len(ids)}')
 for a in row['allocations']:ids.setdefault(a[0],f'client-{len(ids)}')
 def walk(v):
  if isinstance(v,dict):return {ids.get(k,k):walk(x) for k,x in v.items() if k!='archive_backup_sha256'}
  if isinstance(v,list):return [walk(x) for x in v]
  return ids.get(v,v) if isinstance(v,str) else v
 out=dict(row);out['allocations']=[[a,json.loads(b),c,json.loads(d)] for a,b,c,d in row['allocations']];return walk(out)

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();report={'method':'Independent Decimal40 ledger and NumPy matrix OLS/HAC7; no producer imports','fx_sha256':sha(FXPATH),'scope':'Provisional: completed Spot baseline four scenes and immutable original Coin incumbent four scenes only','spot':{},'coin_original':{}}
 original=ROOT/'spotquant/evidence/complete-delivery-20261001/spot-consensus-corrected.json';new=Path('/workspace/scratch/alpha-beta-next/spot-singletons/consensus.json.gz');old=read(original);bundle=read(new);report['identities']={str(original):sha(original),str(new):sha(new)};report['spot_source']=bundle['source']
 for name,row in bundle['results'].items():
  norm=normalize(row);ref=normalize(old['results'][name]);diff=[k for k,v in ref.items() if norm.get(k)!=v];report['spot'][name]={'complete':row['complete'],'original_field_differences':diff,'sessions':len(row['sessions']),'all_archive_claims_true':all(s['archive_verified'] and len(s['archive_backup_sha256'])==64 for s in row['sessions']),'ledger':spot(row),'statistics':curves(row,'spot')}
 del bundle,old
 original=ROOT/'coinquant/evidence/complete-delivery-20261001/perp-exclusive-accounts.json';bundle=read(original);report['identities'][str(original)]=sha(original);rows=list(bundle['results']['incumbent'].values());rates,marks,used=funding_inputs(rows);report['public_funding_mark_inputs']=used
 for row in rows:report['coin_original'][row['scenario']]={'complete':row['complete'],'sessions':len(row['sessions']),'ledger':perp(row,rates,marks),'statistics':curves(row,'perp')}
 Path(a.out).write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'spot_differences':{k:r['original_field_differences'] for k,r in report['spot'].items()},'spot_ledgers':{k:r['ledger'] for k,r in report['spot'].items()},'coin_ledgers':{k:r['ledger'] for k,r in report['coin_original'].items()}},indent=2))
if __name__=='__main__':main()
