# Pancakequant project state

## Effective mandate

Repository: `ychenracing/pancakequant`.

Continue the attached 2026-09-20 redesign on `research/on-demand-btc-20260920`. Main remains unchanged until the candidate meets the applicable economic and trading-safety requirements. Formal economics remain CNY 10,000 initial capital, 2020-01-01 UTC through the research protocol's frozen complete-data endpoint in 2026, CAGR > 200%, complete-account mark-to-market MDD < 20%, with exchange leverage fixed at 20. This work does not authorize live trading, transfers, credential changes, or real account-setting changes.

## Current production design

The candidate is a single manually triggered Bybit BTCUSD inverse-perpetual system. The resident multi-exchange/multi-strategy bot path has been removed.

A normal run is bounded:

1. reconcile the configured exchange account, position, ordinary/conditional orders and fills;
2. read complete market/account state;
3. compute one causal model target;
4. remain read-only unless the current invocation explicitly enables execution and the configured UID/exposure authorization matches;
5. execute through durable intents and deterministic exchange client IDs;
6. re-read actual position/order/protection state;
7. persist the report/recovery state and exit.

The current execution path includes unknown-write reconciliation before retry, conditional FOK entries while flat, IOC immediate execution with bounded order chunking, full-position MarkPrice-triggered native TP/SL, reduce-only risk removal, cancel/fill-race handling, same-candle protection repair, and a shared pre-write risk validator. A single-order venue cap no longer incorrectly caps total safe position size; total position remains constrained by risk tier, account authorization, margin, risk budget, effective leverage and liquidity.

`api_host` is explicit and restricted to an allowlist of official Bybit hosts matching `live` or `testnet`; redirects remain blocked so credentials cannot be sent to arbitrary hosts.

## Latest runtime correction

Remote HEAD before this state-only update is:

`345c9fccf21a6bc8562e55a6b439e755fcc18eac`

The preceding CI at `3f99e28f9d7a2c809ff602dc51878352e466a8a2` exposed one real model bug: protection prices were computed from mark/trigger before spread and slippage were applied to the conservative executable entry. In sufficiently low volatility this could make a long entry limit exceed its own take-profit.

The fix now:
- keeps the stop beyond the causal current-mark/trigger reference;
- measures reward from the conservative executable entry to that stop;
- therefore cannot place TP on the wrong side of the executable entry merely because execution friction exceeds short-term ATR;
- uses one shared unit-risk calculation in both sizing and pre-write validation, eliminating Decimal regrouping drift that previously produced a false `1E-32 BTC` risk-understatement failure.

A regression test explicitly covers the low-volatility/high-friction geometry.

## Verification evidence

The GitHub Actions source artifact from failed run `35528571079` contains the exact `3f99e28` source tree and was used locally as the reproduction base.

On that exact source artifact plus the two corrective files that became commits `2e8e4568166f1370cdc308c31081cf77542c14ef` and `345c9fccf21a6bc8562e55a6b439e755fcc18eac`, the full short offline suite ran:

- Python 3.13-compatible source;
- 87 tests;
- 87 passed;
- no test errors/failures.

This is a local verification of the exact predecessor artifact plus the committed diff, not a substitute for reading the hosted result on the current SHA. GitHub Actions run `35542946661`, attempt 2, targets `345c9fc` and is currently queued. Do not call hosted CI passed until that run actually completes successfully.

These tests are offline/synthetic safety and replay checks. No private Bybit credentials were used. Live/testnet private-order semantics remain unverified.

## Historical-data pipeline

The branch now includes:

- `research/acquire.py`: resumable SHA-256-verified Bybit static archive acquisition;
- `research/build_trade_bars.py`: deterministic strict tick-to-minute trade OHLCV conversion with no forward-filled missing minutes;
- `research/acquire_v5.py`: public V5 trade/mark/funding acquisition with raw JSON receipts, deterministic normalized shards, resume-time hash revalidation and causal funding mark convention;
- `research/build_manifest.py`: strict manifest assembly that refuses incomplete/corrupt shards and requires an explicitly sourced historical rules timeline;
- `research/probe.py`: bounded public-only endpoint/archive coverage probe;
- hourly research input support that rebuilds the same UTC-aligned four-hour signal clock and rejects sub-bar historical rule changes.

Static official archive evidence currently establishes:
- BTCUSD trade originals exist from before the 2020 start and the public directory currently extends through 2026-08-08;
- BTCUSD static spot-index and premium-index archives contain the 2020 start but end in March 2020;
- therefore static directories alone cannot supply native mark/funding coverage for the complete 2020-2026 protocol.

Bybit V5 officially exposes inverse-contract trade klines, mark-price klines and funding-rate history. The US-hosted GitHub runner has returned HTTP 403 to the global V5 endpoint, so the collector supports explicit approved official regional hosts. This is an access constraint, not permission to synthesize missing native data.

## Replay correctness already tightened

Recent commits also:
- remove future bar extremes from trigger fill pricing;
- budget hosted FOK spread/slippage causally;
- model inverse liquidation/takeover through bankruptcy price and isolated position margin;
- freeze the supported hourly research replay basis;
- reject mid-hour rule changes that cannot be represented causally;
- separate single-order venue caps from total protected position capacity.

No fresh formal CAGR/MDD result exists for the current candidate.

## Remaining blockers before main

1. Complete native BTCUSD trade + mark + funding history through one frozen 2026 endpoint with causal warmup, or document the exact latest complete-data endpoint if official native sources demonstrably stop earlier.
2. Source a defensible dated historical timeline for fee, funding interval, tick/size limits, risk tier, maintenance margin and liquidation assumptions. Current rules must not be copied backward and labeled historical.
3. Assemble the strict manifest and run the fixed sparse baseline plus the declared absence stress replay; preserve identity, equity, orders and result artifacts.
4. Report CAGR, continuous whole-account MDD, annual/segment behavior, costs, funding, turnover/activity and failure modes honestly.
5. Keep 2020-2023 development distinct from the chronological validation interval; if validation is used for tuning it is no longer unseen.
6. Validate current private order/TP-SL/amendment semantics on an explicitly authorized Bybit testnet account when usable credentials/UID are actually available.
7. Merge to main only after the applicable economic targets and necessary safety checks actually pass.

## Direct recovery

Read this file and `AGENTS.md`, then re-read the remote branch HEAD before writing. Continue from the latest commit; do not restore the historical `.transfer` packet over current source. Preserve meaningful work promptly on the same research branch. If data access or private API validation remains blocked, continue all independent engineering/research work, but keep economics `NOT_MEASURED/NOT_QUALIFIED` and leave main unchanged.
