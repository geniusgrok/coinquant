r"""Summarize the preserved 2x2 experiment plus the registered combined-v3 fix.

No replay, source mutation, account access or online verification. A --case is
five arguments: NAME REGISTRATION RECEIPT AUDIT_SUMMARY PUBLIC_COMMIT_URL.
The URL must name the exact registered commit; its online availability and
commit/tree readback belong to the separately retained publication evidence.

Examples (all paths may be absolute):
  python repair_results_v2.py --check-baselines
  python repair_results_v2.py \
    --case margin-only replays/margin-only/REGISTRATION.json \
      replays/margin-only/full-current-segment-002.json.gz \
      replays/margin-only/full-audit-summary.json \
      https://github.com/geniusgrok/coinquant/commit/FULL_REGISTERED_HEAD \
    --out FINAL_RESULTS.json --markdown FINAL_RESULTS.md

Repeat --case for book-v2-only, combined-v2 and combined-v3. Final output requires
all four registered repairs. Each full audit still compares with 2.0.0; the
v3-minus-v2 increment uses their exact common-control input binding, not another
replay. The invalid v3 head placeholder must be replaced after public freezing.
Partial, failed and smoke receipts are rejected. Existing v1 evidence is kept.
"""
import argparse
from collections import Counter
from decimal import Decimal as D, localcontext
import importlib.util
import json
from pathlib import Path
from statistics import median
import sys

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
ORIGINAL = BASE / 'remeasure-evidence/evidence/2.0.0-remeasure-20261009'
FROZEN = BASE / 'coinquant-remeasure-2.0.0-v2'
CONTROL = '162ee7138952925ffafbc9b68be7c754c0c0a6c3'
HISTORICAL = '79a334b2d776be2dbe8756f3a616697f9403982e'
ORIGINAL_SUMMARY_SHA = 'b607c483b0c70682e3889e43b14aa9e4fd1f72db7a186ad649218b71b477bed3'
ORIGINAL_METRICS_SHA = '240a0c2682f52269a9dfe064082cd2d9c648258309f145bceaa3dce33caedb5e'
HELPER_SHA = 'b8d097a60f390da0cc95f5424ff2f8649c7250045fa82ba5e3c7f7acffd3145e'
PRODUCER_SHA = '9b5ee3aea3a4f977b0b20c7b25e4a81ecdc5b7b188d9f26a3e119e03101f5413'
COMMIT_PREFIX = 'https://github.com/geniusgrok/coinquant/commit/'
REPAIR_HEADS = {
    'margin-only': '06206ac0c5383fb009df8bac20601cd9e2d9b004',
    'book-v2-only': '37bfc8a833d1ff3c0992842ce363758a47b1d06f',
    'combined-v2': '3561728dab351d269b19b107fb4fbabb2ac1f674',
    'combined-v3': '230a61daade55d7d80de56f61aae24e660fb3a40',
}
FACTORIAL_CASES = ('margin-only', 'book-v2-only', 'combined-v2')
BOOK_GUARD_CASES = ('book-v2-only', 'combined-v2', 'combined-v3')
INCREMENTAL_BASE = {
    'case': 'combined-v2',
    'head': '3561728dab351d269b19b107fb4fbabb2ac1f674',
    'spec_sha256': 'd0937a2415e464cdeae3ec0749affc11f2345269edff5e355c6edae8eef9060b',
    'receipt_sha256': '6b1fe9dd901e933928e4148df614ff67ad94a3910fa502dfe41a17047846fc0b',
}
FROZEN_BUFFER_AMENDMENT_SHA = '040729b29351abcf2a87244ba66f385eefbb2db33c5601cd80a31198d0bba9f4'
REPAIR_LABELS = {'margin-only': '仅修定仓余量', 'book-v2-only': '仅修盘口匹配（v2）',
                 'combined-v2': '合并修复（v2）', 'combined-v3': '合并修复（v3，保留冻结缓冲）'}


