# Task 7 Spot canonical preparation — scoped fix3 re-review

T7-CP-R1: **CLOSED / ADDRESSED**.

SPEC: **PASS for this scoped correction and preparation acceptance**.

QUALITY: **APPROVE for this scoped correction**. No remaining or new Critical/Important finding was identified. The previously deferred nine affected account checks are now covered by retained passing evidence. Actual financial and five-account canonical proof remain pending; this is not promotion approval.

## Scope and source

Reviewed only the changes since the previous independently reviewed HEAD `bd9fbc04813d29015c8231cdc63ec784d4a46256`: the T7-CP-R1 parser/provenance correction and its two new tests, followed by the partial-entry fixture correction and completed-check receipts. The prior report `task-7-spot-canonical-preparation-review.md` and its failing probe remain unchanged. No repeat whole-branch/18-file review, test run or new behavioral probe was needed.

Repository: `/workspace/btc-alpha-beta-canonical-prepare/spotquant`.

- Original BASE: `74bd6e035e36531c517029077c1a9e2e5ec44516`.
- Material fix2: `9797cfd9110286c5a9c10c00bb0a5dfd798d47c4`.
- Final reviewed HEAD: `609606d9c0e0ad8d3c3038b329c9c4ab6d1b9629`; clean worktree.
- Python SHA256: `b81f1bfee086e875cbf8ff22a67b2cfdff419130a7918a6ce8754b2e9e2936c5`.
- Protected archive bytes/modes SHA256: `eeb22cfe227c0d9ed60c937da330f515a6093dfcd82205114644e8bed8c7c7f6`.

Independently obtained current source/archive matches the final receipt. Runtime/research source is unchanged between fix2 and final HEAD; that final commit changes only the affected test fixture. Full BASE-to-final patch bytes match Git, but only the subsequent four-file correction was substantively re-reviewed.

## T7-CP-R1 resolution

`research/edge_forward.py:987` still validates raw receipt bytes, hash, endpoint and clocks through `payload` before parsing. At line990 the required Spot bars still use strict parsing. Only the added crowding funding/futures categories use the shared `spotquant.crowding.public_body` helper, which converts parser ValueErrors into explicit unavailable inputs. JSON decoding errors, invalid UTF-8, duplicate fields and prohibited nonfinite constants therefore reach `ObservedFeatures` as missing feature data instead of aborting the transition before safety processing.

Native successful-response parsing now uses the same helper and hashes the actual response bytes even when their content is malformed. `ObservedFeatures` records provenance before checking error status, so missing diagnostics retain URL, request/receipt clocks and raw hash. Valid-data predicate thresholds, availability, sizing and recovery were not changed by this fix. Corrupt provenance and malformed required Spot bars remain hard failures.

The two new tests are meaningful and bounded. Across funding and futures categories they exercise malformed HTML, NaN, invalid UTF-8 and duplicate JSON fields; check BUY blocking, missing causes, retained provenance and deterministic raw reconstruction; and invoke the actual shared preview to verify a safety SELL remains. The transition-order check uses actual receipt/bar handling and the corrected adapter, mocks unrelated book/FX readers, and stops at the passive safety handler. It proves that the formerly failing parser cannot prevent reaching that handler; it does not claim a complete financial ledger execution. The second test preserves hash/endpoint and required-Spot-bar rejection. Together with the unchanged safety path, these directly cover the reported defect without requiring an account replay.

Retained `affected-malformed-public-fix2.log` records both new tests passing once in Python3.13. No earlier passing case or original failing review probe was rerun here.

## Account fixture and completed affected checks

The nine reserved affected checks ran once on fix2: eight passed; only the partial-entry/restart/stop-amendment fixture failed with expected99.00 versus actual91.80. The failure log remains intact.

