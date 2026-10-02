# Task 1 fix round 1 — scoped independent re-review

Scope: prior two attribution findings and immediate regressions only, FIX_BASE `c2a01d1c7ad09d58001ec2897a5a64d1b8284dd6` → FIX_HEAD `31e8b1e2b3f286fe3f948b7e1c473328ffdfeafa`. Read the entire fix package/diff and report's final fix-round section; followed the affected session, macro selection, checkpoint and diagnostic paths. No source edits, financial reruns, account calls or children.

**Spec compliance verdict: PASS for Task 1 implementation.** Both previously open findings are addressed; the earlier mechanism review remains applicable.

**Task quality verdict: APPROVE.** No material immediate regression found. Later economic/calibration/qualification gates remain separate.

## Finding status

1. **Duplicate/backdated cycle failures — ADDRESSED.** `research/alpha_perp.py:309–318` retains one authoritative actual-time failure with session/cycle-sequence/phase identity. `record_session_phases` at lines 345–352 excludes duplicate cycle summaries and labels other phases as report-completion summaries rather than invented failure timestamps. The finite-session test exercises identical errors on cycles 1 and 3 with a successful decision between them; both remain distinct and correctly ordered. Rechecked the saved real-prefix comparison: all 14 cycle failures have unique identities and actual post-start times, no `session_error` copies remain, and the ledger is sorted chronologically.

2. **Missing macro provenance — ADDRESSED.** `research/alpha_perp.py:124–135` records successful macro creation once, preserving the original mark and a deep copy of the observed DFII10 row. Lines 159–202 hash-bind and restore the provenance and reject missing/mismatched macro identity. Lines 267–274 attach immutable provenance and actual decision age. The new real Lifecycle fixture verifies repeated polls, changed later observations/prices, owned decisions and another session do not rewrite or re-emit creation. Independently checked delayed geometry: an earlier negative epoch remains unchanged when geometry becomes legal later; `created_at_ms` records that later successful creation, survives restore, and produces one event. This distinction is causal and does not alter trading identity.

   Diagnostics at lines 415–425 remain post-execution only. Each 5/20-day horizon is based on successful creation time and uses the last completed four-hour close at or before that horizon, reporting both timestamps. Primary boundary-aligned horizons retain their prior price semantics. The diagnostic fixture verifies price access occurs only after execution returns.

## Evidence and immediate effects

- Independently reran `python -m unittest tests.test_alpha_perp -v`: **13/13 passed**, including original no-op calls/writes/clock/balances/fills and mechanism tests. Full fix-range `git diff --check` passed.
- Re-executed `/tmp/task1-fix1-compare.py` against saved real three-session artifacts: **26 original non-session fields and all session summaries equal**, two fills, three daily rows, audit passed. Monetary SHA-256 remains `1889de3d0f75ee61fce760087ff4bb8ae32ab2d85b5a67bd147a48bea11606d2`. Output source is FIX_HEAD and dirty=false.
- No adapter requests or simulated clock advances were added. Precisely, line 396 adds **one passive `exchange.clock()` call per completed session** for report-summary time; `research/session_exchange.py:99` implements that clock as `self.now_ms / 1000`. Thus “no new clock calls” is not literally true, but the binding no-request/no-clock-change invariant holds. Macro attribution reuses existing observations.
- The reported 359-test exact-head suite and compile pass were inspected, not independently repeated. Old alpha checkpoints lack the new required provenance and fail closed; source binding already makes cross-source reuse invalid.

No remaining blocking or important finding in this scoped fix review. Full historical measurements and trained-calibration proof were intentionally not repeated and are not Task 1 defects.
