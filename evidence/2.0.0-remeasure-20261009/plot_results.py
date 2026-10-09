"""Plot only complete, audited paired replay results that exactly match metrics.

Example: python plot_results.py --metrics metrics.json --out-prefix equity-drawdown
Reads local final receipts and the standalone summarizer; never imports the
producer or accesses an account. No output is created for incomplete inputs.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import sys


HEADS = {'previous': '79a334b2d776be2dbe8756f3a616697f9403982e',
         'current': '162ee7138952925ffafbc9b68be7c754c0c0a6c3'}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def closing_series(points, initial):
    """Use the stated initial capital as the peak, then each actual daily close."""
    peak = initial
    equity, drawdown = [initial], [Decimal(0)]
    for point in points:
        value = Decimal(point['equity_cny'])
        require(value.is_finite() and value > 0, 'nonpositive/nonfinite equity cannot use a log axis')
        peak = max(peak, value)
        equity.append(value)
        drawdown.append((1 - value / peak) * 100)
    return equity, drawdown


def verified_inputs(metrics_path):
    here = Path(__file__).resolve().parent
    metrics_bytes = metrics_path.read_bytes()
    metrics = json.loads(metrics_bytes)
    require(metrics['version'] == 'coinquant-fixed-sha-results-v1'
            and metrics['economic_results_ready'] is True, 'publishable final metrics required')
    summary_path = here / 'summarize_results.py'
    module_spec = importlib.util.spec_from_file_location('standalone_replay_summary', summary_path)
    summary = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(summary)
    metrics_identity = summary.artifact(metrics_path)
    require(metrics_identity['sha256'] == hashlib.sha256(metrics_bytes).hexdigest()
            and metrics_identity['bytes'] == len(metrics_bytes), 'metrics changed while being read')
    require(summary.HEADS == HEADS and set(metrics['arms']) == set(HEADS), 'specified paired runtime commits required')
    require(summary.artifact(summary_path) == metrics['summarizer'], 'metrics were made by another summarizer')
    attempt = summary.read(here / 'ATTEMPTS.json')['second_attempt']
    spec = summary.read(here / 'spec.json')
    require(Path(attempt['root']).resolve() == here, 'second-attempt directory identity differs')
    require(summary.sha(here / 'spec.json') == attempt['spec_sha256']
            and summary.sha(here / 'PROTOCOL.md') == attempt['protocol_sha256'] == spec['protocol_sha256'],
            'registered attempt/spec/protocol identity differs')
    require(spec['runtime_heads'] == HEADS and spec['session_count'] == 795
            and spec['producer_sha256'] == attempt['producer_sha256']
            and spec['source_sha256_by_arm'] == attempt['source_sha256_by_arm'], 'registered paired source differs')
    for name, head in HEADS.items():
        arm = metrics['arms'][name]
        require(arm['head'] == head and arm['producer_sha256'] == spec['producer_sha256']
                and arm['source_sha256'] == spec['source_sha256_by_arm'][name], 'metrics refer to another ' + name + ' source')
    previous = Path(metrics['arms']['previous']['receipt']['path'])
    current = Path(metrics['arms']['current']['receipt']['path'])
    audit_path = Path(metrics['audit']['path'])
    # This rechecks 795 successful sessions, receipts, reports, audit/source
    # identities, the full window, and exact 50-digit Decimal calculations.
    recomputed = summary.summarize(previous, current, audit_path)
    require(recomputed == metrics, 'recomputed audited metrics differ; no tolerance or replacement is applied')
    series = {}
    with localcontext() as context:
        context.prec = 50
        for name, path in (('previous', previous), ('current', current)):
            arm = metrics['arms'][name]
            require(summary.artifact(path) == arm['receipt'], 'final receipt changed before plotting')
            receipt = summary.read(path)
            financial = receipt['financial']
            daily = summary.daily_metrics(financial)
            require(summary.plain(daily) == arm['daily_equity'], 'daily metrics differ from receipt values')
            require(summary.cagr(financial['final_cny']) == summary.number(arm['cagr_pct']), 'CAGR differs from final metrics')
            # raw[0] is the post-conversion opening snapshot. The chart starts
            # at 10,000 CNY instead, followed by all 2,454 actual daily closes.
            points = financial['daily'][1:]
            equity, drawdown = closing_series(points, summary.INITIAL)
            require(max(drawdown) == summary.number(arm['daily_equity']['full_period']['mdd_pct']),
                    'plotted daily-close maximum drawdown differs from metrics')
            stamps = [summary.START, *(point['stamp_ms'] for point in points)]
            require(len(stamps) == 2455 and len(points) == 2454, 'complete daily series required')
            series[name] = {'timestamps': [datetime.fromtimestamp(stamp / 1000, timezone.utc) for stamp in stamps],
                            'equity': [float(value) for value in equity],
                            'drawdown': [-float(value) for value in drawdown]}
            require(all(math.isfinite(value) and value > 0 for value in series[name]['equity'])
                    and all(math.isfinite(value) for value in series[name]['drawdown']), 'values cannot be represented on the chart')
            require(summary.artifact(path) == arm['receipt'], 'final receipt changed while preparing plot')
    require(summary.artifact(metrics_path) == metrics_identity, 'metrics changed during verification')
    provenance = {'metrics': metrics_identity, 'summarizer': metrics['summarizer'],
                  'audit': metrics['audit'], 'receipts': {name: arm['receipt'] for name, arm in metrics['arms'].items()},
                  'runtime_heads': HEADS, 'producer_sha256': spec['producer_sha256'],
                  'spec_sha256': attempt['spec_sha256'], 'protocol_sha256': attempt['protocol_sha256'],
                  'plotter': summary.artifact(__file__), 'initial_capital_cny': '10000',
                  'daily_closes_per_arm': 2454, 'x_axis': 'UTC timestamp from stamp_ms',
                  'drawdown_basis': 'Initial 10000 plus financial.daily[1:] daily closing CNY equity; not financial.mdd_close or the intraday path proxy.',
                  'decimal_precision': 50, 'metrics_comparison': 'exact; no numeric tolerance'}
    return summary, metrics, series, provenance


def render(metrics, series, provenance):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.dates as dates
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter, PercentFormatter

    provenance['matplotlib_version'] = matplotlib.__version__
    description = json.dumps(provenance, sort_keys=True, ensure_ascii=True)
    title = 'Coinquant 2.0.0: paired replay of fixed commits'
    style = {'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.titlesize': 11,
             'axes.spines.top': False, 'axes.spines.right': False,
             'svg.fonttype': 'none', 'svg.hashsalt': provenance['metrics']['sha256']}
    with plt.rc_context(style):
        fig, (equity_ax, drawdown_ax) = plt.subplots(2, 1, figsize=(12, 8.5), sharex=True,
                                                   gridspec_kw={'height_ratios': [2.2, 1]})
        try:
            fig.subplots_adjust(left=0.105, right=0.97, top=0.80, bottom=0.18, hspace=0.12)
            handles, labels = [], []
            for name, color, linestyle, label in (
                    ('previous', '#666666', '--', 'Previous: 79a334b'),
                    ('current', '#087E8B', '-', 'Current: 162ee71 (2.0.0)')):
                arm, values = metrics['arms'][name], series[name]
                line, = equity_ax.plot(values['timestamps'], values['equity'], color=color,
                                       linewidth=1.65, linestyle=linestyle)
                drawdown_ax.plot(values['timestamps'], values['drawdown'], color=color,
                                 linewidth=1.2, linestyle=linestyle)
                drawdown_ax.fill_between(values['timestamps'], values['drawdown'], 0, color=color, alpha=0.08)
                handles.append(line)
                labels.append(f"{label}\nCAGR {Decimal(arm['cagr_pct']):.2f}% | Daily-close MDD {Decimal(arm['daily_equity']['full_period']['mdd_pct']):.2f}%")
            equity_ax.set_yscale('log')
            equity_ax.set_ylabel('CNY equity (log scale)', labelpad=10)
            equity_ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _position: f'{value:,.0f}'))
            equity_ax.grid(axis='y', which='major', color='#DDDDDD', linewidth=0.6)
            equity_ax.tick_params(axis='x', which='both', bottom=False)
            drawdown_ax.set_ylabel('Daily-close drawdown (%)', labelpad=10)
            drawdown_ax.yaxis.set_major_formatter(PercentFormatter(xmax=100, decimals=0))
            drawdown_ax.axhline(0, color='#777777', linewidth=0.6)
            drawdown_ax.grid(axis='y', color='#DDDDDD', linewidth=0.6)
            worst = min(min(values['drawdown']) for values in series.values())
            drawdown_ax.set_ylim(min(-1, worst * 1.10), 1)
            drawdown_ax.set_xlim(series['previous']['timestamps'][0], series['previous']['timestamps'][-1])
            drawdown_ax.xaxis.set_major_locator(dates.YearLocator(tz=timezone.utc))
            drawdown_ax.xaxis.set_major_formatter(dates.DateFormatter('%Y', tz=timezone.utc))
            drawdown_ax.set_xlabel('UTC closing boundary', labelpad=9)
            fig.suptitle(title, x=0.105, y=0.965, ha='left', fontsize=17, fontweight='semibold')
            fig.text(0.105, 0.918, '2020-01-01 to 2026-09-20 UTC (end exclusive) | 795 sessions per arm | Initial CNY 10,000', color='#444444')
            fig.legend(handles, labels, loc='upper left', bbox_to_anchor=(0.098, 0.894),
                       ncol=2, frameon=False, fontsize=9.5, columnspacing=3.5)
            fig.text(0.105, 0.096, 'Equity: initial capital plus 2,454 actual daily closes. The post-conversion opening snapshot is excluded.', fontsize=8.5, color='#444444')
            fig.text(0.105, 0.068, 'Drawdown uses daily closing CNY equity and the initial peak of CNY 10,000; the intraday path proxy is not plotted.', fontsize=8.5, color='#444444')
            fig.text(0.105, 0.039, f"Metrics SHA256: {provenance['metrics']['sha256'][:16]} | Producer SHA256: {provenance['producer_sha256'][:16]}", fontsize=8, color='#666666')
            outputs = {}
            for extension in ('png', 'svg'):
                metadata = {'Title': title, 'Description': description}
                metadata.update({'Software': f'Matplotlib {matplotlib.__version__}'} if extension == 'png'
                                else {'Creator': f'Matplotlib {matplotlib.__version__}', 'Date': None})
                target = io.BytesIO()
                fig.savefig(target, format=extension, dpi=180, facecolor='white', metadata=metadata)
                outputs[extension] = target.getvalue()
            return outputs
        finally:
            plt.close(fig)


def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metrics', type=Path, default=here / 'metrics.json')
    parser.add_argument('--out-prefix', type=Path, default=here / 'equity-drawdown')
    args = parser.parse_args()
    try:
        destinations = {extension: Path(str(args.out_prefix.resolve()) + '.' + extension) for extension in ('png', 'svg')}
        require(not any(path.exists() for path in destinations.values()), 'preserve existing chart artifacts')
        summary, metrics, series, provenance = verified_inputs(args.metrics.resolve())
        outputs = render(metrics, series, provenance)
        require(summary.artifact(args.metrics) == provenance['metrics'], 'metrics changed while rendering')
        for extension, path in destinations.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as target:
                target.write(outputs[extension])
                target.flush()
                os.fsync(target.fileno())
        print(json.dumps({'passed': True, 'provenance': provenance,
                          'artifacts': [summary.artifact(path) for path in destinations.values()]}, ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError, ImportError) as exc:
        print(f'No verified plot: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
