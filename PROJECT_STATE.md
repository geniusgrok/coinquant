# Pancakequant project state

## Effective mandate

Implement the attached 2026-09-20 redesign on `research/on-demand-btc-20260920`. Main remains at `c886b7c63c6455bd7c933269e32cd35a6fb3e09a` and must not receive an unqualified candidate. Formal economics remain CNY 10,000 initial capital, 2020-01-01 UTC through the frozen 2026 endpoint, CAGR > 200%, complete-account MDD < 20%, and exchange leverage fixed at 20. This task does not authorize live trading or real account changes.

## Current remote implementation

The active candidate is the single Bybit BTCUSD inverse path in `pancakequant/`. The old multi-exchange/multi-strategy resident bot was removed. The production lifecycle is bounded run-once: reconcile exchange state, read complete market/account data, compute one model target, optionally execute under explicit account authorization, verify actual orders/protection, persist a recoverable result, then exit.

The current path includes deterministic order identities, durable write intents, unknown-result reconciliation before retry, conditional FOK entries that may remain hosted only while flat, full-position native TP/SL readback, reduce-only risk removal, same-candle protection repair, cancel/fill race handling, and a shared pre-write risk validator used by both production execution and replay.

The `.transfer` packet is historical recovery evidence containing a different unqualified implementation. Preserve it independently; never restore it over current source or mix its adapter into production.

## Verified evidence

Remote commit `8662b403024d65876a0810d2400cd38f073fc54f` added pre-write revalidation of margin, leverage, risk budget, quantity/price rules and projected liquidation before any new exposure. GitHub Actions run `35521903584` checked out that exact SHA, compiled `pancakequant` and `tests`, and ran 55 offline tests successfully in Python 3.13. The workflow also preserved an immutable source archive artifact for that SHA.

These are synthetic/offline safety and replay checks, not live or testnet order validation. No private exchange credentials were used. Native Git from the current agent container still cannot resolve github.com, so connector writes are the active preservation path.

## Current research status

`research/spec.json` locks the formal upper bound at 2026-09-20T00:00:00Z and keeps the predeclared sparse irregular invocation schedule. The replay uses the same target model, one-minute trade and mark inputs, funding, dated rules/costs, inverse-contract arithmetic, continuous whole-account BTC/USD/CNY equity and conservative minute extrema.

No formal CAGR/MDD result exists yet. Complete native 2020-2026 trade + mark + funding data and a defensible dated historical fee/risk/liquidation-rule timeline have not yet been assembled into the strict manifest. Current-rule responses must not be backfilled across history and called native evidence.

A bounded public endpoint probe now checks the frozen start and end for native trade, mark and funding availability plus current instrument/risk schemas and one public historical trade file. Its output is schema/coverage evidence only; favorable endpoint responses do not qualify economics.

## Remaining blockers before main

1. Obtain and hash complete native BTCUSD inverse trade/mark/funding history for the frozen window, with enough causal warmup.
2. Source or explicitly bound the historical fee, funding schedule, risk-tier, size-limit and liquidation-cost timeline without copying current rules backward.
3. Run baseline sparse replay and the declared absence replay, preserving raw identity/equity/orders/results; report CAGR and MDD honestly.
4. Keep development (2020-2023) and chronological validation (2024-end) distinguishable; if validation is used for tuning, mark it no longer unseen.
5. Validate the current Bybit private-order lifecycle on an authorized testnet account when credentials/UID are actually available. Until then, private API behavior is unverified and live use remains blocked.
6. Only if the economic thresholds and necessary trading-safety checks pass should this redesign be merged to `main`.

## Direct recovery

Read this file and `AGENTS.md`, then read the current remote branch before writing. Continue from the latest commit; do not reconstruct from the old recovery packet. Preserve meaningful work promptly to the same research branch. If data or private API access is blocked, continue independent engineering and evidence work, but keep economics NOT_MEASURED/NOT_QUALIFIED and leave main unchanged.
