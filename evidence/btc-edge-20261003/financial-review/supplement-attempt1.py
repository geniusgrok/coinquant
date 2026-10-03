"""Financial provenance and deterministic ownership/new-risk journal supplement.
Reuses completed account and canonical calculations; no accounts are recalculated.
"""
from recompute import *
from decimal import ROUND_DOWN
ART=ROOT/'task-artifacts';PH=load(OUT/'account-phase-complete.json');A={k:load(p) for k,p in PH['account_paths'].items()};PROV=load(OUT/'provenance.json')
def provenance_extra():
 dest=OUT/'provenance-supplement.json'
 if dest.exists():return load(dest)
 hashes=dict(PROV['input_hashes']);inodes={(Path(p).stat().st_dev,Path(p).stat().st_ino):h for p,h in hashes.items()}
 def verify(p,h=None):
  p=str(p);st=Path(p).stat();inode=(st.st_dev,st.st_ino);actual=hashes.get(p) or inodes.get(inode) or sha(p)
  if h is not None:eq(actual,h,'bound hash '+p)
  hashes[p]=actual;inodes[inode]=actual;return actual
 freeze=load(ART/'reviewed-source-freeze.json')
 for project in freeze['projects'].values():
  for f in project['bound_files']:verify(f['path'],f['sha256']);require(Path(f['path']).stat().st_size==f['bytes'],'bound size')
  for tree in project['bound_trees']:
   actual=sorted(str(p) for p in Path(tree['root']).rglob('*') if p.is_file() and any(str(p).endswith(s) for s in tree['suffixes']));eq(actual,tree['files'],'immutable input set')
 for f in freeze['reviews']:verify(f['path'],f['sha256'])
 prep=load(ART/'source-freeze-preparation.json')
 for f in prep['artifacts']:verify(f['path'],f['sha256'])
 phases=[]
 for p in sorted((ART/'controller-receipts').glob('*/*/finish.json')):
  b=load(p);verify(p);s=load(p.parent/'start.json');verify(p.parent/'start.json');owner=Path(s['owner_path']);o=load(owner);rel=owner.with_name(owner.name.replace('.owner.json','.released.json'));release=load(rel);eq(release['owner_sha256'],verify(owner),'released owner');require(release['all_children_reaped'] is True,'durable drain');verify(rel)
  if b.get('attempt')=='recovery1' or 'canonical' in b.get('phase',''):
   require(b['status']=='completed' and b['all_children_reaped'] and not b['pending_labels'] and not b['errors'],'phase successful complete')
   for v in b['results']:require(v['exit_code']==0 and v['reaped'] and v['finish_receipt_saved'] and not v['errors'],'actual child exit');verify(v['finish_path'])
  phases.append({'path':str(p),'sha256':hashes[str(p)],'status':b['status'],'phase':b.get('phase'),'project':b.get('project_kind'),'actual_children':len(b['results']),'durable_release':str(rel),'release_sha256':hashes[str(rel)]})
 correction=load(WORK/'assessment/public-print-input-path-correction.json')
 for k in ['original_failed_report','consumed_raw','original_vault_snapshot']:verify(correction[k]['path'],correction[k]['sha256'])
 raw=load(correction['consumed_raw']['path']);restores=raw['edge']['print_restore_receipts'];extra=correction['additional_official_files']
 for f in extra:
  verify(f['path'],f['sha256']);require(f['sha256']==f['consumed_receipt_expected_sha256'] and f['status']==200 and f['url']=='https://data.binance.vision/data/futures/um/daily/aggTrades/BTCUSDT/'+Path(f['path']).name and Path(f['path']).stat().st_size==f['bytes'],'exact official retrieval')
  require(f['sha256'] in json.dumps(restores),'extra original consumed receipt hash')
 require(arg('--coin-prints')==correction['assessment_only_root'] and correction['account_replays']==0,'assessment only correction')
 selected=load(WORK/'assessment/spot-selected-budgets-registration.json');require(len(selected['bound_files'])==54 and len(selected['jobs'])==3,'selected budget condition54')
 for f in selected['bound_files']:verify(f['path'],f['sha256'])
 for name in ['task-6-recovery-rereview.md','task-7-spot-canonical-five-operational-review.md','task-7-spot-canonical-preparation-rereview-fix3.md','task-5-fix2-rereview.md','task-5-selection-contract-review.md','spot-public-input-load-preflight.json','perp-public-input-load-preflight.json','first-financial-attempt-storage-failure.json','recovery-approval.json','reviewed-source-archive-first-verification-failure.json','reviewed-financial-source-archives.json','current-incumbent-runtime-before-full-finance.json','current-incumbent-runtime-identity.json']:verify(ART/name)
 incumbent=load(ART/'current-incumbent-runtime-identity.json')['projects']['coinquant'];require(len(incumbent['python_files'])==20,'twenty native runtime bytes')
 for p,h in incumbent['python_files'].items():eq(PROV['sources']['perp']['files'][p],h,'native incumbent unchanged');verify(ROOT/'coinquant'/p,h)
 require('from research.edge_assessment import' not in (ROOT/'coinquant/research/edge_forward.py').read_text() and "sys.path.insert" not in (ROOT/'coinquant/research/edge_forward.py').read_text(),'standalone Coin reader')
 for kind in ['spotquant','coinquant']:
  p=ART/(kind+'-reviewed-financial-source.tar.gz');verify(p)
  with tarfile.open(p,'r:gz') as t:
   for m in t.getmembers():
    if m.isfile() and m.name in PROV['sources']['spot' if kind=='spotquant' else 'perp']['files']:
     eq(hashlib.sha256(t.extractfile(m).read()).hexdigest(),PROV['sources']['spot' if kind=='spotquant' else 'perp']['files'][m.name],'original source archive byte');eq(m.mode,PROV['sources']['spot' if kind=='spotquant' else 'perp']['modes'][m.name],'original source archive mode')
 out={'passed':True,'bound_file_sha256':hashes,'actual_controller_phases':phases,'selected_budget_bindings':54,'coin_native_runtime_files':incumbent['python_files'],'first_failure_preserved':True,'one_resource_recovery':True,'assessment_only_correction':correction['additional_official_files'],'source_edits':0,'account_replays':0};put(dest,out);print('PROVENANCE SUPPLEMENT PASS',len(hashes),'files',len(phases),'phases',flush=True);return out

