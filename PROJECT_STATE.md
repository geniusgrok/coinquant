# Pancakequant current recovery state

Status: ACTIVE RESEARCH / NOT_QUALIFIED. The task is not complete. Continue without
re-asking existing authorization. Read AGENTS.md and HANDOFF_PROMPT.md as well.

## Latest mandate

The user explicitly selected **Binance only** on 2026-09-21. Target one BTCUSDT
USDT-settled linear perpetual, one causal model, one adapter/current config and a
bounded manually triggered run_once. Retire other production adapters in the
coherent migration; retained Bybit/OKX evidence is historical research only.
All core architecture/model/risk code may change. Communicate in Chinese.

Frozen acceptance: CNY 10,000, 2020-01-01 UTC through 2026-09-20 exclusive,
CAGR > 200%, continuous complete-account MDD < 20%, exchange leverage exactly 20x,
the original sparse market-independent invocation schedule and realistic costs,
funding, margin, liquidation and collateral risk. No target/window/statistic change,
proxy relabeling or leverage escalation. No real trades, transfers, credentials or
real account-setting changes are authorized. Do not merge main before real economic
and necessary execution-safety acceptance. A checkpoint or CI pass is not completion.

## Git and verification

Repository ychenracing/pancakequant. Continue research/on-demand-btc-20260920.
Last remotely checked main: c886b7c63c6455bd7c933269e32cd35a6fb3e09a (unchanged).
Latest verified saved checkpoint before the changes in this commit:
f9ddd4321ffbf445f5d3cee2732d2500f6612cb6. Query the actual branch HEAD on recovery.
Native Git reads work; writes used the authorized GitHub connector. Changed files
were read back with exact-byte/hash and Git tree checks. No historical .transfer
restoration. No local-only winning strategy needs rescue.

Local full suite passed 110 tests in 1.323 seconds at CI cleanup source
bf40d47f383d543a154b1867036660b2ece5d370. Current Binance decoder/transport and
L3 causal-label tests passed 9 targeted checks. This does not imply a hosted pass.

Current data acquisition Actions run: **35564939199**, source
1ae46b54f21040b2e6f5b85e3390d805b0a3a8dc, job 106224786844; last observed queued.
Check current status instead of assuming it. Run 35564642239 was cancelled when
this explicitly requested data run superseded it. Do not wait if independent work
remains. Use [skip ci] for interim evidence/code commits to avoid cancelling the
needed queued acquisition. The same workflow has one 10-minute job, no secrets or
private API. Its exact-message public-data remainder/upload steps are temporary;
remove them again after Binance originals are durable. No optimization runs in CI.

## Current production / migration code

The prior production path is still Bybit inverse. Do NOT call it Binance-capable.
Original validated runtime reference: 14b89f70daa0a53dcebd437e2938dcc621c2898a,
91 tests in run 35557150822. Correctness fixes must not be removed for better metrics.

pancakequant/data.py and replay.py now support verified per-tick resolution, causal
volume normalization and complete 4h signal aggregation. Minute refinement is a
replay correction, not a profitable new strategy.

research/binance_readonly.py is a migration component, not yet production run_once:
bounded GET-only, exact Binance HMAC query, fixed official hosts, no redirects,
no caller signing-field overrides, errors scrubbed, UID read from Spot account
schema. No private request or real credential was used; tests use fake credentials.
The pure account decoder separates USDT equity, BTC quantity, isolated wallet,
native liquidation, current full-position TP/SL, stop/liquidation geometry and
possible entry remainders. It blocks incompatible modes, foreign collateral/positions
and conflicting account observations. A bounded snapshot now compares wallet/position identities, configuration, ordinary
orders and algo orders across two reads, retries state races at most twice, checks
mark freshness and reprices equity in USDT. Recent fills are explicitly not complete
recovery history. It exposes no write support.

