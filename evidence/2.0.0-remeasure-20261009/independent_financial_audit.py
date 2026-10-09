"""Read-only audit of new independent replay receipts; never imports production."""
import argparse
import bisect
from collections import Counter
import csv
from datetime import datetime, timezone
from decimal import Decimal as D
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
ORIGINAL = ROOT
HELPER_SHA = 'b8d097a60f390da0cc95f5424ff2f8649c7250045fa82ba5e3c7f7acffd3145e'
FEE = D('.00075')
TOLERANCE = D('.00000001')  # Original ledger audit tolerance, never applied to arm differences.


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    path = Path(path)
    with (gzip.open(path, 'rt') if path.suffix == '.gz' else path.open()) as stream:
        return json.load(stream)


require(sha(ORIGINAL / 'original_compare_arms.py') == HELPER_SHA, 'original read-only utility changed')
loader = importlib.util.spec_from_file_location('original_audit_utilities', ORIGINAL / 'original_compare_arms.py')
helper = importlib.util.module_from_spec(loader)
loader.loader.exec_module(helper)
digest, differences = helper.digest, helper.exact_differences


def near(a, b, reason):
    require(abs(D(a) - D(b)) <= TOLERANCE, reason)


def source_and_inputs(row, arm, spec, spec_path, full):
    s = row['source']
    registration_root = spec_path.resolve().parent
    runtime = Path(spec['runtime_roots'][arm]).resolve()
    actual = {str(p.relative_to(runtime)): sha(p) for p in sorted((runtime / 'coinquant').glob('*.py'))}
    require(len(actual) == 19 and actual == s['files'] == read(spec['source_files_by_arm'][arm]), 'production bytes')
    require(s['git_head'] == spec['runtime_heads'][arm] and s['runtime_module'] == str(runtime / 'coinquant/session.py'), 'runtime identity')
    tooling = Path(spec['tooling_root']).resolve()
    tools = {str(p.relative_to(tooling)): sha(p) for p in sorted((tooling/'research').glob('*.py'))}
    require(tools == s['tooling_files'], 'measurement module bytes')
    producer = sha(tooling/'driver.py')
    require(producer == s['producer_sha256'] == spec['producer_sha256'], 'driver bytes')
    packet = dict(actual)
    packet.update({'tooling/' + k: v for k, v in tools.items()})
    packet['tooling/driver.py'] = producer
    require(digest(packet) == s['source_sha256'] == spec['source_sha256_by_arm'][arm] == row['binding']['source_sha256'], 'source digest')
    require(row['binding']['producer_sha256'] == producer, 'producer binding')
    inp = row['inputs']
    starts = read(spec['schedule'])['primary']['starts_ms']
    require(len(starts) == 795 and starts == sorted(set(starts)) and starts[0] == 1577836800000, 'original795 schedule')
    require(inp['starts_ms'] == (starts if full else starts[:6]), 'actual schedule binding')
    for name, field in (('schedule', 'schedule_sha256'), ('fx', 'fx_sha256'), ('qualified_metadata', 'qualified_metadata_sha256')):
        require(sha(spec[name]) == inp[field], 'input SHA ' + name)
    require(inp['schedule_sha256'] == 'c21b4fcfe3cb12fb062bb01d3c3591aa0ee8c65db9e9afde3c26b1bcdc2ac28e', 'original schedule SHA')
    require(inp['specification_sha256'] == sha(spec_path), 'new specification binding')
    require(inp['parser_sha256'] == spec['parser_sha256'] == sha(tooling/'research/session_market.py'), 'parser identity')
    sidecars = {str(p.resolve()): p.read_text() for k in ('prints', 'market') for p in sorted(Path(spec[k]).rglob('*.CHECKSUM'))}
    require(inp['official_sidecars'] == sidecars, 'original sidecar bytes')
    require(digest(inp) == row['binding']['input_sha256'], 'input packet digest')
    require(digest(row['strategy']) == row['binding']['strategy_sha256'], 'strategy registration digest')
    for key, value in {'primary_risk': '7.5', 'macro_risk': '3.6', 'session_seconds': 300,
                       'poll_seconds': 5, 'read_latency_ms': 200, 'write_latency_ms': 1000,
                       'mark_gap': 'bound', 'matcher': 'trade_print', 'uid': '12000'}.items():
        require(row['strategy'][key] == value, 'frozen economic setting ' + key)
    for key, value in spec['risk_by_arm'][arm].items():
        require(row['strategy'][key] == value, 'registered default runtime risk ' + key)
    require(inp['terminal_ms'] == row['terminal_ms'] == spec['terminal_ms'] == 1789862400000, 'exclusive terminal')
    require(inp['market_root'] == str(Path(spec['market']).resolve()) and inp['prints_root'] == str(Path(spec['prints']).resolve()), 'raw input roots')
    require(sha(spec['restored_input_identity']) == spec['restored_input_identity_sha256'], 'frozen input identity registry')
    require(sha(spec['input_manifest']) == spec['input_manifest_sha256'], 'frozen raw input manifest')
    qualification = read(spec['restored_input_identity'])
    downloaded = read(spec['download_receipt'])
    require(downloaded['complete'] is True and len(downloaded['results']) == 1164, 'all frozen inputs actually restored')
    restored = {item['relative_path']: item for item in downloaded['results']}
    require(len(restored) == 1164, 'unique restored raw inputs')
    for item in read(spec['input_manifest'])['files']:
        proof = restored[item['relative_path']]
        path = Path(spec['input_manifest']).parent / item['relative_path']
        require(proof['status'] in ('downloaded-verified', 'verified-existing')
                and proof['bytes'] == item['bytes'] and proof['sha256'] == item['sha256']
                and path.stat().st_size == item['bytes'], 'restored actual raw identity ' + item['relative_path'])
    for key in ('market_identity_sha256', 'market_values_sha256', 'macro_sha256'):
        require(inp[key] == qualification['derived_original_identities'][key], 'original economic input ' + key)
    registered = {r['name']: r for r in qualification['prints']['files']}
    require(len(registered) == 773 and sum(v['bytes'] for v in registered.values()) == 14067765753, 'original raw prints registry')
    for name, item in registered.items():
        p = Path(spec['prints']) / name
        require(p.stat().st_size == item['bytes'] and Path(str(p) + '.CHECKSUM').read_text().split() == [item['sha256'], name], 'raw print availability/identity ' + name)
    for name, value in row['financial']['loaded_print_files'].items():
        require(registered[name]['sha256'] == value, 'consumed print identity ' + name)
    minutes = {r['relative_path']: r['expected_sha256'] for r in qualification['market']['files']}
    for name, value in row['financial']['loaded_minute_files'].items():
        require(minutes.get(name) == value, 'consumed minute identity ' + name)
    return {'head': s['git_head'], 'source_sha256': s['source_sha256'], 'producer_sha256': producer,
            'input_sha256': row['binding']['input_sha256'], 'consumed_prints': len(row['financial']['loaded_print_files']),
            'consumed_minutes': len(row['financial']['loaded_minute_files']),
            'raw_identity_basis': 'original qualified receipts, available bytes/sidecars and actual loader raw SHA; no full vault rehash'}


