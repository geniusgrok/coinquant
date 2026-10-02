"""Diagnostic only: retain failed unity controls; NEVER confers stage approval."""
import gc,gzip,hashlib,importlib.util,json,sys
from pathlib import Path
sys.path.insert(0,'/workspace/btc-alpha-beta-analysis/spotquant')
from research import alpha_assessment as a
R=Path('/workspace/btc-alpha-beta-next/review');O=Path('/workspace/scratch/alpha-beta-next');ROOT=Path('/workspace/btc-alpha-beta-next');identities={}
def read(p):return json.loads(Path(p).read_text())
def bind(p,want=None):
 p=Path(p);h=a.sha(p);assert want is None or h==want,(str(p),h,want);identities[str(p)]=h;return h
raw=O/'risk-perp.json.gz';rawsha=bind(raw)
command=read(O/'risk-perp.command.json');assert command['exit_code']==0 and command['source_head']=='acedaa43ca94223f24e2fe11851bbef74e032a69'
assert command['output_sha256']==rawsha and command['command'][command['command'].index('--out')+1]==str(raw)
reportpath=O/'registered-risk.json';receipt=read(O/'registered-risk.command.json');assert receipt['exit_code']==0 and receipt['source_head']=='99fcf005d2cb15c13bb37322b65ab2863b19d65e'
bind(reportpath,receipt['output_sha256']);report=read(reportpath);assert report['inputs']['risk_perp']['raw_sha256']==rawsha
aupath=R/'financial-audit-risk-perp.json';ar=read(R/'financial-audit-risk-perp.command.json');assert ar['exit_code']==0
bind(aupath,ar['output_sha256']);audit=read(aupath);assert audit['raw_sha256']==rawsha and audit['all_examined_checks_passed'] and audit['all_reported_complete']
for p in ['risk-perp.command.json','registered-risk.command.json']:bind(O/p)
for p in ['financial-audit-risk-perp.command.json','coin-unscaled20-financial-proof.json','coin-unscaled20-financial-review.md']:bind(R/p)
for c in ar['verification_context'].values():bind(c['path'],c['sha256'])
assert bind(R/'independent_financial_audit.py',ar['checker_sha256'])=='492d46ff9bbff72f1291ad77988fbf8478b35fd880c818e1d3979a6215f1897c'
bind(R/'financial-audit-risk-perp.run.log',ar['log_sha256'])
calpath=O/'registered-calibration.json';calsha=bind(calpath,'ed8c99295e71386a7cef300f7d101ea941e5a7a0147bc9038012d6cc58e23821');cal=read(calpath)
spotpath=O/'spot-project-calibration.json';bind(spotpath,'d574693fe94480c598dc1698b008147267227385ada31df82eab9498d38e7b2b');spot=read(spotpath)
assert {k:v for k,v in cal['profiles'].items() if k in a.SPEC['spot_candidates']}==spot['profiles']
original=read(R/'coin-unscaled20-financial-proof.json');oldraw=O/'perp-singletons-retry1.json.gz';bind(oldraw,'bf1d167979f4bb3d15925f0bcaf5337bd1cc0a17523628b3af0599875dc5a7c1')
assert original['identities'][str(oldraw)]==a.sha(oldraw)
oldreportpath=O/'registered-unscaled.json';bind(oldreportpath,original['identities'][str(oldreportpath)]);oldreport=read(oldreportpath)
for name in a.SPEC['perp_candidates']:assert cal['profiles'][name]==original['coin5_calibration'][name]['profile']
for module,path in [('ind',R/'independent_financial_audit.py'),('sizing',R/'coin_risk_actual_sizing_check.py')]:
 spec=importlib.util.spec_from_file_location(module,path);loaded=importlib.util.module_from_spec(spec);spec.loader.exec_module(loaded);globals()[module]=loaded
bind(R/'coin_risk_actual_sizing_check.py');public=sizing.public_daily_inputs()
data=ind.read(raw);rows=ind.labelled_rows(data,'perp');assert {r['candidate']+'/'+r['scenario'] for r in rows}=={n+'/base' for n in a.SPEC['perp_candidates']}
source=data['inputs']['source'];assert source==original['source']==data['inputs']['measured_source'] and data['inputs']['risk_calibration_sha256']==calsha
assert data['inputs']['risk_profiles']=={n:cal['profiles'][n] for n in a.SPEC['perp_candidates']}
# Every public 4h zip used for past-only sizing is part of the measured market identity.
vision={str(Path('/tmp/coinquant-market')/v['path']):v['sha256'] for v in data['inputs']['market_identity']['vision']}
for path,h in public[3].items():assert vision[path]==h
rates,marks,funding_public=ind.funding_inputs(rows);checks={}
for row in rows:
 key=row['candidate']+'/base';name=row['candidate'];profile=cal['profiles'][name];au=audit['accounts'][key]
 assert row['complete'] and row['audit']['passed'] and row['known_path'] and row['unknown_from'] is None and row['failure'] is None and row['execution_unresolved']==0 and len(row['sessions'])==795
 ledger=ind.perp(row,rates,marks);stats=ind.curves(row,'perp');assert ledger==au['ledger'] and stats==au['statistics']
 for k,v in ledger.items():
  if 'delta' in k:assert abs(ind.D(v))<ind.D('1e-12')
 assert abs(ind.D(row['fees'])-ind.D(ledger['commission']))<ind.D('1e-12') and abs(ind.D(row['funding'])-ind.D(ledger['funding_paid']))<ind.D('1e-12')
 assert ind.training_fingerprint(row,'perp')==original['accounts'][key]['training_ledger_sha256']
 assert stats['training_usdt']==original['accounts'][key]['statistics']['training_usdt']
 causal=sizing.check(row,profile['scale'],public)
 checks[key]={'scale':profile['scale'],'sessions':795,'reported_complete':True,'hindsight_bounded':row['hindsight_bounded'],'bounded_minutes':len(row['bounded_minutes']),'ledger':ledger,'statistics':stats,'sizing_causality':causal,'training731_actual_ledger_and_stats_unchanged':True,'cagr':row['cagr'],'mdd':row['mdd']}
 print(json.dumps({'actual_risk_account':key,'money_and_sizing_passed':True}),flush=True)
