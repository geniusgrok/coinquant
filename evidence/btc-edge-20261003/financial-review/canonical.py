"""Five original-vs-canonical case accounting and exact six-group bridge."""
from recompute import *
INV=WORK/'canonical-spot/canonical-inventory.json';CAN=Path('/workspace/btc-alpha-beta-canonical-prepare/spotquant')
def main():
 require(sha(INV)=='1d4dd97eb7d9941073f1413f82f885f0baefd024f37f61377f12c1b39ba75eb3','five inventory');inventory=load(INV);bars,mr,cr=market();cases={};details={};source=None
 for item in inventory['files']:
  label=item['label'];checkpoint=OUT/('canonical-'+label+'.json')
  if checkpoint.exists():d=load(checkpoint);cases[label]=d['bridge_case'];details[label]=d;print('REUSE canonical',label,flush=True);continue
  p=item['path'];eq(sha(p),item['sha256'],'canonical raw');eq(sha(item['original_path']),item['original_raw_sha256'],'old raw');b=load(p);old=load(item['original_path']);r=next(iter(b['results'].values()));o=next(iter(old['results'].values()));require(len(b['results'])==len(old['results'])==1,'single actual account');a=load(OUT/'accounts'/(hashlib.sha256(item['account_id'].encode()).hexdigest()+'.json'))
  eq(b['source'],{k:item['canonical_source'][k] for k in ['git_head','dirty','python_sources_sha256']},'canonical measurement source');eq(b['canonical_source'],item['canonical_source'],'canonical archive');eq(old['source'],item['original_measured_source'],'original source retained');require(b['source']!=old['source'],'distinct source identities')
  if source is None:
   source=source_proof(CAN,b['source']);arch=ROOT/'task-artifacts/spot-canonical-reviewed-source-fix3.tar.gz';require(sha(arch)=='250bd1381114afde1b06d835185b908b1b499d3c773d53bf4ac6baecf580175a','canonical archive bytes')
   with tarfile.open(arch,'r:gz') as t:
    names={m.name:m for m in t.getmembers() if m.isfile()}
    for name,h in b['canonical_source']['protected_files'].items():
     require(name in names,'protected archive file '+name);m=names[name];require(hashlib.sha256(t.extractfile(m).read()).hexdigest()==h and m.mode==b['canonical_source']['protected_modes'][name] and sha(CAN/name)==h,'protected canonical archive/current '+name)
   put(OUT/'canonical-source.json',{'archive_path':str(arch),'archive_sha256':sha(arch),'full_source':b['canonical_source'],'python_verification':source})
  for k in ['spec_sha256','protocol_sha256','feature_sha256','market_sha256','schedule_sha256','fx_sha256','risk_calibration_sha256']:eq(b[k],old[k],'canonical input '+k)
  for k in ['candidate','scenario','risk_calibration','subpools']:eq(r.get(k),o.get(k),'original annotation '+k)
  ad=b['adoption'];require(ad['execution']=='canonical_shared_session' and ad['candidate']=='crowding-interaction' and ad['components']==['crowding-interaction'] and ad['rule']=='2026-10-03-atr-stop-crowding-interaction-v1' and D(ad['scale'])==1,'canonical native rule')
  proofs=ledger(r,'spot');eq(proofs[0],a['monetary_audit'],'canonical independent wallet');cur=curve(r,'spot',bars);eq(cur,a['curve'],'canonical every daily point');met=metrics(r,cur,'spot',mr,cr);eq(met,a['metrics'],'canonical every attribution metric');timing=clocks(r,'spot',r['scenario'],0);oldgroups=groups(o,'spot');newgroups=groups(r,'spot');eq(oldgroups,newgroups,'canonical six original groups')
  receipt=receipts(p,item['sha256']);eq(receipt['start_sha256'],item['command_start']['sha256'],'canonical start');eq(receipt['finish_sha256'],item['command_finish']['sha256'],'canonical finish')
  case={'account_id':item['account_id'],'measured_source':old['source'],'original_raw_sha256':item['original_raw_sha256'],'source':b['canonical_source'],'complete':True,'archives_verified':True,'audit_passed':True,'evidence_groups':{k:True for k in oldgroups},'canonical_raw_sha256':item['sha256'],'command_receipt_sha256':receipt['finish_sha256']}
  d={'label':label,'original_path':item['original_path'],'canonical_path':p,'bridge_case':case,'reference_groups':oldgroups,'actual_groups':newgroups,'original_annotations':{k:o.get(k) for k in ['candidate','scenario','research_identity','risk_calibration','subpools']},'canonical_annotations':{k:r.get(k) for k in ['candidate','scenario','research_identity','risk_calibration','subpools']},'monetary_audit':proofs[0],'daily_curve_sha256':checksum(cur),'metrics_sha256':checksum(met),'timing':timing,'receipt':receipt,'passed':True};put(checkpoint,d);cases[label]=case;details[label]=d;print('CANONICAL PASS',label,flush=True)
 require(set(cases)=={'base','fee150','slip2','outage','unity-risk-base'},'exact five')
 source=cases['base']['source'];base=cases['base'];template={'candidate':'crowding-interaction','adapter':'canonical-spot-crowding-v1','components':['crowding-interaction'],'scale':'1','source':source,'measured_source':base['measured_source'],'account_id':base['account_id'],'raw_sha256':base['original_raw_sha256'],'original_accepted_result_sha256':[c['original_raw_sha256'] for c in cases.values()],'canonical_accounts':cases}
 put(OUT/'spot-canonical-five-case-proof.json',{'format':'btc-edge-canonical-five-independent-financial-proof-v1','status':'independently_reviewed','inventory':{'path':str(INV),'sha256':sha(INV)},'cases':details,'source_archive':load(OUT/'canonical-source.json'),'native_cases':0,'actual_account_days':0,'prospective_alpha_proven':False,'script_sha256':sha(__file__)})
 template['canonical_review_sha256']=sha(OUT/'spot-canonical-five-case-proof.json');put(OUT/'spot-canonical-bridge-template.json',template)
 print('FIVE COMPLETE',sha(OUT/'spot-canonical-five-case-proof.json'),flush=True)
if __name__=='__main__':
 try:main()
 except Exception:traceback.print_exc();sys.exit(1)