class PublicInputs:
    def __init__(self, spec):
        self.root = Path(spec['market'])
        self.qualification = read(spec['qualified_metadata'])['qualification_maps']['files']
        self.rates, self.marks, self.files = {}, {}, {}
        for path in sorted((self.root / 'funding').glob('*.zip')):
            for row in self.rows(path):
                if not row[0].isdigit():
                    continue
                stamp, rate = int(row[0]), D(row[2])
                require(stamp not in self.rates or self.rates[stamp] == rate, 'funding input conflict')
                self.rates[stamp] = rate

    def rows(self, path):
        relative = str(path.relative_to(self.root))
        matches = [v for k, v in self.qualification.items() if k.endswith('/' + relative)]
        require(len(matches) == 1, 'raw qualification identity ' + relative)
        raw = path.read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        require(actual == matches[0]['original_content_sha256'] and len(raw) == matches[0]['metadata']['bytes'], 'official raw bytes/SHA ' + relative)
        require(Path(str(path) + '.CHECKSUM').read_text().split() == [actual, path.name], 'official sidecar ' + relative)
        self.files[relative] = {'bytes': len(raw), 'sha256': actual}
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            require(len(z.namelist()) == 1, 'single original CSV member')
            with z.open(z.namelist()[0]) as member:
                yield from csv.reader(io.TextIOWrapper(member, encoding='utf-8'))

    def mark_closes(self, needed):
        missing = set(needed) - self.marks.keys()
        months = {datetime.fromtimestamp(t / 1000, timezone.utc).strftime('%Y-%m') for t in missing}
        for month in sorted(months):
            wanted = {t for t in missing if datetime.fromtimestamp(t / 1000, timezone.utc).strftime('%Y-%m') == month}
            candidates = [self.root / 'mark/1m' / ('BTCUSDT-1m-' + month + '.zip')]
            candidates += sorted((self.root / 'mark/1m/daily').glob('BTCUSDT-1m-' + month + '-*.zip'))
            for path in candidates:
                if not path.exists():
                    continue
                for row in self.rows(path):
                    if not row[0].isdigit():
                        continue
                    stamp = int(row[0])
                    if stamp in wanted:
                        require(int(row[6]) == stamp + 59999, 'official mark minute alignment')
                        close = D(row[4])
                        require(stamp not in self.marks or self.marks[stamp] == close, 'mark input conflict')
                        self.marks[stamp] = close
            require(wanted <= self.marks.keys(), 'official funding mark unavailable')
        return self.marks


