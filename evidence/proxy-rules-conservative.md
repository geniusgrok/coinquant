# Conservative proxy rules for economic diagnostics

This file accompanies `evidence/proxy-rules-conservative.csv`. It is **not**
a native historical rules timeline and must only be passed to
`research.build_manifest` with `--rules-provenance proxy`.

The single row deliberately uses conservative values that are supported at
multiple points but not proven for every instant of 2019-12-11 through
2026-09-20:

- launch time: 2018-11-15 from the current official BTCUSD instrument response;
- funding interval: 8 hours from the official current instrument response;
- tick: 0.5, matching direct Bybit `v2/public/symbols` captures from
  2020-06, 2020-08, 2020-10, 2021-04 and 2022-01; current tick 0.1 is not used;
- quantity step/minimum: 1, matching the same historical captures and current
  V5 instrument;
- single-order and market-order maximum: 1,000,000 USD contracts, matching the
  lower historical cap rather than the current 25,000,000 / 5,000,000 values;
- risk-limit base tier: 150 BTC and MMR 0.5%, matching current Bybit inverse
  documentation and the dated V5 risk-limit example, but **not** proven across
  the full historical window;
- taker fee: 0.075% for the entire window, matching the 2020-early-2022 regime
  and intentionally refusing later lower fees (0.06%, then 0.055%).

This proxy is intentionally pessimistic for fees/order capacity and should be
useful for answering whether the strategy is remotely close to the economic
target. Favorable results are still diagnostic only. Formal qualification
continues to require a dated native rules timeline.
