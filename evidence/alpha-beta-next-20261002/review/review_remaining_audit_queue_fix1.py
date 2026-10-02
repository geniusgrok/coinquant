"""Pure fix1 queue regressions; no subprocess, checker, producer, State or cache calls."""
import copy,hashlib,importlib.util,json,tempfile
from pathlib import Path
from types import SimpleNamespace
REVIEW=Path('/workspace/btc-alpha-beta-next/review');p=REVIEW/'audit_remaining_registered.py';expected='5fdef514d1f3d382ca04a4a2e1c38d0e2991f698df08cbca46f1fcfb711090bd'
assert hashlib.sha256(p.read_bytes()).hexdigest()==expected
spec=importlib.util.spec_from_file_location('remaining_fix1_target',p);q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
checks={}
def rejects(name,fn):
 try:fn()
 except (ValueError,RuntimeError):checks[name]=True
 else:raise AssertionError('did not reject '+name)
with tempfile.TemporaryDirectory(prefix='remaining-fix1-pure-',dir=REVIEW) as temp:
 root=Path(temp);q.OUT=q.REVIEW=root
 output=root/'stage.json';output.write_text('{}')
 receipt={'exit_code':0,'output_sha256':q.sha(output),'command':['fixture','--out',str(output)]};receiptpath=root/'stage.command.json'
 def rec(d):receiptpath.write_text(json.dumps(d))
 rec(receipt);assert q.command_receipt('stage')==receipt;checks['exact_report_path_sha_accepted']=True
 rec(dict(receipt,output_sha256='0'*64));rejects('wrong_receipt_report_sha_rejected',lambda:q.command_receipt('stage'))
 rec(dict(receipt,command=['fixture','--out',str(root/'different.json')]));rejects('wrong_receipt_output_path_rejected',lambda:q.command_receipt('stage'))
 rec(dict(receipt,command=receipt['command']+['--out',str(output)]));rejects('duplicate_out_option_rejected',lambda:q.command_receipt('stage'))
 rec(dict(receipt,exit_code=1));rejects('failed_completed_command_rejected',lambda:q.command_receipt('stage'))
 raw=root/'raw.json.gz';raw.write_bytes(b'fixture never read by a producer');digest=q.sha(raw)
 existing=root/'financial-audit-existing.json';existing.write_text(json.dumps({'raw_sha256':digest,'accounts':{},'all_examined_checks_passed':True,'all_reported_complete':True}))
 rejects('existing_same_raw_audit_reuse_rejected',lambda:q.audit_one(raw,'spot','existing',stage='risk',calibration=root/'absent',baseline=root/'absent2',unscaled=root/'absent3'))
 # Stub the only execution call to inspect exclusive context receipt and false flags.
 contexts=[]
 for name in ('calibration','baseline','unscaled'):
  path=root/(name+'.json');path.write_text(json.dumps({'fixture':name}));contexts.append(path)
 def stub_run(command,**kwargs):
  target=Path(command[command.index('--out')+1]);target.write_text(json.dumps({'raw_sha256':digest,'accounts':{'consensus/base':{'errors':['fixture failed check']}},'all_examined_checks_passed':False,'all_reported_complete':False}));return SimpleNamespace(returncode=0)
 original_run=q.subprocess.run;q.subprocess.run=stub_run
 keys=q.audit_one(raw,'spot','new-context',stage='risk',calibration=contexts[0],baseline=contexts[1],unscaled=contexts[2]);q.subprocess.run=original_run
 assert keys=={'consensus/base'} and not q.INDEX[-1]['all_checks_passed'] and not q.INDEX[-1]['all_reported_complete'];checks['failed_check_flags_preserved']=True
 command=json.loads((root/'financial-audit-new-context.command.json').read_text());assert command['checker_sha256']==q.CHECKER_SHA
 for key,path in zip(('calibration','baseline_audit','unscaled_audit'),contexts):assert command['verification_context'][key]=={'path':str(path),'sha256':q.sha(path)}
 checks['new_audit_exact_context_shas_recorded']=True
 original_audit=q.audit_one;called=[]
 q.audit_one=lambda raw,kind,label,**kwargs: called.append(str(raw)) or {'consensus/base'}
 rejects('wrong_assessed_root_sha_rejected',lambda:q.audit_path(raw,'spot','raw','0'*64,{'consensus/base'},stage='risk'))
 q.audit_path(raw,'spot','raw',digest,{'consensus/base'},stage='risk');checks['exact_root_sha_and_case_set_accepted']=True
 rejects('missing_expected_account_rejected',lambda:q.audit_path(raw,'spot','raw',digest,{'consensus/base','atr-close/base'},stage='risk'))
 rejects('unexpected_account_rejected',lambda:q.audit_path(raw,'spot','raw',digest,set(),stage='risk'))
 manifest=root/'manifest.json';body={'format':'alpha-account-manifest-v1','kind':'spot','files':[{'path':raw.name,'sha256':digest},{'path':raw.name,'sha256':digest}]};manifest.write_text(json.dumps(body))
 rejects('duplicate_manifest_account_rejected',lambda:q.audit_path(manifest,'spot','manifest',q.sha(manifest),{'consensus/base'},stage='risk'))
 body['files']=body['files'][:1];body['files'][0]['sha256']='0'*64;manifest.write_text(json.dumps(body))
 rejects('manifest_child_sha_mismatch_rejected',lambda:q.audit_path(manifest,'spot','manifest',q.sha(manifest),{'consensus/base'},stage='risk'))
 q.audit_one=original_audit
 # Exact final reconciliation is independent of account counts and preserves stage.
 audit=root/'final-fixture-audit.json';audit.write_text('{}')
 entry={'kind':'spot','stage':'risk','account_keys':['consensus/base'],'raw_path':str(raw),'raw_sha256':digest,'audit_path':str(audit),'audit_sha256':q.sha(audit)}
 final={'accounts':{'spot/risk/consensus/base':{'candidate':'consensus','scenario':'base','raw_bundle_sha256':digest}},'sensitivity':[]};q.INDEX=[entry]
 q.verify_final_inventory(final);checks['exact_final_raw_identity_set_accepted']=True
 q.INDEX=[entry,copy.deepcopy(entry)];rejects('duplicate_final_audit_identity_rejected',lambda:q.verify_final_inventory(final));q.INDEX=[entry]
 wrong=copy.deepcopy(final);wrong['accounts']['spot/risk/consensus/base']['raw_bundle_sha256']='0'*64
 rejects('final_assessment_different_raw_rejected',lambda:q.verify_final_inventory(wrong))
 rejects('extra_final_audited_identity_rejected',lambda:q.verify_final_inventory({'accounts':{},'sensitivity':[]}))
 q.INDEX=[];rejects('missing_final_audit_identity_rejected',lambda:q.verify_final_inventory(final));q.INDEX=[entry]
 audit.write_text('{"changed":true}');rejects('changed_audit_before_index_rejected',lambda:q.verify_final_inventory(final))
 # stage extraction: registered singles excluded; actual combo and risk retained.
 accounts={'spot/consensus/base':{'candidate':'consensus','scenario':'base'},'spot/combo/base':{'candidate':'combo','scenario':'base'},'spot/risk/atr-close/base':{'candidate':'atr-close','scenario':'base'}}
 assert q.stage_keys({'accounts':accounts},'spot','combo')=={'combo/base'} and q.stage_keys({'accounts':accounts},'spot','risk')=={'atr-close/base'};checks['stage_keys_match_final_schema']=True
proof={'queue_sha256':expected,'checker_sha256':q.CHECKER_SHA,'checks':checks,'passed_checks':len(checks),'real_subprocesses':0,'account_replays':0,'State_invocations':0}
with (REVIEW/'remaining-audit-queue-fix1-review-proof.json').open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps(proof))
