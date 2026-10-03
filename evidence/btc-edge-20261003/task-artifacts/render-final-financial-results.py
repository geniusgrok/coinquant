"""Render the already reviewed final report; never invoke financial producers."""
import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--out-dir', required=True, type=Path)
    args = parser.parse_args()
    report_bytes = args.report.read_bytes()
    report = json.loads(report_bytes)
    if (report['status'] != 'complete_reviewed' or report['pending'] or
            report['blocking'] or report['rejected_files']):
        raise ValueError('Rendering requires the complete independently reviewed report')
    args.out_dir.mkdir(parents=True, exist_ok=False)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.ticker import PercentFormatter

    accounts = report['accounts']
    baseline = {'spot': 'atr-stop', 'perp': 'incumbent'}
    colors = {'spot': '#2874a6', 'perp': '#a65b21'}
    fields = ['account_id', 'project', 'candidate', 'scenario', 'initial_cny',
              'actual_risk_sizing', 'offset_ms', 'cagr', 'continuous_mdd_proxy',
              'daily_mdd', 'worst_day', 'daily_es99_loss', 'underwater_days',
              'usdt_beta', 'descriptive_usdt_alpha_annualized',
              'validation_usdt_beta', 'validation_usdt_vol_annualized',
              'validation_descriptive_alpha_annualized', 'fees_usdt',
              'funding_paid_usdt', 'raw_sha256']
    with (args.out_dir / 'account-metrics.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for key, account in sorted(accounts.items()):
            stats = account['metrics']
            daily = stats['metrics']
            regression = stats['usdt_btc_regression']
            validation = stats['validation_2022_plus']
            writer.writerow(dict(
                account_id=key, project=account['kind'], candidate=account['candidate'],
                scenario=account['scenario'], initial_cny=account['capital'],
                actual_risk_sizing=account['risk'], offset_ms=account['offset'],
                cagr=account['gate_inputs']['values']['cagr'],
                continuous_mdd_proxy=account['gate_inputs']['values']['mdd'],
                daily_mdd=daily['daily_mdd'], worst_day=daily['worst_day'],
                daily_es99_loss=daily['daily_es99_loss'],
                underwater_days=daily['longest_daily_underwater_days'],
                usdt_beta=regression.get('beta_btc'),
                descriptive_usdt_alpha_annualized=regression.get('residual_arithmetic_annualized'),
                validation_usdt_beta=validation['regression'].get('beta_btc'),
                validation_usdt_vol_annualized=validation['usdt']['daily_volatility_annualized'],
                validation_descriptive_alpha_annualized=validation['regression'].get('residual_arithmetic_annualized'),
                fees_usdt=stats['fees_usdt'], funding_paid_usdt=stats['funding_paid_usdt'],
                raw_sha256=account['raw_sha256']))

    def base_account(kind, name, risk=False):
        return accounts[f'{kind}|{name}|base|1E+4|0|{"risk" if risk else "unscaled"}']

    def dates(curve):
        return [datetime.fromtimestamp(p['day_ms'] / 1000, timezone.utc) for p in curve]

    figure, axes = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
    for column, kind in enumerate(baseline):
        names = list(dict.fromkeys([baseline[kind], report['selected'][kind]]))
        for index, name in enumerate(names):
            account = base_account(kind, name)
            curve = account['curve']
            axes[0, column].plot(dates(curve), [p['equity_cny'] for p in curve],
                                 label=name, linewidth=1.25, alpha=1 - index * .15)
        axes[0, column].set(title=f'{kind}: actual CNY10,000 funded accounts',
                            ylabel='Closing CNY equity (log scale)', yscale='log')
        axes[0, column].legend()
    for label, portfolios in report['portfolios'].items():
        portfolio = next(p for p in portfolios if p['neutral_reference'])
        curve = portfolio['curve']
        axes[1, 0].plot(dates(curve), [p['equity_cny'] for p in curve], label=label)
        peak = 10000
        drawdowns = []
        for point in curve:
            peak = max(peak, point['equity_cny'])
            drawdowns.append(point['equity_cny'] / peak - 1)
        axes[1, 1].plot(dates(curve), drawdowns, label=label)
    axes[1, 0].set(title='Fixed neutral pair: Spot5000 / Coin5000',
                   ylabel='Closing CNY equity (log scale)', yscale='log')
    axes[1, 1].set(title='Neutral pair: daily closing drawdown', ylabel='Daily drawdown')
    axes[1, 1].yaxis.set_major_formatter(PercentFormatter(1))
    for axis in axes.flat:
        axis.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        axis.grid(alpha=.2)
    for axis in axes[1]:
        axis.legend()
    figure.suptitle('BTC historical measured accounts | costs included | no added capital')
    figure.savefig(args.out_dir / 'funded-performance.png', dpi=180)
    figure.savefig(args.out_dir / 'funded-performance.svg')
    plt.close(figure)

    figure, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    for kind in baseline:
        candidates = [baseline[kind], *report['decisions'][kind]]
        for name in dict.fromkeys(candidates):
            unscaled = base_account(kind, name)
            sized = base_account(kind, name, risk=True)
            valid = sized['metrics']['validation_2022_plus']['regression']
            beta = valid.get('beta_btc')
            alpha = valid.get('residual_arithmetic_annualized')
            interval = valid.get('residual_arithmetic_annualized_normal95_descriptive')
            chosen = name == report['selected'][kind]
            marker = '*' if chosen else 'o'
            if beta is not None and alpha is not None:
                axes[0].scatter(beta, alpha, color=colors[kind], marker=marker,
                                 s=150 if chosen else 38)
                if interval:
                    axes[0].vlines(beta, interval[0], interval[1], color=colors[kind], alpha=.35)
                axes[0].annotate(f'{kind}/{name}', (beta, alpha), fontsize=7,
                                  xytext=(4, 4), textcoords='offset points')
            gate = unscaled['gate_inputs']['values']
            axes[1].scatter(float(gate['mdd']), gate['cagr'], color=colors[kind],
                             marker=marker, s=150 if chosen else 38)
            axes[1].annotate(f'{kind}/{name}', (float(gate['mdd']), gate['cagr']),
                              fontsize=7, xytext=(4, 4), textcoords='offset points')
    axes[0].set(title='Actual risk sizing: 2022+ USDT attribution', xlabel='BTC beta',
                ylabel='Descriptive annualized arithmetic intercept')
    axes[0].axhline(0, color='grey', linewidth=.7)
    axes[1].set(title='Unscaled actual accounts: cost-net return and risk',
                xlabel='Continuous MDD proxy', ylabel='CNY CAGR')
    for axis in axes:
        axis.yaxis.set_major_formatter(PercentFormatter(1))
        axis.grid(alpha=.2)
    axes[1].xaxis.set_major_formatter(PercentFormatter(1))
    figure.suptitle('Historical selection is contaminated; native cases=0; prospective alpha unproven\n'
                    'Stars: declared selected defaults. Intervals: descriptive HAC7, no selection adjustment.', fontsize=10)
    figure.savefig(args.out_dir / 'alpha-beta-and-risk.png', dpi=180)
    figure.savefig(args.out_dir / 'alpha-beta-and-risk.svg')
    plt.close(figure)

    files = [dict(path=p.name, bytes=p.stat().st_size, sha256=sha256(p.read_bytes()).hexdigest())
             for p in sorted(args.out_dir.iterdir())]
    with (args.out_dir / 'render-manifest.json').open('x') as stream:
        json.dump(dict(format='btc-edge-final-render-v1',
                       report=dict(path=str(args.report), sha256=sha256(report_bytes).hexdigest()),
                       renderer_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                       arithmetic_metrics='Copied from independently reviewed final report; no new financial replay.',
                       plot_limitations='Closing daily curves; joint daily drawdown is not continuous joint MDD. '
                                        'Historical descriptive attribution is not proven prospective alpha. '
                                        'Continuous account MDD remains the original producer proxy.',
                       files=files), stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(out_dir=str(args.out_dir), files=len(files), new_financial_producers=0)))


if __name__ == '__main__':
    main()
