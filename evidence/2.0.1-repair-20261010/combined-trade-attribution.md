# 组合修复版完整回放：交易与年度归因

组合 `3561728` 与封存 2.0.0 均为完整 795 会话。脚本先通过登记、公有 head 身份、spec、完整独立审计及原基线逐值校准，再读取账本；没有启动回放或账户操作。公开 URL 的登记身份由脚本核对，在线公开来源由主控另行验证。

## 总体结果

| 指标 | 2.0.0 控制组 | 组合 v2 |
|---|---:|---:|
| CNY 年化收益率 % | 27.6263502252 | 31.1572597593 |
| 路径最大回撤代理 % | 15.1634397848 | 16.7574317368 |
| 日末最大回撤 % | 12.1153946429 | 12.8548458608 |
| 期末 CNY | 51,498.4956 | 61,862.2825 |
| 期末 USDT | 7,696.79372997 | 9,245.73081133 |
| 闭合持仓组 | 44 | 49 |
| 有成交普通订单 | 93 | 104 |
| 逐笔 fills | 142 | 174 |
| 中位持仓天数 | 4.458823 | 4.541525 |
| 跨日末持仓边界数 | 241 | 275 |
| 手续费 USDT | 257.22685435 | 410.41983544 |
| 净支付资金费 USDT | 282.66349837 | 474.44776590 |

组合期末多 1,548.93708137 USDT：毛已实现收益多 1,893.91433000，扣除新增手续费 153.19298110 和净资金费 191.78426753。年化提高 3.5309095341 个百分点；日末回撤增加 0.7394512179 个百分点。两臂期末均空仓，全部闭合持仓净损益与钱包变化残差小于 1e-8 USDT。

## 逐年收益及账本贡献

| 年份 | 控制 CNY 收益 % | 组合 CNY 收益 % | 控制当年 USDT 增减 | 组合当年 USDT 增减 | 组合减控制 USDT |
|---|---:|---:|---:|---:|---:|
| 2020 | 28.762877 | 87.839727 | 536.449794 | 1,440.974032 | +904.524238 |
| 2021 | 23.987333 | 23.261963 | 544.248348 | 772.480776 | +228.232429 |
| 2022 | 8.830040 | 2.841133 | 5.331246 | -193.469827 | -198.801074 |
| 2023 | 126.498181 | 121.299988 | 3,023.379576 | 3,969.036725 | +945.657149 |
| 2024 | 35.029572 | 34.112972 | 1,742.705976 | 2,267.262129 | +524.556153 |
| 2025 | -4.066950 | -1.809377 | 1.599896 | 230.241666 | +228.641770 |
| 2026（部分年度） | 1.021985 | -10.850202 | 408.043342 | -675.830242 | -1,083.873584 |

年度 USDT 贡献包括当年已实现盈亏、佣金、资金费及未实现盈亏变化；并非把跨年持仓全部记入平仓年。每年同时核对收入账本、持仓组贡献、日末权益。CNY 年度收益还受汇率与换汇成本影响，不能直接用 USDT 增减替代。2026 数据截至 9 月 19 日。

## 四个原短持仓日期

| 首次成交日 | 控制持仓秒 | 组合持仓天 | 控制净 USDT | 组合净 USDT | 同日持仓净差 USDT |
|---|---:|---:|---:|---:|---:|
| 2020-01-03 | 192.842 | 11.042149 | -8.266669 | 425.266183 | +433.532852 |
| 2020-07-21 | 219.969 | 5.336847 | -10.252874 | 233.722912 | +243.975786 |
| 2020-08-06 | 91.606 | 7.417154 | -0.585972 | -7.563345 | -6.977372 |
| 2026-04-06 | 45.464 | 1.411699 | -48.672195 | -308.142270 | -259.470075 |

这四个日期都不再五分钟内平仓，但持仓延长不保证每一笔获利；例如 2026 年 4 月持仓延长后仍遇下跌并亏损。以上净差同时包含数量、价格和路径变化，不是单因素修复收益。

## 新出现的两笔短持仓

| 日期 | 组合持仓秒 | 初买 / 补买 BTC | 控制净 USDT | 组合净 USDT | 同日持仓净差 USDT | 平仓证据 |
|---|---:|---:|---:|---:|---:|---|
| 2025-02-09 | 91.988 | 0.025 / 0.02 | 20.542309 | -9.974768 | -30.517076 | archived_jsonl seq 22612 |
| 2026-08-20 | 91.919 | 0.133 / 0.015 | 727.946393 | -28.316818 | -756.263212 | sqlite_read_only seq 29947 |

