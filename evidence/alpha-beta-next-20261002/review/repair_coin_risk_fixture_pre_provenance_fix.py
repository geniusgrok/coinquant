"""Temporary-only repair checks; no real controller launch, account/cache or State."""
import copy
import gzip
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

REVIEW = Path('/workspace/btc-alpha-beta-next/review')
spec = importlib.util.spec_from_file_location('repair', REVIEW/'repair_coin_risk_incumbent.py')
h = importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
sys.path.insert(0, '/workspace/btc-alpha-beta-analysis/spotquant')
from research import alpha_assessment as a
passed = []


def expect_error(call, message=None):
    try:
        call()
    except (ValueError, FileExistsError, EOFError, gzip.BadGzipFile) as exc:
        if message:
            assert message in str(exc), str(exc)
    else:
        raise AssertionError('expected refusal')


def gz(path, body):
    with gzip.open(path, 'wt') as f:json.dump(body,f)


def setup(root):
    starts = [1577836800000+i*86400000 for i in range(795)]
    env = {k: 'b'*64 for k in ('spec_sha256','protocol_sha256','fx_sha256','primary_sha256')}
    env['starts'] = starts
    profiles = {name:{'scale':'.8' if name=='compression-breakout' else '1'} for name in h.NAMES}
    h.write(root/'registered-calibration.json', {'profiles':profiles})
    source = {'git_head':'a'*40,'dirty':False,'python_sources_sha256':'a'*64}
    meta = dict(source=source,measured_source=source,initial_cny='10000',start_offset_ms=0,
        spec_sha256=env['spec_sha256'],protocol_sha256=env['protocol_sha256'],fx_sha256=env['fx_sha256'],
        schedule_sha256=env['primary_sha256'],original_schedule_sha256=env['primary_sha256'],
        actual_starts_sha256=a.checksum(starts),crowding_source='not used by alpha/beta mechanisms',
        crowding_sha256=a.checksum(None),market_identity={'fixture':True},loaded_minute_files={},loaded_print_files={},
        original_meter_protocol_sha256='c'*64,candidates={n:[] if n=='incumbent' else [n] for n in h.NAMES},
        risk_calibration_sha256=h.sha(root/'registered-calibration.json'),risk_profiles=profiles)
    row = dict(initial_cny='10000',final_cny='11000',final_usdt='1500',cagr=.1,mdd='.1',mdd_close='.09',
        audit={'passed':True},fees='0',funding='0',position='0',final_mark='100',trades=[],funding_ledger=[],
        daily=[],daily_cny=[],known_path=True,unknown_from=None,hindsight_bounded=False,bounded_minutes=[],
        mdd_envelope_at=starts[0],mdd_close_at=starts[0],funnel={},failure=None,feature_coverage={},execution_unresolved=0,
        complete=True,opportunity_ledger=[{'event':'fixture','at_ms':starts[0]}],
        sessions=[dict(start_ms=t,cleanup='verified',execution_unresolved=False,cycles=10,observations={}) for t in starts])
    original = {'inputs':meta,'conditions':{'conversion_each_way':'.001','terminal_funding_exclusive_ms':a.END_MS},
                'results':{n:{'base':copy.deepcopy(row)} for n in h.NAMES},'selection':{'fixture':'unchanged'}}
    old = copy.deepcopy(original);old['inputs']['risk_calibration_sha256']=None;old['inputs']['risk_profiles']={}
    new = copy.deepcopy(original);new['results']={'incumbent':{'base':copy.deepcopy(row)}}
    new['inputs']['candidates']={'incumbent':[]};new['inputs']['risk_profiles']={'incumbent':profiles['incumbent']}
    original['results']['incumbent']['base']['sessions'][31]['cycles'] += 1
    gz(root/'perp-singletons-retry1.json.gz',old);gz(root/'risk-perp.json.gz',original);gz(root/h.NEW.name,new)
    h.write(root/'risk-perp.command.json',{'fixture':'original receipt'});(root/'risk-perp.run.log').write_text('fixture original log')
    h.write(root/'risk-perp-incumbent-retry1.command.json',{'fixture':'new actual receipt'})
    pin={p:h.sha(p) for p in (root/'registered-calibration.json',root/'risk-perp.json.gz',root/'risk-perp.command.json')}
    bound={**pin,Path(h.__file__):h.sha(Path(h.__file__)),root/'risk-perp.run.log':h.sha(root/'risk-perp.run.log'),root/h.NEW.name:h.sha(root/h.NEW.name)}
    consumed={'valid':True,'rejections':[],'raw_bundle_sha256':h.sha(root/h.NEW.name),'evidence_sha256':a.evidence_fingerprints(row,'perp')}
    return env,original,new,pin,bound,consumed