def features():
 f=load(arg('--features'));eq(sha(arg('--features')),R['environment']['features_sha256'],'feature actual');eq(hashlib.sha256(json.dumps({k:v for k,v in f.items() if k!='content_sha256'},sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(),f['content_sha256'],'feature content');raw=load(ART/'crowding-verified-before-edge.json');eq(sha(ART/'crowding-verified-before-edge.json'),f['source']['raw_sha256'],'verified original crowding');require(len(f['funding'])==7488 and len(f['basis'])==2485,'feature counts')
 for name,lag in [('funding',28800000),('basis',60000)]:
  require([x['observation_ms'] for x in f[name]]==sorted(set(x['observation_ms'] for x in f[name])),'unique feature times')
  for x in f[name]:require(x['available_ms']==x['observation_ms']+lag,'causal lag');require(x['value'] is None or D(x['value']).is_finite(),'finite feature')
 return f

def lookup(book,name,t):
 rows=book[name];i=bisect.bisect_right([r['available_ms'] for r in rows],t)-1
 if not START<=t<END:return None,'outside_frozen_window',None
 if i<0:return None,'not_yet_available',None
 r=rows[i];age=t-r['available_ms'];cause=None
 if name=='funding' and age>=28800000:cause='stale_funding'
 elif name=='basis' and age>DAY:cause='stale_basis'
 elif name=='basis' and r['available_ms']//DAY!=t//DAY:cause='basis_availability_date_mismatch'
 else:cause=r.get('cause')
 return None if cause else r['value'],cause,r

def journal(book):
 dest=OUT/'journal-sizing-supplement.json'
 if dest.exists():return load(dest)
 records={};files={a['path'] for a in A.values()};cutproof=[]
 for path in sorted(files):
  cp=OUT/('journal-'+hashlib.sha256(path.encode()).hexdigest()+'.json')
  if cp.exists():records.update(load(cp));continue
  bundle=load(path);out={}
  for key,a in A.items():
   if a['path']!=path:continue
   kind=a['kind'];row=bundle['results'][a['candidate']+'-'+a['scenario']] if kind=='spot' else bundle['results'][a['candidate']][a['scenario']];events=row['opportunity_ledger'];scale=D(R['calibration_documents'][kind]['profiles'][a['candidate']]['scale']) if a['risk'] else D(1);counts=Counter();samples=[];targets={};previous=None
   for i,e in enumerate(events):
    if kind=='spot' and e['event']=='decision':
     t=e['decision_ms'];require(e['completed_bar_ms']+DAY<=t,'completed causal daily');diagnostics=e['diagnostics'];desired=[o for o in e['desired_orders'] if o['side']=='BUY'];accepted=[o for o in e['accepted_orders'] if o['side']=='BUY']
     for d in diagnostics:
      if d['mechanism']=='new-buy':
       expected_scale=scale if t>=CUT else D(1);require(D(d['risk_scale'])==expected_scale,'actual new buy scale');counts['scaled_new_buy_after_cutoff' if t>=CUT else 'unity_before_cutoff']+=1
       before=next((D(o['quoteOrderQty']) for o in desired if o['sleeves']==d['sleeves']),None)
       if before is not None and a['candidate']=='exit-confirm' and not d['blocked_reason']:require(D(d['quote'])==(before*expected_scale//D('.01'))*D('.01'),'new BUY actual scale rounding')
       for o in accepted:
        if o['sleeves']==d['sleeves']:require(D(o['quoteOrderQty'])==D(d['quote']) and all(D(e['sleeves'][str(w)]['owned_btc'])<D('.00001') for w in o['sleeves']),'accepted held topup')
       if d['blocked_reason']:counts['blocked_new_buy']+=1
      elif d['mechanism']=='crowding-interaction':
       values=[]
       for inp in d['inputs']:
        v,cause,r=lookup(book,inp['name'],t);eq(inp['value'],v,'causal feature value');eq(inp['cause'],cause,'causal feature missing');values.append(v)
        if r:
         eq(inp['observation_ms'],r['observation_ms'],'feature observation');eq(inp['available_ms'],r['available_ms'],'feature publication')
       mom=d['momentum'];require(mom['current_completed_bar_ms']+DAY<=t,'causal trend');missing=any(v is None for v in values) or mom['prior_close'] is None
       hit=not missing and D(values[0])>D('.0003') and D(values[1])>D('.01') and D(mom['current_close'])<=D(mom['prior_close']);counts['crowding_halved' if hit else 'crowding_missing' if missing else 'crowding_unchanged']+=1
       if missing:require(not accepted,'missing blocks new BUY only')
       elif desired:
        before=D(desired[0]['quoteOrderQty']);expected=before/2 if hit else before;require(D(d['quote'])==expected,'once half crowding proposal')
       if hit or missing:samples.append({'index':i,'time':t,'kind':'crowding_exception','event_sha256':checksum(e),'missing':missing,'halve':hit})
      elif d['mechanism']=='stop-budget':
       counts['stop_budget']+=1
       if not d['blocked_reason'] and d['existing_risk'] is not None and desired:require(D(d['quote'])==min(D(desired[0]['quoteOrderQty']),max(D(0),D(d['budget'])-D(d['existing_risk']))/D(d['proposed_loss_per_quote'])),'actual stop budget cap')
     if i%997==0 or any(d.get('blocked_reason') for d in diagnostics):samples.append({'index':i,'time':t,'kind':'ownership_or_exception','event_sha256':checksum(e),'sleeves':e['sleeves'],'accepted_orders':e['accepted_orders']})
    elif kind=='perp':
     if e['event']=='decision':
      t=e['at_ms'];require(D(e['risk_scale'])==(scale if t>=CUT else D(1)),'Coin actual risk scale');counts['decision_scale']+=1
     if e['event']=='entry_sizing':targets[e['opportunity']]=e['desired_btc'];counts['new_committed_target']+=1
     if e['event']=='topup_sizing':
      require(e['opportunity'] in targets and D(e['desired_btc'])==D(targets[e['opportunity']]),'held Coin committed target changed');counts['held_target_unchanged']+=1
     if e['event']=='edge_predecision':
      for name,inp in e['rules']['features'].items():
       v,cause,r=lookup(book,name,e['at_ms']);eq(inp['value'],v,'Coin causal feature');eq(inp['cause'],cause,'Coin missing feature')
      counts['edge_predecision']+=1
     if e['event'] in ['entry_sizing','topup_sizing','write_attempt'] and (i%97==0 or e.get('constraint') not in [None,'target']):samples.append({'index':i,'event':e})
   if a['risk']:
    original=A[ident(kind,a['candidate'])];eq(a['curve'][:731],original['curve'][:731],'risk unchanged pre-cutoff curve');counts['training_daily_identity']=731
   out[key]={'raw_sha256':a['raw_sha256'],'events_scanned':len(events),'counts':dict(counts),'sample_rule':'all feature exceptional/missing and sizing constraints; deterministic every997th Spot decision/every97th Coin sizing; all decision scales and committed targets checked','samples':samples,'passed':True}
  put(cp,out);records.update(out);print('JOURNAL PASS',len(out),path,flush=True)
 put(dest,{'passed':True,'accounts':records,'zero_scale_contract':'Verified finite 0<=scale<=1 guards and multiply-new-only call sites; zero was not an actual fitted profile and no new boundary test was run.','features_sha256':sha(arg('--features'))});return records
if __name__=='__main__':
 try:provenance_extra();journal(features());print('SUPPLEMENT PASS',flush=True)
 except Exception:traceback.print_exc();sys.exit(1)
