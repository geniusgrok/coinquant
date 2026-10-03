"""Capture reviewed clean source and actual input bytes before full replay.

External controller helper. It performs no account operation or producer run.
Review paths are controller-approved evidence; financial acceptance is separate.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

BASE = Path('/workspace/btc-alpha-beta-improve')
ART = BASE / 'task-artifacts'


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4194304), b''):
            result.update(block)
    return result.hexdigest()


def git(repo, *argv):
    return subprocess.run(['git', *argv], cwd=repo, check=True,
                          capture_output=True, text=True).stdout.strip()


def source(repo):
    result = subprocess.run([sys.executable, '-c',
        'import json; from research.rebuild import source_identity; print(json.dumps(source_identity()))'],
        cwd=repo, check=True, capture_output=True, text=True)
    identity = json.loads(result.stdout)
    if identity['dirty'] or git(repo, 'status', '--porcelain'):
        raise ValueError('whole reviewed working tree must be clean: ' + str(repo))
    return identity


def binding(path):
    path = Path(path).resolve(strict=True)
    return {'path': str(path), 'sha256': sha(path), 'bytes': path.stat().st_size}


def market_files(root):
    return sorted(p.resolve() for p in root.rglob('*') if p.is_file() and
                  (p.name.endswith('.zip') or p.name.endswith('.zip.CHECKSUM')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', action='append', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('exclusive freeze output required')
    references = json.loads((ART/'baseline-reference-bindings.json').read_bytes())
    common = [ART/'edge-features-v1.json', ART/'baseline-reference-bindings.json',
              ART/'registered-financial-commands.json', ART/'run-registered-phase.py',
              ART/'vault-before-task4.json', Path(__file__),
              BASE/'coinquant/research/session_schedule.json',
              BASE/'starquant/data/usdcny_frankfurter.json']
    for entry in references['accepted_inputs']:
        if sha(entry['path']) != entry['sha256']:
            raise ValueError('approved reference mutated: ' + entry['path'])
        common.append(Path(entry['path']))
    for entry in references['references']:
        if sha(entry['raw']) != entry['raw_sha256']:
            raise ValueError('approved raw mutated: ' + entry['raw'])
        common.append(Path(entry['raw']))
    reviews = [binding(path) for path in args.review]
    projects = {}
    for kind, repo_name, market_root in (
            ('spot', 'spotquant', '/tmp/spotquant-market/klines'),
            ('perp', 'coinquant', '/tmp/coinquant-market')):
        repo = BASE/repo_name
        identity = source(repo)
        paths = list(common)
        for name in git(repo, 'ls-files', repo_name, 'research').splitlines():
            path = repo/name
            expected = git(repo, 'rev-parse', identity['git_head']+':'+name)
            actual = git(repo, 'hash-object', str(path))
            if expected != actual:
                raise ValueError('working file not committed: ' + str(path))
            paths.append(path)
        if kind == 'perp':
            paths.extend(repo/p for p in (
                'evidence/binance-boundary-20260921/warmup-trade.json',
                'evidence/binance-boundary-20260921/warmup-funding.json',
                'evidence/bounded-session-20260926/public/rules.json'))
            paths.extend(p for p in (repo/'evidence/real-yield-20260924/alfred').rglob('*') if p.is_file())
        market = Path(market_root)
        originals = market_files(market)
        if not originals:
            raise ValueError('public market input absent')
        for path in originals:
            if path.name.endswith('.zip'):
                declared = Path(str(path)+'.CHECKSUM').read_text().split()
                if not declared or sha(path) != declared[0]:
                    raise ValueError('official CHECKSUM mismatch: ' + str(path))
        paths.extend(originals)
        paths.extend(Path(v['path']) for v in reviews)
        projects[kind] = {
            'repository': str(repo), 'source': identity,
            'bound_files': [binding(p) for p in sorted(set(p.resolve(strict=True) for p in paths))],
            'bound_trees': [{'root': str(market), 'suffixes': ['.zip', '.zip.CHECKSUM'],
                             'files': [str(p) for p in originals]}],
        }
        if source(repo) != identity:
            raise ValueError('source changed while freezing: ' + kind)
    document = {'format': 'btc-edge-reviewed-source-freeze-v1',
        'recorded_utc': datetime.now(timezone.utc).isoformat(),
        'projects': projects, 'reviews': reviews,
        'public_vault_preflight': binding(ART/'vault-before-task4.json'),
        'original_market_vault': '/workspace/scratch/alpha-beta-next/public-print-vault',
        'meaning': 'Reviewed producer/evaluator/input identity, not financial qualification.'}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as stream:
        json.dump(document, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'output': str(args.out), 'sha256': sha(args.out),
        'sources': {k: v['source'] for k,v in projects.items()},
        'bound_files': {k: len(v['bound_files']) for k,v in projects.items()}}))


if __name__ == '__main__':
    main()
