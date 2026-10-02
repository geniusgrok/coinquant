# BTC alpha/beta mechanism implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development task by task. User approved the full preceding design and execution; continue without repeated approvals.

**Goal:** implement and validate all eight mechanism directions, identify actual cost-net alpha/beta improvement and integrate only eligible defaults.
**Architecture:** reuse current real session/Lifecycle, ownership, causal history and money audits; small isolated research modules and bounded hooks, immutable source-bound outputs. Evaluation/calibration in Spot consumes exact same Coin/Spot inputs; two runtime repositories remain separate.
**Tech Stack:** Python standard library; optional existing matplotlib for charts.
**Spec:** research/alpha-beta-PROTOCOL.md and research/alpha_beta_spec.json (byte-identical in both worktrees).

## Global Constraints

- BTCUSDT only, initial CNY10000, no deposits;2020-01-01..2026-09-20 UTC exclusive.
- Original795 primary starts,300s sessions/5s polls; no client decisions while stopped.
- Spot long/cash/no leverage; Coin one-way isolated, original funded/protected ownership and macro budget.
- Spot target CAGR>=100%/continuous MDD<=30%; Coin>=150%/MDD<50%; qualification remains NOT_QUALIFIED.
- All48 single-candidate/stress accounts: Spot7x4, Coin5x4, plus10 new-candidate real risk-calibrated base accounts, eligible combinations and frozen Coin sensitivity accounts.
- Clean measured Git source, full input/protocol/spec hashes, complete known execution, ledger audit and measured backup checks; no overwrite or source relabeling.
- Calibration cutoff2022-01-01, future observations excluded; actual accounts rerun, no curve scaling/splicing.
- No credentials/account/order/transfer/setting requests; public inputs and synthetic actual-session exchange only.
- No new runtime dependencies, daemons, force push or destructive history; progress only existing PROJECT_STATE/HANDOFF.

## Review Focus

- A protection exit and same-day late fill must not permit re-entry or double allocation.
- Core/tactical simultaneous intents and fees must conserve real pool without loan or ownership mixing.
- Checkpoint replay, failed observation or unknown order must not advance allowance/stop/cash.
- Unpublished/future calibration, rolling trigger inputs or offline protection amendments fail closed.
- Instrumentation/no-op baseline must preserve clock, fill path and immutable financial inputs.

### Task1: Coin mechanisms, causal event journal and reuse of real measurement engine

**Files:** create research/alpha_perp.py and tests/test_alpha_perp.py; modify shared pure code only if required for a reviewed seam, preserve existing default.
**Consumes:** complete_perp.ResearchExchange/variant/session runner, original market/prints/FX, frozen JSON spec.
**Produces:** CLI python -m research.alpha_perp --out FILE [--limit N] [--candidate NAME] [--scenario NAME] [--risk-calibration FILE] [--combo COMPONENTS] [--initial-cny VALUE] [--start-offset-ms VALUE] [--restore-prints]; source-bound JSON or lossless .json.gz with nested results candidate/scenario compatible monetary rows and causal opportunity_ledger. Inputs explicitly bind spec/protocol, component/risk/capital/starts and measured source. Full primary matrix default includes all5x4.
- [x] Read actual call paths and add meaningful tests for rolling prior-only trigger, stale/chase entry, primary-only monotone stop and through-mark exit, confirmed top-up allowance/unknown recovery, checkpoint identity and no-op baseline.
- [x] Implement exactly four variants and instrumentation with scoped hooks restored finally, no extra adapter calls. Reuse old measurement/audit; do not copy an exchange or change old candidate list permanently.
- [x] Ensure unchanged incumbent actual three-session monetary/fill/daily prefix versus old complete_perp; include generated incomplete smoke only in /tmp.
- [x] Run focused tests/compile, commit clean source. Write report with commits, exact tests, smoke evidence and limitations, no subagents.
- [x] Independent spec+quality review from BASE..HEAD diff and report; address material findings before completion.

### Task2: Spot mechanisms, independent core subpools and causal journal