Binance public API docs support MARK_PRICE close-all STOP_MARKET and
TAKE_PROFIT_MARKET; this does not prove atomic entry or partial-fill protection.
Native bracket/partial-fill/parent-remainder semantics, unknown writes and testnet
lifecycle remain unverified. Full migration must preserve default read-only,
matching account authorization, durable intent, stable client IDs, reconcile-before-
retry, full protection surviving exit and safe risk reduction. No daemon substitute.
See evidence/binance-linear-feasibility-20260921.md and
evidence/binance-api-chronology-20260921.json. Official changelog dates isolated
API support to 2020-01-03 and closePosition to 2020-05-18; historical replay must
not assume those features existed at January 1. Current conditional orders use
the Algo Service (migration 2025-12-09), not the old ordinary-order endpoints.

## Native Binance data: partial originals durable, remainder queued

Official current BTCUSDT instrument: PERPETUAL, margin/quote USDT, onboardDate
1567965300000 (2019-09-08 UTC), pre-2020 listing. Current rules are not historical
rules and must not be backfilled.

2020-01 trade/mark/funding ZIPs and 2026-09-19 trade/mark ZIPs have matching official
SHA256 checksums. September funding API tail has 57 settlements, with raw timestamp
millisecond offsets retained. Daily funding archive URL returned 404, official API
works. December 2019 API has 744 trade hours and 93 funding events; mark starts
2019-12-23 only. Signal warmup may use native trade, never fabricated earlier mark.
Formal account start remains January 1. All boundary responses/receipts are in
evidence/binance-boundary-20260921/.

Local acquisition was interrupted by network policy. Physical audit verified
**75 archives, 2020-01 through 2022-01**. The interrupted progress inventory claimed
one additional file not retained: physical-inventory is authoritative.
Original archive receipt: evidence/binance-partial-originals.json; inventory:
evidence/binance-partial-inventory-20260921.json.
Original ZIP: PANCAKEQUANT_BINANCE_NATIVE_PARTIAL_20260921.zip, 1,637,860 bytes,
SHA256 5ca1555d37fb4549b3ead4d61415d15500612aac6d01222b92f638c2ab580656,
Library id libfile_2a68f05223408191b0f115aff601c93f. Restore it, do not reacquire it.

research/binance-acquisition-request.json lists exactly **203 missing archives**.
research/acquire_binance.py verifies exchange checksums/CRC/OHLC and reuses cache.
Run 35564939199 requests only those missing public archives. Download its actual
artifact, verify all payloads, preserve originals and combine with the saved 75.
research/audit_binance.py then checks the complete frozen trade/mark/funding window,
without calculating validation economics. It is implemented but not yet run on a
complete Binance dataset. Historical fee/risk/filter timelines, exact funding price
at offset timestamps and USDT depeg exposure remain unqualified.

## Alpha experiments

Do not transplant the inverse model as a claimed solution: inverse BTC-unit CAGR
was only 0.283%, BTC quantity multiple 1.01917; almost all USD gain was BTC beta.
Read evidence/collateral-alpha-attribution-20260921.json.

L1 and L2 are rejected development-only proxies on native Bybit inverse prices and
funding, hypothetical linear USDT accounting/rules; not native Binance qualification.
2020-2023 only, original frozen sparse schedule, no validation fitting:

- L1 CAGR 0.583756%, MDD 1.355090%, 10 entries / 468 invocations. 306 no-direction,
  127 unsafe initial stop decisions. Low drawdown reflected very low participation.
- L2 CAGR -1.096052%, MDD 15.974647%, final CNY 9568.73; 297 entries, 244 stops,
  33 takes, 5 liquidations. More participation lost money after costs. Do not tune
  neighboring stop caps, thresholds or increase risk/leverage.

Read evidence/l1-development-20260921.json, l2-development-20260921.json,
research/linear-hypothesis.md. Exact source/full traces are durable in the originals
receipts below. research/linear_replay.py and sparse_trend.py currently contain the
rejected L2 research implementation, not an approved production strategy.

