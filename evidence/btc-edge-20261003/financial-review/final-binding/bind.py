"""Final metadata/source binding only. No account math, tests, producers or export."""
import copy,hashlib,io,json,subprocess,tarfile
from pathlib import Path
ROOT=Path('/workspace/btc-alpha-beta-improve');ART=ROOT/'task-artifacts';WORK=Path('/workspace/scratch/btc-alpha-beta-edge-20261003');REVIEW=WORK/'financial-review';OUT=REVIEW/'final-binding'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def check(x,msg):
 if not x:raise ValueError(msg)
def write(p,x):
 with Path(p).open('x') as f:json.dump(x,f,indent=2,allow_nan=False);f.write('\n')
def bound(p):return {'path':str(p),'sha256':sha(p)}
def git(repo,*args):return subprocess.check_output(['git',*args],cwd=repo)
def source(repo):
 head=git(repo,'rev-parse','HEAD').decode().strip();check(not git(repo,'status','--porcelain').strip(),'current repository not clean');pkg=repo.name;paths=[]
 for row in git(repo,'ls-tree','-rz','--full-tree',head).split(b'\0'):
  if not row:continue
  meta,name=row.split(b'\t',1);mode,typ,_=meta.decode().split();name=name.decode();parts=Path(name).parts
  protected=parts[0] in (pkg,'.github') or (parts[0]=='research' and (not name.endswith('.md') or 'protocol' in parts[-1].lower())) or (len(parts)==1 and (Path(name).suffix in {'.py','.json','.toml','.yaml','.yml','.cfg','.ini','.sh'} or int(mode,8)&0o111))
  if protected:check(typ=='blob' and mode!='120000','protected symlink');paths.append(name)
 raw=git(repo,'archive',head,'--',*sorted(paths));files={};modes={};python=hashlib.sha256()
 with tarfile.open(fileobj=io.BytesIO(raw)) as t:
  for m in sorted(t.getmembers(),key=lambda m:m.name):
   if not m.isfile():continue
   b=t.extractfile(m).read();files[m.name]=hashlib.sha256(b).hexdigest();modes[m.name]=m.mode;check((repo/m.name).read_bytes()==b,'working protected bytes differ')
   if m.name.startswith((pkg+'/', 'research/')) and m.name.endswith('.py'):python.update(m.name.encode()+b'\0'+b+b'\0')
 digest=hashlib.sha256(json.dumps({'files':files,'modes':modes},sort_keys=True,separators=(',',':')).encode()).hexdigest()
 return {'git_head':head,'dirty':False,'python_sources_sha256':python.hexdigest(),'protected_files':files,'protected_modes':modes,'protected_sha256':digest}
FINAL=WORK/'assessment/complete-final-input-path-fix1.json';PRE=WORK/'assessment/complete-preliminary.json';PROOF=WORK/'assessment/independent-financial-review-proof.json'
check(sha(FINAL)=='16ee432bd45c9783f9f38beb19aa7fef21ca3cc6305bee29469a371d388b2625','final report bytes');check(sha(PRE)=='b54a0324570d2b2a21ed7450b3f4a905887408ae31a115a180cc8743911aa6b3','prior report bytes');check(sha(PROOF)=='50dc293c8225027f2bfa49508cdd058f2ccc4a44ebb4976f3b41b206d048aefc','accepted proof bytes')
f=read(FINAL);p=read(PRE);proof=read(PROOF);changed={k for k in set(f)|set(p) if f.get(k)!=p.get(k)};check(changed=={'phase','status','financial_review','command'},'financial evidence changed');check(f['phase']=='final' and f['status']=='complete_reviewed' and not f['pending'] and not f['blocking'],'final incomplete');check(f['inventory_sha256']==proof['inventory_sha256']=='c3f4e9d3bee09bac4242660aafaed51e767d849dae5549343af7176c62226e74','inventory');check(f['financial_review']['sha256']==sha(PROOF) and f['financial_review']['preliminary_sha256']==sha(PRE),'final proof binding')
for cat,entry in proof['checks'].items():check(sha(entry['artifact']['path'])==entry['artifact']['sha256'],'accepted category changed')
# Bind actual completion and retained first failure, without reevaluation.
receipts={}
for label,code in [('complete-final',1),('complete-final-input-path-fix1',0)]:
 base=WORK/'assessment'/(label+'.json');sp=Path(str(base)+'.command-start.json');fp=Path(str(base)+'.command-finish.json');lp=Path(str(base)+'.run.log');s=read(sp);end=read(fp)
 check(end['exit_code']==code and end['reaped'] is True and end['state']=='exited','actual assessor exit');check(end['command_start_sha256']==sha(sp) and end['log_sha256']==sha(lp),'actual assessor receipt hashes');check(end['source_after']['spot']==p['analysis_source'],'frozen actual assessor source')
 if code==0:
  for path,digest in end['outputs'].items():check(sha(path)==digest,'final output bytes')
 receipts[label]={'start':bound(sp),'finish':bound(fp),'log':bound(lp),'actual_exit':code,'command':s['command']}
