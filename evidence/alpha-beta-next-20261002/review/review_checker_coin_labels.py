"""Small read-only extractor/source-binding and actual-training regression; no replay."""
import copy,hashlib,json,subprocess,sys
from pathlib import Path
import independent_financial_audit as a
root=Path('/workspace/btc-alpha-beta-next/review');prefix=Path('/tmp/task1-fix1-alpha-incumbent-3.json.gz')
before=a.sha(prefix);body=a.read(prefix);encoded=json.dumps(body,sort_keys=True,separators=(',',':'));rows=a.labelled_rows(body,'perp')
assert len(rows)==1 and rows[0]['candidate']=='incumbent' and rows[0]['scenario']=='base'
assert 'candidate' not in body['results']['incumbent']['base'] and 'scenario' not in body['results']['incumbent']['base']
assert rows[0] is not body['results']['incumbent']['base'] and rows[0]['trades'] is body['results']['incumbent']['base']['trades']
assert json.dumps(body,sort_keys=True,separators=(',',':'))==encoded
checks={'retained_real_prefix_nested_labels':True,'raw_object_and_bytes_unchanged':True,'prefix_fills':len(rows[0]['trades'])}
for field,bad in [('candidate','other'),('scenario','fees-x1.5')]:
 changed=copy.deepcopy(body);changed['results']['incumbent']['base'][field]=bad
 try:a.labelled_rows(changed,'perp')
 except AssertionError:checks['conflicting_'+field+'_rejected']=True
 else:raise AssertionError('accepted conflicting '+field)
changed=copy.deepcopy(body);changed['inputs']['candidates']={'other':[]}
try:a.labelled_rows(changed,'perp')
except AssertionError:checks['conflicting_input_candidates_rejected']=True
else:raise AssertionError('accepted conflicting inputs.candidates')
# Real preserved legacy optional row labels also agree with the nested map.
legacy=a.read('/workspace/btc-alpha-beta-next/coinquant/evidence/complete-delivery-20261001/perp-exclusive-accounts.json');legacy_encoded=json.dumps(legacy['results']['incumbent'],sort_keys=True)
legacy_rows=a.labelled_rows(legacy,'perp');assert all(r['candidate'] and r['scenario'] for r in legacy_rows)
assert json.dumps(legacy['results']['incumbent'],sort_keys=True)==legacy_encoded;checks['legacy_optional_labels_consistent']=True;del legacy,legacy_rows
# Source checks remain mandatory: old prefix is not frozen aced, even though its Python digest matches.
rejected_path=root/'must-not-exist-old-prefix-audit.json';assert not rejected_path.exists()
proc=subprocess.run([sys.executable,str(root/'independent_financial_audit.py'),'--bundle',str(prefix),'--sha256',before,'--kind','perp','--out',str(rejected_path)],capture_output=True,text=True)
assert proc.returncode and "assert source==frozen['sources']" in proc.stderr and not rejected_path.exists();checks['old_source_rejected_before_audit']=True
# Independent scale formula consumes only actual baseline training statistics.
baseline=a.read(root/'financial-audit-spot-consensus-v2-final.json')['accounts']['consensus/base']['statistics']
assert baseline['training_usdt']['days']==731 and baseline['validation_usdt']['days']==1723
assert a.comparison(baseline,baseline)['training_only_unscaled_risk_scale']==1;checks['actual_baseline_unity_scale']=True
changed=copy.deepcopy(baseline);changed['validation_usdt']['beta']=1000;changed['validation_usdt']['annual_vol']=1000
assert a.comparison(changed,baseline)['training_only_unscaled_risk_scale']==1;assert not a.comparison(changed,baseline)['validation_risk_match_achieved'];checks['validation_cannot_change_training_scale']=True
changed=copy.deepcopy(baseline);changed['training_usdt']['annual_vol']*=2;changed['training_usdt']['beta']*=2
assert abs(a.comparison(changed,baseline)['training_only_unscaled_risk_scale']-.5)<1e-15;checks['training_vol_and_beta_ratios_applied']=True
assert a.sha(prefix)==before
proof={'checks':checks,'prefix_raw_sha256':before,'prefix_source':body['inputs']['source'],'checker_sha256':a.sha(root/'independent_financial_audit.py'),'previous_checker_sha256':a.sha(root/'independent_financial_audit_bundle_v2.py'),'account_replays':0,'new_coin_cases_accepted':0}
with (root/'checker-coin-label-compatibility-proof.json').open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps(proof))
