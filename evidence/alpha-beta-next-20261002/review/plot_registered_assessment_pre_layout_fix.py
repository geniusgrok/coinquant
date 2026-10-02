"""Standalone figures from the completed registered assessment; no trading code."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--assessment', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    digest = hashlib.sha256(args.assessment.read_bytes()).hexdigest()
    report = json.loads(args.assessment.read_text())
    if report['registered_work_pending'] or report['native_cases'] != 0:
        raise ValueError('completed registered inventory with disclosed native-zero scope required')
    args.out.mkdir(parents=True, exist_ok=True)
    names = ['registered-risk-return', 'actual-validation-risk']
    outputs = [args.out / (name + suffix) for name in names for suffix in ('.png', '.svg')]
    if any(path.exists() for path in outputs) or (args.out / 'figure-provenance.json').exists():
        raise ValueError('never overwrite retained figures')
    plt.rcParams.update({'svg.hashsalt': digest, 'svg.fonttype': 'none', 'font.size': 10})
    palette = {}
    for kind in ('spot', 'perp'):
        baseline = 'consensus' if kind == 'spot' else 'incumbent'
        order = list(report['selection'][kind]['decisions'])
        palette[kind] = {name: '#172b4d' if name == baseline else plt.get_cmap('tab10')(i % 10)
                         for i, name in enumerate(order)}

    def save(fig, name):
        fig.savefig(args.out / (name + '.png'), dpi=180)
        fig.savefig(args.out / (name + '.svg'), metadata={'Date': None})
        plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(13, 6), constrained_layout=True)
    for ax, kind, title in zip(axes, ('spot', 'perp'), ('BTC spot', 'BTC perpetual')):
        baseline = 'consensus' if kind == 'spot' else 'incumbent'
        rejected = []
        for key, account in report['accounts'].items():
            if not key.startswith(kind + '/') or '/risk/' in key or account['scenario'] != 'base':
                continue
            if not account['valid']:
                rejected.append(account['candidate'])
                continue
            name = account['candidate']
            ax.scatter(account['mdd'] * 100, account['cagr'] * 100,
                       marker='s' if name == baseline else 'o', s=75 if name == baseline else 42,
                       color=palette[kind][name], label=name)
        target_mdd, target_cagr = (30, 100) if kind == 'spot' else (50, 150)
        ax.axvline(target_mdd, color='#a24832', linestyle='--', linewidth=1)
        ax.axhline(target_cagr, color='#a24832', linestyle='--', linewidth=1)
        ax.set(title=title, xlabel='Continuous proxy account MDD (%)', ylabel='Cost-net CNY CAGR (%)')
        ax.grid(alpha=.2)
        ax.legend(loc='upper center', bbox_to_anchor=(.5, -.17), ncol=2, fontsize=8,
                  frameon=False)
        if rejected:
            ax.text(.02, .02, 'Invalid accounts omitted: ' + ', '.join(rejected),
                    transform=ax.transAxes, fontsize=7, wrap=True)
    fig.suptitle('Registered base accounts; dashed lines retain original targets\n'
                 'Historical proxies, previously researched data; 2026 is partial', fontsize=13)
    save(fig, names[0])

    fig, axes = plt.subplots(1, 2, figsize=(13, 6), constrained_layout=True)
    for ax, kind, title in zip(axes, ('spot', 'perp'), ('BTC spot', 'BTC perpetual')):
        baseline = 'consensus' if kind == 'spot' else 'incumbent'
        base = report['accounts'][kind + '/' + baseline + '/base']
        if not base['valid']:
            ax.text(.1, .5, 'Invalid baseline: no risk comparison', transform=ax.transAxes)
            continue
        validation = base['financial']['validation_2022_plus']
        beta = validation['regression']['beta_btc']
        vol = validation['usdt']['daily_volatility_annualized'] * 100
        if beta is None:
            ax.text(.1, .5, 'Baseline beta unidentifiable', transform=ax.transAxes)
            continue
        ax.scatter(beta, vol, marker='s', color='#172b4d', s=75, label=baseline)
        ax.axvline(beta + .02, color='#a24832', linestyle='--', linewidth=1)
        ax.axhline(vol * 1.05, color='#a24832', linestyle='--', linewidth=1)
        for key, account in report['accounts'].items():
            if not key.startswith(kind + '/risk/') or account['candidate'] == baseline or not account['valid']:
                continue
            values = account['financial']['validation_2022_plus']
            x = values['regression']['beta_btc']
            y = values['usdt']['daily_volatility_annualized'] * 100
            if x is None:
                continue
            matched = report['risk'][kind][account['candidate']].get('achieved_match', False)
            ax.scatter(x, y, marker='o' if matched else 'x', s=45,
                       color=palette[kind][account['candidate']], label=account['candidate'])
        ax.set(title=title, xlabel='Actual BTC beta (USDT daily returns)', ylabel='Actual annualized USDT volatility (%)')
        ax.grid(alpha=.2)
        ax.legend(loc='upper center', bbox_to_anchor=(.5, -.17), ncol=2, fontsize=8,
                  frameon=False)
    fig.suptitle('Actual rerun validation, 2022 through 2026-09-19\n'
                 'Circles meet both registered risk limits; crosses fail. No prospective-alpha claim.', fontsize=12)
    save(fig, names[1])
    provenance = {'assessment_sha256': digest, 'matplotlib_version': matplotlib.__version__,
                  'scope': 'Actual account metrics only; no derived/scaled account curves.',
                  'figures': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in outputs}}
    with (args.out / 'figure-provenance.json').open('x') as stream:
        json.dump(provenance, stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
