"""Summarize completed, independently audited fixed-SHA paired replay receipts.

No production/research imports, replay, input inference or prefilled results.
All published rates use Decimal; JSON retains unrounded decimal strings.
"""
import argparse
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal as D, localcontext
import gzip
import hashlib
import json
from pathlib import Path
import sys

DAY = 86_400_000
START = 1577836800000
END = 1789862400000
DAYS = 2454
YEAR_DAYS = D('365.2425')
INITIAL = D('10000')
HEADS = {
    'previous': '79a334b2d776be2dbe8756f3a616697f9403982e',
    'current': '162ee7138952925ffafbc9b68be7c754c0c0a6c3',
}
HISTORICAL = {
    'cagr_pct': '167.94868978615018',
    'path_mdd_proxy_pct': '46.27197712514759',
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def number(value):
    result = D(value)
    require(result.is_finite(), 'nonfinite financial amount')
    return result


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def read(path):
    path = Path(path)
    with (gzip.open(path, 'rt', encoding='utf-8') if path.suffix == '.gz'
          else path.open(encoding='utf-8')) as source:
        return json.load(source)


def artifact(path):
    path = Path(path).resolve()
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def plain(value):
    if isinstance(value, D):
        return str(value)
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    return value


def cagr(final):
    final = number(final)
    if final < 0:
        return None
    return ((final / INITIAL) ** (YEAR_DAYS / D(DAYS)) - 1) * 100


def period(points, opening, opening_at):
    """Daily-close MDD includes the period's carried opening capital."""
    require(bool(points), 'period has no observed daily closing equity')
    opening = number(opening)
    peak, peak_at = opening, opening_at
    maximum = D(0) if opening > 0 else None
    worst = None
    for point in points:
        value = number(point['equity_cny'])
        if value > peak:
            peak, peak_at = value, point['date']
        if peak > 0:
            drawdown = (1 - value / peak) * 100
            if maximum is None or drawdown > maximum:
                maximum = drawdown
                worst = {'peak_at': peak_at, 'trough_date': point['date'],
                         'peak_equity_cny': peak, 'trough_equity_cny': value}
    final = number(points[-1]['equity_cny'])
    return {'start_date': points[0]['date'], 'end_date': points[-1]['date'],
            'days': len(points), 'opening_equity_cny': opening,
            'opening_equity_at': opening_at, 'ending_equity_cny': final,
            'return_pct': (final / opening - 1) * 100 if opening > 0 else None,
            'mdd_pct': maximum, 'mdd_event': worst}


def daily_metrics(financial):
    raw = financial['daily']
    # capture() dates a midnight valuation to the day just finished. The first
    # entry is the opening post-conversion snapshot, not a 2019 investment year.
    expected_stamps = list(range(START, END + DAY, DAY))
    require(len(raw) == DAYS + 1 and [p['stamp_ms'] for p in raw] == expected_stamps,
            'complete ordered daily boundary series required; no missing-value imputation')
    for point in raw:
        expected_date = datetime.fromtimestamp((point['stamp_ms'] - 1) / 1000,
                                               timezone.utc).date().isoformat()
        require(point['date'] == expected_date, 'daily date does not match its UTC closing boundary')
        number(point['equity_cny'])
    days = raw[1:]
    whole = period(days, INITIAL, '2020-01-01T00:00:00Z:initial-capital')
    annual = []
    carry, carry_at = INITIAL, whole['opening_equity_at']
    for year in range(2020, 2027):
        points = [p for p in days if date.fromisoformat(p['date']).year == year]
        row = period(points, carry, carry_at)
        row['year'] = year
        row['complete_calendar_year'] = (row['start_date'] == f'{year}-01-01'
                                         and row['end_date'] == f'{year}-12-31')
        annual.append(row)
        carry, carry_at = row['ending_equity_cny'], row['end_date']
    return {'basis': 'financial.daily UTC closing-boundary valuations; initial 10000; annual prior-year-end carry',
            'missing_values_imputed': 0, 'opening_post_conversion_cny': number(raw[0]['equity_cny']),
            'full_period': whole, 'by_year': annual,
            'terminal_vs_daily_equity_difference_cny': number(financial['final_cny']) - carry}


def load_arm(path, arm, checked):
    path = Path(path).resolve()
    receipt_identity = artifact(path)
    require(Path(checked['receipt']).resolve() == path
            and checked['receipt_sha256'] == receipt_identity['sha256'], 'audit names another ' + arm + ' receipt')
    row = read(path)
    require(row['complete'] is True and row['original_window_complete'] is True
            and row['failure'] is None and row['session_count'] == checked['sessions'] == 795,
            'full successful 795-session receipt required for ' + arm)
    require(row['no_live_account'] is True and row['native_verified'] is False,
            'expected offline measurement qualification')
    require(row['source']['git_head'] == checked['source_inputs']['head'] == HEADS[arm],
            'unexpected fixed runtime head for ' + arm)
    for field in ('source_sha256', 'producer_sha256'):
        require(row['source'][field] == checked['source_inputs'][field], 'audited source identity ' + field)
    require(row['binding']['input_sha256'] == checked['source_inputs']['input_sha256'], 'audited input identity')
    f = row['financial']
    require(number(row['initial_cny']) == INITIAL
            and row['inputs']['starts_ms'][0] == START
            and row['terminal_ms'] == row['at_ms'] == f['now_ms'] == END
            and (END - START) // DAY == DAYS, 'fixed 2454-day measurement window')
    require(f['audit']['passed'] is True and checked['financial']['passed'] is True,
            'independent financial audit did not pass')
    path_check = checked['path_audit']
    require(path_check['passed'] is True and path_check['rolling_digest_recomputed'] is True,
            'independently recomputed full path required')
    require(path_check['points'] == f['path_audit']['count']
            and path_check['rolling_sha256'] == f['path_audit']['rolling_sha256']
            and number(path_check['mdd_proxy']) == number(f['mdd'])
            and number(path_check['mdd_close_proxy']) == number(f['mdd_close']), 'audited path identity/metrics')
    require(bool(path_check['raw_trace_files']), 'raw path evidence absent')
    reports_path = Path(row['reports']['path'])
    require(sha(reports_path) == row['reports']['sha256'] == checked['reports_sha256'], 'audited session report bytes')
    with reports_path.open(encoding='utf-8') as source:
        reports = [json.loads(line) for line in source]
    require(len(reports) == 795 and [p['start_ms'] for p in reports] == row['inputs']['starts_ms'], 'full report chronology')
    require(all(p['cleanup'] == 'verified' and p['pending_intents'] == 0
                and p['execution_unresolved'] is False for p in reports), 'session cleanup incomplete')
    require(row['sqlite']['pending'] == [], 'terminal durable pending intent')
    errors = [error for report in reports for error in report.get('errors', [])]
    fees = -sum((number(item['income']) for item in f['funding_ledger']
                 if item['incomeType'] == 'COMMISSION'), D(0))
    insurance = -sum((number(item['income']) for item in f['funding_ledger']
                      if item['incomeType'] == 'INSURANCE_CLEAR'), D(0))
    quantity = number(f['quantity_btc'])
    daily = daily_metrics(f)
    return {'head': HEADS[arm], 'receipt': receipt_identity,
            'source_sha256': row['source']['source_sha256'], 'producer_sha256': row['source']['producer_sha256'],
            'input_sha256': row['binding']['input_sha256'], 'risk_configuration': {
                key: row['strategy'][key] for key in ('capital_limit_usdt', 'max_stop_loss_fraction', 'stop_slippage_fraction')},
            'initial_cny': INITIAL, 'final_cny': number(f['final_cny']), 'final_usdt': number(f['final_usdt']),
            'total_return_pct': (number(f['final_cny']) / INITIAL - 1) * 100,
            'cagr_pct': cagr(f['final_cny']), 'path_mdd_proxy_pct': number(path_check['mdd_proxy']) * 100,
            'close_observation_mdd_proxy_pct': number(path_check['mdd_close_proxy']) * 100,
            'daily_equity': daily, 'net_commission_paid_usdt': fees, 'insurance_charge_usdt': insurance,
            'fees_including_insurance_usdt': number(f['fees']), 'net_funding_paid_usdt': number(f['funding']),
            'fills': len(f['trades']), 'filled_ordinary_orders': sum(number(order['executedQty']) > 0 for order in f['orders'].values()),
            'income_records': len(f['funding_ledger']), 'funding_events': checked['financial']['funding_events'],
            'end_position': {'quantity_btc': quantity, 'flat': quantity == 0, 'entry_usdt': number(f['entry']),
                             'mark_usdt': number(f['final_mark']), 'wallet_usdt': number(f['wallet_usdt']),
                             'margin_usdt': number(f['margin']), 'live_protections': checked['financial']['end_live_protections']},
            'cleanup': {'verified_sessions': len(reports), 'sessions': 795, 'terminal_pending_intents': 0,
                        'execution_unresolved_sessions': 0, 'reported_error_entries': len(errors),
                        'reports_with_errors': sum(bool(p.get('errors')) for p in reports),
                        'error_types': dict(Counter(str(error.get('error_type', 'unspecified')) for error in errors))},
            'path_evidence': {'points': path_check['points'], 'rolling_sha256': path_check['rolling_sha256'],
                              'trace_files': len(path_check['raw_trace_files']), 'hindsight_bounded': path_check['hindsight_bounded'],
                              'bounded_minutes': path_check['bounded_minutes'], 'limitation': path_check['limitation']}}


def summarize(previous, current, audit_path):
    checked = read(audit_path)
    require(checked['version'] == 'independent-financial-audit-v1'
            and checked['passed'] is True and checked['full795'] is True,
            'successful independent full795 audit required; smoke is not publishable economic evidence')
    require(checked['arm_difference_tolerance'] is None, 'arm differences must not use a tolerance')
    require(sha(Path(__file__).with_name('independent_financial_audit.py')) == checked['auditor_sha256'],
            'current auditor bytes differ from the passed audit')
    if 'detail' in checked:
        require(artifact(checked['detail']['path']) == checked['detail'], 'audit detail identity changed')
    with localcontext() as context:
        context.prec = 50
        arms = {'previous': load_arm(previous, 'previous', checked['main']),
                'current': load_arm(current, 'current', checked['candidate'])}
        before, after = arms['previous'], arms['current']
        require(before['producer_sha256'] == after['producer_sha256'], 'paired producer differs')
        fields = ('cagr_pct', 'path_mdd_proxy_pct', 'total_return_pct')
        delta = {field + '_delta_pp': after[field] - before[field]
                 if after[field] is not None and before[field] is not None else None for field in fields}
        delta['daily_mdd_delta_pp'] = (after['daily_equity']['full_period']['mdd_pct']
                                       - before['daily_equity']['full_period']['mdd_pct'])
        delta['final_cny_difference'] = after['final_cny'] - before['final_cny']
        calibration = {'historical_head': HEADS['previous'], 'historical_reported': dict(HISTORICAL),
                       'basis': 'Historical PR74 reported values versus the same runtime SHA under the newly registered producer; no inferred attribution.',
                       'numeric_differences_ignored': False, 'tolerance_applied': None}
        for field, reference in HISTORICAL.items():
            calibration[field + '_remeasured'] = before[field]
            calibration[field + '_delta_pp'] = before[field] - D(reference) if before[field] is not None else None
        result = {'version': 'coinquant-fixed-sha-results-v1', 'economic_results_ready': True,
                  'period': {'start_inclusive': '2020-01-01T00:00:00Z', 'end_exclusive': '2026-09-20T00:00:00Z',
                             'days': DAYS, 'year_days': YEAR_DAYS, 'cagr_exponent': YEAR_DAYS / D(DAYS),
                             'cagr_formula': '(final_cny / 10000) ** (365.2425 / 2454) - 1',
                             'daily_mdd_basis': 'Initial 10000 plus all 2454 UTC daily closing values; each calendar year starts with previous-year-end carried equity.'},
                  'audit': artifact(audit_path), 'auditor_sha256': checked['auditor_sha256'],
                  'summarizer': artifact(__file__), 'arms': arms, 'current_minus_previous': delta,
                  'historical_previous_calibration': calibration,
                  'notes': ['CAGR and returns use terminal CNY equity after the registered costs and FX conversions.',
                            'Funding paid is signed: positive is net expense, negative is net income.',
                            'Fills are execution records; filled ordinary orders are counted separately.',
                            '2026 is a partial calendar year; its period return is not annualized.',
                            'Daily-close MDD is calculated from financial.daily, not financial.mdd_close.',
                            'All source, cost, path and old-baseline differences remain visible; no causal attribution is inferred.']}
        return plain(result)


def display(value, places=4, signed=False):
    if value is None:
        return '不适用'
    value = number(value)
    result = f'{value:+,.{places}f}' if signed else f'{value:,.{places}f}'
    if signed and value and not value.quantize(D(1).scaleb(-places)):
        return f'{value:+.8E}'
    return result


def markdown(metrics):
    before, after = metrics['arms']['previous'], metrics['arms']['current']
    rows = [
        ('成本后 CAGR', display(before['cagr_pct']) + '%', display(after['cagr_pct']) + '%'),
        ('期末权益 / CNY', display(before['final_cny'], 2), display(after['final_cny'], 2)),
        ('全期日权益收益率', display(before['daily_equity']['full_period']['return_pct']) + '%', display(after['daily_equity']['full_period']['return_pct']) + '%'),
        ('原模拟路径 MDD 代理', display(before['path_mdd_proxy_pct']) + '%', display(after['path_mdd_proxy_pct']) + '%'),
        ('日收盘 MDD', display(before['daily_equity']['full_period']['mdd_pct']) + '%', display(after['daily_equity']['full_period']['mdd_pct']) + '%'),
        ('close 观测 MDD 代理', display(before['close_observation_mdd_proxy_pct']) + '%', display(after['close_observation_mdd_proxy_pct']) + '%'),
        ('净手续费 / USDT', display(before['net_commission_paid_usdt'], 2), display(after['net_commission_paid_usdt'], 2)),
        ('保险扣费 / USDT', display(before['insurance_charge_usdt'], 2), display(after['insurance_charge_usdt'], 2)),
        ('净支付资金费 / USDT', display(before['net_funding_paid_usdt'], 2), display(after['net_funding_paid_usdt'], 2)),
        ('成交记录 / 已成交普通订单', f"{before['fills']} / {before['filled_ordinary_orders']}", f"{after['fills']} / {after['filled_ordinary_orders']}"),
        ('期末有符号持仓 / BTC', display(before['end_position']['quantity_btc'], 8), display(after['end_position']['quantity_btc'], 8)),
        ('cleanup verified / 全部会话', '795 / 795', '795 / 795'),
        ('期末 pending / 未解决执行会话', '0 / 0', '0 / 0'),
        ('会话报告错误条目', str(before['cleanup']['reported_error_entries']), str(after['cleanup']['reported_error_entries'])),
    ]
    lines = ['# Coinquant 2.0.0 固定版本配对重测', '',
             f"previous `{HEADS['previous']}` → current `{HEADS['current']}`。",
             '两臂均完成原 795 次会话，独立账本审计及完整保留路径的重算审计通过。', '',
             '窗口为 2020-01-01 00:00 UTC 至 2026-09-20 00:00 UTC（终点排除），2454 天；初始资金 10,000 CNY。CAGR 使用 365.2425 天/年。', '',
             '| 指标 | previous，同 producer 重测 | current，2.0.0 |', '|---|---:|---:|']
    lines.extend(f'| {name} | {left} | {right} |' for name, left, right in rows)
    lines.extend(['', '## 分年日权益收益与回撤', '',
                  '沿同一复利账户路径计算；2020 年从 10,000 CNY 起算，后续每年包含上年末权益作为初始峰值。2026 年为截至 9 月 19 日日终的部分年度收益。', '',
                  '| 年度 | previous 收益率 | current 收益率 | previous 日收盘 MDD | current 日收盘 MDD |', '|---|---:|---:|---:|---:|'])
    for left, right in zip(before['daily_equity']['by_year'], after['daily_equity']['by_year'], strict=True):
        lines.append(f"| {left['year']} | {display(left['return_pct'])}% | {display(right['return_pct'])}% | {display(left['mdd_pct'])}% | {display(right['mdd_pct'])}% |")
    calibration = metrics['historical_previous_calibration']
    lines.extend(['', '## 历史 PR74 数字校准', '',
                  '以下单独比较旧发布记录与本次对同一 previous SHA 的重测。旧 producer 与本次 producer 的身份不作相同声明；差异完整保留，不据此推测原因。', '',
                  '| 指标 | 旧记录 | 本次 previous 重测 | 差值 / 百分点 |', '|---|---:|---:|---:|'])
    for field, label in (('cagr_pct', 'CAGR'), ('path_mdd_proxy_pct', '路径 MDD 代理')):
        lines.append(f"| {label} | {HISTORICAL[field]}% | {display(before[field], 10)}% | {display(calibration[field + '_delta_pp'], 10, True)} |")
    lines.extend(['', '净支付资金费为正表示净支出，为负表示净收入。日收盘回撤由 `financial.daily` 逐日重算；`mdd_close` 是原 close 观测代理，单独列示。', '',
                  '路径代理仍包含原 OHLC 极值先后、print/mark 代理及 hindsight 缺口界限。表格作展示舍入，metrics.json 保留未舍入值、审计身份和期末仓位细节。'])
    for name, arm in metrics['arms'].items():
        gap = number(arm['daily_equity']['terminal_vs_daily_equity_difference_cny'])
        if gap:
            lines.extend(['', f"{name} 期末估值与最后日终估值存在 {gap} CNY 差异；两项均保留，未用其中一项覆盖另一项。"])
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous', required=True, type=Path)
    parser.add_argument('--current', required=True, type=Path)
    parser.add_argument('--audit', required=True, type=Path, help='Passed independent audit detail or summary')
    parser.add_argument('--out', type=Path, default=Path(__file__).with_name('metrics.json'))
    parser.add_argument('--markdown', type=Path, default=Path(__file__).with_name('results-comparison.md'))
    args = parser.parse_args()
    try:
        require(args.out.resolve() != args.markdown.resolve(), 'output paths must be distinct')
        require(not args.out.exists() and not args.markdown.exists(), 'preserve existing result artifacts')
        result = summarize(args.previous, args.current, args.audit)
        rendered = markdown(result)
        for path in (args.out, args.markdown):
            path.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open('x', encoding='utf-8') as target:
            json.dump(result, target, ensure_ascii=False, indent=2, allow_nan=False)
            target.write('\n')
        with args.markdown.open('x', encoding='utf-8') as target:
            target.write(rendered)
        print(json.dumps({'metrics': artifact(args.out), 'markdown': artifact(args.markdown)}, ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError) as exc:
        print(f'No publishable summary: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
