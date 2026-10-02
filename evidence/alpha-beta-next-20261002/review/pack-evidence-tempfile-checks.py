import copy
import importlib.util
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

TOOL = Path('/workspace/btc-alpha-beta-next/review/pack_completed_evidence.py')
spec = importlib.util.spec_from_file_location('copier', TOOL)
a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)

def write(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body))

def sha(path): return a.fingerprint(path)['sha256']

with tempfile.TemporaryDirectory(prefix='evidence-copy-tests-') as temp:
    root = Path(temp)
    a.SCRATCH = root/'scratch'; a.REVIEW = root/'review'
    a.SCRATCH.mkdir(); a.REVIEW.mkdir()
    (a.REVIEW/TOOL.name).write_bytes(TOOL.read_bytes())
    for name in a.DOC_PINS: (a.REVIEW/name).write_bytes(b'reviewed doc\r\n')
    a.DOC_PINS = {name: sha(a.REVIEW/name) for name in a.DOC_PINS}
    required = a.REVIEW/'final-reviewed.md'; required.write_bytes(b'bridge decision diaries fixture\r\n')
    pins = {str(required): sha(required)}
    for name in a.PARTIALS: (a.SCRATCH/name).write_bytes(b'partial bytes\x00\r\n')
    (a.SCRATCH/'public-print-vault-watch.log').write_bytes(b'watch stopped\n')
    write(a.SCRATCH/'public-print-vault/records/a.json', {'observed':'public'})
    write(a.SCRATCH/'other.progress.json', {'exclude':True})
    write(a.SCRATCH/'tmp/excluded.json', {'exclude':True})
    (a.SCRATCH/'figures').mkdir()
    (a.SCRATCH/'figures/plot.png').write_bytes(b'unchanged PNG fixture')
    (a.SCRATCH/'figures/plot.svg').write_bytes(b'<svg><!-- exact fixture --></svg>')
    write(a.SCRATCH/'figures/provenance.json', {'source_sha256':'a'*64})
    (a.SCRATCH/'spot-singletons').mkdir()
    canonical = []
    for name in ('base','fee150','slip2','outage','calibrated-base'):
        p=a.SCRATCH/'spot-canonical'/(name+'.json.gz');p.parent.mkdir(exist_ok=True);p.write_bytes(b'original gzip fixture '+name.encode())
        canonical.append({'label':name,'path':p.name,'sha256':sha(p),
                          'calibrated':name=='calibrated-base','scenario':'base' if name=='calibrated-base' else name})
    write(a.SCRATCH/'spot-canonical/canonical-inventory.json',{'files':canonical})
    final = {'rules_freeze_ready':True,'all_measured_accounts_valid':True,'pending':[],
             'sensitivity_missing':[], 'registered_work_pending':False,'risk_accounts_pending':False,
             'native_cases':0,'actual_account_days':0,'accounts':{},'sensitivity':[],'inputs':{}}
    indexes={'unscaled':{'account_count':48,'audits':[]},'remaining':{'account_count':16,'audits':[],
        'final_inventory_exactly_reconciled':True,'all_examined_checks_passed':True,'all_reported_complete':True}}
    def audit(kind,stage,number,keys):
        raw=a.SCRATCH/('spot-singletons/' if stage=='unscaled' and kind=='spot' else '')/f'{kind}-{stage}-{number}.json.gz'
        raw.write_bytes(b'raw exact \x00\r\n'+str(raw).encode())
        digest=sha(raw); audited={}
        for key in keys:
            candidate,scenario=key.split('/')
            account={'valid':True,'candidate':candidate,'scenario':scenario,'raw_bundle_sha256':digest}
            audited[key]={'reported_complete':True,'independent_checks_passed':True,'errors':[]}
            if stage=='sensitivity': final['sensitivity'].append({'account':account,'raw_sha256':digest})
            else: final['accounts'][kind+('/risk/' if stage=='risk' else '/')+key]=account
        path=a.REVIEW/f'audit-{kind}-{stage}-{number}.json'
        write(path,{'raw_path':str(raw),'raw_sha256':digest,'kind':kind,'accounts':audited,
                    'all_examined_checks_passed':True,'all_reported_complete':True})
        entry={'raw_sha256':digest}
        if stage=='unscaled': entry.update(path=str(path),sha256=sha(path))
        else: entry.update(audit_path=str(path),audit_sha256=sha(path),raw_path=str(raw),stage=stage,kind=kind,
                          account_keys=sorted(keys),accounts=len(keys),all_checks_passed=True,all_reported_complete=True)
        indexes['unscaled' if stage=='unscaled' else 'remaining']['audits'].append(entry)
    for kind,names in a.CANDIDATES.items():
        audit(kind,'unscaled',0,[n+'/'+s for n in names for s in a.SCENARIOS[kind]])
        audit(kind,'risk',0,[n+'/base' for n in names])
    for n in range(4): audit('perp','sensitivity',n,['incumbent/base'])
    finalpath=a.SCRATCH/'registered-final.json';write(finalpath,final)
    (a.SCRATCH/'registered-final.run.log').write_bytes(b'command log\r\n')
    receipt={'exit_code':0,'command':['python','--final','--out',str(finalpath)],'output_sha256':sha(finalpath),
             'log_sha256':sha(a.SCRATCH/'registered-final.run.log')}
    write(a.SCRATCH/'registered-final.command.json',receipt)
    indexes['remaining']['final_assessment_sha256']=sha(finalpath)
    for stage,body in indexes.items():write(a.REVIEW/f'financial-audit-{stage}-index.json',body)
    failures=[]
    def reject(label, match=None):
        out=root/label
        try: a.pack(out,[required],pins)
        except (ValueError,FileNotFoundError) as error:
            assert not out.exists(), label
            if match: assert match in str(error), str(error)
            failures.append(label)
        else: raise AssertionError('accepted '+label)
    with patch.object(a,'stopped',side_effect=ValueError('active processes')): reject('active')
    with patch.object(a,'stopped',return_value=None):
        saved=finalpath.read_bytes();finalpath.unlink();reject('missing-final');finalpath.write_bytes(saved)
        bad=dict(final,pending=['still pending']);write(finalpath,bad)
        receipt['output_sha256']=sha(finalpath);write(a.SCRATCH/'registered-final.command.json',receipt)
        reject('pending','pending');finalpath.write_bytes(saved)
        receipt['output_sha256']=sha(finalpath);write(a.SCRATCH/'registered-final.command.json',receipt)
        path=a.REVIEW/'financial-audit-remaining-index.json';original=path.read_bytes()
        indexes['remaining']['final_assessment_sha256']='0'*64;write(path,indexes['remaining']);reject('wrong-final-sha');path.write_bytes(original)
        link=a.REVIEW/'link.json';link.symlink_to(required);reject('symlink','symlink');link.unlink()
        oversized=a.REVIEW/'oversized.json'
        with oversized.open('wb') as stream:stream.truncate(a.LIMIT)
        reject('oversized','100MiB');oversized.unlink()
        canonical_path=a.SCRATCH/'spot-canonical/canonical-inventory.json'
        saved_canonical=canonical_path.read_bytes()
        duplicate=copy.deepcopy(canonical)
        for entry in duplicate:
            entry['path']=canonical[0]['path'];entry['sha256']=canonical[0]['sha256']
        write(canonical_path,{'files':duplicate});reject('duplicate-canonical-path','label/path')
        canonical_path.write_bytes(saved_canonical)
        for key,value in [('scenario','base'),('calibrated',True)]:
            bad=copy.deepcopy(canonical);bad[1][key]=value
            write(canonical_path,{'files':bad});reject('wrong-canonical-'+key,'scenario/calibration')
            canonical_path.write_bytes(saved_canonical)
        for label,error in [('manifest-serialization',TypeError('injected serialization failure')),
                            ('manifest-write',OSError('injected write failure'))]:
            failed_output=root/label
            def broken_dump(body,stream,**kwargs):
                stream.write('{"partial":')
                raise error
            with patch.object(a.json,'dump',side_effect=broken_dump):
                try:a.pack(failed_output,[required],pins)
                except type(error):pass
                else:raise AssertionError('manifest failure not propagated')
            assert failed_output.is_dir() and not (failed_output/'MANIFEST.json').exists()
            assert not list(failed_output.glob('.MANIFEST.*.tmp'))
            failures.append(label)
        failed_output=root/'manifest-fsync'
        with patch.object(a.os,'fsync',side_effect=OSError('injected fsync failure')):
            try:a.pack(failed_output,[required],pins)
            except OSError:pass
            else:raise AssertionError('fsync failure not propagated')
        assert not (failed_output/'MANIFEST.json').exists()
        assert not list(failed_output.glob('.MANIFEST.*.tmp'))
        failures.append('manifest-fsync')
        protected=root/'manifest-existing';protected.mkdir()
        (protected/'MANIFEST.json').write_bytes(b'original final bytes\r\n')
        try:a.publish_manifest(protected,{'replacement':True})
        except FileExistsError:pass
        else:raise AssertionError('existing manifest replaced')
        assert (protected/'MANIFEST.json').read_bytes()==b'original final bytes\r\n'
        assert not list(protected.glob('.MANIFEST.*.tmp'))
        failures.append('existing-manifest-no-overwrite')
        unlink_original=Path.unlink
        def fail_manifest_cleanup(path, *args, **kwargs):
            if path.name.startswith('.MANIFEST.') and path.suffix=='.tmp':
                raise PermissionError('injected cleanup failure')
            return unlink_original(path, *args, **kwargs)
        published_output=root/'post-link-unlink-failure'
        with patch.object(Path,'unlink',fail_manifest_cleanup):
            published=a.pack(published_output,[required],pins)
        assert json.loads((published_output/'MANIFEST.json').read_text())==published
        assert len(list(published_output.glob('.MANIFEST.*.tmp')))==1
        failures.append('post-link-unlink-failure-is-success')
        unpublished=root/'prepublication-error-and-unlink-failure';unpublished.mkdir()
        original_error=ValueError('original serialization error')
        with patch.object(Path,'unlink',fail_manifest_cleanup), patch.object(a.json,'dump',side_effect=original_error):
            try:a.publish_manifest(unpublished,{'fixture':True})
            except ValueError as error:assert error is original_error
            else:raise AssertionError('original publication error lost')
        assert not (unpublished/'MANIFEST.json').exists()
        assert len(list(unpublished.glob('.MANIFEST.*.tmp')))==1
        failures.append('prepublication-error-not-masked-by-cleanup')
        output=root/'package';manifest=a.pack(output,[required],pins)
        assert json.loads((output/'MANIFEST.json').read_text())==manifest
        assert not list(output.glob('.MANIFEST.*.tmp'))
        for item in manifest['files']:
            assert Path(item['original_absolute_path']).read_bytes()==(output/item['archive_path']).read_bytes()
        assert len([item for item in manifest['files'] if item['classification'].startswith('operational-incomplete')])==3
        assert not (output/'scratch/other.progress.json').exists()
        assert not (output/'scratch/tmp').exists()
        assert (output/'scratch/figures/plot.png').read_bytes()==b'unchanged PNG fixture'
        assert (output/'scratch/figures/plot.svg').read_bytes()==b'<svg><!-- exact fixture --></svg>'
        assert (output/'scratch/figures/provenance.json').is_file()
        assert (output/'review'/TOOL.name).read_bytes()==TOOL.read_bytes()
        try:a.pack(output,[required],pins)
        except ValueError as error:assert 'NEW' in str(error);failures.append('overwrite')
        else:raise AssertionError('overwrite accepted')
        print(json.dumps({'tempfile_checks_passed':failures+['full-64-plus-5-byte-copy','relative-paths','exclusions','self-hash','operational-partials','figures-and-provenance'],
                          'copied_files':len(manifest['files']),'tool_sha256':sha(TOOL),'real_output_used':False}))
