"""Exact five-case source-bound financial bridge, read-only; no replay or source override."""
import gc,gzip,hashlib,importlib.util,json,sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0,'/workspace/btc-alpha-beta-analysis/spotquant')
from research import alpha_assessment as a
R=Path('/workspace/btc-alpha-beta-next/review');O=Path('/workspace/scratch/alpha-beta-next');C=O/'spot-canonical';ROOT=Path('/workspace/btc-alpha-beta-next')
HEAD='0c52c812301de3712f3637a1ce1b1241de0c40f1';PY='619570fb7baa586f28ad5de2a440d7752a536cc8f8ce7e357264612e65801537'
FROZEN={'git_head':'8ca002522fbdce531dcfbbb783ff4d152a7fd66c','dirty':False,'python_sources_sha256':'0df8c537ee8d47db6e841778e8e37eac847e1a0c1151e379440081b9473ae026'}
CANON={'git_head':HEAD,'dirty':False,'python_sources_sha256':PY}
def read(p):return json.loads(p.read_text())
identities={}
def bind(p,expected=None):
 p=Path(p);h=a.sha(p);assert expected is None or h==expected,(str(p),h,expected);identities[str(p)]=h;return h
inv=read(C/'canonical-inventory.json');bind(C/'canonical-inventory.json')
assert inv['format']=='canonical-spot-five-v1' and inv['source_head']==HEAD
assert inv['adoption_approved'] is False and inv['native_cases']==inv['actual_account_days']==0
expected=[('base','base',False),('fee150','fee150',False),('slip2','slip2',False),('outage','outage',False),('calibrated-base','base',True)]
assert [(x['label'],x['scenario'],x['calibrated']) for x in inv['files']]==expected
assert len(inv['runs'])==5
for p,h in inv['launch_bindings'].items():bind(p,h)
assert set(inv['review_bindings'])<=set(inv['launch_bindings']) and len(inv['review_bindings'])==2
for p,h in inv['review_bindings'].items():
 bind(p,h);text=Path(p).read_text();assert HEAD in text and 'PASS' in text and 'APPROVE' in text
