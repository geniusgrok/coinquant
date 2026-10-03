"""Manual, source-bound paper ledger; never sends native requests or orders.

Only ``observe`` acquires decision inputs, with real request/receipt clocks.
Imported completed bars are warmup only. A frozen export is an independently
approved trust anchor, not a signature; callers must pin its reviewed raw hash.
This deliberately models discrete public observations, not native Lifecycle.
"""
from __future__ import annotations

import argparse
import base64
import copy
import csv
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal as D, ROUND_DOWN
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import time
from urllib.parse import parse_qs, urlsplit, urlencode
from urllib.request import urlopen, Request, build_opener, HTTPCookieProcessor
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
KIND = 'perp'
PACKAGE = 'coinquant'
INTERVAL = 14400000
DAY = 86400000
BASE = {'spot': 'atr-stop', 'perp': 'incumbent'}
ADAPTER = 'canonical-incumbent-v1'
CATEGORIES = {'source_and_inputs', 'original_accounting', 'baseline_six_groups',
              'calibration_and_actual_risk', 'adoption_gates', 'actual_budget_aggregation'}
FX_URL = 'https://fred.stlouisfed.org/graph/?id=DEXCHUS'
DFII_URL = 'https://alfred.stlouisfed.org/series/downloaddata?seid=DFII10'
FX_FEE = D('.001')
FEE = D('.001') if KIND == 'spot' else D('.00075')
SLIP = D('.0011')
MAX_AGE = 60000


def require(test, message):
    if not test:
        raise ValueError(message)


