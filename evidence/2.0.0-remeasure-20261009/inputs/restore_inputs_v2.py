"""Restore v2: archived sidecar identity, exact public body, resumable verified transfers."""
import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
DOWNLOADER_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
RESERVE = 2 * 1024**3
CHUNK = 1024 * 1024


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save_json(path, value):
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def download(item, progress):
    started = time.monotonic()
    target = ROOT / item['relative_path']
    target.parent.mkdir(parents=True, exist_ok=True)
    expected, length = item['sha256'], item['bytes']
    result = dict(name=item['name'], kind=item['kind'], relative_path=item['relative_path'],
                  original_path=item['original_path'], url=item['url'], sha256=expected,
                  bytes=length, group=item['group'], downloader_sha256=DOWNLOADER_SHA256)
    sidecar = item.get('sidecar_text')
    partial = target.with_name(target.name + '.part')
    if target.exists():
        if target.stat().st_size != length or sha(target) != expected:
            return dict(result, status='failed', error='Existing final file differs from frozen identity')
        if sidecar is not None:
            check = target.with_name(target.name + '.CHECKSUM')
            if check.exists() and check.read_text() != sidecar:
                return dict(result, status='failed', error='Existing sidecar differs from frozen identity')
            if not check.exists():
                check.write_text(sidecar)
        return dict(result, status='verified-existing', seconds=time.monotonic() - started)
    try:
        if sidecar is not None:
            if sidecar.split() != [expected, item['name']]:
                raise ValueError('Archived CHECKSUM differs from frozen manifest identity')
            result['archived_sidecar_sha256'] = hashlib.sha256(sidecar.encode()).hexdigest()
        for attempt in range(3):
            offset = partial.stat().st_size if partial.exists() else 0
            if offset > length:
                raise ValueError('Partial file exceeds frozen length')
            if offset == length:
                break
            if shutil.disk_usage(ROOT).free < length - offset + RESERVE:
                raise ValueError('Insufficient free disk above the 2 GiB reserve')
            headers = {'Accept-Encoding': 'identity'}
            if offset:
                headers['Range'] = f'bytes={offset}-'
            try:
                with urlopen(Request(item['url'], headers=headers), timeout=30) as response:
                    if response.status == 206:
                        match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', response.headers.get('Content-Range', ''))
                        if not match or tuple(map(int, match.groups())) != (offset, length - 1, length):
                            raise ValueError('Invalid resumed Content-Range')
                    elif response.status == 200:
                        # Some public mirrors ignore Range. Restart this unverified partial.
                        offset = 0
                    else:
                        raise ValueError(f'Unexpected transfer status {response.status}')
                    declared = response.headers.get('Content-Length')
                    if declared is not None and int(declared) != length - offset:
                        raise ValueError('Content-Length differs from frozen length')
                    digest = hashlib.sha256()
                    if offset:
                        with partial.open('rb') as prefix:
                            for block in iter(lambda: prefix.read(CHUNK), b''):
                                digest.update(block)
                    count = offset
                    with partial.open('ab' if offset else 'wb') as output:
                        while block := response.read(CHUNK):
                            if count + len(block) > length:
                                raise ValueError('Transfer exceeds frozen length')
                            output.write(block)
                            digest.update(block)
                            count += len(block)
                            progress[item['relative_path']] = count
                            if shutil.disk_usage(ROOT).free < RESERVE:
                                raise ValueError('Download paused to preserve 2 GiB free disk')
                        output.flush()
                        os.fsync(output.fileno())
                    if count != length:
                        raise OSError('Incomplete response; verified-length partial retained')
                    if digest.hexdigest() != expected:
                        raise ValueError('Downloaded SHA-256 differs from frozen source')
                break
            except (URLError, TimeoutError, OSError) as exc:
                if isinstance(exc, HTTPError) or attempt == 2:
                    raise
                time.sleep(1)
        if partial.stat().st_size != length or sha(partial) != expected:
            raise ValueError('Final independent file readback differs from frozen source')
        if item.get('git_blob_sha'):
            digest = hashlib.sha1(b'blob ' + str(length).encode() + b'\0')
            with partial.open('rb') as stream:
                for block in iter(lambda: stream.read(CHUNK), b''):
                    digest.update(block)
            if digest.hexdigest() != item['git_blob_sha']:
                raise ValueError('Git object ID differs from frozen source')
        os.replace(partial, target)
        if sidecar is not None:
            target.with_name(target.name + '.CHECKSUM').write_text(sidecar)
        return dict(result, status='downloaded-verified', seconds=time.monotonic() - started)
    except Exception as exc:
        return dict(result, status='failed', error=f'{type(exc).__name__}: {exc}',
                    partial_bytes=partial.stat().st_size if partial.exists() else 0,
                    seconds=time.monotonic() - started)
    finally:
        progress.pop(item['relative_path'], None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--groups', default='fx,4h,funding')
    parser.add_argument('--workers', type=int, default=16)
    parser.add_argument('--summary', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.workers <= 16:
        parser.error('workers must be 1..16')
    manifest_path = ROOT / 'INPUT_MANIFEST.json'
    manifest = json.loads(manifest_path.read_text())
    for identity in manifest['source_files']:
        source = ROOT / identity['relative_path']
        if source.stat().st_size != identity['bytes'] or sha(source) != identity['sha256']:
            raise ValueError('Frozen manifest source changed')
    groups = set(args.groups.split(','))
    allowed = {'fx', 'market', 'prints', '4h', 'funding', 'trade_1m', 'mark_1m', 'all'}
    if not groups <= allowed:
        parser.error('unknown input group')
    selected = [item for item in manifest['files'] if 'all' in groups or item['group'] in groups
                or 'market' in groups and item['group'] in {'4h', 'funding', 'trade_1m', 'mark_1m'}]
    summary = dict(groups=sorted(groups), files=len(selected), bytes=sum(x['bytes'] for x in selected),
                   manifest_sha256=sha(manifest_path), downloader_sha256=DOWNLOADER_SHA256,
                   workers=args.workers, identity_policy='frozen-archived-sidecar-plus-exact-official-body',
                   disk_free_bytes=shutil.disk_usage(ROOT).free)
    print(json.dumps(summary), flush=True)
    if args.summary:
        return
    lock = (ROOT / '.restore.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    progress, results = {}, []
    started = last = time.monotonic()
    with (ROOT / 'DOWNLOAD_PROGRESS_V2.jsonl').open('a') as ledger, ThreadPoolExecutor(args.workers) as pool:
        remaining = {pool.submit(download, item, progress) for item in selected}
        while remaining:
            done, remaining = wait(remaining, timeout=15, return_when=FIRST_COMPLETED)
            for future in done:
                result = future.result()
                results.append(result)
                ledger.write(json.dumps(result, ensure_ascii=False) + '\n')
                ledger.flush()
                if result['status'] == 'failed':
                    print(json.dumps(result, ensure_ascii=False), flush=True)
            now = time.monotonic()
            if now - last >= 20 or not remaining:
                verified = sum(r['bytes'] for r in results if r['status'] != 'failed')
                print(json.dumps(dict(completed=len(results), total=len(selected), verified_bytes=verified,
                                      active_partial_bytes=sum(progress.values()), seconds=round(now-started, 2),
                                      failures=sum(r['status'] == 'failed' for r in results),
                                      free_bytes=shutil.disk_usage(ROOT).free)), flush=True)
                last = now
    receipt = dict(**summary, complete=all(r['status'] != 'failed' for r in results),
                   seconds=time.monotonic()-started, results=results)
    save_json(ROOT / 'DOWNLOAD_RECEIPT.json', receipt)
    print(json.dumps(dict(receipt=str(ROOT / 'DOWNLOAD_RECEIPT.json'), complete=receipt['complete'],
                          failures=sum(r['status'] == 'failed' for r in results))), flush=True)
    raise SystemExit(0 if receipt['complete'] else 2)


if __name__ == '__main__':
    main()
