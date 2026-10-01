# BTC Complete Delivery Implementation Plan

> Execute tasks directly under the user's all-scope instruction; use
> superpowers:subagent-driven-development for isolated research implementation
> and independent review. Repository PROJECT_STATE.md remains the recovery ledger.

**Goal:** finish two usable development projects and every registered improvement
experiment with auditable decisions and source-bound evidence.

**Architecture:** reuse existing session/Lifecycle and market adapters; candidates
are research-only variants until complete comparable results pass the protocol.
Persist financial evidence in existing SQLite state and immutable artifacts.

**Tech Stack:** Python standard library, SQLite, existing Star research dependency.
**Spec:** research/complete-delivery-PROTOCOL.md and Spot matching protocol.

## Constraints and review focus

- BTC only, original capital/window/targets, finite manual sessions, no account use.
- Unknown transport/order/history never becomes zero balances or resend permission.
- Snapshot timing, future funding, daily-stop order and FX causality must be checked.
- Incremental cursors cannot omit same-millisecond fills or reset money anchors.
- Native evidence must bind actual IDs, code, account, environment and source files.

## Task 1: registration and market inputs (controller)
- [ ] Commit matching protocols before candidate outcomes.
- [ ] Restore official frozen spot daily data and build lagged funding/daily basis
  artifact from checksum-verified published archives; retain SHA and availability.

## Task 2: spot accounting and recovery (controller)
- [ ] Add persistent fill ledger and overlap watermark in execution.py, reused by
  follow/session; tests pin late fills, mutation, external trades and rollback.
- [ ] Add immutable session reports plus online backups in state.py/session.py;
  read-only restore-check reports without account adoption or state reset.

## Task 3: complete perpetual candidates (research implementer)
- [ ] Implement research/complete_perp.py using real session and protocol variants.
- [ ] Add causality/short/size tests; commit clean source, smoke then full matched
  accounts; preserve each raw complete result and independent accounting checks.
- [ ] Write task report /tmp/btc-complete-perp-report.md with commits and results.

## Task 4: complete spot candidates (controller)
- [ ] Implement research/session_account.py and research/complete_spot.py using
  session.run/Lifecycle and explicit historical price/stop assumptions.
- [ ] Test money/causal boundaries, commit source, full matched accounts and audits.

## Task 5: native evidence and cross-project analysis (controller)
- [ ] Implement source-bound archive validator and immutable native case report;
  synthetic data cannot establish native closure.
- [ ] Generate return/exposure attribution, passive controls, fixed-capital splits
  and Star first-divergence diagnostics with uncertainty/coverage visible.

## Task 6: independent review and integration
- [ ] Review complete diffs and protocols, fix material findings, run final suites.
- [ ] Update README/PROJECT_STATE/HANDOFF and existing PR descriptions, push and
  verify CI on submitted heads. Normally merge reviewed passing PRs, verify main.

Only actual evidence sets task completion. Failed candidates yield explicit
rejection; unavailable native data yields unverified, not a fabricated pass.
