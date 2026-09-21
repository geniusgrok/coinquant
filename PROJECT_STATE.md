# Pancakequant project state

## Effective mandate

Repository: `ychenracing/pancakequant`.

Continue the 2026-09-20 redesign on `research/on-demand-btc-20260920`. The system is for one user, manually triggered, one BTC perpetual, one production model and one exchange adapter. Normal execution must be bounded `run_once`: reconcile, read complete current state, decide, optionally execute under explicit authorization, verify protection/orders, persist recovery state, report, and exit.

Formal economics remain frozen:
- initial capital: CNY 10,000;
- formal interval: 2020-01-01T00:00:00Z through 2026-09-20T00:00:00Z;
- CAGR > 200%;
- complete-account mark-to-market MDD < 20%;
- exchange leverage setting fixed at 20x;
- sparse irregular manual trigger schedule is frozen before economic observations;
- no moving the window, lowering targets, hiding costs, or relabeling proxy results as native qualification.

No live trading, transfers, credential changes, or real account-setting changes are authorized by this work.

## Latest continuation: measured native refinement and rejected L1

See `evidence/continuation-results-20260921.md` and its linked JSON results.

- The baseline was reproduced exactly from the preserved native archive without
  reacquisition. Eight exact event states were recovered.
- Native minute execution resolves six events; two remain conservative within-minute
  ambiguities. Full refined proxy result: CAGR 44.121475%, MDD 77.049869%, two
  liquidations, 537 fills, unchanged 795 manual invocation schedule.
- Shared research replay supports verified minute/hour execution while retaining
  four-hour signal aggregation. Production adapter/execution/model are unchanged.
- L1 development-only linear-account proxy: CAGR 0.583756%, MDD 1.355090%; ten
  entries. Rejected for validation progression; 2024-end L1 data uninspected.
- 23 targeted checks passed across replay, native-parent replay, mixed resolution
  and linear accounting. Exact measured source and complete traces are persisted;
  restore via `evidence/native-refinement-originals.json`.
- OKX run 35559716288 was still queued at the latest check. Historical linear
  data/rules and execution protection semantics are not yet established.

All original economic and safety acceptance remains in force. No candidate
qualifies and main remains unchanged. Continue structural participation research
on this branch; never present cross-venue proxy as native qualification.

## Git / remote state

- `main`: `c886b7c63c6455bd7c933269e32cd35a6fb3e09a` (unchanged)
- active research branch before this state update: `ed157042464767e088503aa3a0f8b1ec677f5f53`
- latest verified runtime-code commit: `14b89f70daa0a53dcebd437e2938dcc621c2898a`
- durable native-history evidence branch: `evidence/native-btcusd-20260920`
- evidence branch HEAD: `230f9d60361bfec144d066c5684b5c3b96f996bb`
- durable native archive: `evidence/native-btcusd-history-6f5ba384.zip`, 4,679,317 bytes

Do not restore the historical `.transfer` packet over current source.

## Current production/runtime implementation

The current runtime is a bounded single-Bybit BTCUSD inverse-perpetual system with:
- explicit read-only default and UID/exposure authorization for writes;
- approved-host allowlist and redirect refusal;
- stable client order IDs and durable intents;
- unknown-write reconciliation before retry;
- conditional FOK hosted entries while flat;
- bounded IOC chunking for immediate execution;
- full-position MarkPrice native TP/SL;
- reduce-only risk removal;
- cancel/fill race handling;
- same-candle protection repair;
- shared pre-write risk validation;
- separation of single-order venue caps from total safe protected position capacity.

The runtime/model fixes through `14b89f70` also correct:
- executable-entry vs TP/SL geometry under spread/slippage;
- duplicated Decimal risk formula drift;
- new-entry stop positioning before projected liquidation;
- native exit replay lifecycle/ordering correctness discovered during structural research.

GitHub Actions run `35557150822` checked out exact runtime SHA `14b89f70...`, compiled `pancakequant`, `research`, and `tests` under Python 3.13, and ran **91/91 tests successfully**.

One requested production capability is still incomplete end-to-end: the adapter exposes Bybit isolated-margin adjustment, but the normal execution lifecycle does not yet apply model-driven add/reduce margin decisions. The economic M1 margin-buffer candidate was rejected, so implement margin adjustment only as a coherent execution capability, not as an assumed alpha improvement.