old=receipts['complete-final']['command'];new=receipts['complete-final-input-path-fix1']['command'];check(len(old)==len(new),'argv length drift');allowed={'--spot','--perp','--out','--csv','--markdown'};diff=[]
for i,(a,b) in enumerate(zip(old,new)):
 if a!=b:check(i>0 and old[i-1] in allowed,'unregistered correction argv');diff.append({'option':old[i-1],'before':a,'after':b})
for flag in ['--spot','--perp','--coin-prints']:
 check(new[new.index(flag)+1]==p['command'][p['command'].index(flag)+1],'final exact prior input path')
check(sha(WORK/'assessment/complete-final-input-path-fix1.csv')==sha(WORK/'assessment/complete-preliminary.csv'),'CSV changed')
bridges={};attestations={};source_bindings={}
for kind,repo_name,name,expected_hash in [('spot','spotquant','spot-canonical-bridge-template.json','c06ade6a93b11d727189e7a2e0692ac6059b0ff850e3384ea4f71bf21fce00de'),('perp','coinquant','coin-incumbent-bridge-template.json','43c1ae13882ddf6c2fc6b0c6d8136875691e091d03198226c3fe198d6350bcbb')]:
 template_path=REVIEW/name;template=read(template_path);recorded=template['source'];current_path=ART/(repo_name+'-accepted-current-forward-source.json');check(sha(current_path)==expected_hash,'current source supplied bytes');current=source(ROOT/repo_name);check(current==read(current_path),'current independently computed source differs')
 for field in ['python_sources_sha256','protected_files','protected_modes','protected_sha256']:check(current[field]==recorded[field],'accepted/current protected equivalence '+field)
 check(current['git_head']!=recorded['git_head'],'metadata head expected distinct');bridge=copy.deepcopy(template);bridge['source']=current;case_sources={}
 if kind=='spot':
  for label,case in bridge['canonical_accounts'].items():
   check(case['source']==recorded,'original five source binding');case_sources[label]=copy.deepcopy(case['source']);case['source']=current
   actual=f['accounts'][case['account_id']];check(case['measured_source']==actual['source'] and case['original_raw_sha256']==actual['raw_sha256'],'original raw/measurement relabel');check(case['complete'] and case['archives_verified'] and case['audit_passed'] and len(case['evidence_groups'])==6 and all(case['evidence_groups'].values()),'case evidence incomplete')
  caseproof=REVIEW/'spot-canonical-five-case-proof.json';check(sha(caseproof)==bridge['canonical_review_sha256'],'accepted five proof bytes')
 else:
  caseproof=REVIEW/'coin-incumbent-case-proof.json';check(sha(caseproof)==bridge['canonical_review_sha256'],'accepted Coin proof bytes')
 check(bridge['measured_source']==f['accounts'][bridge['account_id']]['source'] and bridge['raw_sha256']==f['accounts'][bridge['account_id']]['raw_sha256'] and bridge['candidate']==f['selected'][kind],'bridge original/final selection binding')
 for key,n in [('spec_sha256','edge_spec.json'),('protocol_sha256','edge-PROTOCOL.md')]:check(current['protected_files']['research/'+n]==f['contracts'][kind][key],'final local contract')
 attestation={'format':'btc-edge-canonical-forward-bridge-v1','status':'independently_reviewed','project':kind,'bridge':bridge,'final_report':bound(FINAL),'financial_review':bound(PROOF),'accepted_case_proof':bound(caseproof),'accepted_template':bound(template_path),'source_equivalence':{'original_accepted_source':recorded,'current_source_receipt':bound(current_path),'protected_bytes_and_modes_equal':True,'actual_canonical_case_sources':case_sources},'review_scope':'Final report, source bytes/modes and metadata binding only. All 71 financial and five canonical calculations are reused unchanged.','native_cases':0,'actual_account_days':0,'prospective_alpha_proven':False,'original_targets':'NOT_MET'}
 path=OUT/(kind+'-canonical-forward-attestation.json');write(path,attestation);bridges[kind]=dict(bridge,canonical_review=bound(path));attestations[kind]=bound(path);source_bindings[kind]={'accepted_head':recorded['git_head'],'current_head':current['git_head'],'python_sources_sha256':current['python_sources_sha256'],'protected_sha256':current['protected_sha256'],'protected_file_count':len(current['protected_files'])}
