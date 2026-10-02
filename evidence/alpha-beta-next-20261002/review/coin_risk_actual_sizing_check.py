"""Independent read-only recorded Coin sizing/ownership checks; no producer imports."""
import bisect,csv,gzip,hashlib,io,json,zipfile
from pathlib import Path
from decimal import Decimal as D,getcontext,ROUND_FLOOR
getcontext().prec=40
DAY=86400000;H4=14400000;CUT=1640995200000

def public_daily_inputs():
 bars={};identities={}
 for p in sorted(Path('/tmp/coinquant-market/klines/4h').rglob('*.zip')):
  with p.open('rb') as f:identities[str(p)]=hashlib.file_digest(f,'sha256').hexdigest()
  with zipfile.ZipFile(p) as z:
   for name in z.namelist():
    for r in csv.reader(io.TextIOWrapper(z.open(name))):
     if r and r[0].isdigit():
      t=int(r[0]);t=t//1000 if t>10**14 else t
      value=[D(r[2]),D(r[3]),D(r[4])];assert t+H4 not in bars or bars[t+H4]==value;bars[t+H4]=value
 closes={t:v[2] for t,v in bars.items() if t%DAY==0}
 return bars,closes,sorted(closes),identities

def check(row,scale,public):
 bars,closes,ends,identities=public;scale=D(scale)
 trades=sorted(row['trades'],key=lambda t:(t['time'],t['id']));times=[];quantities=[D(0)]
 for t in trades:times.append(t['time']);quantities.append(quantities[-1]+D(t['qty'])*(1 if t['side']=='BUY' else -1))
 journal=row['opportunity_ledger'];decisions=[e for e in journal if e['event']=='decision'];post=0
 for e in decisions:
  assert D(e['quantity_before'])==quantities[bisect.bisect_right(times,e['at_ms'])],('owned quantity not explained by actual fills',e['at_ms'])
  assert D(e['risk_scale'])==(scale if e['at_ms']>=CUT else D(1))
  post+=int(e['at_ms']>=CUT)
 assert quantities[-1]==D(row['position'])
 plans=[e for e in journal if e['event'] in ('entry_sizing','topup_sizing')];keys={};requested_count=0;max_error=D(0);examples=[]
 for e in plans:
  key=(e['opportunity'],abs(D(e['accepted_btc'])),D(e['entry_estimate']));keys.setdefault(key,[]).append(e['at_ms'])
  if e['event']!='entry_sizing' or e['at_ms']<CUT:continue
  last=e['at_ms']//DAY*DAY;i=bisect.bisect_right(ends,last);days=ends[i-21:i];assert days==list(range(last-20*DAY,last+1,DAY))
  returns=[closes[days[j]]/closes[days[j-1]]-1 for j in range(1,21)]
  primary=e['opportunity']>0
  fraction=D('7.5' if primary else '3.6')*D('.20')/(D('2.33')*(sum(v*v for v in returns)/20).sqrt()*D(7).sqrt()+D('.10')+D('.01')+2*(D('.00075')+D('.0011')))*scale
  capital=D(e['sizing_capital_usdt']);price=D(e['entry_estimate']);desired=capital*fraction/price
  # Actual complete recorded cases are long; successful exact checks establish
  # executable entry >= simultaneous mark for this demand calculation.
  if not primary:
   lows=[v[1] for t,v in bars.items() if last-10*DAY<t<=last];assert len(lows)==60
   stop=(min(lows)/D('.1')).to_integral_value(rounding=ROUND_FLOOR)*D('.1')
   desired=min(desired,capital*D('.03')/(price-stop))
  error=abs(desired-D(e['desired_btc']));max_error=max(max_error,error);assert error<D('1e-20'),('post-cutoff desired quantity differs from past-only public-vol sizing',e['at_ms'],str(error))
  requested_count+=1
  if len(examples)<4:examples.append({'at_ms':e['at_ms'],'opportunity':e['opportunity'],'sizing_capital_usdt':e['sizing_capital_usdt'],'desired_btc':e['desired_btc'],'accepted_btc':e['accepted_btc'],'fraction_after_fixed_scale':str(fraction),'macro_stop_budget_applies':not primary})
 writes={};linked_writes=0
 for e in journal:
  if e['event']!='write_attempt' or e['method']!='POST' or e['path']!='/fapi/v1/order':continue
  payload=e['payload']
  if payload.get('type')!='LIMIT' or payload.get('timeInForce')!='IOC':continue
  assert payload['side']=='BUY' and not payload.get('reduceOnly',False)
  key=(e['opportunity'],D(payload['quantity']),D(payload['price']));candidates=keys.get(key,[])
  assert any(t<=e['at_ms'] for t in candidates),('IOC lacks matching accepted sizing plan',e['identity'])
  if e['identity'] in writes:assert writes[e['identity']]['payload']==payload
  else:writes[e['identity']]=e
  linked_writes+=1
 fill_events=[e for e in journal if e['event']=='fill'];assert [e['trade'] for e in fill_events]==row['trades']
 filled={};buyfills=0
 for e in fill_events:
  t=e['trade']
  if t['side']!='BUY':continue
  write=writes[e['client_order_id']];assert write['at_ms']<=t['time'] and D(t['price'])<=D(write['payload']['price'])
  filled[e['client_order_id']]=filled.get(e['client_order_id'],D(0))+D(t['qty']);assert filled[e['client_order_id']]<=D(write['payload']['quantity'])
  buyfills+=1
 first=next((e for e in decisions if e['at_ms']>=CUT),None)
 return {'fixed_scale':str(scale),'owned_quantity_decisions_checked':len(decisions),'post_cutoff_decisions':post,'first_post_cutoff_owned_btc':first['quantity_before'] if first else None,'post_cutoff_new_entry_demands_reconstructed':requested_count,'max_requested_btc_delta':str(max_error),'IOC_write_attempts_linked_to_accepted_plans':linked_writes,'filled_IOC_orders':len(filled),'BUY_fills_linked_to_IOC':buyfills,'examples':examples,'all_checks_passed':True}
