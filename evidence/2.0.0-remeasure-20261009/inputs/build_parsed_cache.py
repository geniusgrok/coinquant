"""Preparse qualified print ZIPs with the immutable historical parser only.

No strategy, venue, session, account state or network request is executed.
The frozen loader consumes the .bin.gz files; metadata is independent audit
evidence, not a validation feature claimed for that loader.
"""
import argparse
import array
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
import fcntl
import gzip
import hashlib
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import signal
import sys
import tempfile
import time
import zipfile


PARSER_SHA = '7ab3a31b7e02cec0c95802a309b7c0c0c0f66b596e6fc96afedef13e192557ae'
FLOOR = 2 * 1024 ** 3
HEADROOM = 64 * 1024 ** 2
BLOCK = 1024 ** 2
ABI = dict(byteorder=sys.byteorder, header_typecode='q', column_typecodes=['q'] * 4,
           itemsize=array.array('q').itemsize, columns=['time_ms', 'agg_id', 'price_1e8', 'qty_1e8'])


def hashed(stream):
    size = 0
    digest = hashlib.sha256()
    for block in iter(lambda: stream.read(BLOCK), b''):
        size += len(block)
        digest.update(block)
    return size, digest.hexdigest()


def file_hash(path):
    with Path(path).open('rb') as stream:
        return hashed(stream)[1]


def identity(path):
    stat = Path(path).stat()
    return dict(device=stat.st_dev, inode=stat.st_ino, bytes=stat.st_size, mtime_ns=stat.st_mtime_ns)


def atomic_json(path, value):
    temporary = Path(str(path) + f'.{os.getpid()}.tmp')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def qualify(row, inputs):
    path = inputs / row['relative_path']
    sidecar = Path(str(path) + '.CHECKSUM')
    if not path.is_file() or not sidecar.is_file():
        return None  # Not downloaded yet; never classified as a missing series.
    before = identity(path)
    if before['bytes'] != row['bytes'] or sidecar.read_text() != row['sidecar_text']:
        raise ValueError('registered source size or original CHECKSUM differs: ' + path.name)
    if file_hash(path) != row['sha256'] or identity(path) != before:
        raise ValueError('registered raw source SHA or file identity differs: ' + path.name)
    # C-level newline counting bounds the original parser's binary size without
    # reimplementing its CSV conversion or sorting. Header/blank lines overbound.
    with zipfile.ZipFile(path) as archive:
        members = [item for item in archive.infolist() if not item.is_dir()]
        if len(members) != 1:
            raise ValueError('unexpected print ZIP members')
        count = 1
        with archive.open(members[0]) as stream:
            for block in iter(lambda: stream.read(BLOCK), b''):
                count += block.count(b'\n')
    return dict(row=row, source_identity=before, row_bound=count,
                bin_bound=ABI['itemsize'] * (1 + 4 * count), csv_bytes=members[0].file_size)


def verify_pack(path, record):
    if (record['parser_sha256'] != PARSER_SHA or record['array_abi'] != ABI
            or record['bin_bytes'] != ABI['itemsize'] * (1 + 4 * record['count'])
            or path.stat().st_size != record['packed_bytes']
            or file_hash(path) != record['packed_sha256']):
        raise ValueError('existing parsed pack identity differs: ' + path.name)
    with gzip.open(path, 'rb') as stream:
        size, digest = hashed(stream)
    if (size, digest) != (record['bin_bytes'], record['bin_sha256']):
        raise ValueError('parsed pack does not reconstruct the recorded binary')


