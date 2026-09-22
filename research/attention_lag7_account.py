"""Replay the one frozen post-hoc C2_lag7 attention account experiment.

This is deliberately a runner, not a new signal search.  It accepts only the
saved lag7 prediction rows and delegates all account mechanics to the shared
payoff and persistent-hold replay code.
"""
import argparse
import csv
from decimal import Decimal as D
import gzip
import hashlib
import json
from pathlib import Path
import shutil

from pancakequant.research import invocations, spec, timestamp
from research.executable_payoff import RULES, WARM, REPAIR, account, load
from research.payoff_audit import audit
from research.persistent_hold_replay import DAY, run as replay
from research.target_attribution import summarize


ARCHIVES = [
    dict(name='PANCAKEQUANT_ATTENTION_EVIDENCE_20260922.zip', bytes=3373375,
         sha256='ffd0195d2b7e47c8b9a7ee1bf7fae2f50a6fc3523eec96bca89d7e46157dfa56'),
    dict(name='PANCAKEQUANT_EXECUTABLE_PAYOFF_EVIDENCE_20260922.zip', bytes=53179721,
         sha256='0b46f6fccff4c68d7accc23ef126fbaefb6fdbb3143d3dfb6c74e5912c0c892f'),
    dict(name='PANCAKEQUANT_RETURN_FIRST_L21_L26_20260921.zip', bytes=140850994,
         sha256='001813d77bb3d4ceba82c2a73f37f5513ffd6eef91cd42f5cd344fe9401b4357'),
    dict(name='PANCAKEQUANT_L29_RETURN_CAPTURE_20260921.zip', bytes=141577623,
         sha256='79d3fdbc28cedfbaaa144c1541b3b7b73293d7a97b81052a341d4be017628abe'),
    dict(name='PANCAKEQUANT_BASIS_DIRECTION_ECONOMIC_EVIDENCE_20260921.zip', bytes=15486668,
         sha256='b33a6e53e23e6b52ba6d01b22fc2e8a20d2538a526d8dc6a615c6423ed8a452f'),
]
INPUT_FILES = ('lag7_predictions.json', 'lag7_fits.json', 'weeks.json')
EXPECTED_INPUT_SHA256 = {
    'lag7_predictions.json': 'f7e4d38caa9bcbc6c8085ab5b29ddec3ff4e6884c57c2045d0316024e4219282',
    'lag7_fits.json': '455d1b95f7b8f254ea2ee849cad743a45f6bebc72880004fd173222d863888c0',
    'weeks.json': '413133e6b048506ca5df5cabeb7a22bfdd41126505c707e1fc1c3e2669e4067b',
    'labels.json': '03c4ba9c6ef54260175e72b86dd35888b826c16c9900420146ded8d6c7b9e329',
}
EXPECTED_PRIOR_B1_SHA256 = {
    'inputs.json': 'b54a9d0391f2575d21b9e7137dcd7dbeb14c9413220077592e64a1449fb60f4f',
    'result.json': '3be7eedec00d1c542a6f469bafacfa2a0afc56a0fe50921ae28e9489f5893065',
}
EXPECTED_PRIOR_B1_TRACE_SHA256 = {
    'orders.csv.gz': '50af2da789bef02d31fd7022e61f0a9e75bd9b06259b718f4830436812d3fd5f',
    'equity.csv.gz': '919aa2f45d63974a02884d1618c2e7210fe3101a8c7e1b8ff1b23eff32bab659',
    'decisions.csv.gz': '4b53febaeb581744a648a3e05a9e35888060731a77c272a4e165f41fe458b3c5',
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prediction_streams(attention):
    """Load and causally validate the saved, extra-seven-day prediction rows."""
    attention = Path(attention)
    rows = json.loads((attention/'lag7_predictions.json').read_text())
    if not isinstance(rows, list) or not rows:
        raise ValueError('saved lag7 predictions are empty')
    start = timestamp(spec()['start'])
    end = timestamp(spec()['development_end'])
    calls = sorted(call for call in invocations(spec()) if call < end)
    streams = {name: {} for name in ('C0', 'C1', 'C2_lag7')}
    prior = None
    for row in rows:
        required = ('t', 'u', 'week_end', 'assumed_available_at', 'available_at', 'status', 'C0', 'C1', 'C2')
        if any(key not in row for key in required):
            raise ValueError('incomplete saved lag7 row')
        t, u = int(row['t']), int(row['u'])
        if prior is not None and t <= prior:
            raise ValueError('saved lag7 timestamps are not strictly increasing')
        if not (start <= t < end and t < u <= end):
            raise ValueError('saved lag7 row lies outside the development account')
        expected_u = next((call for call in calls if call >= t + 7*DAY), None)
        if t not in calls or (expected_u is not None and u != expected_u) or (expected_u is None and u != end):
            raise ValueError('saved lag7 row does not use frozen sparse expiry')
        if row['status'] not in ('eligible', 'unfunded_or_unsafe') or row['available_at'] is not None:
            raise ValueError('saved lag7 row lost its frozen proxy status')
        if int(row['assumed_available_at']) != int(row['week_end']) + 9*DAY:
            raise ValueError('saved lag7 availability is not week end plus nine days')
        if int(row['assumed_available_at']) > t:
            raise ValueError('saved lag7 prediction is not available by its invocation')
        values = (row['C0'], row['C1'], row['C2'])
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values):
            raise ValueError('saved lag7 prediction is not numeric')
        streams['C0'][t] = float(row['C0'])
        streams['C1'][t] = float(row['C1'])
        streams['C2_lag7'][t] = float(row['C2'])
        prior = t
    return rows, streams


