"""Read-only final review reconciliation; uses existing audits, never runs a checker/producer."""
import json, hashlib
from pathlib import Path
from decimal import Decimal as D
R=Path('/workspace/btc-alpha-beta-next/review');O=Path('/workspace/scratch/alpha-beta-next');ids={}
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text())
def bind(p,expected=None):
 z=sha(p);assert expected is None or z==expected,(str(p),z,expected);ids[str(p)]=z;return z
fp=O/'registered-final-repaired.json';bind(fp,'a35ef6727d1a3befa1c86778eadc3bb604ffff3ad2b7cb63275419dc30c9a5d6');f=read(fp)
cp=O/'registered-final-repaired.command.json';bind(cp,'0d93d033818604eb8d849e854c092b9e764537da2b296ffc05bc39bb217f1431');cr=read(cp)
assert cr['exit_code']==0 and cr['output_sha256']==sha(fp) and cr['source_head']=='99fcf005d2cb15c13bb37322b65ab2863b19d65e'
assert cr['command'].count('--final')==1 and cr['command'][cr['command'].index('--out')+1]==str(fp);bind(O/'registered-final-repaired.run.log',cr['log_sha256'])
assert not f['pending'] and not f['registered_work_pending'] and not f['risk_accounts_pending'] and f['all_measured_accounts_valid'] and f['rules_freeze_ready']
assert f['native_cases']==f['actual_account_days']==0 and f['prospective_alpha_proven'] is False
ip=R/'financial-audit-remaining-repaired-index.json';bind(ip,'0d78b9355deb09f7597be3b756aa51c209980188536d186c3b5a72d7dcb6a44e');index=read(ip)
assert index['final_assessment_sha256']==sha(fp) and (index['account_count'],index['unscaled_account_count'],index['full_registered_account_count'])==(16,48,64)
for k in ['all_examined_checks_passed','all_reported_complete','all64_exactly_reconciled','final_inventory_exactly_reconciled']:assert index[k] is True
assert not index['adoption_approval'] and not index['continuous_proxy_independently_replayed']
bind(R/'audit_repaired_remaining_registered.py','8366717a1758ba57998c89baa067a4ef23443ba538222ae1e259bbc00df0fdc5');assert index['helper_sha256']==sha(R/'audit_repaired_remaining_registered.py')
for p,z in index['preserved_evidence_sha256'].items():bind(p,z)
checker=R/'independent_financial_audit.py';bind(checker,'492d46ff9bbff72f1291ad77988fbf8478b35fd880c818e1d3979a6215f1897c')
rp=R/'final64-actual-repair-provenance-proof.json';bind(rp,'d844ce8274cb4e8cee1d19ad7ec94407c86c7716910ed8456376f17654af0eeb');repair=read(rp)
for p,z in repair['identities'].items():bind(p,z)
assert repair['all_four_unity_six_groups_exact'] and repair['projection_only_declared_changes'] and repair['new_incumbent_causal_quantity_check']['owned_quantities_equal_actual_cumulative_fills']
op=O/'registered-final.json';bind(op,'538b7a3614d07088b6ac5db1bee25392dd08a45e543d714d5ad5702fa02db05b');old=read(op)
assert not old['rules_freeze_ready'] and {k:v['rejections'] for k,v in old['accounts'].items() if not v['valid']}=={'perp/risk/incumbent/base':['unity_control_evidence_mismatch']}
for k in ['baseline_verification','selection','sensitivity','passive_controls','training','calibration_sha256','calibration_scope','risk_calibrations','limitations','native_cases','actual_account_days']:assert f[k]==old[k],k
for key,a in f['accounts'].items():
 assert a['valid'] and not a['rejections']
 if not key.startswith('perp/risk/'):assert a==old['accounts'][key]
 elif key!='perp/risk/incumbent/base':assert {k:v for k,v in a.items() if k!='raw_bundle_sha256'}=={k:v for k,v in old['accounts'][key].items() if k!='raw_bundle_sha256'}
 else:
  for k in ['cagr','mdd','target_status','financial']:assert a[k]==old['accounts'][key][k]
