"""Export the two completed current-main wallets; never run a strategy or audit."""
import csv
from datetime import datetime, timezone
from decimal import Decimal as D
import gzip
import hashlib
import json
from pathlib import Path

TASK = Path('/workspace/btc-main-backtest-20261006')
START, END, DAY = 1577836800000, 1789862400000, 86400000
HEADS = {'coinquant': '47837e391be4130104967d794e9701068a0bcc5a',
         'spotquant': 'b81db17c31a4b1fed8d8fc3d63c9954053a66613'}
# Preserve the pre-existing meter conventions, before looking at the results.
YEAR_DAYS = {'coinquant': D('365.2425'), 'spotquant': D('365.25')}


def iso(stamp):
    return datetime.fromtimestamp(int(stamp) / 1000, timezone.utc).isoformat()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def read_completed(repo, filename):
    path = TASK / filename
    raw = path.read_bytes()
    packet = json.loads(gzip.decompress(raw))
    identity = packet['source'] if repo == 'coinquant' else packet['identity']
    actual_head = identity['git_head'] if repo == 'coinquant' else identity['runtime_head']
    money = packet['financial'] if repo == 'coinquant' else packet
    if (not packet['complete'] or packet['session_count'] != 795
            or actual_head != HEADS[repo] or not money['audit']['passed']):
        raise ValueError('Only the registered completed current-main wallet can be published')
    terminal = money['now_ms'] if repo == 'coinquant' else packet['actual_terminal_ms']
    if terminal != END:
        raise ValueError('Actual terminal differs from the registered exclusive endpoint')
    return packet, money, {'name': filename, 'sha256': hashlib.sha256(raw).hexdigest()}


def observed_rows(repo, money):
    rows = money['daily']
    if repo == 'coinquant':
        return [(int(r['stamp_ms']), r['equity_cny'], r['equity_usdt'],
                 r['wallet_usdt'], r['quantity_btc'], r['mark_usdt'],
                 r['gross_btc_exposure_usdt'], r['net_btc_exposure_usdt']) for r in rows]
    return [(int(r['timestamp_ms']), r['equity_cny'], r['equity_usdt'],
             r['cash_usdt'], r['btc'], r['price_usdt'],
             r['gross_notional_usdt'], r['net_notional_usdt'])
            for _, r in sorted(rows.items(), key=lambda item: int(item[0]))]


def export(repo, filename):
    packet, money, receipt = read_completed(repo, filename)
    folder = TASK / 'export' / repo
    folder.mkdir()  # Preserve an existing export instead of silently overwriting it.
    growth = D(money['final_cny']) / D(10000)
    years = D(END - START) / (YEAR_DAYS[repo] * DAY)
    cagr = float(growth) ** (1 / float(years)) - 1
    rows = observed_rows(repo, money)
    draws, peak = [], D(10000)
    for row in rows:
        peak = max(peak, D(row[1]))
        draws.append(D(1) - D(row[1]) / peak)
    summary = dict(project=repo, measured_runtime_head=HEADS[repo],
                   backtest_date='2026-10-06 Asia/Shanghai', complete=True,
                   window_utc={'begin': iso(START), 'end_exclusive': iso(END)},
                   initial_cny='10000', initial_usdt=packet['initial_usdt'],
                   final_cny=money['final_cny'], final_usdt=money['final_usdt'],
                   net_return_cny=str(growth - 1), cagr_cny=cagr,
                   cagr_year_days=str(YEAR_DAYS[repo]),
                   max_drawdown_cny_path_proxy=money['mdd'],
                   max_drawdown_cny_observed_daily=str(max(draws)),
                   observed_daily_rows=len(rows), first_observation_utc=iso(rows[0][0]),
                   last_observation_utc=iso(rows[-1][0]),
                   session_count=packet['session_count'], registered_session_count=795,
                   no_external_cash_flows=True, producer_financial_audit=money['audit'],
                   source_packet=receipt, actual_account_days=0,
                   native_execution_verified=False, prospective_alpha_proven=False)
    if repo == 'coinquant':
        summary.update(strategy='SX60 + DFII10; primary risk 7.5 / macro risk 3.6',
                       fills=len(money['trades']), fees_usdt=money['fees'],
                       funding_paid_usdt=money['funding'], final_quantity_btc=money['quantity_btc'],
                       max_drawdown_cny_close_proxy=money['mdd_close'],
                       wall_seconds=packet['cumulative_wall_seconds'],
                       source_identity=packet['source'], input_identity=packet['binding'],
                       execution_parameters=packet['strategy'],
                       costs={'fee_per_fill': '0.00075', 'fx_conversion_each_end': '0.001',
                              'funding': 'historical settlement events',
                              'quote_and_liquidity': 'one-level quote/depth proxy from trade prints and minute volume'},
                       path={'known': money['known_path'], 'hindsight_bounded': money['hindsight_bounded'],
                             'bounded_minutes': money['bounded_minutes']},
                       price_model='historical prints and minute mark/trade envelope; not observed order book or native fills')
    else:
        summary.update(strategy='SMA30 / 40 / 50 + ATR stop + crowding entry adjustment',
                       fills=len(money['fills']), fees_usdt=money['audit']['fees_usdt'],
                       funding_paid_usdt='0', final_quantity_btc=money['btc'],
                       wall_seconds=packet['wall_seconds'], source_identity=packet['identity'],
                       costs=packet['costs'], price_model=packet['price_model'])
    write_json(folder / 'summary.json', summary)
    with (folder / 'daily-equity.csv').open('w', newline='') as out:
        writer = csv.writer(out)
        writer.writerow(['observation_utc', 'timestamp_ms', 'equity_cny', 'equity_usdt',
                         'cash_or_wallet_usdt', 'quantity_btc', 'mark_or_price_usdt',
                         'gross_btc_exposure_usdt', 'net_btc_exposure_usdt',
                         'observed_daily_drawdown_cny'])
        for row, draw in zip(rows, draws):
            writer.writerow([iso(row[0]), *row, str(draw)])
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    dates = [datetime.fromtimestamp(r[0] / 1000, timezone.utc) for r in rows]
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True,
                             gridspec_kw={'height_ratios': [3, 1]})
    axes[0].plot(dates, [float(r[1]) for r in rows], linewidth=1.2, color='#126a87')
    axes[0].set_yscale('log')
    axes[0].axhline(10000, linewidth=.6, color='#888888', linestyle=':')
    axes[0].set_ylabel('Equity (CNY, log scale)')
    axes[0].set_title(f'{repo}: current runtime {HEADS[repo][:7]}')
    axes[1].fill_between(dates, [-100 * float(d) for d in draws], color='#b33d40', alpha=.8)
    axes[1].set_ylabel('Daily DD (%)')
    axes[1].set_xlabel('Actual observation time (UTC); daily marks, no interpolation')
    for ax in axes:
        ax.grid(alpha=.18)
    fig.tight_layout()
    fig.savefig(folder / 'equity.png', dpi=130)
    plt.close(fig)
    descriptions(repo, folder, summary)
    return {key: summary[key] for key in ('project', 'measured_runtime_head', 'final_cny',
             'cagr_cny', 'max_drawdown_cny_path_proxy', 'fills', 'wall_seconds')}


