import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path('/workspace/btc-alpha-beta-improve')
OUT = ROOT / 'task-artifacts'
ARTIFACT = OUT / 'edge-features-v1.json'
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
raw = json.loads((OUT/'crowding-verified-before-edge.json').read_bytes())
a = json.loads(ARTIFACT.read_bytes())
assert sha('/tmp/btc-complete-inputs/crowding-complete.json') == sha(OUT/'crowding-verified-before-edge.json') == a['source']['raw_sha256']
assert sha('/tmp/btc-complete-inputs/futures.json') == a['source']['market_identities']['original_futures_artifact_sha256']
assert len(raw['funding']) == 7488 and len(raw['basis']) == 2485
assert [[r['observation_ms'],r['value']] for r in a['funding']] == raw['funding']
assert [[r['available_ms'],r['value']] for r in a['basis']] == raw['basis']
assert all(r['available_ms']==r['observation_ms']+28800000 for r in a['funding'])
assert all(r['observation_ms']==r['available_ms']-60000 and r['observation_ms']%86400000==0 for r in a['basis'])
spot = (ROOT/'spotquant/research/edge_features.py').read_text()
coin = (ROOT/'coinquant/research/edge_features.py').read_text()
reader = spot[spot.index('DAY ='):spot.index('\ndef _verify_archive')].strip()
assert reader == coin[coin.index('DAY ='):].strip()
reader_sha = hashlib.sha256(reader.encode()).hexdigest()
program = r'''
from collections import Counter
import hashlib,json,sys
from pathlib import Path
from research.edge_features import FeatureBook, DAY, FUNDING_LAG, START_MS, END_MS
p=Path(sys.argv[1]); book=FeatureBook(p,sys.argv[3]); a=json.loads(p.read_bytes())
probes={START_MS-1,START_MS,END_MS-1,END_MS,END_MS+1}
for name in ('funding','basis'):
 for row in a[name]:
  t=row['available_ms']; expiry=t+FUNDING_LAG if name=='funding' else (t//DAY+1)*DAY
  probes.update([t-1,t,t+1,expiry-1,expiry,expiry+1,t+DAY,t+DAY+1])
digest=hashlib.sha256(); counts=Counter()
for stamp in sorted(probes):
 for name in ('funding','basis'):
  value=book.value(name,stamp); log=book.last_lookup
  result={k:log[k] for k in ('name','now_ms','value','cause','observation_ms','available_ms','age_ms','artifact_sha256','raw_sha256','market_identities')}
  digest.update(json.dumps(result,sort_keys=True,separators=(',',':')).encode()+b'\n')
  counts[(name+':'+(log['cause'] or 'known'))]+=1
schedule=json.loads(Path(sys.argv[2]).read_bytes()); starts=schedule['primary']['starts_ms']
assert len(starts)==795 and len(set(starts))==795
session_counts=Counter()
for start in starts:
 for delta in range(0,300000,5000):
  for name in ('funding','basis'):
   book.value(name,start+delta)
   session_counts[name+':'+(book.last_lookup['cause'] or 'known')]+=1
print(json.dumps({'lookup_digest':digest.hexdigest(),'unique_probe_timestamps':len(probes),'lookups':2*len(probes),'causes':dict(counts),'session_probe_counts':dict(session_counts),'sessions':len(starts),'polls_per_session':60,'coverage_disclosure':'registered starts plus nominal 5s polls; not actual adapter decision timings or execution proof'},sort_keys=True))
'''
schedule=ROOT/'coinquant/research/session_schedule.json'
results={}
for repo in ('spotquant','coinquant'):
 r=subprocess.run([sys.executable,'-c',program,str(ARTIFACT),str(schedule),sha(ARTIFACT)],cwd=ROOT/repo,capture_output=True,text=True,check=True)
 results[repo]=json.loads(r.stdout)
assert results['spotquant']==results['coinquant']
# Reject existing output without processing archives and without changing bytes.
previous=sha(ARTIFACT)
command=[sys.executable,'-m','research.edge_features','--build','--crowding','/tmp/btc-complete-inputs/crowding-complete.json','--out',str(ARTIFACT)]
r=subprocess.run(command,cwd=ROOT/'spotquant',capture_output=True,text=True)
assert r.returncode==2 and 'choose a new immutable output' in r.stderr and sha(ARTIFACT)==previous
receipt={'status':'PASS','artifact_sha256':sha(ARTIFACT),'content_sha256':a['content_sha256'],'registered_raw_sha256':a['source']['raw_sha256'],'original_futures_sha256':sha('/tmp/btc-complete-inputs/futures.json'),'reader_logic_sha256':reader_sha,'schedule_sha256':sha(schedule),'reconstructed_records_exactly_match_registered_raw':True,'reader_decisions_identical':True,'output_overwrite_rejected_unchanged':True,'checks':results,'coverage':a['coverage'],'source':a['source'],'financial_producer_executed':False,'native_requests':False}
with (OUT/'task-2-acceptance.json').open('x') as stream:
 json.dump(receipt,stream,indent=2,sort_keys=True);stream.write('\n')
for repo,result in results.items(): print(repo,json.dumps(result,sort_keys=True))
print('PASS',sha(OUT/'task-2-acceptance.json'))
