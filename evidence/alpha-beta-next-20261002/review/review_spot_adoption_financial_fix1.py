"""Exact-commit offline compatibility proof using immutable analysis99 without stubs."""
import contextlib, io, hashlib, importlib.util, json, subprocess, sys, tempfile
from decimal import Decimal as D
from pathlib import Path
root=Path('/workspace/btc-alpha-beta-adoption/spotquant')
analysis=Path('/workspace/btc-alpha-beta-analysis/spotquant')
head='0c52c812301de3712f3637a1ce1b1241de0c40f1'
def git(*args):return subprocess.check_output(['git',*args],cwd=root)
assert git('rev-parse','HEAD').decode().strip()==head
paths=sorted(p for p in git('ls-tree','-r','--name-only',head,'spotquant','research').decode().splitlines() if p.endswith('.py'))
h=hashlib.sha256()
for p in paths:h.update(p.encode()+b'\0'+git('show',head+':'+p)+b'\0')
assert h.hexdigest()=='619570fb7baa586f28ad5de2a440d7752a536cc8f8ce7e357264612e65801537'
source={'dirty':False,'git_head':head,'python_sources_sha256':h.hexdigest()}
sys.path[:0]=[str(root),str(root/'tests')]
from research.adoption_spot import measure, risk_identity
from research import alpha_spot
from test_alpha_spot import bars
from spotquant.model import ORIGIN, DAY
spec=importlib.util.spec_from_file_location('immutable99',analysis/'research/alpha_assessment.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
assert a.sha(a.__file__)=='a5bb0569f25e66b5aa660b0106d42c3ecffc7f30ebc5e2cf1b1216958ff43edf'
# ROOT and all gates are untouched; shared Git objects include the actual proposal commit.
a.verify_source(source,'spot')
rows=bars(); starts=[ORIGIN+i*DAY for i in (401,402,403)]
env={'starts':starts,'spec_sha256':a.sha(a.SPEC_PATH),'protocol_sha256':a.sha(a.PROTOCOL_PATH),'fx_sha256':a.checksum('synthetic constant 7'),'schedule_sha256':a.checksum(starts),'market_sha256':a.checksum([[str(v) for v in r] for r in rows])}
cal=Path('/workspace/scratch/alpha-beta-next/spot-project-calibration.json')
calibration=json.loads(cal.read_text()); results=[]
with tempfile.TemporaryDirectory(prefix='financial-adoption-fix1-') as tmp:
 for path in [None,cal]:
  sha=a.sha(path) if path else None
  with contextlib.redirect_stdout(io.StringIO()):
   row=measure('base',rows,starts,lambda t:D(7),limit=3,calibration_path=path)
   original=alpha_spot.measure('atr-stop','base',rows,starts,lambda t:D(7),limit=3,risk=alpha_spot.calibration(path,'atr-stop'))
  fingerprints=a.evidence_fingerprints(row,'spot')
  assert fingerprints==a.evidence_fingerprints(original,'spot')
  assert row['complete'] is False
  bundle={'format':1,'source':source,'risk_calibration_sha256':sha,'results':{'atr-stop-base':row},**{k:v for k,v in env.items() if k.endswith('sha256')}}
  raw=Path(tmp)/('calibrated.json' if path else 'unscaled.json');raw.write_text(json.dumps(bundle))
  consumed=a.consume(raw,'spot',env,rows,lambda t:D(7),[],[],expected={'atr-stop/base'},calibration=calibration if path else None,calibration_sha=sha)
  account=consumed['accounts']['atr-stop/base']
  assert account['valid'] is False and account['rejections']==['measurement_incomplete']
  results.append({'calibrated':bool(path),'calibration_sha256':sha,'scale':risk_identity(path)['scale'],'rejections':account['rejections'],'six_groups_match_synthetic_selected_research':True,'evidence_sha256':fingerprints})
print(json.dumps({'head':head,'python_sha256':h.hexdigest(),'immutable_consumer_sha256':a.sha(a.__file__),'gates_stubbed':False,'root_relocated':False,'actual_git_source_verified':True,'cases':results,'scope':'three-session synthetic schema proof only; no historical or outcome acceptance'},indent=2))
