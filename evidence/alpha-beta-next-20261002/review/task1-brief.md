# BTC alpha/beta mechanism round — registered 2026-10-02

The user approved all eight directions described in the preceding design. This document and alpha_beta_spec.json make the approved design executable; routine parameter choices are fixed before new outcomes. Long-term runtimes remain Coinquant perpetual and Spotquant spot; Starquant supplies historical research/FX only. Neither engineering nor research authorizes credentials, account requests, orders, transfers or account settings.

## Frozen economics and source

BTCUSDT; initial CNY10000 without additions; 2020-01-01 through 2026-09-20 UTC exclusive. Use the original 795 primary starts, 300-second manual sessions and 5-second polls. Preserve prior-date FX and .001 conversion each way. Spot is long/cash, no borrowing/leverage. Perp retains one-way isolated funded protection. Only previously installed venue protection may act while the client is stopped. Preserve the disclosed Spot OHLC and Coin historical minute/volume proxies, known mark gap bound and complete money/execution/archive gates. Targets remain Spot CAGR>=100%/continuous MDD<=30%, Perp CAGR>=150%/continuous MDD<50%.

Baseline is the actually adopted Spot consensus (51.8503%/41.2073%) and Coin incumbent (119.2284%/44.1051%). Baseline commits and exact finite candidates are in the JSON spec. Baseline full monetary/trade/daily outputs must agree with previous originals under normalized synthetic identities; discrepancies block candidate promotion. Do not rewrite older raw files or their measured source identities. Full measurements require clean committed source and hashes of protocol/spec, market, FX, schedule and optional calibration inputs.

## Four Spot directions (six concrete variants)

trend-reentry: only an actual protective-stop or overextension exit may permit one recovery in the same bullish episode. Require two new completed closes after exit, close reclaiming the actual exit price, at least two original bullish sleeves and all ordinary fresh/capital/execution gates other than the explicitly bypassed fresh-cross latch. SMA/adverse exits keep original fresh-cross requirements. A close below the sleeve SMA resets the episode. Same-day stops never lead to same-day re-entry; consume allowance only after confirmed fill.

target-participation: with at least two actual bullish original sleeves and an already owned material tactical position, consider at most one confirmed add per completed day. If tactical BTC weight is below85%, buy toward90% using only free unreserved cash, original capital ceiling and protective ownership. Add only to already-held bullish sleeves; do not arm previously forbidden empty sleeves. Ordinary exits take priority. Preserve the existing new-BUY consensus path; no repeated within-bar churn.

atr-close: replace only ordinary adverse-close distance by clip(2*ATR14/actual entry, .02,.10), using completed daily true ranges only. Repair exceptions and all other rules stay. atr-stop: replace only protective distance by clip(4*ATR14/completed close,.10,.30); confirmed old protection can only tighten, never loosen. A stop through current price creates an ordinary next legal reduction, not a fictitious fill. Entry peak starts at actual fill, no pre-entry high. Do not revise protection while stopped. Evaluate the two variants separately before any combination.

core-permanent/core-slow: initial20% USDT subpool is a separate durable sleeve200, remaining80% continues all original SMA30/40/50 consensus sleeves. Subpools independently compound, never borrow cash/BTC, transfer, or maintain a 20/80 equity ratio. Reconstruct both cash ledgers from actual cached allocated fills and execution anchor; they must sum to the real account, including fees and dust. Tactical consensus sees only tactical quantities/free cash and its original three votes. Core orders/protection never merge with tactical groups. Permanent core is long whenever legally actionable and includes the original28% prior-peak protective stop; after stop it resumes only on a later new completed day. It is explicitly not pure buy-and-hold. Slow core uses completed close>SMA200, with the same protection and new-day restriction. Both keep cold-start/entries-enabled gates. Research checkpoint candidate/core mode and ratios are hash-bound and fail closed on mismatch.

## Four Coin directions

fresh-entry: original primary new longs require signal age<=24h and decision mark<=trigger completed close+one ATR14 computed before the trigger. No retroactive filtering of owned positions; macro rules remain unchanged. Preserve immutable trigger provenance through checkpoints.

atr-trail: only primary owned longs, only at actual session decision, raise stop to max(old proven stop, highest completed high since confirmed entry-3*completed ATR14). Never loosen; if through current mark, request normal owned reduction. Macro stop budget and all protection/replacement gates remain. Completed historical bars update causal state, never issue unattended modifications.

compression-breakout: add one primary long opportunity when no existing primary opportunity is active. Completed close must exceed the highest high of20 prior completed4h bars and prior ATR14 be<=.75*median of20 prior ATR14 observations. Stop=close-2*prior ATR; original funded sizing, seven-day life42bars, take=close*(close/stop)**20, priority/consumed identity and ordinary account gates. All rolling inputs precede trigger; no expanded grid or negative entries.

