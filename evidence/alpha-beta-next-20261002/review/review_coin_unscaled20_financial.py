"""Read-only completed Coin20 financial/source/statistical review; no producers or State."""
import gc,gzip,hashlib,importlib.util,json,sys
from collections import Counter
from pathlib import Path
sys.path.insert(0,'/workspace/btc-alpha-beta-analysis/spotquant')
from research import alpha_assessment as a
R=Path('/workspace/btc-alpha-beta-next/review');O=Path('/workspace/scratch/alpha-beta-next');ROOT=Path('/workspace/btc-alpha-beta-next')
raw=O/'perp-singletons-retry1.json.gz';RAWSHA='bf1d167979f4bb3d15925f0bcaf5337bd1cc0a17523628b3af0599875dc5a7c1';identities={}
def read(p):return json.loads(Path(p).read_text())
def bind(p,want=None):
 p=Path(p);h=a.sha(p);assert want is None or h==want,(str(p),h,want);identities[str(p)]=h;return h
bind(raw,RAWSHA)
completion=read(O/'perp-full-retry1.completion.json');assert completion['exit_code']==0 and completion['output_sha256']==RAWSHA
h=hashlib.sha256();size=0
with gzip.open(raw,'rb') as f:
 for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk);size+=len(chunk)
assert h.hexdigest()==completion['decompressed_json_sha256'] and size==completion['decompressed_json_bytes']==289863983
assert raw.stat().st_size==completion['output_bytes']==12869574
bind(completion['log_path'],completion['log_sha256'])
reportpath=O/'registered-unscaled.json';receipt=read(O/'registered-unscaled.command.json');assert receipt['exit_code']==0 and receipt['source_head']=='99fcf005d2cb15c13bb37322b65ab2863b19d65e'
bind(reportpath,receipt['output_sha256']);report=read(reportpath);argv=receipt['command'];assert argv[argv.index('--perp')+1]==str(raw) and argv[argv.index('--out')+1]==str(reportpath)
audpath=R/'financial-audit-perp-singletons.json';audreceipt=read(R/'financial-audit-perp-singletons.command.json');assert audreceipt['exit_code']==0
bind(audpath,audreceipt['output_sha256']);audit=read(audpath);assert audit['raw_sha256']==RAWSHA and audit['all_examined_checks_passed'] and audit['all_reported_complete']
assert bind(R/'independent_financial_audit.py',audreceipt['checker_sha256'])=='492d46ff9bbff72f1291ad77988fbf8478b35fd880c818e1d3979a6215f1897c'
bind(R/'financial-audit-perp-singletons.run.log',audreceipt['log_sha256'])
calpath=O/'registered-calibration.json';bind(calpath,report['calibration_sha256']);cal=read(calpath)
for name in ['perp-full-retry1.completion.json','registered-unscaled.command.json','registered-calibration.json','serial-retry1-registration.json']:bind(O/name)
for name in ['financial-audit-perp-singletons.command.json','financial-audit-unscaled-index.json','spot-actual-risk-financial-proof.json','parallel-sensitivity-operational-approval-retraction.md']:bind(R/name)
s=importlib.util.spec_from_file_location('independent',R/'independent_financial_audit.py');ind=importlib.util.module_from_spec(s);s.loader.exec_module(ind)
data=ind.read(raw);rows=ind.labelled_rows(data,'perp');assert len(rows)==20
source=data['inputs']['source'];a.verify_source(source,'perp');assert source==data['inputs']['measured_source']==audit['source']
assert source['git_head']=='acedaa43ca94223f24e2fe11851bbef74e032a69' and source['python_sources_sha256']=='a6e3f30f02208ff7e604b6181c5d8fa7000fe7e30dbc3276fbcc93ffbb0ad227'
assert data['conditions']['terminal_funding_exclusive_ms']==ind.END and data['conditions']['post_run_diagnostic_prices_used_for_decisions'] is False
rates,marks,public=ind.funding_inputs(rows);assert public==audit['public_funding_mark_inputs']
checks={}
for row in rows:
 key=row['candidate']+'/'+row['scenario'];au=audit['accounts'][key]
 assert row['complete'] and row['audit']['passed'] and row['known_path'] and row['unknown_from'] is None and row['failure'] is None and row['execution_unresolved']==0 and len(row['sessions'])==795
 money=ind.perp(row,rates,marks);stats=ind.curves(row,'perp');assert money==au['ledger'] and stats==au['statistics']
 for k,v in money.items():
  if 'delta' in k:assert abs(ind.D(v))<ind.D('1e-12')
 totals={}
 for event in row['funding_ledger']:totals[event['incomeType']]=totals.get(event['incomeType'],ind.D(0))+ind.D(event['income']);assert ind.START<=event['time']<ind.END
 assert not totals.get('INSURANCE_CLEAR',0) and row['funnel']['liquidations']==row['funnel']['gap_forfeits']==0
 assert abs(ind.D(row['fees'])-ind.D(money['commission']))<ind.D('1e-12') and abs(ind.D(row['funding'])-ind.D(money['funding_paid']))<ind.D('1e-12')
 journal=row['opportunity_ledger'];counts=Counter(e['event'] for e in journal);journalfills=[e['trade'] for e in journal if e['event']=='fill'];assert journalfills==row['trades']
 decisions=[e for e in journal if e['event']=='decision'];ages=[]
 for e in decisions:
  assert ind.START<=e['at_ms']<ind.END and e['bar_ms']<=e['at_ms'] and ind.D(e['risk_scale'])==1
  if e.get('age_ms') is not None:assert e['age_ms']>=0;ages.append(e['age_ms'])
  if e.get('trigger'):
   trigger=e['trigger'];created=trigger.get('created_at_ms',trigger.get('at_ms'))
   if created is not None:assert created<=e['at_ms']
 cagr=(float(row['final_cny'])/10000)**(365.2425*ind.DAY/(ind.END-ind.START))-1;assert abs(cagr-row['cagr'])<1e-12
 assert stats['full_usdt']['days']==2454 and stats['training_usdt']['days']==731 and stats['validation_usdt']['days']==1723
 checks[key]={'reported_complete':True,'sessions':795,'known_path':True,'hindsight_bounded':row['hindsight_bounded'],'bounded_minutes_count':len(row['bounded_minutes']),'unknown_from':None,'liquidations':0,'gap_forfeits':0,'registered_cagr':row['cagr'],'reported_continuous_mdd':row['mdd'],'ledger':money,'statistics':stats,'journal_event_counts':dict(counts),'journal_fill_records_equal_actual_trades':True,'past_trigger_age_checks':len(ages),'training_ledger_sha256':ind.training_fingerprint(row,'perp')}
 print(json.dumps({'account':key,'ledger_stats_passed':True}),flush=True)
