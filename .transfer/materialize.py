"""Reconstruct an authorized source packet, verify it, and save it on its research ref.

No exchange credentials, financial writes, secret extraction, or force pushes.
The transport-only workflow is left byte-identical for a connector cleanup commit.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = Path.cwd()
BRANCH = 'research/on-demand-btc-20260920'
REPO = 'ychenracing/pancakequant'
STAGE = ROOT / '.transfer'
WORKFLOW = '.github/workflows/check.yml'

def run(*args):
    return subprocess.check_output(args, text=True).strip()

def digest(data):
    return hashlib.sha256(data).hexdigest()

def oid(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()

def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')

def remote_head():
    output = run('git', 'ls-remote', 'origin', f'refs/heads/{BRANCH}')
    if not output:
        raise RuntimeError('research ref missing')
    return output.split()[0]

def public_probes():
    """Bounded source availability checks; NOT a historical backtest/data harvest."""
    queries = {
        'instrument': ('public/instruments', {'instType':'SWAP','instId':'BTC-USDT-SWAP'}),
        'trade_2020_sample': ('market/history-candles', {'instId':'BTC-USDT-SWAP','bar':'1m','after':'1577836860001','limit':'2'}),
        'mark_2020_sample': ('market/history-mark-price-candles', {'instId':'BTC-USDT-SWAP','bar':'1m','after':'1577836860001','limit':'2'}),
        'funding_2020_sample': ('public/funding-rate-history', {'instId':'BTC-USDT-SWAP','after':'1577923200001','limit':'2'}),
    }
    result = {'qualification':'AVAILABILITY_ONLY_NOT_CONTINUITY', 'requests':{}}
    for name, (path, params) in queries.items():
        url = 'https://www.okx.com/api/v5/' + path + '?' + urllib.parse.urlencode(params)
        record = {'url':url, 'retrieved_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
        try:
            req = urllib.request.Request(url, headers={'User-Agent':'pancakequant-source-check'})
            with urllib.request.urlopen(req, timeout=8) as response:
                raw = response.read(262145)
                if len(raw) > 262144:
                    raise ValueError('bounded response exceeded')
                record['http_status'] = response.status
                record['response'] = json.loads(raw)
            record['status'] = 'RESPONSE_OBTAINED'
        except urllib.error.HTTPError as exc:
            record.update(status='HTTP_FAILURE', http_status=exc.code)
        except Exception as exc:
            record.update(status='UNAVAILABLE', error_type=type(exc).__name__)
        save(ROOT / 'evidence' / 'public-probes' / (name + '.json'), record)
        response = record.get('response', {})
        result['requests'][name] = {'status':record['status'], 'http_status':record.get('http_status'),
            'api_code':response.get('code'), 'rows':len(response.get('data', []))}
    save(ROOT / 'evidence' / 'public-probes' / 'summary.json', result)
    return result

assert run('git','branch','--show-current') == BRANCH, 'wrong ref'
base = run('git','rev-parse','HEAD')
assert remote_head() == base, 'concurrent remote update; refusing rewrite'
manifest = json.loads((STAGE / 'manifest.json').read_text())
packet = io.BytesIO()
offset = 0
for index, part in enumerate(manifest['parts']):
    assert index == part['index'] and offset == part['offset'], 'part ordering/offset'
    data = (STAGE / part['path']).read_bytes()
    assert len(data) == part['length'] and digest(data) == part['sha256'], 'part bytes'
    assert oid(data) == part['git_blob_oid'], 'part Git object'
    packet.write(data)
    offset += len(data)
blob = packet.getvalue()
assert offset == manifest['archive_length'] and digest(blob) == manifest['archive_sha256'], 'archive identity'
expected = {item['path']:item for item in manifest['files']}
assert len(expected) == len(manifest['files']), 'duplicate paths'
with tarfile.open(fileobj=io.BytesIO(blob), mode='r:xz') as archive:
    members = archive.getmembers()
    assert {m.name for m in members} == set(expected), 'archive file set'
    content = {}
    for member in members:
        assert member.isfile() and not member.issym() and not member.islnk(), 'unsupported archive member'
        path = Path(member.name)
        assert not path.is_absolute() and '..' not in path.parts and '.git' not in path.parts
        data = archive.extractfile(member).read()
        item = expected[member.name]
        assert len(data) == item['bytes'] and digest(data) == item['sha256'] and oid(data) == item['git_blob_oid']
        content[member.name] = data
workflow_bytes = (ROOT / WORKFLOW).read_bytes()
for path in list(ROOT.iterdir()):
    if path.name in {'.git', '.transfer', '.github'}:
        continue
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()
# The bootstrap commit is a minimal tree. No unknown workflow is preserved.
assert sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/'.github').rglob('*') if p.is_file()) == [WORKFLOW]
for path, data in content.items():
    if path == WORKFLOW:
        continue
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
assert (ROOT / WORKFLOW).read_bytes() == workflow_bytes
for path, data in content.items():
    if path != WORKFLOW:
        assert (ROOT / path).read_bytes() == data
save(ROOT/'evidence'/'source-packet-manifest.json', manifest)
probes = public_probes()
compile_result = subprocess.run(['python','-m','compileall','-q','pancakequant','research','tests'], capture_output=True, text=True)
tests = subprocess.run(['python','-m','unittest','discover','-s','tests','-v'], capture_output=True, text=True)
(ROOT/'evidence'/'hosted-safety-tests.txt').write_text(tests.stdout + tests.stderr)
save(ROOT/'evidence'/'hosted-validation.json', {'python':run('python','--version'),
    'compile_exit_code':compile_result.returncode,'tests_exit_code':tests.returncode,
    'exchange_authentication':'NOT_ATTEMPTED','economic_measurement':'NOT_RUN',
    'workflow_cleanup_pending':True, 'packet_sha256':manifest['archive_sha256']})
# Even a failing check is saved honestly; it cannot publish this candidate to main.
run('git','config','user.name','pancakequant research')
run('git','config','user.email','research@users.noreply.github.com')
run('git','add','-A')
assert run('git','diff','--cached','--name-only','--',WORKFLOW) == '', 'workflow must remain unchanged'
assert remote_head() == base, 'concurrent remote update before source save'
run('git','commit','-m','Replace daemon with on-demand BTC research implementation; preserve qualification gaps')
source_commit = run('git','rev-parse','HEAD')
run('git','push','origin',f'HEAD:refs/heads/{BRANCH}')
assert remote_head() == source_commit, 'source ref not persisted'
# Fresh server archive is an independent byte readback, not a local Git object check.
url = f'https://codeload.github.com/{REPO}/zip/{source_commit}'
with urllib.request.urlopen(url, timeout=30) as response:
    remote_zip = response.read(5000001)
assert len(remote_zip) <= 5000000, 'remote readback bound'
tracked = run('git','ls-files','-z').split('\0')
tracked = [p for p in tracked if p]
identities = []
with zipfile.ZipFile(io.BytesIO(remote_zip)) as archive:
    prefix = archive.namelist()[0].split('/')[0] + '/'
    actual_paths = {name[len(prefix):] for name in archive.namelist() if not name.endswith('/')}
    assert actual_paths == set(tracked), 'remote tree path mismatch'
    for path in sorted(tracked):
        actual = archive.read(prefix+path)
        local = (ROOT/path).read_bytes()
        assert actual == local, f'byte mismatch: {path}'
        expected_oid = run('git','rev-parse',f'{source_commit}:{path}')
        assert oid(actual) == expected_oid, f'Git object mismatch: {path}'
        identities.append({'path':path,'bytes':len(actual),'sha256':digest(actual),'git_blob_oid':expected_oid})
receipt = {'status':'BYTE_IDENTICAL_REMOTE_READBACK', 'verified_commit':source_commit,
    'verified_tree':run('git','rev-parse',f'{source_commit}^{{tree}}'), 'repository':REPO,'branch':BRANCH,
    'source_packet_sha256':manifest['archive_sha256'], 'file_count':len(identities),
    'bytes':sum(x['bytes'] for x in identities), 'files':identities,
    'verification':'Fresh pinned codeload archive; exact path set, all bytes, SHA256 and Git blob OIDs',
    'deferred_source_path':WORKFLOW,'deferred_reason':'Connector must replace temporary transport workflow with final read-only CI',
    'compile_exit_code':compile_result.returncode,'tests_exit_code':tests.returncode,'public_probes':probes}
save(ROOT/'evidence'/'remote-source-readback.json',receipt)
run('git','add','evidence/remote-source-readback.json')
assert remote_head() == source_commit, 'concurrent remote update before receipt save'
run('git','commit','-m','Record full remote byte and Git object verification of source checkpoint')
receipt_commit = run('git','rev-parse','HEAD')
run('git','push','origin',f'HEAD:refs/heads/{BRANCH}')
assert remote_head() == receipt_commit
raw_url = f'https://raw.githubusercontent.com/{REPO}/{receipt_commit}/evidence/remote-source-readback.json'
with urllib.request.urlopen(raw_url, timeout=20) as response:
    actual_receipt = response.read(2000001)
expected_receipt = (ROOT/'evidence/remote-source-readback.json').read_bytes()
assert actual_receipt == expected_receipt
assert oid(actual_receipt) == run('git','rev-parse',f'{receipt_commit}:evidence/remote-source-readback.json')
print('PRESERVATION_RECEIPT='+json.dumps({'source_commit':source_commit,'receipt_commit':receipt_commit,
    'source_tree':receipt['verified_tree'],'files_verified':len(identities),'bytes_verified':receipt['bytes'],
    'packet_sha256':manifest['archive_sha256'],'receipt_sha256':digest(actual_receipt),
    'compile_exit_code':compile_result.returncode,'tests_exit_code':tests.returncode,
    'public_probes':probes,'main_changed':False}, sort_keys=True))
if compile_result.returncode or tests.returncode:
    raise SystemExit('Source and failing evidence saved; targeted validation failed')