for kind in ['spot','perp']:
 b=f['baseline_verification'][kind];assert b['passed'] and len(b['evidence_checks'])==4 and all(len(g)==6 and all(g.values()) for g in b['evidence_checks'].values())
 c=f['risk_baseline_controls'][kind];assert c['passed'] and not c['rejections'] and len(c['evidence_checks'])==6 and all(c['evidence_checks'].values())
expected={}
for key,a in f['accounts'].items():
 parts=key.split('/');identity=(parts[0],'risk' if len(parts)==4 else 'unscaled',a['candidate']+'/'+a['scenario'],a['raw_bundle_sha256']);assert identity not in expected;expected[identity]=a
for s in f['sensitivity']:
 a=s['account'];identity=('perp','sensitivity',a['candidate']+'/'+a['scenario'],s['raw_sha256']);assert identity not in expected and a['raw_bundle_sha256']==s['raw_sha256'];expected[identity]=a
assert len(expected)==64
up=R/'financial-audit-unscaled-index.json';bind(up,'c1fdd880d44acd052a780a63aebcfd9df48d31367229692d6049d14bacbaae88');ui=read(up);assert ui['account_count']==48
entries=[(e['path'],e['sha256'],e['raw_sha256'],'unscaled',e) for e in ui['audits']]+[(e['audit_path'],e['audit_sha256'],e['raw_sha256'],e['stage'],e) for e in index['audits']]
seen={};risks={};unscaled={};maxreg=0;maxmoney=D(0);summary=[];outage=[]
for path,report_sha,raw_sha,stage,entry in entries:
 ap=Path(path);bind(ap,report_sha);au=read(ap);raw=Path(au['raw_path']);bind(raw,raw_sha);assert au['raw_sha256']==raw_sha and au['all_examined_checks_passed'] and au['all_reported_complete'];kind=au['kind']
 if stage!='unscaled':
  arp=ap.with_suffix('.command.json');ar=read(arp);bind(arp);bind(ap.with_suffix('.run.log'),ar['log_sha256']);assert ar['exit_code']==0 and ar['checker_sha256']==sha(checker) and ar['output_sha256']==sha(ap)
  cmd=ar['command'];want=[cmd[0],str(checker),'--bundle',str(raw),'--sha256',sha(raw),'--kind',kind,'--out',str(ap)]
  if stage=='risk':
   calpath=O/('registered-calibration.json' if kind=='perp' else 'spot-project-calibration.json');basepath=R/('financial-audit-perp-singletons.json' if kind=='perp' else 'financial-audit-spot-unscaled-comparison.json')
   ctx={'calibration':{'path':str(calpath),'sha256':sha(calpath)},'baseline_audit':{'path':str(basepath),'sha256':sha(basepath)},'unscaled_audit':{'path':str(basepath),'sha256':sha(basepath)}};want+=['--calibration',str(calpath),'--baseline-audit',str(basepath),'--unscaled-audit',str(basepath)]
  else:ctx={}
  assert ar['verification_context']==ctx and cmd==want
  assert entry['account_keys']==sorted(au['accounts']) and entry['accounts']==len(au['accounts'])
  for v in ctx.values():bind(v['path'],v['sha256'])
 for key,a in au['accounts'].items():
  identity=(kind,stage,key,raw_sha);assert identity in expected and identity not in seen;account=expected[identity];seen[identity]={'audit_path':str(ap),'audit_sha256':sha(ap),'raw_path':str(raw)}
  assert a['independent_checks_passed'] and not a['errors'] and a['producer_audit_passed'] and a['reported_complete']
  # Frozen Spot outage omits six registered March2020 starts, not incomplete execution.
  sessions=789 if kind=='spot' and key.endswith('/outage') else 795
  assert a['sessions']==sessions,(key,a['sessions'],sessions)
  if sessions==789:outage.append(key)
  st=a['statistics'];assert st['full_usdt']['days']==st['full_cny']['days']==2454 and st['validation_usdt']['days']==1723 and st['training_usdt']['days']==731
  for k,v in a['ledger'].items():
   if 'delta' in k and isinstance(v,(str,int,float)):assert abs(D(str(v)))<D('1e-12');maxmoney=max(maxmoney,abs(D(str(v))))
  fin=account['financial']
  for stats,reg in [(st['full_usdt'],fin['usdt_btc_regression']),(st['full_cny'],fin['cny_btc_regression']),(st['validation_usdt'],fin['validation_2022_plus']['regression'])]:
   pairs=[(stats['beta'],reg['beta_btc']),(stats['alpha_daily'],reg['intercept_daily']),(stats['hac7_se_daily'],reg['intercept_hac7_standard_error_daily'])]+list(zip(stats['alpha_annual_normal95'],reg['residual_arithmetic_annualized_normal95_descriptive']))
   for v,w in pairs:assert abs(v-w)<1e-12;maxreg=max(maxreg,abs(v-w))
  assert fin['annualization']['account_year_days']==(365.2425 if kind=='perp' else 365.25) and fin['annualization']['daily_metrics_cagr_year_days']==365.25 and fin['annualization']['account_end_exclusive_ms']==1789862400000
  if stage=='risk':risks[(kind,key)]=a
  if stage=='unscaled':unscaled[(kind,key)]=a
 summary.append({'audit_path':str(ap),'audit_sha256':sha(ap),'raw_sha256':raw_sha,'kind':kind,'stage':stage,'accounts':len(au['accounts'])})
