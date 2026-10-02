"""One-shot external operating-evidence repair. Launch only after independent review.

No runtime hooks, source changes, economic rescaling, ignored fingerprint fields,
repeated retries, adoption, diary, packaging, or Git mutations.
"""
from datetime import datetime, timezone
from decimal import Decimal
import fcntl
import gc
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('/workspace/btc-alpha-beta-next')
REVIEW = ROOT/'review'
OUT = Path('/workspace/scratch/alpha-beta-next')
COIN, ANALYSIS = ROOT/'coinquant', Path('/workspace/btc-alpha-beta-analysis/spotquant')
WAIT_PIDS = (52503, 38554)
SOURCES = {
    COIN: ('acedaa43ca94223f24e2fe11851bbef74e032a69', 'a6e3f30f02208ff7e604b6181c5d8fa7000fe7e30dbc3276fbcc93ffbb0ad227'),
    ROOT/'spotquant': ('8ca002522fbdce531dcfbbb783ff4d152a7fd66c', '0df8c537ee8d47db6e841778e8e37eac847e1a0c1151e379440081b9473ae026'),
    ANALYSIS: ('99fcf005d2cb15c13bb37322b65ab2863b19d65e', '427f34ca3640cfa78f51173583af1d9c82f007baae155f3a992dcffb8171ad7b'),
    Path('/workspace/btc-alpha-beta-adoption/spotquant'): ('0c52c812301de3712f3637a1ce1b1241de0c40f1', '619570fb7baa586f28ad5de2a440d7752a536cc8f8ce7e357264612e65801537'),
}
PINNED = {
    OUT/'risk-perp.json.gz': '3b958b2e92d8aefcf7b9f073a3916c325420a546cf7652203ce6692be5ee2446',
    OUT/'risk-perp.command.json': '6177756a15cc19007ea7c14db7acdf84a02967512555c71d4272e26d495196d9',
    OUT/'registered-risk.json': '6854ef5fcfebb9e746c7a586f2122c7360d21ed2a40d573c73b8f6b8fee2bcfd',
    OUT/'perp-singletons-retry1.json.gz': 'bf1d167979f4bb3d15925f0bcaf5337bd1cc0a17523628b3af0599875dc5a7c1',
    OUT/'registered-calibration.json': 'ed8c99295e71386a7cef300f7d101ea941e5a7a0147bc9038012d6cc58e23821',
    OUT/'spot-project-calibration.json': 'd574693fe94480c598dc1698b008147267227385ada31df82eab9498d38e7b2b',
    REVIEW/'public_print_vault.py': '65ad132f5bf48559d455d4fa8a76966da76f661b1dda1540068f81c5f422e506',
}
NAMES = ('incumbent', 'fresh-entry', 'atr-trail', 'compression-breakout', 'single-topup')
GROUPS = {'financial', 'fills', 'daily', 'ownership', 'operating', 'remaining_original_fields'}
NEW = OUT/'risk-perp-incumbent-retry1.json.gz'
PROJECTED = OUT/'risk-perp-retained4-projection.json.gz'
MANIFEST = OUT/'risk-perp-repaired-manifest.json'
PROOF = OUT/'risk-perp-repair-projection-proof.json'
FINAL = OUT/'registered-final-repaired.json'
INTENT = OUT/'risk-perp-incumbent-retry1.attempt-intent.json'


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def ordinary(path):
    path = Path(path)
    require(path.resolve() == path.absolute() and not path.is_symlink(), 'Symlink path refused: '+str(path))
    require(not path.exists() or path.is_file(), 'Not an ordinary file: '+str(path))


