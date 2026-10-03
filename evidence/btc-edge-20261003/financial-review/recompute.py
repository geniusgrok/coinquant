"""Independent read-only financial reconstruction. Never calls producer/evaluator math.
Arithmetic ordering preserves the frozen Decimal ledger and IEEE daily-statistics contracts.
Exclusive account checkpoints permit only failed portions to resume, without repeating passes.
"""
import bisect,csv,gzip,hashlib,io,json,math,os,statistics,subprocess,sys,tarfile,traceback,zipfile
from collections import Counter
from datetime import datetime,timezone
from decimal import Decimal as D
from pathlib import Path
ROOT=Path('/workspace/btc-alpha-beta-improve'); WORK=Path('/workspace/scratch/btc-alpha-beta-edge-20261003'); OUT=WORK/'financial-review'; PRE=WORK/'assessment/complete-preliminary.json'
START=1577836800000;END=1789862400000;CUT=1640995200000;DAY=86400000
BASE={'spot':'atr-stop','perp':'incumbent'};ORDER={'spot':['exit-confirm','stop-budget','crowding-interaction'],'perp':['quality-budget','cost-horizon','crowding-interaction']};STRESS={'spot':['base','fee150','slip2','outage'],'perp':['base','fees-x1.5','read-400ms','trigger-slip']}
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def checksum(v):return hashlib.sha256(json.dumps(v,sort_keys=True,allow_nan=False).encode()).hexdigest()
def load(p):
 p=Path(p)
 with (gzip.open(p,'rt') if p.suffix=='.gz' else p.open()) as f:return json.load(f,parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
def put(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
def require(v,msg):
 if not v:raise AssertionError(msg)
def eq(a,b,msg):require(type(a)==type(b) and a==b,msg+'\nactual='+str(a)[:900]+'\nexpected='+str(b)[:900])
def near(a,b,msg):require(abs(D(str(a))-D(str(b)))<=D('1e-8'),msg+': '+str(a)+' / '+str(b))
def ident(k,n,s='base',capital='10000',offset=0,risk=False):return '|'.join([k,n,s,str(D(str(capital)).normalize()),str(offset),'risk' if risk else 'unscaled'])
def record(category,id,raw,values):return {'id':id,'raw_bindings':raw,'values':values,'matches':True}
def ds(v):return format(D(str(v)).normalize(),'f')
R=load(PRE); require(sha(PRE)=='b54a0324570d2b2a21ed7450b3f4a905887408ae31a115a180cc8743911aa6b3','preliminary bytes')
ARGV=R['command']; arg=lambda flag:ARGV[ARGV.index(flag)+1]
FX=load(arg('--fx'))['rates'];FXD=sorted(FX)
def fx(t):
 day=datetime.fromtimestamp(t/1000,timezone.utc).date().isoformat();i=bisect.bisect_left(FXD,day)-1
 return D(str(FX[FXD[i]]['CNY'])) if i>=0 else D('6.9615')
def daily(vals,initial,es=False,usd=False):
 peak=initial;mdd=0;under=longest=0;prev=initial;ret=[]
 for v in vals:
  require(v>0,'nonpositive equity');ret.append(v/prev-1);prev=v;peak=max(peak,v);mdd=max(mdd,1-v/peak);under=under+1 if v<peak else 0;longest=max(longest,under)
 out={'daily_mdd':mdd,'longest_daily_underwater_days':longest,'worst_day':min(ret),'daily_volatility_annualized':statistics.stdev(ret)*math.sqrt(365.25),'cagr':(vals[-1]/initial)**(365.25/len(vals))-1,'final_usdt' if usd else 'final_cny':vals[-1]}
 if es:out['daily_es99_loss']=float(-sum(sorted(D(str(x)) for x in ret)[:(len(ret)+99)//100],D(0))/((len(ret)+99)//100))
 return out,ret
def reg(yv,xv):
 x=statistics.mean(xv);y=statistics.mean(yv);den=sum((v-x)**2 for v in xv);beta=sum((a-y)*(b-x) for a,b in zip(yv,xv))/den;inter=y-beta*x
 errors=[a-inter-beta*b for a,b in zip(yv,xv)];n=len(xv);xx=sum(v*v for v in xv);det=n*xx-sum(xv)**2
 infl=[e*(xx-sum(xv)*v)/det for e,v in zip(errors,xv)];var=sum(v*v for v in infl)
 for lag in range(1,min(7,n-1)+1):var+=2*(1-lag/8)*sum(infl[i]*infl[i-lag] for i in range(lag,n))
 var=max(0,var)*n/(n-2);se=math.sqrt(var)
 return {'beta_btc':beta,'intercept_daily':inter,'residual_arithmetic_annualized':365.25*inter,'intercept_hac7_t_descriptive':inter/se if var else None,'intercept_hac7_standard_error_daily':se,'residual_arithmetic_annualized_normal95_descriptive':[365.25*(inter-1.96*se),365.25*(inter+1.96*se)],'uncertainty_limit':'Descriptive fixed seven-lag normal approximation; no selection adjustment or prospective claim.','residual_volatility_annualized':statistics.stdev(errors)*math.sqrt(365.25),'days':n,'prospective_alpha_proven':False}
def risk_stats(ret,mr):return {'volatility':statistics.stdev(ret)*math.sqrt(365.25),'beta':reg(ret,mr)['beta_btc'],'days':len(ret)}
def groups(row,kind):
 ids={}
 if kind=='spot':
  for e in row['client_events']:ids.setdefault(e['client_id'],'synthetic-client-'+str(len(ids)))
  for id,*_ in row['allocations']:ids.setdefault(id,'synthetic-client-'+str(len(ids)))
 def norm(v):
  if isinstance(v,dict):return {ids.get(k,k):norm(x) for k,x in v.items()}
  if isinstance(v,list):return [norm(x) for x in v]
  return ids.get(v,v) if isinstance(v,str) else v
 fields={'financial':['initial_cny','final_cny','final_usdt','cagr','mdd','audit']+(['cash_usdt','btc'] if kind=='spot' else ['fees','funding','position','final_mark','mdd_close']), 'fills':['fills'] if kind=='spot' else ['trades','funding_ledger'],'daily':['daily'] if kind=='spot' else ['daily','daily_cny'],'ownership':['positions','allocations','pending_intents'] if kind=='spot' else ['position'],'operating':['sessions','session_error_count','execution_unresolved_sessions','policy_pending','filters','client_events'] if kind=='spot' else ['sessions','known_path','unknown_from','hindsight_bounded','bounded_minutes','mdd_envelope_at','mdd_close_at','funnel','failure','feature_coverage','execution_unresolved']}
 result={}
 for name,keys in fields.items():
  body={k:row[k] for k in keys}
  if 'allocations' in body:body['allocations']=[[id,json.loads(p),s,json.loads(r)] for id,p,s,r in body['allocations']]
  if kind=='spot' and 'sessions' in body:
   require(all(s['archive_verified'] is True and len(s['archive_backup_sha256'])==64 for s in body['sessions']),'archive normalization precondition')
   body['sessions']=[{k:v for k,v in s.items() if k!='archive_backup_sha256'} for s in body['sessions']]
  result[name]=checksum(norm(body))
 covered={k for v in fields.values() for k in v};additional={'candidate','scenario','original_row_sha256','opportunity_ledger','research_identity','risk_calibration','subpools'}
 result['remaining_original_fields']=checksum(norm({k:v for k,v in row.items() if k not in covered|additional}))
 return result

def source_proof(repo,source):
 require(source['dirty'] is False,'dirty measured source');head=source['git_head'];package='spotquant' if (repo/'spotquant').exists() else 'coinquant'
 raw=subprocess.check_output(['git','archive',head,'research',package],cwd=repo);h=hashlib.sha256();files={};modes={}
 with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
  for m in sorted(tar.getmembers(),key=lambda x:x.name):
   if m.isfile():
    b=tar.extractfile(m).read();files[m.name]=hashlib.sha256(b).hexdigest();modes[m.name]=m.mode
    if m.name.endswith('.py'):h.update(m.name.encode()+b'\0'+b+b'\0')
 require(h.hexdigest()==source['python_sources_sha256'],'committed full Python source hash')
 current=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
 if current==head:
  for n,v in files.items():
   if n.endswith('.py') or n.endswith('spec.json') or 'PROTOCOL' in n:require(sha(repo/n)==v,'working protected bytes '+n)
 return {'source':source,'files':files,'modes':modes,'current_head':current,'git_status':subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True)}

def provenance():
 path=OUT/'provenance.json'
 if path.exists():print('REUSE provenance',flush=True);return load(path)
 inputs={}
 for i,(p,h) in enumerate(R['inputs'].items()):
  require(sha(p)==h,'input hash '+p);inputs[p]=h
  if p.endswith('.zip') and Path(p+'.CHECKSUM').exists():
   c=Path(p+'.CHECKSUM').read_text().split();require(c[0]==h and c[1].lstrip('*')==Path(p).name,'official checksum '+p)
  if i%300==0:print('INPUT',i,len(R['inputs']),flush=True)
 sources={}
 for kind in BASE:
  source=next(a['source'] for a in R['accounts'].values() if a['kind']==kind);sp=source_proof(ROOT/('spotquant' if kind=='spot' else 'coinquant'),source);sources[kind]=sp
  for n,f in [('edge_spec.json','spec_sha256'),('edge-PROTOCOL.md','protocol_sha256')]:eq(sp['files']['research/'+n],R['contracts'][kind][f],'committed contract')
 correction=load(WORK/'assessment/public-print-input-path-correction.json');require(len(correction['original_files'])==1596,'union original coverage')
 for f in correction['original_files']:
  a=Path(f['path']);b=Path(f['original_path']);require(a.stat().st_ino==b.stat().st_ino and a.stat().st_dev==b.stat().st_dev and a.stat().st_size==f['bytes'],'union original hardlink')
 out={'input_hashes':inputs,'sources':sources,'correction_sha256':sha(WORK/'assessment/public-print-input-path-correction.json'),'correction':{k:v for k,v in correction.items() if k!='original_files'},'native_cases':0,'actual_account_days':0}
 put(path,out);return out

def market():
 out={};files=sorted((Path(arg('--market'))/'1d').glob('BTCUSDT-1d-*.zip'))+sorted((Path(arg('--market'))/'1d/daily').glob('BTCUSDT-1d-*.zip'));h=hashlib.sha256()
 for p in files:
  raw=p.read_bytes();dig=hashlib.sha256(raw).digest();h.update(p.name.encode()+b'\0'+dig)
  require(p.with_suffix('.zip.CHECKSUM').read_text().split()[0]==dig.hex(),'daily ZIP checksum')
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   for line in z.read(z.namelist()[0]).decode().splitlines():
    if not line or not line[0].isdigit():continue
    v=line.split(',');t=int(v[0]);t=t//1000 if t>10**14 else t
    if t%DAY:continue
    bar=(D(v[1]),D(v[2]),D(v[3]),D(v[4]),D(v[7]));require(t not in out or out[t]==bar,'conflicting daily bars');out[t]=bar
 require(h.hexdigest()==R['environment']['market_sha256'],'daily market aggregate')
 bars={t:out[t] for t in range(START,END,DAY)};prev=bars[START][0];pcny=prev*fx(START);mr=[];cr=[]
 for t,b in bars.items():
  val=b[3];cny=val*fx(t+DAY);mr.append(float(val/prev-1));cr.append(float(cny/pcny-1));prev=val;pcny=cny
 return bars,mr,cr

def receipts(path,digest):
 p=Path(path);start=load(str(p)+'.command-start.json');finish=load(str(p)+'.command-finish.json')
 require(finish['exit_code']==0 and finish['reaped'] is True and finish['state']=='exited' and not finish['errors'],'actual exit/reap')
 eq(finish['output_sha256'],digest,'raw receipt');eq(finish['command_start_sha256'],sha(str(p)+'.command-start.json'),'start receipt')
 eq(sha(str(p)+'.run.log'),finish['log_sha256'],'producer log')
 require(start['output']==str(p) and start['command'][start['command'].index('--out')+1]==str(p),'actual output argv')
 for a,b in [('registry_path','registry_sha256'),('freeze_path','freeze_sha256'),('approval_path','approval_sha256'),('phase_input_path','phase_input_sha256'),('supplemental_path','supplemental_sha256')]:
  if start.get(a):eq(sha(start[a]),start[b],a)
 require(start['uid']==1000 and start['home']=='/home/agent' and start['concurrency']==1,'UID/HOME/concurrency')
 return {'start_sha256':sha(str(p)+'.command-start.json'),'finish_sha256':sha(str(p)+'.command-finish.json'),'actual_argv':start['command'],'pid':finish['pid'],'exit_code':0,'reaped':True}

def ledger(row,kind):
 initial=D(row['initial_cny'])/fx(START)*D('.999');cash=initial;qty=entry=realized=fees=D(0);ids=set()
 fills=row['fills' if kind=='spot' else 'trades'];incomes=row.get('funding_ledger',[])
 require([x['time'] for x in fills]==sorted(x['time'] for x in fills),'fill time order')
 for t in fills:
  require(t['id'] not in ids,'duplicate fill');ids.add(t['id']);part=D(t['qty']);price=D(t['price']);buy=t['buyer'] if kind=='spot' else t['side']=='BUY';signed=part if buy else -part
  require(part>0 and price>0 and START<=t['time']<END,'fill bounds')
  if kind=='spot':
   fee=D(t['commission']);require(type(buy)==bool and t['commission_asset'] in ['BTC','USDT'] and fee>=0,'spot fee')
   qty+=signed-(fee if t['commission_asset']=='BTC' else 0);cash-=(D(t['quote']) if buy else -D(t['quote']))+(fee if t['commission_asset']=='USDT' else 0);fees+=fee*price if t['commission_asset']=='BTC' else fee
  else:
   if not qty or qty*signed>0:entry=(abs(qty)*entry+part*price)/(abs(qty)+part)
   else:
    realized+=min(abs(qty),part)*(price-entry)*(1 if qty>0 else -1)
    if part>abs(qty):entry=price
   qty+=signed
   if not qty:entry=D(0)
 if kind=='spot':
  near(cash,row['cash_usdt'],'cash from fills');near(qty,row['btc'],'BTC from fills');proof={'passed':True,'cash_from_fills':str(cash),'btc_from_fills':str(qty),'fees_usdt':str(fees),'no_deposits':True};eq(proof,row['audit'],'entire original Spot audit');funding=D(0)
 else:
  sums=Counter()
  for t in incomes:require(START<=t['time']<END and t['incomeType'] in ['REALIZED_PNL','COMMISSION','INSURANCE_CLEAR','FUNDING_FEE'],'external flow or terminal funding');sums[t['incomeType']]+=D(t['income'])
  cash=initial+sum(sums.values(),D(0));fees=-sums['COMMISSION']-sums['INSURANCE_CLEAR'];funding=-sums['FUNDING_FEE'];near(realized,sums['REALIZED_PNL'],'realized PNL');near(fees,row['fees'],'fees');near(funding,row['funding'],'funding');near(qty,row['position'],'signed inventory');near(cash,row['audit']['wallet_from_ledger_usdt'],'wallet');near(cash+(qty*(D(row['final_mark'])-entry) if qty else 0),row['final_usdt'],'final equity');require(all(row['audit']['checks'].values()),'original checks');proof={'passed':True,'wallet_usdt':str(cash),'position_btc':str(qty),'entry_usdt':str(entry)}
 near(D(row['final_usdt'])*fx(END)*D('.999'),row['final_cny'],'final FX')
 return proof,fees,funding

def curve(row,kind,bars):
 raw=row['daily'];raw=list(raw.values()) if isinstance(raw,dict) else raw;tk='timestamp_ms' if kind=='spot' else 'stamp_ms';qk='btc' if kind=='spot' else 'quantity_btc';ck='cash_usdt' if kind=='spot' else 'wallet_usdt'
 stamps=[p[tk] for p in raw];require(stamps==sorted(set(stamps)),'daily clock order');points={p[tk]:p for p in raw};cash=D(row['initial_cny'])/fx(START)*D('.999');qty=entry=D(0);fi=ii=0;fills=row['fills' if kind=='spot' else 'trades'];incomes=row.get('funding_ledger',[]);last=(cash,qty,fi,ii)
 for stamp in sorted(set(stamps)|set(range(START+DAY,END+DAY,DAY))):
  require(START<=stamp<=END,'daily clock bounds');bound=stamp-1 if kind=='perp' and stamp%DAY==0 else stamp
  while fi<len(fills) and fills[fi]['time']<=bound:
   t=fills[fi];part=D(t['qty']);price=D(t['price']);buy=t['buyer'] if kind=='spot' else t['side']=='BUY';signed=part if buy else -part
   if kind=='spot':
    fee=D(t['commission']);cash-=(D(t['quote']) if buy else -D(t['quote']))+(fee if t['commission_asset']=='USDT' else 0);qty+=signed-(fee if t['commission_asset']=='BTC' else 0)
   else:
    if not qty or qty*signed>0:entry=(abs(qty)*entry+part*price)/(abs(qty)+part)
    elif part>abs(qty):entry=price
    qty+=signed
    if not qty:entry=D(0)
   fi+=1
  while ii<len(incomes) and (incomes[ii]['time']<=bound or incomes[ii]['time']==stamp and incomes[ii]['incomeType']=='FUNDING_FEE'):cash+=D(incomes[ii]['income']);ii+=1
  if stamp not in points:require(qty==0 and (cash,qty,fi,ii)==last,'missing active daily snapshot');continue
  p=points[stamp];price=D(p['price_usdt' if kind=='spot' else 'mark_usdt']);equity=cash+qty*(price if kind=='spot' else price-entry)
  for a,b,name in [(cash,p[ck],'cash'),(qty,p[qk],'qty'),(equity,p['equity_usdt'],'USDT'),(equity*fx(stamp)*D('.999'),p['equity_cny'],'CNY')]:near(a,b,'daily '+name+' '+str(stamp))
  if kind=='perp' and qty:require(abs(D(p[qk])*price)==D(p['gross_btc_exposure_usdt']),'perp exposure')
  last=(cash,qty,fi,ii)
 # Use verified original decimal snapshot precision (ledger additions differ at ~1e-21).
 # No curve projection: every raw daily point was just independently reconstructed above.
 result=[];previous={tk:START,qk:'0',ck:str(D(row['initial_cny'])/fx(START)*D('.999'))};i=0
 for day,bar in bars.items():
  while i<len(raw) and raw[i][tk]<=day+DAY:previous=raw[i];i+=1
  q=D(previous[qk]);require(not q or previous[tk]==day+DAY,'held missing close');usd=D(previous['equity_usdt']) if q else D(previous[ck]);price=bar[3];gross=float(abs(q)*price/usd)
  if kind=='perp' and q:price=D(previous['mark_usdt']);gross=float(D(previous['gross_btc_exposure_usdt'])/D(previous['equity_usdt']))
  result.append({'day_ms':day,'equity_cny':float(usd*fx(day+DAY)*D('.999')),'equity_usdt':float(usd),'net_btc':float(q),'price_usdt':float(price),'gross_exposure_over_equity':gross,'mark_timestamp_ms':previous[tk]})
 return result

def metrics(row,cur,kind,mr,cr):
 initial=float(row['initial_cny']);usd_initial=float(D(str(initial))/fx(START)*D('.999'));cm,ret=daily([p['equity_cny'] for p in cur],initial,True);um,ur=daily([p['equity_usdt'] for p in cur],usd_initial,usd=True)
 year_days=365.25 if kind=='spot' else 365.2425;cagr=(cur[-1]['equity_cny']/initial)**(year_days*DAY/(END-START))-1
 require(abs(cagr-row['cagr'])<=1e-8,'original year CAGR');require(type(row['mdd'])==str and D(row['mdd']).is_finite() and D(row['mdd'])>=D(str(cm['daily_mdd']))-D('1e-8'),'exact original MDD');years={};logs={}
 for p,r,u in zip(cur,ret,ur):
  y=str(datetime.fromtimestamp(p['day_ms']/1000,timezone.utc).year);years[y]=years.get(y,1)*(1+r);logs[y]=logs.get(y,0.0)+math.log1p(u)
 capture={}
 for name,pred in [('up',lambda x:x>0),('down',lambda x:x<0)]:
  ix=[i for i,v in enumerate(mr) if pred(v)];capture[name]={'days':len(ix),'mean_account_usdt_return':statistics.mean(ur[i] for i in ix),'mean_btc_usdt_return':statistics.mean(mr[i] for i in ix),'arithmetic_capture_ratio':sum(ur[i] for i in ix)/sum(mr[i] for i in ix)}
 down=[i for i,v in enumerate(mr) if v<0];total=sum(logs.values());validation={'usdt':daily([p['equity_usdt'] for p in cur[731:]],cur[730]['equity_usdt'],True,True)[0],'cny':daily([p['equity_cny'] for p in cur[731:]],cur[730]['equity_cny'],True)[0],'regression':dict(reg(ur[731:],mr[731:]),identifiable=True)}
 return {'metrics':cm,'usdt_btc_regression':reg(ur,mr),'cny_btc_regression':reg(ret,cr),'down_market_beta':reg([ur[i] for i in down],[mr[i] for i in down])['beta_btc'],'calendar_returns':{y:v-1 for y,v in years.items()},'mean_closing_gross_exposure_over_equity':statistics.mean(p['gross_exposure_over_equity'] for p in cur),'mean_closing_signed_exposure_over_equity':statistics.mean((1 if p['net_btc']>=0 else -1)*p['gross_exposure_over_equity'] for p in cur),'btc_up_down_day_capture':capture,'days_with_closing_btc_position':sum(bool(p['net_btc']) for p in cur),'days_with_closing_btc_notional_at_least_usdt5':sum(abs(p['net_btc'])*p['price_usdt']>=5 for p in cur),'days_with_closing_short_position':sum(p['net_btc']<0 for p in cur),'fees_usdt':row['fees'] if kind=='perp' else row['audit']['fees_usdt'],'funding_paid_usdt':row.get('funding','0'),'fill_count':len(row['fills' if kind=='spot' else 'trades']),'continuous_mdd_from_account':float(row['mdd']),'native_execution_verified':False,'usdt_metrics':um,'registered_account_cagr':float(row['cagr']),'annualization':{'account_kind':kind,'account_year_days':year_days,'account_start_ms':START,'account_end_exclusive_ms':END,'daily_metrics_cagr_year_days':365.25,'daily_volatility_year_days':365.25,'regression_arithmetic_year_days':365.25},'validation_2022_plus':validation,'calendar_log_return':logs,'calendar_log_return_share':{y:v/total if total else None for y,v in logs.items()},'calendar_2026':'partial through 2026-09-19 UTC','prior_research_contamination':True,'prospective_alpha_proven':False,'closing_gross_exposure_over_equity':cur[-1]['gross_exposure_over_equity'],'closing_signed_exposure_over_equity':(1 if cur[-1]['net_btc']>=0 else -1)*cur[-1]['gross_exposure_over_equity'],'registered_account_usdt_cagr':(cur[-1]['equity_usdt']/float(D(row['initial_cny'])/fx(START)*D('.999')))**(year_days*DAY/(END-START))-1}

def clocks(row,kind,scenario,offset):
 expected=[t+offset for t in R['environment']['starts'] if not (kind=='spot' and scenario=='outage' and 1583020800000<=t<1584835200000)];sessions=row['sessions'];eq([s['start_ms'] for s in sessions],expected,'all original sessions');exception=[];writes=0
 require(row['complete'] is True and row['audit']['passed'] is True and all(not s['execution_unresolved'] for s in sessions),'unresolved account')
 if kind=='spot':
  require(not row['execution_unresolved_sessions'] and not row['policy_pending'] and not row['pending_intents'],'pending spot');prior=-1;receipts={t:[] for t in expected}
  for e in row['client_events']:
   sent=e['sent_ms'];received=e['received_ms'];i=bisect.bisect_right(expected,sent)-1;require(sent>=prior and i>=0 and sent<expected[i]+300000 and received==sent+1000 and e['method'] in ['POST','DELETE'] and received<=sessions[i]['ended_ms'],'write timing');prior=received;receipts[expected[i]].append(received);writes+=1
  for i,s in enumerate(sessions):
   start=s['start_ms'];end=s['ended_ms'];require(s['archive_verified'] is True and len(s['archive_backup_sha256'])==64 and end>=start+300000 and s['elapsed_seconds']==max(0,end/1000-start/1000),'session/archive clock');require(s['status'] in ['offline_execution','demo_execution'] or s['errors'] and all('session deadline' in e['reason'] for e in s['errors']),'session error status')
   if end>=start+300200:require(end in receipts[start] and end<start+301000,'unexplained overrun')
   if s['errors'] or end!=start+300000:exception.append(i)
  near(sum((D(p['qty']) for p in row['positions'].values() if p is not None),D(0)),row['btc'],'owned final qty')
  for id,p,status,res in row['allocations']:
   payload=json.loads(p);result=json.loads(res);require(status in ['settled','cancelled','resting'],'allocation status '+status);require(payload['order']['symbol']=='BTCUSDT','allocation symbol')
   if status=='resting':require(payload['order']['side']=='SELL' and payload['order']['type']=='STOP_LOSS' and result['status']=='NEW' and D(result['executedQty'])==0,'resting owned protective stop')
 else:
  require(row['known_path'] and not row['failure'] and not row['execution_unresolved'],'coin path');
  for i,s in enumerate(sessions):
   require(s['index']==i and s['cleanup']=='verified' and s['status'] in ['executed','no_action','unknown'] and type(s['cycles'])==int and s['cycles']>=0,'coin session')
   if s['status']=='unknown' or s['observations'].get('constraints') or s['observations'].get('reasons'):exception.append(i)
  for e in row['opportunity_ledger']:
   if e['event'] in ['decision','edge_predecision','write_attempt']:
    t=e['at_ms'];i=bisect.bisect_right(expected,t)-1;require(i>=0 and t<=expected[i]+300000 and (e['event']!='write_attempt' or t<expected[i]+300000),'coin dispatch deadline')
    if 'completed_at_ms' in e:require(e['completed_at_ms']>=t,'coin completion order')
    writes+=e['event']=='write_attempt'
 sample=sorted(set([0,len(sessions)-1,*range(0,len(sessions),97),*exception]));return {'session_count':len(sessions),'all_session_clocks_checked':True,'all_write_count':writes,'sample_rule':'first,last,every97th,and every exceptional/unknown/constraint/reason session','sample_indices':sample,'exception_indices':exception,'all_cleanup_verified':True}

def accounts(bars,mr,cr):
 allout={};paths={a['path'] for a in R['accounts'].values()}
 for path in sorted(paths):
  ids=[k for k,a in R['accounts'].items() if a['path']==path];need=[k for k in ids if not (OUT/'accounts'/ (hashlib.sha256(k.encode()).hexdigest()+'.json')).exists()]
  if not need:
   for k in ids:allout[k]=load(OUT/'accounts'/(hashlib.sha256(k.encode()).hexdigest()+'.json'))
   print('REUSE',len(ids),path,flush=True);continue
  b=load(path);digest=sha(path);receipt=receipts(path,digest)
  for k in ids:
   cp=OUT/'accounts'/(hashlib.sha256(k.encode()).hexdigest()+'.json')
   if cp.exists():allout[k]=load(cp);continue
   a=R['accounts'][k];kind=a['kind'];name=a['candidate'];scenario=a['scenario'];row=b['results'][name+'-'+scenario] if kind=='spot' else b['results'][name][scenario];meta=b if kind=='spot' else b['inputs'];edge=b if kind=='spot' else b['edge'];env={z:v for z,v in b.items() if z!='results'}
   eq(digest,a['raw_sha256'],'raw');eq(meta['source'],a['source'],'raw source');eq(env,R['input_envelopes'][path],'original envelope');eq(row['initial_cny'],a['capital'],'funded capital');require(a['status']=='complete' and not a['reasons'],'account complete')
   proof,fees,funding=ledger(row,kind);eq(proof,a['monetary_audit'],'independent ledger');cur=curve(row,kind,bars);eq(cur,a['curve'],'independent daily curve');m=metrics(row,cur,kind,mr,cr);eq(m,a['metrics'],'independent all metrics');timing=clocks(row,kind,scenario,a['offset']);fp=groups(row,kind)
   gate={'raw_sha256':digest,'values':{'cagr':row['cagr'],'mdd':row['mdd'],'worst_day':m['metrics']['worst_day'],'es99':m['metrics']['daily_es99_loss'],'underwater':m['metrics']['longest_daily_underwater_days']}};eq(gate,a['gate_inputs'],'gate original exact typed')
   out={'id':k,'path':path,'raw_sha256':digest,'kind':kind,'candidate':name,'scenario':scenario,'capital':row['initial_cny'],'offset':a['offset'],'risk':bool(edge['risk_calibration_sha256']),'components':a['components'],'source':meta['source'],'curve':cur,'metrics':m,'monetary_audit':proof,'gate_inputs':gate,'groups':fp,'timing':timing,'receipt':receipt,'annotations':{z:row[z] for z in ['candidate','scenario','original_row_sha256','research_identity','risk_calibration','subpools'] if z in row},'passed':True}
   eq(out['risk'],a['risk'],'actual risk binding');put(cp,out);allout[k]=out;print('ACCOUNT PASS',k,'fills',m['fill_count'],'days',len(cur),flush=True)
  del b
 return allout

def main():
 prov=provenance();bars,mr,cr=market();a=accounts(bars,mr,cr);put(OUT/'account-phase-complete.json',{'count':len(a),'account_paths':{k:str(OUT/'accounts'/(hashlib.sha256(k.encode()).hexdigest()+'.json')) for k in a},'market_returns':mr,'cny_market_returns':cr,'script_sha256':sha(__file__),'input_hashes_sha256':checksum(prov['input_hashes'])});print('ACCOUNT PHASE PASS',len(a),flush=True)
if __name__=='__main__':
 try:main()
 except Exception:
  traceback.print_exc();sys.exit(1)
