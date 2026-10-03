from recompute import *
art=ROOT/'task-artifacts';index=load(art/'reviewed-financial-source-archives.json');checks={}
for item in index['projects']:
 repo=item['repo'];src=item['recorded_source'];p=art/(repo+'-reviewed-financial-source.tar.gz');files=src['protected_files'];modes=src['protected_modes'];actual={};actual_modes={}
 with tarfile.open(p,'r:gz') as t:
  for member in t.getmembers():
   if member.isfile() and member.name in files:
    raw=t.extractfile(member).read();actual[member.name]=hashlib.sha256(raw).hexdigest();actual_modes[member.name]=member.mode;eq(sha(ROOT/repo/member.name),actual[member.name],'current protected source '+member.name)
 eq(actual,files,'original protected archive allfiles');eq(actual_modes,modes,'original protected Git modes');eq(hashlib.sha256(json.dumps({'files':files,'modes':modes},sort_keys=True,separators=(',',':')).encode()).hexdigest(),src['protected_sha256'],'protected source digest')
 checks[repo]={'source':src,'archive':{'path':str(p),'sha256':sha(p)},'protected_count':len(files),'passed':True}
put(OUT/'original-source-archive-binding.json',{'passed':True,'index':{'path':str(art/'reviewed-financial-source-archives.json'),'sha256':sha(art/'reviewed-financial-source-archives.json')},'projects':checks});print('PROTECTED ARCHIVES PASS',[(k,v['protected_count']) for k,v in checks.items()])
