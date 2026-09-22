"""Run from any directory: python3 path/to/restore_multipart.py [repository_root]."""
import hashlib
import json
import pathlib
import sys

here = pathlib.Path(__file__).resolve().parent
root = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else here.parents[1]
manifest = json.loads((here / 'multipart-manifest.json').read_text())
def verify(data, item):
    assert len(data) == item['size'], item
    assert hashlib.sha256(data).hexdigest() == item['sha256'], item
    assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() == item['git_blob'], item
for item in manifest['multipart']:
    chunks = []
    offset = 0
    for part in item['parts']:
        assert part['offset'] == offset
        data = (root / part['path']).read_bytes()
        verify(data, part)
        chunks.append(data)
        offset += len(data)
    data = b''.join(chunks)
    verify(data, item)
    for name in item['paths']:
        target = root / name
        if target.exists():
            verify(target.read_bytes(), item)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
for item in manifest['files']:
    verify((root / item['path']).read_bytes(), item)
print('Verified all', len(manifest['files']), 'source files against original bytes and Git blob IDs.')
