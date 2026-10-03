"""Read committed archives only; no account/proof recomputation or execution."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path('/workspace/btc-alpha-beta-improve/spotquant')
OUT = Path('/workspace/btc-alpha-beta-improve/task-artifacts/final-export-proof-reader-fix')
BASE = 'baf0939a8d0ae1f38b84d7579912d67b0db8c13c'
FINAL = 'b49291f7a1df569c2910359e0de1c5a769c40256'
CANONICAL = '609606d9c0e0ad8d3c3038b329c9c4ab6d1b9629'
ORIGINAL = '74bd6e035e36531c517029077c1a9e2e5ec44516'

def git(*args, root=ROOT):
    return subprocess.check_output(['git', *args], cwd=root)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def snapshot(head):
    files, modes, digest = {}, {}, hashlib.sha256()
    with tarfile.open(fileobj=io.BytesIO(git('archive', head))) as archive:
        for member in sorted(archive.getmembers(), key=lambda m: m.name):
            if not member.isfile():
                assert not member.issym() and not member.islnk()
                continue
            name, raw = member.name, archive.extractfile(member).read()
            parts = Path(name).parts
            protected = (parts[0] in ('spotquant', '.github') or
                (parts[0] == 'research' and (not name.endswith('.md') or 'protocol' in parts[-1].lower())) or
                (len(parts) == 1 and (Path(name).suffix in {'.py', '.json', '.toml', '.yaml', '.yml', '.cfg', '.ini', '.sh'} or bool(member.mode & 0o111))))
            if not protected:
                continue
            files[name], modes[name] = sha(raw), member.mode
            if name.startswith(('spotquant/', 'research/')) and name.endswith('.py'):
                digest.update(name.encode() + b'\0' + raw + b'\0')
    protected_raw = json.dumps({'files': files, 'modes': modes}, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return dict(git_head=head, python_sources_sha256=digest.hexdigest(), protected_files=files,
                protected_modes=modes, protected_sha256=sha(protected_raw))

def difference(a, b):
    return {p: dict(before_sha256=a['protected_files'].get(p), after_sha256=b['protected_files'].get(p),
                   before_mode=a['protected_modes'].get(p), after_mode=b['protected_modes'].get(p))
            for p in sorted(a['protected_files'].keys() | b['protected_files'].keys())
            if a['protected_files'].get(p) != b['protected_files'].get(p) or a['protected_modes'].get(p) != b['protected_modes'].get(p)}

sources = {label: snapshot(head) for label, head in [('original_measurement', ORIGINAL),
    ('accepted_canonical', CANONICAL), ('implementation_base', BASE), ('implementation_final', FINAL)]}
result = dict(sources=sources,
    base_to_final_protected_difference=difference(sources['implementation_base'], sources['implementation_final']),
    canonical_to_final_protected_difference=difference(sources['accepted_canonical'], sources['implementation_final']),
    canonical_to_base_protected_difference=difference(sources['accepted_canonical'], sources['implementation_base']),
    working_status=git('status', '--short').decode(),
    coin_head=git('rev-parse', 'HEAD', root=ROOT.parent / 'coinquant').decode().strip(),
    note='Committed archive identities. Root-owned metadata is concurrently dirty; no current clean-source assertion.')
assert set(result['base_to_final_protected_difference']) == {'research/edge_assessment.py'}
assert set(result['canonical_to_final_protected_difference']) == {'research/edge_assessment.py'}
assert not result['canonical_to_base_protected_difference']
(OUT / 'source-impact.json').write_text(json.dumps(result, indent=2) + '\n')
(OUT / 'BASE-to-FINAL.diff').write_bytes(git('diff', '--binary', BASE, FINAL))
print(json.dumps({k: {p: v[p] for p in ('git_head', 'python_sources_sha256', 'protected_sha256')} for k, v in sources.items()}, indent=2))
print(json.dumps(result['base_to_final_protected_difference'], indent=2))
