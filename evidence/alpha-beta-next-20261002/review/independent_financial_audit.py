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
 return {'full_usdt':fullu,'full_cny':fullc,'validation_usdt':vu,'validation_cny':vc,'calendar_usdt_log_returns':years,'training_usdt':stats(usd[:cut],float(initial),btc[:cut])[0],'reported_continuous_proxy_mdd':row['mdd'],'final_cny_delta':str(D(str(cny[-1]))-D(row['final_cny']))}

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


# Stable single-bundle audit extension. Original baseline implementation is archived
# verbatim in independent_financial_audit_baselines_v1.py for its recorded SHA.
def core_pools(row):
 identity=row.get('research_identity',{});fraction=D(identity.get('core_fraction','0'))
 if fraction==0:
  assert row.get('subpools') is None
  return {'applicable':False}
 assert fraction==D('.20') and identity.get('core_mode') in ('core-permanent','core-slow')
 owners={}
 for client,payload,status,result in row['allocations']:
  payload=json.loads(payload);result=json.loads(result);group=payload['sleeves']
  assert group and len(group)==len(set(group)) and set(group)<={30,40,50,200}
  assert 200 not in group or group==[200],('mixed core tactical order',client,group)
  if 'orderId' not in result:continue
  native=str(result['orderId']);pool='core' if group==[200] else 'tactical'
  relation=(pool,payload['order']['side'],tuple(group))
  assert native not in owners or owners[native]==relation,('conflicting allocation',native)
  owners[native]=relation
 cash=D(row['initial_cny'])/fx(START)*D('.999')
 pools={'core':{'cash':cash*fraction,'btc':D(0)},'tactical':{'cash':cash*(1-fraction),'btc':D(0)}}
 minimum={k:dict(v) for k,v in pools.items()};fills=sorted(row['fills'],key=lambda x:(x['time'],x['id']));i=0
 maxcash=maxbtc=D(0);observations=0;same_stamp=0
 def apply(f):
  relation=owners[str(f['order_id'])];pool=pools[relation[0]];assert relation[1]==('BUY' if f['buyer'] else 'SELL')
  q,quote,fee=D(f['qty']),D(f['quote']),D(f['commission']);asset=f['commission_asset'];assert asset in ('BTC','USDT')
  pool['cash']+=(-quote if f['buyer'] else quote)-(fee if asset=='USDT' else 0)
  pool['btc']+=(q if f['buyer'] else -q)-(fee if asset=='BTC' else 0)
  for k in pool:minimum[relation[0]][k]=min(minimum[relation[0]][k],pool[k]);assert pool[k]>=D('-1e-20'),('pool borrowing',relation[0],k,f['id'])
 for e in sorted((e for e in row.get('opportunity_ledger',[]) if e.get('event')=='decision' and e.get('pool_ledgers') is not None),key=lambda e:e['decision_ms']):
  stamp=e['decision_ms']
  while i<len(fills) and fills[i]['time']<=stamp:
   same_stamp+=int(fills[i]['time']==stamp);apply(fills[i]);i+=1
  for pool,ledger in e['pool_ledgers'].items():
   maxcash=max(maxcash,abs(pools[pool]['cash']-D(ledger['cash'])));maxbtc=max(maxbtc,abs(pools[pool]['btc']-D(ledger['btc'])))
  observations+=1
 while i<len(fills):apply(fills[i]);i+=1
 for pool,ledger in row['subpools'].items():
  maxcash=max(maxcash,abs(pools[pool]['cash']-D(ledger['cash'])));maxbtc=max(maxbtc,abs(pools[pool]['btc']-D(ledger['btc'])))
 totalcash=sum(p['cash'] for p in pools.values());totalbtc=sum(p['btc'] for p in pools.values())
 assert abs(totalcash-D(row['cash_usdt']))<D('1e-12') and abs(totalbtc-D(row['btc']))<D('1e-20')
 assert maxcash<D('1e-12') and maxbtc<D('1e-20'),('recorded core ledgers differ',str(maxcash),str(maxbtc))
 return {'applicable':True,'fraction':str(fraction),'fill_count':len(fills),'native_owner_count':len(owners),'observed_decision_pool_snapshots':observations,'same_timestamp_fill_boundary_count':same_stamp,'final_pools':{k:{f:str(v) for f,v in p.items()} for k,p in pools.items()},'minimum_pool_balances':{k:{f:str(v) for f,v in p.items()} for k,p in minimum.items()},'max_recorded_cash_delta':str(maxcash),'max_recorded_btc_delta':str(maxbtc),'terminal_cash_conservation_delta':str(totalcash-D(row['cash_usdt'])),'terminal_btc_conservation_delta':str(totalbtc-D(row['btc']))}