def number(value):
    require(not isinstance(value, bool), 'boolean money')
    result = D(str(value))
    require(result.is_finite(), 'nonfinite money')
    return result


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def dump(body):
    return json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def strict(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON field')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('nonfinite JSON')
    body = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    def finite(value):
        if isinstance(value, dict):
            for v in value.values(): finite(v)
        elif isinstance(value, list):
            for v in value: finite(v)
        elif isinstance(value, float): number(value)
    finite(body)
    return body


def now_ms():
    return time.time_ns() // 1000000


def utc(stamp):
    return datetime.fromtimestamp(stamp / 1000, timezone.utc).isoformat()


def git(root, *args):
    return subprocess.run(['git', *args], cwd=root, check=True, capture_output=True).stdout


def source(root=ROOT, head=None):
    """Archive every runtime byte, research program/data and executable/configuration file.

    Ordinary Markdown prose is metadata. All runtime files, research non-prose
    files and research protocols, root executable/configuration files, and .github
    execution configuration are protected, including their modes. Tests and inert
    evidence/review packets are not execution inputs. No per-file change exclusions or caller allowlist.
    """
    root = Path(root)
    current = git(root, 'rev-parse', 'HEAD').decode().strip()
    head = head or current
    require(len(head) == 40 and all(c in '0123456789abcdef' for c in head), 'full source commit required')
    package = 'spotquant' if (root / 'spotquant').is_dir() else 'coinquant'
    files, modes, python = {}, {}, hashlib.sha256()
    archive = git(root, 'archive', head)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tree:
        for member in sorted(tree.getmembers(), key=lambda m: m.name):
            if not member.isfile():
                require(not member.issym() and not member.islnk(), 'source symlinks unsupported')
                continue
            name = member.name
            parts = Path(name).parts
            protected = (parts[0] in (package, '.github') or
                         (parts[0] == 'research' and (not name.endswith('.md') or 'protocol' in parts[-1].lower())) or
                         (len(parts) == 1 and (Path(name).suffix in {'.py', '.json', '.toml', '.yaml', '.yml', '.cfg', '.ini', '.sh'} or
                                               bool(member.mode & 0o111))))
            if not protected: continue
            raw = tree.extractfile(member).read()
            files[name] = sha(raw); modes[name] = member.mode
            if name.startswith((package + '/', 'research/')) and name.endswith('.py'):
                python.update(name.encode() + b'\0' + raw + b'\0')
            if head == current:
                require((root / name).is_file() and (root / name).read_bytes() == raw, 'working source differs from committed archive')
    if head == current:
        require(not git(root, 'status', '--porcelain').strip(), 'clean committed repository required')
    return {'git_head': head, 'dirty': False, 'python_sources_sha256': python.hexdigest(),
            'protected_files': files, 'protected_modes': modes, 'protected_sha256': sha(dump({'files': files, 'modes': modes}))}


def assert_equivalent(recorded, current, root=ROOT):
    actual = source(root, recorded['git_head'])
    require(dump(actual) == dump(recorded), 'recorded source archive mismatch')
    require(recorded['protected_files'] == current['protected_files'] and recorded['protected_modes'] == current['protected_modes'], 'protected source changed; new verified bridge/diary required')


def read_bound(path, expected):
    raw = Path(path).read_bytes()
    require(sha(raw) == expected, 'raw file checksum mismatch')
    return strict(raw), raw


def inventory(report):
    """Frozen v1 inventory contract, also recomputed by the standalone reader."""
    checksum = lambda value: sha(json.dumps(value, sort_keys=True).encode())
    return {'inputs': report['inputs'], 'analysis_source': report['analysis_source'],
            'contracts': report['contracts'], 'accounts': {
                k: {field: v[field] for field in ('raw_sha256', 'source', 'status', 'reasons', 'components')}
                for k, v in report['accounts'].items()},
            'account_evidence_sha256': {k: checksum(v) for k, v in report['accounts'].items()},
            'portfolio_evidence_sha256': checksum(report['portfolios']),
            'input_envelopes_sha256': checksum(report['input_envelopes']),
            'calibration_input_documents': report['calibration_input_documents'],
            'calibration_diagnostics_sha256': checksum(report['calibration_diagnostics']),
            'environment_sha256': checksum(report['environment']), 'combinations': report['combinations'],
            'required_accounts': report['required_accounts'], 'selected': report['selected'],
            'calibration_documents': report['calibration_documents'], 'decisions': report['decisions'],
            'baseline_equality': report['baseline_equality']}


def export_binding(analysis, review, bridges, out):
    """Spot-only: run the approved full proof verifier, then freeze all proof bytes.

    ``bridges`` is a separately reviewed JSON file, containing per-project exact
    current source(), recorded measurement identity, adapter, candidate, scale,
    original accepted-result SHA list and an independent canonical-review SHA.
    The final export hash must be independently approved before initialization.
    """
    require(KIND == 'spot', 'export is produced by the reviewed Spot evaluator')
    from research import edge_assessment as evaluator  # lazy: standalone Coin never imports it
    before = source()
    raw = Path(analysis).read_bytes(); report = strict(raw)
    require(report['phase'] == 'final' and report['status'] == 'complete_reviewed' and
            not report['pending'] and not report['blocking'], 'final accepted analysis required')
    verified = evaluator.verify_financial_review(review, report)
    require(report['financial_review']['sha256'] == verified['sha256'], 'final review identity mismatch')
    expected = evaluator.review_expectations(report)
    proof_raw = Path(review).read_bytes(); proof = strict(proof_raw)
    _, prior_raw = read_bound(Path(review).parent / proof['preliminary']['path'], proof['preliminary']['sha256'])
    artifacts = {}
    for category, item in proof['checks'].items():
        p = Path(review).parent / item['artifact']['path']
        a, b = read_bound(p, item['artifact']['sha256'])
        artifacts[category] = base64.b64encode(b).decode()
    bridge_raw = Path(bridges).read_bytes(); bridge = strict(bridge_raw)
    body = {'format': 'btc-edge-forward-export-v1', 'analysis_raw': base64.b64encode(raw).decode(),
            'analysis_sha256': sha(raw), 'review_raw': base64.b64encode(proof_raw).decode(),
            'review_sha256': sha(proof_raw), 'artifacts': artifacts, 'expected': expected,
            'bridges_raw': base64.b64encode(bridge_raw).decode(), 'bridges_sha256': sha(bridge_raw),
            'exporter_source': before, 'preliminary_raw': base64.b64encode(prior_raw).decode(), 'canonical_reviews': {}}
    for kind, project in bridge.items():
        repo = ROOT if kind == 'spot' else ROOT.parent / 'coinquant'
        require(project['source'] == source(repo), 'canonical bridge current source mismatch')
        require(project['measured_source'] == report['accounts'][project['account_id']]['source'], 'bridge measured source mismatch')
        require(project['candidate'] == report['selected'][kind], 'bridge selected candidate mismatch')
        canonical, canonical_raw = read_bound(Path(bridges).parent / project['canonical_review']['path'], project['canonical_review']['sha256'])
        require(canonical['format'] == 'btc-edge-canonical-forward-bridge-v1' and canonical['status'] == 'independently_reviewed', 'canonical review required')
        body['canonical_reviews'][kind] = base64.b64encode(canonical_raw).decode()
    require(source() == before and Path(analysis).read_bytes() == raw and
            Path(review).read_bytes() == proof_raw and Path(bridges).read_bytes() == bridge_raw, 'export input changed')
    new_file(out, dump(body))
    return sha(dump(body))


def decode(raw):
    return base64.b64decode(raw, validate=True)


def validate_export(path, expected_hash, review_hash, root=ROOT):
    body, raw = read_bound(path, expected_hash)
    require(body['format'] == 'btc-edge-forward-export-v1', 'unknown export format')
    analysis_raw, proof_raw, bridge_raw = (decode(body[key]) for key in ('analysis_raw', 'review_raw', 'bridges_raw'))
    require(sha(analysis_raw) == body['analysis_sha256'] and sha(proof_raw) == body['review_sha256'] == review_hash and
            sha(bridge_raw) == body['bridges_sha256'], 'export embedded evidence mismatch')
    report, proof, bridges = strict(analysis_raw), strict(proof_raw), strict(bridge_raw)
    require(report['phase'] == 'final' and report['status'] == 'complete_reviewed' and
            not report['blocking'] and not report['pending'] and report['financial_review']['sha256'] == review_hash,
            'final reviewed complete selection required')
    require(proof['format'] == 'btc-edge-financial-review-v1' and
            proof['inventory_sha256'] == report['inventory_sha256'] and
            set(proof['checks']) == set(body['expected']) == set(body['artifacts']) == CATEGORIES,
            'six-category proof coverage required')
    # Expected typed records were derived by the full approved evaluator. The
    # externally pinned export freezes that derivation as well as original proof.
    for category in sorted(CATEGORIES):
        check = proof['checks'][category]
        a_raw = decode(body['artifacts'][category]); artifact = strict(a_raw)
        require(check['passed'] is True and sha(a_raw) == check['artifact']['sha256'] and
                set(artifact) == {'inventory_sha256', 'category', 'recomputations'} and
                artifact['inventory_sha256'] == proof['inventory_sha256'] and artifact['category'] == category,
                'financial proof artifact binding failed')
        expected = body['expected'][category]
        records = artifact['recomputations']; seen = set()
        require(expected and isinstance(records, list), 'empty financial recomputation coverage')
        for record in records:
            identity = record['id']
            require(identity not in seen and identity in expected and record['matches'] is True and
                    dump(record) == dump(expected[identity]) and record['raw_bindings'], 'financial recomputation mismatch/duplicate')
            seen.add(identity)
        require(seen == set(expected), 'incomplete financial recomputation coverage')
    prior_raw = decode(body['preliminary_raw']); prior = strict(prior_raw)
    require(set(proof) == {'format', 'preliminary', 'inventory_sha256', 'reviewer_source', 'checks'} and
            sha(prior_raw) == proof['preliminary']['sha256'] and prior['phase'] == 'preliminary' and
            prior['status'] == 'complete_pending_independent_review' and not prior['pending'] and not prior['blocking'] and
            inventory(prior) == inventory(report) and
            sha(json.dumps(inventory(report), sort_keys=True).encode()) == proof['inventory_sha256'], 'preliminary/final inventory mismatch')
    bridge = bridges[KIND]
    canonical_raw = decode(body['canonical_reviews'][KIND]); canonical = strict(canonical_raw)
    require(sha(canonical_raw) == bridge['canonical_review']['sha256'] and
            canonical['format'] == 'btc-edge-canonical-forward-bridge-v1' and canonical['status'] == 'independently_reviewed' and
            canonical['project'] == KIND and canonical['bridge'] == {k: v for k, v in bridge.items() if k != 'canonical_review'},
            'canonical review bytes/source/rule binding mismatch')
    require(bridge['candidate'] == report['selected'][KIND] == BASE[KIND] and
            bridge['adapter'] == ADAPTER and bridge['components'] == [] and bridge['scale'] == '1',
            'selected rule has no verified canonical forward adapter')
    require(bridge['canonical_review_sha256'] and len(bridge['canonical_review_sha256']) == 64 and
            bridge['original_accepted_result_sha256'] and all(len(x) == 64 for x in bridge['original_accepted_result_sha256']),
            'independent canonical/original result bridge missing')
    account = report['accounts'][bridge['account_id']]
    require(account['status'] == 'complete' and account['source'] == bridge['measured_source'] and
            bridge['raw_sha256'] == account['raw_sha256'] and account['components'] == [], 'canonical account bridge mismatch')
    current = source(root); assert_equivalent(bridge['source'], current, root)
    for key, name in [('spec_sha256', 'edge_spec.json'), ('protocol_sha256', 'edge-PROTOCOL.md')]:
        require(current['protected_files']['research/' + name] == report['contracts'][KIND][key], 'local contract differs from reviewed selection')
    return {'export_sha256': expected_hash, 'review_sha256': review_hash,
            'analysis_sha256': body['analysis_sha256'], 'bridge': bridge, 'recorded_source': bridge['source'],
            'current_source': current}, raw


def new_file(path, raw):
    with Path(path).open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    fsync_dir(Path(path).parent)


def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


def replace_file(path, raw):
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path); fsync_dir(path.parent)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def endpoint(url, kind=KIND):
    parsed = urlsplit(url)
    require(parsed.scheme == 'https' and not parsed.username and not parsed.password and
            not parsed.fragment and parsed.port in (None, 443), 'public HTTPS URL required')
    if kind == 'perp' and url == DFII_URL: return 'dfii10'
    if parsed.hostname == 'fred.stlouisfed.org' and parsed.path == '/graph/':
        require(parse_qs(parsed.query) == {'id': ['DEXCHUS']}, 'only public DEXCHUS FX CSV allowed')
        return 'fx'
    host, prefix = ('api.binance.com', '/api/v3/') if kind == 'spot' else ('fapi.binance.com', '/fapi/v1/')
    require(parsed.hostname == host and parsed.path.startswith(prefix), 'wrong official market endpoint')
    name = parsed.path[len(prefix):]; query = parse_qs(parsed.query)
    names = {'klines': 'bars', 'depth': 'depth', 'aggTrades': 'trades', 'exchangeInfo': 'instrument',
             'premiumIndex': 'mark', 'fundingRate': 'funding'}
    require(name in names and (kind == 'perp' or name not in ('premiumIndex', 'fundingRate')), 'endpoint not public observation allowlist')
    require(set(query) <= {'symbol', 'interval', 'limit', 'startTime', 'endTime', 'fromId'} and
            all(len(v) == 1 for v in query.values()), 'unknown/duplicate public request parameter')
    if name != 'exchangeInfo': require(query.get('symbol') == ['BTCUSDT'], 'wrong symbol')
    elif 'symbol' in query: require(query['symbol'] == ['BTCUSDT'], 'wrong instrument symbol')
    if name == 'klines': require(query.get('interval') == [('1d' if kind == 'spot' else '4h')], 'wrong completed interval')
    return names[name]