calpath=Path(inv['calibration_path']);bind(calpath,inv['calibration_sha256']);cal=read(calpath)
rawrisk=Path(inv['reference_risk_path']);bind(rawrisk,inv['reference_risk_sha256']);bind(O/'spot-early-risk-completed.json',inv['reference_completion_receipt_sha256'])
refraw=O/'spot-singletons/atr-stop.json.gz';bind(refraw,'f8f2e18abbeb7f062796026c074fb7868e3b2524a52c5a5bcf89131b6e655917')
for name in ['financial-audit-spot-atr-stop.json','financial-audit-risk-spot-project-early.json','spot-actual-risk-financial-review.md','spot-actual-risk-financial-proof.json','spot-adoption-financial-boundary-fix1-review.md','spot-canonical-controller-fix1-review.md']:bind(R/name)
assert bind(R/'independent_financial_audit.py')=='492d46ff9bbff72f1291ad77988fbf8478b35fd880c818e1d3979a6215f1897c'
s=importlib.util.spec_from_file_location('independent_money',R/'independent_financial_audit.py');ind=importlib.util.module_from_spec(s);s.loader.exec_module(ind)
env=a.environment(ROOT/'coinquant/research/session_schedule.json',ROOT/'starquant/data/usdcny_frankfurter.json',Path('/tmp/spotquant-market/klines'))
bars=a.load_daily(Path('/tmp/spotquant-market/klines'),a.END_MS,require_through=a.END_MS);fx=a.PriorFX(ROOT/'starquant/data/usdcny_frankfurter.json');usd,cny=a.market_returns_for(bars,fx)
assert a.sha(a.__file__)=='a5bb0569f25e66b5aa660b0106d42c3ecffc7f30ebc5e2cf1b1216958ff43edf'
for source in [FROZEN,CANON,a.source_identity()]:a.verify_source(source,'spot')
try:a.verify_execution_equivalence(FROZEN,CANON,'spot',env['spec_sha256'],env['protocol_sha256'])
except ValueError as e:source_gate_rejection=str(e);assert 'not equivalent' in source_gate_rejection
else:raise AssertionError('canonical runtime must not be falsely declared source equivalent')
refs=a.consume(refraw,'spot',env,bars,fx,usd,cny,expected={'atr-stop/'+s for s in a.SPEC['spot_scenarios']})
risk=a.consume(rawrisk,'spot',env,bars,fx,usd,cny,expected={n+'/base' for n in cal['profiles']},calibration=cal,calibration_sha=a.sha(calpath))
assert refs['metadata']['source']==risk['metadata']['source']==FROZEN
reference_risk=risk['accounts']['atr-stop/base'];del risk;gc.collect()
auditplain=read(R/'financial-audit-spot-atr-stop.json');auditrisk=read(R/'financial-audit-risk-spot-project-early.json')
assert auditplain['raw_sha256']==a.sha(refraw) and auditrisk['raw_sha256']==a.sha(rawrisk)
assert auditplain['all_examined_checks_passed'] and auditrisk['all_examined_checks_passed']
results={};prior_end=0
for item,run,(label,scenario,calibrated) in zip(inv['files'],inv['runs'],expected):
 path=C/item['path'];bind(path,item['sha256']);commandpath=C/(label+'.command.json');compressionpath=C/(label+'.compression.json');logpath=C/(label+'.run.log')
 bind(commandpath);bind(compressionpath);command=read(commandpath);comp=read(compressionpath)
 assert dict(command,retained_sha256=item['sha256'])==run
 assert run['label']==label and run['scenario']==scenario and run['calibrated']==calibrated and run['source_head']==HEAD and run['exit_code']==0
 assert run['cwd']=='/workspace/btc-alpha-beta-adoption/spotquant' and run['review_bindings']==inv['review_bindings'] and run['launch_bindings']==inv['launch_bindings']
 argv=run['command'];expected_args=['-u','-m','research.adoption_spot','--scenario',scenario,'--out',str(C/(label+'.json'))]+(['--risk-calibration',str(calpath)] if calibrated else [])
 assert argv[1:]==expected_args
 start=datetime.fromisoformat(run['started_utc']).timestamp();assert start>=prior_end;prior_end=start+run['elapsed_seconds']
 bind(logpath,run['log_sha256'])
 h=hashlib.sha256();size=0
 with gzip.open(path,'rb') as stream:
  for chunk in iter(lambda:stream.read(1048576),b''):h.update(chunk);size+=len(chunk)
 assert h.hexdigest()==comp['original_sha256']==run['output_sha256'];assert size==comp['original_bytes']
 assert comp['retained_sha256']==item['sha256'] and comp['retained_bytes']==path.stat().st_size and comp['lossless_roundtrip_verified'] is True
 bundle,_=a.read_json(path);assert bundle['source']==CANON and set(bundle['results'])=={'atr-stop-'+scenario}
 row=bundle['results']['atr-stop-'+scenario];adopt=bundle['adoption'];identity=row['research_identity'];profile=dict(cal['profiles']['atr-stop'],sha256=a.sha(calpath)) if calibrated else {'scale':'1','sha256':None}
 assert adopt==identity and identity['execution']=='canonical_shared_session' and identity['rule']=='2026-10-02-atr-stop'
 assert identity['candidate']=='atr-stop' and identity['components']==['atr-stop'] and identity['core_mode'] is None and identity['core_fraction']=='0'
 assert identity['cutoff_ms']==1640995200000 and identity['profile']==row['risk_calibration']==profile
 assert identity['scale']==identity['risk_scale']==profile['scale'] and identity['calibration_sha256']==bundle['risk_calibration_sha256']==profile['sha256']
 assert identity['profile_sha256']==hashlib.sha256(json.dumps(profile,sort_keys=True).encode()).hexdigest()
 assert row['opportunity_ledger']==[] and row['subpools'] is None and bundle['native_execution_verified'] is False
 money=ind.spot(row);stats=ind.curves(row,'spot')
 for k,v in money.items():
  if 'delta' in k:assert abs(ind.D(v))<ind.D('1e-12')
 del bundle,row;gc.collect()
 # No reference override: each source passes its own genuine metadata/source gate.
 account=a.consume(path,'spot',env,bars,fx,usd,cny,expected={'atr-stop/'+scenario},calibration=cal if calibrated else None,calibration_sha=a.sha(calpath) if calibrated else None)['accounts']['atr-stop/'+scenario]
 reference=reference_risk if calibrated else refs['accounts']['atr-stop/'+scenario]
 assert account['valid'] and reference['valid'] and not account['rejections'] and not reference['rejections']
 g6={k:account['evidence_sha256'][k]==v for k,v in reference['evidence_sha256'].items()}
 assert len(g6)==6 and all(g6.values())
 frozen_audit=(auditrisk if calibrated else auditplain)['accounts']['atr-stop/'+scenario]
 assert money==frozen_audit['ledger'] and stats==frozen_audit['statistics']
 results[label]={'raw_path':str(path),'compressed_sha256':item['sha256'],'original_json_sha256':h.hexdigest(),'command_receipt_sha256':a.sha(commandpath),'compression_receipt_sha256':a.sha(compressionpath),'reference_raw_sha256':reference['raw_bundle_sha256'],'calibration_sha256':profile['sha256'],'scale':profile['scale'],'source':CANON,'reference_source':FROZEN,'valid':True,'evidence_equal':g6,'evidence_sha256':account['evidence_sha256'],'independent_ledger':money,'independent_statistics':stats,'registered_cagr':account['cagr'],'reported_continuous_mdd':account['mdd'],'verified_frozen_audit_propagated_after_complete_six_group_equality':True}
 print(json.dumps({'case':label,'six_groups_equal':True,'ledger_equal':True}),flush=True)
 del account;gc.collect()
for path,h in identities.items():assert a.sha(path)==h
bind(Path(__file__))
proof={'format':'independent-canonical-five-financial-bridge-v1','identities':identities,'canonical_source':CANON,'frozen_source':FROZEN,'analysis_source':a.source_identity(),'economic_inputs':env,'unchanged_old_source_gate_rejects_new_runtime':source_gate_rejection,'cases':results,'all_five_complete_and_six_groups_equal':True,'scope':'five-account exact financial equivalence only; no global/adoption approval','adoption_approved':False,'native_cases':0,'actual_account_days':0,'limitations':['Continuous OHLC proxy not independently replayed.','Archive validity/flags/hashes checked; backup contents not reopened.','Historical research contamination unchanged.']}
with (R/'spot-canonical-five-financial-proof.json').open('x') as stream:json.dump(proof,stream,indent=2)