def risk_evidence(row,kind,metadata,calibration,calibration_sha):
 candidate=row['candidate'];rawsha=metadata.get('risk_calibration_sha256')
 if calibration is not None:
  assert rawsha==calibration_sha
  assert calibration['cutoff_ms']==CUT
  profile=calibration['profiles'][candidate]
  assert profile['effective_from_ms']==CUT and profile['calibration_end_ms']==CUT
  scale=D(profile['scale']);assert 0<=scale<=1
 else:
  assert rawsha is None, 'supply exact calibration to audit a calibrated account'
  scale=D(1)
 observed=before=after=0
 for e in row.get('opportunity_ledger',[]):
  if 'risk_scale' not in e:continue
  stamp=e.get('decision_ms',e.get('at_ms',e.get('session_ms')))
  assert stamp is not None,('risk scale without timestamp',e.get('event'))
  expected=D(1) if stamp<CUT else scale
  assert D(e['risk_scale'])==expected,('risk chronology',stamp,e['risk_scale'],str(expected))
  observed+=1;before+=int(stamp<CUT);after+=int(stamp>=CUT)
 return {'calibration_sha256':rawsha,'fixed_scale':str(scale),'risk_scale_observations':observed,'pre_cutoff_observations':before,'post_cutoff_observations':after,'limit':'Journal scale chronology checked; actual sizing/owned-position causality still requires comparison of unscaled and rerun account evidence.'}

def comparison(stat,baseline):
 c=stat['training_usdt'];b=baseline['training_usdt'];scale=min(1,b['annual_vol']/c['annual_vol'] if c['annual_vol']>0 else 1)
 if c['beta']>b['beta'] and c['beta']>0:scale=min(scale,max(.01,b['beta'])/max(.01,c['beta']))
 c=stat['validation_usdt'];b=baseline['validation_usdt']
 return {'training_only_unscaled_risk_scale':scale,'training_days':731,'validation_days':1723,'validation_risk_match_achieved':c['annual_vol']<=b['annual_vol']*1.05 and c['beta']<=b['beta']+.02,'validation_vol_limit':b['annual_vol']*1.05,'validation_beta_limit':b['beta']+.02}

def training_fingerprint(row,kind):
 raw=list(row['daily'].values()) if kind=='spot' else row['daily'];stamp='timestamp_ms' if kind=='spot' else 'stamp_ms'
 daily=[r for r in sorted(raw,key=lambda r:r[stamp]) if START<r[stamp]<=CUT]
 fields=('time','qty','quote','price','buyer','commission','commission_asset') if kind=='spot' else ('time','qty','price','side')
 fills=[{k:f[k] for k in fields} for f in row['fills' if kind=='spot' else 'trades'] if f['time']<CUT]
 income=[{k:f[k] for k in ('time','incomeType','asset','income')} for f in row.get('funding_ledger',[]) if f['time']<CUT]
 return hashlib.sha256(json.dumps({'daily':daily,'fills':fills,'income':income},sort_keys=True,separators=(',',':')).encode()).hexdigest()

def labelled_rows(data,kind):
 """Create audit-only views; nested Coin labels are the recorded identities."""
 if kind=='spot':return list(data['results'].values())
 assert kind=='perp'
 candidates=data['inputs'].get('candidates')
 if candidates is not None:
  assert isinstance(candidates,dict) and set(candidates)==set(data['results']),'Coin input candidates differ from nested result labels'
 rows=[]
 for candidate,scenes in data['results'].items():
  assert isinstance(candidate,str) and candidate and isinstance(scenes,dict)
  for scenario,raw in scenes.items():
   assert isinstance(scenario,str) and scenario and isinstance(raw,dict)
   for key,expected in (('candidate',candidate),('scenario',scenario)):
    assert key not in raw or raw[key]==expected,('Coin optional row label disagrees with nested result',key,expected,raw.get(key))
   rows.append(dict(raw,candidate=candidate,scenario=scenario))
 return rows

