import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request
import urllib.error

SOURCE = 'ychenracing/pancakequant'
TARGET = 'geniusgrok/coinquant'
REFS = {
    'refs/heads/main': 'f94276236c7a8fa5e2551405822d575be5438a47',
    'refs/heads/evidence/native-btcusd-20260920': '230f9d60361bfec144d066c5684b5c3b96f996bb',
    'refs/heads/research/okx-linear-feasibility-20260921': 'c098178d7834b161185fa399950932bb607fee22',
    'refs/heads/research/on-demand-btc-20260920': 'f926dc50004b43841e2d12769750387dcb7c0e14',
    'refs/tags/1.0.0': 'c886b7c63c6455bd7c933269e32cd35a6fb3e09a',
}

def git(*args, cwd=None, data=None):
    return subprocess.check_output(['git', *args], cwd=cwd, input=data).decode().strip()

def api(path, payload=None, authenticated=True):
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request('https://api.github.com/' + path, data=data,
        headers={**({'Authorization': 'Bearer ' + os.environ['GH_TOKEN']} if authenticated else {}),
                 'Accept': 'application/vnd.github+json', 'User-Agent': 'coinquant-migration'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)

assert os.environ['GITHUB_REPOSITORY'] == TARGET
source_url = f'https://github.com/{SOURCE}.git'
target_url = f'https://github.com/{TARGET}.git'
actual = dict(line.split()[::-1] for line in git('ls-remote', '--heads', '--tags', source_url).splitlines() if not line.endswith('^{}'))
assert actual == REFS, ('Source refs changed', actual)
root = Path.cwd()
out = root / 'migration-evidence'
out.mkdir()
git('init', '--bare', 'source.git')
src = root / 'source.git'
git('fetch', '--no-tags', source_url, *[f'{sha}:{ref}' for ref, sha in REFS.items()], cwd=src)
git('fsck', '--full', '--no-reflogs', cwd=src)
# Original objects are already durably published in the target's ancestry.
# The connector created the two historical workflow-bearing branches.
carrier = '4830db6710ba343acded1ea5336274458998aac7'
tag_ref = 'refs/tags/1.0.0'
try:
    tag = api(f'repos/{TARGET}/git/ref/tags/1.0.0')
except urllib.error.HTTPError as exc:
    if exc.code != 404:
        raise
    tag = api(f'repos/{TARGET}/git/refs', {'ref': tag_ref, 'sha': REFS[tag_ref]})
assert tag['object']['sha'] == REFS[tag_ref]
releases = api(f'repos/{SOURCE}/releases?per_page=100', authenticated=False)
assert len(releases) == 1 and releases[0]['tag_name'] == '1.0.0'
original_release = releases[0]
assert not original_release['assets'], 'Release assets require separate file-backed transfer'
try:
    published_release = api(f'repos/{TARGET}/releases/tags/1.0.0')
except urllib.error.HTTPError as exc:
    if exc.code != 404:
        raise
    published_release = api(f'repos/{TARGET}/releases', {
        'tag_name': '1.0.0', 'target_commitish': REFS[tag_ref],
        'name': original_release['name'], 'body': original_release['body'],
        'draft': original_release['draft'], 'prerelease': original_release['prerelease']})
readback_release = api(f'repos/{TARGET}/releases/tags/1.0.0')
assert original_release['body'].encode() == readback_release['body'].encode()
assert original_release['name'] == readback_release['name']
(out / 'source-release.json').write_text(json.dumps(original_release, ensure_ascii=False, indent=2) + '\n')
(out / 'target-release.json').write_text(json.dumps(readback_release, ensure_ascii=False, indent=2) + '\n')
# Verify by a fresh independent clone of the published destination.
git('clone', '--bare', target_url, 'destination.git')
dst = root / 'destination.git'
git('fsck', '--full', '--no-reflogs', cwd=dst)
for ref, sha in REFS.items():
    if ref == 'refs/heads/main':
        subprocess.run(['git', 'merge-base', '--is-ancestor', sha, 'refs/heads/main'], cwd=dst, check=True)
    else:
        assert git('rev-parse', ref, cwd=dst) == sha
objects = sorted(set(git('rev-list', '--objects', '--no-object-names', *REFS.values(), cwd=src).splitlines()))
left = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=src, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
right = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=dst, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
manifest = []
for oid in objects:
    for process in (left, right):
        process.stdin.write((oid + '\n').encode())
        process.stdin.flush()
    headers = [process.stdout.readline() for process in (left, right)]
    assert headers[0] == headers[1]
    parsed_oid, kind, size_text = headers[0].decode().split()
    size = int(size_text)
    object_hash = hashlib.sha1(f'{kind} {size}\0'.encode())
    content_hash = hashlib.sha256()
    remaining = size
    while remaining:
        count = min(262144, remaining)
        a = left.stdout.read(count)
        b = right.stdout.read(count)
        assert len(a) == count and a == b, ('Object content mismatch', oid)
        object_hash.update(a)
        content_hash.update(a)
        remaining -= count
    assert left.stdout.read(1) == right.stdout.read(1) == b'\n'
    assert object_hash.hexdigest() == oid == parsed_oid
    if kind == 'blob' and size < 1024:
        assert not (size and a.startswith(b'version https://git-lfs.github.com/spec/v1')), ('LFS payload requires transfer', oid)
    manifest.append({'oid': oid, 'type': kind, 'length': size, 'sha256': content_hash.hexdigest()})
for process in (left, right):
    process.stdin.close()
    assert process.wait(timeout=20) == 0
(out / 'objects.json').write_text(json.dumps(manifest, indent=2) + '\n')
summary = {'source': SOURCE, 'target': TARGET, 'source_refs': REFS, 'carrier_commit': carrier,
    'source_main_tree': git('rev-parse', REFS['refs/heads/main'] + '^{tree}', cwd=src),
    'objects_verified': len(manifest), 'bytes_verified': sum(row['length'] for row in manifest),
    'release_notes_byte_equal': True, 'release_url': readback_release['html_url'],
    'release_notes_sha256': hashlib.sha256(original_release['body'].encode()).hexdigest(),
    'all_original_objects_byte_equal': True, 'all_original_object_ids_verified': True,
    'verification': 'Independent destination clone; every original reachable object compared byte-for-byte, SHA-256 and Git SHA-1 verified',
    'next_step': 'Publish the original source tree to target main through a normal fast-forward commit, removing bootstrap files'}
(out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
git('bundle', 'create', str(out / 'pancakequant-original.bundle'), *REFS.keys(), cwd=src)
git('bundle', 'verify', str(out / 'pancakequant-original.bundle'), cwd=src)
bundle = out / 'pancakequant-original.bundle'
with bundle.open('rb') as file:
    digest = hashlib.file_digest(file, 'sha256').hexdigest()
(out / 'bundle.sha256').write_text(digest + '  ' + bundle.name + '\n')
print('MIGRATION_VERIFIED ' + json.dumps(summary, sort_keys=True))
