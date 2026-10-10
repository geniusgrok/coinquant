"""Package completed public repair evidence; --check performs read-only readiness checks."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile
import sys

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
NAME='coinquant-2.0.1-repair-evidence-20261010'
EXCLUDED={'state','selected-prints','selected-prints-cache','private-parsed-prints-cache','__pycache__'}
HEADS={'control_2_0_0':'162ee7138952925ffafbc9b68be7c754c0c0a6c3',
       'margin-only':'06206ac0c5383fb009df8bac20601cd9e2d9b004',
       'book-v2-only':'37bfc8a833d1ff3c0992842ce363758a47b1d06f',
       'combined-v2':'3561728dab351d269b19b107fb4fbabb2ac1f674',
       'combined-v3':'230a61daade55d7d80de56f61aae24e660fb3a40'}
CHART_FILES={f'repair-{kind}-daily.{ext}' for kind in ('equity','drawdown') for ext in ('png','svg')}
REQUIRED_ROOT_FILES={'FINAL_RESULTS.json','FINAL_RESULTS.md','RESULTS.json','RESULTS.md',
    'repair_results.py','plot_repair_results.py','repair_results_v2.py','plot_repair_results_v2.py',
    'PROTOCOL.md','BOOK_GUARD_AMENDMENT_V2.md','FROZEN_BUFFER_AMENDMENT_V3.md','register_case_v3.py',
    'combined_execution_attribution.py','combined-execution-attribution.json','combined-execution-attribution.md',
    'book_execution_attribution.py','book-execution-attribution.json','book-execution-attribution.md',
    'collateral_probe.py','collateral_probe.json','buffer_gap_probe.py',
    'buffer-gap-baseline-probe.json','buffer-gap-fixed-probe.json','buffer-fix-evidence-files.json',
    'PUBLIC_SOURCE_VERIFICATION_V3.json','RELEASE_SOURCE_VERIFICATION.json'}


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def require(condition, reason):
    if not condition:raise ValueError(reason)


def read(path):
    path=Path(path)
    with (gzip.open(path,'rt') if path.suffix=='.gz' else path.open()) as f:return json.load(f)


def checked_artifact(ref):
    path=Path(ref['path'])
    require(path.is_file() and not path.is_symlink() and path.stat().st_size==ref['bytes']
            and sha(path)==ref['sha256'],'artifact changed or missing: '+str(path))
    return path


def complete_results(path, final):
    result=read(path)
    expected=dict(HEADS)
    if not final:expected.pop('combined-v3')
    require(result['version']==('coinquant-repair-results-v2' if final else 'coinquant-repair-results-v1')
            and result['all_three_registered_repairs_present'] is True
            and (not final or result['all_four_registered_repairs_present'] is True)
            and set(result['cases'])==set(expected)-{'control_2_0_0'}
            and len(result['accepted_full_window_cases'])==len(expected)
            and set(result['accepted_full_window_cases'])==set(expected)
            and result['baseline_calibration']['passed'] is True,
            'incomplete or mismatched result arms: '+str(path))
    require(result['period']['days']==2454 and result['qualification']['offline_simulation'] is True
            and result['qualification']['native_execution_verified'] is False,
            'unexpected final result qualification')
    require(checked_artifact(result['summarizer']).resolve()
            == (ROOT/('repair_results_v2.py' if final else 'repair_results.py')).resolve(),
            'result names another summarizer')
    arms={'control_2_0_0':result['control_2_0_0'],**result['cases']}
    for name,arm in arms.items():
        receipt=read(checked_artifact(arm['receipt']))
        require(arm['head']==receipt['source']['git_head']==expected[name]
                and receipt['complete'] is True and receipt['original_window_complete'] is True
                and receipt['failure'] is None and receipt['session_count']==795
                and receipt['scope']=={'kind':'original-full','planned_sessions':795}
                and receipt['no_live_account'] is True and receipt['native_verified'] is False,
                'full795 receipt required for '+name)
        require(arm['cleanup']['verified_sessions']==795
                and arm['cleanup']['terminal_pending_intents']==0
                and arm['cleanup']['execution_unresolved_sessions']==0
                and arm['path_evidence']['passed'] is True
                and arm['path_evidence']['rolling_digest_recomputed'] is True,
                'incomplete audited cleanup/path evidence for '+name)
        checked_artifact(arm['specification'])
        if name=='control_2_0_0':continue
        for key in ('registration','auditor','protocol'):checked_artifact(arm[key])
        audit=read(checked_artifact(arm['audit']))
        require(audit['passed'] is True and audit['full795'] is True
                and audit['main']['receipt_sha256']==arms['control_2_0_0']['receipt']['sha256']
                and audit['candidate']['receipt_sha256']==arm['receipt']['sha256']
                and audit['main']['source_inputs']['head']==HEADS['control_2_0_0']
                and audit['candidate']['source_inputs']['head']==expected[name]
                and all(audit[side]['sessions']==795 and audit[side]['financial']['passed'] is True
                        and audit[side]['path_audit']['passed'] is True for side in ('main','candidate')),
                'full independent control/candidate audit required for '+name)
        checked_artifact(audit['detail'])
    return result,arms,expected


def complete_figures(directory, results_path, arms, expected, final):
    validation=read(directory/'repair-charts-validation.json')
    provenance=validation['provenance']
    require(validation['passed'] is True
            and provenance['version']==('coinquant-repair-daily-charts-v2' if final else 'coinquant-repair-daily-charts-v1')
            and provenance['heads']==expected and set(provenance['receipts'])==set(expected)
            and provenance['daily_closes_per_arm']==2454,
            'incomplete chart manifest: '+str(directory))
    require(checked_artifact(provenance['results']).resolve()==results_path.resolve(),
            'charts refer to another results artifact')
    require(checked_artifact(provenance['plotter']).resolve()
            == (ROOT/('plot_repair_results_v2.py' if final else 'plot_repair_results.py')).resolve(),
            'charts refer to another plotter')
    for name,ref in provenance['receipts'].items():
        checked_artifact(ref)
        require(all(ref[key]==arms[name]['receipt'][key] for key in ('bytes','sha256')),
                'charts refer to another receipt: '+name)
    refs=validation['artifacts']
    require(len(refs)==len(CHART_FILES) and {Path(ref['path']).name for ref in refs}==CHART_FILES,
            'both equity/drawdown PNG/SVG charts are required')
    for ref in refs:
        require(checked_artifact(ref).resolve()==(directory/Path(ref['path']).name).resolve(),
                'chart manifest member is outside its directory')


def public_file(path):
    relative=path.relative_to(BASE)
    name=path.name.lower()
    database=name.endswith(('.sqlite','.sqlite3','.db','.sqlite-wal','.sqlite-shm',
                            '.sqlite3-wal','.sqlite3-shm','.db-wal','.db-shm','-wal','-shm'))
    return (path.is_file() and not path.is_symlink() and not database
            and not any(part in EXCLUDED or part.startswith('.') for part in relative.parts))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='Check readiness without creating an archive or receipt')
    args=parser.parse_args()
    results,final_arms,final_heads=complete_results(ROOT/'FINAL_RESULTS.json',True)
    _,old_arms,old_heads=complete_results(ROOT/'RESULTS.json',False)
    complete_figures(ROOT/'figures-v3',ROOT/'FINAL_RESULTS.json',final_arms,final_heads,True)
    complete_figures(ROOT/'figures',ROOT/'RESULTS.json',old_arms,old_heads,False)
    release=json.loads((ROOT/'RELEASE_SOURCE_VERIFICATION.json').read_text())
    assert results['all_three_registered_repairs_present'] is True
    assert results['all_four_registered_repairs_present'] is True
    assert set(results['cases'])=={'margin-only','book-v2-only','combined-v2','combined-v3'}
    assert release['passed'] is True and release['measured_head']=='230a61daade55d7d80de56f61aae24e660fb3a40'
    paths=[]
    for p in ROOT.iterdir():
        if p.is_file() and p.suffix in {'.py','.md','.json','.jsonl','.log','.patch'} and p.name not in {
                'TASK_PROGRESS.json','RELEASE_NOTES_2.0.1.md','PUBLIC_ARCHIVE.json','PRIVATE_ARCHIVE.json'}:
            paths.append(p)
    for case in ['book-only','margin-only','combined','book-v2-only','combined-v2','margin-only-rerun-001','margin-only-rerun-002','combined-v3']:
        for p in (ROOT/'replays'/case).rglob('*'):
            relative=p.relative_to(ROOT/'replays'/case)
            if any(part in EXCLUDED or part.startswith('.') for part in relative.parts):continue
            if p.is_file() and not p.is_symlink() and p.suffix not in {'.pyc','.sqlite','.zip','.bin'}:paths.append(p)
    paths += [p for p in (ROOT/'figures').iterdir() if p.is_file()]
    paths += [p for p in (ROOT/'figures-v3').iterdir() if p.is_file()]
    paths += [p for p in (BASE/'remeasure-inputs').iterdir()
              if p.is_file() and not p.name.startswith('.') and p.suffix in {'.py','.json','.jsonl','.log'}]
    paths += [p for p in (BASE/'coinquant-remeasure-tooling-v2').rglob('*')
              if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
    paths += [p for p in (BASE/'remeasure-evidence/evidence/2.0.0-remeasure-20261009').iterdir()
              if p.is_file() and p.suffix in {'.py','.json','.md','.jsonl','.log'}]
    paths=sorted({p for p in paths if public_file(p)},key=lambda p:str(p.relative_to(BASE)))
    require({ROOT/name for name in REQUIRED_ROOT_FILES}<=set(paths),
            'required final, v3 or execution-attribution evidence is missing from public selection')
    for name,arm in final_arms.items():
        if name=='control_2_0_0':continue  # Original control is in the separate frozen baseline asset.
        require({Path(arm[key]['path']) for key in ('receipt','registration','specification','audit')}<=set(paths),
                'measured repair evidence is not selected for '+name)
    if args.check:
        print(json.dumps(dict(ready=True,final_arms=len(final_arms),original_2x2_arms=len(old_arms),
            chart_files_per_set=len(CHART_FILES),selected_files=len(paths),
            selected_bytes=sum(p.stat().st_size for p in paths),archive_written=False)),flush=True)
        return
    manifest=dict(version='coinquant-repair-public-evidence-v1',source=release,
        baseline_asset=dict(name='coinquant-2.0.0-remeasurement-evidence-20261009.tar.xz',bytes=67465568,
                            sha256='3b2ebd1078c373c8b09fd152b82bc70c6722b77853909b726633d5b4498f73d3'),
        excluded='Account state directories, credentials, raw market ZIP vaults, parsed binary caches and git worktrees.',
        files=[dict(path=str(p.relative_to(BASE)),bytes=p.stat().st_size,sha256=sha(p)) for p in paths])
    encoded=(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n').encode()
    destination=BASE/(NAME+'.tar.xz')
    assert not destination.exists(),'preserve existing archive'
    with tarfile.open(destination,'w:xz',preset=1) as archive:
        item=tarfile.TarInfo(NAME+'/PUBLIC_FILE_MANIFEST.json');item.size=len(encoded);item.mode=0o644
        archive.addfile(item,io.BytesIO(encoded))
        for path,record in zip(paths,manifest['files']):
            item=tarfile.TarInfo(NAME+'/'+record['path']);item.size=record['bytes'];item.mode=0o644
            with path.open('rb') as data:archive.addfile(item,data)
    # Compare every extracted member to the manifest without extracting a second copy.
    with tarfile.open(destination,'r:xz') as archive:
        members=archive.getmembers()
        assert len(members)==len(paths)+1 and all(m.isfile() for m in members)
        assert archive.extractfile(members[0]).read()==encoded
        for item,record in zip(members[1:],manifest['files']):
            assert item.name==NAME+'/'+record['path'] and item.size==record['bytes']
            with archive.extractfile(item) as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
            assert actual==record['sha256'],item.name
    result=dict(name=destination.name,path=str(destination),bytes=destination.stat().st_size,
        sha256=sha(destination),members=len(paths)+1,manifest_sha256=hashlib.sha256(encoded).hexdigest(),
        file_readback_verified=True,source=release['release_head'])
    with (ROOT/'PUBLIC_ARCHIVE.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,TypeError,AssertionError) as exc:
        print('Public evidence is not ready: '+str(exc),file=sys.stderr)
        raise SystemExit(1)