def canonical(records):
    return sorted(json.dumps(row, sort_keys=True, separators=(',', ':')) for row in records)


def verify_native_inputs(bundle, minutes, prior_b1):
    """Prove that the current shared cache is the old B1 raw input set."""
    prior = json.loads((Path(prior_b1)/'inputs.json').read_text())
    actual = list(bundle[3]) + list(minutes[1]) + [dict(path=str(RULES), sha256=sha256(RULES))]
    minute_rows = [row for row in minutes[1] if '/1m/' in row.get('path', '')]
    prior_minutes = [row for row in prior if '/1m/' in row.get('path', '')]
    result = dict(
        shared_raw_records=len(actual),
        prior_b1_raw_records=len(prior),
        current_minute_records=len(minute_rows),
        prior_b1_minute_records=len(prior_minutes),
        minute_identity_equal=canonical(minute_rows) == canonical(prior_minutes),
        complete_identity_equal=canonical(actual) == canonical(prior),
    )
    result['passed'] = result['current_minute_records'] == 22 and result['minute_identity_equal'] and result['complete_identity_equal']
    return result


def copy_frozen_inputs(attention, labels, prior_b1, output):
    output = Path(output)
    frozen = output/'frozen_inputs'
    if frozen.exists():
        raise ValueError('frozen inputs already exist; refusing to overwrite a run')
    frozen.mkdir()
    records = []
    for name in INPUT_FILES:
        source = Path(attention)/name
        target = frozen/name
        shutil.copy2(source, target)
        if sha256(target) != EXPECTED_INPUT_SHA256[name]:
            raise ValueError(f'wrong frozen {name} identity')
        records.append(dict(name=name, source=str(source), bytes=target.stat().st_size, sha256=sha256(target)))
    for name, source in (('labels.json', Path(labels)),):
        target = frozen/name
        shutil.copy2(source, target)
        expected = EXPECTED_INPUT_SHA256.get(name)
        if expected and sha256(target) != expected:
            raise ValueError(f'wrong frozen {name} identity')
        records.append(dict(name=name, source=str(source), bytes=target.stat().st_size, sha256=sha256(target)))
    prior_snapshot = frozen/'prior_B1'
    prior_snapshot.mkdir()
    prior_files = EXPECTED_PRIOR_B1_SHA256 | EXPECTED_PRIOR_B1_TRACE_SHA256
    for name, expected in prior_files.items():
        source = Path(prior_b1)/name
        target = prior_snapshot/name
        shutil.copy2(source, target)
        if sha256(target) != expected:
            raise ValueError(f'wrong archived B1 {name} identity')
        records.append(dict(name='prior_B1/'+name, source=str(source), bytes=target.stat().st_size, sha256=sha256(target)))
    identity = dict(
        status='POST_HOC_EXPLORATORY / RETROSPECTIVE_PROXY',
        purpose='saved C0/C1/C2_lag7 predictions only; no labels or fits regenerated',
        archives=ARCHIVES,
        files=records,
    )
    (frozen/'identity.json').write_text(json.dumps(identity, indent=2)+'\n')
    return frozen, identity


def attach_frozen_inputs(root, frozen):
    target = Path(root)/'frozen_attention_inputs'
    target.mkdir()
    for name in (*INPUT_FILES, 'labels.json', 'identity.json'):
        shutil.copy2(Path(frozen)/name, target/name)


def decompressed_sha256(path):
    digest = hashlib.sha256()
    with gzip.open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def trace_equivalence(current, prior_b1):
    files = {}
    for name in ('orders.csv.gz', 'equity.csv.gz', 'decisions.csv.gz'):
        new_hash = decompressed_sha256(Path(current)/name)
        old_hash = decompressed_sha256(Path(prior_b1)/name)
        files[name] = dict(current_decompressed_sha256=new_hash, prior_b1_decompressed_sha256=old_hash,
                           equal=new_hash == old_hash)
    current_inputs = json.loads((Path(current)/'inputs.json').read_text())
    prior_inputs = json.loads((Path(prior_b1)/'inputs.json').read_text())
    return dict(
        input_identity_equal=canonical(current_inputs) == canonical(prior_inputs),
        files=files,
        trace_equal=all(value['equal'] for value in files.values()),
    )