**L3 preregistered, implemented, NOT YET MEASURED.**
research/linear-l3-hypothesis.md and linear_forecast.py: one expanding ridge model
predicts four-day returns using causal 20-day momentum, one-day return and most
recent settled funding. Only matured labels enter training; fixed ridge 10, minimum
90 labels, no grid. Two tests verify label maturity isolation. Native Binance
2020-2023 screen at the original sparse invocation times; no shortened window as
substitute. Costs and overlapping forward-label limitations are explicit. It is not
a tradable account CAGR. Reject unless correlation is positive and directional net
forward return beats the causal long control. Only a passing screen justifies a
fully specified execution/account candidate. Do not tune against 2024-end; boundary
prices were inspected for data completeness, not alpha selection.

## Bybit baseline, refinement and rejected directions (retain evidence)

Native BTCUSD original is already durable on evidence/native-btcusd-20260920 at
230f9d60361bfec144d066c5684b5c3b96f996bb, path
evidence/native-btcusd-history-6f5ba384.zip, 4,679,317 bytes, SHA256
717841c3267f5de40d0c0b103aeff3c067054eb7752ccf5b8cc1bcad11228159.
83 shards, 59,400 hourly rows, 7,425 funding rows; no integrity errors. Do not
reacquire complete Bybit history. Conservative historical rules remain proxy:
evidence/historical-rules-research.md and proxy-rules-conservative.*.

Exact old baseline reproduced: CAGR 43.920748%, MDD 77.051193%, 8 liquidations,
537 fills, 795 invocations, max gap 151h. Absence stress remains failed. Original
reports: evidence/proxy-diagnostic-20260921.*. H3, H4, M1, risk escalation and
stop-first upper bound already failed; see structural-research/candidates evidence.
Do not resurrect them as economic candidates.

Minute task 35559122193 artifact 10622037487 is already recovered and saved.
8 complete native days, 11,520 minute rows, exact hashes/CRC/hour reconstruction.
Original 729,363 bytes, SHA256
7cf97ac730953674d7da9f503eddf0d16470b7fd3fa885d5ab16b4ace098580f,
durable 23 parts under evidence/ambiguous-minutes-20260921/.
Six stops resolve earlier than liquidation; two same-minute ambiguities remain.
Full refined replay: CAGR 44.121475%, MDD 77.049869%, final CNY 116538.70,
2 liquidations, 537 fills, 795 invocations, identical schedule hash. It confirms
ordering is not the main economic failure. See native-minute-ordering and
native-refined-baseline JSON and continuation-results-20260921.md.

OKX is no longer a production candidate. Run 35559716288 completed with failure:
both official hosts returned empty 2020 mark/funding, while trade and end pages
worked. All 15 raw/report files are under evidence/okx-boundary-probe-20260921/.
Original ZIP SHA256 fddc78d56d85f7b6fb382a6d3a85923c0da6a7e2a1fd9bb53c4ba0661de75c15.

## Other durable full originals

- evidence/native-refinement-originals.json: full baseline/refinement traces,
  exact measured sources and L1. ZIP 21,825,726 bytes, SHA256
  9985156a6c37bf733de49b0f162a0fddc9994a685a24b614f1062488d13105cd,
  Library libfile_4d0b56787e048191b3754decb32b983c.
- evidence/l2-boundary-originals.json: full L2 traces/exact source, OKX ZIP and
  Binance boundary ZIPs. 1,349,536 bytes, SHA256
  2d26c0a3b15827ce73297999e7a6562291c4b6853c26168dbbfd37f303525314,
  Library libfile_ba354742cd748191a65d34dd04515224.

Original refined replay preceded a later continuity guard; exact measured source is
inside its evidence archive. Do not mislabel a reused result as a fresh run of later
code. Preserve new meaningful evidence promptly, verify remote identities and keep
working on the same research branch. No task-completion claim is justified yet.

## Runner queue adaptation

The Ubuntu x64 data job remained queued for over 20 minutes. The same single job
is now submitted on the officially supported ubuntu-24.04-arm pool, with unchanged
Python version, 10-minute limit and 203-file request. This is one controlled pool
change, not repeated blind reruns. Query the newest run for the commit carrying this
change; 35564939199 is superseded by branch concurrency. No economic parameters
changed. L3 now records every archive/warmup hash in input-identity.json.