Private Bybit testnet order/TP-SL/amendment/margin semantics remain unverified without explicitly authorized usable credentials/UID.

## Native historical data: completed and preserved

Full native Bybit BTCUSD inverse trade/mark/funding history was successfully acquired from official `api.manepa.jp`:

- source workflow run: `35548881482`
- source artifact ID: `10617971281`
- artifact SHA-256: `717841c3267f5de40d0c0b103aeff3c067054eb7752ccf5b8cc1bcad11228159`
- inventory SHA-256: `43caf20501d1c076af42d74ee279be833be5fba6dfbb3ee1e43e668869a3ab47`
- acquisition window: 2019-12-11 warmup through 2026-09-20 exclusive
- base interval: native 60-minute trade + mark bars
- 83 contiguous shards
- 249 raw V5 pages
- 59,400 bar rows
- 7,425 funding rows
- independent integrity errors: 0

The original Actions artifact is additionally preserved byte-for-byte in the dedicated evidence branch above, so recovery does not depend on Actions retention.

## Historical rules status

`evidence/historical-rules-research.md` preserves dated evidence. Important facts:
- direct Bybit API captures from 2020-06 through 2022-01 repeatedly show BTCUSD tick 0.5, qty step/min 1, max order 1,000,000, max leverage 100, taker 0.075%, maker -0.025%;
- a 2024-04-26 V5 raw response shows tick 0.50, maxMktOrderQty 1,000,000, maxOrderQty 1,943,695, step/min 1, max leverage 100, 8-hour funding;
- current 2026 official instrument response has tick 0.10, maxOrderQty 25,000,000 and maxMktOrderQty 5,000,000;
- current/dated material supports a 150 BTC / 0.5% base risk tier, but the full dated 2020-2026 risk-tier/MMR timeline and exact later specification-change timestamps are not yet proven.

Therefore formal native-rule qualification is still blocked. The conservative proxy rules are intentionally pessimistic and live at:
- `evidence/proxy-rules-conservative.csv`
- `evidence/proxy-rules-conservative.md`

Proxy economics must stay `NOT_QUALIFIED`.

## Frozen proxy economic baseline on native market/funding

Evidence:
- `evidence/proxy-diagnostic-20260921.json`
- `evidence/proxy-diagnostic-20260921.md`

Runtime basis: `36fad1849bca116efffc23c8d3abb770508f2de8`.

Baseline:
- CAGR: **43.9207%**
- MDD: **77.0512%**
- final CNY: **¥115,452.49**
- liquidations: 8
- fills: 537
- decisions/invocations: 795 / 795
- longest baseline trigger gap: 151h
- drawdown: 2021-11-10 through 2022-11-21

Annual returns:
- 2020: +310.94%
- 2021: +58.55%
- 2022: -62.97%
- 2023: +150.41%
- 2024: +126.80%
- 2025: -8.41%
- 2026 partial: -8.01%

21-day absence stress:
- CAGR: 44.2932%
- MDD: 77.0472%
- liquidations: 8
- longest gap: 697h

The current inverse strategy is structurally far from CAGR > 200% / MDD < 20%.

## Structural research already completed — do not repeat

Evidence:
- `evidence/structural-research-20260921.json`
- `evidence/structural-candidates-20260921.json`
- `evidence/structural-candidates-20260921.md`

Rejected / closed directions:

1. **Immediate bearish collateral hedge (H3)**
   - CAGR ~41.38%, MDD ~78.0%, liquidations 12
   - worsened return, drawdown and churn
   - do not revive.

2. **Buffered isolated margin / M1**
   - full coherent candidate result: CAGR 43.51%, MDD 77.25%, liquidations 9, final CNY ~¥113,239
   - rejected economically.
   - A narrower immediate-fill safety experiment reduced liquidations in one diagnostic variant, but did not materially improve MDD/CAGR. Treat additional margin as execution safety capability only, not economic alpha.

3. **Collateral-neutralized bearish alpha (H4)**
   - CAGR 35.02%, MDD 76.59%, liquidations 13, final CNY ~¥75,196
   - reject.

4. **Exposure/leverage scaling**
   - increasing risk_fraction / effective leverage did not approach target and later worsened return
   - stop leverage scaling; do not chase the goal via more leverage.