def bundle_main():
 p=argparse.ArgumentParser(description='Independent audit of ONE already completed immutable bundle; no replay or producer imports')
 p.add_argument('--bundle',type=Path,required=True);p.add_argument('--sha256',required=True);p.add_argument('--kind',choices=['spot','perp'],required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--calibration',type=Path);p.add_argument('--baseline-audit',type=Path);p.add_argument('--unscaled-audit',type=Path)
 args=p.parse_args();assert not args.out.exists(),'never overwrite independent evidence';assert sha(args.bundle)==args.sha256
 data=read(args.bundle);assert data.get('format')!='alpha-account-manifest-v1','one raw bundle only'
 metadata=data if args.kind=='spot' else data['inputs'];source=metadata.get('source') or metadata.get('measured_source');frozen=read('/workspace/scratch/alpha-beta-next/frozen-sources.json')
 assert source==frozen['sources']['spotquant' if args.kind=='spot' else 'coinquant']
 assert metadata['spec_sha256']==frozen['economic_inputs']['alpha_beta_spec.json'];assert metadata['protocol_sha256']==frozen['economic_inputs']['alpha-beta-PROTOCOL.md'];assert metadata['fx_sha256']==sha(FXPATH)
 calibration=read(args.calibration) if args.calibration else None;calsha=sha(args.calibration) if args.calibration else None
 if calibration is not None:assert calibration['spec_sha256']==frozen['economic_inputs']['alpha_beta_spec.json']
 rows=labelled_rows(data,args.kind)
 rates,marks,used=funding_inputs(rows) if args.kind=='perp' else ({},{},{})
 report={'format':'independent-financial-single-bundle-v2.1','raw_path':str(args.bundle),'raw_sha256':args.sha256,'kind':args.kind,'row_label_origin':('raw row fields' if args.kind=='spot' else 'nested results candidate/scenario keys; optional raw row labels checked for exact agreement'),'source':source,'spec_sha256':metadata['spec_sha256'],'protocol_sha256':metadata['protocol_sha256'],'fx_sha256':metadata['fx_sha256'],'accounts':{},'public_funding_mark_inputs':used,'limitations':['No adoption approval; financial identities and descriptive statistics only.','Continuous historical proxy path is reported, not independently replayed here.','Archive flags are inspected; underlying backups are not reopened.','All studied history is research-contaminated; native cases/actual account-days remain zero.']}
 baseline=read(args.baseline_audit) if args.baseline_audit else None
 unscaled=read(args.unscaled_audit) if args.unscaled_audit else None
 for row in rows:
  name=row['candidate']+'/'+row['scenario'];entry={'reported_complete':row.get('complete'),'producer_audit_passed':row.get('audit',{}).get('passed'),'initial_cny':row.get('initial_cny'),'sessions':len(row.get('sessions',[])),'independent_checks_passed':False,'errors':[]};report['accounts'][name]=entry
  try:
   ledger=spot(row) if args.kind=='spot' else perp(row,rates,marks);entry['ledger']=ledger
   for key,value in ledger.items():
    if 'delta' in key:assert abs(D(value))<D('1e-12'),(key,value)
   if args.kind=='spot':entry['core_pools']=core_pools(row)
   entry['risk_journal']=risk_evidence(row,args.kind,metadata,calibration,calsha)
   if row.get('complete'):
    entry['statistics']=s=curves(row,args.kind)
    expected=(float(row['final_cny'])/float(row['initial_cny']))**((365.25 if args.kind=='spot' else 365.2425)*DAY/(END-START))-1
    assert abs(expected-row['cagr'])<1e-8
    assert float(row['mdd'])+1e-8>=s['full_cny']['mdd_daily']
    entry['training_ledger_sha256']=training_fingerprint(row,args.kind)
    if unscaled:
     original=unscaled['accounts'][name];assert entry['training_ledger_sha256']==original['training_ledger_sha256'],'pre-cutoff actual ledger changed in risk rerun'
     entry['pre_cutoff_actual_ledger_equal_to_unscaled']=True
    entry['registered_cagr']=row['cagr'];entry['account_year_days']=365.25 if args.kind=='spot' else 365.2425
    if baseline:
     baserows=baseline['accounts'];base=baserows[('consensus' if args.kind=='spot' else 'incumbent')+'/base']['statistics'];entry['baseline_comparison']=comparison(s,base)
     if calibration is not None:
      expected=entry['baseline_comparison']['training_only_unscaled_risk_scale'];assert abs(float(calibration['profiles'][row['candidate']]['scale'])-expected)<1e-12,'calibrated scale differs from independent training-only recomputation'
   else:entry['statistics_status']='not asserted: producer declares incomplete account'
   entry['independent_checks_passed']=True
  except (AssertionError,KeyError,ValueError,TypeError,ZeroDivisionError) as e:entry['errors'].append(type(e).__name__+': '+str(e))
 assert sha(args.bundle)==args.sha256,'input changed during audit'
 report['all_examined_checks_passed']=all(r['independent_checks_passed'] for r in report['accounts'].values());report['all_reported_complete']=all(r['reported_complete'] for r in report['accounts'].values())
 with args.out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps({'output':str(args.out),'accounts':len(rows),'all_checks_passed':report['all_examined_checks_passed'],'errors':{k:r['errors'] for k,r in report['accounts'].items() if r['errors']}}))
if __name__=='__main__':
 import sys
 bundle_main() if '--bundle' in sys.argv else main()
