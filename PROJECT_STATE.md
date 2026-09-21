# Pancakequant project state

## Effective mandate

Repository: `ychenracing/pancakequant`.

Continue the attached 2026-09-20 redesign on `research/on-demand-btc-20260920`. Main remains unchanged until the candidate meets the applicable economic and trading-safety requirements. Formal economics remain CNY 10,000 initial capital, 2020-01-01 UTC through the frozen 2026 endpoint, CAGR > 200%, complete-account mark-to-market MDD < 20%, exchange leverage fixed at 20. This work does not authorize live trading, transfers, credential changes, or real account-setting changes.

## Current production design

The candidate is a single manually triggered Bybit BTCUSD inverse-perpetual system. Normal execution is bounded: reconcile account/orders/fills, read complete market state, compute one causal target, optionally execute under explicit UID/exposure authorization, re-read position/orders/protection, persist a recoverable report, then exit.

The current path includes stable client order IDs, durable write intents, unknown-write reconciliation before retry, flat-account conditional FOK entries, bounded IOC order chunking, full-position MarkPrice native TP/SL, reduce-only risk removal, cancel/fill-race handling, same-candle protection repair, and shared pre-write risk validation. Single-order limits do not incorrectly cap total protected position size; total exposure remains constrained by risk tier, account authorization, margin, risk budget, effective leverage and liquidity.

`api_host` is explicit and restricted to approved Bybit hosts matching `live` or `testnet`; redirects remain blocked.

One requested production capability is still not end-to-end: the adapter exposes Bybit `/v5/position/add-margin`, but the execution lifecycle does not yet apply model-driven add/reduce margin decisions. The interface semantics have been rechecked against current Bybit documentation (positive amount adds isolated margin, negative amount reduces it, up to 4 decimals). This remains a real implementation item, not an assumed capability.

## Runtime verification

Runtime code SHA `345c9fccf21a6bc8562e55a6b439e755fcc18eac` fixed two real issues found by hosted CI:

- low-volatility execution friction could previously place a conservative entry beyond its own TP;
- separate Decimal regrouping in sizing vs pre-write risk validation could create a false 1E-32 BTC risk-understatement failure.

The fix anchors stop geometry to the causal mark/trigger, measures reward from the conservative executable entry, and reuses one unit-risk function.

GitHub Actions run `35542946661`, attempt 2, checked out exact SHA `345c9fc`, compiled `pancakequant`, `research`, and `tests` under Python 3.13, and ran **87/87 tests successfully**. Immutable source artifact `10615063830` has digest `sha256:85a6006d9217842f40ed797a34ac1353827ba8eea895e7fc978e99be8c73f4a9`.

Later commits are workflow, acquisition-request, state, and evidence changes unless explicitly noted; do not silently claim a later runtime SHA without a runtime diff.

## Native historical-data access is now proven

Public probe commit `49e0184e535a55b5fa1a4af0ebda4a652b342d35` completed successfully in GitHub Actions run `35543278216`. The same run also executed 87/87 offline tests successfully.

The probe established:

- official static BTCUSD trade archive: first 2019-10-01, latest **2026-09-19**, 2,546 dated files;
- static spot-index archive: through 2020-03-17 only;
- static premium-index archive: through 2020-03-10 only;
- global `api.bybit.com` and `api.bytick.com` returned HTTP 403 from the US-hosted runner;
- official Bybit Japan host `api.manepa.jp` returned successful BTCUSD inverse V5 data for both formal boundaries.

Persisted raw receipts under `evidence/public-probe-49e0184/` prove:

- current instrument launchTime `1542211200000` (2018-11-15), leverage max 100, funding interval 480 minutes, step/min 1, current tick 0.10, current maxOrderQty 25,000,000 and maxMktOrderQty 5,000,000;
- native mark-price rows exist at 2020-01-01 and 2026-09-19;
- native funding rows exist at both boundaries, including the 2020-01-01 00:00 UTC funding event.

Therefore the formal 2020-01-01 through 2026-09-20 market/funding window is not blocked by Bybit history availability. The remaining task is full acquisition and hashing.