del rows,data;gc.collect()
env=a.environment(ROOT/'coinquant/research/session_schedule.json',ROOT/'starquant/data/usdcny_frankfurter.json',Path('/tmp/spotquant-market/klines'))
bars=a.load_daily(Path('/tmp/spotquant-market/klines'),a.END_MS,require_through=a.END_MS);fx=a.PriorFX(ROOT/'starquant/data/usdcny_frankfurter.json');usd,cny=a.market_returns_for(bars,fx)
expected={n+'/'+s for n in a.SPEC['perp_candidates'] for s in a.SPEC['perp_scenarios']}
bundle=a.consume(raw,'perp',env,bars,fx,usd,cny,expected=expected)
oldpath=ROOT/'coinquant/evidence/complete-delivery-20261001/perp-exclusive-accounts.json';baseline=a.original_baseline(oldpath,'perp',bundle,env);assert baseline['passed'] and baseline==report['baseline_verification']['perp'];bind(oldpath,baseline['raw_sha256'])
maxdiff=0
for key,acct in bundle['accounts'].items():
 assert acct['valid'] and not acct['rejections'];recorded=report['accounts']['perp/'+key];assert acct['evidence_sha256']==recorded['evidence_sha256'] and acct['cagr']==recorded['cagr'] and acct['mdd']==recorded['mdd']
 checks[key]['evidence_sha256']=acct['evidence_sha256'];checks[key]['target_status']=acct['target_status']
 financial=acct['financial'];st=checks[key]['statistics']
 for independent,reg in [(st['full_usdt'],financial['usdt_btc_regression']),(st['full_cny'],financial['cny_btc_regression']),(st['validation_usdt'],financial['validation_2022_plus']['regression'])]:
  pairs=[(independent['beta'],reg['beta_btc']),(independent['alpha_daily'],reg['intercept_daily']),(independent['hac7_se_daily'],reg['intercept_hac7_standard_error_daily'])]+list(zip(independent['alpha_annual_normal95'],reg['residual_arithmetic_annualized_normal95_descriptive']))
  for x,y in pairs:maxdiff=max(maxdiff,abs(x-y));assert abs(x-y)<1e-12
 doc_training=checks[key]['statistics']['training_usdt']
