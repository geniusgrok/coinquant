# Independent Task 3 review — Spot edge mechanisms

## Verdicts

**SPEC: PASS** for the Task 3 implementation and verification scope.

**QUALITY: APPROVE**.

No Critical, Important, or Minor findings identified in the reviewed patch. No corrective change is requested. This approval does not approve a financial outcome, default adoption, or native execution.

## Immutable review scope

- BASE: `bdde051095453cbb32163b7a9913df208a52f0f2`.
- HEAD: `6eb9474cf50f8d00de06e5e727235f31b812853d`.
- Reviewed `task-3-review-package-final.diff`, containing only `research/edge_spot.py` and `tests/test_edge_spot.py`.
- Independently compared the package SHA256 with the actual two-file BASE..HEAD diff: both `56d18c8f599c0db220ae9b28e99daab292f7e92a896f7ae07be20255e473e4cb`.
- Read the review brief, full implementation brief including the final closed-dust/source rulings, Spot AGENTS, frozen edge spec/protocol, and implementation report. Inspected the actual incumbent preview, session, execution, follow, complete meter, source identity, feature-reader use, and relevant tests.
- The reported shared-index sequence is preserved: implementation in `ddccd6074f773e7b0aaf2d4e8a17682bccc95599`, followed by the implementation author's dust-protection correction in review HEAD. This review does not relabel earlier receipts.

## SPEC evidence

### Decisions and protection

`previous_sma` (edge_spot.py:85) uses the previous close's own window. The scoped position wrapper (182–205) delays only the ordinary bearish SMA exit when the previous close is strictly above that SMA. Equality and missing history preserve the original exit. It does not change the underlying bullish vote. Repair/adverse/extended/breached/through-close and native-floor conditions retain priority; the original through-current-mark reduction pass still runs after the wrapper. The focused tests exercise these branches and the bearish vote's effect on another sleeve's allocation.

The stop-budget path (105–147, 226–243) accounts for the whole marked cash/BTC account, checks position quantities against ownership, and uses attributable active allocated native protection with remaining executed quantity. Missing ownership/protection and wholly unprotected dust block new risk. Covered sub-step rounding residual is retained and charged at full mark. The proposed loss reserve conservatively takes the larger of proposed stop distance and fill-based trail distance, then adds fee, entry/stop slippage, and tick reserves. The result only reduces the canonical proposal and is floored before minimum-notional handling.

The actual canonical portfolio creates **one pooled BUY** for all entering sleeves (`preview.portfolio`, then `preview.decision`). Thus this implementation applies the risk limit once to the aggregate new proposal; there are no independently proposed BUYs reusing the same remaining risk in the real path. This conclusion comes from the call chain, not an assumption about the loop. Held quantities at or above BASE_STEP are blocked; active smaller positions remain blocked. Re-entry through retained closed dust requires the original dust flag, applied-sale proof, and `_owned_dust` marker. The original follow retains ownership and weighted cost basis.

Crowding consumes the pinned FeatureBook only on a genuine BUY and at `venue.now_ms` (244–261). Each lookup is copied before the next overwrites `last_lookup`. Both thresholds are strict and combined with completed five-day weak momentum; known zero is not treated as missing. Future/incomplete history and missing/stale features suppress only the proposed new risk. Existing safety reductions execute first. No extra adapter requests or waits are introduced.

### Actual controls and money

Controls use the same finite meter, Lifecycle, ownership, original checkpoint/new-bar gates, and actual fill accounting. The declared fraction applies to then-free cash under the whole-account capital ceiling (222–225). Controls retain static 28% trailing protection, use unconditional legal entry, and explicitly differ from the ATR/SMA/adverse/repair policy. They are not maintained constant weights. Actual cached stop fills determine the completed-day re-entry gate (173–181); repeated polls cannot re-enter the stopped campaign on the same completed day. Native fill allocation and retained residual handling stay in the existing follow code.

The synthetic finite-account test independently rerun in this review exercises cash plus 25% and 100% controls, an actual stop, a same-day observation, and later re-entry. Both funded controls have exactly two BUYs, real fees, a filled first stop and a currently active stop; the first stop is 72.03 for the scenario's actual fill. This provides branch evidence beyond the short original-market CLI receipts.

### Identity and recovery ordering

`configured` (287–343) binds candidate/components, edge spec, complete risk profile/file hash, consumed feature bytes, and executable Python digest in both durable account identity and model checkpoints. Its guard calls the original strict guard, which restores/validates models and pending allocations before Lifecycle creation/recovery in `session.cycle`. The independently rerun test spies on the actual `Lifecycle.recover` call and verifies it is never called for unbound, wrong-rule, wrong-profile, wrong-checkpoint or wrong-source state; database contents and sent orders remain unchanged. This is not merely a late restore failure.