## Full native acquisition

`research/acquire_v5.py` is resumable, hashes every raw page and normalized shard, revalidates checkpoints, supports 60-minute native trade/mark bars, and stores funding with a causal boundary mark convention.

Attempt 1 failed before network access because the workflow invoked the module as a file and could not import `pancakequant`. This was fixed to `python -m research.acquire_v5`.

A temporary one-time acquisition job now exists inside the single workflow. It is restricted to the exact commit message `Acquire native BTCUSD history`, uses no private credentials, has a 10-minute timeout, and does not run economic tuning. Current request:

- run: `35548881482`
- requested data: `api.manepa.jp`, BTCUSD inverse
- warmup start: 2019-12-11
- formal end exclusive: 2026-09-20
- base interval: 60 minutes
- shard size: 30 days
- status at this state update: queued for dedicated Ubuntu acquisition runner

Do not call data complete until this run produces and validates its artifact.

## Historical trading-rule evidence

`evidence/historical-rules-research.md` preserves dated evidence rather than copying current rules backward.

Direct Bybit API captures preserved in public GitHub issues show BTCUSD at multiple points from 2020-06 through 2022-01 with tick 0.5, quantity step/minimum 1, max order quantity 1,000,000, max leverage 100, taker 0.075%, maker -0.025%.

A 2024-04-26 V5 raw response preserved in Bybit.Net issue #207 shows BTCUSD still at tick 0.50, maxMktOrderQty 1,000,000, maxOrderQty 1,943,695, step/min 1, max leverage 100 and 8-hour funding. The 2026 current official response has tick 0.10 and larger order caps, so those changes occurred after 2024-04-26; exact change timestamps remain unverified.

Current/dated Bybit material supports a 150 BTC base risk tier with 0.5% MMR, but a full 2020-2026 dated risk-tier timeline is not yet proven.

For economic diagnostics only, `evidence/proxy-rules-conservative.csv` fixes conservative assumptions: tick 0.5, step/min 1, 1,000,000 order caps, 150 BTC / 0.5% base risk tier, 8-hour funding interval, and 0.075% taker fee for the entire window. It must only be used with `--rules-provenance proxy`; favorable results cannot qualify as native acceptance.

## Replay/data pipeline

The branch includes:

- `research/acquire.py`
- `research/build_trade_bars.py`
- `research/acquire_v5.py`
- `research/build_manifest.py`
- `research/probe.py`

Replay supports native 60-minute trade/mark extrema while rebuilding the same UTC-aligned four-hour signal clock, rejects sub-hour rule changes that cannot be represented causally, prevents future bar extremes from setting fills, models funding and inverse liquidation/takeover, and separates venue single-order limits from total protected position capacity.

No fresh formal CAGR/MDD result exists for the current candidate.

## Remaining blockers before main

1. Finish the full native trade + mark + funding acquisition and verify the artifact/hash inventory.
2. Assemble a proxy manifest immediately for economic diagnosis; run the fixed sparse baseline and absence stress without relabeling it native.
3. Continue closing the dated historical rules timeline. Only a defensible native rules timeline can turn a favorable replay into formal native qualification.
4. Report CAGR, continuous whole-account MDD, annual/segment behavior, costs, funding and activity honestly; if targets fail, continue structural model improvement without moving the frozen window.
5. Implement and verify model-driven isolated-margin adjustment without weakening protection or unknown-write semantics.
6. Validate private Bybit order/TP-SL/amendment/margin semantics on an explicitly authorized testnet account when usable credentials/UID are actually available.
7. Merge to main only after economic targets and necessary safety checks actually pass.

## Direct recovery

Read this file and `AGENTS.md`, then re-read remote branch HEAD and acquisition run `35548881482`. Continue from the latest commit; do not restore the historical `.transfer` packet over current source. Preserve meaningful work promptly. Until native economics are actually measured, keep qualification `NOT_MEASURED/NOT_QUALIFIED` and leave main unchanged.