5. **Stop-first liquidation-ordering upper bound**
   - diagnostic CAGR 44.16%, MDD still ~77.05%, liquidations artificially reduced to 0
   - proves hourly stop-vs-liquidation ordering is not the main economic blocker.
   - it is not a production rule.

Additional measured fact: in 2022 the derivative position was ~79.5% flat, ~12.2% short, ~8.3% long. Simple inverse short hedging did not solve the account economics.

## Collateral-vs-alpha attribution

Evidence: `evidence/collateral-alpha-attribution-20260921.json`.

Over the frozen interval:
- initial BTC equity: ~0.199976 BTC
- final BTC equity: ~0.203809 BTC
- BTC-unit equity multiple: only **1.01917x**
- BTC-unit CAGR: ~**0.283%**
- BTC-unit MDD: ~8.40%
- BTC price multiple: **11.328x**
- USD account equity multiple: **11.545x**

Interpretation: almost all USD CAGR in the current inverse system comes from BTC collateral appreciation; the trading alpha adds only ~1.9% BTC units over the entire window. Merely swapping settlement asset will remove this collateral beta but will not create enough alpha to reach CAGR > 200%. A new alpha/exposure structure is required.

## Active evidence job at handoff

Workflow run `35559122193`, commit `411419f3cd7796bf3fe73237d8bd796e74e6af13`, was queued at handoff to acquire **native 1-minute BTCUSD evidence** for eight hourly stop-vs-liquidation ambiguity dates:

- 2020-02-15
- 2020-11-02
- 2021-11-03
- 2023-12-11
- 2024-01-11
- 2024-03-15
- 2024-08-27
- 2024-12-05

Request file: `research/ambiguity-request.json`.

First action in the next session: read this run's actual current status. If successful, preserve the artifact remotely and use it only to resolve replay ordering evidence. Do not treat it as an economic strategy path because the stop-first upper-bound already showed that eliminating these liquidations barely changes MDD/CAGR.

## Next structural direction

Do **not** continue neighboring inverse-contract parameter tuning.

The strongest next hypothesis recorded by the completed research is to evaluate a **stable-settlement BTC linear perpetual** under the same frozen economic protocol, because BTC-settled collateral beta dominates current USD returns/drawdown. This is a research hypothesis, not an already-approved production exchange switch.

Before changing production:
1. verify a candidate single exchange/contract has real continuous coverage from the formal 2020 start through the same 2026 endpoint (trade, mark, funding, dated costs/rules);
2. verify the exchange can satisfy the required run-once native TP/SL and offline-order safety semantics;
3. keep 20x exchange leverage setting, sparse frozen trigger schedule, CNY 10,000 start and all cost/account-equity rules unchanged;
4. design a new alpha model that can generate genuine stable-settlement returns; do not expect the contract swap itself to deliver the target;
5. use 2020-2023 as development and preserve 2024-end as chronological validation until it is actually inspected for tuning.

`evidence/structural-candidates-20260921.md` mentions OKX BTCUSDT as a candidate direction. Re-verify its official 2020-boundary data and current protection semantics before relying on it.

## Remaining blockers before main

- No current candidate meets the economic targets.
- Full native historical trading-rule timeline is incomplete.
- Stable-settlement structural candidate has not yet been built/measured.
- Model-driven isolated-margin execution is not end-to-end.
- Private testnet order/protection/margin lifecycle is not yet verified.
- One-time/evidence acquisition hooks currently exist in the lightweight workflow; remove temporary acquisition plumbing after required evidence is durably preserved.
- Main must remain unchanged until applicable economic and safety requirements actually pass.

## Recovery instruction

Read `AGENTS.md`, this file, and `HANDOFF_PROMPT.md`; then re-read the live remote branch before writing. Prefer current remote evidence over stale local scratch. Rejected H3/H4/M1/leverage candidates are evidence, not code to restore. Preserve every meaningful checkpoint remotely.

## 2026-09-21 continuation: L2 rejected; native linear boundaries

L2 development proxy measured CAGR -1.096052%, MDD 15.974647%, 297 entries,
244 stops and five liquidations. Rejected, no validation run or adjacent tuning.
See evidence/l2-development-20260921.json and research/linear-hypothesis.md.