The correction in `tests/test_p4_execution.py:226` matches the unchanged `spotquant/follow.py:28` rule. A fill at day-open+60000ms falls outside the strict first-minute inclusion condition. The completed entry-day high110 is not proven post-fill, so the fill peak102 and10% floor retain91.80. The revised test explicitly asserts91.80, then supplies a genuinely subsequent completed day with high110 and asserts99.00. It retains the restart/no-duplicate-send checks, one active stop, offline-trigger reconciliation and no pending intents. This strengthens the causal fixture rather than relaxing the runtime stop rule.

Only that failed case was rerun and passed. Its recorded working-diff hash equals the final test-only Git diff. SQLite ResourceWarnings are retained; the assertions passed. The completed-check packet therefore closes the prior nine-case deferred list: synthetic canonical/research six-group equality, no research hooks, risk-profile guards/owned sizing, retained ATR baseline/budget, cold native entry, partial-entry/restart/protection, unknown-query identity recovery, forward conservation/checkpoint and forward rounding/depth/no-top-up sizing. These are synthetic affected checks, not the five full historical canonical measurements.

## Bound evidence

Files are under `task-artifacts/task-7-spot-canonical-preparation/`; actual bytes and indexed log hashes were checked.

| Artifact | SHA256 |
|---|---|
| `source-and-checks-fix3.json` | `309710ba4d667713f2c6fb2adb0fd36279e32745f7487aeacbcddf4065b6357c` |
| `affected-checks-completed-fix3.json` | `8148e5832e01d5e018afffeb5b20e7bc1728d91a201980ff282798b170e60274` |
| `base-to-final-fix3.diff` | `53cb7b1cebf0e1e69147baf0c3a362264b93707e4569567173c8b44bf97d506b` |
| `scoped-fix2.diff` | `a0db7f566c19d8c121e52366bd3180f4fd54da371b02cdb95771ea83489b00dc` |
| `scoped-fixture-fix3.diff` | `15d5191e37f3888efe0f6ba7f09a23c8b0e33257ba02dcd994d67e432545182e` |
| `affected-malformed-public-fix2.log` | `01437de755368ee5554629c974d7c63a98e249ac0811400c9486f843e01ac730` |
| `affected-nine-account-first.log` | `3c4da9b005a8720a7501ebfb7706e2f6d8e048daf765463ed5e87a5705383ba8` |
| `affected-account-fixture-fix3.log` | `378682cb705ef23fb59f3951d1af8224f9f972504e839b46a5a532a661458f1b` |
| `five-canonical-commands-fix3.json` | `2afa67613285f9f71a4311701d802d1e3df4983503c6967f91c707fee7bbfc6d` |
| Appended `implementation-report.md` | `a9a7180bdb3c42521fa1d31e2ce538429f94a653d4a9a71246e4490f63e44f74` |

The implementation report's original prefix still hashes to `b4e74552e2cdb975e53829e89b59d80332e578e697be7d47551d9c5fa48d3653`. All five command entries preserve their previously reviewed argv, original measured IDs/raw SHAs/envelopes and other expectations; only expected current source changed, and all five now match the reviewed final archive.

## Remaining acceptance gates

The code finding and nine deferred affected tests are closed. The following gates remain separate and pending:

1. Complete the original registered financial inventory and substantive independent financial proof, preserving original source/input/economic identities and all registered adoption/risk/budget gates.
2. Execute the five prepared full canonical historical accounts on the final bound source: base, fee150, slip2, outage and unity-risk-base. Independently establish complete audited accounts, verified archives and equality in all six original evidence groups under existing normalization, retaining original/current source identities separately.
3. Obtain the pinned independent canonical bridge and final financial proof before promotion/export/init; complete root's authorized integration and single final-delivery validation/whole-branch review. Actual future initialization still requires genuine allowed observations and fresh FRED pairing, with no retrospective backfill. HTTP451 may leave it market-pending.

No native qualification, prospective alpha, elapsed account-days, real observations or promotion readiness is established by this scoped approval. No source edits, account calls/tests, financial producers, fullsuite, public preflight, export/init, child agents, HOME/UID/lock changes or independent financial attestation occurred during this re-review. Only this new report was written.
