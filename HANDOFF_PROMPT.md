# HANDOFF_PROMPT — Pancakequant redesign continuation

Continue the existing Pancakequant redesign. This is a continuation of the same authorized task, not a new project. Work directly from GitHub remote state and do not ask me to repeat authorization already granted.

Repository: `ychenracing/pancakequant`
Active branch: `research/on-demand-btc-20260920`
Main must remain unchanged until the active acceptance is genuinely met.

## Continuation update

Read the latest PROJECT_STATE.md section and `evidence/continuation-results-20260921.md`.
The old missing baseline-state blocker is resolved. Full native-minute refinement
was measured: CAGR 44.121475%, MDD 77.049869%, liquidations 8 -> 2. L1 development
proxy failed (0.583756% CAGR, 1.355090% MDD, ten entries); do not advance it to
validation or treat its low activity as success. Complete original evidence and
exact measured source recovery are in `evidence/native-refinement-originals.json`.
OKX probe 35559716288 remained queued. Continue authorized structural research.

## 1. Recovery order

Before changing code:

1. Read remote `AGENTS.md`.
2. Read remote `PROJECT_STATE.md`.
3. Re-read this `HANDOFF_PROMPT.md`.
4. Verify the actual current branch HEAD and `main`; do not assume the SHAs below are still latest.
5. Check GitHub Actions run `35559122193` first. It was queued at handoff for native 1-minute evidence on eight stop/liquidation ambiguity dates. If it completed, preserve and inspect its artifact before doing new work.
6. Do not restore `.transfer` over current source.
7. Keep meaningful work pushed to the same research branch promptly.

Handoff-time remote facts:
- `main`: `c886b7c63c6455bd7c933269e32cd35a6fb3e09a`
- research branch before handoff commit: `ed157042464767e088503aa3a0f8b1ec677f5f53`
- latest verified runtime code: `14b89f70daa0a53dcebd437e2938dcc621c2898a`
- native-data evidence branch: `evidence/native-btcusd-20260920`
- evidence branch HEAD: `230f9d60361bfec144d066c5684b5c3b96f996bb`

## 2. Original goal and non-negotiable acceptance

Pancakequant is being rebuilt as a simple personal, manually triggered BTC perpetual system:

- no 7x24 daemon requirement;
- user/AI explicitly invokes a bounded `run_once`;
- reconcile real account/orders first;
- fetch latest complete data;
- one quantitative model computes target direction/size/margin/entry/full-position TP/SL;
- execute through exchange API when explicitly authorized;
- re-read actual state/protection;
- persist recovery/report;
- exit.

Only one production BTC perpetual model, one production exchange adapter and one current configuration. Old multi-strategy/multi-exchange compatibility is not an acceptance requirement.

Formal economic acceptance stays:
- initial capital CNY 10,000;
- formal start 2020-01-01T00:00:00Z;
- frozen end 2026-09-20T00:00:00Z;
- CAGR > 200%;
- complete-account continuous MDD < 20%;
- exchange leverage setting fixed at 20x;
- real costs/funding/margin/liquidation semantics;
- sparse irregular trigger schedule frozen before economic observations.

Do not lower/rename these two economic targets, move the window, hide failures, or call proxy diagnostics native qualification. Backtests are not future-return guarantees.

No real-money trading, transfers, credentials or account-security setting changes are authorized by this continuation.

## 3. Engineering state already achieved

The runtime is already a bounded single-Bybit BTCUSD inverse path with:
- read-only default;
- explicit UID/exposure authorization for writes;
- approved API host allowlist and redirect refusal;
- stable client IDs and durable intents;
- unknown-write reconciliation before retry;
- conditional FOK hosted entries while flat;
- immediate IOC execution with bounded chunking;
- full-position MarkPrice native TP/SL;
- reduce-only risk removal;
- cancel/fill-race handling;
- same-candle protection repair;
- pre-write risk revalidation;
- total protected position capacity separated from per-order caps.

Latest verified runtime commit:
`14b89f70daa0a53dcebd437e2938dcc621c2898a`

