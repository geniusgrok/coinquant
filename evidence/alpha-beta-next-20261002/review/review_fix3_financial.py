"""Read-only scoped re-review of committed fix3 against prior independent calculations."""
import json,hashlib,subprocess,ast
from pathlib import Path
from research import alpha_assessment as a
ROOT=Path('/workspace/btc-alpha-beta-next'); OUT=ROOT/'review/task3-fix3-financial-review-proof.json'
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='32ab1bb546bde064e641c4a2eb5ed4248e590acb'
ind=json.loads((ROOT/'review/financial-audit-baselines.json').read_text());frozen=json.loads(Path('/workspace/scratch/alpha-beta-next/frozen-sources.json').read_text())
bars=a.load_daily(Path('/tmp/spotquant-market/klines'),a.END_MS,require_through=a.END_MS);fx=a.PriorFX(ROOT/'starquant/data/usdcny_frankfurter.json');market,cny=a.market_returns_for(bars,fx)
proof={'head':a.source_identity(),'account_replays':0,'scenes':{},'unchanged_functions':[],'equivalence':{}}
# Compare function ASTs independent of author commentary.
base=subprocess.check_output(['git','show','3d723fb5dd42ec38376f243d23ecb052b3212420:research/alpha_assessment.py'],text=True)
head=Path('research/alpha_assessment.py').read_text()
old={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(base).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))};new={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(head).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
assert old.keys()==new.keys();assert {k for k in old if old[k]!=new[k]}=={'financial','consume'}
for k in ('calibrate','achieved_match','selection','verify_execution_equivalence','evidence_fingerprints','calibration_document'):
 assert old[k]==new[k];proof['unchanged_functions'].append(k)
for kind,path,group in [('spot',ROOT/'spotquant/evidence/complete-delivery-20261001/spot-consensus-corrected.json','spot'),('perp',ROOT/'coinquant/evidence/complete-delivery-20261001/perp-exclusive-accounts.json','coin_original')]:
 body,digest=a.read_json(path);assert digest==a.APPROVED_BASELINES[kind]
 rows=body['results'] if kind=='spot' else body['results']['incumbent']
 for name,row in rows.items():
  before=a.checksum(row);curve=a.canonical(row,bars,fx,10000,kind);actual=a.financial(row,curve,bars,fx,market,cny,10000,kind=kind);ref=ind[group][name]['statistics'];delta={}
  for label,m,key in [('full_usdt',actual['usdt_btc_regression'],'full_usdt'),('full_cny',actual['cny_btc_regression'],'full_cny'),('validation_usdt',actual['validation_2022_plus']['regression'],'validation_usdt')]:
   for field,rfield in [('beta_btc','beta'),('intercept_daily','alpha_daily'),('intercept_hac7_standard_error_daily','hac7_se_daily')]:
    diff=abs(m[field]-ref[key][rfield]);assert diff<1e-12;(delta.setdefault(label,{}))[field]=diff
  assert before==a.checksum(row);assert actual['registered_account_cagr']==row['cagr']
  y=365.25 if kind=='spot' else 365.2425;expected=(float(row['final_cny'])/10000)**(y*86400000/(a.END_MS-a.START_MS))-1
  assert abs(expected-row['cagr'])<1e-14
  assert actual['annualization']['account_year_days']==y
  for m in [actual['usdt_metrics'],actual['validation_2022_plus']['usdt']]:
   assert 'final_cny' not in m and m['final_usdt']==curve[-1]['equity_usdt']
  assert 'final_cny' in actual['validation_2022_plus']['cny']
  for bad in (row['cagr']+.01,):
   try:a.financial(dict(row,cagr=bad),curve,bars,fx,market,cny,10000,kind=kind)
   except ValueError as e:assert 'CAGR differs' in str(e)
   else:raise AssertionError('incorrect raw CAGR accepted')
  if kind=='perp':
   try:a.financial(dict(row,cagr=actual['metrics']['cagr']),curve,bars,fx,market,cny,10000,kind=kind)
   except ValueError as e:assert 'CAGR differs' in str(e)
   else:raise AssertionError('normalized CAGR accepted in place of registered value')
  proof['scenes'][kind+'/'+name]={'raw_sha256':digest,'registered_cagr':row['cagr'],'normalized_cagr':actual['metrics']['cagr'],'row_unchanged':True,'independent_statistic_deltas':delta,'usdt_labels_correct':True}
for kind,repo in [('spot','spotquant'),('perp','coinquant')]:
 current=a.current_source(kind);measured=frozen['sources'][repo]
 proof['equivalence'][kind]=a.verify_execution_equivalence(measured,current,kind,frozen['economic_inputs']['alpha_beta_spec.json'],frozen['economic_inputs']['alpha-beta-PROTOCOL.md'])
 headnow=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT/repo,text=True).strip();assert headnow==measured['git_head']
 status=subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT/repo,text=True).splitlines()
 assert all(line==' M PROJECT_STATE.md' for line in status);proof.setdefault('preserved_progress_changes',{})[kind]=status
proof['frozen_producers_unchanged']=True
OUT.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'scenes':len(proof['scenes']),'equivalence':proof['equivalence'],'output':str(OUT)}))
