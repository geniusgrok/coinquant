"""One-shot registered command queue. No economic rules or runtime code here."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip, hashlib, json, os
from pathlib import Path
import shutil, subprocess, sys, time

ROOT = Path('/workspace/btc-alpha-beta-next')
ANALYSIS = Path('/workspace/btc-alpha-beta-analysis/spotquant')
OUT = Path('/workspace/scratch/alpha-beta-next')
HEADS = {ROOT/'coinquant': 'acedaa43ca94223f24e2fe11851bbef74e032a69',
         ROOT/'spotquant': '8ca002522fbdce531dcfbbb783ff4d152a7fd66c',
         ANALYSIS: '32ab1bb546bde064e641c4a2eb5ed4248e590acb'}
SPEC = json.loads((ROOT/'spotquant/research/alpha_beta_spec.json').read_text())
SINGLES = {'spot': OUT/'spot-singletons/accounts-manifest.json',
           'perp': OUT/'perp-singletons-retry1.json.gz'}
CAL = OUT/'registered-calibration.json'
ENV = dict(os.environ, TMPDIR=str(OUT/'tmp'), PYTHONDONTWRITEBYTECODE='1')

def read(path):
    with (gzip.open(path, 'rt') if path.suffix == '.gz' else path.open()) as stream:
        return json.load(stream)

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def write(path, body):
    with path.open('x') as stream:
        json.dump(body, stream, indent=2, allow_nan=False); stream.write('\n')

def source(repo):
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    package = 'coinquant' if repo.name == 'coinquant' else 'spotquant'
    dirty = subprocess.check_output(['git', 'status', '--porcelain', '--', package, 'research'], cwd=repo)
    if head != HEADS[repo] or dirty:
        raise ValueError('Protected source/HEAD changed: ' + str(repo))

def run(label, repo, module, arguments, output):
    source(repo)
    log = OUT/(label + '.run.log')
    if output.exists() or log.exists(): raise ValueError('Never overwrite evidence: ' + label)
    command = [sys.executable, '-u', '-m', module, *map(str, arguments), '--out', str(output)]
    started = datetime.now(timezone.utc).isoformat(); begin = time.monotonic()
    with log.open('x') as stream:
        result = subprocess.run(command, cwd=repo, env=ENV, stdout=stream, stderr=subprocess.STDOUT)
    receipt = {'label': label, 'command': command, 'cwd': str(repo), 'source_head': HEADS[repo],
               'started_utc': started, 'elapsed_seconds': time.monotonic()-begin,
               'exit_code': result.returncode, 'log_sha256': sha(log)}
    if output.exists(): receipt['output_sha256'] = sha(output)
    write(OUT/(label + '.command.json'), receipt)
    print(json.dumps(receipt), flush=True)
    if result.returncode or not output.exists(): raise RuntimeError('Command failed; originals retained: ' + label)
    source(repo)
    return output

def pack(raw):
    packed = raw.with_suffix('.json.gz'); original = sha(raw)
    with raw.open('rb') as src, packed.open('xb') as dst:
        with gzip.GzipFile(filename='', fileobj=dst, mode='wb', mtime=0) as stream:
            shutil.copyfileobj(src, stream, 1024*1024)
    with gzip.open(packed, 'rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != original:
            raise ValueError('Lossless compression mismatch')
    write(raw.with_suffix('.compression.json'), {'original_sha256': original,
          'original_bytes': raw.stat().st_size, 'retained_sha256': sha(packed),
          'retained_bytes': packed.stat().st_size, 'lossless_roundtrip_verified': True})
    raw.unlink(); return packed

def manifest(kind, paths, name):
    path = OUT/(name + '.json')
    write(path, {'format': 'alpha-account-manifest-v1', 'kind': kind,
                'files': [{'path': str(p.relative_to(OUT)), 'sha256': sha(p)} for p in paths]})
    return path

def assess(label, extra=(), calibration_out=False, final=False):
    args = ['--spot', SINGLES['spot'], '--perp', SINGLES['perp'],
            '--baseline-spot', ROOT/'spotquant/evidence/complete-delivery-20261001/spot-consensus-corrected.json',
            '--baseline-perp', ROOT/'coinquant/evidence/complete-delivery-20261001/perp-exclusive-accounts.json',
            '--csv', OUT/(label+'.csv'), '--markdown', OUT/(label+'.md'), *extra]
    if calibration_out: args += ['--calibration-out', CAL]
    if final: args += ['--final']
    path = run(label, ANALYSIS, 'research.alpha_assessment', args, OUT/(label+'.json'))
    report = read(path)
    if not all(v['passed'] for v in report['baseline_verification'].values()):
        raise ValueError('Original baseline mismatch; do not proceed')
    print(json.dumps({'assessment': label, 'pending': report['pending'],
          'selection': {k: v['selected_research_candidate'] for k,v in report['selection'].items()},
          'all_measured_accounts_valid': report['all_measured_accounts_valid']}), flush=True)
    return report

def risk(kind):
    names = [n for n in SPEC[kind+'_candidates'] if n in read(CAL)['profiles']]
    if not names: return None
    repo = ROOT/('spotquant' if kind == 'spot' else 'coinquant')
    module = 'research.alpha_spot' if kind == 'spot' else 'research.alpha_perp'
    common = ['--scenario', 'base', '--risk-calibration', CAL]
    common += ['--workers', '2'] if kind == 'spot' else ['--restore-prints']
    batches = [None] if names == SPEC[kind+'_candidates'] else names
    paths = []
    for name in batches:
        label = 'risk-'+kind+('-'+name if name else '')
        args = common + (['--candidate', name] if name else [])
        path = OUT/(label+('.json' if kind == 'spot' else '.json.gz'))
        run(label, repo, module, args, path)
        paths.append(pack(path) if kind == 'spot' else path)
    return paths[0] if len(paths) == 1 else manifest(kind, paths, 'risk-'+kind+'-manifest')

def combo(kind, parts):
    if len(parts) < 2: return None
    is_spot = kind == 'spot'; label = 'combo-'+kind
    path = OUT/(label+('.json' if is_spot else '.json.gz'))
    args = ['--combo', ','.join(parts)] + (['--workers', '2'] if is_spot else ['--restore-prints'])
    run(label, ROOT/('spotquant' if is_spot else 'coinquant'),
        'research.alpha_spot' if is_spot else 'research.alpha_perp', args, path)
    return pack(path) if is_spot else path

def main():
    # Existing producer processes finish first; Coin public print cache is serial.
    while not all(p.exists() for p in SINGLES.values()) or Path('/proc/32321').exists():
        time.sleep(10)
    provisional = assess('registered-unscaled', calibration_out=True)
    extra = ['--calibration', CAL]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {k: pool.submit(risk, k) for k in ('spot','perp')}
        for kind, future in futures.items():
            path = future.result()
            if path: extra += ['--risk-'+kind, path]
    matched = assess('registered-risk', extra)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {k: pool.submit(combo, k, matched['selection'][k]['compatible_components']) for k in ('spot','perp')}
        for kind, future in futures.items():
            path = future.result()
            if path: extra += ['--combo-'+kind, path]
    combined = assess('registered-combinations', extra)
    final_name = combined['selection']['perp']['selected_research_candidate']
    names = ['incumbent'] + ([] if final_name == 'incumbent' else [final_name])
    for name in names:
        for budget, offset in [('9900',0),('10100',0),('10000',-60000),('10000',60000)]:
            label = 'sensitivity-serial-retry1-'+name+'-'+budget+'-'+str(offset)
            path = OUT/(label+'.json.gz')
            args = ['--scenario','base','--initial-cny',budget,'--start-offset-ms',str(offset),'--restore-prints']
            args += ['--combo', ','.join(name.split('+'))] if '+' in name else ['--candidate',name]
            run(label, ROOT/'coinquant','research.alpha_perp',args,path)
            extra += ['--sensitivity-perp',path]
    final = assess('registered-final', extra, final=True)
    print(json.dumps({'finished_registered_measurements': True, 'rules_freeze_ready': final['rules_freeze_ready'],
          'independent_final_review_and_adoption_pending': True}), flush=True)

if __name__ == '__main__': main()
