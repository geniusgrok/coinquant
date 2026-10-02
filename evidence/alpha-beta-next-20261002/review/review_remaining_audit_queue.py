"""Pure queue-function fixtures; never starts checker/producer/State or reads caches."""
import hashlib,importlib.util,json,tempfile
from pathlib import Path
REVIEW=Path('/workspace/btc-alpha-beta-next/review');path=REVIEW/'audit_remaining_registered.py'
assert hashlib.sha256(path.read_bytes()).hexdigest()=='b9dabb63236db0a0c16a8f965ddb0afe964cb1a6b0a6b49b88861bed6f3d1c3c'
spec=importlib.util.spec_from_file_location('remaining_queue_review_target',path);q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
proof={'queue_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'fixture_only':True,'subprocesses':0,'account_replays':0,'findings':{}}
with tempfile.TemporaryDirectory(prefix='remaining-audit-pure-',dir=REVIEW) as temp:
 root=Path(temp);q.OUT=q.REVIEW=root
 raw=root/'raw.json.gz';raw.write_bytes(b'fixture raw bytes; never parsed as an account')
 target=root/'financial-audit-existing-risk.json';target.write_text(json.dumps({'raw_sha256':q.sha(raw),'accounts':{'consensus/base':{}},'all_examined_checks_passed':True,'all_reported_complete':True}))
 # Existing-report branch must not launch anything. It nevertheless accepts missing
 # desired comparison/calibration files and no evidence that those checks ever ran.
 q.audit_one(raw,'spot','existing-risk',calibration=root/'ABSENT-calibration.json',baseline=root/'ABSENT-baseline.json',unscaled=root/'ABSENT-unscaled.json')
 proof['findings']['existing_risk_audit_without_required_context_reused']=bool(q.INDEX[-1]['all_checks_passed'])
 output=root/'stage.json';output.write_text('actual output differs from receipt digest')
 receipt={'exit_code':0,'output_sha256':'0'*64,'command':['fixture','--out',str(output)]}
 (root/'stage.command.json').write_text(json.dumps(receipt));assert q.command_receipt('stage')==receipt
 proof['findings']['receipt_output_sha_not_checked']=q.sha(output)!=receipt['output_sha256']
 called=[];q.audit_one=lambda path,kind,label,**kwargs:called.append((str(path),kind,label))
 manifest=root/'manifest.json';manifest.write_text(json.dumps({'format':'alpha-account-manifest-v1','kind':'spot','files':[{'path':raw.name,'sha256':q.sha(raw)},{'path':raw.name,'sha256':q.sha(raw)}]}))
 q.audit_path(manifest,'spot','duplicate')
 proof['findings']['duplicate_same_raw_manifest_child_counted_twice']=len(called)==2 and called[0][0]==called[1][0]
assert all(proof['findings'].values())
with (REVIEW/'remaining-audit-queue-review-proof.json').open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps(proof))
