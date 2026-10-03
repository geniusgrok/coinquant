"""Isolated controller tests: temporary paths, fake or harmless Python children only."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import signal
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ART = Path(__file__).resolve().parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

r = load('runner', ART/'run-registered-phase.py')
f = load('freeze', ART/'prepare-source-freeze.py')
b = load('binding_helper', ART/'bind-phase-inputs.py')

class FakeProcess:
    pid = 918273
    def __init__(self, command, **kwargs):
        self.output = Path(command[-1])
        self.log = kwargs['stdout']
        self.waited = False
    def poll(self):
        return None
    def wait(self):
        self.waited = True
        self.output.write_text('actual fake-process result')
        return 0

class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='controller-isolated-')
        self.root = Path(self.temp.name)
        self.jobs = [dict(label=name, command=['harmless',str(self.root/(name+'.json'))],
                          cwd=str(self.root), project_kind='spot', output=str(self.root/(name+'.json')))
                     for name in ('one','two','three')]
        self.started = []
        self.provenance = dict(registry_sha256='a'*64)
    def retain_examples(self, name):
        if os.environ.get('CONTROLLER_TEST_EXAMPLES'):
            target=Path(os.environ['CONTROLLER_TEST_EXAMPLES'])/name
            if not target.exists():  # Preserve original retained synthetic evidence across amended checks.
                shutil.copytree(self.root,target,ignore=shutil.ignore_patterns('*.lock'))
    def tearDown(self):
        self.temp.cleanup()
    def factory(self, command, **kwargs):
        process = FakeProcess(command, **kwargs)
        self.started.append(process)
        return process
    def run_core(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return r.run_jobs(self.jobs, kwargs.pop('check', lambda job:None), self.root,
                              'spot', 'isolated', self.provenance, popen=kwargs.pop('popen',self.factory), **kwargs)
    def summary(self):
        return json.loads(next((self.root/'controller-receipts').rglob('finish.json')).read_bytes())
    def drained(self):
        self.assertTrue(all(p.waited and p.log.closed for p in self.started))
        self.assertTrue(self.summary()['all_children_reaped'])
        self.assertEqual(self.summary()['status'],'failed')
    def test_existing_output_drains_and_preserves_pending(self):
        Path(self.jobs[1]['output']).write_text('original')
        self.assertEqual(self.run_core(),2)
        self.assertEqual(len(self.started),1)
        self.drained()
        self.assertEqual(self.summary()['pending_labels'],['two','three'])
        record=json.loads(next((self.root/'controller-receipts').rglob('two.not-started.json')).read_bytes())
        self.assertNotIn('exit_code',record)
        self.assertEqual(Path(self.jobs[1]['output']).read_text(),'original')
        self.retain_examples('launch-failure-drain')
    def test_popen_failure_drains_active_and_closes_failed_log(self):
        failed_logs=[]
        def factory(command, **kwargs):
            if self.started:
                failed_logs.append(kwargs['stdout'])
                raise OSError('isolated Popen failure')
            return self.factory(command, **kwargs)
        self.assertEqual(self.run_core(popen=factory),2)
        self.drained()
        self.assertTrue(failed_logs[0].closed)
        self.assertEqual(self.summary()['pending_labels'],['two','three'])
    def test_launch_receipt_write_failure_with_active_children(self):
        original=r.write_new
        def write(path, body):
            if Path(path).name=='two.launched.json':raise PermissionError('isolated launched receipt')
            return original(path,body)
        with patch.object(r,'write_new',write):self.assertEqual(self.run_core(),2)
        self.drained()
        self.assertEqual(len(self.started),2)
        self.assertEqual(self.summary()['pending_labels'],['three'])
    def test_finish_receipt_failure_retains_truthful_fallback(self):
        original=r.write_new
        def write(path,body):
            if Path(path).name.endswith('command-finish.json'):raise PermissionError('isolated finish unwritable')
            return original(path,body)
        def factory(command,**kwargs):
            process=self.factory(command,**kwargs)
            process.poll=lambda:0
            return process
        with patch.object(r,'write_new',write):self.assertEqual(self.run_core(popen=factory),2)
        self.drained()
        self.assertEqual(len(self.started),2)
        self.assertTrue(all(not x['finish_receipt_saved'] and x['exit_code']==0 for x in self.summary()['results']))
        self.assertTrue(list((self.root/'controller-diagnostics').glob('*.phase-result.json')))
    def test_output_hash_failure_drains_other_active(self):
        original=r.sha
        def digest(path):
            if str(path)==self.jobs[0]['output']:raise OSError('isolated output hash failure')
            return original(path)
        def factory(command,**kwargs):
            process=self.factory(command,**kwargs)
            process.poll=lambda:0
            return process
        with patch.object(r,'sha',digest):self.assertEqual(self.run_core(popen=factory),2)
        self.drained()
        self.assertEqual(len(self.started),2)
        self.assertIsNone(self.summary()['results'][0]['output_sha256'])
    def test_pre_guard_failure_no_launch_persistent_pending(self):
        def check(job):raise ValueError('pre guard mutation')
        self.assertEqual(self.run_core(check=check),2)
        self.assertEqual(self.started,[])
        self.assertEqual(self.summary()['pending_labels'],['one','two','three'])
    def test_post_guard_failure_stops_next_and_drains(self):
        calls=0
        def check(job):
            nonlocal calls
            calls+=1
            if calls>2:raise ValueError('post guard mutation')
        def factory(command,**kwargs):
            process=self.factory(command,**kwargs)
            process.poll=lambda:0
            return process
        self.assertEqual(self.run_core(check=check,popen=factory),2)
        self.drained()
        self.assertEqual(len(self.started),2)
    def test_harmless_actual_child_success_reaped(self):
        self.jobs=self.jobs[:1]
        output=self.jobs[0]['output']
        self.jobs[0]['command']=[sys.executable,'-c','from pathlib import Path; import sys; Path(sys.argv[1]).write_text("ok")',output]
        self.assertEqual(self.run_core(popen=subprocess.Popen),0)
        result=self.summary()['results'][0]
        self.assertTrue(result['reaped'])
        self.assertEqual(result['exit_code'],0)
    def test_actual_nonzero_is_failure(self):
        self.jobs=self.jobs[:1]
        self.jobs[0]['command']=[sys.executable,'-c','raise SystemExit(7)']
        self.assertEqual(self.run_core(popen=subprocess.Popen),2)
        self.assertEqual(self.summary()['results'][0]['exit_code'],7)
    def test_different_phase_denied_before_popen_and_finished_release(self):
        reservation=r.Reservation(self.root,'spot','first')
        try:
            with self.assertRaises(BlockingIOError):self.run_core()
            self.assertEqual(self.started,[])
        finally:reservation.close(True)
        second=r.Reservation(self.root,'spot','second')
        second.close(True)
        self.assertEqual(len(list((self.root/'controller-reservations/spot').glob('*.released.json'))),2)
    def test_unknown_owner_failclosed_even_without_live_process(self):
        reservation=r.Reservation(self.root,'spot','first')
        reservation.close(False)
        with self.assertRaisesRegex(ValueError,'unfinished'):r.Reservation(self.root,'spot','second')
    def test_parent_exit_inherits_reservation_then_unknown_stays_closed(self):
        # Pipe keeps harmless child alive until explicit release, with no sleeps/accounts.
        read_fd,write_fd=os.pipe()
        ready_read,ready_write=os.pipe()
        script='''import importlib.util, os, subprocess, sys
spec=importlib.util.spec_from_file_location('r',sys.argv[1]); r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
owner=r.Reservation(sys.argv[2],'perp','parent')
subprocess.Popen([sys.executable,'-c','import os,sys; os.write(int(sys.argv[2]),b"R"); os.read(int(sys.argv[1]),1)',sys.argv[3],sys.argv[4]],pass_fds=(owner.fd,int(sys.argv[3]),int(sys.argv[4])))
os._exit(0)
'''
        parent=subprocess.Popen([sys.executable,'-c',script,str(ART/'run-registered-phase.py'),str(self.root),str(read_fd),str(ready_write)],pass_fds=(read_fd,ready_write))
        os.close(read_fd);os.close(ready_write)
        try:
            self.assertEqual(os.read(ready_read,1),b'R')
            parent.wait(timeout=5)
            with self.assertRaises(BlockingIOError):r.Reservation(self.root,'perp','second')
        finally:
            os.write(write_fd,b'X');os.close(write_fd)
            # EOF proves child closed descriptors on exit; then owner remains unknown.
            self.assertEqual(os.read(ready_read,1),b'')
            os.close(ready_read)
        with self.assertRaisesRegex(ValueError,'unfinished'):r.Reservation(self.root,'perp','third')
    def test_vault_snapshot_binds_bytes_inventory_and_metadata(self):
        root=self.root/'vault';root.mkdir()
        for name,text in [('a.zip','zip'),('a.zip.CHECKSUM','official'),('metadata.json','meta')]: (root/name).write_text(text)
        snapshot=self.root/'snapshot.json'
        snapshot.write_text(json.dumps(dict(format='immutable-public-vault-snapshot-v1',root=str(root),files=[dict(path=p.name,size=p.stat().st_size,sha256=r.sha(p)) for p in root.iterdir()])))
        bound,tree=f.vault_binding(snapshot)
        self.assertEqual(len(bound),3)
        job=dict(project_kind='perp',cwd=str(self.root))
        freeze=dict(projects=dict(perp=dict(repository=str(self.root),source=dict(dirty=False),bound_files=bound,bound_trees=[tree])))
        with patch.object(r,'source_at',lambda cwd:dict(dirty=False)):
            r.guard(job,freeze)
            for name in ('a.zip','a.zip.CHECKSUM','metadata.json'):
                path=root/name;old=path.read_bytes();path.write_bytes(old+b'changed')
                with self.assertRaises(ValueError):r.guard(job,freeze)
                path.write_bytes(old)
            extra=root/'new';extra.write_text('addition')
            with self.assertRaises(ValueError):r.guard(job,freeze)
            extra.unlink()
            removed=root/'a.zip';data=removed.read_bytes();removed.unlink()
            with self.assertRaises(ValueError):r.guard(job,freeze)
            removed.write_bytes(data)
            (root/'metadata.json').write_text('mutated metadata')
            with self.assertRaises(ValueError):f.vault_binding(snapshot)
    def test_profile_original_and_production_replacement_missing(self):
        original=self.root/'original.json';production=self.root/'production.json'
        original.write_text('{"actual":"export"}');production.write_bytes(original.read_bytes())
        items=[b.binding(original),b.binding(production)]
        r.verify_files(items)
        for path in (original,production):
            saved=path.read_bytes();path.write_text('{"actual":"replacement"}')
            with self.assertRaises(ValueError):r.verify_files(items)
            path.write_bytes(saved)
            path.unlink()
            with self.assertRaises(FileNotFoundError):r.verify_files(items)
            path.write_bytes(saved)
    def assessor_fixture(self):
        # Actual reviewed schema/functions, synthetic account evidence only.
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(ART.parent/'spotquant'))
        from research import edge_assessment as api
        freeze = dict(controller_root=str(self.root), projects={kind:dict(
            repository=str(ART.parent/('spotquant' if kind=='spot' else 'coinquant')),
            source=dict(dirty=False, git_head='synthetic-'+kind)) for kind in ('spot','perp')})
        report = dict(format='btc-edge-assessment-v1', analysis_source=freeze['projects']['spot']['source'],
                      blocking=[],rejected_files=[],pending=['spot individual eligibility remains pending'],
                      contracts={k:dict(spec_sha256=api.SPEC_HASH[k],protocol_sha256=api.PROTOCOL_HASH[k]) for k in api.BASE},
                      accounts={},inputs={},calibration_documents={},calibration_diagnostics={},combinations={},
                      decisions={k:{n:dict(eligible=False,status='pending') for n in api.ORDER[k]} for k in api.BASE},selected=dict(api.BASE))
        for key in api.required_matrix():
            if not key.endswith('|0|unscaled') or key.split('|')[3]!='1E+4':continue
            kind,name,scenario,*_=key.split('|')
            path=self.root/(hashlib.sha256(key.encode()).hexdigest()+'.raw')
            path.write_text('synthetic raw evidence '+key)
            report['accounts'][key]=dict(kind=kind,status='complete',reasons=[],monetary_audit={'synthetic':True},
                source=freeze['projects'][kind]['source'],path=str(path),raw_sha256=r.sha(path))
            report['inputs'][str(path)]=r.sha(path)
        for kind in api.BASE:
            profiles={};diagnostics={}
            for name in [api.BASE[kind],*api.ORDER[kind]]:
                account=report['accounts'][api.account_id(kind,name)]
                profiles[name]=dict(candidate=name,project_kind=kind,scale='1',base_bundle_sha256=account['raw_sha256'],
                    baseline_candidate=api.BASE[kind],effective_from_ms=api.CUTOFF,calibration_end_ms=api.CUTOFF,
                    training_end_day_exclusive='2022-01-01')
                diagnostics[name]=dict(source=account['source'],raw_sha256=account['raw_sha256'],training_days=731)
            report['calibration_documents'][kind]=dict(format=1,project_kind=kind,baseline_candidate=api.BASE[kind],
                cutoff_ms=api.CUTOFF,spec_sha256=api.SPEC_HASH[kind],profiles=profiles)
            report['calibration_diagnostics'][kind]=diagnostics
        return api,freeze,report
    def test_actual_assessor_interface_requires_all_audited_unscaled_bases(self):
        api,freeze,report=self.assessor_fixture()
        self.assertEqual(len(b.validate_report(report,freeze,api)),52)
        document=report['calibration_documents']['spot']
        b.validate_export(report,document,'spot','spot',freeze,api)
        key=api.account_id('spot','exit-confirm')
        report['accounts'][key]['status']='pending'
        with self.assertRaisesRegex(ValueError,'audited'):b.validate_report(report,freeze,api)
        report['accounts'][key]['status']='complete'
        report['blocking']=['original rejection']
        with self.assertRaisesRegex(ValueError,'nonblocking'):b.validate_report(report,freeze,api)
    def test_actual_profile_schema_source_spec_and_raw_mismatch(self):
        api,freeze,report=self.assessor_fixture()
        original=json.dumps(report['calibration_documents']['spot'])
        for mutate in (lambda d:d.update(project_kind='perp'),lambda d:d.update(spec_sha256='0'*64),
                       lambda d:d['profiles']['exit-confirm'].update(base_bundle_sha256='0'*64)):
            doc=json.loads(original);mutate(doc)
            with self.assertRaises(ValueError):b.validate_export(report,doc,'spot','spot',freeze,api)
        document=json.loads(original)
        report['calibration_diagnostics']['spot']['exit-confirm']['source']={'changed':'source'}
        with self.assertRaisesRegex(ValueError,'source'):b.validate_export(report,document,'spot','spot',freeze,api)
    def test_exclusive_phase_binding_actual_export_paths_and_byte_identity(self):
        api,freeze,report=self.assessor_fixture()
        freeze_path=self.root/'freeze.json';freeze_path.write_text(json.dumps(freeze))
        (self.root/'controller-parent-freeze.json').write_text(json.dumps(b.binding(freeze_path)))
        export_dir=self.root/'original-assessor-exports';export_dir.mkdir()
        export=export_dir/'spot.json';export.write_text(json.dumps(report['calibration_documents']['spot']))
        production=self.root/'spot-calibration.json';production.write_bytes(export.read_bytes())
        report_path=self.root/'assessment.json'
        report['command']=[sys.executable,'-m','research.edge_assessment','--phase','calibration','--calibration-out-dir',str(export_dir),'--out',str(report_path)]
        report_path.write_text(json.dumps(report))
        registry=self.root/'registry.json';registry.write_text(json.dumps(dict(jobs=[dict(project_kind='spot',phase='risk',command=['synthetic','--risk-calibration',str(production)])])))
        out=self.root/'binding.json'
        argv=['--freeze',str(freeze_path),'--report',str(report_path),'--export',str(export),'--production-profile',str(production),
              '--out',str(out),'--kind','spot','--phase','risk','--export-label','spot','--registry',str(registry),'--registry-sha256',r.sha(registry)]
        with patch.object(b,'ART',self.root),patch.object(b.controller,'REGISTRY',registry),patch.object(b.controller,'REGISTRY_SHA',r.sha(registry)),patch.object(b.controller,'guard',lambda job,freeze:None),contextlib.redirect_stdout(io.StringIO()):
            b.main(argv)
            with self.assertRaises(FileExistsError):b.main(argv)
            body=json.loads(out.read_bytes())
            self.assertEqual(body['parent_freeze_sha256'],r.sha(freeze_path))
            self.assertEqual(body['original_export']['sha256'],body['production_profile']['sha256'])
            self.assertEqual(body['project_kind'],'spot')
            self.assertTrue(body['created_utc'])
            self.retain_examples('derived-binding-synthetic-schema')
            production.write_text(json.dumps(report['calibration_documents']['spot'],indent=2))
            with self.assertRaisesRegex(ValueError,'ORIGINAL export bytes'):b.main(argv)
    def test_conditional_registry_rejects_subset_arbitrary_command_and_wrong_parent(self):
        api,freeze,report=self.assessor_fixture()
        kind='spot';parts=list(api.ORDER[kind][:2])
        report['combinations'][kind]=parts
        report['decisions'][kind]={n:dict(eligible=n in parts,status='complete') for n in api.ORDER[kind]}
        report_file=self.root/'condition-report.json';report_file.write_text(json.dumps(report))
        original=json.loads(r.REGISTRY.read_bytes())['jobs']
        exemplar=next(j for j in original if j['project_kind']==kind)
        output_root=Path(exemplar['output']).parent.parent
        features=exemplar['command'][exemplar['command'].index('--features')+1]
        jobs=[]
        for scenario in api.STRESSES[kind]:
            out=str(output_root/'conditional'/('combo-'+scenario+'.json.gz'))
            jobs.append(dict(label='combo-'+scenario,project_kind=kind,phase='combo-unscaled',cwd=freeze['projects'][kind]['repository'],
                expected_accounts=1,output=out,command=[*exemplar['command'][:4],'--candidate','combo','--combo',','.join(parts),
                '--scenario',scenario,'--features',features,'--out',out]))
        registry=dict(format='btc-edge-conditional-registration-v1',parent_freeze_sha256='f'*64,parent_registry_sha256=r.REGISTRY_SHA,
            assessment_report=b.binding(report_file),bound_files=[b.binding(report_file),*b.validate_report(report,freeze,api)],
            condition='all-eligible-combination',role='unscaled',project_kind=kind,phase='combo-unscaled',jobs=jobs)
        b.validate_supplement(registry,'f'*64,freeze)
        (self.root/'supplemental-registry.json').write_text(json.dumps(registry,indent=2))
        self.retain_examples('conditional-registry-synthetic-schema')
        with self.assertRaisesRegex(ValueError,'parent'):b.validate_supplement(registry,'e'*64,freeze)
        registry['jobs']=jobs[:-1]
        with self.assertRaisesRegex(ValueError,'inventory'):b.validate_supplement(registry,'f'*64,freeze)
        registry['jobs']=jobs
        command=jobs[0]['command'];old=command[0];command[0]='/bin/echo'
        with self.assertRaisesRegex(ValueError,'entrypoint'):b.validate_supplement(registry,'f'*64,freeze)
        command[0]=old
        command[command.index('--combo')+1]=parts[0]
        with self.assertRaisesRegex(ValueError,'ALL eligible'):b.validate_supplement(registry,'f'*64,freeze)
    def test_phase_finish_unwritable_retains_fallback_and_release_error_stays_unknown(self):
        self.jobs=self.jobs[:1]
        def factory(command,**kwargs):
            process=self.factory(command,**kwargs);process.poll=lambda:0;return process
        original=r.write_new
        def write(path,body):
            if Path(path).name=='finish.json' or str(path).endswith('.released.json'):
                raise PermissionError('isolated receipt destination unwritable')
            return original(path,body)
        with patch.object(r,'write_new',write):self.assertEqual(self.run_core(popen=factory),2)
        self.assertTrue(self.started[0].waited and self.started[0].log.closed)
        results=[json.loads(p.read_bytes()) for p in (self.root/'controller-diagnostics').glob('*.phase-result.json')]
        self.assertTrue(any(any(e['stage']=='reservation_release' for e in result['errors']) for result in results))
        self.assertTrue(all(result['status']=='failed' and result['results'][0]['reaped'] for result in results))
        with self.assertRaisesRegex(ValueError,'unfinished'):r.Reservation(self.root,'spot','next-phase')
    def test_main_rechecks_parent_and_phase_input_before_after(self):
        # Synthetic immutable parent and registry; no source or producer execution.
        source=dict(dirty=False)
        freeze_path=self.root/'freeze.json'
        freeze=dict(format='btc-edge-reviewed-source-freeze-v1',controller_root=str(self.root),projects=dict(spot=dict(
            repository=str(self.root),source=source,bound_files=[],bound_trees=[])))
        freeze_path.write_text(json.dumps(freeze))
        (self.root/'controller-parent-freeze.json').write_text(json.dumps(b.binding(freeze_path)))
        profile=self.root/'profile.json';profile.write_text('original export bytes')
        report=self.root/'report.json';report.write_text('original report bytes')
        job=self.jobs[0];job.update(phase='risk',command=['synthetic','--risk-calibration',str(profile)])
        registry=self.root/'registry.json';registry.write_text(json.dumps(dict(jobs=[job])))
        registry_sha=r.sha(registry)
        derived=dict(format='btc-edge-phase-input-binding-v1',parent_freeze_sha256=r.sha(freeze_path),project_kind='spot',
            phase='risk',registry_sha256=registry_sha,assessor_report=b.binding(report),original_export=b.binding(profile),
            production_profile=b.binding(profile),bound_files=[b.binding(freeze_path),b.binding(report),b.binding(profile)])
        phase_path=self.root/'phase-input.json';phase_path.write_text(json.dumps(derived))
        argv=['--phase','risk','--kind','spot','--freeze',str(freeze_path),'--phase-input',str(phase_path)]
        def inspect(jobs,check,*args,**kwargs):
            check(jobs[0])
            for path in (profile,report,phase_path,freeze_path,self.root/'controller-parent-freeze.json'):
                previous=path.read_bytes();path.write_bytes(previous+b'changed')
                with self.assertRaises(ValueError):check(jobs[0])
                path.write_bytes(previous)
            return 0
        with patch.object(r,'ART',self.root),patch.object(r,'REGISTRY',registry),patch.object(r,'REGISTRY_SHA',registry_sha),patch.object(r,'source_at',lambda cwd:source),patch.object(r,'run_jobs',inspect):
            self.assertEqual(r.main(argv),0)
            anchor=self.root/'controller-parent-freeze.json';body=json.loads(anchor.read_bytes());body['sha256']='0'*64;anchor.write_text(json.dumps(body))
            with self.assertRaisesRegex(ValueError,'original anchor'):r.main(argv)
    def test_signal_during_launch_registers_then_drains_child(self):
        def factory(command,**kwargs):
            process=self.factory(command,**kwargs)
            os.kill(os.getpid(),signal.SIGTERM)
            return process
        self.assertEqual(self.run_core(popen=factory),2)
        self.drained()
        self.assertEqual(len(self.started),1)
        self.assertEqual(self.summary()['pending_labels'],['two','three'])
    def test_original_registry_and_preserved_review_identity(self):
        self.assertEqual(r.sha(r.REGISTRY),r.REGISTRY_SHA)
        self.assertEqual(r.sha(ART/'task-6-controller-review.md'),'59c7fbfe0dee244874331bd50feee5a9b6d1c1554d61ee1aa424a4611805b57b')

if __name__=='__main__':unittest.main(verbosity=2)
