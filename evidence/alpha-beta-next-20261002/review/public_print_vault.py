"""Retain verified public ZIPs without touching the active producer's cache."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import uuid

OUT = Path('/workspace/scratch/alpha-beta-next')
SOURCE = Path('/workspace/.btc-third-round-prints')
VAULT = OUT/'public-print-vault'
MARKER = 'BTC-third-round-20261001\n'
MAX_BYTES = 16 * 1024**3
NAME = re.compile(r'BTCUSDT-aggTrades-\d{4}-\d{2}-\d{2}\.zip\Z')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def require_source():
    if any(p.resolve() != p for p in (SOURCE, OUT, VAULT)):
        raise ValueError('Public paths may not traverse symlink directories')
    ordinary(SOURCE, directory=True)
    ordinary(VAULT, directory=True)
    marker = SOURCE/'.unified-perp-cache'
    ordinary(marker)
    if marker.read_text() != MARKER:
        raise ValueError('Unrecognized public cache; never access another directory')


def ordinary(path, *, directory=False):
    if path.is_symlink() or (path.exists() and not (path.is_dir() if directory else path.is_file())):
        raise ValueError('Task-owned public path must be an ordinary file/directory: '+str(path))


def record_new(path, value):
    ordinary(path.parent, directory=True)
    ordinary(path)
    temporary = path.with_name(path.name+'.'+uuid.uuid4().hex+'.pending')
    with temporary.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
    os.link(temporary, path)  # Atomic exclusive publication; never overwrite.
    temporary.unlink()


def expected(checksum, name):
    fields = checksum.decode('ascii').split()
    if (len(fields) not in (1, 2) or not re.fullmatch('[0-9a-f]{64}', fields[0])
            or (len(fields) == 2 and fields[1].lstrip('*') != name)):
        raise ValueError('Malformed or wrong-name official checksum')
    return fields[0]


def watch():
    tool_sha = sha(Path(__file__))
    require_source()
    VAULT.mkdir(exist_ok=True)
    records = VAULT/'records'
    ordinary(records, directory=True)
    records.mkdir(exist_ok=True)
    ordinary(VAULT/'.watch.lock')
    with (VAULT/'.watch.lock').open('a+b') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Count every retained ZIP, including interrupted captures without records.
        retained_files = list(VAULT.glob('*.zip'))
        for path in retained_files:
            ordinary(path)
            if not NAME.fullmatch(path.name):
                raise ValueError('Unexpected retained public archive')
        total = sum(p.stat().st_size for p in retained_files)
        ordinary(VAULT/'.stop')
        while not (VAULT/'.stop').exists():
            require_source()
            ordinary(records, directory=True)
            ordinary(VAULT/'.stop')
            if sha(Path(__file__)) != tool_sha:
                raise ValueError('Read-only public archive watcher changed')
            for source in sorted(SOURCE.glob('*.zip')):
                if not NAME.fullmatch(source.name):
                    raise ValueError('Unexpected file in task-owned public cache')
                record = records/(source.name+'.json')
                ordinary(record)
                if record.exists():
                    continue
                try:
                    ordinary(source)
                    ordinary(Path(str(source)+'.CHECKSUM'))
                    checksum = Path(str(source)+'.CHECKSUM').read_bytes()
                    digest = expected(checksum, source.name)
                    size = source.stat().st_size
                    retained = VAULT/source.name
                    ordinary(retained)
                    already_retained = retained.exists()
                    if not already_retained and (total+size > MAX_BYTES or shutil.disk_usage(VAULT).free < 5*1024**3):
                        continue  # Unretained days still use normal official restoration.
                    if sha(source) != digest:
                        raise ValueError('Public source ZIP differs from official checksum')
                    if not already_retained:
                        os.link(source, retained)  # New link only in VAULT; producer paths unchanged.
                except FileNotFoundError:
                    continue  # Producer may prune a day between observation and link.
                if sha(retained) != digest:
                    raise ValueError('Retained public ZIP changed during capture')
                sidecar = Path(str(retained)+'.CHECKSUM')
                ordinary(sidecar)
                if sidecar.exists():
                    if sidecar.read_bytes() != checksum:
                        raise ValueError('Interrupted capture has conflicting official checksum')
                else:
                    with sidecar.open('xb') as stream:
                        stream.write(checksum)
                record_new(record, dict(name=source.name, sha256=digest, bytes=size,
                      official_checksum_sha256=hashlib.sha256(checksum).hexdigest(),
                      origin='Original official public ZIP retained read-only from frozen producer cache',
                      source_cache_marker_sha256=hashlib.sha256(MARKER.encode()).hexdigest()))
                if not already_retained:
                    total += size
                print(json.dumps({'retained': source.name, 'sha256': digest, 'bytes': size}), flush=True)
            time.sleep(5)


def restore(label):
    tool_sha = sha(Path(__file__))
    require_source()
    if not re.fullmatch('[A-Za-z0-9_.+-]+', label):
        raise ValueError('Invalid one-shot receipt label')
    ordinary(OUT/'.coin-public-restore.lock')
    ordinary(VAULT/'records', directory=True)
    with (OUT/'.coin-public-restore.lock').open('a+b') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        active = subprocess.check_output(['ps', '-eo', 'args'], text=True).splitlines()
        if any(any(' -m '+m+' ' in line for m in ('research.alpha_perp', 'research.complete_perp'))
               for line in active):
            raise ValueError('Restore requires NO active Coin economic producer')
        entries = []
        for record in sorted((VAULT/'records').glob('*.json')):
            ordinary(record)
            value = json.loads(record.read_text())
            name = value['name']
            if not NAME.fullmatch(name) or record.name != name+'.json':
                raise ValueError('Invalid vault record name')
            retained = VAULT/name
            ordinary(retained)
            ordinary(Path(str(retained)+'.CHECKSUM'))
            checksum = Path(str(retained)+'.CHECKSUM').read_bytes()
            digest = expected(checksum, name)
            if (sha(retained) != digest or digest != value['sha256']
                    or retained.stat().st_size != value['bytes']
                    or hashlib.sha256(checksum).hexdigest() != value['official_checksum_sha256']):
                raise ValueError('Public vault bytes/checksum differ')
            target = SOURCE/name
            sidecar = Path(str(target)+'.CHECKSUM')
            ordinary(target)
            ordinary(sidecar)
            if target.exists() and sha(target) != digest:
                raise ValueError('Never overwrite a conflicting cache ZIP')
            if sidecar.exists() and sidecar.read_bytes() != checksum:
                raise ValueError('Never overwrite a conflicting cache checksum')
            linked = not target.exists()
            if linked:
                os.link(retained, target)
            if not sidecar.exists():
                with sidecar.open('xb') as stream:
                    stream.write(checksum)
            entries.append(dict(name=name, sha256=digest, linked=linked,
                                vault_record_sha256=sha(record)))
        path = OUT/(label+'-public-archive-restore.json')
        if sha(Path(__file__)) != tool_sha:
            raise ValueError('Public archive restore code changed')
        record_new(path, dict(format='official-public-cache-restore-v1', label=label,
                  vault_tool_sha256=tool_sha, records=entries,
                  scope='Original ZIP bytes only; no derived bins, runtime/model/source/clock/UID change.',
                  producer_concurrency='No Coin producer at restore; next economic process remains serial.'))
        return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('watch', 'restore'))
    parser.add_argument('--label')
    args = parser.parse_args()
    if args.mode == 'watch':
        watch()
    else:
        if not args.label:
            parser.error('restore requires a unique receipt label')
        restore(args.label)


if __name__ == '__main__':
    main()
