"""Read completed, audited simulation receipts; extract three preselected paths.

No strategy, exchange, database, account client, or replay code is imported.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D, getcontext
import gzip
from hashlib import sha256
import json
from pathlib import Path

getcontext().prec = 50
ROOT = Path('/workspace/scratch/4a60782c7dbc')
CAMPAIGNS = (1612800000000, 1708963200000, 1759104000000)
AUDIT_SHA = 'd551eeb6b0cc22bbdccca0a09d4c6c2dd4bb4e856cf5fc824a5d9a5688ddcaca'
HEADS = {
    'control_2_0_0': '162ee7138952925ffafbc9b68be7c754c0c0a6c3',
    'book_v2_only': '37bfc8a833d1ff3c0992842ce363758a47b1d06f',
}
BOOK_ERROR = 'order book changed before the order was sent'
ACTUAL_FIELDS = (
    'quantity_btc', 'entry', 'wallet_usdt', 'equity_usdt',
    'isolated_wallet_usdt', 'mark_price', 'mark_time', 'observed_at_ms',
    'last_fill_id', 'native_liquidation_price', 'protective_algos',
    'possible_entry_remainders', 'native_full_position_protected',
    'stop_before_liquidation',
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def iso(ms):
    stamp = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=ms)
    return stamp.isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def encoded(value):
    return json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n'


def identity(path, data):
    return {'path': str(path), 'bytes': len(data), 'sha256': sha256(data).hexdigest()}


def read_json(path):
    data = path.read_bytes()
    return json.loads(data), identity(path, data)


def narrow(item, raw_sha=None):
    report = item['report']
    preview, actual = report.get('model_preview'), report.get('actual')
    return {
        'sequence': item['sequence'], 'raw_line_sha256': raw_sha,
        'session_started_at_ms': report['session_started_at_ms'],
        'cycle': report.get('cycles'), 'status': report.get('status'),
        'reason': report.get('reason'), 'actions': report.get('actions', []),
        'errors': report.get('errors', []), 'risk_limits': report.get('risk_limits'),
        'model_preview': {k: preview.get(k) for k in (
            'action', 'opportunity', 'position_campaign', 'consumed_campaign',
            'entry_constraint', 'ownership',
        )} if preview else None,
        'actual': {k: actual.get(k) for k in ACTUAL_FIELDS} if actual else None,
    }


def ordinary_actions(record):
    return [a for a in record['actions']
            if a.get('method') == 'POST' and a.get('path') == '/fapi/v1/order']


def exposure_groups(trades):
    """Observed long-only flat-to-flat segments, retaining original fill order."""
    groups, quantity = [], D(0)
    for fill in trades:
        require(fill['side'] in ('BUY', 'SELL'), 'Unexpected fill side')
        amount = D(fill['qty'])
        require(amount > 0, 'Non-positive fill quantity')
        if quantity == 0:
            require(fill['side'] == 'BUY', 'This extract supports observed long-only paths')
            groups.append([])
        groups[-1].append(fill)
        quantity += amount if fill['side'] == 'BUY' else -amount
        require(quantity >= 0, 'Unexpected short or reversal in selected receipt')
    require(quantity == 0, 'Full receipt does not finish flat')
    return groups


def load_arm(arm, audit_arm, archive_path, selected_sessions, archive_expected_sha=None):
    receipt_path = Path(audit_arm['receipt'])
    data = receipt_path.read_bytes()
    provenance = {'receipt': identity(receipt_path, data)}
    require(provenance['receipt']['sha256'] == audit_arm['receipt_sha256'], 'Receipt SHA mismatch')
    receipt = json.loads(gzip.decompress(data))
    require(receipt['complete'] is True and receipt['failure'] is None
            and receipt['original_window_complete'] is True
            and receipt['session_count'] == 795, 'Receipt is not a successful full 795-session run')
    require(receipt['source']['git_head'] == HEADS[arm], 'Unexpected runtime source')
    require(receipt['no_live_account'] is True, 'Expected simulated-account evidence')
    require(audit_arm['financial']['passed'] is True and audit_arm['path_audit']['passed'] is True,
            'Independent financial/path audit did not pass')
    provenance.update(source=receipt['source'], binding=receipt['binding'],
                      qualification=receipt['qualification'], native_verified=receipt['native_verified'])

    reports_path = Path(receipt['reports']['path'])
    reports_data = reports_path.read_bytes()
    provenance['reports'] = identity(reports_path, reports_data)
    require(provenance['reports']['sha256'] == receipt['reports']['sha256']
            == audit_arm['reports_sha256'], 'Reports SHA mismatch')
    reports = [json.loads(line) for line in reports_data.splitlines()]
    require(len(reports) == receipt['reports']['count'] == 795, 'Reports count mismatch')
    terminals = {r['start_ms']: r for r in reports if r['start_ms'] in selected_sessions}

    sessions, entries = defaultdict(list), defaultdict(list)
    archive_hash, archive_bytes, archive_lines = sha256(), 0, 0
    prior_sequence = None
    with archive_path.open('rb') as stream:
        for line in stream:
            archive_hash.update(line)
            archive_bytes += len(line)
            archive_lines += 1
            item = json.loads(line)
            require(prior_sequence is None or item['sequence'] > prior_sequence,
                    'Observation archive sequence is not strictly increasing')
            prior_sequence = item['sequence']
            report = item['report']
            preview = report.get('model_preview') or {}
            campaign = (preview.get('opportunity') or {}).get('identity')
            selected_entry = campaign in CAMPAIGNS and preview.get('action') == 'enter'
            selected_session = report.get('session_started_at_ms') in selected_sessions
            if selected_entry or selected_session:
                record = narrow(item, sha256(line).hexdigest())
                if selected_entry:
                    entries[campaign].append(record)
                if selected_session:
                    sessions[report['session_started_at_ms']].append(record)
    provenance['observations_archive'] = {
        'path': str(archive_path), 'bytes': archive_bytes, 'sha256': archive_hash.hexdigest(),
        'lines': archive_lines,
        'binding_note': 'Archive bytes hashed here; selected terminal actual snapshots match the receipt-bound reports.',
    }
    if archive_expected_sha:
        require(archive_hash.hexdigest() == archive_expected_sha, 'Original archive SHA mismatch')
    for start, records in sessions.items():
        last = records[-1]
        terminal = terminals[start]
        require(last['actual'] == {k: terminal['actual'].get(k) for k in ACTUAL_FIELDS},
                f'Archive terminal actual mismatch at {start}')
        require(last['cycle'] == terminal['cycles'] and last['reason'] == terminal.get('reason'),
                f'Archive terminal cycle/reason mismatch at {start}')

    orders = receipt['financial']['orders']
    groups = exposure_groups(receipt['financial']['trades'])
    group_by_first_order = {group[0]['orderId']: group for group in groups}
    selected = {}
    for campaign in CAMPAIGNS:
        candidates = []
        for record in entries[campaign]:
            for action in ordinary_actions(record):
                order = orders.get(action['id'])
                if order and order['orderId'] in group_by_first_order:
                    candidates.append((record, action, order, group_by_first_order[order['orderId']]))
        unique_entries = {}
        for candidate in candidates:
            record, action, order, group = candidate
            key = (order['orderId'], action['id'], action['at_ms'])
            unique_entries.setdefault(key, candidate)
        require(len(unique_entries) == 1, f'Campaign {campaign} has ambiguous or absent filled entry identity')
        record, action, first_order, group = next(iter(unique_entries.values()))
        buys = [t for t in group if t['side'] == 'BUY']
        buy_ids = list(dict.fromkeys(t['orderId'] for t in buys))
        first_fills = [t for t in buys if t['orderId'] == first_order['orderId']]
        bought = sum((D(t['qty']) for t in buys), D(0))
        require(bought == sum((D(t['qty']) for t in group if t['side'] == 'SELL'), D(0)),
                'Selected segment does not reconcile to flat')
        order_evidence = []
        for order_id in buy_ids:
            native = next(o for o in orders.values() if o['orderId'] == order_id)
            fills = [t for t in buys if t['orderId'] == order_id]
            require(sum((D(t['qty']) for t in fills), D(0)) == D(native['executedQty']),
                    'Order executed quantity differs from its fills')
            sent = [s for s in receipt['financial']['sent'] if s[0] == 'POST'
                    and s[1] == '/fapi/v1/order'
                    and s[2].get('newClientOrderId') == native['clientOrderId']]
            require(len(sent) == 1, 'Missing or duplicate ordinary POST payload')
            require(sent[0][2]['side'] == 'BUY' and not native['reduceOnly'], 'Unexpected entry order')
            require(D(sent[0][2]['quantity']) == D(native['origQty']), 'POST/order quantity mismatch')
            require(D(sent[0][2]['price']) == D(native['price']), 'POST/order limit mismatch')
            require(all(D(t['price']) <= D(native['price']) for t in fills), 'Buy fill exceeds IOC limit')
            order_evidence.append({'order': native, 'sent_payload': sent[0], 'fills': fills})
        require(action['at_ms'] < buys[0]['time'], 'POST action does not precede first fill')
        selected[campaign] = {
            'opportunity': record['model_preview']['opportunity'],
            'entry_observation': record, 'entry_cycle': record['cycle'],
            'entry_action_observation_sequences': [r['sequence'] for r, _, _, _ in candidates],
            'entry_session_start_ms': record['session_started_at_ms'],
            'entry_session_start_utc': iso(record['session_started_at_ms']),
            'first_post_action': action, 'first_fill': buys[0],
            'first_fill_at_utc': iso(buys[0]['time']),
            'first_fill_quantity_btc': buys[0]['qty'],
            'first_order_executed_quantity_btc': sum((D(t['qty']) for t in first_fills), D(0)),
            'total_entry_quantity_btc': bought,
            'entry_vwap_usdt': sum((D(t['qty']) * D(t['price']) for t in buys), D(0)) / bought,
            'entry_fill_count': len(buys), 'filled_entry_order_count': len(buy_ids),
            'entry_orders': order_evidence,
            'last_exit_fill': group[-1], 'last_exit_at_utc': iso(group[-1]['time']),
            'exposure_segment_fill_ids': [t['id'] for t in group],
        }
    return provenance, receipt, sessions, terminals, selected


def session_evidence(records, terminal):
    require(bool(records), 'Selected session missing from archived observations')
    post_observations = [dict(sequence=r['sequence'], cycle=r['cycle'], **a)
                         for r in records for a in ordinary_actions(r)]
    unique_post = {}
    for action in post_observations:
        key = (action['method'], action['path'], action['id'], action['at_ms'])
        unique_post.setdefault(key, action)
    post = list(unique_post.values())
    reason_counts = Counter(r['reason'] for r in records if r['reason'])
    no_post = Counter(
        r['reason'] or f"model_preview.action={(r.get('model_preview') or {}).get('action')}"
        for r in records if not ordinary_actions(r)
    )
    return {
        'session_start_ms': records[0]['session_started_at_ms'],
        'session_start_utc': iso(records[0]['session_started_at_ms']),
        'archived_observation_records': len(records), 'reported_cycles': terminal['cycles'],
        'current_reason_record_counts': dict(reason_counts),
        'book_rejection_observation_count': reason_counts[BOOK_ERROR],
        'no_ordinary_post_record_class_counts': dict(no_post),
        'ordinary_post_actions': post, 'ordinary_post_count': len(post),
        'ordinary_post_action_observations': post_observations,
        'terminal_status': terminal['status'], 'terminal_reason': terminal.get('reason'),
        'terminal_quantity_btc': terminal['actual']['quantity_btc'],
        'terminal_native_full_position_protected': terminal['actual'].get('native_full_position_protected'),
        'terminal_execution_unresolved': terminal['execution_unresolved'],
        'terminal_possible_entry_remainders': terminal['possible_entry_remainders'],
        'observations': records,
    }


def single_factor_binding(out, audit, arms):
    """Read registered source bytes and inputs; never execute production code."""
    control, book = arms['control_2_0_0'][1], arms['book_v2_only'][1]
    registration_path = out / 'replays/book-v2-only/REGISTRATION.json'
    registration, registration_identity = read_json(registration_path)
    spec_path = registration_path.with_name('spec.json')
    spec, spec_identity = read_json(spec_path)
    amendment_path = out / 'BOOK_GUARD_AMENDMENT_V2.md'
    amendment = identity(amendment_path, amendment_path.read_bytes())
    require(registration['case'] == 'book-v2-only'
            and registration['head'] == spec['runtime_heads']['current'] == HEADS['book_v2_only']
            and registration['source_sha256'] == book['source']['source_sha256']
            and registration['runtime'] == spec['runtime_roots']['current'],
            'Book-only registration does not bind the measured runtime')
    require(registration['spec_sha256'] == spec_identity['sha256']
            == book['inputs']['specification_sha256'], 'Book-only registered specification differs')
    require(registration['book_guard_amendment_sha256'] == spec['book_guard_amendment_sha256']
            == amendment['sha256'], 'Book-only amendment identity differs')
    require(Path(registration['control_receipt']).resolve()
            == Path(arms['control_2_0_0'][0]['receipt']['path']).resolve(), 'Another control was registered')
    inputs_before = {k:v for k,v in control['inputs'].items() if k != 'specification_sha256'}
    inputs_after = {k:v for k,v in book['inputs'].items() if k != 'specification_sha256'}
    require(inputs_before == inputs_after and control['strategy'] == book['strategy'],
            'Book-only economic inputs or strategy differ from the control')
    economic = audit['economic_input_registration']
    require(economic['allowed_input_difference'] == 'specification_sha256 only'
            and economic['declared_strategy_registration_differences'] == []
            and economic['main_binding'] == control['binding']
            and economic['candidate_binding'] == book['binding'],
            'Independent audit does not bind the same fixed-input pair')
    require(registration['fixed_risk'] == spec['risk_by_arm']['current']
            == {k:control['strategy'][k] for k in registration['fixed_risk']},
            'Registered risk settings differ')
    require(control['source']['tooling_files'] == book['source']['tooling_files']
            and control['source']['producer_sha256'] == book['source']['producer_sha256']
            == registration['producer_sha256'], 'Producer or research module bytes differ')
    old_files, new_files = control['source']['files'], book['source']['files']
    require(set(old_files) == set(new_files) and len(old_files) == 19,
            'Production source inventory differs')
    changed = {name:{'control_sha256':old_files[name], 'book_only_sha256':new_files[name]}
               for name in old_files if old_files[name] != new_files[name]}
    require(set(changed) == {'coinquant/native_preview.py', 'coinquant/lifecycle.py'},
            'Unexpected production modules changed in the registered book-only arm')
    shapes, sources = [], []
    for receipt in (control, book):
        path = Path(receipt['source']['runtime_module']).with_name('native_preview.py')
        raw = path.read_bytes()
        source_identity = identity(path, raw)
        require(source_identity['sha256'] == receipt['source']['files']['coinquant/native_preview.py'],
                'Frozen native_preview source bytes differ from the receipt')
        node = next(node for node in ast.parse(raw).body
                    if isinstance(node, ast.FunctionDef) and node.name == '_funded_quantity')
        shapes.append(ast.dump(node))
        sources.append(source_identity)
    require(shapes[0] == shapes[1], 'Book-only arm changed collateral sizing arithmetic')
    return {
        'registration':registration_identity, 'specification':spec_identity, 'amendment':amendment,
        'economic_inputs_equal_except_specification_identity':True, 'strategy_exactly_equal':True,
        'normalized_economic_input_sha256':economic['normalized_exact_economic_input_sha256'],
        'fixed_risk':registration['fixed_risk'], 'producer_and_research_bytes_equal':True,
        'changed_production_modules':changed,
        'funded_quantity_function_ast_unchanged':True, 'funded_quantity_source_files':sources,
        'scope':'Registered book-guard v2 source only; stop-scenario collateral-sizing and frozen-buffer fixes are absent.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    out = args.root / 'diagnosis'
    json_path, md_path = (out / name for name in ('book-execution-attribution.json', 'book-execution-attribution.md'))
    require(not json_path.exists() and not md_path.exists(), 'Existing book-only evidence must be preserved')
    audit_path = out / 'replays/book-v2-only/full-audit-summary.json'
    audit, audit_identity = read_json(audit_path)
    require(audit_identity['sha256'] == AUDIT_SHA, 'Audit summary differs from the reviewed complete result')
    require(audit['passed'] is True and audit['full795'] is True, 'Full independent audit has not passed')
    preselection_path = out / 'trade-path-details.json'
    preselection, preselection_identity = read_json(preselection_path)
    original = {r['campaign']: r for r in preselection['delayed_same_campaign_entries']}
    require(set(original) == set(CAMPAIGNS), 'Preselected campaigns changed')
    starts = {c: original[c]['previous_entry_observation']['session_started_at_ms'] for c in CAMPAIGNS}
    selected_sessions = set(starts.values()) | {
        original[c]['current_entry_observation']['session_started_at_ms'] for c in CAMPAIGNS
    }
    previous_archive = preselection['source_provenance']['current']
    arms = {
        'control_2_0_0': load_arm('control_2_0_0', audit['main'], Path(previous_archive['path']),
            selected_sessions, previous_archive['sha256']),
        'book_v2_only': load_arm('book_v2_only', audit['candidate'],
            out / 'replays/book-v2-only/full-current/state/observations-archive.jsonl', selected_sessions),
    }
    require(arms['control_2_0_0'][1]['binding']['strategy_sha256']
            == arms['book_v2_only'][1]['binding']['strategy_sha256'], 'Strategy registration changed')
    binding = single_factor_binding(out, audit, arms)
    rows = []
    for campaign in CAMPAIGNS:
        row = {'campaign': campaign, 'preselected_original_session_start_utc': iso(starts[campaign])}
        for name, (_, _, sessions, terminals, entries) in arms.items():
            entry = entries[campaign]
            if name == 'control_2_0_0':
                require(entry['first_fill']['time'] == original[campaign]['current']['start_ms'],
                        'Control entry differs from preselected original evidence')
                require(entry['total_entry_quantity_btc'] == D(original[campaign]['current']['buy_quantity_btc']),
                        'Control quantity differs from preselected original evidence')
                require(entry['entry_vwap_usdt'] == D(original[campaign]['current']['buy_vwap_usdt']),
                        'Control VWAP differs from preselected original evidence')
            entry['original_session'] = session_evidence(sessions[starts[campaign]], terminals[starts[campaign]])
            entry_start = entry['entry_session_start_ms']
            if entry_start != starts[campaign]:
                entry['actual_entry_session'] = session_evidence(sessions[entry_start], terminals[entry_start])
            row[name] = entry
        control, book = row['control_2_0_0'], row['book_v2_only']
        geometry = ('identity', 'direction', 'anchor', 'risk', 'stop')
        require(all(control['opportunity'][k] == book['opportunity'][k] for k in geometry),
                'Campaign identity/fixed signal geometry differs')
        row['same_opportunity_geometry'] = {k: control['opportunity'][k] for k in geometry}
        row['entry_earlier_seconds'] = D(control['first_fill']['time'] - book['first_fill']['time']) / 1000
        row['entry_earlier_hours'] = row['entry_earlier_seconds'] / 3600
        row['entry_vwap_reduction_pct'] = (1 - book['entry_vwap_usdt'] / control['entry_vwap_usdt']) * 100
        row['book_entered_original_session'] = book['entry_session_start_ms'] == starts[campaign]
        require(control['original_session']['ordinary_post_count'] == 0
                and D(control['original_session']['terminal_quantity_btc']) == 0,
                'Original no-POST/flat evidence changed')
        require(row['book_entered_original_session']
                and D(book['original_session']['terminal_quantity_btc']) > 0,
                'Book-only result did not enter and hold the original session')
        require(book['original_session']['terminal_native_full_position_protected'] is True
                and book['original_session']['terminal_execution_unresolved'] is False
                and book['original_session']['terminal_possible_entry_remainders'] == 0,
                'Book-only selected session does not finish protected and resolved')
        rows.append(row)
    result = {
        'version': 'book-execution-attribution-v1',
        'scope': 'Three preselected actual paths from the registered book-only full replay; read-only archived extraction, no additional replay.',
        'independent_full_audit': audit_identity, 'preselection': preselection_identity,
        'single_factor_binding':binding,
        'extractor': identity(Path(__file__).resolve(), Path(__file__).read_bytes()),
        'source_provenance': {name: arm[0] for name, arm in arms.items()},
        'campaigns': rows,
        'interpretation_limits': [
            'These are actual fills in a completed historical simulation, not native venue execution or live-account verification.',
            'Opportunity identity and fixed geometry connect entry observations to ordinary POST client IDs, native order IDs and fill IDs; dates alone are not the identity match.',
            'The registered book-only arm and 2.0.0 control use identical economic inputs and strategy, with the registered book guard as the sole source treatment. These paths establish restored execution for the three preselected opportunities; they do not allocate the full-period financial difference among individual campaigns.',
            'Quantities also reflect earlier compounded equity and different entry timing. Their increase is not a direct increase in the configured risk limit.',
            'A book-changed reason can represent limit/band, depth, capacity, freshness or bar-boundary rejection. The failed quote snapshots are absent, so the exact failed subcondition is not invented.',
            'Reason counts count current report.reason records, never repeated historical errors array members. Normal hold/no-POST and end-of-session deadline records are not missed opportunities.',
            'Terminal observations may repeat the preceding action: identical method/path/client ID/action time is one POST, with every observation sequence retained. This carries forward the previously verified duplicate-observation handling from the unchanged combined extractor.',
            'POST action at_ms is a recorded simulated action timestamp. Fill time is the receipt trade timestamp. financial.sent has no independent request timestamp; no missing request arrival time is reconstructed.',
            'Total entry quantity and VWAP include every BUY fill in the matched flat-to-flat exposure segment, including adds; the first print and first order quantities are retained separately.',
            'Archived terminal actual snapshots were checked against SHA-bound complete reports; this does not reconstruct absent intra-cycle book snapshots.',
        ],
    }
    lines = [
        '# 盘口单因素修复：三个预选机会的实际执行路径', '',
        '盘口单因素修复在这三个预选机会的原定会话均已实际成交；2.0.0 在对应原会话没有普通订单 POST，最后仍空仓。这里的“实际”指完成回放中的成交账本，不代表真实交易所或账户验证。', '',
        '输入为独立审计通过的完整 795 会话回执。通过 `model_preview.opportunity.identity` 及相同 direction、anchor、risk、stop 验证机会身份，再连接普通订单 POST 的 client ID、orderId 和成交 ID。', '',
        '单因素登记另经核对：两组经济输入除 spec 身份外完全相同，策略、风险配置、生产器和研究模块一致；实际差异只在已登记的盘口 guard 及其调用位置。已按回执 SHA 核对冻结源码，`_funded_quantity` 函数 AST 与 2.0.0 完全一致，未混入保证金定仓或 v3 冻结缓冲修复。', '',
        '## 入场时间与价格', '',
        '| Campaign | 2.0.0 首次成交（UTC） | 盘口单因素首次成交（UTC） | 提前小时 | 2.0.0 买入 VWAP（USDT） | 盘口单因素买入 VWAP（USDT） | VWAP 降低 |',
        '|---:|---|---|---:|---:|---:|---:|',
    ]
    for row in rows:
        control, book = row['control_2_0_0'], row['book_v2_only']
        lines.append(f"| {row['campaign']} | {control['first_fill_at_utc']} | {book['first_fill_at_utc']} | {row['entry_earlier_hours']:.6f} | {control['entry_vwap_usdt']:,.4f} | {book['entry_vwap_usdt']:,.4f} | {row['entry_vwap_reduction_pct']:.4f}% |")
    lines += ['', '## 数量口径', '',
        '首笔是第一个分笔成交；首单是第一张普通订单的累计成交；总买入量与 VWAP 包含该空仓至空仓持仓段内的全部买入成交及补单。数量受此前复利权益、入场价格和风险约束共同影响。', '',
        '| Campaign | 2.0.0 首笔 / 首单 / 总买入（BTC） | 盘口单因素首笔 / 首单 / 总买入（BTC） | 2.0.0 / 盘口单因素有成交买单数 |',
        '|---:|---|---|---:|']
    for row in rows:
        control, book = row['control_2_0_0'], row['book_v2_only']
        keys = ('first_fill_quantity_btc', 'first_order_executed_quantity_btc', 'total_entry_quantity_btc')
        lines.append(f"| {row['campaign']} | {' / '.join(str(control[k]) for k in keys)} | {' / '.join(str(book[k]) for k in keys)} | {control['filled_entry_order_count']} / {book['filled_entry_order_count']} |")
    lines += ['', '## 原定会话的未发单与恢复路径', '',
        '| Campaign | 2.0.0 / 盘口单因素当前盘口失败观察数 | 2.0.0 / 盘口单因素普通 POST 数 | 盘口单因素入场 cycle / sequence | 盘口单因素 orderId | 2.0.0 / 盘口单因素会话末仓位（BTC） |',
        '|---:|---:|---:|---|---:|---:|']
    for row in rows:
        control, book = row['control_2_0_0'], row['book_v2_only']
        old, new = control['original_session'], book['original_session']
        lines.append(f"| {row['campaign']} | {old['book_rejection_observation_count']} / {new['book_rejection_observation_count']} | {old['ordinary_post_count']} / {new['ordinary_post_count']} | {book['entry_cycle']} / {book['entry_observation']['sequence']} | {book['first_fill']['orderId']} | {old['terminal_quantity_btc']} / {new['terminal_quantity_btc']} |")
    lines += ['',
        '前两例仍在第 1 个 cycle 拒绝一次盘口检查，第 2 个 cycle 成交；第三例第 1 个 cycle 即成交。盘口单因素臂三个会话末均持仓且有完整原生保护的模拟观察，执行未决和潜在入场余单均为零。最终 observation deadline 是会话收尾记录，不能据此写成未成交；持仓中的 hold/no-POST 也不是漏单。', '',
        '逐观察当前原因计数不重复累计 `errors` 数组；收尾报告重复保留同一 client ID、动作时间的 POST 也只计一单，两个原始 sequence 都保留。本次沿用此前组合证据中已核实的重复观察处理方式。JSON 保留原始行 SHA、sequence、完整动作、当期 reason、历史 errors 和缩减的实际观察字段。原始盘口失败字符串涵盖数个检查条件，缺少当期前后完整报价，不能仅靠字符串断言每次是哪一个条件拒绝。', '',
        '## 归因边界', '',
        '这份完整单因素对照证明：在同一输入、策略和风险配置下，仅应用登记的盘口 v2 修复，就恢复了三个已预选机会在原会话的实际入场，并改善了这些案例的入场价格。数量还会受此前路径的复利权益影响；这不是放宽风险参数的证据。不能将三个案例的价格、数量或收益变化直接相加，作为全期收益变化的分解。', '',
        '入场 VWAP 不含手续费；回执完整财务审计另外计算手续费、资金费和汇率成本。这份文件不重算年化或回撤。', '',
        '## 输入身份与复现', '',
        f"- 独立审计 summary SHA-256：`{audit_identity['sha256']}`。",
        f"- 2.0.0 完整回执 SHA-256：`{arms['control_2_0_0'][0]['receipt']['sha256']}`。",
        f"- 盘口单因素完整回执 SHA-256：`{arms['book_v2_only'][0]['receipt']['sha256']}`。",
        '- JSON 另含单因素登记、盘口 amendment、源码、生产器、输入、会话排程、逐会话 reports、逐观察归档和提取脚本身份。', '',
        '复现：`python diagnosis/book_execution_attribution.py`。须具有审计 summary 指向的两份完整回执、对应只读归档和冻结源码；任何完整性或身份检查不符即失败。输出已存在时拒绝覆盖。脚本只使用 Python 标准库，源码仅作 AST 读取，不导入账户、策略或回放模块。',
    ]
    for path, content in ((json_path, encoded(result)), (md_path, '\n'.join(lines) + '\n')):
        with path.open('x') as stream:
            stream.write(content)
    print(encoded({'outputs': [identity(p, p.read_bytes()) for p in (json_path, md_path)],
                   'campaigns': [{k: row[k] for k in (
                       'campaign', 'entry_earlier_hours', 'entry_vwap_reduction_pct',
                       'book_entered_original_session')} for row in rows]}), end='')


if __name__ == '__main__':
    main()