assert set(seen)==set(expected) and len(risks)==12 and len(unscaled)==48 and len(outage)==7
calp=O/'registered-calibration.json';bind(calp,'ed8c99295e71386a7cef300f7d101ea941e5a7a0147bc9038012d6cc58e23821');cal=read(calp)
sp=O/'spot-project-calibration.json';bind(sp,'d574693fe94480c598dc1698b008147267227385ada31df82eab9498d38e7b2b');spotcal=read(sp);assert {k:v for k,v in cal['profiles'].items() if k in spotcal['profiles']}==spotcal['profiles'] and len(cal['profiles'])==12
profiles={}
for (kind,key),a in risks.items():
 name=key.split('/')[0];baseline='incumbent' if kind=='perp' else 'consensus';original=unscaled[(kind,key)];train=original['statistics']['training_usdt'];b=unscaled[(kind,baseline+'/base')]['statistics']['training_usdt'];profile=cal['profiles'][name]
 scales=[1.0]
 if train['annual_vol']>0:scales.append(b['annual_vol']/train['annual_vol'])
 if train['beta']>b['beta'] and train['beta']>0:scales.append(max(.01,b['beta'])/max(.01,train['beta']))
 recomputed=min(scales);assert abs(float(profile['scale'])-recomputed)<1e-12,(name,profile['scale'],recomputed)
 assert profile['effective_from_ms']==profile['calibration_end_ms']==1640995200000 and profile['training_end_day_exclusive']=='2022-01-01' and profile['baseline_candidate']==baseline
 assert a['pre_cutoff_actual_ledger_equal_to_unscaled'] and a['training_ledger_sha256']==original['training_ledger_sha256'] and a['statistics']['training_usdt']==train
 val=a['statistics']['validation_usdt'];bv=risks[(kind,baseline+'/base')]['statistics']['validation_usdt'];matched=val['beta']<=bv['beta']+.02 and val['annual_vol']<=bv['annual_vol']*1.05;gain=(1+val['cagr'])**(1723/365.25)-(1+bv['cagr'])**(1723/365.25)
 if name!=baseline:
  item=f['risk'][kind][name];assert item['status']=='measured_valid' and item['achieved_match']==matched and abs(item['validation_total_usdt_return_gain']-gain)<1e-12
 profiles[kind+'/'+name]={'profile':profile,'scale_recomputed_from_actual731':recomputed,'training_ledger_and_statistics_unchanged':True,'validation_beta':val['beta'],'validation_annual_volatility':val['annual_vol'],'achieved_match':matched,'validation_cumulative_usdt_gain':gain,'validation_hac95_annual_arithmetic':val['alpha_annual_normal95']}