assert set(checks)==expected
coin_doc,training=a.calibration_document({'perp':bundle},usd,fx)
spot_doc=read(O/'spot-project-calibration.json');bind(O/'spot-project-calibration.json')
assert cal==dict(coin_doc,profiles={**spot_doc['profiles'],**coin_doc['profiles']}) and len(cal['profiles'])==12
baseline_stats=checks['incumbent/base']['statistics'];independent_scales={}
for name,profile in coin_doc['profiles'].items():
 value=ind.comparison(checks[name+'/base']['statistics'],baseline_stats)['training_only_unscaled_risk_scale'];assert abs(float(profile['scale'])-value)<1e-12
 independent_scales[name]={'profile':profile,'independent_scale':value,'training':checks[name+'/base']['statistics']['training_usdt']}
# Mechanical unscaled eligibility independently from actual complete rows.
manual={};scenes=a.SPEC['perp_scenarios'];names=a.SPEC['perp_candidates']
for name in names:
 rows=[checks[name+'/'+s] for s in scenes];base=[checks['incumbent/'+s] for s in scenes]
 paired=all(x['registered_cagr']>=b['registered_cagr']-.01 and float(x['reported_continuous_mdd'])<.5 for x,b in zip(rows,base))
 improved=rows[0]['registered_cagr']>=base[0]['registered_cagr']+.01 or(float(rows[0]['reported_continuous_mdd'])<=float(base[0]['reported_continuous_mdd'])-.01 and rows[0]['registered_cagr']>=base[0]['registered_cagr']-.01)
 eligible=name!='incumbent' and paired and improved
 assert eligible==report['selection']['perp']['decisions'][name]['eligible'];manual[name]={'eligible':eligible,'paired_constraints':paired,'base_improvement':improved,'worst_cagr':min(x['registered_cagr'] for x in rows)}
assert not any(x['eligible'] for x in manual.values()) and report['selection']['perp']['selected_research_candidate']=='incumbent' and report['selection']['perp']['compatible_components']==[]
assert not report['rules_freeze_ready'] and report['registered_work_pending']
for path,h in identities.items():assert a.sha(path)==h
bind(Path(__file__))
proof={'format':'coin-unscaled20-independent-financial-review-v1','identities':identities,'source':source,'analysis_source':a.source_identity(),'raw_uncompressed_sha256':completion['decompressed_json_sha256'],'economic_inputs':env,'public_funding_mark_input_hashes':public,'original_baseline_verification':baseline,'accounts':checks,'global12_calibration_exact_project_union':True,'coin5_calibration':independent_scales,'manual_unscaled_selection':manual,'selected_research_candidate':'incumbent','all20_financial_checks_passed':True,'max_independent_vs_immutable_regression_difference':maxdiff,'native_cases':0,'actual_account_days':0,'scope':'Coin unscaled20 only; actual risk5/global final/sensitivity/adoption remain pending','limitations':['Continuous historical envelope not independently replayed','Hindsight bounded minutes retained explicitly; public proxies are not native','Recorded loaded print/minute provenance retained; historical evicted print files not downloaded or recreated']}
with (R/'coin-unscaled20-financial-proof.json').open('x') as f:json.dump(proof,f,indent=2)
print(json.dumps({'complete_accounts':len(checks),'max_regression_delta':maxdiff,'all20_passed':True,'selection':'incumbent'}))