Hooks are restored in `finally` both around per-decision substitutions and the outer meter/configuration scope. The failure tests exercise both seams. The canonical producer is not edited. Serial/process-isolated use remains required and disclosed.

The CLI validates strict project-specific calibration document/profile fields, duplicate keys, finite string scales in [0,1], cutoff/training boundary, spec, registered candidate and baseline/source-artifact binding. Baseline scale must be exactly 1. Candidate scaling is applied to actual new BUY orders only at/after the cutoff. Old calibration validation is untouched. The new baseline profile is validated separately, while the baseline delegates to unchanged `complete.measure(...canonical=True)` without passing a new profile into the old validator. Fixed-budget baseline uses the existing `initial_cny` parameter.

### Evidence and CLI

The baseline test compares direct `adoption_spot.measure` and the edge no-op with every existing `evidence_fingerprints` group, including operating and remaining original fields, and separately checks incumbent research identity. The new mechanisms/controls only add the named `research_identity`, `opportunity_ledger`, and `risk_calibration` row fields; other provenance is in the top-level edge envelope.

CLI source must be committed/clean; candidate/scenario/component and allowed capital/partial-limit inputs are checked. Partial output is restricted to `/tmp`, exclusive creation uses `xb`, and gzip output is deterministic. Original schedule, market, FX, and original meter fields are retained. Source, spec/protocol, risk profile, and supplied feature identity are rechecked before output. The retained baseline overwrite rejection is documented; this review did not overwrite any receipt.

## Independent verification performed

1. `python -m unittest discover -s tests -p 'test_edge_spot.py' -v`: **13 tests passed in 5.334s**, exit 0. No full financial producer or Coin job was run. The implementation's 261-test full-suite result was read from its report/log context, not independently rerun or claimed as this review's execution.
2. Read/decompressed **all ten final CLI output files**, recomputed each compressed-file SHA256 against the final manifest, and checked exact clean review-HEAD bindings, original row field presence, incomplete status, null CAGR, and absence of pending/unresolved sessions.
3. Independently reconstructed each receipt's cash and BTC from actual initial CNY/FX/conversion and every fill/commission, rather than relying only on `audit.passed`. All ten matched retained terminal balances. Verified current spec/protocol/schedule/FX byte bindings and market digest against the retained report hashes.
4. For the two original-market control receipts, independently checked the sum of durable sleeve positions against actual net BTC, the allocated active native stop, exact floor-rounded 28% stop from actual entry fill, and retained sub-step rounding residuals. The 25% control spent **358.75 USDT**, paid **0.35875 USDT-equivalent** BTC commission, and retained **0.05146288774911069304167498797 BTC**. The 100% control spent **1435.03 USDT**, paid **1.43503 USDT-equivalent** BTC commission, and retained **0.2058558545131883423988706843 BTC**. Both installed a **5014.13** stop owned by sleeves 30/40/50. This is actual finite execution, not a fractional equity curve.
5. Inspected actual session clocks: base receipts keep starts 1577836800000 and 1578006000000 and end each session 300000ms later. Funded control sessions have fewer poll cycles because real execution consumes simulated latency. The producer's original archive verification call and retained archive hashes/fields remain present; temporary archive databases were not independently reconstructed from the compressed rows.

## Limits and remaining work

- These short original-market receipts are incomplete. Baseline/mechanisms remain flat and the crowding receipt contains **zero real feature lookups**. The meaningful new-entry, missing/stale, and actual-clock branches are established by focused tests, not by those receipts. This limitation is accurately disclosed in the implementation report.
- The fee150/slip2/outage CLI receipts each cover only the first start. They prove CLI/scenario wiring and retained identities, not stressed invested behavior or the later outage interval. Complete registered financial measurements belong to later tasks.
- Source-artifact hashes in risk profiles are binding references; downstream assessment must verify the referenced complete account and training formula/provenance. This review does not claim those future documents exist or have been financially validated.
- Stop-budget can remain unable to add risk after a stop leaves wholly unprotected owned dust. That is the frozen conservative missing-protection rule, not permission to delete the residual.
- Full-window economics, complete baseline equality, candidate eligibility/combination selection, adoption, prospective alpha, continuous-proxy limitations, and native qualification remain outside this Task 3 approval. No goals, gates, defaults, or ownership rules are relaxed.

## Findings register

Critical: none. Important: none. Minor: none. No finding IDs or fixes are required.
