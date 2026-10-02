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

 Freeze, measure all accounts, inspect completed evidence and adopt eligible code

**Files:** immutable evidence/alpha-beta-next-20261002/*, selected minimal runtime changes if any, current README/AGENTS/PROJECT_STATE/HANDOFF and reproduction guide.
- [ ] Freeze all implementation/evaluation source before full runs. Run every48 single case on exact original public inputs; preserve failed cases, repair proven implementation defects and rerun affected complete accounts with source provenance.
- [ ] Verify baselines against originals, complete real session/archive gates and independent funds. Prepare training-only calibration and run all10 complete new-candidate base risk-account replays.
- [ ] Run prescribed eligible compatible combos in all4stresses and incumbent/finalCoin9900/10100/start+/-60s sensitivity accounts. Do not skip registered single directions or turn diagnostics into optimal-capital search.
- [ ] Independently review cash/fills/funding/daily/continuous proxy risks, causal gates, risk-calibration chronology, selected choices and all descriptive claims.
- [ ] If eligible, move selected minimal logic into shared default path with complete executable equivalence, state migration rejection and mandatory safety tests; otherwise preserve default and document all rejection reasons.
- [ ] Retain complete public raws/review/SHA manifests (exclude self/progress/cache), final attribution/CSV/chart, initialization only forward ledger and full reproduction commands. Preserve original targets, original measurement identities and native0/actualdays0.
- [ ] Run appropriate final local checks, normal branch push and independent whole-branch review; exact-head CI then normal PR integration, mainCI, clean worktrees. No additional permission for already-authorized normal integration.

## Financial evidence audit context

Previous immutable baseline originals:
Spot evidence/complete-delivery-20261001/spot-consensus-corrected.json bytes SHAcf075b86ba5df590e078a7c626c53cb20937be955cfb6ad8d41eae19b78645e8, use all four complete corrected consensus scenes. Assembled spot-accounts-verified.json SHA439edad38e7a2af382597d204f35cd0a6372ca9da98cdcf4c964852329568e92 has truthful per-account source maps. Earlier spot-accounts-final.json SHA65cc08a7341eb2ef7d7b30641b783341edd7dc7781e8dfa10ae801b5b8c86022 retains failed consensus cases; exclude them as reference.
Coin evidence/complete-delivery-20261001/perp-exclusive-accounts.json bytes SHA15dd7bfc242d52bf692663179cd1e3867418f8b55a4cad0894d253a8b296f00a, use incumbent all four scenes. It is explicit end-exclusive derivation of older source; preserve measured provenance.

Full new-baseline equality must compare exact money, fills, daily closing balances/equity, fees/funding, continuous MDD, original action/clock traces and session statuses/cycles under any necessary normalized synthetic owner IDs. Ignore generated SQLite/archive content hashes and source/checkpoint metadata only when explicitly nondeterministic; verify each archive proof separately. Do not normalize price, quantity, actual timestamp, cash, deadline or financial events. Report every remaining difference and stop adoption until resolved.

Original references: Spotconsensus CAGR.5185027797160926, continuousproxyMDD.4120733483379038, finalCNY165529.1033820122; Coinincumbent CAGR1.1922835553585416, continuousproxyMDD.4410507881955692, finalCNY1951753.808294805. Coin previous USD positive daily beta .2758482 and old Spotconsensus .3970688 are descriptive checks, not fixed acceptable outputs.

All48 registered unscaled actual cases and ten calibrated new base cases must be inventoried, including measured failures. Conditional combo runs and Coin registered robustness accounts must be listed explicitly and never treated as absent because new candidates lose. Source fixes during evidence phase preserve failed outputs and rerun affected cases under new clean source; account source mappings cannot be rewritten.

Audit independent trade ledger: actual cash, quantity, both fee assets, realized perp PNL, every funding timestamp strictly<END, open terminal BTC mark and both .001 FX conversions. Recalculate closing returns/regression/calibration/validation from actual raw daily paths. Continuous MDD is only the declared dailyOHLC or minute/envelope historical proxy; do not call it native or order-book verified. Check core/tactical pool invariants and grouped order owners, no offline amendments or reentries. Unknown pending and unverified archives fail complete.

Risk-calibrated profiles train only2020-2021. The actual validation-rerun can retain incumbent positions crossing cutoff, not rescale existing equity or owned targets. Report achieved-match limits; failed matching forbids a matched-alpha claim. Postevent5/20-day prices never become trades or attainable missed-profit values. Year2026 is partial and whole2020-2026 is previously studied, not clean future evidence.

Total new source-bound forward history should initialize all cash with zero events/days, using actual initialization UTC after freeze. Only later observed completed public bars may append. Native cases0, actual account-days0 and original economics targets unchanged. No real credentials/accounts/orders.
