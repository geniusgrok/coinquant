"""Verify final Git blobs, archive order, and every development account byte."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parent


def check(raw,record):
    assert len(raw)==record['bytes']
    assert hashlib.sha256(raw).hexdigest()==record['sha256']
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==record['git_blob_sha1']


def restore(destination):
    dest=Path(destination)
    dest.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((ROOT/'ORIGINALS.json').read_text())
    archive=bytearray()
    for part in manifest['parts']:
        assert part['offset']==len(archive)
        raw=(ROOT/part['path']).read_bytes()
        check(raw,part)
        archive.extend(raw)
    check(archive,manifest['archive'])
    expected={row['path']:row for row in manifest['members']}
    seen=set()
    with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as source:
        for item in source:
            assert item.isfile() and item.name in expected and item.name not in seen
            assert not item.name.startswith('/') and '..' not in Path(item.name).parts
            raw=source.extractfile(item).read()
            check(raw,expected[item.name])
            target=dest/item.name
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(raw)
            seen.add(item.name)
    assert seen==set(expected)
    print(json.dumps(dict(parts=len(manifest['parts']),originals=len(seen),
                          archive_sha256=manifest['archive']['sha256'])))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',type=Path)
    restore(parser.parse_args().destination)
