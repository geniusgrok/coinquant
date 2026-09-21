# Proxy economic diagnostic — current BTCUSD redesign

This diagnostic uses **native Bybit BTCUSD trade/mark/funding history** but a
deliberately conservative **proxy** historical trading-rule timeline. It is not
formal native qualification.

Runtime code: `36fad1849bca116efffc23c8d3abb770508f2de8`.

Native data:
- Bybit official `api.manepa.jp`
- 2019-12-11 warmup through 2026-09-20 exclusive
- 60-minute trade + mark bars
- 83 contiguous shards, 59,400 bars, 7,425 funding events
- all 417 artifact files independently checked against inventory bytes/SHA-256
- artifact SHA-256 `717841c3267f5de40d0c0b103aeff3c067054eb7752ccf5b8cc1bcad11228159`

Proxy rules intentionally retain the older/coarser tick, lower order capacity
and 0.075% taker fee across the full period. Therefore favorable numbers still
cannot qualify as native.

## Results

| Metric | Baseline | 21-day absence |
|---|---:|---:|
| CAGR | 43.92% | 44.29% |
| MDD | 77.05% | 77.05% |
| Final CNY | ¥115,452 | ¥117,475 |
| Liquidation events | 8 | 8 |
| Fills | 537 | 531 |
| Invocations | 795 | 787 |
| Longest invocation gap | 151 h | 697 h |

Formal targets remain CAGR > 200% and MDD < 20%. Both runs fail by a wide
margin.

The baseline peak-to-trough maximum drawdown spans 2021-11-10 through
2022-11-21. Annual returns are strongly regime-dependent: 2020 +310.94%,
2021 +58.55%, 2022 -62.97%, 2023 +150.41%, 2024 +126.80%, 2025 -8.41%,
and 2026 partial -8.01%.

## Implication

The result does not support parameter polishing as the main next step. The
largest problem is structural: BTC-settled collateral remains materially
price-exposed during bear regimes, while sparse trend decisions and the current
derivative sizing/exit structure do not hedge that fiat delta sufficiently.
Eight conservative liquidation events further indicate that the 20x
position/protection interaction needs a safer target construction and/or finer
exit-path evidence.

The immediate model fix in `36fad184` makes a borderline new-entry stop move
inward to the next legal tick before liquidation instead of terminating the
entire replay; it does not relax the liquidation safety requirement.

Next research should prioritize collateral-delta hedging and regime-consistent
target exposure, then re-run the same frozen trigger schedule and data. Do not
move the window or lower targets.