single-topup: preserve initial entry and all safety checks; allow at most one confirmed top-up per completed4h bar and only in the original entry's actual session. Count only proven increased position linked to the owned campaign; pending/unknown identities are recovered through the original Lifecycle and never resent. No weakening of fresh sizing/protection reads.

## Attribution, risk controls and selection

Instrument without extra adapter requests or clock changes. Retain distinct causal events for actual opportunity identity/age, trigger and decision price, reason for nonparticipation, desired/accepted/fill size, exit type, idle cash and capital/liquidity constraints. Post-run5/20-day prices are diagnosis only; they are never decision inputs or assumed missed profit. Preserve actual client/write bounds, positions, fees, funding, daily curves and original independent audits.

Run all registered single variants in all four existing project stresses, even if a base variant loses. Then independently rerun every complete new candidate with a fixed risk scale calibrated ONLY from2020-2021 USDT daily returns and the contemporaneous baseline. Scale is1 before2022, then min(1, training volatility ratio, positive beta ratio when necessary); beta floor .01. Calibration file binds input hashes/candidate/cutoff. No equity-curve rescaling/splicing. Existing positions keep their owned committed size; new sizing/allocation follows the fixed scale. Report2022-2026 validation achieved risk match separately; if realized vol>baseline*1.05 or beta>baseline+.02, no matched-alpha claim. This is historical stability testing, not clean OOS.

Mechanical selection requires all complete/known/audited matching stresses. Every matched CAGR must be>=baseline-.01; Spot matched continuous proxy MDD cannot increase, Perp matched MDD<.50. Base CAGR gain>=.01 OR continuous MDD reduction>=.01 with CAGR loss<=.01. Rank by worst stressed CAGR, then registered order. Report alpha-vs-beta evidence separately; neither a regression intercept nor increased exposure alone proves repeatable alpha. Original target qualification is separately unchanged.

Combine all independently eligible compatible directions without a subset search; two core modes are mutually exclusive, choose higher worst-stress CAGR (tie slow). If no mechanism eligible, report combination not applicable; if one, its tested account is the same final candidate. A new multi-mechanism combination requires all four complete stresses before selecting it. Finally replay incumbent and final selected Coin at initial9900/10100CNY and original-start offsets -/+60000ms in base as predeclared robustness diagnostics; original schedule/goal results remain separate. Do not choose an optimal capital or shifted schedule from these outcomes.

Candidate/default code may be integrated only after review and economic gates, preserving measured source and proving executable equivalence to the selected research path. Default replacement does not enable native trading. Initialize a source-bound all-cash shadow ledger after rules freeze; append only future observed completed public bars. Actual accounts/native cases/days remain zero. Full reports include every rejection, capital path sensitivity, costs, downside capture, ES, continuous vs daily MDD, partial2026, and prior research contamination.

## Implementation workflow

User already authorized implementation and normal integration. Use two mirrored isolated worktrees so existing sibling schedule/FX paths resolve; no account operations. Standard library runtime, no new dependencies or daemons. Use the existing PROJECT_STATE.md/HANDOFF_PROMPT.md as the single progress/recovery source. Briefs/reports/diff packages live in external task scratch, not a second progress system. Independently review source and completed financial evidence, run risk-relevant tests and exact-head CI, then integrate normal PRs without force or history loss.

 Coin mechanisms, causal event journal and reuse of real measurement engine

**Files:** create research/alpha_perp.py and tests/test_alpha_perp.py; modify shared pure code only if required for a reviewed seam, preserve existing default.
**Consumes:** complete_perp.ResearchExchange/variant/session runner, original market/prints/FX, frozen JSON spec.
**Produces:** CLI python -m research.alpha_perp --out FILE [--limit N] [--candidate NAME] [--scenario NAME] [--risk-calibration FILE] [--combo COMPONENTS] [--initial-cny VALUE] [--start-offset-ms VALUE] [--restore-prints]; source-bound JSON or lossless .json.gz with nested results candidate/scenario compatible monetary rows and causal opportunity_ledger. Inputs explicitly bind spec/protocol, component/risk/capital/starts and measured source. Full primary matrix default includes all5x4.
- [ ] Read actual call paths and add meaningful tests for rolling prior-only trigger, stale/chase entry, primary-only monotone stop and through-mark exit, confirmed top-up allowance/unknown recovery, checkpoint identity and no-op baseline.
- [ ] Implement exactly four variants and instrumentation with scoped hooks restored finally, no extra adapter calls. Reuse old measurement/audit; do not copy an exchange or change old candidate list permanently.
- [ ] Ensure unchanged incumbent actual three-session monetary/fill/daily prefix versus old complete_perp; include generated incomplete smoke only in /tmp.
- [ ] Run focused tests/compile, commit clean source. Write report with commits, exact tests, smoke evidence and limitations, no subagents.
- [ ] Independent spec+quality review from BASE..HEAD diff and report; address material findings before completion.