def sha(path):
    ordinary(path)
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    ordinary(path)
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON key: '+key)
            result[key] = value
        return result
    opener = gzip.open if Path(path).suffix == '.gz' else open
    with opener(path, 'rt') as stream:
        # Reading to EOF validates gzip CRC; no partial account extraction.
        return json.load(stream, object_pairs_hook=pairs,
                         parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def write(path, body):
    ordinary(path)
    with Path(path).open('x') as stream:
        json.dump(body, stream, indent=2, allow_nan=False)
        stream.write('\n')


def unchanged(bound):
    for path, digest in bound.items():
        require(sha(path) == digest, 'Protected artifact changed: '+str(path))


def bind(bound, values):
    for path, digest in values.items():
        require(path not in bound or bound[path] == digest, 'Bound identity changed: '+str(path))
        bound[path] = digest


def sources():
    for repo, (head, digest) in SOURCES.items():
        def git(*args):
            return subprocess.check_output(['git', *args], cwd=repo, text=True).strip()
        package = repo.name
        require(git('rev-parse', 'HEAD') == head, 'Frozen HEAD changed: '+str(repo))
        require(not git('status', '--porcelain', '--', package, 'research'), 'Dirty frozen source: '+str(repo))
        actual = hashlib.sha256()
        for name in sorted(git('ls-files', package, 'research').splitlines()):
            if name.endswith('.py'):
                actual.update(name.encode()+b'\0'+(repo/name).read_bytes()+b'\0')
        require(actual.hexdigest() == digest, 'Frozen Python bytes changed: '+str(repo))


def no_producer():
    lines = subprocess.check_output(['ps', '-eo', 'pid=,args='], text=True).splitlines()
    modules = {'research.alpha_perp', 'research.complete_perp', 'research.alpha_spot',
               'research.complete_spot', 'research.adoption_spot', 'research.rebuild', 'coinquant', 'spotquant'}
    for line in lines:
        fields = line.strip().split()
        if not fields or int(fields[0]) == os.getpid():
            continue
        argv = fields[1:]
        executable = Path(argv[0]).name if argv else ''
        require(executable not in ('coinquant', 'spotquant'), 'Another account entrypoint is active')
        if not executable.startswith('python'):
            continue  # A parent shell may mention this command; its Python child is checked.
        if '-m' in argv:
            index = argv.index('-m')
            require(index+1 == len(argv) or argv[index+1] not in modules, 'Another account producer is active')
        require(not any(Path(arg).name.startswith('run_registered_followthrough') or
                        Path(arg).name == Path(__file__).name for arg in argv), 'Another registered controller is active')


def flag(command, name):
    require(command.count(name) == 1, 'Missing/duplicate command flag '+name)
    return command[command.index(name)+1]


def receipt(label, bound, *, directory=OUT, load=True):
    path = directory/(label+'.command.json')
    body = read(path)
    require(body['exit_code'] == 0, 'Original command did not complete: '+label)
    output = Path(flag(body['command'], '--out'))
    require(sha(output) == body['output_sha256'], 'Original command output changed: '+label)
    log = directory/(label+'.run.log')
    require(sha(log) == body['log_sha256'], 'Original command log changed: '+label)
    bind(bound, {path: sha(path), output: sha(output), log: sha(log)})
    return body, read(output) if load else None


def closed_inventory(bound):
    original_command, final = receipt('registered-final', bound)
    require(original_command['cwd'] == str(ANALYSIS) and original_command['source_head'] == SOURCES[ANALYSIS][0], 'Original final source/cwd differs')
    require(not final['pending'] and not final['registered_work_pending'], 'Original final inventory is pending')
    require(final['rules_freeze_ready'] is False and final['all_measured_accounts_valid'] is False and
            all(v['passed'] is True for v in final['baseline_verification'].values()), 'Old failure differs from known incumbent-only defect')
    invalid = {k: v['rejections'] for k, v in final['accounts'].items() if not v['valid']}
    require(invalid == {'perp/risk/incumbent/base': ['unity_control_evidence_mismatch']} and
            all(v['account']['valid'] for v in final['sensitivity']), 'Unexpected invalid old account')
    control = final['risk_baseline_controls']
    require(set(control) == {'spot', 'perp'} and control['spot']['passed'] is True and
            control['perp']['passed'] is False and control['perp']['rejections'] == ['unity_control_evidence_mismatch'] and
            control['perp']['evidence_checks'] == {key: key != 'operating' for key in GROUPS} and
            control['perp']['raw_sha256'] == PINNED[OUT/'risk-perp.json.gz'], 'Old failure is not exact known operating-only unity mismatch')
    path = REVIEW/'financial-audit-remaining-index.json'
    index = read(path)
    require(index['final_assessment_sha256'] == sha(OUT/'registered-final.json') and
            index['final_inventory_exactly_reconciled'] is True and index['all_examined_checks_passed'] is True and
            index['all_reported_complete'] is True, 'Original remaining audit inventory not closed')
    bind(bound, {path: sha(path)})
    actual = set()
    for row in index['audits']:
        raw, audit = Path(row['raw_path']), Path(row['audit_path'])
        require(sha(raw) == row['raw_sha256'] and sha(audit) == row['audit_sha256'], 'Remaining index bytes changed')
        bind(bound, {raw: row['raw_sha256'], audit: row['audit_sha256']})
        ar = read(audit.with_suffix('.command.json'))
        require(ar['exit_code'] == 0 and ar['output_sha256'] == row['audit_sha256'] and
                sha(audit.with_suffix('.run.log')) == ar['log_sha256'], 'Remaining audit receipt/log differs')
        bind(bound, {audit.with_suffix('.command.json'): sha(audit.with_suffix('.command.json')),
                      audit.with_suffix('.run.log'): ar['log_sha256']})
        for key in row['account_keys']:
            identity = (row['kind'], row['stage'], key, row['raw_sha256'])
            require(identity not in actual, 'Duplicate old audit identity')
            actual.add(identity)
    expected = {(kind, 'risk', key[len(kind+'/risk/'):], value['raw_bundle_sha256'])
                for key, value in final['accounts'].items() for kind in ('spot', 'perp') if key.startswith(kind+'/risk/')}
    require(not any(key.startswith(('spot/combo/', 'perp/combo/')) for key in final['accounts']), 'Unexpected combination requires new explicit review')
    expected.update(('perp', 'sensitivity', v['account']['candidate']+'/'+v['account']['scenario'], v['raw_sha256']) for v in final['sensitivity'])
    require(actual == expected and index['account_count'] == len(expected) == 16, 'Old assessment/audit inventories differ')
    required_inputs = {'--spot': OUT/'spot-singletons/accounts-manifest.json',
        '--perp': OUT/'perp-singletons-retry1.json.gz',
        '--baseline-spot': ROOT/'spotquant/evidence/complete-delivery-20261001/spot-consensus-corrected.json',
        '--baseline-perp': COIN/'evidence/complete-delivery-20261001/perp-exclusive-accounts.json',
        '--calibration': OUT/'registered-calibration.json', '--risk-spot-calibration': OUT/'spot-project-calibration.json',
        '--risk-spot': OUT/'risk-spot-project-early.json.gz', '--risk-perp': OUT/'risk-perp.json.gz'}
    require(all(flag(original_command['command'], option) == str(path) for option,path in required_inputs.items()),
            'Original assessment command inputs differ from registered paths')
    sensitivities = [Path(original_command['command'][i+1]) for i, value in enumerate(original_command['command']) if value == '--sensitivity-perp']
    require(len(sensitivities) == 4 and {sha(p) for p in sensitivities} == {v['raw_sha256'] for v in final['sensitivity']}, 'Original four sensitivity inputs differ')
    for p in sensitivities:
        receipt(p.name.removesuffix('.json.gz'), bound, load=False)
    # Preserve every original command input, including one-level Spot originals.
    for option in ('--spot', '--perp', '--baseline-spot', '--baseline-perp', '--calibration', '--risk-spot-calibration', '--risk-spot', '--risk-perp'):
        p = Path(flag(original_command['command'], option));bind(bound, {p: sha(p)})
        if p.suffix == '.json':
            item = read(p)
            if item.get('format') == 'alpha-account-manifest-v1':
                for child in item['files']:
                    child_path = p.parent/child['path']
                    require(sha(child_path) == child['sha256'], 'Original manifest child changed')
                    bind(bound, {child_path: child['sha256']})
    return original_command, final


def public_catalog():
    original = read(OUT/'risk-perp.json.gz')
    required = original['inputs']['loaded_print_files']
    records = {}
    for name, digest in required.items():
        require(Path(name).name == name and name.endswith('.zip'), 'Invalid recorded public ZIP name')
        record = OUT/'public-print-vault/records'/(name+'.json')
        row = read(record)
        require(row['name'] == name and row['sha256'] == digest, 'Vault catalog missing/conflicts with original consumed ZIP')
        records[name] = sha(record)
    return {'required_loaded_print_files': required, 'matched_records': len(records),
            'catalog_record_sha256': records, 'zip_bytes_must_be_verified_by_approved_restore': True,
            'catalog_is_not_operating_equality': True}


def run(label, repo, command, output, bound):
    sources();unchanged(bound);no_producer()
    log, record = OUT/(label+'.run.log'), OUT/(label+'.command.json')
    for p in (output, log, record):
        ordinary(p);require(not p.exists(), 'Never retry or overwrite: '+str(p))
    started, begin = datetime.now(timezone.utc).isoformat(), time.monotonic()
    env = dict(os.environ, TMPDIR=str(OUT/'tmp'), PYTHONDONTWRITEBYTECODE='1')
    with log.open('x') as stream:
        result = subprocess.run(command, cwd=repo, env=env, stdout=stream, stderr=subprocess.STDOUT)
    body = {'label': label, 'command': command, 'cwd': str(repo), 'source_head': SOURCES[repo][0],
            'started_utc': started, 'elapsed_seconds': time.monotonic()-begin, 'exit_code': result.returncode,
            'log_sha256': sha(log), 'TMPDIR': env['TMPDIR'], 'helper_sha256': bound[Path(__file__)],
            'output_sha256': sha(output) if output.exists() else None,
            'attempt_intent_sha256': bound[INTENT]}
    write(record, body)
    require(result.returncode == 0 and output.exists(), 'Actual command failed; originals retained: '+label)
    sources();unchanged(bound)
    bind(bound, {output: body['output_sha256'], record: sha(record), log: body['log_sha256']})
    return body


def validate_bundle(a, bundle, env, cal, names, *, calibrated=True):
    meta = a.metadata(bundle, 'perp', env)
    require(set(bundle['results']) == set(names) == set(meta['candidates']), 'Wrong candidate inventory')
    require(meta['risk_calibration_sha256'] == (PINNED[OUT/'registered-calibration.json'] if calibrated else None), 'Calibration hash differs')
    for name in names:
        require(meta['risk_profiles'].get(name) == (cal['profiles'][name] if calibrated else None), 'Actual risk profile changed')
        if calibrated:
            require(set(bundle['results'][name]) == {'base'}, 'Unexpected risk stress')
        row = bundle['results'][name]['base']
        require(len(row['sessions']) == 795 and row['complete'] is True and not a.row_validity(row, 'perp', env['starts'], '10000'), 'Incomplete/invalid actual account')
    return meta


def derive(a, env, bound, consumed):
    cal = read(OUT/'registered-calibration.json')
    require(Decimal(cal['profiles']['incumbent']['scale']) == 1, 'Incumbent is not a unity control')
    original = read(OUT/'perp-singletons-retry1.json.gz')
    baseline = a.evidence_fingerprints(original['results']['incumbent']['base'], 'perp')
    baseline_meta = original['inputs']
    del original;gc.collect()
    new = read(NEW)
    new_meta = validate_bundle(a, new, env, cal, ('incumbent',))
    a.equivalent_inputs(baseline_meta, new_meta, 'perp')
    six = a.evidence_fingerprints(new['results']['incumbent']['base'], 'perp')
    require(consumed['valid'] is True and consumed['rejections'] == [] and
            consumed['raw_bundle_sha256'] == sha(NEW) and consumed['evidence_sha256'] == six,
            'Immutable99 consume differs from actual incumbent evidence')
    require(set(six) == GROUPS and six == baseline, 'New incumbent fails strict all-six equality; no projection/manifest/final')
    new_row_hash = a.checksum(new['results']['incumbent']['base'])
    del new;gc.collect()
    original = read(OUT/'risk-perp.json.gz')
    original_meta = validate_bundle(a, original, env, cal, NAMES)
    a.equivalent_inputs(original_meta, new_meta, 'perp')
    require(original_meta['source'] == new_meta['source'] and original_meta['measured_source'] == new_meta['measured_source'], 'Measured source relabel refused')
    row_hashes = {name+'/base': a.checksum(original['results'][name]['base']) for name in NAMES[1:]}
    # Full input provenance and actual profiles remain exactly original, even
    # though consumed-file/profile supersets include the removed incumbent.
    derivation = {'kind': 'lossless-account-projection', 'original_bundle_path': str(OUT/'risk-perp.json.gz'),
        'original_bundle_sha256': PINNED[OUT/'risk-perp.json.gz'],
        'original_receipt_path': str(OUT/'risk-perp.command.json'),
        'original_receipt_sha256': PINNED[OUT/'risk-perp.command.json'], 'retained_row_sha256': row_hashes}
    projected = {**original, 'inputs': {**original_meta, 'candidates': {n: original_meta['candidates'][n] for n in NAMES[1:]}},
                 'results': {n: original['results'][n] for n in NAMES[1:]}, 'derivation': derivation}
    ordinary(PROJECTED)
    with PROJECTED.open('xb') as raw:
        with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as zipped:
            import io
            with io.TextIOWrapper(zipped, encoding='utf-8') as stream:
                json.dump(projected, stream, allow_nan=False)
    projected_hash = sha(PROJECTED)
    original_top_hash = a.checksum({k: v for k, v in original.items() if k not in ('inputs', 'results')})
    original_input_hash = a.checksum({k: v for k, v in original_meta.items() if k != 'candidates'})
    del original, projected;gc.collect()
    # Independent rereads validate both gzip CRCs and every retained row, not
    # only financial groups; no rescaling or replacing a partial trajectory.
    restored = read(PROJECTED)
    validate_bundle(a, restored, env, cal, NAMES[1:])
    require(restored['derivation'] == derivation and a.checksum({k:v for k,v in restored['inputs'].items() if k != 'candidates'}) == original_input_hash, 'Projection input provenance changed')
    require(a.checksum({k:v for k,v in restored.items() if k not in ('inputs','results','derivation')}) == original_top_hash, 'Projection conditions/top-level metadata changed')
    require({n+'/base': a.checksum(restored['results'][n]['base']) for n in NAMES[1:]} == row_hashes, 'Projected row differs')
    del restored;gc.collect()
    reread = read(OUT/'risk-perp.json.gz')
    require({n+'/base': a.checksum(reread['results'][n]['base']) for n in NAMES[1:]} == row_hashes, 'Original row changed during projection')
    del reread;gc.collect()
    reread = read(NEW)
    require(a.checksum(reread['results']['incumbent']['base']) == new_row_hash and a.evidence_fingerprints(reread['results']['incumbent']['base'], 'perp') == baseline, 'Actual incumbent changed during projection')
    del reread;gc.collect()
    unchanged(bound);sources()
    require(sha(PROJECTED) == projected_hash, 'Projection bytes changed on verification')
    write(PROOF, {'derivation': derivation, 'projected_path': str(PROJECTED), 'projected_sha256': projected_hash,
        'actual_incumbent_path': str(NEW), 'actual_incumbent_sha256': sha(NEW),
        'actual_incumbent_receipt_sha256': sha(OUT/'risk-perp-incumbent-retry1.command.json'),
        'actual_incumbent_row_sha256': new_row_hash, 'immutable99_actual_consume_valid': True,
        'original_run_log_sha256': bound[OUT/'risk-perp.run.log'], 'six_groups': six, 'unscaled_incumbent_six_groups': baseline,
        'all_six_exact': True, 'all_retained_rows_exact': True, 'full_original_profiles_retained': True,
        'original_input_except_candidates_sha256': original_input_hash, 'original_top_except_inputs_results_sha256': original_top_hash,
        'calibration_sha256': PINNED[OUT/'registered-calibration.json'], 'measured_source': new_meta['source'],
        'gzip_crc_reread_passed': True, 'source_relabelled': False, 'helper_sha256': bound[Path(__file__)]})
    write(MANIFEST, {'format': 'alpha-account-manifest-v1', 'kind': 'perp', 'files': [
        {'path': PROJECTED.name, 'sha256': projected_hash}, {'path': NEW.name, 'sha256': sha(NEW)}]})
    bind(bound, {PROJECTED: projected_hash, PROOF: sha(PROOF), MANIFEST: sha(MANIFEST)})


def repaired_command(command):
    result = list(command)
    require(result[1:4] == ['-u', '-m', 'research.alpha_assessment'], 'Original final module/executable shape differs')
    for name, value in (('--risk-perp', MANIFEST), ('--out', FINAL), ('--csv', FINAL.with_suffix('.csv')), ('--markdown', FINAL.with_suffix('.md'))):
        flag(result, name)
        result[result.index(name)+1] = str(value)
    require(result.count('--final') == 1 and flag(result, '--calibration') == str(OUT/'registered-calibration.json') and
            flag(result, '--risk-spot-calibration') == str(OUT/'spot-project-calibration.json'), 'Original final command shape differs')
    return result


def main():
    sys.dont_write_bytecode = True
    bound = {**PINNED, Path(__file__): sha(Path(__file__))}
    ordinary(INTENT);require(not INTENT.exists(), 'One registered attempt already exists; no reroll')
    sources();unchanged(bound)
    while any((Path('/proc')/str(pid)).exists() for pid in WAIT_PIDS):
        time.sleep(10)
    lock_path = OUT/'.registered-followthrough-exclusive.lock'
    ordinary(lock_path)
    with lock_path.open('a+b') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        no_producer();sources();unchanged(bound)
        for path in (INTENT, NEW, PROJECTED, MANIFEST, PROOF, FINAL, FINAL.with_suffix('.csv'), FINAL.with_suffix('.md')):
            ordinary(path);require(not path.exists(), 'Never overwrite repair artifact: '+str(path))
        old_command, old_final = closed_inventory(bound)
        risk_command, _ = receipt('risk-perp', bound, load=False)
        require(risk_command['cwd'] == str(COIN) and risk_command['source_head'] == SOURCES[COIN][0], 'Original risk source/cwd differs')
        command = [risk_command['command'][0], '-u', '-m', 'research.alpha_perp', '--candidate', 'incumbent',
                   '--scenario', 'base', '--risk-calibration', str(OUT/'registered-calibration.json'),
                   '--restore-prints', '--out', str(NEW)]
        final_command = repaired_command(old_command['command'])
        catalog = public_catalog()
        write(INTENT, {'registered_utc': datetime.now(timezone.utc).isoformat(), 'attempt': 1,
            'retry_command': command, 'retry_cwd': str(COIN), 'final_command': final_command, 'final_cwd': str(ANALYSIS),
            'TMPDIR': str(OUT/'tmp'), 'source_heads_and_python_hashes': {str(p): v for p,v in SOURCES.items()},
            'bound_input_sha256': {str(p): h for p,h in bound.items()}, 'helper_sha256': bound[Path(__file__)],
            'gate': 'one complete actual incumbent, immutable99 consume and all six equality; otherwise stop without projection',
            'automatic_second_attempt': False, 'adoption_approval': False, 'public_catalog': catalog})
        bound[INTENT] = sha(INTENT)
        # The approved helper is the sole cache writer, and runs only between jobs.
        spec = importlib.util.spec_from_file_location('repair_public_vault', REVIEW/'public_print_vault.py')
        vault = importlib.util.module_from_spec(spec);spec.loader.exec_module(vault)
        vault.restore('risk-perp-incumbent-retry1')
        restore_receipt = OUT/'risk-perp-incumbent-retry1-public-archive-restore.json'
        restored = {v['name']:v['sha256'] for v in read(restore_receipt)['records']}
        require(all(restored.get(name) == digest for name,digest in catalog['required_loaded_print_files'].items()),
                'Approved restore did not verify the required original public ZIPs')
        bound[restore_receipt] = sha(restore_receipt)
        sources();unchanged(bound);no_producer()
        run('risk-perp-incumbent-retry1', COIN, command, NEW, bound)
        sys.path.insert(0, str(ANALYSIS))
        from research import alpha_assessment as a
        require(Path(a.__file__).resolve() == ANALYSIS/'research/alpha_assessment.py', 'Wrong immutable assessor imported')
        market = Path('/tmp/spotquant-market/klines')
        fx_path = ROOT/'starquant/data/usdcny_frankfurter.json'
        env = a.environment(COIN/'research/session_schedule.json', fx_path, market)
        require(env == old_final['input_environment'], 'Frozen public inputs changed')
        bars = a.load_daily(market, a.END_MS, require_through=a.END_MS)
        fx = a.PriorFX(fx_path)
        usd, cny = a.market_returns_for(bars, fx)
        consumed = a.consume(NEW, 'perp', env, bars, fx, usd, cny, expected={'incumbent/base'},
            reference=old_final['inputs']['perp'], calibration=read(OUT/'registered-calibration.json'),
            calibration_sha=PINNED[OUT/'registered-calibration.json'])
        derive(a, env, bound, consumed['accounts']['incumbent/base'])
        command = final_command
        run('registered-final-repaired', ANALYSIS, command, FINAL, bound)
        final = read(FINAL)
        require(not final['pending'] and not final['registered_work_pending'] and final['rules_freeze_ready'] is True and
                final['all_measured_accounts_valid'] is True and all(v['passed'] is True for v in final['baseline_verification'].values()) and
                all(v['passed'] is True for v in final['risk_baseline_controls'].values()), 'Corrected final acceptance failed; receipts retained without adoption')
        require(final['inputs']['risk_perp']['raw_sha256'] == sha(MANIFEST), 'Final did not consume repaired manifest')
        sources();unchanged(bound)
        print(json.dumps({'corrected_assessment': str(FINAL), 'sha256': sha(FINAL), 'rules_freeze_ready': True,
                          'independent_financial_review_pending': True, 'adoption_approval': False}), flush=True)


if __name__ == '__main__':
    if sys.argv[1:] != ['--execute']:
        raise SystemExit('Reviewed one-shot launch requires explicit --execute; no preflight or producer was run.')
    main()