def paths(root):
    return patch.multiple(h,OUT=root,NEW=root/h.NEW.name,PROJECTED=root/h.PROJECTED.name,
        PROOF=root/h.PROOF.name,MANIFEST=root/h.MANIFEST.name,FINAL=root/h.FINAL.name,INTENT=root/h.INTENT.name)


for alteration in ('none','operating','incomplete','source','profile','consume'):
    with tempfile.TemporaryDirectory(prefix='coin-risk-repair-fixture-') as tmp:
        root=Path(tmp);env,original,new,pin,bound,consumed=setup(root)
        if alteration=='operating':new['results']['incumbent']['base']['sessions'][31]['cycles']+=1
        if alteration=='incomplete':new['results']['incumbent']['base']['sessions'].pop()
        if alteration=='source':
            new['inputs']['source']['python_sources_sha256']='d'*64
        if alteration=='profile':new['inputs']['risk_profiles']['incumbent']={'scale':'.9'}
        if alteration=='consume':consumed['valid']=False
        gz(root/h.NEW.name,new);bound[root/h.NEW.name]=h.sha(root/h.NEW.name);consumed['raw_bundle_sha256']=h.sha(root/h.NEW.name)
        with paths(root),patch.object(h,'PINNED',pin),patch.object(h,'sources',lambda:None),patch.object(a,'verify_source',lambda *_:None):
            if alteration!='none':
                expect_error(lambda:h.derive(a,env,bound,consumed))
                assert not h.PROJECTED.exists() and not h.PROOF.exists() and not h.MANIFEST.exists()
            else:
                h.derive(a,env,bound,consumed)
                projection=h.read(h.PROJECTED);proof=h.read(h.PROOF);manifest=h.read(h.MANIFEST)
                assert projection['results']=={n:original['results'][n] for n in h.NAMES[1:]}
                assert projection['inputs']['risk_profiles']==original['inputs']['risk_profiles']
                assert {k:v for k,v in projection['inputs'].items() if k!='candidates'}=={k:v for k,v in original['inputs'].items() if k!='candidates'}
                assert projection['conditions']==original['conditions'] and projection['selection']==original['selection']
                assert set(projection['inputs']['candidates'])==set(h.NAMES[1:])
                assert proof['all_six_exact'] and proof['all_retained_rows_exact'] and proof['immutable99_actual_consume_valid']
                assert manifest['format']=='alpha-account-manifest-v1' and len(manifest['files'])==2
                assert all(h.sha(root/f['path'])==f['sha256'] for f in manifest['files'])
                before={p:h.sha(p) for p in (h.PROJECTED,h.PROOF,h.MANIFEST)}
                expect_error(lambda:h.derive(a,env,bound,consumed))
                assert all(h.sha(p)==digest for p,digest in before.items())
        passed.append('real99_fingerprints_projection_'+alteration)

with tempfile.TemporaryDirectory(prefix='coin-risk-repair-fixture-') as tmp:
    root=Path(tmp);p=root/'sample.json'
    h.write(p,{'a':1});expect_error(lambda:h.write(p,{'a':2}));assert h.read(p)=={'a':1}
    p.write_text('{"a":1,"a":2}');expect_error(lambda:h.read(p),'Duplicate')
    p.write_text('{"a":NaN}');expect_error(lambda:h.read(p),'Nonfinite')
    g=root/'crc.json.gz';gz(g,{'a':1});g.write_bytes(g.read_bytes()[:-4]);expect_error(lambda:h.read(g))
    link=root/'link.json';link.symlink_to(p);expect_error(lambda:h.read(link),'Symlink')
    expect_error(lambda:h.bind({p:'a'*64},{p:'b'*64}),'Bound identity')
    passed += ['exclusive_write','duplicate_keys','nonfinite_json','gzip_crc','symlink_refusal','bound_hash_cannot_be_replaced']

