"""Verify and restore a saved original-account or official-minute archive."""
import argparse
import hashlib
import io
import json
import tarfile
from pathlib import Path


def verify(label, destination, source=Path(__file__).parent / 'originals'):
    manifest = json.loads((source / (label + '.manifest.json')).read_text())
    chunks = []
    for part in manifest['parts']:
        payload = (source / part['name']).read_bytes()
        assert len(payload) == part['size']
        assert hashlib.sha256(payload).hexdigest() == part['sha256']
        oid = hashlib.sha1(f'blob {len(payload)}\0'.encode() + payload).hexdigest()
        assert oid == part['git_blob_oid']
        chunks.append(payload)
    payload = b''.join(chunks)
    assert len(payload) == manifest['archive_size']
    assert hashlib.sha256(payload).hexdigest() == manifest['archive_sha256']
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as archive:
        members = archive.getmembers()
        assert {m.name for m in members} == set(manifest['members'])
        for member in members:
            assert member.isfile()
            target = destination / member.name
            assert target.resolve().is_relative_to(destination.resolve())
            data = archive.extractfile(member).read()
            expected = manifest['members'][member.name]
            assert len(data) == expected['size']
            assert hashlib.sha256(data).hexdigest() == expected['sha256']
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    return len(members), manifest['archive_sha256']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('label', choices=('development', 'formal', 'minute-source'))
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    print(verify(args.label, args.destination))
