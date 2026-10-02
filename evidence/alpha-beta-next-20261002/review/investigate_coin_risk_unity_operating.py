"""Read-only exact unity differences; no normalization or gate override."""
import gc,gzip,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'/workspace/btc-alpha-beta-analysis/spotquant')
from research.alpha_assessment import evidence_fingerprints
R=Path('/workspace/btc-alpha-beta-next/review');O=Path('/workspace/scratch/alpha-beta-next')
fields=('sessions','known_path','unknown_from','hindsight_bounded','bounded_minutes','mdd_envelope_at','mdd_close_at','funnel','failure','feature_coverage','execution_unresolved')
names=['incumbent','fresh-entry','atr-trail','single-topup']
def read(p):
 with gzip.open(p,'rt') as f:return json.load(f)
def sha(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
oldpath=O/'perp-singletons-retry1.json.gz';newpath=O/'risk-perp.json.gz'
assert sha(oldpath)=='bf1d167979f4bb3d15925f0bcaf5337bd1cc0a17523628b3af0599875dc5a7c1'
assert sha(newpath)=='3b958b2e92d8aefcf7b9f073a3916c325420a546cf7652203ce6692be5ee2446'
b=read(oldpath);old={n:{'groups':evidence_fingerprints(b['results'][n]['base'],'perp'),'operating':{k:b['results'][n]['base'][k] for k in fields}} for n in names};del b;gc.collect()
b=read(newpath);out={}
def diff(a,b,path=''):
 if type(a)!=type(b):return [{'path':path,'old':a,'new':b,'difference':'type'}]
 if isinstance(a,dict):
  result=[]
  for k in sorted(set(a)|set(b)):
   if k not in a or k not in b:result.append({'path':path+'/'+str(k),'old':a.get(k),'new':b.get(k),'difference':'missing'})
   else:result.extend(diff(a[k],b[k],path+'/'+str(k)))
  return result
 if isinstance(a,list):
  if len(a)!=len(b):return [{'path':path,'old_length':len(a),'new_length':len(b),'old':a,'new':b,'difference':'length'}]
  result=[]
  for i,(x,y) in enumerate(zip(a,b)):result.extend(diff(x,y,path+'/'+str(i)))
  return result
 return [] if a==b else [{'path':path,'old':a,'new':b,'difference':'value'}]
for n in names:
 row=b['results'][n]['base'];newgroups=evidence_fingerprints(row,'perp');differences=diff(old[n]['operating'],{k:row[k] for k in fields})
 out[n]={'six_group_equality':{k:v==newgroups[k] for k,v in old[n]['groups'].items()},'old_groups':old[n]['groups'],'new_groups':newgroups,'exact_operating_differences':differences}
 print(n,'differences',len(differences),'paths',[d['path'] for d in differences[:30]],flush=True)
proof={'old_raw_sha256':sha(oldpath),'new_raw_sha256':sha(newpath),'unity_controls':out,'scope':'strict actual differences retained; no field exclusions/normalization/acceptance'}
with (R/'coin-actual-risk-unity-operating-differences.json').open('x') as f:json.dump(proof,f,indent=2)