GitHub Actions run `35557150822`:
- Python 3.13
- compile passed
- **91/91 tests passed**

Runtime correctness fixes already include executable-price protection geometry, shared Decimal risk math, stop-before-liquidation handling, and native exit replay lifecycle corrections. Do not regress them to make an economic candidate pass.

The adapter has isolated margin adjustment support, but the normal execution lifecycle still lacks a complete model-driven add/reduce-margin workflow. That remains an engineering item. However, the tested “extra margin improves economics” hypothesis was rejected, so do not confuse safety capability with alpha.

## 4. Native data is complete and durable

Full native Bybit BTCUSD inverse trade/mark/funding history has already been acquired from official `api.manepa.jp`.

Source:
- run `35548881482`
- artifact `10617971281`
- artifact SHA-256 `717841c3267f5de40d0c0b103aeff3c067054eb7752ccf5b8cc1bcad11228159`
- inventory SHA-256 `43caf20501d1c076af42d74ee279be833be5fba6dfbb3ee1e43e668869a3ab47`
- 2019-12-11 warmup to 2026-09-20 exclusive
- native 60m trade + mark
- 83 contiguous shards
- 249 raw pages
- 59,400 bars
- 7,425 funding rows
- integrity errors 0

It is also durably stored in Git, not only Actions:
branch `evidence/native-btcusd-20260920`
file `evidence/native-btcusd-history-6f5ba384.zip`
size 4,679,317 bytes.

Do not redownload the full dataset unless evidence proves this copy is corrupt/inapplicable.

## 5. Native rules are still incomplete

Read:
- `evidence/historical-rules-research.md`
- `evidence/proxy-rules-conservative.csv`
- `evidence/proxy-rules-conservative.md`

Dated evidence constrains substantial portions of the contract timeline, but a complete native 2020-2026 risk/MMR/specification/fee timeline is not yet defensible. Therefore the current economic numbers are diagnostic only.

Never backfill current exchange rules across the full history and call them native.

## 6. Current measured economics

Read:
- `evidence/proxy-diagnostic-20260921.json`
- `evidence/proxy-diagnostic-20260921.md`

Baseline on native market/funding + conservative proxy rules:
- CAGR 43.9207%
- MDD 77.0512%
- final equity ~¥115,452
- 8 liquidation events
- 537 fills
- 795 decisions/invocations
- longest trigger gap 151h
- max drawdown 2021-11-10 to 2022-11-21

21-day absence stress:
- CAGR 44.2932%
- MDD 77.0472%
- 8 liquidations
- longest gap 697h

Annual baseline returns:
- 2020 +310.94%
- 2021 +58.55%
- 2022 -62.97%
- 2023 +150.41%
- 2024 +126.80%
- 2025 -8.41%
- 2026 partial -8.01%

This is structurally far from CAGR > 200% / MDD < 20%.

## 7. Structural research already done — do not repeat rejected paths

Read:
- `evidence/structural-research-20260921.json`
- `evidence/structural-candidates-20260921.json`
- `evidence/structural-candidates-20260921.md`
- `evidence/collateral-alpha-attribution-20260921.json`

Rejected/closed:

- H3 immediate bearish collateral hedge:
  ~41.38% CAGR, ~78.0% MDD, 12 liquidations. Reject.

- M1 buffered isolated margin:
  43.51% CAGR, 77.25% MDD, 9 liquidations. Reject as economic path.
  Extra margin may still be useful as execution safety functionality.

- H4 collateral-neutralized bearish alpha:
  35.02% CAGR, 76.59% MDD, 13 liquidations. Reject.

- exposure/leverage scaling:
  no meaningful path toward target; higher risk eventually worsens return. Stop.

- stop-first upper-bound:
  44.16% CAGR, ~77.05% MDD even with liquidations forced to zero. This proves hourly stop/liquidation ambiguity is not the main economic blocker. It is diagnostic only, never a production rule.

Do not resurrect these by changing nearby parameters.

## 8. Key attribution result

The inverse system’s apparent USD return is almost entirely BTC collateral beta.