write(OUT/'canonical-bridges.json',bridges)
result={'status':'PASS','scope':'final binding only','bridges':bound(OUT/'canonical-bridges.json'),'attestations':attestations,'final_report':bound(FINAL),'financial_review':bound(PROOF),'inventory_sha256':f['inventory_sha256'],'unchanged_final_evidence_fields':sorted(set(f)-changed),'allowed_final_report_changes':sorted(changed),'corrected_argv':diff,'actual_receipts':receipts,'sources':source_bindings,'financial_calculations_rerun':0,'canonical_cases_rerun':0,'software_tests':0,'producers':0,'network_calls':0,'export_initialization':'not performed; resulting export bytes require subsequent independent approval','script':bound(__file__)}
write(OUT/'final-binding-proof.json',result)
lines=['# Independent final binding review','', '**PASS — final binding only.** The corrected final report retains the exact accepted financial inventory, account/evidence/profile/selection/budget data and all five accepted canonical calculations. No financial calculations, producers, software tests or additional raw-account audits were run.','',f"Final report SHA256 `{sha(FINAL)}`; inventory `{f['inventory_sha256']}`. Independent financial proof remains `{sha(PROOF)}`. Compared complete preliminary and final report objects: only phase, status, financial_review and command differ. All economic evidence is identical.",'','The first final assessment genuinely exited1 and produced no final report. Its command/finish/log are retained. The corrected assessment genuinely exited0 after changing only --spot/--perp to the exact reviewed preliminary manifest paths and choosing exclusive output paths. The same assessment-only public-print union remains in use. Final CSV is byte-identical to preliminary CSV. This corrects a path-bound inventory mismatch, not financial results.','', '| Project | Accepted execution HEAD | Current metadata HEAD | Protected files |','|---|---|---|---:|']
for kind,v in source_bindings.items():lines.append(f"| {kind} | {v['accepted_head']} | {v['current_head']} | {v['protected_file_count']} |")
lines+=['','Both repositories are clean. Independently enumerated protected current Git archive files/modes and working bytes exactly match the accepted template mappings. Spot Python remainsb81f1bfee086e875cbf8ff22a67b2cfdff419130a7918a6ce8754b2e9e2936c5; Coin Python remainsba63895131db566e708a5c96cde4504beace39fa0bdd54881d039dd5b8ef4c50. The metadata HEADs are aliases for these accepted protected bytes.','', 'Original Spot research measurements remain74bd/Pythonf2d6; the five actual canonical measurements remain609606/Pythonb81. Final Spot bridge case source fields name the byte-equivalent current source as required by the export interface; the attestation separately preserves each actual609606 measurement source, original research identity and accepted case-proof hash. No raw result was rewritten or relabeled. Coin’s actual financial measurement remains37061a7/Pythonba638, while its current73660 metadata HEAD has identical protected bytes/modes.','',f"Bridges: `canonical-bridges.json` SHA `{sha(OUT/'canonical-bridges.json')}`."]
for kind,v in attestations.items():lines.append(f"{kind} attestation: `{Path(v['path']).name}` SHA `{v['sha256']}`.")
lines+=['', 'The attestations use btc-edge-canonical-forward-bridge-v1, independently_reviewed, with bridge exactly equal to its final project template fields; the canonical_review pointer lives only in the outer bridges file. The original accepted case proofs remain separately bound. Source-spec/protocol and selected adapter/components/scale1 match the accepted final report.','', 'All financial interpretation limits remain: Spot crowding historical improvement arose from missing-feature entry blocking; no actual triple-condition halve was observed. Historical validation is contaminated, continuous account MDD remains OHLC/minute-envelope proxy, 29 missing mark minutes and native protection limits remain. Neutral5000/5000 is a reference, no optimized allocation. Both targets remainNOT_MET; native cases0, account-days0, prospective alpha false, NOT_QUALIFIED.','', 'This review prepares source/report bridge bytes. Root may perform the authorized single export; its resulting bytes/hash still require independent binding approval before actual initialization. That later binding review reuses completed71/five calculations.','']
with (OUT/'final-binding-review.md').open('x') as stream:stream.write('\n'.join(lines))
write(OUT/'delivery-artifacts.json',{'status':'PASS','bridges':bound(OUT/'canonical-bridges.json'),'attestations':attestations,'proof':bound(OUT/'final-binding-proof.json'),'report':bound(OUT/'final-binding-review.md'),'final_report':bound(FINAL),'financial_review':bound(PROOF)})
print(json.dumps(read(OUT/'delivery-artifacts.json'),indent=2))