def build(job, inputs_text, output_text, parser_text, runtime_text):
    started = time.monotonic()
    inputs, output, parser = Path(inputs_text), Path(output_text), Path(parser_text)
    row = job['row']
    source = inputs / row['relative_path']
    name = source.name
    packed = output / f'{name}.{row["sha256"]}.bin.gz'
    metadata = Path(str(packed) + '.json')
    if file_hash(parser) != PARSER_SHA or identity(source) != job['source_identity']:
        raise ValueError('parser or qualified source changed before parsing')
    if packed.is_file() and metadata.is_file():
        record = json.loads(metadata.read_text())
        if record['raw_sha256'] != row['sha256'] or record['raw_bytes'] != row['bytes']:
            raise ValueError('existing cache refers to another original')
        verify_pack(packed, record)
        return dict(status='reused-verified', name=name, seconds=time.monotonic() - started, record=record)
    sys.path.insert(0, runtime_text)
    spec = importlib.util.spec_from_file_location('immutable_print_parser', parser)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    day = int(datetime.strptime(name.removeprefix('BTCUSDT-aggTrades-').removesuffix('.zip'),
                                '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp() * 1000)
    private_root = output.parent / 'worker-temporary'
    private_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f'worker-{os.getpid()}-', dir=private_root) as temporary:
        private = Path(temporary)
        selected = private / 'prints'
        selected.mkdir()
        for suffix in ('', '.CHECKSUM'):
            (selected / (name + suffix)).symlink_to(Path(str(source) + suffix))
        if shutil.disk_usage(output).free < FLOOR + HEADROOM + 2 * job['bin_bound']:
            raise OSError('disk reserve before parse; no original removed')
        tape = module.TradePrints(selected)
        columns = tape._load(day)  # The exact frozen parser writes the original binary.
        if (columns is None or len(columns) != 4 or any(type(a) is not array.array
                or a.typecode != 'q' or a.itemsize != ABI['itemsize'] for a in columns)):
            raise ValueError('original parser did not return four native q arrays')
        count = len(columns[0])
        if (not 0 < count <= job['row_bound'] or any(len(a) != count for a in columns)
                or columns[0][0] < day or columns[0][-1] >= day + 86400000
                or tape.loaded.get(name) != row['sha256']):
            raise ValueError('original parser row count, date boundary or raw identity differs')
        binary = private / 'prints-cache' / f'{name}.{row["sha256"]}.bin'
        if binary.stat().st_size != ABI['itemsize'] * (1 + 4 * count):
            raise ValueError('original parser binary size differs from its q-array count')
        temporary_pack = private / 'verified.bin.gz'
        digest = hashlib.sha256()
        with binary.open('rb') as source_stream, temporary_pack.open('wb') as raw_target:
            with gzip.GzipFile(filename='', mode='wb', fileobj=raw_target, compresslevel=3, mtime=0) as target:
                for block in iter(lambda: source_stream.read(BLOCK), b''):
                    if shutil.disk_usage(output).free < FLOOR + 16 * BLOCK:
                        raise OSError('disk reserve during compression; private temporary output discarded')
                    digest.update(block)
                    target.write(block)
            raw_target.flush()
            os.fsync(raw_target.fileno())
        record = dict(format='original-tradeprints-cache-v1', raw_name=name,
            raw_relative_path=row['relative_path'], raw_sha256=row['sha256'], raw_bytes=row['bytes'],
            raw_identity=job['source_identity'], original_checksum_sha256=file_hash(Path(str(source) + '.CHECKSUM')),
            parser_sha256=PARSER_SHA, bin_bytes=binary.stat().st_size, bin_sha256=digest.hexdigest(),
            packed_bytes=temporary_pack.stat().st_size, packed_sha256=file_hash(temporary_pack),
            array_abi=ABI, count=count, day_ms=day,
            first={key: values[0] for key, values in zip(ABI['columns'], columns)},
            last={key: values[-1] for key, values in zip(ABI['columns'], columns)},
            csv_uncompressed_bytes=job['csv_bytes'], gzip_compresslevel=3,
            builder_sha256=file_hash(__file__), python=sys.version.split()[0],
            verification='full gzip reconstruction matches original parser binary SHA and length')
        verify_pack(temporary_pack, record)
        if identity(source) != job['source_identity'] or file_hash(parser) != PARSER_SHA:
            raise ValueError('source or parser changed during parsing')
        if packed.exists():
            # A prior interruption may have published the complete pack first.
            if file_hash(packed) != record['packed_sha256']:
                raise ValueError('preserve existing cache with a different compressed identity')
        else:
            os.link(temporary_pack, packed)  # Never overwrite another worker's artifact.
        atomic_json(metadata, record)
    return dict(status='built-verified', name=name, seconds=time.monotonic() - started, record=record)


def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs-root', type=Path, default=here)
    parser.add_argument('--tooling', type=Path, default=here.parent / 'coinquant-remeasure-tooling')
    parser.add_argument('--runtime-root', type=Path, default=here.parent / 'coinquant-remeasure-2.0.0/current')
    parser.add_argument('--workers', type=int, choices=(2, 3), default=2)
    parser.add_argument('--watch', action='store_true')
    args = parser.parse_args()
    inputs = args.inputs_root.resolve()
    frozen_parser = (args.tooling / 'research/session_market.py').resolve()
    if file_hash(frozen_parser) != PARSER_SHA or ABI['itemsize'] != 8:
        raise ValueError('exact frozen parser and 64-bit q-array ABI required')
    manifest = inputs / 'INPUT_MANIFEST.json'
    registered = json.loads(manifest.read_text())['files']
    rows = sorted((row for row in registered if row.get('group') == 'prints'), key=lambda row: row['name'])
    output = inputs / 'shared-parsed-cache' / PARSER_SHA
    output.mkdir(parents=True, exist_ok=True)
    stop = [False]
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda _signum, _frame: stop.__setitem__(0, True))
    lock = (inputs / '.parsed-cache-builder.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    done, failed, inspected, futures = set(), {}, {}, {}
    journal = (inputs / 'PARSED_CACHE_PROGRESS.jsonl').open('a', encoding='utf-8')
    last_status = 0
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=multiprocessing.get_context('spawn')) as pool:
        while True:
            now = time.monotonic()
            ready, _ = wait(futures, timeout=0, return_when=FIRST_COMPLETED) if futures else (set(), set())
            for future in ready:
                name, reserved = futures.pop(future)
                try:
                    result = future.result()
                    done.add(name)
                except Exception as exc:
                    result = dict(status='failed', name=name, error_type=type(exc).__name__, reason=str(exc))
                    failed[name] = result
                    if isinstance(exc, OSError):
                        stop[0] = True
                journal.write(json.dumps(result, sort_keys=True) + '\n')
                journal.flush()
                os.fsync(journal.fileno())
                print(json.dumps({k: v for k, v in result.items() if k != 'record'}), flush=True)
            waiting_for_download = 0
            space_blocked = False
            active_names = {name for name, _ in futures.values()}
            # Preserve capacity for every registered original still downloading.
            raw_remaining = sum(max(0, row['bytes'] - (inputs / row['relative_path']).stat().st_size)
                                if (inputs / row['relative_path']).is_file() else row['bytes'] for row in registered)
            for row in rows:
                name = row['name']
                if name in done or name in failed or name in active_names:
                    continue
                if not (inputs / row['relative_path']).is_file() or not Path(str(inputs / row['relative_path']) + '.CHECKSUM').is_file():
                    waiting_for_download += 1
                    continue
                if stop[0] or len(futures) >= args.workers:
                    continue
                try:
                    job = inspected.get(name)
                    if job is None:
                        job = qualify(row, inputs)
                        if job is None:
                            continue
                        inspected[name] = job
                    reserve = 2 * job['bin_bound'] + HEADROOM
                    available = shutil.disk_usage(output).free
                    if available <= FLOOR + HEADROOM + raw_remaining + reserve + sum(size for _, size in futures.values()):
                        space_blocked = True
                        continue
                    future = pool.submit(build, job, str(inputs), str(output), str(frozen_parser), str(args.runtime_root.resolve()))
                    futures[future] = (name, reserve)
                    active_names.add(name)
                except Exception as exc:
                    failed[name] = dict(status='qualification-failed', name=name, error_type=type(exc).__name__, reason=str(exc))
                    journal.write(json.dumps(failed[name]) + '\n')
                    journal.flush()
                    print(json.dumps(failed[name]), flush=True)
            if now - last_status >= 15 or stop[0] or len(done) + len(failed) == len(rows):
                status = dict(status='stopping' if stop[0] else 'working', pid=os.getpid(),
                    parser_sha256=PARSER_SHA, builder_sha256=file_hash(__file__), input_manifest_sha256=file_hash(manifest),
                    registered_print_days=len(rows), verified_cache_days=len(done), failed_days=len(failed),
                    waiting_for_download=waiting_for_download, active=sorted(name for name, _ in futures.values()),
                    disk_free_bytes=shutil.disk_usage(output).free, floor_bytes=FLOOR,
                    reserved_future_original_bytes=raw_remaining, space_blocked=space_blocked,
                    updated_at=datetime.now(timezone.utc).isoformat())
                atomic_json(inputs / 'PARSED_CACHE_STATUS.json', status)
                print(json.dumps(status), flush=True)
                last_status = now
            if not futures and (stop[0] or len(done) + len(failed) == len(rows) or not args.watch or space_blocked):
                break
            time.sleep(1)
    journal.close()
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
