"""Rebuild the complete immutable C7 evidence archive from checked Git parts."""
import hashlib
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
manifest = json.loads((root/'MANIFEST.json').read_text())
target = Path(sys.argv[1]) if len(sys.argv) > 1 else root/manifest['name']
if target.exists():
    raise SystemExit('refusing to replace an existing original')
offset = 0
whole = hashlib.sha256()
with target.open('xb') as result:
    for part in manifest['parts']:
        path = root/part['name']
        data = path.read_bytes()
        if offset != part['offset'] or len(data) != part['bytes'] or hashlib.sha256(data).hexdigest() != part['sha256']:
            raise ValueError('misordered or damaged evidence part: '+part['name'])
        result.write(data)
        whole.update(data)
        offset += len(data)
if offset != manifest['bytes'] or whole.hexdigest() != manifest['sha256']:
    target.unlink()
    raise ValueError('reassembled original differs from manifest')
print(target, offset, whole.hexdigest())