def descriptions(repo, folder, s):
    coin = repo == 'coinquant'
    limit = ('使用历史成交打印、分钟标记价格和交易价格包络。盘口深度、逐仓维持保证金及'
             '缺失标记价格的扩大区间仍为代理；缺口区间可能使用全窗口观测边界。'
             if coin else '使用日 OHLC，并按开盘→最高→最低→收盘线性构造日内价格路径；'
             '它不是实际日内成交序列。')
    costs = ('成交手续费为 0.075%，另计历史资金费；买卖报价与可成交深度来自单层代理。'
             if coin else '成交手续费为 0.1%，市价滑点 0.05%，止损滑点 0.1%。')
    md = f'''# 当前版本完整回测

2026-10-06（Asia/Shanghai）完成。测量运行代码为 [`{s['measured_runtime_head'][:7]}`](https://github.com/geniusgrok/{repo}/tree/{s['measured_runtime_head']})，策略为 **{s['strategy']}**。

| 指标 | 结果 |
|---|---:|
| 初始资金 | 10,000.00 元 |
| 期末人民币权益 | {float(s['final_cny']):,.2f} 元 |
| 累计净收益 | {100 * float(s['net_return_cny']):,.2f}% |
| 人民币年化净收益 | {100 * s['cagr_cny']:.2f}% |
| 人民币路径最大回撤代理 | {100 * float(s['max_drawdown_cny_path_proxy']):.2f}% |
| 日观测最大回撤 | {100 * float(s['max_drawdown_cny_observed_daily']):.2f}% |
| 实际模拟成交笔数 | {s['fills']:,} |
| 成交手续费 | {float(s['fees_usdt']):,.4f} USDT |
| 净支付资金费 | {float(s['funding_paid_usdt']):,.4f} USDT |
| 历史会话 | {s['session_count']} / 795 |

独立账户以 1 万元启动，不追加或提取资金；UTC 窗口为 **2020-01-01 00:00:00 至 2026-09-20 00:00:00，末端不含**。每次会话 300 秒、轮询 5 秒，读延迟 0.2 秒、写延迟 1 秒。最终持仓按末端价格估值，不为窗口结束强制造成交。始末换汇各扣 0.1%，汇率使用当时已可得的历史参考值；USD/USDT 按平价估值。{costs}

年化采用 `(期末人民币权益 / 10000) ** (1 / 年数) - 1`，每年 {s['cagr_year_days']} 天。人民币指标包含汇率变化。生产者已在完成时核对成交、费用与资金账本，结果通过；本报告直接导出该结果。

![当前回测权益和日观测回撤](backtest/equity.png)

图和 [日权益 CSV](backtest/daily-equity.csv) 保留生产者实际观测时间，不填补每日点或重构未记录的账户路径。图中的日观测回撤可能低于表中日内路径最大回撤代理。[机器可读结果](backtest/summary.json) 保留精确资金、测量源码、输入身份、成本和生产者账本核对结果。

{limit} 回测执行与保护成交均为历史模拟，不能证明交易所真实委托、重启或止损触发能力。该历史窗口曾用于策略开发，因此本结果不构成独立样本外 alpha 或未来收益证明；实际账户观察天数为 0。
'''
    (folder / 'BACKTEST.md').write_text(md)
    (folder / 'README-section.md').write_text(f'''## 当前完整回测

2026-10-06 对当前运行代码 `{s['measured_runtime_head'][:7]}` 完成独立 1 万元账户的完整回测（2020-01-01 至 2026-09-20 UTC，末端不含，795 会话，不追加资金）。期末人民币权益 **{float(s['final_cny']):,.2f} 元**，年化净收益 **{100 * s['cagr_cny']:.2f}%**，人民币路径最大回撤代理 **{100 * float(s['max_drawdown_cny_path_proxy']):.2f}%**。

结果已计入模拟成交成本和换汇成本；历史价格与执行使用代理，历史窗口曾用于开发，不证明实盘或样本外 alpha。详细口径、权益图及数据见 [BACKTEST.md](BACKTEST.md)。
''')


if __name__ == '__main__':
    results = [export('coinquant', 'coin-full.json.gz'),
               export('spotquant', 'spot-full-recovery.json.gz')]
    print(json.dumps(results, ensure_ascii=False, indent=2))
