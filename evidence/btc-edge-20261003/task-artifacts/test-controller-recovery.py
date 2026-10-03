"""Retained isolated recovery fixtures; no financial producer/account operation."""
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ART = Path(__file__).resolve().parent
RECEIPTS = ART/'task-6-recovery-isolated-receipts'
RECEIPTS.mkdir(exist_ok=True)
sys.dont_write_bytecode = True

def load(path):
    spec=importlib.util.spec_from_file_location('isolated_'+str(time.time_ns()),path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

r=load(ART/'run-registered-recovery.py')
legacy=load(ART/'test-controller-fix2.py')

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(tempfile.mkdtemp(prefix=self._testMethodName+'-',dir=RECEIPTS))
        self.provenance={'registry_sha256':'a'*64}
    def jobs(self,kind='spot',code=None):
        code=code or 'from pathlib import Path; import sys,time; time.sleep(.06); Path(sys.argv[1]).write_text("done")'
        return [dict(label=label,command=[sys.executable,'-c',code,str(self.root/(label+'.json'))],
                     output=str(self.root/(label+'.json')),cwd=str(self.root),project_kind=kind)
                for label in ('first','second','third')]
    def run_core(self,jobs=None,**kw):
        with contextlib.redirect_stdout(io.StringIO()) as log:
            result=r.run_jobs(jobs or self.jobs(),kw.pop('check',lambda job:None),self.root,
                              kw.pop('kind','spot'),'probe',self.provenance,**kw)
        (self.root/'probe-controller.log').write_text(log.getvalue())
        return result
    def summary(self):
        return json.loads(next((self.root/'controller-receipts').rglob('finish.json')).read_bytes())
    def assert_released(self):
        summary=self.summary()
        self.assertTrue(summary['all_children_reaped'])
        for release in (self.root/'controller-reservations').rglob('*.released.json'):
            body=json.loads(release.read_bytes())
            self.assertEqual(body['owner_sha256'],r.sha(str(release).replace('.released.json','.owner.json')))
            self.assertIs(body['all_children_reaped'],True)
    def test_one_child_per_project(self):
        for kind in ('spot','perp'):
            with self.subTest(kind=kind):
                self.root=self.root/kind;self.root.mkdir()
                active=[]
                def popen(command,**kwargs):
                    self.assertTrue(all(p.poll() is not None for p in active),'overlapping project children')
                    process=subprocess.Popen(command,**kwargs);active.append(process);return process
                self.assertEqual(self.run_core(self.jobs(kind),kind=kind,popen=popen),0)
                self.assertEqual(len(active),3);self.assert_released()
    def test_actual_nonzero_pending_and_no_rerun(self):
        jobs=self.jobs(code='from pathlib import Path; import sys; Path(sys.argv[1]).write_text("failed"); raise SystemExit(7)')
        self.assertEqual(self.run_core(jobs),2)
        self.assertEqual(self.summary()['results'][0]['exit_code'],7)
        self.assertEqual(self.summary()['pending_labels'],['second','third']);self.assert_released()
        before=Path(jobs[0]['output']).read_bytes()
        with patch.object(r.subprocess,'Popen',side_effect=AssertionError('no rerun')):
            self.assertEqual(self.run_core(jobs),2)
        self.assertEqual(Path(jobs[0]['output']).read_bytes(),before)
    def test_existing_output_and_progress_refuse_before_popen(self):
        for suffix in ('output','progress'):
            self.root=self.root/suffix;self.root.mkdir()
            jobs=self.jobs();output=Path(jobs[0]['output'])
            occupied=output if suffix=='output' else output.with_suffix('.progress.json')
            occupied.write_text('original occupied bytes')
            def forbidden(*args,**kwargs):raise AssertionError('existing destination must not launch')
            self.assertEqual(self.run_core(jobs,popen=forbidden),2)
            self.assertEqual(self.summary()['results'],[])
            self.assertEqual(self.summary()['pending_labels'],['first','second','third'])
            self.assertEqual(occupied.read_text(),'original occupied bytes');self.assert_released()
    def test_original_conditional_validator_remains_all_eligible(self):
        fixture=legacy.ControllerTests('test_conditional_registry_rejects_subset_arbitrary_command_and_wrong_parent')
        fixture.root=self.root
        fixture.test_conditional_registry_rejects_subset_arbitrary_command_and_wrong_parent()
        registry=json.loads((self.root/'supplemental-registry.json').read_bytes())
        recovered=[r.transformed_job(j) for j in registry['jobs']]
        self.assertEqual(len(recovered),4)
        self.assertTrue(all(j['original_job'] in registry['jobs'] for j in recovered))
    def test_popen_failure_pending_truth_and_closed_log(self):
        logs=[]
        def fail(*args,**kwargs):logs.append(kwargs['stdout']);raise OSError('isolated Popen failure')
        self.assertEqual(self.run_core(popen=fail),2)
        self.assertTrue(logs[0].closed)
        self.assertEqual(self.summary()['results'],[])
        self.assertEqual(self.summary()['pending_labels'],['first','second','third']);self.assert_released()
    def test_post_popen_bookkeeping_signal_drain_both_signals(self):
        for signum in (signal.SIGINT,signal.SIGTERM):
            self.root=self.root/str(int(signum));self.root.mkdir()
            children=[];signals=[];blocked=[]
            original=r.write_new
            def write(path,body):
                if Path(path).name=='first.launched.json':
                    raise PermissionError('isolated post-Popen bookkeeping')
                return original(path,body)
            def popen(*args,**kwargs):
                process=subprocess.Popen(*args,**kwargs);children.append(process)
                wait=process.wait
                def waiting(*a,**kw):
                    if not signals:
                        self.assertIsNone(process.poll());os.kill(os.getpid(),signum);signals.append(int(signum))
                        try:r.Reservation(self.root,'spot','other')
                        except BlockingIOError:blocked.append(True)
                    return wait(*a,**kw)
                process.wait=waiting;return process
            alive=[]
            def check(job):
                if children:alive.append(children[0].poll() is None)
            with patch.object(r,'write_new',write):self.assertEqual(self.run_core(popen=popen,check=check),2)
            summary=self.summary();self.assertEqual(signals,[int(signum)]);self.assertEqual(blocked,[True])
            self.assertEqual(alive,[False]);self.assertEqual(summary['pending_labels'],['second','third'])
            self.assertEqual(summary['results'][0]['exit_code'],0)
            self.assertTrue(any(e['stage']=='handled_signal' for e in summary['errors']));self.assert_released()
    def test_signal_in_popen_window_drains_actual_child(self):
        children=[]
        def popen(*args,**kwargs):
            process=subprocess.Popen(*args,**kwargs);children.append(process)
            os.kill(os.getpid(),signal.SIGTERM);return process
        self.assertEqual(self.run_core(popen=popen),2)
        self.assertEqual(children[0].returncode,0);self.assertEqual(self.summary()['pending_labels'],['second','third'])
        self.assert_released()
    def test_post_guard_hash_and_receipt_failure_preserve_actual_exit(self):
        for stage in ('guard','hash','receipt','phase','release'):
            self.root=self.root/stage;self.root.mkdir()
            checks=[];original_sha=r.sha;original_write=r.write_new
            def check(job):
                checks.append(job)
                if stage=='guard' and len(checks)>1:raise ValueError('source changed')
            def sha(path):
                if stage=='hash' and Path(path).name=='first.json':raise OSError('output hash unavailable')
                return original_sha(path)
            def write(path,body):
                name=Path(path).name
                if ((stage=='receipt' and name.endswith('.command-finish.json')) or
                    (stage=='phase' and name=='finish.json') or
                    (stage=='release' and name.endswith('.released.json'))):raise OSError('receipt unavailable')
                return original_write(path,body)
            with patch.object(r,'sha',sha),patch.object(r,'write_new',write):
                self.assertEqual(self.run_core(check=check),2)
            fallback=list((self.root/'controller-diagnostics').glob('*.phase-result.json'))
            self.assertTrue(fallback)
            summary=json.loads(fallback[-1].read_bytes())
            self.assertTrue(summary['all_children_reaped']);self.assertEqual(summary['results'][0]['exit_code'],0)
            if stage=='release':
                with self.assertRaisesRegex(ValueError,'unfinished'):r.Reservation(self.root,'spot','another')
    def test_original_and_recovery_shared_reservation_inherited_child(self):
        original=load(ART/'run-registered-phase.py')
        owner=original.Reservation(self.root,'spot','original')
        try:
            with self.assertRaises(BlockingIOError):r.Reservation(self.root,'spot','recovery')
        finally:owner.close(True)
        # Parent exits abruptly; inherited fd blocks recovery until actual child exit,
        # then unknown durable original owner still refuses reuse.
        read_fd,write_fd=os.pipe();ready_read,ready_write=os.pipe()
        script='''import importlib.util,os,subprocess,sys
s=importlib.util.spec_from_file_location('r',sys.argv[1]);r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
x=r.Reservation(sys.argv[2],'perp','parent')
subprocess.Popen([sys.executable,'-c','import os,sys; os.write(int(sys.argv[2]),b"R"); os.read(int(sys.argv[1]),1)',sys.argv[3],sys.argv[4]],pass_fds=(x.fd,int(sys.argv[3]),int(sys.argv[4])))
os._exit(0)
'''
        parent=subprocess.Popen([sys.executable,'-c',script,str(ART/'run-registered-recovery.py'),str(self.root),str(read_fd),str(ready_write)],pass_fds=(read_fd,ready_write))
        os.close(read_fd);os.close(ready_write)
        try:
            self.assertEqual(os.read(ready_read,1),b'R');parent.wait(timeout=5)
            with self.assertRaises(BlockingIOError):original.Reservation(self.root,'perp','other')
        finally:
            os.write(write_fd,b'X');os.close(write_fd)
            self.assertEqual(os.read(ready_read,1),b'');os.close(ready_read)
        with self.assertRaisesRegex(ValueError,'unfinished'):r.Reservation(self.root,'perp','next')
    def test_tmpdir_actual_propagation_home_uid_and_environment(self):
        tmp=self.root/'tmp';tmp.mkdir()
        before=dict(os.environ)
        code='import os,json,tempfile,sys; from pathlib import Path; t=tempfile.TemporaryDirectory(); Path(sys.argv[1]).write_text(json.dumps(dict(env=dict(os.environ),uid=os.getuid(),tmp=t.name))); t.cleanup()'
        jobs=self.jobs(code=code)[:1]
        self.assertEqual(self.run_core(jobs,environment=dict(os.environ,TMPDIR=str(tmp))),0)
        body=json.loads(Path(jobs[0]['output']).read_bytes())
        self.assertEqual(body['env'],dict(before,TMPDIR=str(tmp)));self.assertEqual(body['uid'],os.getuid())
        self.assertEqual(Path(body['tmp']).parent,tmp);self.assertEqual(dict(os.environ),before)
    def test_storage_overlay_floor_owner_residue_and_symlink(self):
        recovery=self.root/'recovery1'
        with patch.object(r,'RECOVERY_ROOT',recovery):
            result=r.storage_guard('spot','a'*64)
            self.assertEqual(result['filesystem'],'overlayfs');self.assertGreaterEqual(result['available_bytes'],r.MIN_FREE_BYTES)
            tmp=Path(result['path']);(tmp/'residue').write_text('preserve')
            with self.assertRaisesRegex(ValueError,'unreaped'):r.storage_guard('spot','a'*64)
            self.assertEqual((tmp/'residue').read_text(),'preserve')
            with self.assertRaisesRegex(ValueError,'owner mismatch'):r.storage_guard('spot','b'*64)
            with patch.object(r,'MIN_FREE_BYTES',10**20):
                with self.assertRaisesRegex(ValueError,'insufficient'):r.storage_guard('perp','a'*64)
            (self.root/'link').symlink_to(tmp,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'symlink'):r.no_symlinks(self.root/'link'/'file')
    def test_mapping_exact50_no_dropped_negatives_calibration_unchanged(self):
        original=json.loads(r.REGISTRY.read_bytes())['jobs']
        jobs=[r.transformed_job(j) for j in original]
        self.assertEqual(len(jobs),50);self.assertEqual(sum(j['expected_accounts'] for j in jobs if j['phase']=='unscaled'),52)
        self.assertEqual(sum(j['expected_accounts'] for j in jobs if j['phase']=='risk'),8)
        self.assertEqual(sum(j['expected_accounts'] for j in jobs if j['phase']=='sensitivity'),2)
        self.assertEqual(sum(j['expected_accounts'] for j in jobs if j['phase']=='budgets'),6)
        for old,new in zip(original,jobs):
            self.assertEqual(new['original_job'],old)
            allowed={old['command'].index(k)+1 for k in ('--out','--prints') if k in old['command']}
            for index,(a,b) in enumerate(zip(old['command'],new['command'])):
                self.assertEqual(a==b,index not in allowed)
            for k in ('phase','project_kind','cwd','expected_accounts','label'):self.assertEqual(old[k],new[k])
        self.assertEqual(len({j['output'] for j in jobs}),50)
    def test_fresh_print_binary_owner_and_output_symlink_refused(self):
        original=next(j for j in json.loads(r.REGISTRY.read_bytes())['jobs'] if j['project_kind']=='perp')
        with patch.object(r,'RECOVERY_ROOT',self.root/'recovery1'):
            job=r.transformed_job(original);r.fresh_paths(job)
            path=Path(job['command'][job['command'].index('--prints')+1]);path.parent.mkdir(parents=True)
            cache=Path(str(path)+'-cache');cache.mkdir()
            with self.assertRaisesRegex(ValueError,'existing recovery print/cache'):r.fresh_paths(job)
            self.assertTrue(cache.exists())
    def authority_fixture(self):
        art=self.root/'art';art.mkdir()
        for name in ('run-registered-recovery.py','registered-financial-commands.json','reviewed-source-freeze.json',
                     'run-registered-phase.py','prepare-source-freeze.py','bind-phase-inputs.py','task-6-controller-fix2-rereview.md'):
            shutil.copyfile(ART/name,art/name)
        q=load(art/'run-registered-recovery.py')
        q.RECOVERY_ROOT=self.root/'recovery1'
        q.write_new(art/'controller-parent-freeze.json',q.binding(q.FREEZE))
        failure=json.loads((ART/'first-financial-attempt-storage-failure.json').read_bytes())
        failure['retained_files']=[]
        q.write_new(art/'first-financial-attempt-storage-failure.json',failure)
        body=dict(format='btc-edge-resource-recovery-v1',attempt='recovery1',parent_freeze_sha256=q.FREEZE_SHA,
                  parent_registry_sha256=q.REGISTRY_SHA,root_output=str(q.RECOVERY_ROOT),concurrency={'spot':1,'perp':1},
                  minimum_free_bytes=q.MIN_FREE_BYTES,first_failure=q.binding(art/'first-financial-attempt-storage-failure.json'),
                  bound_files=[q.binding(p) for p in art.iterdir() if p.is_file()],first_attempt_trees=[],first_attempt_absent_outputs=[],
                  jobs=[q.transformed_job(j) for j in json.loads(q.REGISTRY.read_bytes())['jobs']])
        q.write_new(q.RECOVERY_REGISTRY,body)
        (art/'task-6-recovery-report.md').write_text('synthetic implementation report')
        (art/'task-6-recovery-rereview.md').write_text('synthetic independent approval')
        approval=dict(format='btc-edge-recovery-approval-v1',attempt='recovery1',approved=True,
                      review=q.binding(art/'task-6-recovery-rereview.md'),bound_files=[q.binding(p) for p in
                      (q.RECOVERY_REGISTRY,art/'run-registered-recovery.py',art/'task-6-recovery-report.md',art/'task-6-recovery-rereview.md')])
        q.write_new(q.APPROVAL,approval)
        return q,body,q.sha(q.RECOVERY_REGISTRY),q.sha(q.APPROVAL)
    def test_authority_tamper_parent_registry_original_helpers_failure_recovery_approval(self):
        q,body,regsha,approvalsha=self.authority_fixture()
        q.verify_authorities(body,regsha,approvalsha)
        names=['controller-parent-freeze.json','reviewed-source-freeze.json','registered-financial-commands.json',
               'run-registered-phase.py','prepare-source-freeze.py','bind-phase-inputs.py','first-financial-attempt-storage-failure.json',
               'registered-financial-recovery1.json','run-registered-recovery.py','recovery-approval.json',
               'task-6-recovery-report.md','task-6-recovery-rereview.md']
        for name in names:
            with self.subTest(name=name):
                path=q.ART/name;before=path.read_bytes();path.write_bytes(before+b' ')
                with self.assertRaises(ValueError):q.verify_authorities(body,regsha,approvalsha)
                path.write_bytes(before)
        for mutate in (lambda x:x['jobs'].pop(),lambda x:x['jobs'][0]['command'].extend(['--limit','1']),
                       lambda x:x['jobs'][0].update(output='elsewhere'),lambda x:x.update(concurrency={'spot':2,'perp':1})):
            bad=copy.deepcopy(body);mutate(bad)
            with self.assertRaises(ValueError):q.validate_registration(bad)
    def test_main_pre_post_guards_provenance_and_registry_mutation(self):
        q,body,regsha,approvalsha=self.authority_fixture()
        checks=[];actual=[]
        def harmless_core(jobs,check,root,kind,phase,provenance,**kwargs):
            self.assertEqual(len(jobs),1)
            job=jobs[0]
            self.assertEqual(job['command'][:4],job['original_job']['command'][:4])
            self.assertEqual(provenance['parent_registry_sha256'],q.REGISTRY_SHA)
            self.assertEqual(provenance['approval_sha256'],approvalsha)
            # Only fixture child code changes, after verifying the production-selected argv.
            job['command']=[sys.executable,'-c','from pathlib import Path; import sys; Path(sys.argv[1]).write_text("done")',job['output']]
            original_check=check
            def wrapped(job):
                actual.append('check')
                original_check(job)
            return q.run_jobs_original(jobs,wrapped,root,kind,phase,provenance,**kwargs)
        q.run_jobs_original=q.run_jobs
        with patch.object(q,'run_jobs',harmless_core),patch.object(q,'guard',lambda job,freeze:checks.append(job['project_kind'])):
            self.assertEqual(q.main(['--phase','unscaled','--kind','perp','--approval-sha256',approvalsha]),0)
        self.assertEqual(checks,['spot','perp','spot','perp']);self.assertEqual(actual,['check','check'])
        start=json.loads(next(q.RECOVERY_ROOT.rglob('*.command-start.json')).read_bytes())
        self.assertEqual(start['original_job']['label'],'perp-registered-16')
        self.assertEqual(start['storage_launch']['filesystem'],'overlayfs')
        # A fresh fixture mutates registry after actual Popen: child drains, post guard fails.
        self.root=self.root/'post-mutation';self.root.mkdir()
        q,body,regsha,approvalsha=self.authority_fixture()
        original_core=q.run_jobs
        def core(jobs,check,root,kind,phase,provenance,**kwargs):
            jobs[0]['command']=[sys.executable,'-c','from pathlib import Path; import sys; Path(sys.argv[1]).write_text("done")',jobs[0]['output']]
            def popen(*args,**kw):
                process=subprocess.Popen(*args,**kw)
                with q.RECOVERY_REGISTRY.open('ab') as stream:stream.write(b' ')
                return process
            return original_core(jobs,check,root,kind,phase,provenance,popen=popen,**kwargs)
        with patch.object(q,'run_jobs',core),patch.object(q,'guard',lambda job,freeze:None):
            self.assertEqual(q.main(['--phase','unscaled','--kind','perp','--approval-sha256',approvalsha]),2)
        summary=json.loads(next((q.ART/'controller-receipts').rglob('finish.json')).read_bytes())
        self.assertTrue(summary['all_children_reaped']);self.assertEqual(summary['results'][0]['exit_code'],0)
        self.assertTrue(any(e['stage']=='post_guard' for e in summary['errors']))
    def test_main_missing_approval_no_launch_or_reservation(self):
        q,body,regsha,approvalsha=self.authority_fixture()
        q.APPROVAL.rename(q.ART/'withheld-approval.json')
        with patch.object(q,'run_jobs',side_effect=AssertionError('must not launch')):
            with self.assertRaises(FileNotFoundError):q.main(['--phase','unscaled','--kind','spot','--approval-sha256',approvalsha])
        self.assertFalse((q.ART/'controller-reservations').exists())
    def test_source_tree_bytes_metadata_and_inventory_tamper(self):
        root=self.root/'input';root.mkdir();data=root/'metadata.json';data.write_text('original')
        source={'dirty':False,'git_head':'synthetic'}
        freeze={'projects':{'spot':{'repository':str(self.root),'source':source,
                'bound_files':[r.binding(data)],'bound_trees':[dict(root=str(root),suffixes=None,files=[str(data)])]}}}
        job={'project_kind':'spot','cwd':str(self.root)}
        with patch.object(r,'source_at',lambda cwd:source):
            r.guard(job,freeze);data.write_text('mutated')
            with self.assertRaises(ValueError):r.guard(job,freeze)
            data.write_text('original');(root/'extra').write_text('extra')
            with self.assertRaises(ValueError):r.guard(job,freeze)
        with patch.object(r,'source_at',lambda cwd:{'dirty':False,'git_head':'different'}):
            with self.assertRaises(ValueError):r.guard(job,freeze)
    def test_original_binder_accepts_all52_recovery_raws_and_original_profile_path(self):
        # Reuse the actual frozen assessor interface fixture; its file bytes are synthetic.
        fixture=legacy.ControllerTests('test_actual_assessor_interface_requires_all_audited_unscaled_bases')
        fixture.root=self.root
        api,freeze,report=fixture.assessor_fixture()
        recovery=self.root/'recovery1'/'unscaled';recovery.mkdir(parents=True)
        for account in report['accounts'].values():
            old=Path(account['path']);new=recovery/old.name;shutil.copyfile(old,new)
            report['inputs'].pop(str(old));account['path']=str(new);report['inputs'][str(new)]=r.sha(new)
        self.assertEqual(len(legacy.b.validate_report(report,freeze,api)),52)
        legacy.b.validate_export(report,report['calibration_documents']['spot'],'spot','spot',freeze,api)
        for kind in api.BASE:
            for d in report['decisions'][kind].values():d.update(status='complete',eligible=False)
        self.assertEqual(len(legacy.b.validate_report(report,freeze,api)),52)
        for bad in (None,False,1,'true'):
            account=next(iter(report['accounts'].values()));account['monetary_audit']={'passed':bad}
            with self.assertRaises(ValueError):legacy.b.validate_report(report,freeze,api)
            account['monetary_audit']={'passed':True}
        freeze_path=self.root/'freeze.json';freeze_path.write_text(json.dumps(freeze))
        (self.root/'controller-parent-freeze.json').write_text(json.dumps(legacy.b.binding(freeze_path)))
        exports=self.root/'assessment-exports';exports.mkdir()
        export=exports/'spot.json';export.write_text(json.dumps(report['calibration_documents']['spot']))
        original_root=self.root/'original-root';(original_root/'assessment').mkdir(parents=True)
        production=original_root/'assessment'/'spot-calibration.json';production.write_bytes(export.read_bytes())
        report_path=self.root/'assessment.json'
        report['command']=[sys.executable,'-m','research.edge_assessment','--phase','calibration','--calibration-out-dir',str(exports),'--out',str(report_path)]
        report_path.write_text(json.dumps(report))
        registry=self.root/'original-registry.json';registry.write_text(json.dumps({'jobs':[dict(project_kind='spot',phase='risk',command=['synthetic','--risk-calibration',str(production)])]}))
        out=self.root/'actual-original-binding.json'
        argv=['--freeze',str(freeze_path),'--report',str(report_path),'--export',str(export),'--production-profile',str(production),
              '--out',str(out),'--kind','spot','--phase','risk','--export-label','spot','--registry',str(registry),'--registry-sha256',r.sha(registry)]
        with patch.object(legacy.b,'ART',self.root),patch.object(legacy.b.controller,'REGISTRY',registry),patch.object(legacy.b.controller,'REGISTRY_SHA',r.sha(registry)),patch.object(legacy.b.controller,'guard',lambda job,freeze:None),contextlib.redirect_stdout(io.StringIO()) as captured:
            legacy.b.main(argv)
        (self.root/'binder.log').write_text(captured.getvalue())
        binding=json.loads(out.read_bytes())
        self.assertEqual(binding['production_profile']['path'],str(production))
        self.assertEqual(len([x for x in binding['bound_files'] if str(recovery) in x['path']]),52)
        self.assertEqual(binding['registry_sha256'],r.sha(registry))
        (self.root/'synthetic-report.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':unittest.main(verbosity=2)
