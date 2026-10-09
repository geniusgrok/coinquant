"""Strict offline receipt comparison; never runs or changes either producer."""
import argparse
import array
import bisect
from collections import Counter, deque
from datetime import date, datetime, timezone
from decimal import Decimal as D
import gzip
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import struct
import sys

ROOT = Path(__file__).resolve().parent
NORMALIZATION = {
    'sqlite_wall_time': ['intents.updated (exchange preparation time required for non-rejected margins)',
                         'observations.recorded_at', 'observations-archive.jsonl[*].recorded_at',
                         'meta[writer_host].value.at'],
    'host_process_identity': 'meta[writer_host].value.pid is checked against receipt.process_pid, then represented as that receipt process',
    'preserved': 'hostname, every other schema/row/meta/payload/result/ledger field, exchange execution timestamps, archive order and duplicates',
    'financial_io_annotation': 'input_qualification_reuse is reported separately; per-process raw verification counters reset at setup and never affect the venue or production decision path',
}


def encoded(value):
    """Independent implementation of the existing explicit checkpoint encoding."""
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is float and math.isfinite(value):
        return {'type': 'float', 'value': repr(value)}
    if isinstance(value, D) and value.is_finite():
        return {'type': 'decimal', 'value': str(value)}
    if type(value) is date:
        return {'type': 'date', 'value': value.isoformat()}
    if type(value) is dict:
        return {'type': 'dict', 'value': [[encoded(k), encoded(v)] for k, v in value.items()]}
    if type(value) in (tuple, list, set, deque):
        return {'type': type(value).__name__, 'value': [encoded(v) for v in (sorted(value) if type(value) is set else value)]}
    raise ValueError('unsupported checkpoint value: ' + type(value).__name__)


def decoded(value):
    if value is None or type(value) in (str, int, bool):
        return value
    assert type(value) is dict and set(value) == {'type', 'value'}
    kind, items = value['type'], value['value']
    if kind in ('decimal', 'float', 'date'):
        result = {'decimal': D, 'float': float, 'date': date.fromisoformat}[kind](items)
        assert kind == 'date' or (result.is_finite() if kind == 'decimal' else math.isfinite(result))
        return result
    if kind == 'dict':
        pairs = [(decoded(k), decoded(v)) for k, v in items]
        result = dict(pairs)
        assert len(result) == len(pairs)
        return result
    assert kind in ('list', 'tuple', 'set', 'deque')
    return {'list': list, 'tuple': tuple, 'set': set, 'deque': deque}[kind](decoded(v) for v in items)


