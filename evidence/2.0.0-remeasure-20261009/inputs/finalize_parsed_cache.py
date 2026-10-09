"""Inventory and independently stream-verify completed immutable parser caches.

Reads finished gzip/sidecar files only. It does not import the producer, parse
CSV, create uncompressed caches, change account data, or delete raw inputs.
"""
import argparse
import array
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
import zlib


FLOOR = 2 * 1024 ** 3
BLOCK = 1024 ** 2
PARSER_SHA = '7ab3a31b7e02cec0c95802a309b7c0c0c0f66b596e6fc96afedef13e192557ae'
BUILDER_SHA = '2d10eccfa50ad30760b9bdeaa9b300e667cf8005675e5e059973490e8e959dcd'
INPUT_SHA = 'a808f1333b4fc18a5a65afe883804795b9286c117e1cc38a4b2a252a90064e82'
ABI = {'byteorder': sys.byteorder, 'header_typecode': 'q',
       'column_typecodes': ['q'] * 4, 'itemsize': array.array('q').itemsize,
       'columns': ['time_ms', 'agg_id', 'price_1e8', 'qty_1e8']}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(BLOCK), b''):
            digest.update(block)
    return digest.hexdigest()


def identity(path):
    stat = Path(path).stat()
    return {'device': stat.st_dev, 'inode': stat.st_ino,
            'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns}


def artifact(path, root):
    return {'relative_path': str(path.relative_to(root)),
            'bytes': path.stat().st_size, 'sha256': sha(path)}


def save(path, value, replace=False):
    temporary = Path(str(path) + f'.{os.getpid()}.tmp')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    try:
        if replace:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def verify_stream(path, row):
    """One compressed pass; bounded decompression, hashes and native-q edges."""
    before = identity(path)
    require(before == row['packed_identity'], 'packed file changed before verification')
    record = row['parser_record']
    count, width = record['count'], ABI['itemsize']
    positions = {0: ('count', None)}
    for index, name in enumerate(ABI['columns']):
        positions[width * (1 + index * count)] = ('first', name)
        positions[width * ((index + 1) * count)] = ('last', name)
    edges = {offset: bytearray() for offset in positions}
    packed_hash, bin_hash = hashlib.sha256(), hashlib.sha256()
    packed_bytes, bin_bytes = 0, 0
    decoder = zlib.decompressobj(zlib.MAX_WBITS + 16)

    def consume(data):
        nonlocal bin_bytes
        start, end = bin_bytes, bin_bytes + len(data)
        bin_hash.update(data)
        for offset in positions:
            left, right = max(offset, start), min(offset + width, end)
            if left < right:
                edges[offset].extend(data[left - start:right - start])
        bin_bytes = end

    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(BLOCK), b''):
            packed_bytes += len(block)
            packed_hash.update(block)
            pending = block
            while pending:
                consume(decoder.decompress(pending, BLOCK))
                pending = decoder.unconsumed_tail
            require(not decoder.unused_data, 'unexpected trailing or extra gzip member')
        consume(decoder.flush())
    require(decoder.eof, 'incomplete gzip stream')
    require(identity(path) == before, 'packed file changed during verification')
    require((packed_bytes, packed_hash.hexdigest()) ==
            (record['packed_bytes'], record['packed_sha256']), 'packed SHA or size mismatch')
    require((bin_bytes, bin_hash.hexdigest()) ==
            (record['bin_bytes'], record['bin_sha256']), 'reconstructed bin SHA or size mismatch')
    values = {'first': {}, 'last': {}}
    for offset, (kind, name) in positions.items():
        require(len(edges[offset]) == width, 'incomplete native-q field')
        value = int.from_bytes(edges[offset], byteorder=ABI['byteorder'], signed=True)
        if name is None:
            require(value == count, 'binary row-count header mismatch')
        else:
            values[kind][name] = value
    require(values['first'] == record['first'] and values['last'] == record['last'],
            'binary array boundary mismatch')
    return {'raw_name': record['raw_name'], 'passed': True,
            'packed_sha256': packed_hash.hexdigest(), 'packed_bytes': packed_bytes,
            'bin_sha256': bin_hash.hexdigest(), 'bin_bytes': bin_bytes,
            'count': count, 'array_abi': ABI, **values}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs-root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--builder-session', type=int, required=True)
    parser.add_argument('--builder-exit-code', type=int, required=True)
    args = parser.parse_args()
    root = args.inputs_root.resolve()
    tooling = root.parent / 'coinquant-remeasure-tooling/research'
    require(args.builder_exit_code == 0, 'builder normal exit must have been observed')
    require(ABI['byteorder'] == 'little' and ABI['itemsize'] == 8, 'expected frozen native-q ABI')
    require(shutil.disk_usage(root).free >= FLOOR, 'disk reserve below 2 GiB')
    output = root / 'shared-parsed-cache' / PARSER_SHA
    inputs = root / 'INPUT_MANIFEST.json'
    builder = root / 'build_parsed_cache.py'
    frozen_parser = tooling / 'session_market.py'
    require((sha(inputs), sha(builder), sha(frozen_parser)) ==
            (INPUT_SHA, BUILDER_SHA, PARSER_SHA), 'input/parser/builder source identity changed')
    registered = sorted((row for row in json.loads(inputs.read_text())['files']
                         if row['group'] == 'prints'), key=lambda row: row['name'])
    status_path, journal_path = root / 'PARSED_CACHE_STATUS.json', root / 'PARSED_CACHE_PROGRESS.jsonl'
    status = json.loads(status_path.read_text())
    journal = [json.loads(line) for line in journal_path.read_text().splitlines()]
    counts = dict(Counter(row['status'] for row in journal))
    require(len(registered) == len(journal) == 773 and counts == {'built-verified': 773},
            'expected exactly 773 successful build records and no failures')
    by_name = {row['name']: row for row in journal}
    require(len(by_name) == 773 and set(by_name) == {row['name'] for row in registered},
            'journal differs from registered print dates')
    require(status['verified_cache_days'] == status['registered_print_days'] == 773
            and status['failed_days'] == status['waiting_for_download'] == 0
            and status['active'] == [], 'builder terminal counts are incomplete')
    require((status['parser_sha256'], status['builder_sha256'], status['input_manifest_sha256']) ==
            (PARSER_SHA, BUILDER_SHA, INPUT_SHA), 'builder terminal source identity differs')
    files, expected_paths = [], set()
    for source in registered:
        raw = root / source['relative_path']
        original_checksum = Path(str(raw) + '.CHECKSUM')
        packed = output / f'{source["name"]}.{source["sha256"]}.bin.gz'
        sidecar = Path(str(packed) + '.json')
        expected_paths.update((packed, sidecar))
        record = json.loads(sidecar.read_text())
        require(record == by_name[source['name']]['record'], 'sidecar differs from build journal')
        require(record['raw_name'] == source['name']
                and record['raw_relative_path'] == source['relative_path']
                and record['raw_sha256'] == source['sha256']
                and record['raw_bytes'] == raw.stat().st_size == source['bytes'], 'raw input binding differs')
        require(identity(raw) == record['raw_identity'], 'original ZIP metadata changed after qualification')
        require(original_checksum.read_text() == source['sidecar_text']
                and sha(original_checksum) == record['original_checksum_sha256'], 'original CHECKSUM changed')
        require(record['parser_sha256'] == PARSER_SHA and record['builder_sha256'] == BUILDER_SHA
                and record['array_abi'] == ABI and record['count'] > 1
                and record['bin_bytes'] == 8 * (1 + 4 * record['count']), 'parser/builder/ABI/count differs')
        require(packed.stat().st_size == record['packed_bytes'], 'packed file size differs')
        files.append({'raw_current_identity': identity(raw), 'parser_record': record,
                      'sidecar': artifact(sidecar, root),
                      'packed_relative_path': str(packed.relative_to(root)),
                      'packed_identity': identity(packed)})
    require(set(output.iterdir()) == expected_paths, 'cache directory contains unexpected or absent files')
    manifest = {
        'format': 'coinquant-original-parser-cache-manifest-v1', 'created_at_utc': utc(),
        'registered_print_days': 773, 'cache_days': len(files), 'builder_failures': 0,
        'input_manifest': artifact(inputs, root), 'parser_sha256': PARSER_SHA,
        'builder': artifact(builder, root), 'array_abi': ABI,
        'frozen_loader_sha256': sha(tooling / 'data_loader.py'),
        'loader_scope': 'Frozen data_loader.setup/Prints._load does not read these sidecars or verify packed SHA. It checks original ZIP provenance through registered qualified metadata/CHECKSUM, or the original raw hash path when needed, and uses the raw digest plus parser digest to locate the cache. Packed/bin verification here is independent.',
        'builder_completion': {'session_id': args.builder_session, 'exit_code': args.builder_exit_code,
            'exit_evidence': 'Observed completed tools.write_stdin result; terminal status stage label remains working.',
            'journal': artifact(journal_path, root), 'journal_status_counts': counts,
            'terminal_status': artifact(status_path, root), 'terminal_status_snapshot': status},
        'totals': {key: sum(row['parser_record'][key] for row in files)
                   for key in ('raw_bytes', 'packed_bytes', 'bin_bytes', 'count')},
        'raw_inputs_preserved': True, 'files': files,
    }
    manifest_path = root / 'CACHE_MANIFEST.json'
    save(manifest_path, manifest)
    validation = {
        'format': 'coinquant-original-parser-cache-validation-v1', 'started_at_utc': utc(),
        'manifest': artifact(manifest_path, root), 'validator': artifact(Path(__file__).resolve(), root),
        'input_manifest_sha256': INPUT_SHA, 'parser_sha256': PARSER_SHA, 'builder_sha256': BUILDER_SHA,
        'scope': 'Independent one-pass SHA256 of actual gzip bytes and bounded streaming decompression; SHA256/size of original-format binary, native-q header count, ABI and every column first/last value; gzip EOF/CRC; stable packed/sidecar/original identities.',
        'raw_content_rehashed_in_this_validation': False, 'csv_reparsed': False,
        'producer_imported_or_modified': False, 'accounts_accessed': False,
        'uncompressed_files_created': False, 'raw_inputs_deleted': False,
        'loader_validates_sidecars_or_packed_sha': False, 'disk_floor_bytes': FLOOR,
        'minimum_observed_disk_free_bytes': shutil.disk_usage(root).free,
        'passed': False, 'verified_days': 0, 'failures': [], 'files': [],
    }
    started = time.monotonic()
    try:
        with (root / 'CACHE_VALIDATION_PROGRESS.jsonl').open('x', encoding='utf-8') as progress:
            for row in files:
                free = shutil.disk_usage(root).free
                validation['minimum_observed_disk_free_bytes'] = min(free, validation['minimum_observed_disk_free_bytes'])
                require(free >= FLOOR, 'disk reserve below 2 GiB; no original inputs removed')
                verified = verify_stream(root / row['packed_relative_path'], row)
                require(artifact(root / row['sidecar']['relative_path'], root) == row['sidecar'], 'sidecar changed during validation')
                require(identity(root / row['parser_record']['raw_relative_path']) == row['raw_current_identity'], 'original changed during validation')
                validation['files'].append(verified)
                validation['verified_days'] += 1
                progress.write(json.dumps(verified, sort_keys=True) + '\n')
                progress.flush()
                if validation['verified_days'] % 25 == 0 or validation['verified_days'] == 773:
                    update = {key: validation[key] for key in ('verified_days', 'minimum_observed_disk_free_bytes')}
                    update.update(updated_at_utc=utc(), elapsed_seconds=time.monotonic() - started)
                    save(root / 'CACHE_VALIDATION_STATUS.json', update, replace=True)
                    print(json.dumps(update), flush=True)
        require(sha(inputs) == INPUT_SHA and sha(builder) == BUILDER_SHA
                and sha(frozen_parser) == PARSER_SHA, 'source identity changed during verification')
        require(artifact(manifest_path, root) == validation['manifest'], 'manifest changed during verification')
        validation['passed'] = validation['verified_days'] == 773
    except (OSError, ValueError, KeyError, zlib.error) as exc:
        validation['failures'].append({'type': type(exc).__name__, 'reason': str(exc)})
    validation['finished_at_utc'] = utc()
    validation['elapsed_seconds'] = time.monotonic() - started
    validation['disk_free_bytes_at_finish'] = shutil.disk_usage(root).free
    save(root / 'CACHE_VALIDATION.json', validation)
    print(json.dumps({key: validation[key] for key in ('passed', 'verified_days', 'failures', 'elapsed_seconds', 'disk_free_bytes_at_finish')}), flush=True)
    return 0 if validation['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
