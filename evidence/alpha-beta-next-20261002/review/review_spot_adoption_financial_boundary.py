"""Offline boundary proof; no producers, account replay, or source mutation."""
import ast, copy, hashlib, importlib.util, json, subprocess, sys
from decimal import Decimal as D
from pathlib import Path
ROOT=Path('/workspace/btc-alpha-beta-adoption/spotquant')
FROZEN=Path('/workspace/btc-alpha-beta-next/spotquant')
ANALYSIS=Path('/workspace/btc-alpha-beta-analysis/spotquant')
HEAD='7ac94e12b41b9958072c9ff080983eea1a3cbd83'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
assert git('rev-parse','HEAD').decode().strip()==HEAD
sys.path.insert(0,str(ROOT))
from spotquant import model, preview, execution
from research.adoption_spot import risk_identity
files=sorted(p for p in git('ls-tree','-r','--name-only',HEAD,'research','spotquant').decode().splitlines() if p.endswith('.py'))
h=hashlib.sha256()
for p in files:h.update(p.encode()+b'\0'+git('show',HEAD+':'+p)+b'\0')
assert h.hexdigest()=='7d4985f9176cd1d6a995be6c4fbcff17ffc5dad832218fae594eeb1b8b76a380'
unchanged={p:git('show',HEAD+':'+p)==git('show','99fcf005:'+p) for p in ['research/alpha_assessment.py','research/alpha_beta_spec.json','research/alpha-beta-PROTOCOL.md','spotquant/follow.py']}
assert all(unchanged.values())
m=model.Model(30); rows=[]
for i in range(80):
    close=D(100+i%19); high=close+D(2+i%7); low=close-D(1+i%5)
    rows.append((high,low,close));m.update(model.ORIGIN+i*model.DAY,high,low,close)
    ranges=[max(rows[j][0]-rows[j][1],abs(rows[j][0]-rows[j-1][2]),abs(rows[j][1]-rows[j-1][2])) for j in range(max(1,i-13),i+1)]
    assert m.atr14==(sum(ranges,D(0))/14 if len(ranges)==14 else None)
assert m.trail==D('.28')
# Execute only the actual frozen adjust_stop method, detached from its producer.
tree=ast.parse((FROZEN/'research/alpha_spot.py').read_text())
policy=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Policy')
method=next(n for n in policy.body if isinstance(n,ast.FunctionDef) and n.name=='adjust_stop')
ns={'D':D,'DAY':model.DAY,'execution':execution};exec(compile(ast.Module(body=[method],type_ignores=[]),'frozen-adjust-stop','exec'),ns)
comparisons=0
for status in ['NEW','PARTIALLY_FILLED','CANCELED','FILLED','EXPIRED','EXPIRED_IN_MATCH','REJECTED',None]:
 for age in [-1,0,1]:
  position={'first_ms':m.last+60000}
  owner={'sleeves':[30],'order':{'type':'STOP_LOSS','stopPrice':'107'},'native_status':status,'signal_ms':m.last-model.DAY+age}
  for atr in [D('.1'),D(4),D(100)]:
   x=copy.copy(m);x.true_ranges=__import__('collections').deque([(m.last-i*model.DAY,atr) for i in range(14)],maxlen=14)
   original=x.checkpoint(); y=copy.copy(x)
   ns['adjust_stop'](None,y,position,{'1':owner},atr)
   z=preview.decision_view(x,position,{'1':owner})
   for peak in [D(100),D(120),D(200)]:assert y.stop_price(peak)==z.stop_price(peak)
   assert y.trail==z.trail and y.protection==z.protection and x.checkpoint()==original
   comparisons+=1
cal=Path('/workspace/scratch/alpha-beta-next/spot-project-calibration.json')
identity=risk_identity(cal)
assert identity['scale']=='0.9972720085277638'
# Reproduce the unchanged consume identity boundary with only surrounding I/O stubbed.
spec=importlib.util.spec_from_file_location('immutable_assessor',ANALYSIS/'research/alpha_assessment.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
row={'candidate':'atr-stop','scenario':'base','research_identity':risk_identity()}
a.read_json=lambda p:({'results':{'atr-stop-base':row}},'f'*64)
a.metadata=lambda *args,**kwargs:{'risk_calibration_sha256':None}
try:a.consume('synthetic-boundary-only','spot',{'starts':[]},[],None,[],[])
except KeyError as exc:failure=str(exc);assert failure=="'components'"
else:raise AssertionError('expected canonical identity schema failure')
required=['components','spec_sha256','risk_scale','core_mode','core_fraction']
missing=[k for k in required if k not in risk_identity()]
assert missing==required
proof={'head':HEAD,'python_sha256':h.hexdigest(),'unchanged':unchanged,'independent_atr_prefixes':80,'frozen_adjust_stop_comparisons':comparisons,'actual_profile_scale':identity['scale'],'actual_calibration_sha256':identity['calibration_sha256'],'immutable_consume_schema_failure':failure,'missing_identity_fields':missing,'scope':'pure functions and source checks; no full replay or source-gate bypass in production'}
print(json.dumps(proof,indent=2))
