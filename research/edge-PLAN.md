# BTC alpha/beta improvement implementation plan

> Execute task by task using subagent-driven-development. The user approved the whole design and direct implementation. PROJECT_STATE.md is the sole current progress ledger; task briefs, reports and diff packages live in external scratch. Existing source-bound evidence remains immutable.

**Goal:** Improve BTC trend participation and cost-net returns at comparable risk, with an adopted shared-runtime change or an explicit audited rejection for every registered mechanism.

**Architecture:** Reuse the finite shared session/Lifecycle and existing financial audits. Add a small registered research layer for causal mechanism changes, then promote only measured eligible mechanisms to the shared runtime. Two execution repositories remain separate.

**Tech stack:** Python standard library, Decimal monetary accounting, existing public market/FX caches, unittest and normal GitHub PR integration.

**Spec:** User-approved design in the preceding response; repository research/spec.json remains binding for economics. Task 2 writes edge-PROTOCOL.md and edge_spec.json before any new financial candidate measurement.

## Global constraints

- BTCUSDT only; Spot long/cash without borrowing or leverage; Coin one-way isolated perpetual, no default shorts.
- Initial CNY10000/no additions; 2020-01-01T00:00:00Z through 2026-09-20T00:00:00Z exclusive; original 795 finite 300-second sessions/5-second polls. No client actions while stopped.
- Preserve original FX, costs, latency, actual fills/funding, ownership, durable unknown-response recovery and installed protection requirements.
- Spot target cost-net CAGR>=100%/continuous MDD<=30%; Coin>=150%/continuous MDD<50%. Proxy MDD, historical contamination and zero native qualification remain explicit.
- Baselines: current shared ATR Spot default scale1; incumbent Coin SX60+DFII10 primary7.5/macro3.6. Old consensus is diagnostic historical evidence only.
- All Coin producers and synthetic-account tests with overlapping UIDs run strictly serially; never modify HOME, remove locks or bypass UID checks.
- Clean committed source and exact input/spec/protocol identity required before financial measurements; protected measured source freezes until its financial review finishes.
- No exchange credentials, accounts, orders, transfers or settings. Engineering authorization includes normal branches/PR integration, never force or history deletion.
- Predeclare a small finite candidate set. No parameter/subset/start-time search or rejection recycling. Funding and basis simple entry filters already have negative prior evidence.

## Review focus

Missing causal feature data must not become zero; future bars/rates cannot influence a prior decision. Spot held positions cannot be topped up. Stops cannot loosen and ordinary-exit changes cannot suppress safety exits. Coin checkpoint restores must bind mechanism state before recovery. A benchmark or portfolio curve must come from actual complete funded accounts under declared execution constraints.

### Task 1: Existing-evidence attribution

- [x] Add research/edge_attribution.py and meaningful synthetic tests in Spotquant; read immutable accepted raw accounts without invoking producers.
- [x] Classify actual Spot exits and subsequent flat periods by stop/SMA/extended/other/never-entered, retaining unresolved ownership as unknown. Separate price opportunity diagnostics from realizable profit.
- [x] Compare incumbent Coin original/-60s/+60s by actual opportunity identity and first causal operational divergence; distinguish prior-equity propagation, different observations, rounding, sizing, top-up, exit and timeout without declaring every timing difference a bug.
- [x] Produce source/hash-bound attribution and prior funding/basis evidence summaries; test, commit and independently review.

### Task 2: Registered protocol and point-in-time features

- [x] Freeze exact candidate rules, parameter values, compatibility, stress/risk/tail adoption gates and controls in edge_spec.json/edge-PROTOCOL.md in both repositories.
- [x] Reuse verified public inputs to build source-bound completed-bar trend/funding/basis features with explicit availability/staleness and coverage reports; preserve missing data rather than manufacture history.
- [x] Test temporal boundaries and prior-result immutability; commit and independently review before candidate measurement.

### Task 3: Spot mechanisms and executable controls

- [x] Implement independently: two completed closes for ordinary SMA exit, and stop-distance account risk budget for genuine new BUY. Both retain the current ATR incumbent and all other exit/cash/protection gates.
- [x] Implement a separately registered funding/basis-trend interaction only if Task 2 establishes complete causal inputs; otherwise deliver the precise infeasibility/rejection evidence.
- [x] Reuse actual finite Lifecycle replay with attributable decisions, actual fills, risk scale and initial capital inputs. Add declared protected BTC participation/cash controls under the same execution meter, identifying any policy-specific protection differences.
- [x] Test money, ownership, exit priority, causality and restoration; commit and independently review.

### Task 4: Coin mechanisms

- [x] Implement opportunity-quality risk budget and trend/funding-aware holding-horizon rules independently, preserving actual funded sizing, installed stops and finite-session constraints.
- [x] Apply an execution-dependence fix only if Task 1 identifies a specific unnecessary same-opportunity dependency; otherwise record no justified fix and retain timing sensitivity tests.
- [x] Include actual journals, causally known features, fixed risk scale and split initial-capital inputs. Test checkpoint/recovery, causal expiry/extension and unchanged macro/safety paths; commit and independently review.

### Task 5: Assessment, combinations and two-account capital

- [x] Reuse independent money reconstruction and risk/statistics helpers with the new spec identity and current ATR baseline; retain all negative results.
- [x] Calibrate only on 2020–2021 USDT returns and rerun actual new sizing after 2022; report achieved beta/vol upper bands accurately, along with tails/capture/underwater and historical-selection limitations.
- [x] Combine all independently eligible compatible mechanisms without subset search; measure a new combination if needed.
- [x] Register actual fixed separate budget pairs Spot/Coin CNY2500/7500,5000/5000,7500/2500, no transfers/rebalancing. Aggregate synchronized real daily equity/exposure; do not claim continuous joint MDD from daily-only data.
- [x] Test invalid/missing/source-mismatched rows, calibration boundaries and capital conservation; commit and independently review.

### Task 6: Measurement, adoption, future evidence and integration

- [x] Freeze reviewed producers/evaluator; run all registered candidates and controls across declared stresses, actual risk accounts, applicable combinations and original +/-60s Coin diagnostics. Complete independent financial review before promotion.
- [x] Run actual split-budget selected accounts and produce a capital/exposure recommendation, including budget-sensitive execution differences and uncertainty.
- [x] Integrate eligible mechanisms into canonical shared runtime and prove executable account equivalence. Rejected mechanisms remain research-only; default retention is an explicit outcome.
- [x] Implement a source-bound forward shadow decision/execution ledger with public observations, explicit modeled fills/costs and no retrospective backfill. Freeze and initialize; no unsupported promise of unattended operation or fabricated elapsed account days.
- [x] Write every result/rejection and original-target distance, preserve complete originals and manifest, run relevant local checks and whole-branch review, push normal PRs, retain one final fullsuite per repository and necessary local failed-case recovery, and complete normal integration.

Financial/default/forward, immutable retention and whole-branch review are complete. Coin sole full CI443/5skips passed; Spot sole full CI350/11skips failed3obsolete fixtures, now corrected and passed once locally with independent narrow review. Spot CI remains failed; approved composite validation is retained. Normal integration completed: SpotPR10 merge9b5b2d69, CoinPR59 merge3da4f77b; both main worktrees fast-forwarded, identical merge trees recorded. Main closure changes documentation/evidence only [skip ci]. No outstanding delivery item. User minimum-check policy: no repeated or optional tests; no second fullsuite.
