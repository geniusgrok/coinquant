"""One-time exact Library-source restoration, confined to the authorized branch."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

BASE = 'a6861aa2d202114ce050371691d9bf339d32a8b4'
BRANCH = 'research/on-demand-btc-20260920'
PACKET = Path('.source-recovery-20260922')
RECEIPT = Path('evidence/sustainable-capital-exit-20260922/SOURCE_RESTORATION.json')


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_after(manifest):
    for row in manifest['files']:
        data = Path(row['path']).read_bytes()
        if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['after']:
            raise ValueError('restored file mismatch: ' + row['path'])
        if git('hash-object', row['path']) != row['blob']:
            raise ValueError('restored Git blob mismatch: ' + row['path'])
    selection = json.loads(Path('evidence/sustainable-capital-exit-20260922/SELECTION.json').read_text())
    for name, sha in selection['source_identity'].items():
        if digest(name) != sha:
            raise ValueError('frozen economic source mismatch: ' + name)
    if git('hash-object', 'pancakequant/capital.py') != manifest['staged_capital_blob']:
        raise ValueError('staged capital source mismatch')
    # This migration never changes entrypoint, credentials, defaults, or writes.
    for name in ('pancakequant/cli.py', 'pancakequant/config.py', 'config.example.json',
                 'pancakequant/native_preview.py', 'research/spec.json'):
        if git('hash-object', name) != git('rev-parse', BASE + ':' + name):
            raise ValueError('protected migration boundary changed: ' + name)


def main():
    if os.environ.get('GITHUB_REF') != 'refs/heads/' + BRANCH:
        raise ValueError('restoration may only run on the authorized research branch')
    if git('rev-parse', 'HEAD') != os.environ['GITHUB_SHA'] or git('rev-parse', 'HEAD^') != BASE:
        raise ValueError('unexpected restoration parent; do not overwrite concurrent work')
    manifest = json.loads((PACKET/'manifest.json').read_text())
    mode = sys.argv[1]
    if mode == 'apply':
        patches = []
        for row in manifest['files']:
            path = Path(row['path'])
            if path.is_absolute() or '..' in path.parts or path.parts[0] not in ('pancakequant', 'research', 'tests'):
                raise ValueError('invalid source path')
            before = digest(path) if path.exists() else None
            if before != row['before']:
                raise ValueError('base source differs: ' + row['path'])
            patch = PACKET/row['patch']
            if digest(patch) != row['patch_sha256']:
                raise ValueError('transport patch differs: ' + row['patch'])
            patches.append(str(patch))
        subprocess.run(['git', 'apply', '--check', *patches], check=True)
        subprocess.run(['git', 'apply', *patches], check=True)
        verify_after(manifest)
        print('Exact source restored; frozen economic hashes and execution block unchanged.')
    elif mode == 'publish':
        verify_after(manifest)
        log = Path(os.environ['RUNNER_TEMP'])/'source-check.log'
        text = log.read_text()
        if not text.rstrip().endswith('OK') or 'Ran 266 tests' not in text:
            raise ValueError('expected complete offline check did not pass')
        # Restore the one read-only CI workflow in the same commit as the sources.
        shutil.copyfile(PACKET/'check.readonly.yml', '.github/workflows/check.yml')
        receipt = dict(archive_sha256=manifest['archive_sha256'], archive_members=899,
            restored_files=manifest['files'], capital_blob=manifest['staged_capital_blob'],
            previous_remote_commit=BASE, staging_commit=os.environ['GITHUB_SHA'],
            frozen_economic_source_identity_verified=True, default_execution_unchanged=True,
            validation='compileall and 266 offline unittest checks passed; no economic replay',
            validation_log_sha256=digest(log), real_or_testnet_writes=False,
            scope='Exact Library implementation restored; not a new strategy result or production qualification.')
        RECEIPT.write_text(json.dumps(receipt, indent=2)+'\n')
        target_paths = [row['path'] for row in manifest['files']]
        shutil.rmtree(PACKET)
        subprocess.run(['git','add','--',*target_paths,str(RECEIPT),'.github/workflows/check.yml',str(PACKET)],check=True)
        changed = set(git('diff','--cached','--name-only').splitlines())
        allowed = set(target_paths)|{str(RECEIPT),'.github/workflows/check.yml'}
        if any(name not in allowed and not name.startswith(str(PACKET)+'/') for name in changed):
            raise ValueError('unexpected staged path')
        subprocess.run(['git','-c','user.name=github-actions[bot]',
            '-c','user.email=41898282+github-actions[bot]@users.noreply.github.com',
            'commit','-m','Restore exact verified SX60 research sources; remove one-time publisher [workspace-export]'],check=True)
        subprocess.run(['git','push','origin','HEAD:refs/heads/'+BRANCH],check=True)
        print('Published exact source commit:',git('rev-parse','HEAD'))
    else:
        raise ValueError('unknown restoration phase')


if __name__ == '__main__':
    main()