**Files:** create research/alpha_spot.py and tests/test_alpha_spot.py; only smallest shared seam if necessary, preserve default consensus.
**Consumes:** complete_spot.measure/Policy, HistoricalVenue, session/Lifecycle, Model/follow, actual cached allocated fills and anchor.
**Produces:** CLI python -m research.alpha_spot --out FILE [--limit N] [--candidate NAME] [--scenario NAME] [--risk-calibration FILE] [--combo COMPONENTS] [--workers1|2]; source-bound results candidate-scenario and opportunity_ledger. Default full7x4 and same monetary/audit schema.
- [x] Pin re-entry confirm/count/actual-exit/new-day gates and partial/unknown behavior; target participation existing material bulls only, one confirmed daily add, exits first.
- [x] Pin causal ATR close vs ATR stop separate, monotone native stop, current fill peak and no unattended actions.
- [x] Implement research-only sleeve200 and independent20/80 initial cash subpools, fee/dust conservation, separate tactical consensus and core intents, new-day restart, core0 no-op and mode-bound checkpoint rejection.
- [x] Prove current consensus three-session no-op equality and exception hook restoration. Run focused tests/compile; commit/report and independent spec+quality review.

### Task3: Shared diagnosis, risk calibration, full-matrix selection, combination and forward tools

**Files:** create Spot research/alpha_assessment.py, tests/test_alpha_assessment.py and research/alpha-forward-GUIDE.md; use original complete_assessment canonical/attribution helpers. Small mirrored reader/calibration interface if needed in Coin.
**Consumes:** raw complete matrices and SHA-bound risk/sensitivity/combo outputs fromTasks1/2.
**Produces:** python -m research.alpha_assessment --spot FILE --perp FILE --out FILE [--calibration-out FILE] [--risk-spot FILE] [--risk-perp FILE] [--combo-spot FILE] [--combo-perp FILE]; all-candidate metrics, causal reason/exit event diagnosis, training-only fixed scales, conditional alpha/beta classification, mechanical choice and compatible combo list. Strict schemas/input identities; standalone export CSV/MD/plots and hash-bound all-cash forward initialization/append observed public bar interface.
- [x] Test exact missing/incomplete matrix rejection, mismatched source/input/candidate/starts/capital, calibration independence from postcutoff mutations and bad validation-risk match labeling.
- [x] Implement past-only calibration and achieved match checks from actual rerun; no curve scaling. Diagnose post-event5/20-day outcomes with explicit nonrealizable labels. Separate full and2022+statements, fees/funding, year/concentration, continuous/daily DD and source identity.
- [x] Pin all-match comparison against consensus/incumbent and deterministic compatible combination (core exclusion/tie slow), no hidden grid or strategy search.
- [x] Add forward artifact source/spec/baseline SHA and observed timestamp checks, initial all-cash/no fake elapsed days. Run relevant tests, commit/report; independent review.

### Task4: Freeze, measure all accounts, inspect completed evidence and adopt eligible code

**Files:** immutable evidence/alpha-beta-next-20261002/*, selected minimal runtime changes if any, current README/AGENTS/PROJECT_STATE/HANDOFF and reproduction guide.
- [x] Freeze all implementation/evaluation source before full runs. Run every48 single case on exact original public inputs; preserve failed cases, repair proven implementation defects and rerun affected complete accounts with source provenance.
- [x] Verify baselines against originals, complete real session/archive gates and independent funds. Prepare training-only calibration and run all10 complete new-candidate base risk-account replays.
- [x] Run prescribed eligible compatible combos in all4stresses and incumbent/finalCoin9900/10100/start+/-60s sensitivity accounts. Do not skip registered single directions or turn diagnostics into optimal-capital search.
- [x] Independently review cash/fills/funding/daily/continuous proxy risks, causal gates, risk-calibration chronology, selected choices and all descriptive claims.
- [x] If eligible, move selected minimal logic into shared default path with complete executable equivalence, state migration rejection and mandatory safety tests; otherwise preserve default and document all rejection reasons.
- [x] Retain complete public raws/review/SHA manifests (exclude self/progress/cache), final attribution/CSV/chart, initialization only forward ledger and full reproduction commands. Preserve original targets, original measurement identities and native0/actualdays0.
- [x] Run appropriate final local checks, normal branch push and independent whole-branch review; exact-head CI then normal PR integration, mainCI, clean worktrees. No additional permission for already-authorized normal integration.
