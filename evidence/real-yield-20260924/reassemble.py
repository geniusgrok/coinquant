"""Verify Git parts and restore every exact official/account original from a clone."""
from hashlib import sha1, sha256
import json
from pathlib import Path
import tarfile

HERE=Path(__file__).resolve().parent


def check(raw,record):
    assert len(raw)==record['bytes'] and sha256(raw).hexdigest()==record['sha256']
    assert sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==record['git_blob_sha1']


def restore(output):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((HERE/'ORIGINALS.json').read_text())
    for record in manifest['alfred']:
        check((HERE/record['path']).read_bytes(),record)
    counts={}
    for label,archive in manifest['archives'].items():
        content=bytearray()
        for part in archive['parts']:
            assert part['offset']==len(content)
            data=(HERE/part['path']).read_bytes();check(data,part)
            content.extend(data)
        check(content,archive)
        target=output/archive['original_name'];target.write_bytes(content)
        expected={r['path']:r for r in archive['members']}
        actual=set()
        with tarfile.open(target,'r:gz') as source:
            for member in source:
                if not member.isfile():continue
                name=member.name
                assert name in expected and name not in actual and not name.startswith('/')
                parts=Path(name).parts
                assert '..' not in parts
                raw=source.extractfile(member).read()
                check(raw,expected[name]);actual.add(name)
                path=output/name;path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(raw)
        assert actual==set(expected)
        counts[label]=len(actual)
    print(json.dumps(dict(archives=len(counts),originals=counts,
        alfred_responses=len(manifest['alfred']))))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    args=parser.parse_args();restore(args.output)
