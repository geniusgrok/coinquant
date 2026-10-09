"""Restore immutable public ZIP bytes from an existing qualified-input manifest."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.request

BASE = 'https://data.binance.vision/data/futures/um'
ROOT = Path(__file__).resolve().parents[1]
META = ROOT / 'github-archive-recovered/data/qualified-market-metadata.json'
DEST = ROOT / 'public-inputs'


def source(path):
    name = Path(path).name
    if 'aggTrades' in name:
        return f'{BASE}/daily/aggTrades/BTCUSDT/{name}', DEST / 'prints' / name
    if 'fundingRate' in name:
        return f'{BASE}/monthly/fundingRate/BTCUSDT/{name}', DEST / 'market/funding' / name
    period = 'daily' if '/daily/' in path else 'monthly'
    kind = 'markPriceKlines' if '/mark/' in path else 'klines'
    interval = '4h' if '/4h/' in path else '1m'
    relative = path.split('/coinquant-market/', 1)[1]
    return f'{BASE}/{period}/{kind}/BTCUSDT/{interval}/{name}', DEST / 'market' / relative


def restore(item):
    start = time.monotonic()
    url, target = source(item['original_path'])
    expected = item['sha256']
    target.parent.mkdir(parents=True, exist_ok=True)
    result = dict(path=str(target), original_path=item['original_path'], sha256=expected)
    if target.exists():
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if digest == expected:
            return dict(result, status='verified-existing', bytes=target.stat().st_size, seconds=time.monotonic()-start)
        raise ValueError('existing input hash mismatch: ' + str(target))
    partial = target.with_name(target.name + '.partial')
    try:
        with urllib.request.urlopen(url+'.CHECKSUM', timeout=45) as response:
            sidecar = response.read(4096)
        if sidecar.decode().split()[0] != expected:
            raise ValueError('official checksum differs from immutable manifest')
        digest = hashlib.sha256()
        total = 0
        with urllib.request.urlopen(url, timeout=90) as response, partial.open('xb') as output:
            while block := response.read(1024*1024):
                output.write(block)
                digest.update(block)
                total += len(block)
        if digest.hexdigest() != expected or total != item['bytes']:
            raise ValueError('downloaded bytes differ from immutable manifest')
        partial.rename(target)
        target.with_name(target.name+'.CHECKSUM').write_bytes(sidecar)
        return dict(result,status='downloaded-verified',bytes=total,seconds=time.monotonic()-start)
    except Exception as error:
        if partial.exists():
            partial.unlink()
        return dict(result,status='failed',error=type(error).__name__+': '+str(error),seconds=time.monotonic()-start)


def main():
    qualified = json.loads(META.read_text())['qualification_maps']['files']
    plan = [dict(original_path=p,sha256=v['original_content_sha256'],bytes=v['metadata']['bytes']) for p,v in qualified.items()]
    DEST.mkdir(exist_ok=True)
    (DEST/'DOWNLOAD_PLAN.json').write_text(json.dumps(plan,indent=2)+'\n')
    sample = '--sample' in sys.argv
    if sample:
        plan = [next(item for item in plan if item['original_path'].endswith('BTCUSDT-aggTrades-2026-09-18.zip'))]
    started = time.monotonic()
    last = started
    results = []
    done_bytes = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=1 if sample else 8) as pool:
        for result in pool.map(restore,plan):
            results.append(result)
            if result['status'] == 'downloaded-verified':
                done_bytes += result['bytes']
            now=time.monotonic()
            if now-last>25 or result['status']=='failed':
                print(json.dumps(dict(completed=len(results),total=len(plan),verified_download_bytes=done_bytes,seconds=now-started,last_status=result['status'],error=result.get('error'))),flush=True)
                last=now
    receipt = dict(complete=all(r['status']!='failed' for r in results),sample=sample,source_metadata_sha256=hashlib.sha256(META.read_bytes()).hexdigest(),seconds=time.monotonic()-started,verified_download_bytes=done_bytes,results=results)
    name='SAMPLE_TRANSFER.json' if sample else 'DOWNLOAD_RECEIPT.json'
    (DEST/name).write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(receipt=str(DEST/name),complete=receipt['complete'],files=len(results),bytes=done_bytes,seconds=receipt['seconds'],failures=sum(r['status']=='failed' for r in results))),flush=True)


if __name__ == '__main__':
    main()