def acquire(url, directory):
    """Fetch a public allowlisted endpoint, retain exact bytes and actual clocks."""
    category = endpoint(url)
    if category == 'dfii10': return acquire_dfii(directory)
    request = now_ms()
    with urlopen(url, timeout=20) as response:
        require(response.geturl() == url, 'public redirect unsupported')
        raw = response.read(16000001)
    receipt = now_ms()
    require(0 <= receipt - request <= MAX_AGE and len(raw) <= 16000000, 'public observation timeout/oversize')
    digest = sha(raw); directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    path = directory / (str(request) + '-' + digest + '.raw')
    new_file(path, raw)
    return {'category': category, 'url': url, 'request_ms': request, 'receipt_ms': receipt,
            'sha256': digest, 'path': str(path.resolve())}


def acquire_dfii(directory):
    from coinquant.dfii10 import _Dates, available
    opener = build_opener(HTTPCookieProcessor())
    started = now_ms()
    with opener.open(DFII_URL, timeout=20) as response:
        require(response.geturl() == DFII_URL, 'unexpected ALFRED redirect')
        page = response.read(2000001)
    require(len(page) <= 2000000, 'ALFRED form oversized')
    parser = _Dates(); parser.feed(page.decode())
    dates = sorted(set(v for v in parser.values if available(v) < started))[-100:]
    require(len(dates) >= 21, 'insufficient causal ALFRED vintages')
    body = urlencode([('form[units]', 'lin'), ('form[obs_start_date]', str(dates[0] - timedelta(days=7))),
                      ('form[obs_end_date]', str(dates[-1])), ('form[entered_vintage_dates]', ''),
                      ('form[file_type]', '3'), ('form[file_format]', 'csv'), ('form[download_data]', 'Download data')] +
                     [('form[selected_vintage_dates][]', str(v)) for v in dates]).encode()
    with opener.open(Request(DFII_URL, data=body, method='POST'), timeout=20) as response:
        require(response.geturl() == DFII_URL, 'unexpected ALFRED archive redirect')
        raw = response.read(4000001)
    receipt = now_ms()
    require(len(raw) <= 4000000 and 0 <= receipt - started <= MAX_AGE, 'ALFRED acquisition stale/oversized')
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    raw_path = directory / (str(started) + '-' + sha(raw) + '.zip')
    form_path = directory / (str(started) + '-' + sha(page) + '.html')
    new_file(raw_path, raw); new_file(form_path, page)
    return dict(category='dfii10', url=DFII_URL, request_ms=started, receipt_ms=receipt,
                sha256=sha(raw), path=str(raw_path.resolve()), form_path=str(form_path.resolve()),
                form_sha256=sha(page), request_body=body.decode(), vintages=[str(v) for v in dates])


def dfii_from(receipt, call):
    from coinquant.dfii10 import available, _Dates
    raw = payload(receipt)
    page = Path(receipt['form_path']).read_bytes()
    require(sha(page) == receipt['form_sha256'], 'ALFRED form checksum mismatch')
    parser = _Dates(); parser.feed(page.decode())
    dates = [date.fromisoformat(v) for v in receipt['vintages']]
    expected = sorted(set(v for v in parser.values if available(v) < receipt['request_ms']))[-100:]
    require(dates == expected and len(dates) >= 21 and all(available(v) < call for v in dates), 'DFII10 causal vintage mismatch')
    with ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        require(len(names) == 1 and names[0].endswith('.csv') and archive.getinfo(names[0]).file_size <= 4000000,
                'official ALFRED CSV archive required')
        rows = list(csv.reader(io.StringIO(archive.read(names[0]).decode('utf-8-sig'))))
    require(rows and rows[0] == ['observation_date'] + [f'DFII10_{v:%Y%m%d}' for v in dates], 'DFII10 vintage columns mismatch')
    updates = {}; seen = set()
    for values in rows[1:]:
        require(len(values) == len(rows[0]), 'DFII10 observation width mismatch')
        observed = date.fromisoformat(values[0])
        require(observed not in seen and observed <= dates[-1], 'duplicate/future DFII10 observation')
        seen.add(observed)
        for vintage, value in zip(dates, values[1:]):
            if value:
                require(observed <= vintage, 'future vintage observation')
                updates[observed] = (number(value), vintage)
    observations = sorted(updates)
    latest = observations[-1] if observations else None
    prior = observations[-21] if len(observations) >= 21 else None
    reason = ('insufficient_20_prior_observations' if prior is None else
              'stale_observation_over_7_calendar_days' if
              (datetime.fromtimestamp(call / 1000, timezone.utc).date() - latest).days > 7 else None)
    return dict(latest_value=str(updates[latest][0]) if latest else None,
                prior20_value=str(updates[prior][0]) if prior else None,
                latest_observation_date=str(latest) if latest else None,
                prior20_observation_date=str(prior) if prior else None,
                latest_value_available_ms=available(updates[latest][1]) if latest else None,
                prior20_value_available_ms=available(updates[prior][1]) if prior else None,
                asof_vintage_date=str(dates[-1]), missing_reason=reason, response_sha256=sha(raw))


def payload(receipt):
    raw = Path(receipt['path']).read_bytes()
    require(sha(raw) == receipt['sha256'] and endpoint(receipt['url']) == receipt['category'], 'raw public provenance mismatch')
    return raw


