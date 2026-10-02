"""Read-only actual-prefix calculation and pure project-document fixtures; no State/replay."""
import ast,copy,gzip,hashlib,json,subprocess,sys,tempfile
from pathlib import Path
import numpy as np
from research import alpha_assessment as a
sys.path.insert(0,'/workspace/btc-alpha-beta-next/review')
import independent_financial_audit as independent
ROOT=Path('/workspace/btc-alpha-beta-next/review');HEAD='99fcf005d2cb15c13bb37322b65ab2863b19d65e';BASE='32ab1bb546bde064e641c4a2eb5ed4248e590acb'
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==HEAD
old=ast.parse(subprocess.check_output(['git','show',BASE+':research/alpha_assessment.py'],text=True));new=ast.parse(Path('research/alpha_assessment.py').read_text())
def functions(tree):return {x.name:ast.dump(x,include_attributes=False) for x in tree.body if isinstance(x,ast.FunctionDef)}
o,n=functions(old),functions(new);assert set(n)-set(o)=={'load_project_calibration'};assert {k for k in o if o[k]!=n[k]}=={'assess','main'}
curves={};rawhash={}
for name in ('consensus','trend-reentry'):
 p=Path('/workspace/scratch/alpha-beta-next/spot-singletons')/(name+'.json.gz');rawhash[name]=independent.sha(p);body=independent.read(p);row=body['results'][name+'-base']
 points={v['timestamp_ms']:v for v in row['daily'].values()};curves[name]=[{'day_ms':day,'equity_usdt':float(points[day+independent.DAY]['equity_usdt'])} for day in independent.DAYS];del body,row,points
assert sum(x['day_ms']<a.CUTOFF for x in curves['consensus'])==731
prices=np.array([float(independent.BARS[d][3]) for d in independent.DAYS]);market=prices/np.r_[float(independent.BARS[independent.START][0]),prices[:-1]]-1
initial=float(independent.D(10000)/independent.fx(independent.START)*independent.D('.999'))
def independent_training(curve):
 vals=np.array([r['equity_usdt'] for r in curve[:731]]);r=vals/np.r_[initial,vals[:-1]]-1;x=market[:731]
 return float(r.std(ddof=1)*np.sqrt(365.25)),float(np.cov(r,x,ddof=1)[0,1]/np.var(x,ddof=1))
bv,bb=independent_training(curves['consensus']);cv,cb=independent_training(curves['trend-reentry']);expected=min(1,bv/cv)
if cb>bb and cb>0:expected=min(expected,max(.01,bb)/max(.01,cb))
scale,diag=a.calibrate(curves['trend-reentry'],curves['consensus'],list(market),initial);assert abs(float(scale)-expected)<1e-12
assert a.calibrate(curves['consensus'],curves['consensus'],list(market),initial)[0]=='1.0'
changed=copy.deepcopy(curves['trend-reentry']);changed_market=list(market)
for i in range(731,len(changed)):changed[i]['equity_usdt']='MUST_NOT_READ_FUTURE';changed_market[i]='MUST_NOT_READ_FUTURE'
assert a.calibrate(changed,curves['consensus'],changed_market,initial)==(scale,diag)
# Pure fixture account statuses, using retained curves only for mathematical inputs.
fixturehash=hashlib.sha256(b'project-calibration-pure-fixture-not-financial-account-evidence').hexdigest()
accounts={name+'/base':{'candidate':name,'valid':name in ('consensus','trend-reentry'),'rejections':[] if name in ('consensus','trend-reentry') else ['fixture_invalid'], 'curve':curves['consensus' if name=='consensus' else 'trend-reentry'],'raw_bundle_sha256':fixturehash} for name in a.SPEC['spot_candidates']}
bundle={'accounts':accounts,'raw_sha256':fixturehash};full,_=a.calibration_document({'spot':bundle},list(market),independent.fx)
assert set(full['profiles'])=={'consensus','trend-reentry'};inventory,needed,control=a.risk_inventory(bundle,'spot')
assert needed=={'consensus/base','trend-reentry/base'};assert len(inventory)==6
assert all(inventory[n]['status']=='not_applicable_due_to_invalid_unscaled_base' for n in a.SPEC['spot_candidates'][2:])
with tempfile.TemporaryDirectory(prefix='project-calibration-pure-',dir=ROOT) as td:
 p=Path(td)/'project.json.gz'
 def write(doc):
  with gzip.open(p,'wt') as f:json.dump(doc,f,indent=3)
 write(full);actual,digest=a.load_project_calibration(p,full,'spot');assert actual==full and digest==independent.sha(p)
 for label,change in [('omit_valid',lambda x:x['profiles'].pop('trend-reentry')),('add_invalid',lambda x:x['profiles'].__setitem__('atr-close',x['profiles']['trend-reentry'])),('change_actual_input',lambda x:x['profiles']['trend-reentry'].__setitem__('base_bundle_sha256','0'*64)),('boolean_format',lambda x:x.__setitem__('format',True))]:
  wrong=copy.deepcopy(full);change(wrong);write(wrong)
  try:a.load_project_calibration(p,full,'spot')
  except ValueError:pass
  else:raise AssertionError('accepted '+label)
 invalid=copy.deepcopy(bundle);invalid['accounts']['consensus/base']['valid']=False;invalid['accounts']['consensus/base']['rejections']=['fixture_invalid_baseline']
 empty,_=a.calibration_document({'spot':invalid},list(market),independent.fx);assert empty['profiles']=={}
 inv,required,ctrl=a.risk_inventory(invalid,'spot');assert not required;assert inv['trend-reentry']['status']=='pending_valid_unscaled_baseline_for_calibration';assert not ctrl['passed']
 write(empty);assert a.load_project_calibration(p,empty,'spot')[0]==empty
frozen=independent.read('/workspace/scratch/alpha-beta-next/frozen-sources.json');source=a.source_identity();equivalence=a.verify_execution_equivalence(frozen['sources']['spotquant'],source,'spot',frozen['economic_inputs']['alpha_beta_spec.json'],frozen['economic_inputs']['alpha-beta-PROTOCOL.md'])
proof={'scope':'Financial boundary review; pure document/status fixtures are not measured cases. No early calibration file for production was emitted.','head':source,'unchanged_function_count':len(o)-2,'source_execution_equivalence_sha256':equivalence,'actual_curve_raw_sha256':rawhash,'training_days':731,'validation_days_excluded':1723,'independent_actual_training':{'baseline_vol':bv,'baseline_beta':bb,'candidate_vol':cv,'candidate_beta':cb,'independent_scale':expected,'assessor_scale':scale},'actual_baseline_unity':True,'postcutoff_non_numeric_values_not_read':True,'invalid_candidate_profiles_absent_but_obligations_retained':True,'invalid_baseline_has_no_legal_rerun_profile':True,'project_actual_gzip_sha_preserved':True,'missing_extra_input_and_root_mutations_rejected':True,'account_replays':0,'State_invocations':0}
with (ROOT/'project-calibration-financial-review-proof.json').open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps(proof))