两笔均先发生部分成交，下一 cycle 依次追加保证金、补买、主动 reduce-only 市价平仓；关闭报告 `action=exit`、`entry_constraint=target`。这份账本报告不把该字段解释成具体内部风控分支。2 月为宏观机会，8 月为主策略机会；不能因为动作形态相似就预先认定同因。JSON 保留前一完整观察、平仓观察、后一观察、所有真实 fills 与订单，逐条标记 JSONL 或只读 SQLite 来源。

2026 年 8 月控制组持仓到 8 月 30 日；组合组 8 月 20 日约 92 秒即退出，丢失了该实际路径中的后续上涨。这是本年对比的重要差异，尚不能用账本比较代替修复后的反事实收益。

## 三次旧入场延迟

| Campaign | 控制首次成交 UTC | 组合首次成交 UTC | 提前小时 | 控制买入 VWAP | 组合买入 VWAP | 控制 / 组合净 USDT |
|---:|---|---|---:|---:|---:|---:|
| 1612800000000 | 2021-02-12T15:04:31.515000+00:00 | 2021-02-10T16:00:21.626000+00:00 | 47.069414 | 46,766.7000 | 44,463.5000 | 65.572989 / 335.544377 |
| 1708963200000 | 2024-03-04T00:00:34.168000+00:00 | 2024-02-28T11:00:21.668000+00:00 | 109.003472 | 63,263.0000 | 59,440.4000 | 257.268596 / 794.704063 |
| 1759104000000 | 2025-10-05T01:00:09.247000+00:00 | 2025-10-02T00:00:09.207000+00:00 | 73.000011 | 122,237.2103 | 118,705.7000 | 55.111226 / 344.418678 |

逐条核对了旧历史版本、控制组与组合版的 campaign ID、direction、anchor、risk、stop 一致。组合三次都恢复旧首次成交日期。数量、持仓结束时间和复利基数也发生变化，因此这些净差不等于盘口修复单独贡献。

## 2020 年 10 月趋势仓位仍按现行止损退出

| 版本 | 总买入 BTC | 平仓 UTC | 平仓 VWAP | 2020 年末该组权益贡献 USDT | 2020 年末持仓 BTC |
|---|---:|---|---:|---:|---:|
| 旧 79a 背景 | 4.839 | 2021-01-22T00:25:00+00:00 | 29,900.0000 | 79,083.410750 | 4.839 |
| 2.0.0 控制 | 0.289 | 2020-11-02T12:45:00+00:00 | 13,247.9000 | 428.460558 | 0.000 |
| 组合 v2 | 0.412 | 2020-11-02T12:45:00+00:00 | 13,230.8000 | 606.488886 | 0.000 |

组合版的会话报告显示原生止损从 10 月 20 日的 11,637.70 上调至 10 月 24 日的 12,717.40，再到 10 月 31 日的 13,230.80；持仓损失上限转负，保存了锁定利润的现行风险政策。该仓位在 11 月 2 日 12:45 平掉，没有持续持有到旧版本的次年 1 月。旧 2020 年大幅收益主要包含该仓位年末未实现利润及更大数量，不能因本次两个执行修复而宣称全部恢复。

## 使用与限制

复核命令（输出必须是尚不存在的新文件）：

```bash
python /workspace/scratch/4a60782c7dbc/diagnosis/combined_trade_attribution.py \
  --out /workspace/scratch/4a60782c7dbc/diagnosis/combined-trade-attribution.json \
  --markdown /workspace/scratch/4a60782c7dbc/diagnosis/combined-trade-attribution.md
```

- Same campaign or date net differences are realized-path comparisons, not isolated causal treatment effects. Position size, subsequent compounding, fills, entry time and later exits differ.
- The margin-only and book-v2-only full cases are outside this report; combined effects cannot yet be divided between repairs or their interaction.
- The four former short exits no longer occur within five minutes, but two new short exits exist. Do not claim the short-exit class is fully fixed.
- Closing observation action=exit and entry_constraint=target do not themselves name the internal guard branch. Independent code/mathematical cause verification is required.
- The old 2020 late-year trend stays open much longer and has much larger exposure. Its return is not a target guaranteed by preserving the current risk policy.
- Path MDD is the registered simulator path proxy; daily MDD uses UTC daily closing valuations. Neither establishes real native execution performance.
- 2026 is partial through 2026-09-19. CNY and USDT returns differ because of currency translation and conversion costs.
- No new out-of-sample economic claim, real account operation, replay or online GitHub verification is made by this script.