def bars_from(receipts, available):
    rows = {}
    for receipt in receipts:
        require(receipt['category'] == 'bars' and receipt['receipt_ms'] <= available, 'bar source/clock mismatch')
        seen = set()
        for item in strict(payload(receipt)):
            require(isinstance(item, list) and len(item) == 12 and type(item[0]) is int and type(item[6]) is int,
                    'official kline schema required')
            start = item[0]; end = item[6] + 1
            require(start not in seen and start <= receipt['receipt_ms'] // INTERVAL * INTERVAL, 'duplicate/future kline')
            seen.add(start)
            require(start % INTERVAL == 0 and end == start + INTERVAL, 'inclusive closeTime+1 boundary mismatch')
            # Official latest responses include the running bar; it is never a cause.
            if end > receipt['receipt_ms']: continue
            o, h, l, c = [number(v) for v in item[1:5]]
            require(0 < l <= min(o, c) <= max(o, c) <= h and number(item[5]) >= 0, 'invalid OHLC')
            row = {'start': start, 'end': end, 'open': str(o), 'high': str(h), 'low': str(l), 'close': str(c)}
            require(start not in rows or rows[start] == row, 'conflicting public bars')
            rows[start] = row
    result = [rows[t] for t in sorted(rows)]
    require(result and all(b['start'] == a['end'] for a, b in zip(result, result[1:])), 'missing completed warmup/history bars')
    return result


def fx_from(receipt, call):
    require(receipt['category'] == 'fx' and receipt['receipt_ms'] <= call, 'FX source/availability mismatch')
    rows = list(csv.reader(io.StringIO(payload(receipt).decode('utf-8-sig'))))
    require(rows and rows[0] in (['DATE', 'DEXCHUS'], ['observation_date', 'DEXCHUS']), 'official FX CSV schema required')
    today = datetime.fromtimestamp(call / 1000, timezone.utc).date()
    values = []
    for row in rows[1:]:
        require(len(row) == 2, 'FX CSV width')
        day = datetime.strptime(row[0], '%Y-%m-%d').date()
        if row[1] in ('', '.'): continue
        value = number(row[1]); require(value > 0, 'FX positive rate required')
        if day < today: values.append((day, value))
    require(values and len({d for d, _ in values}) == len(values), 'missing/duplicate prior-date FX')
    day, rate = max(values)
    require((today - day).days <= 7, 'stale prior-date FX')
    return {'day': str(day), 'cny_per_usdt': str(rate), 'usd_usdt_assumption': '1', 'conversion_fee': str(FX_FEE),
            'source_sha256': receipt['sha256']}


def book_from(receipts, call):
    grouped = {}
    for r in receipts:
        require(r['request_ms'] <= r['receipt_ms'] <= call and call - r['request_ms'] <= MAX_AGE, 'stale/future public receipt')
        grouped.setdefault(r['category'], []).append(r)
    result = {'missing': []}
    for category in ('depth', 'trades', 'instrument', 'mark' if KIND == 'perp' else 'trades'):
        if category not in grouped: result['missing'].append(category)
    if result['missing']: return result
    require(all(len(grouped[c]) == 1 for c in ('depth', 'instrument')), 'duplicate current snapshot category')
    depth = strict(payload(grouped['depth'][0])); trade_rows = {}
    for receipt in grouped['trades']:
        for row in strict(payload(receipt)):
            require(type(row['a']) is int and type(row['T']) is int and row['T'] <= receipt['receipt_ms'] and
                    number(row['p']) > 0 and number(row['q']) > 0, 'official aggregate-trade schema required')
            require(row['a'] not in trade_rows or trade_rows[row['a']] == row, 'conflicting aggregate trades')
            trade_rows[row['a']] = row
    trades = [trade_rows[i] for i in sorted(trade_rows)]
    require(all(a['T'] <= b['T'] for a, b in zip(trades, trades[1:])), 'unordered aggregate trades')
    require(type(depth['lastUpdateId']) is int and trades and isinstance(trades, list), 'official depth/trade schema')
    last = trades[-1]
    require(type(last['T']) is int and 0 <= call - last['T'] <= MAX_AGE and
            last['T'] <= max(r['receipt_ms'] for r in grouped['trades']), 'stale/future public trade')
    trade = number(last['p']); require(trade > 0, 'invalid public trade price')
    for side, descending in [('bids', True), ('asks', False)]:
        levels = [(number(p), number(q)) for p, q in depth[side]]
        require(levels and all(p > 0 and q > 0 for p, q in levels) and
                all((a[0] > b[0] if descending else a[0] < b[0]) for a, b in zip(levels, levels[1:])), 'invalid executable depth')
        result[side] = [[str(p), str(q)] for p, q in levels]
    require(number(result['bids'][0][0]) < number(result['asks'][0][0]), 'crossed executable book')
    instruments = strict(payload(grouped['instrument'][0]))['symbols']
    instruments = [v for v in instruments if v['symbol'] == 'BTCUSDT']
    require(len(instruments) == 1 and instruments[0]['status'] == 'TRADING' and
            instruments[0]['baseAsset'] == 'BTC' and instruments[0]['quoteAsset'] == 'USDT', 'BTCUSDT instrument not trading')
    instrument = instruments[0]
    if KIND == 'perp': require(instrument['contractType'] == 'PERPETUAL' and instrument['marginAsset'] == 'USDT', 'wrong perpetual market')
    filters = {r['filterType']: r for r in instrument['filters']}
    require(len(filters) == len(instrument['filters']), 'duplicate instrument filter')
    for key in ('LOT_SIZE', 'MARKET_LOT_SIZE', 'PRICE_FILTER'):
        require(key in filters, 'missing instrument size/tick filter')
    require('MIN_NOTIONAL' in filters or 'NOTIONAL' in filters, 'missing minimum notional')
    result.update(instrument=instrument, trade=str(trade), mark=str(trade), trades=trades,
                  trade_sources=[r['sha256'] for r in grouped['trades']])
    if KIND == 'perp':
        if 'dfii10' in grouped:
            require(len(grouped['dfii10']) == 1, 'duplicate DFII10 source')
            result['dfii10'] = dfii_from(grouped['dfii10'][0], call)
        mark = strict(payload(grouped['mark'][0]))
        require(mark['symbol'] == 'BTCUSDT' and type(mark['time']) is int and
                0 <= call - mark['time'] <= MAX_AGE and mark['time'] <= grouped['mark'][0]['receipt_ms'], 'wrong/stale/future mark')
        require(number(mark['markPrice']) > 0, 'invalid mark')
        result['mark'] = str(number(mark['markPrice']))
    return result


def floor(value, step):
    require(step > 0, 'positive step required')
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step


def quantity_limit(raw, price, instrument):
    filters = {r['filterType']: r for r in instrument['filters']}
    sizes = [filters[k] for k in ('LOT_SIZE', 'MARKET_LOT_SIZE')]
    from math import lcm
    steps = [number(v['stepSize']) for v in sizes if number(v['stepSize']) > 0]
    require(steps, 'unknown market quantity step')
    unit = D(10) ** min(v.as_tuple().exponent for v in steps)
    step = unit * lcm(*(int(s / unit) for s in steps))
    q = floor(min(raw, *(number(v['maxQty']) for v in sizes)), step)
    minimum = filters.get('NOTIONAL', filters.get('MIN_NOTIONAL'))
    min_notional = number(minimum.get('minNotional', minimum.get('notional')))
    if q < max(number(v['minQty']) for v in sizes) or q * price < min_notional: return D(0)
    if 'maxNotional' in minimum and number(minimum['maxNotional']) > 0 and q * price > number(minimum['maxNotional']):
        q = floor(number(minimum['maxNotional']) / price, step)
    return q


def execution(book, side, requested):
    """Conservative deepest consumed price plus explicit adverse slip reserve."""
    levels = book['asks' if side == 'BUY' else 'bids']
    capacity = sum((number(q) for _, q in levels), D(0))
    qty = min(requested, capacity); left = qty; price = D(0)
    for p, q in levels:
        if left <= 0: break
        price = number(p); left -= min(left, number(q))
    price *= 1 + SLIP if side == 'BUY' else 1 - SLIP
    require(price > 0, 'no executable depth')
    return qty, price


def initial_engine():
    if KIND == 'spot':
        from spotquant.model import Model, SLEEVES
        return {'models': {str(w): Model(w).checkpoint() for w in SLEEVES}, 'positions': {}, 'owners': {}}
    from coinquant.campaign import Campaign
    from coinquant.linear_account import Account
    return {'campaign': Campaign().checkpoint(), 'account': {k: str(v) for k, v in asdict(Account(D(0))).items()},
            'committed_target': None}


def advance(engine, bars, *, bootstrap=False):
    if KIND == 'spot':
        from spotquant.model import Model
        for window, saved in engine['models'].items():
            model = Model.restore(saved); position = engine['positions'].get(window)
            if position:
                model.position_peak = number(position['peak'])
            for bar in bars:
                if model.last is None or bar['start'] > model.last:
                    model.update(bar['start'], bar['high'], bar['low'], bar['close'])
            if position: position['peak'] = str(model.position_peak)
            if bootstrap: model.note_flat()
            engine['models'][window] = model.checkpoint()
    else:
        from coinquant.campaign import Campaign
        model = Campaign.restore(engine['campaign'])
        for bar in bars:
            if bar['end'] > model.last: model.update(bar['end'], bar['high'], bar['low'], bar['close'])
        if bootstrap:
            model.consumed = model.primary_consumed = model.model.active.identity if model.model.active else None
        engine['campaign'] = model.checkpoint()


def seal(state):
    body = copy.deepcopy(state); body.pop('sha256', None)
    body['sha256'] = sha(dump(body))
    return body


def initialize(path, export, export_sha, review_sha, history, fx_url=FX_URL):
    path = Path(path)
    require(not path.exists(), 'exclusive new diary required')
    binding, export_raw = validate_export(export, export_sha, review_sha)
    initialized = now_ms()
    history = strict(Path(history).read_bytes())
    bars = bars_from(history, initialized)
    require(bars[-1]['end'] == initialized // INTERVAL * INTERVAL, 'warmup must reach latest completed interval')
    engine = initial_engine(); advance(engine, bars, bootstrap=True)
    receipts_dir = path.parent / (path.name + '.observations')
    fx_receipt = acquire(fx_url, receipts_dir); recorded = now_ms()
    fx = fx_from(fx_receipt, recorded)
    wallet = D(10000) / number(fx['cny_per_usdt']) * (1 - FX_FEE)
    if KIND == 'perp': engine['account']['wallet'] = str(wallet)
    state = {'format': 'btc-edge-forward-ledger-v1', 'project': KIND, 'binding': binding,
             'initialized_ms': initialized, 'initialized_utc': utc(initialized), 'recorded_at_ms': recorded,
             'initial_cny': '10000', 'initial_fx': fx, 'initial_wallet': str(wallet), 'initial_receipts': history + [fx_receipt],
             'initial_engine': copy.deepcopy(engine), 'engine': engine, 'wallet': str(wallet), 'btc': '0',
             'fees': '0', 'funding': '0', 'last_interval': bars[-1]['end'], 'events': [],
             'unresolved': [], 'native_cases': 0, 'actual_account_days': 0, 'qualification': 'NOT_QUALIFIED',
             'execution': 'DECLARED_MODELED_FILLS_ONLY', 'continuous_equity': False,
             'assumptions': {'fee': str(FEE), 'adverse_slippage': str(SLIP), 'fx_fee': str(FX_FEE),
                             'protection': 'unknown between manual observations without complete public path'}}
    # Initialization clock is actual start, never supplied by caller. No warmup fill.
    require(validate_export(export, export_sha, review_sha)[0] == binding and Path(export).read_bytes() == export_raw,
            'binding changed during initialization')
    for r in state['initial_receipts']: payload(r)
    new_file(path, dump(seal(state)))
    return seal(state)


def audit(state):
    body = dict(state); digest = body.pop('sha256')
    require(sha(dump(body)) == digest and state['format'] == 'btc-edge-forward-ledger-v1' and state['project'] == KIND,
            'ledger/checkpoint checksum or identity mismatch')
    require(state['initial_cny'] == '10000' and state['initialized_utc'] == utc(state['initialized_ms']), 'initial capital/clock identity mismatch')
    require(state['native_cases'] == state['actual_account_days'] == 0 and state['qualification'] == 'NOT_QUALIFIED', 'qualification cannot change')
    wallet, q, fees, funding, entry = number(state['initial_wallet']), D(0), D(0), D(0), D(0)
    last_record, last_interval = state['recorded_at_ms'], state['initialized_ms'] // INTERVAL * INTERVAL
    ids = set()
    for event in state['events']:
        require(event['id'] not in ids and event['id'] == len(ids) + 1 and
                last_record <= event['request_ms'] <= event['receipt_ms'] <= event['decision_ms'] <= event['recorded_at_ms'] and
                event['interval_end'] > max(last_interval, state['initialized_ms']) and
                event['interval_end'] == event['decision_ms'] // INTERVAL * INTERVAL,
                'event identity/clock/backfill mismatch')
        ids.add(event['id']); last_record = event['recorded_at_ms']; last_interval = event['interval_end']
        for item in event['money']:
            amount, price, fee = number(item.get('qty', '0')), number(item.get('price', '0')), number(item.get('fee', '0'))
            if item['kind'] == 'funding':
                cost = number(item['cost'])
                require(KIND == 'perp' and state['initialized_ms'] < item['time'] <= event['receipt_ms'] and
                        cost == q * number(item['mark']) * number(item['rate']), 'funding cashflow mismatch')
                wallet -= cost; funding += cost
            else:
                require(amount > 0 and price > 0 and fee == amount * price * FEE and item['modeled'] is True, 'modeled fill/fee mismatch')
                if item['kind'] == 'buy':
                    if KIND == 'spot': wallet -= amount * price + fee
                    else:
                        wallet -= fee; entry = (q * entry + amount * price) / (q + amount)
                    q += amount
                elif item['kind'] == 'sell':
                    require(amount <= q, 'ledger short/unowned sale')
                    wallet += amount * (price if KIND == 'spot' else price - entry) - fee
                    q -= amount
                    if not q: entry = D(0)
                else: raise ValueError('unknown money entry')
                fees += fee
        mark = number(event['mark'])
        equity = wallet + q * (mark if KIND == 'spot' else mark - entry)
        require(all(number(event[k]) == v for k, v in [('wallet', wallet), ('btc', q), ('fees', fees), ('funding', funding), ('equity_usdt', equity)]), 'event money reconstruction mismatch')
        require(number(event['equity_cny']) == equity * number(event['fx']['cny_per_usdt']) * (1 - FX_FEE) and
                number(event['net_pnl_cny']) == number(event['equity_cny']) - D(10000), 'net CNY accounting mismatch')
    require(all(number(state[k]) == v for k, v in [('wallet', wallet), ('btc', q), ('fees', fees), ('funding', funding)]), 'terminal ledger reconstruction mismatch')
    if KIND == 'spot':
        from spotquant.model import Model
        require(sum((number(p['qty']) for p in state['engine']['positions'].values()), D(0)) == q, 'sleeve ownership mismatch')
        for saved in state['engine']['models'].values(): Model.restore(saved)
    else:
        from coinquant.campaign import Campaign
        model = Campaign.restore(state['engine']['campaign'])
        account = state['engine']['account']
        require(number(account['wallet']) == wallet and number(account['q']) == q and number(account['entry']) == entry and
                number(account['fees']) == fees and number(account['funding']) == funding and
                bool(q) == (model.position_campaign is not None), 'campaign/account checkpoint ownership mismatch')
    require(state['last_interval'] == last_interval, 'checkpoint interval mismatch')
    initial_bars = bars_from([r for r in state['initial_receipts'] if r['category'] == 'bars'], state['initialized_ms'])
    initial = initial_engine(); advance(initial, initial_bars, bootstrap=True)
    fx_receipts = [r for r in state['initial_receipts'] if r['category'] == 'fx']
    require(len(fx_receipts) == 1, 'initial FX receipt missing')
    fx = fx_from(fx_receipts[0], state['recorded_at_ms'])
    require(fx == state['initial_fx'] and number(state['initial_wallet']) == D(10000) / number(fx['cny_per_usdt']) * (1 - FX_FEE), 'initial capital/FX mismatch')
    if KIND == 'perp': initial['account']['wallet'] = state['initial_wallet']
    require(initial == state['initial_engine'] and initial_bars[-1]['end'] == state['initialized_ms'] // INTERVAL * INTERVAL, 'cold-start checkpoint differs from raw history')
    replay = copy.deepcopy(state)
    replay.update(events=[], engine=initial, wallet=state['initial_wallet'], btc='0', fees='0', funding='0', unresolved=[], last_interval=initial_bars[-1]['end'])
    for event in state['events']:
        replay = apply_observation(replay, event['receipts'], event['decision_ms'], event['recorded_at_ms'], bool(event['skipped_intervals']), event['current_source'])
        require(replay['events'][-1] == event, 'proposal/execution/raw replay mismatch')
    require(replay['engine'] == state['engine'] and replay['unresolved'] == state['unresolved'], 'checkpoint differs from independently replayed ownership/protection')
    return True


def passive_fills(state, book, call):
    """Only a complete retained public print path can prove a modeled trigger.

    Even then the print is a declared passive-fill proxy with an adverse reserve,
    not a native execution. Insufficient print size remains ambiguous. Futures
    trigger on marks; trade prints cannot prove that path and remain unknown.
    """
    if not number(state['btc']): return [], True
    if KIND == 'perp' or book['missing'] or not state['events']:
        return [], False
    prior = state['events'][-1]
    anchor = prior.get('trade_anchor')
    if anchor is None: return [], False
    rows = [r for r in book['trades'] if r['a'] > anchor['a']]
    if not rows or rows[0]['a'] != anchor['a'] + 1 or any(b['a'] != a['a'] + 1 for a, b in zip(rows, rows[1:])):
        return [], False
    # The preceding manual decision happened after the anchor print. An entry
    # cannot receive a historical trigger from prints preceding its actual fill.
    positions = state['engine']['positions']; money = []; remaining = set(positions)
    for row in rows:
        capacity = number(row['q'])
        for w in sorted(remaining):
            p = positions[w]
            if row['T'] <= max(prior['decision_ms'], p['first_ms']): continue
            if number(row['p']) > number(p['stop']): continue
            qty = number(p['qty'])
            if capacity < qty: return [], False
            capacity -= qty
            price = number(row['p']) * (1 - SLIP)
            money.append(dict(kind='sell', qty=str(qty), price=str(price), fee=str(qty * price * FEE),
                              modeled=True, time=row['T'], slippage_reserve=str(SLIP), sleeves=[w],
                              passive=True, trigger_stop=p['stop'], trade_id=row['a'], public_print_price=row['p'],
                              source_sha256=book['trade_sources']))
            remaining.remove(w)
    # No claim that the empty interval after the last print was observed. Spot
    # market stop triggers use trades; latest official trade is our observation.
    from spotquant.model import Model
    for item in money:
        w = item['sleeves'][0]
        model = Model.restore(state['engine']['models'][w]); model.note_exit(); model.enter = False
        state['engine']['models'][w] = model.checkpoint()
        del positions[w]; state['engine']['owners'].pop(w, None)
    return money, True


def protection_check(state, bars, book):
    """OHLC never resolves trigger order or claims an exact passive fill."""
    if not number(state['btc']): return []
    if KIND == 'spot':
        stops = [number(p['stop']) for p in state['engine']['positions'].values()]
        touched = any(number(b['low']) <= max(stops) for b in bars)
    else:
        a = state['engine']['account']
        touched = any(number(b['low']) <= number(a['sl']) or number(b['high']) >= number(a['tp']) for b in bars)
    causes = []
    if touched: causes.append('protective_path_ambiguous_OHLC_no_exact_fill')
    if bars[0]['start'] > state['last_interval']: causes.append('unobserved_protective_history_gap')
    # Incomplete current interval has no full path evidence. Current price through
    # a stop is uncertainty about the resting venue order, never a new client fill.
    if not book['missing']:
        mark = number(book['mark'])
        if KIND == 'spot': current_touch = mark <= max(stops)
        else: current_touch = mark <= number(a['sl']) or mark >= number(a['tp'])
        if current_touch: causes.append('current_mark_through_modeled_protection')
    return causes


def funding_entries(state, receipts, call):
    if KIND != 'perp': return [], []
    previous = state['events'][-1]['decision_ms'] if state['events'] else state['initialized_ms']
    expected = set(range((previous // 28800000 + 1) * 28800000, call + 1, 28800000))
    events = {}; q = number(state['btc'])
    for receipt in receipts:
        if receipt['category'] != 'funding': continue
        rows = strict(payload(receipt))
        require(isinstance(rows, list), 'official settled funding list required')
        for row in rows:
            stamp = row['fundingTime']
            require(row['symbol'] == 'BTCUSDT' and type(stamp) is int and stamp <= receipt['receipt_ms'], 'future/wrong settled funding')
            rate, mark = number(row['fundingRate']), number(row['markPrice'])
            require(mark > 0 and abs(rate) < 1, 'invalid observed settled funding')
            if previous < stamp <= call:
                require(stamp not in events, 'duplicate settled funding')
                events[stamp] = dict(kind='funding', time=stamp, rate=str(rate), mark=str(mark),
                                     cost=str(q * mark * rate), source_sha256=receipt['sha256'])
    # Missing actual settlements never mean zero. This strict schedule refuses
    # jittered/changed schedules until their official coverage adapter is reviewed.
    missing = expected - set(events)
    causes = ['missing_settled_funding_coverage'] if missing and q else []
    return [events[t] for t in sorted(events) if q], causes


def spot_decide(state, bars, book, call, enabled):
    from spotquant.model import Model
    from spotquant.preview import decision
    engine = state['engine']; positions = engine['positions']; models = {}
    owned = {}
    for w, saved in engine['models'].items():
        model = Model.restore(saved); p = positions.get(w)
        if p: model.position_peak = number(p['peak'])
        models[int(w)] = model; owned[int(w)] = number(p['qty']) if p else D(0)
    snap = dict(btc=state['btc'], usdt_free=state['wallet'], avg_price=book.get('mark', bars[-1]['close']), open_orders=[])
    proposal = decision(models, owned, snap, positions={int(w): p for w, p in positions.items()},
                        owners=engine['owners'], entries_enabled=enabled,
                        capital_limit=number(state['initial_wallet']))
    money, simulated = [], []
    if book['missing'] or state['unresolved']:
        return proposal, money, [{'status': 'preview_only', 'reason': 'missing executable evidence or unresolved protection'}]
    wallet = number(state['wallet'])
    for order in proposal['orders']:
        side = order['side']; group = [str(w) for w in order['sleeves']]
        if side == 'BUY':
            require(not any(w in positions for w in group), 'Spot held sleeves cannot top up')
            budget = min(number(order['quoteOrderQty']), wallet / (1 + FEE))
            requested = budget / number(book['asks'][0][0])
        else: requested = sum((number(positions[w]['qty']) for w in group), D(0))
        qty, price = execution(book, side, requested)
        if side == 'BUY': qty = min(qty, budget / price)
        qty = quantity_limit(qty, price, book['instrument'])
        if side == 'BUY': qty = floor(qty, D('.00001'))
        if not qty:
            simulated.append({'status': 'rejected', 'reason': 'minimum_or_depth', 'order': order}); continue
        filters = {r['filterType']: r for r in book['instrument']['filters']}
        tick = number(filters['PRICE_FILTER']['tickSize'])
        stops = {}
        for w in group:
            model = models[int(w)]
            atr = model.atr14
            if side == 'BUY':
                require(atr is not None, 'ATR protection warmup missing')
                trail = min(D('.30'), max(D('.10'), 4 * atr / model.close))
                stops[w] = floor(price * (1 - trail), tick)
                require(number(filters['PRICE_FILTER']['minPrice']) <= stops[w] <= number(filters['PRICE_FILTER']['maxPrice']) and
                        0 < stops[w] < min(price, number(book['mark'])), 'unplaceable entry protection')
        fee = qty * price * FEE
        money.append({'kind': 'buy' if side == 'BUY' else 'sell', 'qty': str(qty), 'price': str(price),
                      'fee': str(fee), 'modeled': True, 'time': call, 'slippage_reserve': str(SLIP), 'sleeves': group,
                      'opportunity_interval': bars[-1]['end']})
        simulated.append({'status': 'modeled_fill', 'requested': str(requested), 'accepted': str(qty), 'price': str(price), 'fee': str(fee)})
        wallet += (-qty * price - fee) if side == 'BUY' else (qty * price - fee)
        left = qty
        for index, w in enumerate(group):
            model = models[int(w)]
            if side == 'BUY':
                part = left if index == len(group) - 1 else floor(qty / len(group), D('.00001'))
                left -= part
                if not part: continue
                model.note_entry(price, peak=price)
                if model.cap_enter: model.note_cap_entry()
                positions[w] = dict(qty=str(part), peak=str(price), entry_fill=str(price), first_ms=call, stop=str(stops[w]))
            else:
                part = min(left, number(positions[w]['qty'])); left -= part
                positions[w]['qty'] = str(number(positions[w]['qty']) - part)
                if not number(positions[w]['qty']):
                    del positions[w]; model.note_exit(); model.enter = False
            engine['models'][w] = model.checkpoint()
    # Amend only at this manual observation; allocated floors never loosen.
    for w, p in positions.items():
        model = models[int(w)]
        atr = model.atr14
        stop = max(number(p['stop']), number(p['peak']) * (1 - min(D('.30'), max(D('.10'), 4 * atr / model.close))))
        tick = number(next(f['tickSize'] for f in book['instrument']['filters'] if f['filterType'] == 'PRICE_FILTER'))
        p['stop'] = str(floor(stop, tick))
        engine['owners'][w] = {'order': {'type': 'STOP_LOSS', 'stopPrice': p['stop']}, 'sleeves': [int(w)],
                               'native_status': 'NEW', 'signal_ms': call, 'modeled_only': True}
    engine['owners'] = {w: p for w, p in engine['owners'].items() if w in positions}
    return proposal, money, simulated


def coin_decide(state, bars, book, call, enabled):
    from coinquant.campaign import Campaign
    from coinquant.linear_preview import preview
    from coinquant.linear_account import Account
    from coinquant.linear_sizing import funded_target
    model = Campaign.restore(state['engine']['campaign'])
    account = Account(**{k: number(v) for k, v in state['engine']['account'].items()})
    missing_macro = model.macro_relevant() and 'dfii10' not in book
    # No fabricated macro row: relevant missing public vintage evidence blocks
    # new risk. Existing macro ownership is left explicitly unresolved.
    if missing_macro:
        if account.q: state['unresolved'].append('missing_causal_DFII10_for_owned_macro')
        proposal = {'action': 'blocked', 'reason': 'causal DFII10 raw vintage evidence required', 'opportunity': None}
    else:
        model.select_macro(book.get('dfii10'), book.get('mark', bars[-1]['close']), call, bootstrap=not state['events'])
        proposal = preview(model, dict(quantity_btc=str(account.q), native_full_position_protected=True, stop_before_liquidation=True))
        if proposal['opportunity'] is not None: proposal['opportunity'] = {k: str(v) if isinstance(v, D) else v for k, v in asdict(proposal['opportunity']).items()}
    money, simulated = [], []
    action = proposal['action']
    if book['missing'] or state['unresolved'] or (action == 'enter' and not enabled):
        return proposal, money, [{'status': 'preview_only', 'reason': 'missing evidence/cold start/unresolved protection'}]
    if action == 'enter':
        opportunity = model.active
        require(opportunity is not None and opportunity.direction == 1, 'no shorts allowed')
        fraction = model.entry_fraction(str(SLIP)); requested = account.equity(number(book['mark'])) * fraction / max(number(book['asks'][0][0]), number(book['mark']))
        capacity, price = execution(book, 'BUY', requested)
        filters = {r['filterType']: r for r in book['instrument']['filters']}
        tick = number(filters['PRICE_FILTER']['tickSize'])
        sl, tp = floor(opportunity.stop, tick), floor(opportunity.take, tick)
        limits = filters['PRICE_FILTER']
        if not number(limits['minPrice']) <= sl < tp <= number(limits['maxPrice']):
            result = dict(requested=str(requested), accepted='0', reason='instrument_protection_price_bounds')
        else:
            result = funded_target(account, 1, fraction, price, number(book['mark']), sl, tp,
                                   quantity_limit(capacity, price, book['instrument']), book['instrument'], intended_add=True)
        simulated.append({k: str(v) if isinstance(v, D) else v for k, v in result.items()})
        amount = number(result['accepted'])
        if amount:
            model.filled(opportunity.identity)
            state['engine']['committed_target'] = {'quantity': str(account.q), 'opportunity': opportunity.identity,
                                                    'created_ms': call, 'expires': opportunity.expires}
            money.append(dict(kind='buy', qty=str(amount), price=str(price), fee=str(amount * price * FEE),
                              modeled=True, time=call, slippage_reserve=str(SLIP), opportunity=opportunity.identity))
    elif action == 'exit' and account.q:
        qty, price = execution(book, 'SELL', account.q)
        qty = quantity_limit(qty, price, book['instrument'])
        if not qty:
            simulated.append({'status': 'rejected', 'reason': 'minimum_or_depth', 'requested': str(account.q), 'accepted': '0'})
        if qty:
            simulated.append({'status': 'modeled_fill', 'requested': str(account.q), 'accepted': str(qty), 'price': str(price)})
            account.close(qty, price)
            money.append(dict(kind='sell', qty=str(qty), price=str(price), fee=str(qty * price * FEE),
                              modeled=True, time=call, slippage_reserve=str(SLIP)))
            if not account.q:
                model.position_campaign = None; state['engine']['committed_target'] = None
    state['engine']['campaign'] = model.checkpoint()
    state['engine']['account'] = {k: str(v) for k, v in asdict(account).items()}
    return proposal, money, simulated


def apply_observation(state, receipts, call, recorded, declared_gap, current_source):
    """Pure deterministic transition; audit replays this from retained raw bytes."""
    opening_balances = {k: state[k] for k in ('wallet', 'btc', 'fees', 'funding')}
    bars = bars_from([r for r in receipts if r['category'] == 'bars'], call)
    latest = bars[-1]['end']
    require(latest == call // INTERVAL * INTERVAL and
            all(latest == r['receipt_ms'] // INTERVAL * INTERVAL for r in receipts), 'only latest completed interval at actual receipt/decision allowed')
    require(latest > max(state['last_interval'], state['initialized_ms']), 'no backfill/duplicate/preinitialization decision')
    gap = (latest - state['last_interval']) // INTERVAL - 1
    require(not gap or declared_gap is True, 'skipped periods must be declared')
    new_bars = [b for b in bars if b['end'] > state['last_interval']]
    require(new_bars and new_bars[0]['start'] == state['last_interval'], 'complete causal bars required across declared gaps')
    book = book_from(receipts, call)
    fx_rows = [r for r in receipts if r['category'] == 'fx']
    require(len(fx_rows) == 1, 'one current prior-date FX source required')
    fx = fx_from(fx_rows[0], call)
    passive, path_proven = passive_fills(state, book, call)
    causes = [] if path_proven else protection_check(state, new_bars, book)
    if number(state['btc']) and not path_proven: causes.append('incomplete_public_protection_path')
    if passive:
        # Passive exits precede the manual strategy decision and cannot supply a
        # new same-call BUY. Record the opportunity as consumed via note_exit.
        state['btc'] = str(number(state['btc']) - sum((number(x['qty']) for x in passive), D(0)))
        state['wallet'] = str(number(state['wallet']) + sum((number(x['qty']) * number(x['price']) - number(x['fee']) for x in passive), D(0)))
        state['fees'] = str(number(state['fees']) + sum((number(x['fee']) for x in passive), D(0)))
    funding, funding_causes = funding_entries(state, receipts, call)
    state['unresolved'] = list(dict.fromkeys(state['unresolved'] + causes + funding_causes))
    advance(state['engine'], new_bars)
    if KIND == 'perp':
        from coinquant.linear_account import Account
        a = Account(**{k: number(v) for k, v in state['engine']['account'].items()})
        for cash in funding: a.apply_funding_cost(number(cash['cost']))
        state['engine']['account'] = {k: str(v) for k, v in asdict(a).items()}
    proposal, fills, simulated = (spot_decide if KIND == 'spot' else coin_decide)(state, new_bars, book, call, not state['unresolved'] and not passive)
    money = passive + funding + fills
    wallet, q, fees, total_funding = [number(opening_balances[k]) for k in ('wallet', 'btc', 'fees', 'funding')]
    entry = number(state['events'][-1]['entry']) if state['events'] else D(0)
    for item in money:
        if item['kind'] == 'funding': wallet -= number(item['cost']); total_funding += number(item['cost']); continue
        amount, price, fee = [number(item[k]) for k in ('qty', 'price', 'fee')]
        if item['kind'] == 'buy':
            wallet -= amount * price + fee if KIND == 'spot' else fee
            if KIND == 'perp': entry = (q * entry + amount * price) / (q + amount)
            q += amount
        else:
            wallet += amount * (price if KIND == 'spot' else price - entry) - fee; q -= amount
            if not q: entry = D(0)
        fees += fee
    mark = number(book.get('mark', bars[-1]['close']))
    equity = wallet + q * (mark if KIND == 'spot' else mark - entry)
    cny = equity * number(fx['cny_per_usdt']) * (1 - FX_FEE)
    require(call <= recorded and recorded - min(r['request_ms'] for r in receipts) <= MAX_AGE, 'observation expired during decision')
    event = {'id': len(state['events']) + 1, 'request_ms': min(r['request_ms'] for r in receipts),
             'receipt_ms': max(r['receipt_ms'] for r in receipts), 'decision_ms': call, 'recorded_at_ms': recorded,
             'interval_end': latest, 'skipped_intervals': gap, 'receipts': receipts, 'proposal': proposal,
             'simulated': simulated, 'money': money, 'wallet': str(wallet), 'btc': str(q), 'fees': str(fees),
             'funding': str(total_funding), 'entry': str(entry), 'mark': str(mark), 'fx': fx,
             'equity_usdt': str(equity), 'equity_cny': str(cny), 'net_pnl_cny': str(cny - D(10000)),
             'net_pnl_usdt': str(equity - number(state['initial_wallet'])), 'missing': book['missing'],
             'unresolved': list(state['unresolved']), 'performance_qualified': False,
             'conditional_equity': bool(state['unresolved']),
             'trade_anchor': book['trades'][-1] if not book['missing'] else None,
             'current_source': current_source}
    state.update(wallet=str(wallet), btc=str(q), fees=str(fees), funding=str(total_funding), last_interval=latest)
    state['events'].append(event)
    return seal(state)


def observe(path, export, export_sha, review_sha, urls, *, declared_gap=False):
    """One manual read/decide/model/record cycle. No caller clock or prices."""
    path = Path(path)
    with (path.parent / (path.name + '.lock')).open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        original = path.read_bytes(); state = strict(original)
        binding, export_raw = validate_export(export, export_sha, review_sha)
        require({k: v for k, v in binding.items() if k != 'current_source'} ==
                {k: v for k, v in state['binding'].items() if k != 'current_source'}, 'diary binding mismatch')
        audit(state)
        require(now_ms() >= state['initialized_ms'], 'wall clock before initialization')
        for r in state['initial_receipts']:
            payload(r)
        for event in state['events']:
            for r in event['receipts']: payload(r)
        receipts = [acquire(url, path.parent / (path.name + '.observations')) for url in urls]
        require(receipts, 'public observation URLs required')
        call = now_ms()
        result = apply_observation(state, receipts, call, call, declared_gap, binding['current_source'])
        recorded = now_ms()
        require(call <= recorded and recorded - min(r['request_ms'] for r in receipts) <= MAX_AGE, 'observation expired during decision')
        result['events'][-1]['recorded_at_ms'] = recorded
        result = seal(result); audit(result)
        require(validate_export(export, export_sha, review_sha)[0] == binding and Path(export).read_bytes() == export_raw,
                'source/export changed during observation')
        for r in state['initial_receipts'] + [r for e in result['events'] for r in e['receipts']]: payload(r)
        require(path.read_bytes() == original, 'diary changed outside lock')
        replace_file(path, dump(result))
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('source'); p.add_argument('--head')
    p = sub.add_parser('acquire'); p.add_argument('--url', required=True); p.add_argument('--directory', required=True); p.add_argument('--out', required=True)
    p = sub.add_parser('export'); p.add_argument('--analysis', required=True); p.add_argument('--review', required=True); p.add_argument('--bridges', required=True); p.add_argument('--out', required=True)
    for command in ('init', 'observe'):
        p = sub.add_parser(command)
        for name in ('diary', 'export', 'export-sha', 'review-sha'): p.add_argument('--' + name, required=True)
        if command == 'init': p.add_argument('--history', required=True)
        else: p.add_argument('--url', action='append', required=True); p.add_argument('--declared-gap', action='store_true')
    p = sub.add_parser('audit'); p.add_argument('--diary', required=True)
    args = parser.parse_args(argv)
    if args.command == 'source': result = source(head=args.head)
    elif args.command == 'acquire':
        result = acquire(args.url, args.directory); new_file(args.out, dump(result))
    elif args.command == 'export': result = {'sha256': export_binding(args.analysis, args.review, args.bridges, args.out)}
    elif args.command == 'init': result = initialize(args.diary, args.export, args.export_sha, args.review_sha, args.history)
    elif args.command == 'observe': result = observe(args.diary, args.export, args.export_sha, args.review_sha, args.url, declared_gap=args.declared_gap)
    else:
        state = strict(Path(args.diary).read_bytes()); result = {'audit': audit(state), 'scope': 'raw_ledger_reconstruction_only', 'source_binding_verified': False,
                  'events': len(state['events']), 'qualification': 'NOT_QUALIFIED'}
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