def module(path, name, expected_sha):
    import hashlib
    path = Path(path).resolve()
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        raise ValueError('frozen calculation/helper bytes changed: ' + str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


original = module(ROOT / 'original_summarize_results.py', 'fixed_result_math', ORIGINAL_SUMMARY_SHA)
helper = module(ROOT / 'original_compare_arms.py', 'fixed_result_digest', HELPER_SHA)
require, number, read, sha = original.require, original.number, original.read, original.sha
artifact, plain, display = original.artifact, original.plain, original.display


def registered_cases(cases, check_baselines):
    """Reject an unfrozen head before opening candidate evidence."""
    names = [case[0] for case in cases]
    require(len(names) == len(set(names)) and set(names) <= set(REPAIR_HEADS),
            'duplicate or undeclared case name')
    for name in names:
        head = REPAIR_HEADS[name]
        require(len(head) == 40 and all(char in '0123456789abcdef' for char in head),
                'runtime head is not frozen; replace the explicit placeholder for ' + name)
    require(check_baselines or set(names) == set(REPAIR_HEADS),
            'FINAL_RESULTS requires all four registered complete repairs')
    return sorted(cases, key=lambda case: list(REPAIR_HEADS).index(case[0]))


def passed_audit(path, auditor_path):
    """Bind the success summary to its unchanged full audit detail and code."""
    summary = read(path)
    require(summary['version'] == 'independent-financial-audit-v1'
            and summary['passed'] is True and summary['full795'] is True,
            'independent full795 passed audit required; no smoke/partial results')
    require(summary['arm_difference_tolerance'] is None
            and number(summary['ledger_audit_tolerance']) == D('.00000001'),
            'unexpected financial audit tolerance; arm differences must remain exact')
    require(summary['auditor_sha256'] == sha(auditor_path)
            and summary['helper_sha256'] == HELPER_SHA,
            'audit implementation identity differs from the supplied auditor/helper')
    detail_ref = summary.get('detail')
    require(isinstance(detail_ref, dict) and artifact(detail_ref['path']) == detail_ref,
            'audit summary needs its unchanged complete detail artifact')
    detail = read(detail_ref['path'])
    expected = {key: value for key, value in detail.items()
                if key not in ('official_financial_inputs', 'arm_differences')}
    actual = {key: value for key, value in summary.items()
              if key not in ('detail', 'difference_count')}
    require(expected == actual and summary['difference_count'] == len(detail['arm_differences']),
            'audit summary does not exactly describe its full detail')
    require(summary['main']['sessions'] == summary['candidate']['sessions'] == 795,
            'both independently audited arms must cover all 795 sessions')
    require(all(summary[arm]['financial']['passed'] is True
                and summary[arm]['path_audit']['passed'] is True
                and summary[arm]['path_audit']['rolling_digest_recomputed'] is True
                for arm in ('main','candidate')), 'both audited financial/path checks must pass')
    return summary


def spec_binding(row, spec_path, arm, expected_head):
    spec = read(spec_path)
    require(spec['version'] == row['version'] == 'coinquant-default-runtime-paired-replay-v2'
            and spec['session_count'] == 795 and spec['initial_cny'] == '10000'
            and spec['terminal_ms'] == original.END,
            'registered original-window specification required')
    require(sha(spec_path) == row['inputs']['specification_sha256'], 'receipt/spec bytes differ')
    source, binding = row['source'], row['binding']
    require(source['git_head'] == spec['runtime_heads'][arm] == expected_head,
            'receipt head does not match the registered exact runtime head')
    runtime = Path(spec['runtime_roots'][arm]).resolve()
    require(source['runtime_module'] == str(runtime / 'coinquant/session.py'), 'runtime path changed')
    files = {str(p.relative_to(runtime)): sha(p) for p in sorted((runtime/'coinquant').glob('*.py'))}
    require(len(files) == 19 and files == source['files'] == read(spec['source_files_by_arm'][arm]),
            'registered production module bytes changed')
    tooling = Path(spec['tooling_root']).resolve()
    tools = {str(p.relative_to(tooling)): sha(p) for p in sorted((tooling/'research').glob('*.py'))}
    require(tools == source['tooling_files'], 'registered research modules changed')
    require(sha(tooling/'driver.py') == source['producer_sha256']
            == binding['producer_sha256'] == spec['producer_sha256'] == PRODUCER_SHA,
            'frozen v2 producer changed')
    packet = dict(files)
    packet.update({'tooling/' + key: value for key, value in tools.items()})
    packet['tooling/driver.py'] = PRODUCER_SHA
    require(helper.digest(packet) == source['source_sha256'] == binding['source_sha256']
            == spec['source_sha256_by_arm'][arm], 'source packet binding changed')
    require(helper.digest(row['inputs']) == binding['input_sha256']
            and helper.digest(row['strategy']) == binding['strategy_sha256'],
            'input/strategy packet binding changed')
    require(all(row['strategy'][key] == value for key, value in spec['risk_by_arm'][arm].items()),
            'measured risk configuration differs from the registration')
    require(sha(spec['schedule']) == row['inputs']['schedule_sha256']
            == binding['schedule_sha256'] == 'c21b4fcfe3cb12fb062bb01d3c3591aa0ee8c65db9e9afde3c26b1bcdc2ac28e'
            and read(spec['schedule'])['primary']['starts_ms'] == row['inputs']['starts_ms'],
            'original complete session schedule changed')
    return spec


def holding_statistics(financial):
    """Actual exposure intervals; counts never reinterpret prints as trades."""
    quantity = D(0)
    groups = []
    active = None
    for fill in financial['trades']:
        amount = number(fill['qty']) * (1 if fill['side'] == 'BUY' else -1)
        if quantity == 0:
            active = {'entered_at_ms': fill['time'], 'buy_orders': set(), 'sell_orders': set(),
                      'fills': 0, 'realized_pnl_usdt': D(0), 'commissions_usdt': D(0)}
        require(quantity == 0 or quantity*amount >= 0 or abs(amount) <= abs(quantity),
                'unexpected position reversal inside one fill; exposure statistic needs explicit handling')
        active['buy_orders' if fill['side'] == 'BUY' else 'sell_orders'].add(fill['orderId'])
        active['fills'] += 1
        active['realized_pnl_usdt'] += number(fill['realizedPnl'])
        active['commissions_usdt'] += number(fill['commission'])
        quantity += amount
        if quantity == 0:
            funding = sum((number(item['income']) for item in financial['funding_ledger']
                           if item['incomeType'] == 'FUNDING_FEE'
                           and active['entered_at_ms'] < item['time'] <= fill['time']), D(0))
            groups.append({key: value for key, value in active.items()
                           if key not in ('buy_orders', 'sell_orders')})
            groups[-1].update(exited_at_ms=fill['time'],
                held_seconds=D(fill['time']-active['entered_at_ms'])/1000,
                filled_buy_orders=len(active['buy_orders']), filled_sell_orders=len(active['sell_orders']),
                net_funding_usdt=funding,
                net_realized_after_commission_and_funding_usdt=active['realized_pnl_usdt']-active['commissions_usdt']+funding)
            active = None
    require(quantity == number(financial['quantity_btc']), 'exposure quantity disagrees with the receipt')
    return {'basis': 'Actual signed fills grouped from flat to flat; any still-open group is separate',
            'closed_exposure_groups': len(groups), 'open_exposure_groups': int(active is not None),
            'filled_buy_orders': len({f['orderId'] for f in financial['trades'] if f['side'] == 'BUY'}),
            'filled_sell_orders': len({f['orderId'] for f in financial['trades'] if f['side'] == 'SELL'}),
            'median_closed_holding_days': median(g['held_seconds']/86400 for g in groups) if groups else None,
            'closed_within_300_seconds': sum(g['held_seconds'] <= 300 for g in groups),
            'daily_boundaries_with_exposure': sum(number(day['quantity_btc']) != 0 for day in financial['daily'][1:]),
            'closed_groups': groups}


def audit_receipt_path(checked, audit_path):
    path = Path(checked['receipt'])
    return (path if path.is_absolute() else Path(audit_path).resolve().parent/path).resolve()


def accepted_arm(path, spec_path, spec_arm, expected_head, checked, audit_path):
    path = Path(path).resolve()
    identity = artifact(path)
    require(audit_receipt_path(checked, audit_path) == path and checked['receipt_sha256'] == identity['sha256'],
            'audit names a different receipt')
    row = read(path)
    require(row['complete'] is True and row['original_window_complete'] is True
            and row['failure'] is None and row['session_count'] == checked['sessions'] == 795
            and row['scope'] == {'kind': 'original-full', 'planned_sessions': 795},
            'full successful original 795-session receipt required')
    require(row['no_live_account'] is True and row['native_verified'] is False,
            'expected offline simulation qualification')
    spec = spec_binding(row, spec_path, spec_arm, expected_head)
    require(checked['source_inputs']['head'] == expected_head, 'audit runtime head mismatch')
    for field in ('source_sha256', 'producer_sha256'):
        require(row['source'][field] == checked['source_inputs'][field], 'audited source identity ' + field)
    require(row['binding']['input_sha256'] == checked['source_inputs']['input_sha256'], 'audited input identity')
    f = row['financial']
    require(number(row['initial_cny']) == original.INITIAL and row['inputs']['starts_ms'][0] == original.START
            and row['terminal_ms'] == row['at_ms'] == f['now_ms'] == original.END,
            'fixed 2454-day endpoint and opening capital required')
    require(f['audit']['passed'] is True and checked['financial']['passed'] is True,
            'independent financial audit did not pass')
    audit = checked['path_audit']
    require(audit['passed'] is True and audit['rolling_digest_recomputed'] is True
            and audit['points'] == f['path_audit']['count']
            and audit['rolling_sha256'] == f['path_audit']['rolling_sha256']
            and number(audit['mdd_proxy']) == number(f['mdd'])
            and number(audit['mdd_close_proxy']) == number(f['mdd_close']),
            'independently audited full path identity and metrics required')
    require(bool(audit['raw_trace_files']), 'audited raw path evidence absent')
    for trace in audit['raw_trace_files']:
        require(Path(trace['path']).stat().st_size == trace['bytes'] and sha(trace['path']) == trace['sha256'],
                'audited raw path bytes changed')
    reports_path = Path(row['reports']['path'])
    require(sha(reports_path) == row['reports']['sha256'] == checked['reports_sha256'], 'audited report bytes changed')
    reports = [json.loads(line) for line in reports_path.read_text().splitlines()]
    require(len(reports) == 795 and [report['start_ms'] for report in reports] == row['inputs']['starts_ms'],
            'full report chronology required')
    require(all(report['cleanup'] == 'verified' and report['pending_intents'] == 0
                and report['execution_unresolved'] is False for report in reports)
            and row['sqlite']['pending'] == [], 'session or terminal cleanup incomplete')
    calls_path = reports_path.with_name('production-calls.jsonl')
    require(sha(calls_path) == checked['production_calls_sha256'], 'audited production-call proof changed')
    errors = [error for report in reports for error in report.get('errors', [])]
    fees = -sum((number(item['income']) for item in f['funding_ledger'] if item['incomeType'] == 'COMMISSION'), D(0))
    insurance = -sum((number(item['income']) for item in f['funding_ledger'] if item['incomeType'] == 'INSURANCE_CLEAR'), D(0))
    daily = original.daily_metrics(f)
    metrics = {'head': expected_head, 'receipt': identity, 'specification': artifact(spec_path),
        'source_sha256': row['source']['source_sha256'], 'producer_sha256': row['source']['producer_sha256'],
        'input_sha256': row['binding']['input_sha256'],
        'strategy_sha256': row['binding']['strategy_sha256'],
        'normalized_economic_input_sha256': helper.digest({key: value for key, value in row['inputs'].items()
                                                          if key != 'specification_sha256'}),
        'risk_configuration': {key: row['strategy'][key] for key in
                               ('capital_limit_usdt', 'max_stop_loss_fraction', 'stop_slippage_fraction')},
        'initial_cny': original.INITIAL, 'final_cny': number(f['final_cny']), 'final_usdt': number(f['final_usdt']),
        'total_return_pct': (number(f['final_cny'])/original.INITIAL-1)*100,
        'cagr_pct': original.cagr(f['final_cny']),
        'path_mdd_proxy_pct': number(audit['mdd_proxy'])*100,
        'close_observation_mdd_proxy_pct': number(audit['mdd_close_proxy'])*100,
        'daily_equity': daily, 'net_commission_paid_usdt': fees, 'insurance_charge_usdt': insurance,
        'fees_including_insurance_usdt': number(f['fees']), 'net_funding_paid_usdt': number(f['funding']),
        'fills': len(f['trades']), 'filled_ordinary_orders': sum(number(order['executedQty']) > 0 for order in f['orders'].values()),
        'income_records': len(f['funding_ledger']), 'funding_events': checked['financial']['funding_events'],
        'end_position': {'quantity_btc': number(f['quantity_btc']), 'flat': number(f['quantity_btc']) == 0,
                         'entry_usdt': number(f['entry']), 'mark_usdt': number(f['final_mark']),
                         'wallet_usdt': number(f['wallet_usdt']), 'margin_usdt': number(f['margin']),
                         'live_protections': checked['financial']['end_live_protections']},
        'cleanup': {'verified_sessions': 795, 'terminal_pending_intents': 0, 'execution_unresolved_sessions': 0,
                    'reported_error_entries': len(errors), 'reports_with_errors': sum(bool(r.get('errors')) for r in reports),
                    'error_types': dict(Counter(str(e.get('error_type','unspecified')) for e in errors)),
                    'error_reasons': dict(Counter(str(e.get('reason','unspecified')) for e in errors)),
                    'counting_note': 'Retained last-ten error entries in each terminal session report; not all attempts or exchange rejections'},
        'path_evidence': audit, 'holding_statistics': holding_statistics(f)}
    return row, spec, metrics


def paired_binding(audit, before, after, before_spec, after_spec):
    registration = audit['economic_input_registration']
    left, right = dict(before['inputs']), dict(after['inputs'])
    left_sha, right_sha = left.pop('specification_sha256'), right.pop('specification_sha256')
    require(left == right and registration['allowed_input_difference'] == 'specification_sha256 only'
            and registration['normalized_exact_economic_input_sha256'] == helper.digest(left),
            'economic inputs differ beyond the expressly registered spec identity')
    require(left_sha == registration['main_specification_sha256'] == sha(before_spec)
            and right_sha == registration['candidate_specification_sha256'] == sha(after_spec),
            'independent audit paired different specifications')
    require(registration['main_binding'] == before['binding']
            and registration['candidate_binding'] == after['binding'], 'audit paired different source/input bindings')
    require(registration['main_spec']['sha256'] == sha(before_spec)
            and registration['candidate_spec']['sha256'] == sha(after_spec), 'audit specification artifact identities differ')
    require(registration['declared_strategy_registration_differences'] ==
            helper.exact_differences(before['strategy'], after['strategy'], 'strategy'),
            'audited strategy differences changed')
    require(before['initial_usdt'] == after['initial_usdt'], 'paired initial USDT differs')


def delta(after, before):
    result = {name + '_delta_pp': after[name]-before[name]
              if after[name] is not None and before[name] is not None else None
              for name in ('cagr_pct','path_mdd_proxy_pct','total_return_pct')}
    result['daily_mdd_delta_pp'] = after['daily_equity']['full_period']['mdd_pct']-before['daily_equity']['full_period']['mdd_pct']
    result['final_cny_difference'] = after['final_cny']-before['final_cny']
    return result


def summarize(args):
    cases = registered_cases(args.case, args.check_baselines)
    old_audit = passed_audit(args.original_audit, args.original_auditor)
    previous, _, history = accepted_arm(args.historical_receipt, args.original_spec, 'previous', HISTORICAL, old_audit['main'], args.original_audit)
    baseline, _, control = accepted_arm(args.control_receipt, args.original_spec, 'current', CONTROL, old_audit['candidate'], args.original_audit)
    paired_binding(old_audit, previous, baseline, args.original_spec, args.original_spec)
    published = read(args.original_metrics)
    require(sha(args.original_metrics) == ORIGINAL_METRICS_SHA, 'original published metric bytes changed')
    fields = ('head','source_sha256','producer_sha256','input_sha256','risk_configuration','initial_cny',
              'final_cny','final_usdt','total_return_pct','cagr_pct','path_mdd_proxy_pct',
              'close_observation_mdd_proxy_pct','daily_equity','net_commission_paid_usdt','insurance_charge_usdt',
              'fees_including_insurance_usdt','net_funding_paid_usdt','fills','filled_ordinary_orders',
              'income_records','funding_events','end_position')
    for name, calculated in (('previous',history), ('current',control)):
        require({field:plain(calculated[field]) for field in fields} ==
                {field:published['arms'][name][field] for field in fields},
                'original high-precision metric calibration differs for ' + name)
    result = {'version':'coinquant-repair-results-v2',
        'period':published['period'], 'historical_context':history, 'control_2_0_0':control,
        'baseline_calibration':{'passed':True, 'reference_metrics':artifact(args.original_metrics),
                                'fields_compared_exactly':list(fields), 'tolerance':None},
        'original_audit':artifact(args.original_audit), 'cases':{}, 'case_minus_control':{},
        'factorial_cases':list(FACTORIAL_CASES), 'incremental_comparisons':{},
        'calculation_dependencies':{'original_summarizer':artifact(ROOT/'original_summarize_results.py'),
                                    'original_digest_helper':artifact(ROOT/'original_compare_arms.py')},
        'summarizer':artifact(__file__),
        'qualification':{'offline_simulation':True, 'native_execution_verified':False,
                         'online_publication_checked_by_this_script':False,
                         'public_head_basis':'Caller supplies previously verified immutable GitHub URL; this script checks its exact registered/measured head, not online accessibility.'},
        'notes':['Every accepted result completes and independently passes the full original 795-session window.',
                 'CAGR uses cost-adjusted terminal CNY and 365.2425/2454; daily MDD uses initial 10000 plus 2454 day-end values.',
                 'The first boundary is labeled 2019-12-31 and is not an extra investment year; each later year carries prior-year-end equity.',
                 'Path MDD and close-observation MDD remain historical simulation proxies; daily MDD is separately recomputed.',
                 '2026 is a partial calendar year; its annual-table return is not annualized.',
                 'Historical 79a334b is background, not the repair control. Each repair must retain the full 2.0.0 strategy/risk registration.',
                 'The original 2x2 uses combined-v2. Combined-v3 is a later registered frozen-buffer fix and never replaces that original interaction cell.',
                 'The v3-minus-v2 increment uses two full audited results with exact economic-input and strategy equality to the same 2.0.0 control; no additional replay is performed by this script.',
                 'Error entries are retained terminal-report entries, not every attempt. Fills, orders and exposure groups are separate counts.']}
    for name, registration_path, receipt_path, audit_path, public_url in cases:
        require(name not in result['cases'] and name in REPAIR_HEADS, 'duplicate or undeclared case name')
        registration_path = Path(registration_path).resolve()
        registration = read(registration_path)
        head = registration['head']
        require(head == REPAIR_HEADS[name]
                and public_url == COMMIT_PREFIX + head and registration['case'] == name,
                'public commit URL must exactly identify the registered case head')
        spec_path = registration_path.with_name('spec.json')
        require(sha(spec_path) == registration['spec_sha256'], 'case registered spec bytes changed')
        require(sha(registration_path.with_name('run_pair.py')) == registration['controller_sha256'],
                'registered case controller bytes changed')
        require(Path(registration['control_receipt']).resolve() == Path(args.control_receipt).resolve()
                and sha(registration['control_spec']) == sha(args.original_spec), 'case names another control')
        audit = passed_audit(audit_path, args.candidate_auditor)
        require(audit['main']['receipt_sha256'] == control['receipt']['sha256']
                and audit_receipt_path(audit['main'], audit_path) == Path(args.control_receipt).resolve()
                and audit['main']['source_inputs']['head'] == CONTROL,
                'repair audit must compare the complete exact 2.0.0 control')
        row, spec, metrics = accepted_arm(receipt_path, spec_path, 'current', head, audit['candidate'], audit_path)
        require(registration['runtime'] == spec['runtime_roots']['current']
                and registration['source_sha256'] == metrics['source_sha256']
                and registration['producer_sha256'] == metrics['producer_sha256']
                and registration['protocol_sha256'] == spec['protocol_sha256'] == sha(ROOT/'PROTOCOL.md'),
                'case registration does not bind this source/protocol')
        if name in BOOK_GUARD_CASES:
            require(registration['book_guard_amendment_sha256'] == spec['book_guard_amendment_sha256']
                    == sha(ROOT/'BOOK_GUARD_AMENDMENT_V2.md'), 'registered v2 book-guard amendment bytes changed')
        if name == 'combined-v3':
            require(registration['frozen_buffer_amendment_sha256'] == spec['frozen_buffer_amendment_sha256']
                    == sha(ROOT/'FROZEN_BUFFER_AMENDMENT_V3.md') == FROZEN_BUFFER_AMENDMENT_SHA,
                    'registered v3 frozen-buffer amendment bytes changed')
            require(registration['incremental_base'] == spec['incremental_base'] == INCREMENTAL_BASE,
                    'v3 incremental_base must bind the unchanged full combined-v2 result')
        require(registration['fixed_risk'] == spec['risk_by_arm']['current'] == control['risk_configuration']
                and row['strategy'] == baseline['strategy'], 'repair changed the registered 2.0.0 economic settings')
        paired_binding(audit, baseline, row, args.original_spec, spec_path)
        metrics.update(registration=artifact(registration_path), audit=artifact(audit_path),
                       auditor=artifact(args.candidate_auditor), public_commit_url=public_url,
                       protocol=artifact(ROOT/'PROTOCOL.md'))
        if name in BOOK_GUARD_CASES:
            metrics['book_guard_amendment']=artifact(ROOT/'BOOK_GUARD_AMENDMENT_V2.md')
        if name == 'combined-v3':
            metrics['frozen_buffer_amendment'] = artifact(ROOT/'FROZEN_BUFFER_AMENDMENT_V3.md')
            metrics['incremental_base'] = dict(INCREMENTAL_BASE)
        result['cases'][name] = metrics
        result['case_minus_control'][name] = delta(metrics, control)
    if set(FACTORIAL_CASES) <= set(result['cases']):
        margin,book,combined = (result['cases'][name] for name in ('margin-only','book-v2-only','combined-v2'))
        result['factorial_interaction'] = {
            'basis':'Observed combined-v2 - margin-only - book-v2-only + control; preserved descriptive 2x2 interaction on this fixed historical path. CAGR and MDD effects are nonlinear. Combined-v3 is excluded.',
            **{name+'_interaction_pp':combined[name]-margin[name]-book[name]+control[name]
               if all(arm[name] is not None for arm in (margin,book,combined,control)) else None
               for name in ('cagr_pct','path_mdd_proxy_pct')},
            'daily_mdd_interaction_pp':sum(sign*arm['daily_equity']['full_period']['mdd_pct']
                for sign,arm in ((1,combined),(-1,margin),(-1,book),(1,control))),
            'final_cny_interaction':combined['final_cny']-margin['final_cny']-book['final_cny']+control['final_cny']}
    if 'combined-v3' in result['cases']:
        before, after = (result['cases'][name] for name in ('combined-v2','combined-v3'))
        require({'case':'combined-v2', 'head':before['head'],
                 'spec_sha256':before['specification']['sha256'],
                 'receipt_sha256':before['receipt']['sha256']} == INCREMENTAL_BASE,
                'accepted combined-v2 differs from the registered incremental base')
        require(before['normalized_economic_input_sha256'] == after['normalized_economic_input_sha256']
                == control['normalized_economic_input_sha256']
                and before['strategy_sha256'] == after['strategy_sha256'] == control['strategy_sha256'],
                'incremental results do not share the exact audited control inputs and strategy')
        result['incremental_comparisons']['combined-v3_minus_combined-v2'] = {
            'before_case':'combined-v2', 'after_case':'combined-v3',
            'basis':'Difference between two completed full795 results, each independently audited against the same exact 2.0.0 control. Economic inputs are exactly equal apart from registered specification identity, and strategies match the control. This is transitive input consistency, not an additional replay or a new 2x2 cell.',
            'incremental_base':dict(INCREMENTAL_BASE),
            'control_receipt':control['receipt'], 'before_receipt':before['receipt'], 'after_receipt':after['receipt'],
            'normalized_economic_input_sha256':control['normalized_economic_input_sha256'],
            'strategy_sha256':control['strategy_sha256'],
            'audits_against_control':{'combined-v2':before['audit'], 'combined-v3':after['audit']},
            'amendment':after['frozen_buffer_amendment'], 'delta':delta(after,before)}
    result['accepted_full_window_cases'] = ['control_2_0_0'] + list(result['cases'])
    result['all_three_registered_repairs_present'] = set(FACTORIAL_CASES) <= set(result['cases'])
    result['all_four_registered_repairs_present'] = set(result['cases']) == set(REPAIR_HEADS)
    return plain(result)


def markdown(result):
    arms = [('历史79a（背景）',result['historical_context']), ('2.0.0控制组',result['control_2_0_0'])]
    labels = REPAIR_LABELS
    arms += [(labels[name],row) for name,row in result['cases'].items()]
    lines=['# Coinquant 最终修复结果：原 2×2 与冻结缓冲增量', '',
        '仅纳入登记源码、spec 配对一致且独立 full795 审计通过的完整结果。原 2.0.0（162ee713）是修复控制组；79a334b 只作历史背景。', '',
        '窗口 `[2020-01-01T00:00Z, 2026-09-20T00:00Z)`，2454 天，初始 10,000 CNY；CAGR 采用 365.2425 天/年。', '',
        '| 指标 | '+' | '.join(name for name,_ in arms)+' |', '|---|'+'---:|'*len(arms)]
    rows=[('成本后 CAGR',lambda a:display(a['cagr_pct'])+'%'),
          ('路径最大回撤代理',lambda a:display(a['path_mdd_proxy_pct'])+'%'),
          ('日收盘最大回撤',lambda a:display(a['daily_equity']['full_period']['mdd_pct'])+'%'),
          ('期末权益 CNY',lambda a:display(a['final_cny'],2)),
          ('净手续费 USDT',lambda a:display(a['net_commission_paid_usdt'],2)),
          ('净支付资金费 USDT',lambda a:display(a['net_funding_paid_usdt'],2)),
          ('分笔成交 / 有成交普通订单',lambda a:f"{a['fills']} / {a['filled_ordinary_orders']}"),
          ('完整持仓段 / 期末未平段',lambda a:f"{a['holding_statistics']['closed_exposure_groups']} / {a['holding_statistics']['open_exposure_groups']}"),
          ('五分钟内结束的持仓段',lambda a:str(a['holding_statistics']['closed_within_300_seconds'])),
          ('持仓时间中位数（天）',lambda a:display(a['holding_statistics']['median_closed_holding_days'])),
          ('完整会话 / 已验证清理',lambda a:'795 / 795')]
    lines += ['| '+name+' | '+' | '.join(extract(arm) for _,arm in arms)+' |' for name,extract in rows]
    lines += ['', '## 相对 2.0.0 控制组', '', '| 修复 | CAGR变化（百分点） | 路径回撤变化（百分点） | 日收盘回撤变化（百分点） | 期末权益差 CNY |', '|---|---:|---:|---:|---:|']
    for name,d in result['case_minus_control'].items():
        lines.append('| '+labels[name]+' | '+' | '.join(display(d[key],4,True) for key in
            ('cagr_pct_delta_pp','path_mdd_proxy_pct_delta_pp','daily_mdd_delta_pp','final_cny_difference'))+' |')
    lines += ['', '## 分年日权益收益与回撤', '',
        '每格为“当年收益率 / 当年日收盘最大回撤”。每年带入上年末权益；2026 年只到 9 月 19 日日终，表中未作年化。', '',
        '| 年度 | '+' | '.join(name for name,_ in arms)+' |', '|---|'+'---:|'*len(arms)]
    for i in range(7):
        year=arms[0][1]['daily_equity']['by_year'][i]['year']
        values=[f"{display(arm['daily_equity']['by_year'][i]['return_pct'])}% / {display(arm['daily_equity']['by_year'][i]['mdd_pct'])}%" for _,arm in arms]
        lines.append(f'| {year} | '+' | '.join(values)+' |')
    if 'factorial_interaction' in result:
        interaction=result['factorial_interaction']
        lines += ['', '## 原两项修复的交互（保留 combined-v2）', '',
            '按“combined-v2 − 仅定仓 − 仅盘口 v2 + 控制”计算，是同一历史路径上的描述性交互。此处不使用 combined-v3。CAGR 与回撤不具有线性可加性，不能据此承诺未来收益。', '',
            '| 指标 | 交互值 |', '|---|---:|']
        for label,key in [('CAGR（百分点）','cagr_pct_interaction_pp'),('路径回撤（百分点）','path_mdd_proxy_pct_interaction_pp'),
                          ('日收盘回撤（百分点）','daily_mdd_interaction_pp'),('期末权益 CNY','final_cny_interaction')]:
            lines.append(f'| {label} | {display(interaction[key],4,True)} |')
    if result['incremental_comparisons']:
        increment = result['incremental_comparisons']['combined-v3_minus_combined-v2']
        lines += ['', '## 冻结强平缓冲修复的增量（v3 − v2）', '',
            '两组均分别对同一完整 2.0.0 控制组通过独立 full795 审计，经济输入除各自 spec 身份外逐项相同，策略与风险配置一致。本节利用共同控制的传递一致性，直接计算两个已审计完整结果之差，没有再次回放。', '',
            'v3 是观察组合 v2 完整结果后登记的后续缺陷修复，保留原 v2 源码及结果；这项事后增量比较不是样本外验收。', '',
            '| 指标 | v3 − v2 |', '|---|---:|']
        for label,key in [('CAGR（百分点）','cagr_pct_delta_pp'),('路径回撤（百分点）','path_mdd_proxy_pct_delta_pp'),
                          ('日收盘回撤（百分点）','daily_mdd_delta_pp'),('期末权益 CNY','final_cny_difference')]:
            lines.append(f"| {label} | {display(increment['delta'][key],4,True)} |")
    lines += ['', '## 身份与证据', '', '| 组 | 精确源码提交 | 回执 SHA-256 |', '|---|---|---|']
    for label,arm in arms:
        url=arm.get('public_commit_url',COMMIT_PREFIX+arm['head'])
        lines.append(f"| {label} | [{arm['head']}]({url}) | `{arm['receipt']['sha256']}` |")
    lines += ['', '完整 JSON 保留未舍入值、逐年权益、持仓段、spec / 回执 / 审计 / 计算脚本身份及原模拟路径证明。摘要与完整审计文件按 SHA-256 绑定，原有两臂指标逐字段精确复算通过。', '',
        '本脚本只验证调用方提供的公共提交 URL 与登记、实测 head 一致，不进行在线可达性核验；公共 commit/tree 读回由另行保存的发布验证记录证明。', '',
        '路径回撤仍采用原 OHLC 极值次序、逐笔成交与标记价格代理以及缺口 hindsight bound。日收盘回撤来自 `financial.daily`，不使用 `financial.mdd_close` 替代。它们是历史模拟结果，不是原生交易风险验收或样本外结果。']
    return '\n'.join(lines)+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--case', action='append', nargs=5, default=[], metavar=('NAME','REGISTRATION','RECEIPT','AUDIT','PUBLIC_URL'))
    p.add_argument('--control-receipt', type=Path, default=FROZEN/'full-current-segment-002.json.gz')
    p.add_argument('--historical-receipt', type=Path, default=FROZEN/'full-previous-segment-003.json.gz')
    p.add_argument('--original-spec', type=Path, default=ORIGINAL/'spec.json')
    p.add_argument('--original-audit', type=Path, default=FROZEN/'full-audit-summary.json')
    p.add_argument('--original-auditor', type=Path, default=ORIGINAL/'independent_financial_audit.py')
    p.add_argument('--original-metrics', type=Path, default=FROZEN/'metrics.json')
    p.add_argument('--candidate-auditor', type=Path, default=ROOT/'independent_financial_audit.py')
    p.add_argument('--check-baselines', action='store_true', help='Verify original published values exactly; no files written')
    p.add_argument('--out', type=Path)
    p.add_argument('--markdown', type=Path)
    args=p.parse_args()
    require(bool(args.case) or args.check_baselines, 'provide complete --case evidence or --check-baselines')
    if args.check_baselines:
        require(not args.case and args.out is None and args.markdown is None,
                '--check-baselines is an output-free mathematical calibration, not a candidate result')
    else:
        args.out = args.out or ROOT/'FINAL_RESULTS.json'
        args.markdown = args.markdown or ROOT/'FINAL_RESULTS.md'
        require(args.out.resolve()!=args.markdown.resolve() and not args.out.exists() and not args.markdown.exists(),
                'new distinct output paths required; existing evidence is never overwritten')
    with localcontext() as context:
        context.prec=50
        result=summarize(args)
        if args.check_baselines:
            print(json.dumps({'passed':True,'baseline_fields_compared':len(result['baseline_calibration']['fields_compared_exactly']),
                'control_cagr_pct':result['control_2_0_0']['cagr_pct'],
                'historical_cagr_pct':result['historical_context']['cagr_pct'],
                'candidate_results_claimed':False,'files_written':False}, ensure_ascii=False))
            return
        body=markdown(result)
        for path,text in ((args.out,json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n'),(args.markdown,body)):
            with path.open('x',encoding='utf-8') as stream:
                stream.write(text)
        print(json.dumps({'accepted_full_window_cases':result['accepted_full_window_cases'],
                          'all_three_registered_repairs_present':result['all_three_registered_repairs_present'],
                          'all_four_registered_repairs_present':result['all_four_registered_repairs_present'],
                          'metrics':artifact(args.out),'markdown':artifact(args.markdown)},ensure_ascii=False))


if __name__=='__main__':
    try:
        main()
    except (ValueError,KeyError,TypeError,OSError) as exc:
        print('repair_results_v2 rejected input: '+str(exc),file=sys.stderr)
        raise SystemExit(1)