def financial(row, spec, public):
    f = row['financial']; trades = f['trades']; ledger = f['funding_ledger']
    fx_rates = read(spec['fx'])['rates']; fx_days = sorted(fx_rates)
    def fx(stamp):
        day = datetime.fromtimestamp(stamp / 1000, timezone.utc).date().isoformat()
        index = bisect.bisect_left(fx_days, day) - 1
        return D(str(fx_rates[fx_days[index]]['CNY'])) if index >= 0 else D('6.9615')
    require(D(row['initial_usdt']) == D(10000) / fx(row['inputs']['starts_ms'][0]) * D('.999'), 'initial wallet and prior FX')
    require(D(f['final_cny']) == D(f['final_usdt']) * fx(f['now_ms']) * D('.999'), 'final prior FX and exit cost')
    for day in f['daily']:
        require(D(day['equity_cny']) == D(day['equity_usdt']) * fx(day['stamp_ms']) * D('.999'), 'daily prior FX')
        require(D(day['net_btc_exposure_usdt']) == D(day['quantity_btc']) * D(day['mark_usdt']) and D(day['gross_btc_exposure_usdt']) == abs(D(day['net_btc_exposure_usdt'])), 'daily effective exposure')
    require(len({t['id'] for t in trades}) == len(trades), 'duplicate trade identity')
    require(len({r['tranId'] for r in ledger}) == len(ledger), 'duplicate income identity')
    require([t['time'] for t in trades] == sorted(t['time'] for t in trades), 'trade chronology')
    require([r['time'] for r in ledger] == sorted(r['time'] for r in ledger), 'income chronology')
    start, end = row['inputs']['starts_ms'][0], f['now_ms']
    require(all(start <= t['time'] <= end and t['time'] < spec['terminal_ms'] for t in trades), 'trade clock window')
    require(all(start <= r['time'] <= end for r in ledger), 'income clock window')
    q = entry = realized = fees = D(0)
    expected_commission, expected_realized, quantities = Counter(), Counter(), Counter()
    for t in trades:
        part, price = D(t['qty']), D(t['price'])
        require(part > 0 and price > 0 and t['side'] in ('BUY', 'SELL'), 'fill geometry')
        signed = part if t['side'] == 'BUY' else -part
        fee = part * price * FEE
        pnl = D(0)
        fees += fee; expected_commission[(t['time'], -fee)] += 1; quantities[t['orderId']] += part
        if not q or q * signed > 0:
            entry = (abs(q) * entry + part * price) / (abs(q) + part)
        else:
            pnl = min(abs(q), part) * (price - entry) * (1 if q > 0 else -1)
            realized += pnl; expected_realized[(t['time'], pnl)] += 1
            if part > abs(q):
                entry = price
        q += signed
        require(t.get('commissionAsset') == 'USDT' and D(t['commission']) == fee
                and D(t['realizedPnl']) == pnl, 'production-consumed per-fill commission and realized PnL')
        if not q:
            entry = D(0)
    require(expected_commission == Counter((r['time'], D(r['income'])) for r in ledger if r['incomeType'] == 'COMMISSION'), 'per-fill commission vs ledger')
    actual_realized = Counter((r['time'], D(r['income'])) for r in ledger if r['incomeType'] == 'REALIZED_PNL')
    require(expected_realized == actual_realized, 'per-close realized PnL vs ledger')
    totals = Counter()
    for r in ledger:
        require(r['asset'] == 'USDT' and r['symbol'] == 'BTCUSDT', 'cash ledger asset/symbol')
        totals[r['incomeType']] += D(r['income'])
    require(set(totals) <= {'COMMISSION', 'REALIZED_PNL', 'FUNDING_FEE', 'INSURANCE_CLEAR'}, 'external cash flow')
    near(q, f['position'], 'final quantity'); near(entry, f['entry'], 'final weighted entry')
    near(realized, totals['REALIZED_PNL'], 'realized total')
    near(fees - totals['INSURANCE_CLEAR'], f['fees'], 'total fees/insurance')
    near(D(row['initial_usdt']) + sum(totals.values(), D(0)), f['wallet_usdt'], 'income-reconstructed wallet')
    near(D(f['wallet_usdt']) + q * (D(f['final_mark']) - entry), f['final_usdt'], 'valued final equity')
    funding_rows = {r['time']: D(r['income']) for r in ledger if r['incomeType'] == 'FUNDING_FEE'}
    require(len(funding_rows) == sum(r['incomeType'] == 'FUNDING_FEE' for r in ledger), 'duplicate funding settlement')
    q_at, cursor, held = D(0), 0, {}
    require(all(t % 28800000 < 1000 for t in public.rates), 'original official funding jitter qualification')
    covered = {t // 28800000 for t in public.rates}
    q_grid, grid_cursor = D(0), 0
    for grid in range((start // 28800000 + 1) * 28800000, min(end + 1, spec['terminal_ms']), 28800000):
        while grid_cursor < len(trades) and trades[grid_cursor]['time'] < grid:
            t = trades[grid_cursor]; q_grid += D(t['qty']) * (1 if t['side'] == 'BUY' else -1); grid_cursor += 1
        require(not q_grid or grid // 28800000 in covered, 'missing held funding slot')
    # Official events retain their millisecond jitter; never substitute the slot boundary.
    for stamp in sorted(t for t in public.rates if start < t <= end and t < spec['terminal_ms']):
        while cursor < len(trades) and trades[cursor]['time'] < stamp:
            t = trades[cursor]; q_at += D(t['qty']) * (1 if t['side'] == 'BUY' else -1); cursor += 1
        if q_at:
            held[stamp] = q_at
    require(set(held) == set(funding_rows), 'held settlements vs actual funding event set')
    marks = public.mark_closes({stamp // 60000 * 60000 - 60000 for stamp in held})
    for stamp, quantity in held.items():
        expected = -quantity * marks[stamp // 60000 * 60000 - 60000] * public.rates[stamp]
        require(expected == funding_rows[stamp], 'funding rate/mark/quantity at ' + str(stamp))
    near(-sum(funding_rows.values(), D(0)), f['funding'], 'funding total')
    orders = {r['orderId']: r for r in f['orders'].values()}
    require(len(orders) == len(f['orders']), 'duplicate venue order ID')
    for t in trades:
        require(t['orderId'] in orders and t['side'] == orders[t['orderId']]['side'], 'fill order ownership')
    for identity, order in f['orders'].items():
        require(identity == order['clientOrderId'] and order['symbol'] == 'BTCUSDT' and order['positionSide'] == 'BOTH', 'order identity')
        require(order['status'] in ('FILLED', 'CANCELED', 'EXPIRED', 'EXPIRED_IN_MATCH', 'REJECTED'), 'unsettled ordinary order')
        require(quantities[order['orderId']] == D(order['executedQty']) <= D(order['origQty']), 'order filled quantity')
    for identity, algo in f['algos'].items():
        require(identity == algo['clientAlgoId'] and identity.startswith('cq-'), 'protection durable identity')
        child_id = int(algo['actualOrderId'])
        if child_id:
            require(algo['algoStatus'] == 'FINISHED' and child_id in orders and orders[child_id]['reduceOnly'] is True, 'protection child ownership')
    for method, path, params in f['sent']:
        if method == 'POST' and path.endswith('/order'):
            require(params['newClientOrderId'] in f['orders'], 'sent entry/exit durable identity')
        if method == 'POST' and path.endswith('/algoOrder'):
            require(params['clientAlgoId'] in f['algos'], 'sent protection durable identity')
    live = [a for a in f['algos'].values() if a['algoStatus'] == 'NEW']
    if q:
        require(len(live) == 2 and {a['orderType'] for a in live} == {'STOP_MARKET', 'TAKE_PROFIT_MARKET'}, 'full final protection')
        require(all(a['side'] == ('SELL' if q > 0 else 'BUY') and a['closePosition'] is True and a['workingType'] == 'MARK_PRICE' and a['priceProtect'] is False for a in live), 'native final protection fields')
        stop = D(next(a['triggerPrice'] for a in live if a['orderType'] == 'STOP_MARKET'))
        liq = (q * entry - D(f['margin'])) / (q - abs(q) * D('.00575'))
        require(stop > liq if q > 0 else stop < liq, 'stop before proxy liquidation')
    return {'passed': True, 'fills': len(trades), 'income': len(ledger), 'funding_events': len(held),
            'fees_usdt': str(fees - totals['INSURANCE_CLEAR']), 'funding_paid_usdt': str(-sum(funding_rows.values(), D(0))),
            'wallet_usdt': f['wallet_usdt'], 'final_quantity_btc': str(q), 'final_entry_usdt': str(entry),
            'end_live_protections': len(live), 'same_timestamp_funding': 'settlement precedes fills at identical millisecond, matching original venue arrival order'}


def path_audit(row, segments):
    f = row['financial']; a = f['path_audit']; start = row['inputs']['starts_ms'][0]
    require(a['version'] == 'readonly-path-audit-v1' and a['count'] > 0, 'path audit registration')
    require(len(a['rolling_sha256']) == 64 and all(c in '0123456789abcdef' for c in a['rolling_sha256']), 'rolling identity format')
    for series, peak, mdd, at in (('envelope', 'peak_envelope_cny', 'mdd', 'mdd_envelope_at'), ('close', 'peak_cny', 'mdd_close', 'mdd_close_at')):
        s = a[series]
        require(D(s['peak_cny']) == D(f[peak]) and D(s['mdd']) == D(f[mdd]), 'independent ' + series + ' metric')
        p = s['mdd_point']
        require((p is None) == (f[at] is None), 'drawdown event existence')
        if p:
            require(p['stamp_ms'] == f[at] and start <= p['stamp_ms'] <= f['now_ms'], 'drawdown clock')
            require(D(1) - D(p['equity_cny']) / D(p['peak_cny']) == D(s['mdd']), 'drawdown point geometry')
            require(p['peak_at_ms'] is None or start <= p['peak_at_ms'] <= p['stamp_ms'], 'peak before drawdown')
            if series == 'close':
                require(p['kind'] == 'close' and p['known_path'] is True, 'qualified close drawdown')
    require(a['first']['stamp_ms'] == start, 'first path point clock')
    near(a['first']['equity_cny'], D('10000') * D('.999') ** 2, 'initial conversion path point')
    require(start <= a['last']['stamp_ms'] <= f['now_ms'], 'last path point clock')
    require(f['known_path'] is True and a['unqualified_close_count'] == 0, 'complete known simulation path')
    count, rolling, prior_stamp, backwards = 0, '0'*64, None, 0
    independent = {
        key: {'peak_cny': D(row['initial_cny']), 'peak_at_ms': None, 'mdd': D(0), 'mdd_point': None}
        for key in ('envelope', 'close')
    }
    traces = []
    for segment in segments:
        trace = segment['path_trace']; path = Path(trace['path'])
        require(trace['verified'] is True and trace['segment_failed'] is False
                and trace['sequence_before'] == count, 'valid path trace segment prefix')
        require(path.stat().st_size == trace['bytes'] and sha(path) == trace['sha256'], 'raw path trace bytes')
        require(trace['rolling_before'] == rolling, 'path trace rolling prefix')
        first = count + 1
        with gzip.open(path, 'rt') as stream:
            for line in stream:
                event = json.loads(line)
                require(len(event) == 10, 'raw path trace schema')
                seq, stamp, kind, cny_text, known, quantity, entry, wallet, margin, fx = event
                require(seq == count + 1 and type(stamp) is int and start <= stamp <= f['now_ms'], 'raw path sequence/clock')
                require(kind in ('favorable', 'envelope', 'close') and type(known) is bool, 'raw path event shape')
                values = [D(v) for v in (cny_text, quantity, entry, wallet, margin, fx)]
                require(all(v.is_finite() for v in values) and values[-1] > 0, 'finite raw path amounts')
                cny, q, entry_value, cash, margin_value, fx_value = values
                if not q:
                    near(cny, cash * fx_value * D('.999'), 'flat raw path FX amount')
                if prior_stamp is not None and stamp < prior_stamp:
                    backwards += 1
                prior_stamp = stamp
                rolling = hashlib.sha256(bytes.fromhex(rolling) + json.dumps(
                    [stamp, kind, cny_text, known], separators=(',', ':')).encode()).hexdigest()
                count = seq
                point = dict(stamp_ms=stamp, equity_cny=cny_text, kind=kind, known_path=known)
                for key, meter in independent.items():
                    if key == 'close' and kind != 'close':
                        continue
                    if cny > meter['peak_cny']:
                        meter['peak_cny'], meter['peak_at_ms'] = cny, stamp
                    if kind == 'favorable' or (key == 'close' and not known):
                        continue
                    dd = D(1) - cny / meter['peak_cny']
                    if dd > meter['mdd']:
                        meter['mdd'] = dd
                        meter['mdd_point'] = dict(point, peak_cny=str(meter['peak_cny']), peak_at_ms=meter['peak_at_ms'])
        points = count - first + 1
        require(trace['points'] == points and trace['sequence_after'] == count
                and trace['rolling_after'] == rolling, 'raw path segment boundaries')
        require((trace['first_sequence'], trace['last_sequence']) == ((first, count) if points else (None, None)),
                'raw path sequence range, including an empty safe segment')
        traces.append(dict(path=str(path), bytes=trace['bytes'], sha256=trace['sha256'], points=trace['points']))
    require(count == a['count'] and rolling == a['rolling_sha256'], 'regenerated complete path digest')
    for key, meter in independent.items():
        require(meter['peak_cny'] == D(a[key]['peak_cny']) and meter['mdd'] == D(a[key]['mdd'])
                and meter['mdd_point'] == a[key]['mdd_point'], 'raw trace independent ' + key + ' MDD')
    return {'passed': True, 'points': a['count'], 'rolling_sha256': a['rolling_sha256'], 'mdd_proxy': f['mdd'],
            'mdd_close_proxy': f['mdd_close'], 'hindsight_bounded': f['hindsight_bounded'], 'bounded_minutes': len(f['bounded_minutes']),
            'rolling_digest_recomputed': True, 'raw_trace_files': traces, 'backward_timestamp_transitions_in_original_event_order': backwards,
            'limitation': 'All original observation points retained and independently recomputed in original event order. OHLC extrema ordering, print/mark proxies and hindsight bounds remain the historical simulation method; no actual native risk acceptance.'}


def receipt_audit(path, arm, spec, spec_path, public, full):
    row = read(path)
    require(row['complete'] and row['failure'] is None and row['no_live_account'] and row['native_verified'] is False, 'completed offline receipt')
    count = 795 if full else 6
    require(row['session_count'] == count and bool(row['original_window_complete']) == full, 'actual window coverage')
    reports_path = Path(row['reports']['path'])
    require(sha(reports_path) == row['reports']['sha256'], 'actual report journal identity')
    reports = [json.loads(line) for line in reports_path.read_text().splitlines()]
    require(len(reports) == count and [r['start_ms'] for r in reports] == row['inputs']['starts_ms'], 'real session chronology')
    require(all(r['cleanup'] == 'verified' and r['pending_intents'] == 0 and r['execution_unresolved'] is False for r in reports), 'all session cleanup')
    held_endpoints = 0
    for report in reports:
        actual = report.get('actual') or {}
        if D(actual.get('quantity_btc', '0')):
            require(actual.get('native_full_position_protected') and actual.get('stop_before_liquidation'), 'protected held session endpoint')
            held_endpoints += 1
    proof_path = reports_path.parent / 'production-calls.jsonl'
    calls = [json.loads(line) for line in proof_path.read_text().splitlines()]
    require([c['start_ms'] for c in calls] == row['inputs']['starts_ms'], 'production call proof chronology')
    for p in calls:
        require(p['calls'].get('coinquant/session.py:run') == 1 and p['calls'].get('coinquant/session.py:cycle', 0) > 0 and p['calls'].get('coinquant/binance.py:_request', 0) > 0 and p['calls'].get('coinquant/state.py:_account_lock_path', 0) > 0, 'actual production request/state paths')
    if full:
        require(row['at_ms'] == row['financial']['now_ms'] == spec['terminal_ms'], 'actual full endpoint')
    identity = source_and_inputs(row, arm, spec, spec_path, full)
    money = financial(row, spec, public)
    raw_lines = reports_path.read_bytes().splitlines(keepends=True)
    chain, current, current_path, seen = [], row, path.resolve(), set()
    while True:
        require(current_path not in seen and len(chain) < spec['max_segments'], 'acyclic bounded receipt chain')
        seen.add(current_path); chain.append((current_path, current))
        previous = current.get('previous_receipt')
        if previous is None:
            break
        current_path = Path(previous['path']).resolve()
        require(sha(current_path) == previous['sha256'], 'previous receipt bytes')
        current = read(current_path)
    prior_cursor = 0
    checkpoint_path_points = []
    for index, (segment_path, segment) in enumerate(reversed(chain), 1):
        cursor = segment['session_count']
        require(segment['source'] == row['source'] and segment['binding'] == row['binding'] and segment['inputs'] == row['inputs'], 'segment source/input registration')
        require(segment['segment'] == index and segment['newly_run_session_count'] == cursor - prior_cursor and segment['failure'] is None, 'segment chronology')
        require(segment['state_directory'] == row['state_directory'] and segment['reports']['path'] == str(reports_path), 'same original account continuation')
        require(hashlib.sha256(b''.join(raw_lines[:cursor])).hexdigest() == segment['reports']['sha256'], 'committed report prefix')
        if index < len(chain):
            require(segment['can_resume'] and segment['current_sqlite_matches_last_checkpoint'], 'actual safe boundary continuation')
            cp = segment['last_checkpoint']; require(sha(cp['path']) == cp['sha256'], 'saved checkpoint bytes')
            env = read(cp['path']); saved = env['body']
            require(digest(saved) == env['sha256'] == cp['envelope_sha256'], 'saved checkpoint identity')
            require(saved['binding'] == row['binding'] and saved['reports'] == segment['reports'] and saved['cursor'] == cursor, 'checkpoint original cursor')
            require(digest(saved['venue']['body']) == saved['venue']['sha256'], 'saved venue identity')
            venue = helper.decoded(saved['venue']['body'])['venue']
            audit = venue['_path_audit']
            require(D(audit['envelope']['mdd']) == venue['mdd_envelope'] and D(audit['close']['mdd']) == venue['mdd_close'], 'checkpoint path summary')
            require(not checkpoint_path_points or audit['count'] >= checkpoint_path_points[-1]['count'], 'continuing path point count')
            checkpoint_path_points.append({'cursor': cursor, 'count': audit['count'], 'rolling_sha256': audit['rolling_sha256']})
        prior_cursor = cursor
    metrics = path_audit(row, [segment for _, segment in reversed(chain)])
    return row, {'receipt': str(path), 'receipt_sha256': sha(path), 'source_inputs': identity, 'financial': money,
                 'path_audit': metrics, 'sessions': count, 'reports_sha256': sha(reports_path), 'production_calls_sha256': sha(proof_path),
                 'held_protected_session_endpoints': held_endpoints, 'continuation_segments': len(chain), 'checkpoint_path_prefixes': checkpoint_path_points,
                 'production_call_totals': {k: sum(p['calls'].get(k, 0) for p in calls) for k in ('coinquant/session.py:run', 'coinquant/session.py:cycle', 'coinquant/binance.py:_request', 'coinquant/state.py:_account_lock_path')}}


def save(path, value):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
        json.dump(value, stream, separators=(',', ':'), allow_nan=False)
        stream.write('\n')


def first_event(before, after):
    keys = range(max(len(before), len(after))) if isinstance(before, list) else sorted(set(before) | set(after))
    for key in keys:
        left = before[key] if (key < len(before) if isinstance(before, list) else key in before) else None
        right = after[key] if (key < len(after) if isinstance(after, list) else key in after) else None
        if left != right:
            return {'index_or_identity': key, 'main': left, 'candidate': right}
    return None


def economic_input_registration(main_inputs, candidate_inputs):
    before, after = dict(main_inputs), dict(candidate_inputs)
    main_spec_sha = before.pop('specification_sha256')
    candidate_spec_sha = after.pop('specification_sha256')
    require(before == after, 'exact economic inputs after specification identity exclusion')
    return {'allowed_input_difference': 'specification_sha256 only',
            'main_specification_sha256': main_spec_sha, 'candidate_specification_sha256': candidate_spec_sha,
            'normalized_exact_economic_input_sha256': digest(before),
            'actual_registration_differences': differences(main_inputs, candidate_inputs, 'inputs'),
            'original_input_packets_claimed_identical': main_inputs == candidate_inputs}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--main', required=True, type=Path); p.add_argument('--candidate', required=True, type=Path)
    p.add_argument('--spec', required=True, type=Path); p.add_argument('--main-spec', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--summary', required=True, type=Path); p.add_argument('--probe', action='store_true')
    args = p.parse_args(); spec = read(args.spec); main_spec = read(args.main_spec); public = PublicInputs(spec)
    before, audit_main = receipt_audit(args.main, 'previous', main_spec, args.main_spec, public, not args.probe)
    after, audit_candidate = receipt_audit(args.candidate, 'current', spec, args.spec, public, not args.probe)
    registration = economic_input_registration(before['inputs'], after['inputs'])
    require(before['initial_usdt'] == after['initial_usdt'], 'paired initial capital')
    registration['declared_strategy_registration_differences'] = differences(before['strategy'], after['strategy'], 'strategy')
    registration['default_risk_by_arm'] = spec['risk_by_arm']
    registration.update(main_binding=before['binding'], candidate_binding=after['binding'],
        main_spec={'path': str(args.main_spec.resolve()), 'sha256': sha(args.main_spec)},
        candidate_spec={'path': str(args.spec.resolve()), 'sha256': sha(args.spec)})
    delta = differences(before['financial'], after['financial'])
    first = {}
    for name in ('trades', 'sent', 'funding_ledger', 'daily', 'orders', 'algos'):
        first[name] = first_event(before['financial'][name], after['financial'][name])
    detail = {'version': 'independent-financial-audit-v1', 'passed': True, 'full795': not args.probe,
              'helper_sha256': HELPER_SHA, 'auditor_sha256': sha(__file__), 'main': audit_main, 'candidate': audit_candidate,
              'economic_input_registration': registration,
              'official_financial_inputs': public.files, 'arm_differences': delta, 'first_differences': first,
              'arm_difference_tolerance': None, 'ledger_audit_tolerance': str(TOLERANCE),
              'request_time_limitation': 'Original sent records contain method/path/payload only; request event timestamps are absent and are not fabricated.'}
    save(args.out, detail)
    summary = {k: v for k, v in detail.items() if k not in ('official_financial_inputs', 'arm_differences')}
    summary['difference_count'] = len(delta)
    summary['detail'] = {'path': str(args.out.resolve()), 'bytes': args.out.stat().st_size, 'sha256': sha(args.out)}
    save(args.summary, summary)
    print(json.dumps({'passed': True, 'full795': not args.probe, 'sessions_per_arm': audit_main['sessions'],
                      'difference_count': len(delta), 'summary_bytes': args.summary.stat().st_size, 'summary_sha256': sha(args.summary)}))


if __name__ == '__main__':
    main()
