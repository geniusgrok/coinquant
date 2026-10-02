"""Independent recorded-order/fill sizing proof; no producer imports or replay."""
import argparse, bisect, gzip, hashlib, json
from decimal import Decimal as D, getcontext, ROUND_FLOOR
from pathlib import Path
getcontext().prec=40
CUT=1640995200000
TOL=D('1e-18')
def sha(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):
 with (gzip.open(p,'rt') if str(p).endswith('.gz') else open(p)) as f:return json.load(f)
def raworder(o):return {k:v for k,v in o.items() if k in ('symbol','side','type','quantity','quoteOrderQty','stopPrice')}
def check(row):
 scale=D(row['risk_calibration']['scale']);owners={};allocations=[]
 for client,body,status,result in row['allocations']:
  body=json.loads(body);result=json.loads(result);allocations.append((client,body,status,result))
  if 'orderId' in result:
   key=str(result['orderId']);assert key not in owners or owners[key]==body
   owners[key]=body
 fills=sorted(row['fills'],key=lambda x:(x['time'],x['id']))
 windows=[30,40,50]+([200] if row['research_identity']['core_mode'] else [])
 owned={str(w):D(0) for w in windows};i=0;maxerr=D(0);buys=post=0;linked=0
 events=sorted((e for e in row['opportunity_ledger'] if e['event']=='decision'),key=lambda e:e['decision_ms'])
 accepted={};quotefills={};beforefirst=None;changedbudgets=[]
 def apply(f):
  owner=owners[str(f['order_id'])];weights=owner['weights'];group=owner['sleeves'];total=sum((D(x) for x in weights.values()),D(0))
  fee=D(f['commission']) if f['commission_asset']=='BTC' else D(0)
  delta=D(f['qty'])-fee if f['buyer'] else D(f['qty'])+fee
  assigned=D(0)
  for n,w in enumerate(group):
   value=delta-assigned if n==len(group)-1 else delta*D(weights[str(w)])/total
   assigned+=value;owned[str(w)]+=value if f['buyer'] else -value
   assert owned[str(w)]>=-TOL
  quotefills[str(f['order_id'])]=quotefills.get(str(f['order_id']),D(0))+D(f['quote'])
 for e in events:
  stamp=e['decision_ms']
  while i<len(fills) and fills[i]['time']<=stamp:apply(fills[i]);i+=1
  for w,s in e['sleeves'].items():maxerr=max(maxerr,abs(owned[w]-D(s['owned_btc'])))
  assert maxerr<TOL,('owned balance not explained by allocated net fills',stamp,str(maxerr))
  if stamp>=CUT and beforefirst is None:beforefirst={'decision_ms':stamp,'owned_btc':{k:str(v) for k,v in owned.items()}}
  factor=D(1) if stamp<CUT else scale
  assert D(e['risk_scale'])==factor
  free=D(e['idle_cash_usdt']);qty=sum(owned.values());mark=D(e['decision_price'])
  cap=max(D(0),D(e['capital_limit'])-qty*mark) if e['capital_limit'] is not None else free
  sells=any(o['side']=='SELL' for o in e['desired_orders']);expected=[]
  for order in e['desired_orders']:
   if order['side']!='BUY':expected.append(raworder(order));continue
   budget=min(free,cap)
   if e['pool_ledgers']:budget=min(budget,D(e['pool_ledgers']['core' if order['sleeves']==[200] else 'tactical']['cash']))
   quote=(min(D(order['quoteOrderQty']),budget)*factor/D('.01')).to_integral_value(rounding=ROUND_FLOOR)*D('.01')
   if sells or quote<D(10):continue
   out=raworder(order);out['quoteOrderQty']=str(quote)
   expected.append(out);free-=quote;cap-=quote;buys+=1;post+=int(stamp>=CUT)
   if stamp>=CUT and quote!=D(order['quoteOrderQty']) and len(changedbudgets)<3:changedbudgets.append({'decision_ms':stamp,'group':order['sleeves'],'desired_quote':order['quoteOrderQty'],'accepted_quote':str(quote),'scale':str(factor)})
  actual=[raworder(o) for o in e['accepted_orders']]
  assert len(expected)==len(actual)
  for a,b in zip(expected,actual):
   assert set(a)==set(b)
   assert all(D(a[k])==D(b[k]) if k in ('quantity','quoteOrderQty','stopPrice') else a[k]==b[k] for k in a),(stamp,a,b)
  for o in e['accepted_orders']:
   if o['side']=='BUY':accepted.setdefault((e['completed_bar_ms'],tuple(o['sleeves']),D(o['quoteOrderQty'])),[]).append(stamp)
 while i<len(fills):apply(fills[i]);i+=1
 for w in windows:
  p=row['positions'].get(str(w));assert abs(owned[str(w)]-D(p['qty'] if p else '0'))<TOL
 for client,o,status,result in allocations:
  if o['order']['side']!='BUY' or not D(result.get('executedQty','0')):continue
  key=(o['signal_ms'],tuple(o['sleeves']),D(o['order']['quoteOrderQty']))
  matching=accepted.get(key,[]);orderfills=[f for f in fills if str(f['order_id'])==str(result['orderId'])]
  assert matching and orderfills and min(matching)<=min(f['time'] for f in orderfills)
  assert quotefills[str(result['orderId'])]<=key[-1]+TOL
  linked+=1
 return {'candidate':row['candidate'],'fixed_scale':str(scale),'decisions':len(events),'max_owned_btc_reconstruction_delta':str(maxerr),'accepted_buy_observations':buys,'post_cutoff_buy_observations':post,'filled_buy_orders_linked_to_actual_accepted_budget':linked,'first_post_cutoff_holdings':beforefirst,'changed_budget_examples':changedbudgets,'all_checks_passed':True}
def main():
 p=argparse.ArgumentParser();p.add_argument('--raw',required=True);p.add_argument('--sha256',required=True);p.add_argument('--out',required=True);a=p.parse_args();assert sha(a.raw)==a.sha256
 data=read(a.raw);results=[check(r) for r in data['results'].values() if r['scenario']=='base'];assert sha(a.raw)==a.sha256
 with open(a.out,'x') as f:json.dump({'raw_sha256':a.sha256,'accounts':results},f,indent=2)
if __name__=='__main__':main()