From `evidence/collateral-alpha-attribution-20260921.json`:
- BTC-unit equity: ~0.199976 -> ~0.203809 BTC
- BTC-unit multiple: 1.01917x
- BTC-unit CAGR: ~0.283%
- BTC price multiple: 11.328x
- USD account equity multiple: 11.545x

So the actual trading strategy adds only ~1.9% BTC units over the whole window. This is the decisive structural finding.

Implication:
- continuing inverse-contract parameter tuning is low-value;
- simply swapping to stable settlement will remove BTC collateral beta, but will also reveal that current alpha is far too weak;
- the next design needs both a stable-settlement account basis and a genuinely stronger causal alpha/exposure model.

## 9. Current active evidence task

Run `35559122193`, source commit `411419f3cd7796bf3fe73237d8bd796e74e6af13`, was queued at handoff.

Purpose: obtain native one-minute trade/mark evidence for eight ambiguous hourly stop-vs-liquidation dates:
2020-02-15, 2020-11-02, 2021-11-03, 2023-12-11, 2024-01-11, 2024-03-15, 2024-08-27, 2024-12-05.

Request: `research/ambiguity-request.json`.

If successful:
- preserve artifact remotely;
- resolve the eight replay ordering events with native 1m evidence;
- update replay/evidence only if the finer data demonstrates a correctness issue.

Do not spend substantial strategy effort on this: the zero-liquidation upper-bound already shows it cannot repair the 77% MDD.

## 10. Highest-value next research direction

Stop neighboring tuning of Bybit BTCUSD inverse.

Evaluate a **stable-settlement BTC linear perpetual** using the same frozen economic protocol and one production exchange candidate. `evidence/structural-candidates-20260921.md` records OKX BTCUSDT as a candidate direction, but independently re-verify before relying on it:

- continuous real data coverage from 2020-01-01 through 2026-09-20;
- contract launch date;
- native trade/mark/funding history;
- dated fees/risk/margin/specification rules;
- one-way isolated 20x execution semantics;
- native full-position TP/SL;
- partial-fill protection and remaining-parent behavior while the process is offline;
- cancel/amend/unknown-write reconciliation suitable for bounded `run_once`.

Do not switch production merely because a different venue looks attractive.

After selecting a viable stable-settlement contract, design a new causal alpha model rather than transplanting the current weak inverse alpha. Keep the system integrated and simple: one model deciding signal, exposure, sizing, margin and protection.

Research discipline:
- 2020-2023 development;
- 2024-end chronological validation until inspected;
- same frozen sparse trigger schedule;
- same CNY 10,000 start;
- same cost/account-equity truthfulness;
- no broad parameter-grid search as a substitute for structural improvement.

If a stable-settlement candidate also fails badly, diagnose signal/exit/exposure structure and replace the core model as authorized; do not lower targets or return to patch stacking.

## 11. Remaining engineering/safety work

In parallel only where independent:
- complete model-driven isolated-margin adjustment lifecycle if it remains relevant to the chosen production exchange;
- test private order / TP-SL / amendment / margin semantics on explicitly authorized testnet credentials when actually available;
- remove temporary one-time/evidence acquisition hooks from the workflow after all required artifacts are durably preserved;
- keep one lightweight CI, no long full-history research in normal CI.

## 12. Main / merge rule

Do not merge this redesign to `main` yet.

Main stays unchanged until:
- an actual candidate meets the economic targets under defensible inputs/assumptions;
- required execution-safety semantics are verified sufficiently for the chosen production path;
- remaining important unknowns are explicitly resolved rather than hidden.

If not yet achieved, continue autonomously on the existing research branch, preserve evidence, and report the exact gap.

## 13. Preservation status at handoff

All meaningful accepted code, acquired native history, baseline economics, rejected structural experiments and alpha attribution are already remote.

There is no accepted local-only strategy candidate that must be reconstructed. H3/H4/M1 scratch implementations are rejected research and should not be restored as production code.

The only active asynchronous external state to inspect first is GitHub Actions run `35559122193`.

Continue until either the active acceptance is genuinely met or a concrete external blocker makes further work impossible. Do not stop at a plan, PR, checkpoint, or partial test result.

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
