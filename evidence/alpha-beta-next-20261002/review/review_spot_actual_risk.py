"""Read-only complete Spot risk stage/source/statistical reconciliation."""
import gc,gzip,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'/workspace/btc-alpha-beta-analysis/spotquant')
from research import alpha_assessment as a
R=Path('/workspace/btc-alpha-beta-next/review');O=Path('/workspace/scratch/alpha-beta-next');ROOT=Path('/workspace/btc-alpha-beta-next')
def read(p):return json.loads(p.read_text())
receipt=read(O/'spot-early-risk-completed.json');raw=Path(receipt['actual_risk_path']);calpath=Path(receipt['actual_calibration_path']);cal=read(calpath)
assert a.sha(raw)==receipt['actual_risk_sha256'] and a.sha(calpath)==receipt['actual_calibration_sha256']
command=read(O/'risk-spot-project-early.command.json');assert command['exit_code']==0 and command['source_head']=='8ca002522fbdce531dcfbbb783ff4d152a7fd66c'
with gzip.open(raw,'rb') as f:uncompressed_sha=hashlib.file_digest(f,'sha256').hexdigest()
assert uncompressed_sha==command['output_sha256']
audit=read(R/'financial-audit-risk-spot-project-early.json');ar=read(R/'financial-audit-risk-spot-project-early.command.json')
assert ar['exit_code']==0 and ar['output_sha256']==a.sha(R/'financial-audit-risk-spot-project-early.json') and audit['raw_sha256']==a.sha(raw)
assert audit['all_examined_checks_passed'] and audit['all_reported_complete']
assert ar['checker_sha256']==a.sha(R/'independent_financial_audit.py')=='492d46ff9bbff72f1291ad77988fbf8478b35fd880c818e1d3979a6215f1897c'
for c in ar['verification_context'].values():assert a.sha(c['path'])==c['sha256']
for p in [R/'financial-audit-risk-spot-project-early.run.log',O/'risk-spot-project-early.log']:
 if p.exists():assert a.sha(p)==(ar if p.parent==R else command)['log_sha256']
env=a.environment(ROOT/'coinquant/research/session_schedule.json',ROOT/'starquant/data/usdcny_frankfurter.json',Path('/tmp/spotquant-market/klines'))
bars=a.load_daily(Path('/tmp/spotquant-market/klines'),a.END_MS,require_through=a.END_MS);fx=a.PriorFX(ROOT/'starquant/data/usdcny_frankfurter.json');usd,cny=a.market_returns_for(bars,fx)
expected={n+'/'+s for n in a.SPEC['spot_candidates'] for s in a.SPEC['spot_scenarios']}
base=a.consume(O/'spot-singletons/accounts-manifest.json','spot',env,bars,fx,usd,cny,expected=expected)
a.verify_execution_equivalence(base['metadata']['source'],a.source_identity(),'spot',env['spec_sha256'],env['protocol_sha256'])
original=a.original_baseline(ROOT/'spotquant/evidence/complete-delivery-20261001/spot-consensus-corrected.json','spot',base,env);assert original['passed']
doc,training=a.calibration_document({'spot':base},usd,fx);assert a.checksum(doc)==a.checksum(cal)
risk=a.consume(raw,'spot',env,bars,fx,usd,cny,expected={n+'/base' for n in cal['profiles']},reference=base,calibration=cal,calibration_sha=a.sha(calpath))
initial=float(a.D(10000)/fx(a.START_MS)*a.D('.999'));results={};maxdiff=0
for key,acct in risk['accounts'].items():
 assert acct['valid'] and not acct['rejections'];aud=audit['accounts'][key];assert aud['pre_cutoff_actual_ledger_equal_to_unscaled']
 stat=aud['statistics']['validation_usdt'];reg=acct['financial']['validation_2022_plus']['regression']
 for x,y in [(stat['beta'],reg['beta_btc']),(stat['alpha_daily'],reg['intercept_daily']),(stat['hac7_se_daily'],reg['intercept_hac7_standard_error_daily'])]+list(zip(stat['alpha_annual_normal95'],reg['residual_arithmetic_annualized_normal95_descriptive'])):
  maxdiff=max(maxdiff,abs(x-y));assert abs(x-y)<1e-12
 match=a.achieved_match(acct['curve'],base['accounts']['consensus/base']['curve'],usd,initial)
 assert match['achieved_match']==aud['baseline_comparison']['validation_risk_match_achieved']
 independent_gain=(1+stat['cagr'])**(1723/365.25)-(1+audit['accounts']['consensus/base']['statistics']['validation_usdt']['cagr'])**(1723/365.25)
 assert abs(independent_gain-match['validation_total_usdt_return_gain'])<1e-12
 results[key]={'raw_sha256':acct['raw_bundle_sha256'],'scale':cal['profiles'][acct['candidate']]['scale'],'valid':acct['valid'],'registered_cagr':acct['cagr'],'reported_continuous_mdd':acct['mdd'],'validation_usdt':stat,'match':match,'evidence_sha256':acct['evidence_sha256'],'training_ledger_equal':True,'fees_usdt':aud['ledger']['fees_usdt'],'core_pools':aud['core_pools']}
assert risk['accounts']['consensus/base']['evidence_sha256']==base['accounts']['consensus/base']['evidence_sha256']
paths=[raw,calpath,O/'spot-early-risk-completed.json',O/'risk-spot-project-early.command.json',O/'spot-project-calibration-proof.json',O/'spot-singletons/accounts-manifest.json',R/'financial-audit-risk-spot-project-early.json',R/'financial-audit-risk-spot-project-early.command.json',R/'financial-audit-spot-unscaled-comparison.json',R/'spot-actual-risk-sizing-proof.json',R/'spot_risk_actual_sizing_check.py',Path(__file__)]
proof={'identities':{str(p):a.sha(p) for p in paths},'raw_uncompressed_sha256':uncompressed_sha,'source':risk['metadata']['source'],'analysis_source':a.source_identity(),'economic_inputs':env,'exact28_unscaled_accounts':len(base['accounts']),'exact7_calibrated_accounts':len(results),'calibration_exactly_rederived_from731_training':True,'original_baseline_four_scenes_pass':True,'unity_control_all_six_groups_equal':True,'max_independent_vs_assessor_regression_delta':maxdiff,'accounts':results,'scope':'Spot actual risk stage only; no adoption/global outcome acceptance; continuous proxy not independently replayed'}
with (R/'spot-actual-risk-financial-proof.json').open('x') as f:json.dump(proof,f,indent=2)
print(json.dumps({'accounts':len(results),'max_regression_delta':maxdiff,'unity_g6':True,'classifications':{k:v['match']['classification'] for k,v in results.items()}}))