def decision_rows(path):
    with gzip.open(Path(path)/'decisions.csv.gz', 'rt') as stream:
        return {int(row['time']): row for row in csv.DictReader(stream)}


def changed_signal_attribution(rows, c1, c2):
    """Descriptive attribution for the only permitted C1/C2 input difference."""
    decisions = dict(C1=decision_rows(c1), C2_lag7=decision_rows(c2))
    audits = dict(C1=audit(c1), C2_lag7=audit(c2))
    trades = {name: {trade['t']: trade for trade in value['trades']} for name, value in audits.items()}
    cases = []
    for row in rows:
        c1_sign = float(row['C1']) > 0
        c2_sign = float(row['C2']) > 0
        if c1_sign == c2_sign:
            continue
        t = int(row['t'])
        cases.append(dict(
            t=t, month=row['month'], C1_prediction=row['C1'], C2_lag7_prediction=row['C2'],
            C1_action=decisions['C1'].get(t, {}).get('action'),
            C2_lag7_action=decisions['C2_lag7'].get(t, {}).get('action'),
            C1_trade=trades['C1'].get(t), C2_lag7_trade=trades['C2_lag7'].get(t),
        ))
    return dict(changed_prediction_signs=len(cases), cases=cases)


def candidate_record(root):
    root = Path(root)
    summarize(root)
    checked = audit(root)
    (root/'ACCOUNT_AUDIT.json').write_text(json.dumps(checked, indent=2)+'\n')
    result = json.loads((root/'result.json').read_text())
    return dict(
        root=str(root),
        result=result,
        audit=checked,
        attribution=json.loads((root/'attribution.json').read_text()),
        cagr_fraction=result['cagr'],
        cagr_percent=100*result['cagr'],
        mdd_fraction=float(result['mdd_conservative_envelope']),
        mdd_percent=100*float(result['mdd_conservative_envelope']),
        final_cny=result['final_cny'],
        insolvent_hours=result['counts'].get('nonpositive_equity_hours', 0),
        accounting_error_usdt=checked['ledger']['max_equity_error_usdt'],
    )


def run_window(native, output, streams, full=False, bundle=None, minutes=None):
    if bundle is None or minutes is None:
        bundle, minutes = load(native, full=full)
    candidates = {}
    for name, predictions in streams.items():
        root = Path(output)/name
        account(native, root, bundle, minutes, predictions, name, full_window=full)
        candidates[name] = candidate_record(root)
    l3 = Path(output)/'L3.6'
    replay(native, WARM, REPAIR, l3, quantity_rules=RULES, schedule='sparse', lifecycle='one_campaign',
           allocation='volatility', reference='impulse_hold', protection='fixed', full_window=full,
           risk_scale=D('3.6'), entry_side='long', short_risk_scale=D('0'),
           cached_inputs=bundle, cached_minutes=minutes)
    candidates['L3.6'] = candidate_record(l3)
    return candidates, bundle, minutes


def gate(candidates, input_check, equivalence):
    c1, c2, l3 = candidates['C1'], candidates['C2_lag7'], candidates['L3.6']
    ledger_ok = all(D(record['accounting_error_usdt']) <= D('1e-18') for record in candidates.values())
    conditions = dict(
        C2_cagr_exceeds_C1=c2['cagr_fraction'] > c1['cagr_fraction'],
        C2_cagr_exceeds_L3_6=c2['cagr_fraction'] > l3['cagr_fraction'],
        C2_mdd_below_50_percent=D(str(c2['mdd_fraction'])) < D('.5'),
        no_nonpositive_equity=c2['insolvent_hours'] == 0,
        shared_input_identity=input_check['passed'],
        independent_ledger_checks=ledger_ok,
        no_partial_trace=all(not list(Path(record['root']).glob('*.partial')) for record in candidates.values()),
    )
    # C1's old B1 trace is evidence, not a substitute for the freshly audited control.
    return dict(passed=all(conditions.values()), conditions=conditions,
                C1_vs_prior_B1=equivalence,
                stop='run full window only when every condition is true; otherwise stop this candidate')


