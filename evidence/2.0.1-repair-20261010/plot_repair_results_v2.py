"""Plot the preserved 2x2 arms plus combined-v3; never replay an account.

    python plot_repair_results_v2.py --results FINAL_RESULTS.json --out-dir figures-v3

FINAL_RESULTS.json contains daily summaries, so all five full receipts are required.
By default their paths come from FINAL_RESULTS.json. To use relocated identical files:

    --receipt control_2_0_0 /path/to/full-control.json.gz
    --receipt margin-only /path/to/full-margin.json.gz
    --receipt book-v2-only /path/to/full-book.json.gz
    --receipt combined-v2 /path/to/full-combined.json.gz
    --receipt combined-v3 /path/to/full-combined-v3.json.gz

Receipt SHA-256 and byte size must match FINAL_RESULTS.json. Curves use initial CNY
10,000 plus financial.daily[1:], never an intraday path or mdd_close proxy.
Missing/partial/mismatched input fails before any chart is written. Existing
outputs are preserved. This script requires only local files and matplotlib.
The explicit invalid combined-v3 head must be replaced after public freezing.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal as D, localcontext
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
START, END, DAY, DAYS = 1577836800000, 1789862400000, 86400000, 2454
INITIAL, YEAR_DAYS = D('10000'), D('365.2425')
HEADS = {
    'control_2_0_0': '162ee7138952925ffafbc9b68be7c754c0c0a6c3',
    'margin-only': '06206ac0c5383fb009df8bac20601cd9e2d9b004',
    'book-v2-only': '37bfc8a833d1ff3c0992842ce363758a47b1d06f',
    'combined-v2': '3561728dab351d269b19b107fb4fbabb2ac1f674',
    'combined-v3': '230a61daade55d7d80de56f61aae24e660fb3a40',
}
FACTORIAL_CASES = ('margin-only', 'book-v2-only', 'combined-v2')
INCREMENTAL_BASE = {
    'case': 'combined-v2',
    'head': '3561728dab351d269b19b107fb4fbabb2ac1f674',
    'spec_sha256': 'd0937a2415e464cdeae3ec0749affc11f2345269edff5e355c6edae8eef9060b',
    'receipt_sha256': '6b1fe9dd901e933928e4148df614ff67ad94a3910fa502dfe41a17047846fc0b',
}
FROZEN_BUFFER_AMENDMENT_SHA = '040729b29351abcf2a87244ba66f385eefbb2db33c5601cd80a31198d0bba9f4'
STYLES = {
    'control_2_0_0': ('2.0.0 control', '#596574', '--', 1.5),
    'margin-only': ('Margin sizing only', '#0072B2', '-', 1.5),
    'book-v2-only': ('Order-book guard v2 only', '#D55E00', '-.', 1.5),
    'combined-v2': ('Combined repair v2', '#009E73', '-', 1.7),
    'combined-v3': ('Combined v3: frozen buffer preserved', '#CC79A7', '-', 2.4),
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def number(value):
    result = D(value)
    require(result.is_finite(), 'nonfinite financial value')
    return result


def identity(path, raw=None):
    path = Path(path).resolve()
    if raw is None:
        raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def load_receipt(path, expected):
    raw = path.read_bytes()
    actual = identity(path, raw)
    require(all(actual[key] == expected[key] for key in ('bytes', 'sha256')),
            'full receipt bytes differ from FINAL_RESULTS.json: ' + str(path))
    decoded = gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw
    return json.loads(decoded), actual


def daily_series(receipt, arm):
    """Independently recompute the daily curve before converting to floats."""
    financial = receipt['financial']
    raw = financial['daily']
    require(len(raw) == DAYS + 1
            and [point['stamp_ms'] for point in raw] == list(range(START, END + DAY, DAY)),
            'complete ordered 2,455-boundary daily series required; no imputation')
    for point in raw:
        date = datetime.fromtimestamp((point['stamp_ms'] - 1) / 1000, timezone.utc).date().isoformat()
        require(point['date'] == date, 'daily UTC date does not match its closing boundary')
        require(number(point['equity_cny']) > 0, 'nonpositive equity cannot use the requested log axis')
    daily = arm['daily_equity']
    whole = daily['full_period']
    require(daily['missing_values_imputed'] == 0
            and number(daily['opening_post_conversion_cny']) == number(raw[0]['equity_cny'])
            and whole['start_date'] == '2020-01-01' and whole['end_date'] == '2026-09-19'
            and whole['days'] == DAYS and number(whole['opening_equity_cny']) == INITIAL,
            'RESULTS.json uses another daily-boundary convention')

    peak = INITIAL
    equity, drawdown = [INITIAL], [D(0)]
    for point in raw[1:]:
        value = number(point['equity_cny'])
        peak = max(peak, value)
        equity.append(value)
        drawdown.append((1 - value / peak) * 100)
    final = number(financial['final_cny'])
    require(equity[-1] == final == number(arm['final_cny']) == number(whole['ending_equity_cny']),
            'daily ending equity differs from the cost-adjusted terminal result')
    require(max(drawdown) == number(whole['mdd_pct']),
            'recomputed daily-close MDD differs from RESULTS.json')
    require((final / INITIAL - 1) * 100 == number(whole['return_pct'])
            and number(daily['terminal_vs_daily_equity_difference_cny']) == 0,
            'daily return or terminal boundary differs')
    require(((final / INITIAL) ** (YEAR_DAYS / D(DAYS)) - 1) * 100 == number(arm['cagr_pct']),
            'cost-adjusted terminal CAGR differs from RESULTS.json')

    # Each year carries the previous year's closing equity, including 2026's
    # partial year. This also checks the summaries against the plotted points.
    carry = INITIAL
    require([row['year'] for row in daily['by_year']] == list(range(2020, 2027)),
            'complete seven-row annual summaries required')
    for annual in daily['by_year']:
        points = [p for p in raw[1:] if p['date'].startswith(str(annual['year']) + '-')]
        high, maximum = carry, D(0)
        for point in points:
            value = number(point['equity_cny'])
            high = max(high, value)
            maximum = max(maximum, (1 - value / high) * 100)
        ending = number(points[-1]['equity_cny'])
        require(annual['days'] == len(points)
                and annual['start_date'] == points[0]['date'] and annual['end_date'] == points[-1]['date']
                and number(annual['opening_equity_cny']) == carry
                and number(annual['ending_equity_cny']) == ending
                and number(annual['return_pct']) == (ending / carry - 1) * 100
                and number(annual['mdd_pct']) == maximum, 'annual summary differs from plotted daily values')
        carry = ending

    values = {'timestamps': [datetime.fromtimestamp(p['stamp_ms'] / 1000, timezone.utc) for p in raw],
              'equity': [float(value) for value in equity],
              'drawdown': [-float(value) for value in drawdown]}
    require(all(math.isfinite(v) and v > 0 for v in values['equity'])
            and all(math.isfinite(v) for v in values['drawdown']), 'plot values are outside finite floating-point range')
    return values


def verified_inputs(results_path, overrides):
    for name, head in HEADS.items():
        require(len(head) == 40 and all(char in '0123456789abcdef' for char in head),
                'runtime head is not frozen; replace the explicit placeholder for ' + name)
    raw = results_path.read_bytes()
    result = json.loads(raw)
    require(result['version'] == 'coinquant-repair-results-v2'
            and result['all_three_registered_repairs_present'] is True
            and result['all_four_registered_repairs_present'] is True
            and result['factorial_cases'] == list(FACTORIAL_CASES)
            and set(result['cases']) == set(HEADS) - {'control_2_0_0'}
            and set(result['accepted_full_window_cases']) == set(HEADS)
            and result['baseline_calibration']['passed'] is True,
            'complete audited FINAL_RESULTS.json with all four registered repairs required')
    require(result['qualification']['offline_simulation'] is True
            and result['qualification']['native_execution_verified'] is False,
            'expected historical simulation qualification')
    require(result['period']['start_inclusive'] == '2020-01-01T00:00:00Z'
            and result['period']['end_exclusive'] == '2026-09-20T00:00:00Z'
            and result['period']['days'] == DAYS and number(result['period']['year_days']) == YEAR_DAYS,
            'fixed 2,454-day measurement window required')
    require(set(overrides) <= set(HEADS), 'unknown --receipt arm')
    arms = {'control_2_0_0': result['control_2_0_0'], **result['cases']}
    before, after = arms['combined-v2'], arms['combined-v3']
    increment = result['incremental_comparisons']['combined-v3_minus_combined-v2']
    require({'case':'combined-v2', 'head':before['head'],
             'spec_sha256':before['specification']['sha256'],
             'receipt_sha256':before['receipt']['sha256']} == INCREMENTAL_BASE
            == after['incremental_base'] == increment['incremental_base'],
            'final v3 result names another incremental base')
    require(increment['before_case'] == 'combined-v2' and increment['after_case'] == 'combined-v3'
            and increment['before_receipt'] == before['receipt']
            and increment['after_receipt'] == after['receipt']
            and increment['control_receipt'] == arms['control_2_0_0']['receipt']
            and increment['audits_against_control'] == {'combined-v2':before['audit'], 'combined-v3':after['audit']}
            and increment['amendment'] == after['frozen_buffer_amendment']
            and increment['amendment']['sha256'] == FROZEN_BUFFER_AMENDMENT_SHA,
            'incremental result identity or frozen-buffer amendment differs')
    require(before['normalized_economic_input_sha256'] == after['normalized_economic_input_sha256']
            == arms['control_2_0_0']['normalized_economic_input_sha256']
            == increment['normalized_economic_input_sha256']
            and before['strategy_sha256'] == after['strategy_sha256']
            == arms['control_2_0_0']['strategy_sha256'] == increment['strategy_sha256'],
            'incremental results do not share the audited control input and strategy identity')
    series, receipts = {}, {}
    common_inputs, common_strategy = None, None
    with localcontext() as context:
        context.prec = 50
        for name, head in HEADS.items():
            arm = arms[name]
            path = Path(overrides.get(name, arm['receipt']['path']))
            if not path.is_absolute():
                path = results_path.parent / path
            row, receipt_identity = load_receipt(path.resolve(), arm['receipt'])
            require(arm['head'] == row['source']['git_head'] == head, 'unexpected measured source head: ' + name)
            require(row['complete'] is True and row['original_window_complete'] is True
                    and row['failure'] is None and row['session_count'] == 795
                    and row['scope'] == {'kind': 'original-full', 'planned_sessions': 795}
                    and row['no_live_account'] is True and row['native_verified'] is False,
                    'successful original full795 offline receipt required: ' + name)
            require(row['at_ms'] == row['terminal_ms'] == row['financial']['now_ms'] == END
                    and row['inputs']['starts_ms'][0] == START
                    and number(row['initial_cny']) == number(arm['initial_cny']) == INITIAL,
                    'receipt measurement window or initial capital differs: ' + name)
            require(all(row['source'][field] == arm[field] for field in ('source_sha256', 'producer_sha256'))
                    and row['binding']['input_sha256'] == arm['input_sha256']
                    and row['binding']['strategy_sha256'] == arm['strategy_sha256'],
                    'receipt identity binding differs: ' + name)
            economic_inputs = {key:value for key,value in row['inputs'].items() if key != 'specification_sha256'}
            if common_inputs is None:
                common_inputs, common_strategy = economic_inputs, row['strategy']
            require(economic_inputs == common_inputs and row['strategy'] == common_strategy,
                    'plotted arms differ in economic inputs or strategy: ' + name)
            require(row['financial']['audit']['passed'] is True
                    and arm['path_evidence']['passed'] is True
                    and arm['path_evidence']['rolling_digest_recomputed'] is True
                    and arm['cleanup']['verified_sessions'] == 795
                    and arm['cleanup']['terminal_pending_intents'] == 0
                    and arm['cleanup']['execution_unresolved_sessions'] == 0,
                    'FINAL_RESULTS.json does not record completed audited evidence: ' + name)
            require(arm['risk_configuration'] == arms['control_2_0_0']['risk_configuration'],
                    'repair risk registration differs from the control')
            series[name] = daily_series(row, arm)
            receipts[name] = receipt_identity
    provenance = {'version': 'coinquant-repair-daily-charts-v2', 'results': identity(results_path, raw),
                  'receipts': receipts, 'heads': HEADS, 'plotter': identity(__file__),
                  'factorial_cases':list(FACTORIAL_CASES), 'incremental_comparison':increment,
                  'initial_capital_cny': '10000', 'daily_closes_per_arm': DAYS,
                  'decimal_precision': 50, 'daily_metric_comparison': 'exact; no tolerance',
                  'drawdown_basis': 'Initial 10000 plus financial.daily[1:] CNY closes; intraday path and mdd_close proxies are not plotted.',
                  'excluded_opening_snapshot': 'financial.daily[0] is the post-conversion opening boundary labeled 2019-12-31, not an extra closing day.',
                  'audit_scope': 'Receipt identity and full-result qualification verified against audited FINAL_RESULTS.json; daily curves, annual summaries, CAGR and daily MDD independently recomputed. Economic inputs and strategy match across the five receipts; v3-minus-v2 uses their full audits against the common 2.0.0 control. No replay or new full financial/path audit.'}
    return arms, series, provenance


def render(arms, series, provenance):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.dates as dates
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter, LogLocator, PercentFormatter

    provenance['matplotlib_version'] = matplotlib.__version__
    description = json.dumps(provenance, sort_keys=True, ensure_ascii=True)
    style = {'font.family': 'DejaVu Sans', 'font.size': 10,
             'axes.spines.top': False, 'axes.spines.right': False,
             'axes.edgecolor': '#75818C', 'axes.labelcolor': '#24333F',
             'xtick.color': '#465663', 'ytick.color': '#465663',
             'svg.fonttype': 'none', 'svg.hashsalt': provenance['results']['sha256']}
    outputs = {}
    with plt.rc_context(style):
        for kind in ('equity', 'drawdown'):
            title = 'Coinquant: equity after costs' if kind == 'equity' else 'Coinquant: daily-close drawdown'
            fig, ax = plt.subplots(figsize=(13.5, 8.0))
            try:
                fig.subplots_adjust(left=0.105, right=0.97, top=0.70, bottom=0.19)
                handles, labels = [], []
                for name, (label, color, linestyle, width) in STYLES.items():
                    values, arm = series[name], arms[name]
                    line, = ax.plot(values['timestamps'], values[kind], color=color,
                                    linestyle=linestyle, linewidth=width)
                    handles.append(line)
                    labels.append((f"{label}  |  CAGR {D(arm['cagr_pct']):.2f}%  |  CNY {D(arm['final_cny']):,.0f}")
                                  if kind == 'equity' else
                                  f"{label}  |  Daily-close MDD {D(arm['daily_equity']['full_period']['mdd_pct']):.2f}%")
                if kind == 'equity':
                    ax.set_yscale('log')
                    ax.set_ylabel('CNY equity (log scale)', labelpad=10)
                    ax.yaxis.set_major_locator(LogLocator(base=10, subs=(1.0, 2.0, 5.0), numticks=9))
                    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, position: f'{value:,.0f}'))
                    ax.axhline(10000, color='#B4BCC2', linewidth=0.7, linestyle=':', zorder=0)
                else:
                    ax.set_ylabel('Drawdown from prior daily high', labelpad=10)
                    ax.yaxis.set_major_formatter(PercentFormatter(xmax=100, decimals=0))
                    worst = max(-min(values['drawdown']) for values in series.values())
                    ax.set_ylim(-max(5, math.ceil(worst / 5) * 5), 1)
                    ax.axhline(0, color='#75818C', linewidth=0.7)
                    values = series['combined-v3']
                    ax.fill_between(values['timestamps'], values['drawdown'], 0, color=STYLES['combined-v3'][1], alpha=0.06)
                ax.grid(axis='y', which='major', color='#DFE4E8', linewidth=0.65)
                ax.set_axisbelow(True)
                stamps = series['control_2_0_0']['timestamps']
                ax.set_xlim(stamps[0], stamps[-1])
                ax.xaxis.set_major_locator(dates.YearLocator(tz=timezone.utc))
                ax.xaxis.set_major_formatter(dates.DateFormatter('%Y', tz=timezone.utc))
                ax.set_xlabel('UTC daily closing boundary', labelpad=9)
                fig.suptitle(title, x=0.105, y=0.965, ha='left', fontsize=19, fontweight='semibold', color='#182A35')
                fig.text(0.105, 0.914, '2020-01-01 to 2026-09-20 UTC (end exclusive)  |  Initial CNY 10,000  |  795 sessions per arm', color='#465663')
                fig.legend(handles, labels, loc='upper left', bbox_to_anchor=(0.099, 0.877),
                           ncol=2, frameon=False, fontsize=9.5, columnspacing=2.3, handlelength=3)
                fig.text(0.105, 0.135, 'Original 2x2 retains combined v2. Combined v3 adds the later registered frozen-buffer fix.', fontsize=8.5, color='#465663')
                fig.text(0.105, 0.107, 'Includes trading fees, funding and entry/exit FX costs. Curves use initial capital plus 2,454 daily closes.', fontsize=8.5, color='#465663')
                fig.text(0.105, 0.079, 'Daily-close drawdown is recomputed from the plotted equity; intraday path proxies are not shown. 2026 is a partial year.', fontsize=8.5, color='#465663')
                fig.text(0.105, 0.051, 'Historical simulation; exchange-native execution and out-of-sample performance are not claimed.', fontsize=8.5, color='#465663')
                fig.text(0.105, 0.025, 'FINAL_RESULTS SHA-256: ' + provenance['results']['sha256'][:24] + '  |  Full receipt identities embedded in PNG / SVG metadata', fontsize=8, color='#687884')
                for extension in ('png', 'svg'):
                    metadata = {'Title': title, 'Description': description}
                    metadata.update({'Software': f'Matplotlib {matplotlib.__version__}'} if extension == 'png'
                                    else {'Creator': f'Matplotlib {matplotlib.__version__}', 'Date': None})
                    target = io.BytesIO()
                    fig.savefig(target, format=extension, dpi=180, facecolor='white', metadata=metadata)
                    outputs[f'repair-{kind}-daily.{extension}'] = target.getvalue()
            finally:
                plt.close(fig)
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--results', type=Path, default=HERE / 'FINAL_RESULTS.json')
    parser.add_argument('--out-dir', type=Path, default=HERE / 'figures-v3')
    parser.add_argument('--receipt', action='append', nargs=2, default=[], metavar=('ARM', 'PATH'))
    args = parser.parse_args()
    try:
        overrides = dict(args.receipt)
        require(len(overrides) == len(args.receipt), 'duplicate --receipt override')
        names = [f'repair-{kind}-daily.{extension}' for kind in ('equity', 'drawdown') for extension in ('png', 'svg')]
        names.append('repair-charts-validation.json')
        require(not any((args.out_dir / name).exists() for name in names), 'preserve existing chart artifacts')
        arms, series, provenance = verified_inputs(args.results.resolve(), overrides)
        outputs = render(arms, series, provenance)
        require(identity(args.results) == provenance['results'], 'FINAL_RESULTS.json changed during plotting')
        require(all(identity(ref['path']) == ref for ref in provenance['receipts'].values()),
                'receipt changed during plotting')
        verification = {'passed': True, 'provenance': provenance,
                        'artifacts': [identity(args.out_dir / name, raw) for name, raw in outputs.items()]}
        outputs['repair-charts-validation.json'] = (json.dumps(verification, ensure_ascii=False, indent=2) + '\n').encode()
        args.out_dir.mkdir(parents=True, exist_ok=True)
        for name, raw in outputs.items():
            with (args.out_dir / name).open('xb') as stream:
                stream.write(raw)
        print(json.dumps({'passed': True, 'artifacts': [identity(args.out_dir / name) for name in outputs]}, ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError, ImportError) as exc:
        print(f'No verified repair charts: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