for argv in ('python -m research.alpha_perp --out fixture', 'python run_registered_followthrough_public_vault.py',
             'python -m research.alpha_spot --out fixture'):
    with patch.object(h.subprocess,'check_output',return_value='999999 '+argv+'\n'):
        expect_error(h.no_producer)
    passed.append('active_process_refusal_'+argv.split()[1])

with tempfile.TemporaryDirectory(prefix='coin-risk-repair-fixture-') as tmp:
    root=Path(tmp);calls=[]
    finalcmd=['python','-u','-m','research.alpha_assessment','--risk-perp',str(root/'risk-perp.json.gz'),
              '--out',str(root/'registered-final.json'),'--csv',str(root/'registered-final.csv'),
              '--markdown',str(root/'registered-final.md'),'--calibration',str(root/'registered-calibration.json'),
              '--risk-spot-calibration',str(root/'spot-project-calibration.json'),'--final']
    oldcmd={'command':finalcmd}
    riskcmd={'cwd':str(h.COIN),'source_head':h.SOURCES[h.COIN][0],'command':['synthetic-python']}
    def blocked_restore(_):
        calls.append('restore')
        assert h.INTENT.exists() and h.read(h.INTENT)['automatic_second_attempt'] is False
        raise ValueError('fixture stop before cache or producer')
    fake_spec=SimpleNamespace(loader=SimpleNamespace(exec_module=lambda _:None))
    with paths(root),patch.object(h,'PINNED',{}),patch.object(h,'WAIT_PIDS',()),patch.object(h,'sources',lambda:None),\
         patch.object(h,'no_producer',lambda:None),patch.object(h,'closed_inventory',return_value=(oldcmd,{})),\
         patch.object(h,'receipt',return_value=(riskcmd,None)),patch.object(h,'public_catalog',return_value={'fixture':True}),patch.object(h.importlib.util,'spec_from_file_location',return_value=fake_spec),\
         patch.object(h.importlib.util,'module_from_spec',return_value=SimpleNamespace(restore=blocked_restore)),\
         patch.object(h,'run',side_effect=AssertionError('producer forbidden in fixture')):
        expect_error(h.main,'fixture stop')
        assert calls==['restore']
        intent_sha=h.sha(h.INTENT)
        expect_error(h.main,'One registered attempt')
        assert calls==['restore'] and h.sha(h.INTENT)==intent_sha
        intent=h.read(h.INTENT)
        assert '--candidate' in intent['retry_command'] and intent['retry_command'][intent['retry_command'].index('--candidate')+1]=='incumbent'
        assert intent['retry_command'].count('--out')==1 and '--initial-cny' not in intent['retry_command']
        assert intent['TMPDIR']==str(root/'tmp')
    passed += ['intent_before_restore_or_producer','one_attempt_refuses_relaunch','exact_incumbent_argv_and_tmpdir']

with patch.object(h.subprocess,'check_output',return_value='999998 bash -lc python '+h.__file__+' --execute\n'):
    h.no_producer()
passed.append('parent_shell_is_not_a_second_controller')

with tempfile.TemporaryDirectory(prefix='coin-risk-repair-fixture-') as tmp:
    root=Path(tmp);name='BTCUSDT-aggTrades-2020-03-29.zip'
    gz(root/'risk-perp.json.gz',{'inputs':{'loaded_print_files':{name:'a'*64}}})
    folder=root/'public-print-vault/records';folder.mkdir(parents=True)
    record=folder/(name+'.json');h.write(record,{'name':name,'sha256':'a'*64})
    with patch.object(h,'OUT',root):
        assert h.public_catalog()['matched_records']==1
        record.write_text(json.dumps({'name':name,'sha256':'b'*64}))
        expect_error(h.public_catalog,'Vault catalog')
    passed += ['catalog_matches_original_consumed_hash','catalog_conflict_blocks_before_restore']

print(json.dumps({'temporary_only':True,'real_controller_launches':0,'real_account_cache_state_operations':0,
                  'immutable99_evidence_fingerprints_used':True,'passed':passed,'count':len(passed)},indent=2))