def write_report(output, summary):
    rows = []
    for name in ('C0', 'C1', 'C2_lag7', 'L3.6'):
        value = summary['development']['candidates'][name]
        rows.append(f"| {name} | {value['cagr_percent']:.6f}% | {value['mdd_percent']:.6f}% | {value['final_cny']} | {value['result']['counts'].get('entry', 0)} | {value['result']['holding_hours']} |")
    if summary['full_window']['ran']:
        verdict = '通过开发门槛，已执行完整窗口复核。'
    elif summary['development_gate']['passed']:
        verdict = '开发门槛通过，但完整窗口被显式跳过；不能把开发结果称为完整窗口复核。'
    else:
        verdict = '未通过开发门槛；按协议停止，不运行 2024+，不调参。'
    changed = summary['changed_signal_attribution']['changed_prediction_signs']
    text = "\n".join([
        '# C2_lag7 连续账户结果',
        '',
        '`POST_HOC_EXPLORATORY / RETROSPECTIVE_PROXY`。只使用已保存的 C2_lag7 预测；未重训标签或模型，未改变账户、仓位、风险预算或执行权限。',
        '',
        '## 2020--2023 连续开发账户',
        '',
        '| 对照 | CAGR | 连续 MDD 包络 | 期末 CNY | 入场 | 持仓小时 |',
        '| --- | ---: | ---: | ---: | ---: | ---: |',
        *rows,
        '',
        '## 判断',
        '',
        f'- {verdict}',
        f'- C1 对旧 B1 解压轨迹等价：`{summary["development_gate"]["C1_vs_prior_B1"]["trace_equal"]}`；输入身份等价：`{summary["development_gate"]["C1_vs_prior_B1"]["input_identity_equal"]}`。',
        f'- C1/C2 预测符号不同的冻结调用数：{changed}；逐笔描述见 `CHANGED_SIGNAL_ATTRIBUTION.json`。',
        '- 逐账户独立现金账本、逐年/费用/funding/敞口归因见各账户目录；本报告不把回溯代理结果称为正式验收。',
        '',
        '## 限制',
        '',
        'Wikimedia 访问量没有可验证的历史 vintage/发布时间；即使本代理回放改善，也不满足正式 150% CAGR / <50% MDD 或生产启用条件。',
    ])
    (Path(output)/'REPORT.md').write_text(text+'\n')


def run(native, attention, labels, prior_b1, output, skip_full_if_gate=False):
    output = Path(output)
    if not (output/'PROTOCOL.md').is_file():
        raise ValueError('the pre-computation protocol must exist first')
    if (output/'SUMMARY.json').exists():
        raise ValueError('this account experiment is already complete; refusing to overwrite it')
    frozen, frozen_identity = copy_frozen_inputs(attention, labels, prior_b1, output)
    rows, streams = prediction_streams(frozen)
    bundle, minutes = load(native)
    prior_snapshot = frozen/'prior_B1'
    input_check = verify_native_inputs(bundle, minutes, prior_snapshot)
    (output/'NATIVE_INPUT_CHECK.json').write_text(json.dumps(input_check, indent=2)+'\n')
    if not input_check['passed']:
        raise ValueError('native input identity differs from the audited B1 control')
    development, _, _ = run_window(native, output, streams, bundle=bundle, minutes=minutes)
    for name in development:
        attach_frozen_inputs(output/name, frozen)
    equivalence = trace_equivalence(output/'C1', prior_snapshot)
    changed = changed_signal_attribution(rows, output/'C1', output/'C2_lag7')
    (output/'CHANGED_SIGNAL_ATTRIBUTION.json').write_text(json.dumps(changed, indent=2)+'\n')
    development_gate = gate(development, input_check, equivalence)
    full = None
    if development_gate['passed'] and not skip_full_if_gate:
        full_root = output/'full-window'
        full, _, _ = run_window(native, full_root, streams, full=True)
        for name in full:
            attach_frozen_inputs(full_root/name, frozen)
    summary = dict(
        status='POST_HOC_EXPLORATORY / RETROSPECTIVE_PROXY',
        frozen_input_identity=frozen_identity,
        development=dict(window='2020-01-01T00:00:00Z to 2024-01-01T00:00:00Z exclusive', candidates=development),
        native_input_check=input_check,
        changed_signal_attribution=changed,
        development_gate=development_gate,
        full_window=dict(ran=full is not None, candidates=full,
                         reason='development gate passed' if full is not None else 'development gate failed or was explicitly skipped'),
    )
    (output/'SUMMARY.json').write_text(json.dumps(summary, indent=2)+'\n')
    write_report(output, summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', required=True, type=Path)
    parser.add_argument('--attention', required=True, type=Path, help='directory containing saved lag7 JSON files')
    parser.add_argument('--labels', required=True, type=Path)
    parser.add_argument('--prior-b1', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--skip-full-if-gate', action='store_true')
    args = parser.parse_args()
    run(args.native, args.attention, args.labels, args.prior_b1, args.output, args.skip_full_if_gate)
