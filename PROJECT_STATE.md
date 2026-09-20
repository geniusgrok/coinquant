# Pancakequant project state

## Effective mandate

Implement the attached 2026-09-20 redesign on `research/on-demand-btc-20260920`. Main remains at `c886b7c63c6455bd7c933269e32cd35a6fb3e09a` and must not receive an unqualified candidate. Formal economics remain CNY 10,000 initial capital, 2020-01-01 UTC through the frozen 2026 endpoint, CAGR > 200%, complete-account MDD < 20%, and exchange leverage fixed at 20. This task does not authorize live trading or real account changes.

## Current remote implementation

The active candidate is the single Bybit BTCUSD inverse path in `pancakequant/`. The old multi-exchange/multi-strategy resident bot was removed. The production lifecycle is bounded run-once: reconcile exchange state, read complete market/account data, compute one model target, optionally execute under explicit account authorization, verify actual orders/protection, persist a recoverable result, then exit.

The current path includes deterministic order identities, durable write intents, unknown-result reconciliation before retry, conditional FOK entries that may remain hosted only while flat, full-position native TP/SL readback, reduce-only risk removal, same-candle protection repair, cancel/fill race handling, and a shared pre-write risk validator used by both production execution and replay.

Through runtime commit `f2eca8a6001edf2d7d0d2af3d3186055a420ecaf`, a blocked/crashed pre-write target no longer consumes the signal candle: `last_candle` is persisted only after the bounded target lifecycle returns successfully. Unknown writes remain deduplicated by durable intents and deterministic exchange client identifiers.

The `.transfer` packet is historical recovery evidence containing a different unqualified implementation. Preserve it independently; never restore it over current source or mix its adapter into production.

## Verification evidence

The last fully verified runtime snapshot is commit `8662b403024d65876a0810d2400cd38f073fc54f`. GitHub Actions run `35521903584` checked out that exact SHA, compiled the current source and ran 55 offline tests successfully in Python 3.13. Those tests cover the run-once execution model, risk validation, unknown-write reconciliation, entry/protection lifecycle and sparse replay behavior.

Later branch changes add:
- resumable, atomic, SHA-256-verified acquisition of Bybit public BTCUSD archive originals in `research/acquire.py`;
- HTTP Range/416 recovery without promoting an unverified partial file;
- deterministic conversion of verified native tick originals into strict complete one-minute trade OHLCV shards in `research/build_trade_bars.py`;
- hard rejection of missing trade minutes instead of forward fill;
- byte-reproducible derived gzip output;
- the pre-write `last_candle` recovery fix and its regression test;
- CI compilation of `pancakequant`, `research` and `tests`, with latest-run concurrency replacing stale queued checks.

These later changes are saved remotely, but their exact latest aggregate test result must be read from the newest workflow run before being called passed. Do not reuse the 55-test result as if it validated later commits.

The public-only probe attached to commit `aab75ea29dbed9678781b6f837b43adb9e47f0d8` is preserved at `evidence/public-probe-aab75ea.json`. GitHub Actions run `35522765182` obtained the official Bybit BTCUSD 2020-01-01 trade archive (1,634,666 bytes, SHA-256 `380fffa270906f97098e98cc68d7358513e8970b9800ff4e84612925927cd3ed`). The same US-hosted runner received HTTP 403 from Bybit V5 market/instrument/risk/funding endpoints. This establishes that the static public archive path is usable from that runner; it does not prove complete historical mark/funding/rule coverage.

All current safety tests are synthetic/offline unless explicitly identified otherwise. No private exchange credentials were used. Native Git from the current agent container cannot reliably resolve github.com, so the authorized GitHub connector is the active preservation path.

## Current research status

`research/spec.json` locks the formal upper bound at 2026-09-20T00:00:00Z and keeps the predeclared sparse irregular invocation schedule. The replay uses the same target model, one-minute trade and mark inputs, funding, dated rules/costs, inverse-contract arithmetic, continuous whole-account BTC/USD/CNY equity and conservative minute extrema.

No formal CAGR/MDD result exists yet. Complete native 2020-2026 mark + funding data and a defensible dated historical fee/risk/liquidation-rule timeline have not yet been assembled into the strict manifest. Current-rule responses must not be copied backward across history and called native evidence. Trade-price bars, spot index and premium index must not silently substitute for native mark price.

The archive collector and trade-bar builder are intentionally separate from the formal dataset manifest. They preserve original bytes, hashes and deterministic derived trade bars while mark, funding and dated rules remain hard qualification dependencies.

## Remaining blockers before main

1. Verify and acquire complete native BTCUSD inverse trade/mark/funding inputs for the frozen window plus causal warmup. Public static candidate paths are probed directly; unsupported paths remain unqualified.
2. Source or explicitly bound historical fee, funding schedule, risk-tier, size-limit, maintenance-margin and liquidation-cost changes without copying current rules backward.
3. Assemble the strict manifest and run baseline sparse replay plus the declared absence replay, preserving identity/equity/orders/results; report CAGR and MDD honestly.
4. Keep development (2020-2023) and chronological validation (2024-end) distinguishable; if validation is used for tuning, mark it no longer unseen.
5. Validate the current Bybit private-order lifecycle on an authorized testnet account when credentials/UID are actually available. Until then, private API behavior is unverified and live use remains blocked.
6. Only if the economic thresholds and necessary trading-safety checks pass should this redesign be merged to `main`.

## Direct recovery

Read this file and `AGENTS.md`, then read the current remote branch before writing. Continue from the latest commit; do not reconstruct from the old recovery packet. Preserve meaningful work promptly to the same research branch. If data or private API access is blocked, continue independent engineering and evidence work, but keep economics NOT_MEASURED/NOT_QUALIFIED and leave main unchanged.
