"""Rebuild and verify the complete original event files from small Git blobs."""
import hashlib
import json
from pathlib import Path
import sys


def restore(root, output):
    manifest=json.loads((root/'ORIGINALS.json').read_text())
    output.mkdir(parents=True,exist_ok=True)
    for name,record in manifest.items():
        if Path(name).name!=name:raise ValueError('unsafe output name')
        result=output/name
        offset=0;sha=hashlib.sha256()
        with result.open('wb') as stream:
            for item in record['parts']:
                if Path(item['path']).name!=item['path'] or item['offset']!=offset:
                    raise ValueError('part path or offset mismatch')
                raw=(root/item['path']).read_bytes()
                if len(raw)!=item['bytes'] or hashlib.sha256(raw).hexdigest()!=item['sha256']:
                    raise ValueError('part identity mismatch')
                stream.write(raw);sha.update(raw);offset+=len(raw)
        if offset!=record['bytes'] or sha.hexdigest()!=record['sha256']:
            result.unlink(missing_ok=True)
            raise ValueError('original length or digest mismatch')
        print(name,offset,sha.hexdigest())


if __name__=='__main__':restore(Path(__file__).resolve().parent,Path(sys.argv[1]))