del data,rows;gc.collect()
env=a.environment(ROOT/'coinquant/research/session_schedule.json',ROOT/'starquant/data/usdcny_frankfurter.json',Path('/tmp/spotquant-market/klines'))
bars=a.load_daily(Path('/tmp/spotquant-market/klines'),a.END_MS,require_through=a.END_MS);fx=a.PriorFX(ROOT/'starquant/data/usdcny_frankfurter.json');usd,cny=a.market_returns_for(bars,fx)
bundle=a.consume(raw,'perp',env,bars,fx,usd,cny,expected=set(checks),reference=oldreport['inputs']['perp'],calibration=cal,calibration_sha=calsha)
initial=float(a.D(10000)/fx(a.START_MS)*a.D('.999'));baseline=bundle['accounts']['incumbent/base'];maxdiff=0
for key,acct in bundle['accounts'].items():
 assert acct['valid'] and not acct['rejections'];assert acct['evidence_sha256']==report['accounts']['perp/risk/'+key]['evidence_sha256']
 item=checks[key];item['evidence_sha256']=acct['evidence_sha256'];name=key.split('/')[0]
 if item['scale']=='1.0':item['unity_all_six_groups_equal']=acct['evidence_sha256']==original['accounts'][key]['evidence_sha256']
 else:assert name=='compression-breakout' and item['scale']=='0.7997705584944133';item['unity_all_six_groups_equal']=None
 stats=item['statistics'];financial=acct['financial']
 for independent,reg in [(stats['full_usdt'],financial['usdt_btc_regression']),(stats['full_cny'],financial['cny_btc_regression']),(stats['validation_usdt'],financial['validation_2022_plus']['regression'])]:
  pairs=[(independent['beta'],reg['beta_btc']),(independent['alpha_daily'],reg['intercept_daily']),(independent['hac7_se_daily'],reg['intercept_hac7_standard_error_daily'])]+list(zip(independent['alpha_annual_normal95'],reg['residual_arithmetic_annualized_normal95_descriptive']))
  for x,y in pairs:maxdiff=max(maxdiff,abs(x-y));assert abs(x-y)<1e-12
 matched=a.achieved_match(acct['curve'],baseline['curve'],usd,initial);comparison=ind.comparison(stats,checks['incumbent/base']['statistics']);assert matched['achieved_match']==comparison['validation_risk_match_achieved']
 independent_gain=(1+stats['validation_usdt']['cagr'])**(1723/365.25)-(1+checks['incumbent/base']['statistics']['validation_usdt']['cagr'])**(1723/365.25)
 assert abs(independent_gain-matched['validation_total_usdt_return_gain'])<1e-12
 item['actual_validation_match']=matched;item['risk_bands']=comparison;item['target_status']=acct['target_status']
 if name!='incumbent':
  observed=report['risk']['perp'][name]
  for k,v in matched.items():assert observed[k]==v,(name,k)
assert sum(c['unity_all_six_groups_equal'] is True for c in checks.values())==3
assert not report['risk_baseline_controls']['perp']['passed']
for path,h in identities.items():assert a.sha(path)==h
bind(Path(__file__))
proof={'format':'independent-coin-five-actual-risk-financial-diagnostic-blocked-v1','identities':identities,'raw_sha256':rawsha,'source':source,'analysis_source':a.source_identity(),'economic_inputs':env,'past_only_sizing_public4h_hashes':public[3],'public_funding_mark_input_hashes':funding_public,'accounts':checks,'four_unity_controls_all_six_groups_equal':False,'stage_approved':False,'blocking_control':report['risk_baseline_controls']['perp'],'strict_failed_attempt_log_sha256':bind(R/'coin-actual-risk-strict-first-attempt.log'),'max_independent_vs_immutable_regression_delta':maxdiff,'all_five_financial_causality_checks_passed':True,'scope':'Coin actual5 risk stage only; sensitivity/global final/bridge/adoption pending','native_cases':0,'actual_account_days':0,'continuous_proxy_independently_replayed':False}
with (R/'coin-actual-risk-financial-diagnostic-blocked.json').open('x') as f:json.dump(proof,f,indent=2)
print(json.dumps({'five_money_and_sizing_checks_passed_but_unity_gate_failed':True,'stage_approved':False,'max_regression_delta':maxdiff}))