for name in ['spot-actual-risk-financial-proof.json','spot-actual-risk-sizing-proof.json','coin-actual-risk-financial-diagnostic-blocked.json','coin-four-sensitivity-financial-proof.json','spot-canonical-five-financial-proof.json']:bind(R/name)
prior=read(R/'coin-actual-risk-financial-diagnostic-blocked.json');assert prior['raw_sha256']=='3b958b2e92d8aefcf7b9f073a3916c325420a546cf7652203ce6692be5ee2446' and prior['all_five_financial_causality_checks_passed'] and prior['stage_approved'] is False
for name in ['fresh-entry','atr-trail','compression-breakout','single-topup']:
 a=risks[('perp',name+'/base')];before=prior['accounts'][name+'/base'];assert a['ledger']==before['ledger'] and a['statistics']==before['statistics'] and before['sizing_causality']['all_checks_passed']
spotprior=read(R/'spot-actual-risk-financial-proof.json');sizes=read(R/'spot-actual-risk-sizing-proof.json');assert sizes['raw_sha256']=='42de6af1d1761ccf0260f81793e7746eb56eb08817c944e282f0f8479cced87f'
for key,a in spotprior['accounts'].items():assert a['evidence_sha256']==f['accounts']['spot/risk/'+key]['evidence_sha256']
assert f['selection']['spot']['selected_research_candidate']=='atr-stop' and f['selection']['spot']['compatible_components']==['atr-stop'] and f['selection']['spot']['combination_status']=='existing_singleton'
assert f['selection']['perp']['selected_research_candidate']=='incumbent' and not f['selection']['perp']['compatible_components'] and f['selection']['perp']['combination_status']=='not_applicable'
for k in ['spot/atr-stop/base','spot/risk/atr-stop/base','perp/incumbent/base','perp/risk/incumbent/base']:assert f['accounts'][k]['target_status']=='NOT_MET'
assert len(f['sensitivity'])==4 and all(s['account']['target_status']=='NOT_MET' for s in f['sensitivity'])
for p in f['passive_controls'].values():assert not p['continuous_mdd_verified'] and not p['native_execution_verified'] and p['additional_capital_cny']==0
sb=f['accounts']['spot/consensus/base']['financial']['metrics'];ss=f['accounts']['spot/atr-stop/base']['financial']['metrics'];assert sb['longest_daily_underwater_days']==ss['longest_daily_underwater_days']==713 and ss['worst_day']<sb['worst_day']
for p,z in ids.items():assert sha(p)==z
bind(Path(__file__))
proof={'format':'independent-final64-financial-evidence-review-v1','scope':'Research financial evidence64 only; runtime bridge/native/adoption separate','identities':ids,'final_sha256':sha(fp),'repaired_index_sha256':sha(ip),'actual_repair_provenance_sha256':sha(rp),'audit_inventory':summary,'exact64_account_identities':[{'kind':i[0],'stage':i[1],'account':i[2],'raw_sha256':i[3],**v} for i,v in sorted(seen.items())],'exact64_reconciled':True,'baseline_four_scenes_each_all_six_groups':True,'actual_four_coin_unity_six_groups':True,'profile12_actual731_recomputation_and1723_results':profiles,'max_existing_independent_audit_vs_final_regression_difference':maxreg,'max_ledger_rounding_delta':str(maxmoney),'spot_outage789_executed_accounts':outage,'other_accounts795_sessions':True,'prior_causal_proofs_preserved_and_bound':True,'repair_changes_no_selection_or_financial_outcomes':True,'selection':f['selection'],'passive_controls':f['passive_controls'],'spot_tail_tradeoff':{'baseline_worst_day':sb['worst_day'],'selected_worst_day':ss['worst_day'],'underwater_days_both':713},'original_failed_reports_preserved':True,'original_control_failure_waived':False,'financial_evidence_approved':True,'adoption_approved':False,'native_cases':0,'actual_account_days':0,'continuous_proxy_independently_replayed':False,'new_checker_or_producer_executed_by_reviewer':False}
output=R/'final64-financial-review-proof.json'
with output.open('x') as stream:json.dump(proof,stream,indent=2)
print(json.dumps({'proof_sha256':sha(output),'max_regression':maxreg,'max_ledger':str(maxmoney),'bound_files':len(ids),'accounts':len(seen)}))