def digest(value):
    return hashlib.sha256(json.dumps(encoded(value), sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def exact_differences(before, after, path='financial'):
    """Keep precise raw differing leaf values; do not apply normalization here."""
    if type(before) is not type(after):
        return [dict(path=path, before=before, after=after)]
    if type(before) is dict:
        differences = []
        for key in sorted(set(before) | set(after)):
            child = path + '[' + json.dumps(key) + ']'
            if key not in before or key not in after:
                differences.append(dict(path=child, before_present=key in before, after_present=key in after,
                                        before=before.get(key), after=after.get(key)))
            else:
                differences.extend(exact_differences(before[key], after[key], child))
        return differences
    if type(before) is list:
        differences = []
        for index in range(max(len(before), len(after))):
            child = path + '[' + str(index) + ']'
            if index >= len(before) or index >= len(after):
                differences.append(dict(path=child, before_present=index < len(before), after_present=index < len(after),
                                        before=before[index] if index < len(before) else None,
                                        after=after[index] if index < len(after) else None))
            else:
                differences.extend(exact_differences(before[index], after[index], child))
        return differences
    return [] if before == after else [dict(path=path, before=before, after=after)]


def source_check(row, arm, spec):
    source = row['source']
    assert source['git_head'] == spec['runtime_heads'][arm]
    assert source['runtime_module'] == str(ROOT / arm / 'coinquant/session.py')
    files = read(ROOT / (arm + '-source-files.json'))
    actual = {str(p.relative_to(ROOT / arm)): sha(p) for p in sorted((ROOT / arm / 'coinquant').glob('*.py'))}
    assert len(actual) == 19 and source['files'] == files == actual
    tools = {str(p.relative_to(ROOT / 'tooling')): sha(p) for p in sorted((ROOT / 'tooling/research').glob('*.py'))}
    assert source['tooling_files'] == tools and len(tools) == 9
    producer = sha(ROOT / 'tooling/driver.py')
    assert source['producer_sha256'] == spec['producer_sha256'] == producer
    packet = dict(actual)
    packet.update({'tooling/' + name: value for name, value in tools.items()})
    packet['tooling/driver.py'] = producer
    assert digest(packet) == source['source_sha256'] == spec['source_sha256_by_arm'][arm]
    assert row['binding']['source_sha256'] == source['source_sha256']
    assert row['binding']['producer_sha256'] == producer
    return source


def input_check(row, count, full, spec):
    inputs = row['inputs']
    schedule = read(spec['schedule'])
    starts = schedule['primary']['starts_ms']
    assert len(starts) == 795 and starts == sorted(set(starts)) and starts[0] == 1577836800000
    assert inputs['starts_ms'] == (starts if full else starts[:count])
    assert sha(spec['schedule']) == inputs['schedule_sha256'] == 'c21b4fcfe3cb12fb062bb01d3c3591aa0ee8c65db9e9afde3c26b1bcdc2ac28e'
    assert hashlib.sha256(json.dumps(starts, separators=(',', ':')).encode()).hexdigest() == schedule['primary']['sha256']
    assert inputs['specification_sha256'] == sha(ROOT / 'spec.json')
    assert inputs['fx_sha256'] == sha(spec['fx'])
    assert inputs['qualified_metadata_sha256'] == spec['qualified_metadata_sha256'] == sha(spec['qualified_metadata'])
    assert inputs['parser_sha256'] == spec['parser_sha256'] == sha(ROOT / 'tooling/research/session_market.py')
    assert inputs['terminal_ms'] == row['terminal_ms'] == spec['terminal_ms'] == 1789862400000
    assert inputs['initial_cny'] == row['initial_cny'] == spec['initial_cny'] == '10000'
    assert inputs['market_root'] == str(Path(spec['market']).resolve())
    assert inputs['prints_root'] == str(Path(spec['prints']).resolve())
    assert inputs['parsed_pack_roots'] == spec['parsed_pack_roots']
    assert inputs['shared_parsed_cache'] == spec['shared_parsed_cache']
    sidecars = {str(p.resolve()): p.read_text() for key in ('prints', 'market') for p in sorted(Path(spec[key]).rglob('*.CHECKSUM'))}
    assert inputs['official_sidecars'] == sidecars
    assert row['binding']['input_sha256'] == digest(inputs)
    assert row['binding']['strategy_sha256'] == digest(row['strategy'])
    assert row['binding']['schedule_sha256'] == inputs['schedule_sha256']
    qualification = read(ROOT / 'input-local-qualification.json')
    original = qualification['derived_original_identities']
    assert original['all_five_exact_original_match']
    for key in ('market_identity_sha256', 'market_values_sha256', 'macro_sha256'):
        assert inputs[key] == original[key]
    for item in qualification['market']['files']:
        path = Path(item['path'])
        stat = path.stat()
        metadata = dict(device=stat.st_dev, inode=stat.st_ino, bytes=stat.st_size, mtime_ns=stat.st_mtime_ns, mode=stat.st_mode, uid=stat.st_uid)
        assert item['content_sha256_verified'] and item['expected_sha256'] == item['actual_sha256']
        assert path.stat().st_size == item['expected_bytes']
        assert Path(item['sidecar_path']).read_text() == item['sidecar_text']
        # Reuse the earlier content qualification only while its metadata is exact.
        if metadata != item['current_metadata']:
            assert sha(path) == item['expected_sha256'], str(path)
    restoration = [json.loads(line) for line in (ROOT / 'input-restore.jsonl').read_text().splitlines()]
    assert len(restoration) == 773 and len({r['name'] for r in restoration}) == 773
    assert sum(r['bytes'] for r in restoration) == 14067765753
    for item in restoration:
        path = Path(spec['prints']) / item['name']
        assert path.stat().st_size == item['bytes']
        checksum, name = Path(str(path) + '.CHECKSUM').read_text().split()
        assert (checksum, name) == (item['sha256'], item['name'])
    registered_prints = {item['name']: item['sha256'] for item in restoration}
    registered_minutes = {item['relative_path']: item['expected_sha256'] for item in qualification['market']['files']}
    assert len(registered_minutes) == 390
    loaded_prints = row['financial']['loaded_print_files']
    loaded_minutes = row['financial']['loaded_minute_files']
    assert loaded_prints and loaded_minutes
    assert all(registered_prints.get(name) == value for name, value in loaded_prints.items()), 'consumed print SHA not an original registered raw input'
    assert all(registered_minutes.get(name) == value for name, value in loaded_minutes.items()), 'consumed minute SHA not an original qualified input'
    if full:
        assert loaded_prints == registered_prints, 'full account did not consume exactly the original 773 raw print inputs'
    for item in qualification['macro']['files']:
        path = ROOT / 'tooling/evidence/real-yield-20260924/alfred' / Path(item['path']).name
        assert sha(path) == item['expected_sha256']
    return dict(input_packet_sha256=digest(inputs), sidecars_sha256=canonical_sha(sidecars),
                qualification_sha256=sha(ROOT / 'input-local-qualification.json'), restoration_sha256=sha(ROOT / 'input-restore.jsonl'),
                consumed_print_count=len(loaded_prints), consumed_print_sha256=canonical_sha(loaded_prints),
                consumed_minute_count=len(loaded_minutes), consumed_minute_sha256=canonical_sha(loaded_minutes),
                consumed_raw_binding='actual frozen loader raw-SHA records match qualified originals; full print map equals all 773 originals',
                raw_body_verification='reuse original content-qualified market metadata and print restoration receipts, linked to actual consumed raw SHA records; changed market files rehashed, full print vault not reread')


def sqlite_check(row, reports):
    state = Path(row['state_directory']).resolve()
    assert state == Path(row['reports']['path']).resolve().parent / 'state'
    path = state / 'intents.sqlite'
    connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    try:
        schema = list(connection.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"))
        tables, raw_tables = {}, {}
        for (name,) in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            quoted = '"' + name.replace('"', '""') + '"'
            columns = [r[1] for r in connection.execute('PRAGMA table_info(' + quoted + ')')]
            order = ','.join('"' + c.replace('"', '""') + '"' for c in columns)
            rows = list(connection.execute('SELECT * FROM ' + quoted + ' ORDER BY ' + order))
            raw_tables[name] = dict(columns=columns, rows=rows)
            canonical = []
            for values in rows:
                values = list(values)
                if name == 'meta' and values[columns.index('key')] == 'writer_host':
                    host = json.loads(values[columns.index('value')])
                    assert set(host) == {'host', 'pid', 'at'} and host['pid'] == row['process_pid']
                    assert isinstance(host['host'], str) and type(host['at']) is float and math.isfinite(host['at'])
                    host['pid'], host['at'] = '<receipt-process>', '<host-wall-time>'
                    values[columns.index('value')] = json.dumps(host, sort_keys=True)
                if name == 'intents':
                    assert values[columns.index('status')] not in ('unknown', 'partial')
                    if values[columns.index('kind')] == 'binance_margin' and values[columns.index('status')] != 'rejected':
                        result = json.loads(values[columns.index('result')])
                        assert type(result.get('prepared_at_ms')) is int, 'legacy margin uses updated as execution boundary; cannot normalize'
                    assert type(values[columns.index('updated')]) is float and math.isfinite(values[columns.index('updated')])
                    values[columns.index('updated')] = '<host-wall-time>'
                if name == 'observations':
                    assert type(values[columns.index('recorded_at')]) is float and math.isfinite(values[columns.index('recorded_at')])
                    values[columns.index('recorded_at')] = '<host-wall-time>'
                canonical.append(values)
            tables[name] = dict(columns=columns, rows=canonical)
        assert set(tables) == {'intents', 'meta', 'native_fills', 'native_income', 'observations'}
        meta = {key: json.loads(value) for key, value in raw_tables['meta']['rows']}
        assert meta['identity'] == 'binance:BTCUSDT:live:' + row['strategy']['uid'] and meta['schema_version'] == 1
        assert meta.get('session_replacement') is None
        for key, exported in (('entry_fill', 'ownership'), ('linear_campaign', 'model'), ('lifecycle_identity', 'lifecycle_identity')):
            assert meta.get(key) == row['sqlite'][exported]
    finally:
        connection.close()
    archive_path = state / 'observations-archive.jsonl'
    archive_hash, archive_count, observed = hashlib.sha256(), 0, set()
    if archive_path.exists():
        with archive_path.open() as stream:
            for line in stream:
                assert line.endswith('\n'), 'incomplete observation archive tail'
                entry = json.loads(line)
                assert set(entry) == {'sequence', 'recorded_at', 'report'}
                assert type(entry['sequence']) is int and type(entry['recorded_at']) is float and math.isfinite(entry['recorded_at'])
                observed.add(entry['sequence'])
                entry['recorded_at'] = '<host-wall-time>'
                archive_hash.update((json.dumps(entry, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode())
                archive_count += 1  # Hash physical order and duplicates, including crash overlaps.
    observed.update(values[0] for values in raw_tables['observations']['rows'])
    assert observed == set(range(1, max(observed, default=0) + 1)), 'missing observation sequence'
    assert read(state / 'latest.json') == {k: v for k, v in reports[-1].items() if k != 'start_ms'}
    canonical = dict(schema=schema, tables=tables, observations_archive=dict(exists=archive_path.exists(), rows=archive_count, canonical_jsonl_sha256=archive_hash.hexdigest()))
    proof = dict(database_path=str(path), database_sha256=sha(path), schema_sha256=canonical_sha(schema),
                 canonical_sha256=canonical_sha(canonical), table_counts={k: len(v['rows']) for k, v in tables.items()},
                 archive_rows=archive_count, archive_sha256=sha(archive_path) if archive_path.exists() else None,
                 host_process_pid=meta['writer_host']['pid'], normalization=NORMALIZATION)
    return canonical, proof


def segment_check(final_path, row, reports, arm, spec, full):
    chain, seen = [], set()
    path, current = final_path.resolve(), row
    while True:
        assert path not in seen and len(chain) < spec['max_segments']
        seen.add(path)
        chain.append((path, current))
        previous = current.get('previous_receipt')
        if previous is None:
            break
        path = Path(previous['path']).resolve()
        assert sha(path) == previous['sha256']
        current = read(path)
    chain.reverse()
    raw_lines = Path(row['reports']['path']).read_bytes().splitlines(keepends=True)
    expected_count, previous_wall = 0, 0
    proof = []
    for index, (path, segment) in enumerate(chain, 1):
        source_check(segment, arm, spec)
        assert segment['segment'] == index and segment['mode'] == ('start' if index == 1 else 'resume')
        assert segment['binding'] == row['binding'] and segment['inputs'] == row['inputs'] and segment['strategy'] == row['strategy']
        assert segment['state_directory'] == row['state_directory'] and segment['reports']['path'] == row['reports']['path']
        assert segment['scope'] == row['scope'] and segment['failure'] is None
        cursor = segment['session_count']
        assert expected_count <= cursor <= len(reports)
        assert segment['newly_run_session_count'] == cursor - expected_count
        assert segment['reports']['count'] == cursor
        assert hashlib.sha256(b''.join(raw_lines[:cursor])).hexdigest() == segment['reports']['sha256']
        assert segment['cumulative_wall_seconds'] >= previous_wall
        assert segment['cumulative_wall_seconds'] >= previous_wall + segment['segment_wall_seconds']
        if index != len(chain):
            assert not segment['complete'] and segment['can_resume'] and segment['current_sqlite_matches_last_checkpoint']
            assert segment['cumulative_wall_seconds'] < spec['total_wall_seconds']
            last = segment['last_checkpoint']
            checkpoint_path = Path(last['path']).resolve()
            assert checkpoint_path.is_relative_to(Path(row['state_directory']).parent / 'checkpoints')
            assert sha(checkpoint_path) == last['sha256']
            envelope = read(checkpoint_path)
            saved = envelope['body']
            assert digest(saved) == envelope['sha256'] == last['envelope_sha256']
            assert saved['version'] == 'slim-production-regression-checkpoint-v1'
            assert saved['cursor'] == last['cursor'] == cursor and saved['starts_ms'] == row['inputs']['starts_ms'][:cursor]
            assert saved['binding'] == row['binding'] and saved['reports'] == segment['reports']
            assert saved['state_directory'] == row['state_directory']
            venue = saved['venue']
            assert digest(venue['body']) == venue['sha256']
            body = decoded(venue['body'])
            assert body['version'] == 'research-exchange-session-checkpoint-v1' and body['binding'] == row['binding']
            assert body['config']['state_dir'] == body['account']['directory'] == row['state_directory']
            assert body['config']['account_uid'] == row['strategy']['uid']
            assert body['account']['scope'] == 'binance:BTCUSDT:live:' + row['strategy']['uid']
            assert body['account']['durable_sha256'] == last['durable_sqlite_sha256']
            assert body['venue']['now_ms'] == segment['at_ms']
        expected_count, previous_wall = cursor, segment['cumulative_wall_seconds']
        proof.append(dict(path=str(path), sha256=sha(path), segment=index, cursor=cursor,
                          previous_receipt=segment.get('previous_receipt'), checkpoint=segment.get('last_checkpoint')))
    assert expected_count == (795 if full else 6)
    return proof


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def read(path):
    path = Path(path)
    with (gzip.open(path, 'rt') if path.suffix == '.gz' else path.open()) as stream:
        return json.load(stream)


def financial_check(row, full, spec):
    financial = row['financial']
    now = financial['now_ms']
    assert now == row['at_ms']
    if full:
        assert now == spec['terminal_ms'], 'full account never reached the original exclusive terminal'
    else:
        assert row['inputs']['starts_ms'][-1] <= now < spec['terminal_ms']
    assert financial['known_path'] and all(financial['audit']['checks'].values())
    assert financial['audit']['passed']
    rates = read(spec['fx'])['rates']
    days = sorted(rates)
    def fx(stamp):
        day = datetime.fromtimestamp(stamp / 1000, timezone.utc).date().isoformat()
        index = bisect.bisect_left(days, day) - 1
        return D(str(rates[days[index]]['CNY'])) if index >= 0 else D('6.9615')
    assert D(row['initial_usdt']) == D(10000) / fx(row['inputs']['starts_ms'][0]) * D('.999')
    assert D(financial['final_cny']) == D(financial['final_usdt']) * fx(now) * D('.999')
    assert D(financial['quantity_btc']) == D(financial['position'])
    assert len({trade['id'] for trade in financial['trades']}) == len(financial['trades'])
    assert len({entry['tranId'] for entry in financial['funding_ledger']}) == len(financial['funding_ledger'])
    assert all(type(trade['time']) is int and row['inputs']['starts_ms'][0] <= trade['time'] <= now and trade['time'] < spec['terminal_ms'] for trade in financial['trades'])
    assert all(type(entry['time']) is int and row['inputs']['starts_ms'][0] <= entry['time'] <= now for entry in financial['funding_ledger'])
    assert all(entry['time'] < spec['terminal_ms'] for entry in financial['funding_ledger'] if entry['incomeType'] == 'FUNDING_FEE')
    assert not [order for order in financial['orders'].values() if order['status'] not in ('FILLED', 'CANCELED', 'EXPIRED', 'EXPIRED_IN_MATCH', 'REJECTED')]
    q = D(financial['position'])
    if q:
        live = [algo for algo in financial['algos'].values() if algo['algoStatus'] == 'NEW']
        assert len(live) == 2 and {algo['orderType'] for algo in live} == {'STOP_MARKET', 'TAKE_PROFIT_MARKET'}
        assert all(algo['symbol'] == 'BTCUSDT' and algo['side'] == ('SELL' if q > 0 else 'BUY')
                   and algo['positionSide'] == 'BOTH' and algo['closePosition'] is True
                   and algo['workingType'] == 'MARK_PRICE' and algo['priceProtect'] is False
                   and algo['clientAlgoId'].startswith('cq-') for algo in live)
        stop = D(next(algo['triggerPrice'] for algo in live if algo['orderType'] == 'STOP_MARKET'))
        liquidation = (q * D(financial['entry']) - D(financial['margin'])) / (q - abs(q) * D('.00575'))
        assert stop > liquidation if q > 0 else stop < liquidation
    return dict(actual_endpoint_ms=now, terminal_funding_exclusive=True, final_owned_protection_checked=bool(q))


def cache_pack_check(entry, raw, abi, destination, binary_bytes):
    assert entry['raw_zip_sha256'] == raw['sha256'] and entry['raw_zip_bytes'] == raw['bytes']
    assert entry['name'] == raw['name'] + '.' + raw['sha256'] + '.bin'
    assert entry['parser_sha256'] == abi['parser_sha256'] and entry['abi'] == abi['native']
    output = Path(entry['output'])
    assert output == destination / (entry['name'] + '.gz')
    assert output.stat().st_size == entry['gzip_bytes'] and sha(output) == entry['gzip_sha256']
    result, size = hashlib.sha256(), 0
    with gzip.open(output, 'rb') as stream:
        header = stream.read(8)
        assert len(header) == 8 and struct.unpack('<q', header)[0] == entry['row_count'] >= 0
        result.update(header); size += len(header)
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block); size += len(block)
    assert size == binary_bytes == entry['decompressed_bytes'] == 8 + 32 * entry['row_count']
    assert result.hexdigest() == entry['bin_sha256'] == entry['decompressed_sha256']


def cache_check(spec, full):
    capture_path = ROOT / 'canonical-cache-capture.jsonl'
    ahead_path = ROOT / 'canonical-parseahead.jsonl'
    destination = Path(spec['shared_parsed_cache']) / spec['parser_sha256']
    paths = [path for path in (capture_path, ahead_path) if path.exists()]
    if not paths:
        assert not list(destination.iterdir()) if destination.exists() else True, 'shared parsed binary exists without a qualification journal'
        return dict(published=0, namespace_complete=True)
    snapshots = {path: path.read_bytes() for path in paths}
    journals = {path: [json.loads(line) for line in data.decode().splitlines()] for path, data in snapshots.items()}
    native = dict(typecode='q', itemsize=8, byteorder=sys.byteorder)
    assert array.array('q').itemsize == 8 and native['byteorder'] == 'little'
    abi = dict(parser_sha256=spec['parser_sha256'], native=native)
    original = {entry['name']: entry for entry in (json.loads(line) for line in (ROOT / 'input-restore.jsonl').read_text().splitlines())}
    captured_publications, ahead_publications = [], []
    if capture_path in journals:
        events = journals[capture_path]
        starts = [entry for entry in events if entry['event'] == 'started']
        assert starts
        for entry in starts:
            assert entry['spec_sha256'] == sha(ROOT / 'spec.json')
            assert entry['restore_journal_sha256'] == sha(ROOT / 'input-restore.jsonl')
            assert entry['parser_sha256'] == spec['parser_sha256'] and entry['abi'] == native
            assert entry['source_arm'] == 'before' and entry['runtime_head'] == spec['runtime_heads']['before']
            assert entry['source_sha256'] == spec['source_sha256_by_arm']['before']
            assert entry['destination'] == str(destination) and entry['registered_inputs'] == 773
            assert entry['historical_bins_scanned'] is False
            assert entry['helper_sha256'] in {sha(path) for path in ROOT.glob('capture_canonical_cache*.py')}
            assert entry['max_stored_gzip_bytes'] == 4000000000 and entry['min_free_bytes'] == 2000000000
        captured = [entry for entry in events if entry['event'] == 'captured']
        captured_publications = [entry for entry in events if entry['event'] == 'published']
        for entry in captured_publications:
            assert entry['source_arm'] == 'before' and entry['source_sha256'] == spec['source_sha256_by_arm']['before']
            assert any(c['name'] == entry['name'] and c['captured'] == entry['captured'] and c['same_inode'] is True
                       and c['raw_zip_sha256'] == entry['raw_zip_sha256'] and c['parser_sha256'] == spec['parser_sha256']
                       and c['source_arm'] == 'before' for c in captured)
            cache_pack_check(entry, original[entry['raw_zip_name']], abi, destination, entry['captured']['bytes'])
            assert entry['stored_gzip_bytes'] <= 4000000000 and entry['free_bytes'] >= 2000000000
    epoch_proofs = []
    if ahead_path in journals:
        assert capture_path in journals and journals[capture_path][-1]['event'] == 'stopped'
        events = journals[ahead_path]
        lines = snapshots[ahead_path].splitlines(keepends=True)
        assert len(lines) == len(events) and all(line.endswith(b'\n') for line in lines)
        offsets = [index for index, entry in enumerate(events) if entry['event'] == 'parseahead_started']
        assert offsets and offsets[0] == 0
        owned_roots, parent_pids = set(), set()
        for epoch_index, offset in enumerate(offsets):
            start = events[offset]
            epoch = events[offset:offsets[epoch_index + 1] if epoch_index + 1 < len(offsets) else len(events)]
            assert start['format'] == 'exact-canonical-parseahead-v1'
            assert start['helper_sha256'] in {sha(path) for path in ROOT.glob('canonical_parseahead*.py')}
            assert start['helper_dependency_sha256'] == sha(ROOT / 'capture_canonical_cache.py')
            assert start['spec_sha256'] == sha(ROOT / 'spec.json') and start['restore_journal_sha256'] == sha(ROOT / 'input-restore.jsonl')
            assert start['stopped_capture_journal_sha256'] == hashlib.sha256(snapshots[capture_path]).hexdigest()
            assert start['capture_baseline_packs'] == len(captured_publications)
            baseline_bytes = sum(entry['gzip_bytes'] for entry in captured_publications)
            assert start['capture_baseline_gzip_bytes'] == baseline_bytes
            assert start['source_arm'] is None and start['actual_production_sessions_added'] == 0
            assert start['parser_sha256'] == spec['parser_sha256'] and start['abi'] == native
            assert start['parser_dependency_source_sha256'] == spec['source_sha256_by_arm']['before']
            assert start['registered_inputs'] == 773 and start['destination'] == str(destination)
            assert start['workers'] == 2 and start['nice'] == 10 and start['gzip_compresslevel'] == 1
            assert start['combined_gzip_cap_bytes'] == 8000000000 and start['min_free_bytes'] == 2000000000
            owned = Path(start['private_owned'])
            assert owned.parent == ROOT and owned.name.startswith('canonical-parseahead-private-')
            assert owned not in owned_roots and start['pid'] not in parent_pids
            owned_roots.add(owned); parent_pids.add(start['pid'])
            if epoch_index:
                assert start['resume_owned_published'] is True
                assert events[offset - 1]['event'] == 'parseahead_stopped' and events[offset - 1]['exitcodes'] == [0, 0]
                assert start['prior_parseahead_journal_sha256'] == hashlib.sha256(b''.join(lines[:offset])).hexdigest()
                assert start['prior_parseahead_packs'] == len(ahead_publications)
                assert start['prior_combined_gzip_bytes'] == baseline_bytes + sum(entry['gzip_bytes'] for entry in ahead_publications)
                assert start['worker_metadata_reserve_bytes'] == 65536 and start['canonical_binary_reservation_block_bytes'] == 4096
            else:
                assert not start.get('resume_owned_published', False)
                assert start.get('prior_parseahead_journal_sha256') is None
            workers = [entry for entry in epoch if entry['event'] == 'parseahead_worker_started']
            assert len(workers) == 2 and {entry['worker'] for entry in workers} == {0, 1}
            for worker in workers:
                assert worker['nice'] == 10 and worker['parser_module'] == str(ROOT / 'tooling/research/session_market.py')
                assert worker['method'] == 'TradePrints._load' and worker['private_owned'] == str(owned / str(worker['worker']))
            stopped = [entry for entry in epoch if entry['event'] == 'parseahead_stopped']
            worker_stops = [entry for entry in epoch if entry['event'] == 'parseahead_worker_stopped']
            closed = (len(stopped) == 1 and epoch[-1]['event'] == 'parseahead_stopped'
                      and stopped[0]['exitcodes'] == [0, 0] and len(worker_stops) == 2
                      and {(entry['worker'], entry['pid']) for entry in worker_stops} == {(entry['worker'], entry['pid']) for entry in workers})
            if full or epoch_index + 1 < len(offsets):
                assert closed, 'final or resumed cache derivation epoch lacks clean worker and parent stop records'
            assignments = [entry for entry in epoch if entry['event'] == 'parseahead_assigned']
            qualified = [entry for entry in epoch if entry['event'] == 'parseahead_qualified_before_publication']
            publications = [entry for entry in epoch if entry['event'] == 'parseahead_published']
            for entry in publications:
                raw = original[entry['raw_zip_name']]
                assert entry['provenance'] == 'rebuilt_by_exact_frozen_TradePrints._load_from_verified_original_raw'
                assert entry['actual_production_sessions_added'] == 0 and entry['initial_private_cache_absent'] is True
                assert entry['shared_cache_preloaded'] is False
                assert entry['raw_sha256_before'] == entry['raw_sha256_after'] == entry['parser_loaded_sha256'] == raw['sha256']
                assert entry['raw_metadata_before'] == entry['raw_metadata_after'] and entry['raw_metadata_before']['bytes'] == raw['bytes']
                assert entry['parser_dependency_source_sha256'] == spec['source_sha256_by_arm']['before']
                assert entry['parser_module'] == str(ROOT / 'tooling/research/session_market.py') and entry['parser_method'] == 'TradePrints._load'
                assert entry['frozen_method_files'] == {name: str(ROOT / 'tooling/research/session_market.py') for name in ('_load', '_checksum', '_iter_zip_rows')}
                assert entry['publication'] == 'renameat2_NOREPLACE'
                task = owned / str(entry['worker']) / raw['name']
                assert entry['owned_selected'] == str(task / 'selected')
                assert entry['owned_bin'] == str(task / 'selected-cache' / entry['name'])
                assert any(worker['worker'] == entry['worker'] and worker['pid'] == entry['pid'] for worker in workers)
                assert any(assignment['worker'] == entry['worker'] and assignment['raw_zip_name'] == raw['name']
                           and assignment['raw_zip_sha256'] == raw['sha256'] and assignment['raw_metadata_before'] == entry['raw_metadata_before']
                           and assignment['selected_by_fullbefore_at_assignment'] is False and assignment['actual_production_sessions_added'] == 0
                           and assignment['initial_private_cache_absent'] is True and assignment['shared_cache_preloaded'] is False
                           and assignment['canonical_binary_bound'] >= entry['bin_metadata']['bytes'] for assignment in assignments)
                evidence = {k: v for k, v in entry.items() if k not in ('event', 'at_utc', 'combined_gzip_bytes', 'free_bytes')}
                assert any(evidence == {k: v for k, v in qualification.items() if k not in ('event', 'at_utc')} for qualification in qualified)
                cache_pack_check(entry, raw, abi, destination, entry['bin_metadata']['bytes'])
                assert entry['combined_gzip_bytes'] <= 8000000000 and entry['free_bytes'] >= 2000000000
            ahead_publications.extend(publications)
            epoch_proofs.append(dict(epoch=epoch_index + 1, helper_sha256=start['helper_sha256'], parent_pid=start['pid'],
                                     private_owned=str(owned), published=len(publications), closed=closed,
                                     resume_prior_journal_sha256=start.get('prior_parseahead_journal_sha256'),
                                     reservation_block_bytes=start.get('canonical_binary_reservation_block_bytes'),
                                     worker_metadata_reserve_bytes=start.get('worker_metadata_reserve_bytes')))
    published = captured_publications + ahead_publications
    assert len({entry['name'] for entry in published}) == len(published), 'duplicate cache publication provenance'
    expected = {entry['name'] + '.gz' for entry in published}
    namespace = {path.name for path in destination.iterdir()}
    stored = sum(entry['gzip_bytes'] for entry in published)
    assert stored <= (8000000000 if ahead_path in journals else 4000000000)
    if full:
        assert capture_path not in journals or journals[capture_path][-1]['event'] == 'stopped', 'actual cache capture still open'
        assert namespace == expected, 'unqualified cache binary or unfinished output in frozen shared namespace'
        assert all(path.read_bytes() == data for path, data in snapshots.items()), 'cache journal changed during final qualification'
    return dict(journals={str(path): dict(sha256=hashlib.sha256(data).hexdigest(), snapshot_events=len(journals[path])) for path, data in snapshots.items()},
                published=len(published), qualified_raw_names=sorted(entry['raw_zip_name'] for entry in published),
                published_gzip_bytes=stored, namespace_complete=namespace == expected, abi=native,
                captured_actual_before_packs=len(captured_publications), rebuilt_exact_parser_packs=len(ahead_publications),
                derivation_epochs=epoch_proofs, all_derivation_epochs_closed=all(epoch['closed'] for epoch in epoch_proofs),
                added_production_sessions=0, all_published_binary_hashes_verified=True,
                scope='final namespace' if full else 'journal snapshot during optional active derivation')


def validate(row, arm, count, full, spec, receipt_path):
    source = source_check(row, arm, spec)
    inputs = input_check(row, count, full, spec)
    assert row['complete'] and row['failure'] is None and not row['can_resume']
    assert row['session_count'] == row['reports']['count'] == count
    assert row['scope'] == {'kind': 'original-full' if full else 'smoke', 'planned_sessions': count}
    assert row['original_window_complete'] == full
    assert row['financial']['audit']['passed'] and row['financial']['known_path']
    assert not row['sqlite']['pending']
    report_path = Path(row['reports']['path'])
    assert sha(report_path) == row['reports']['sha256']
    reports = [json.loads(line) for line in report_path.read_text().splitlines()]
    assert len(reports) == count
    assert [r['start_ms'] for r in reports] == row['inputs']['starts_ms']
    assert all(r.get('cleanup') == 'verified' and r.get('pending_intents') == 0 and r.get('execution_unresolved') is False for r in reports)
    assert all(not [e for e in r.get('errors', []) if e.get('error_type') in ('TypeError', 'KeyError', 'ValueError', 'ArithmeticError')
                   or e.get('reason') == 'Invalid observation or state'] for r in reports)
    proof_path = report_path.parent / 'production-calls.jsonl'
    proofs = [json.loads(line) for line in proof_path.read_text().splitlines()]
    assert [r['start_ms'] for r in proofs] == row['inputs']['starts_ms']
    totals = Counter()
    for proof in proofs:
        assert proof['calls']['coinquant/session.py:run'] == 1
        assert proof['calls']['coinquant/binance.py:_request'] > 0
        assert proof['calls']['coinquant/lifecycle.py:finish'] > 0
        assert proof['calls']['coinquant/state.py:_account_lock_path'] > 0
        assert proof['calls']['coinquant/state.py:__enter__'] > 0
        totals.update(proof['calls'])
    for function in ('coinquant/binance.py:_request', 'coinquant/lifecycle.py:decide',
                     'coinquant/lifecycle.py:finish', 'coinquant/ownership.py:reconcile',
                     'coinquant/audit.py:income', 'coinquant/state.py:prepare'):
        assert totals[function] > 0, function
    canonical, sqlite_proof = sqlite_check(row, reports)
    return dict(production_calls=dict(totals), report_sha256=sha(report_path),
                proof_sha256=sha(proof_path), producer=source, inputs=inputs,
                endpoint=financial_check(row, full, spec), sqlite=sqlite_proof,
                segments=segment_check(receipt_path, row, reports, arm, spec, full), _canonical_sqlite=canonical)


def main():
    if sys.flags.optimize:
        raise RuntimeError('receipt validation requires Python assertions enabled')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('--full', action='store_true')
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    spec = read(ROOT / 'spec.json')
    count = 795 if args.full else 6
    before, after = read(args.before), read(args.after)
    proof = {arm: validate(row, arm, count, args.full, spec, path)
             for arm, row, path in (('before', before, args.before), ('after', after, args.after))}
    equal = {key: before[key] == after[key] for key in
             ('inputs', 'strategy', 'initial_cny', 'initial_usdt', 'terminal_ms', 'sqlite')}
    equal['financial'] = ({k: v for k, v in before['financial'].items() if k != 'input_qualification_reuse'} ==
                          {k: v for k, v in after['financial'].items() if k != 'input_qualification_reuse'})
    equal['sqlite_canonical_entire_database_and_archive'] = proof['before'].pop('_canonical_sqlite') == proof['after'].pop('_canonical_sqlite')
    equal['reports_bytes'] = proof['before']['report_sha256'] == proof['after']['report_sha256']
    for key in ('strategy_sha256', 'input_sha256', 'schedule_sha256', 'producer_sha256'):
        equal['binding.' + key] = before['binding'][key] == after['binding'][key]
    cache = cache_check(spec, args.full)
    published_raw = set(cache.get('qualified_raw_names', []))
    cache['loader_eligible_loaded_names'] = {arm: sorted(set(row['financial']['loaded_print_files']) & published_raw) for arm, row in (('before', before), ('after', after))}
    cache['cache_hit_claim_limit'] = 'frozen loader namespace and derived bytes are qualified; producer does not record per-load cache-hit counts'
    result = dict(scope='original795' if args.full else 'first6-smoke', passed=all(equal.values()),
                  strict_equality=equal, tolerance=None, normalization=NORMALIZATION,
                  raw_financial_equality=before['financial'] == after['financial'],
                  raw_financial_different_fields=sorted(k for k in set(before['financial']) | set(after['financial']) if before['financial'].get(k) != after['financial'].get(k)),
                  raw_financial_exact_differences=exact_differences(before['financial'], after['financial']),
                  non_economic_input_qualification_io={arm: row['financial']['input_qualification_reuse'] for arm, row in (('before', before), ('after', after))},
                  cache_qualification=cache, validator_sha256=sha(__file__),
                  receipts={arm: dict(path=str(path.resolve()), sha256=sha(path))
                            for arm, path in (('before', args.before), ('after', args.after))},
                  proof=proof, before_financial=before['financial'], after_financial=after['financial'])
    assert not args.out.exists(), 'preserve previous comparison'
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(scope=result['scope'], passed=result['passed'], strict_equality=equal)))
    assert result['passed'], 'unexpected exact difference; investigate, never widen tolerance'


if __name__ == '__main__':
    main()