OKX probe run 35559716288 finished: both official hosts return empty 2020 mark
and funding data, although start trade and end trade/mark/funding are available.
All 15 original response/report files are preserved under
evidence/okx-boundary-probe-20260921/. Original ZIP SHA256
fddc78d56d85f7b6fb382a6d3a85923c0da6a7e2a1fd9bb53c4ba0661de75c15.
This rejects the tested API coverage path, not every possible archival source.

Binance official public archives returned January 2020 BTCUSDT linear trade,
mark and funding ZIPs; January mark/funding and September 19 trade/mark checksums also passed.
September 1-19 funding API returned 57 native settlements, retained exactly.
Daily funding archive returned 404; use the verified official API tail instead.
No production exchange change, no live writes, no main merge. All candidates
remain NOT_QUALIFIED; continue native contract/data feasibility and new alpha.

## Native Binance continuation / L3 preregistration

Binance current instrument confirms BTCUSDT PERPETUAL USDT and pre-2020 listing.
December 2019 native trade (744 hours) and funding (93 events) restored from the
official API. Mark starts 2019-12-23; no earlier mark is invented. Formal account
start remains January 1. See evidence/binance-linear-feasibility-20260921.md.

research/acquire_binance.py is acquiring checksum-verified monthly trade/mark/
funding and September daily price archives locally, with four bounded workers.
Known December archive 404s use the separately preserved API warmup evidence.
Do not reacquire successful archives; the script verifies and reuses cached files.

L3 is preregistered in research/linear-l3-hypothesis.md before measurement. It is
one expanding ridge forecast using matured four-day labels and causal momentum,
short return and settled funding inputs. research/linear_forecast.py screens only
2020-2023 at frozen sparse invocation times. Two tests prove unresolved labels do
not affect coefficients. L3 has NOT yet been measured; do not infer success.
It is a forecast diagnostic, not a tradable account or formal CAGR.

## CI cleanup after durable evidence preservation

Removed the one-time public schema, ambiguity acquisition and native-artifact Git
write hooks. One 10-minute read-only job remains: compile and offline unittest.
No full-history optimization or network collection runs in CI. Local full suite
passed 110 tests in 1.323 seconds; one existing ResourceWarning in a replay test
fixture is not a test failure. Hosted status must be checked separately.

## Latest user instruction: Binance only

The user explicitly selected Binance as the only supported exchange. Continue
BTCUSDT USDT-settled linear perpetual migration. Do not build an OKX production
adapter or retain multi-exchange compatibility. Current Bybit production code is
not yet replaced and must not be described as Binance-capable. Historical evidence
remains intact. Economic targets, fixed 20x and native partial-fill protection
requirements are unchanged. No live trading or account settings are authorized.

## Binance acquisition recovery after network-policy interruption

The local acquisition process was stopped by network policy. Physical audit
verified 75 ZIPs with exchange checksums (2020-01 through 2022-01); an interrupted
progress record claimed an additional file not retained, so only the physical
inventory is authoritative. Originals are preserved by
evidence/binance-partial-originals.json, with exact hashes in
evidence/binance-partial-inventory-20260921.json. Do not redownload these files.

The same 10-minute CI job temporarily has one explicitly requested public-data
remainder step, matching the user's authorized temporary evidence collection.
research/binance-acquisition-request.json lists exactly 203 missing archive paths.
It uses no secrets or private API, and runs no optimization. Remove the temporary
step again once this new Binance evidence is durable. L3 measurement remains
pending complete development data; no shorter-window result substitutes for it.

## Binance transport implementation checkpoint

research/binance_readonly.py implements a bounded GET-only migration transport,
exact HMAC query signing, fixed official hosts, redirect refusal, scrubbed failures
and verified Spot UID extraction. It validates native single-asset/one-way and
isolated 20x configuration without settings writes. Five targeted tests passed.
No credentials were read or private API called. Production remains the previous
Bybit runtime until the coherent Binance replacement is ready; this prototype
must not be advertised as a working Binance trading adapter.

Missing-data run 35564939199 corresponds to source
1ae46b54f21040b2e6f5b85e3390d805b0a3a8dc. Check actual status/artifact, preserve
verified results and merge with the 75 saved originals before L3 measurement.
