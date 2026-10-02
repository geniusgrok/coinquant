# Task 3 fix-round 1 independent review

FIX_BASE `ad0102c447c0f9b45f4566ca5f6dbe07601284cc` → FIX_HEAD `b5f7dbf800dd1a88409f68eed6c6a36f0e9c9553`.

**Spec compliance: PASS for the scoped fixes. Code quality: APPROVE. No remaining blocker found in the five findings, invalid-base ruling, or their direct regressions.** This approves the reviewed assessment source for the controller's next verification/measurement stage; it is not financial acceptance, default promotion, or native qualification.

Read the report addendum and entire636-line fix diff, relevant current assessment code, original meter timing code, and retained original/prefix evidence. No implementation/source edits, financial replay, public download, account operation, or child agent.

| Original finding | Verdict | Evidence |
|---|---|---|
| 1. Approved Spot original rejected at300.199s | ADDRESSED | `verify_spot_timing` checks the original200ms read /1000ms write semantics and exact clock arithmetic. Writes must be dispatched before deadline, remain serialized, and finish within the recorded session. Longer endings require an actual qualifying write receipt. Independently ran all four approved Spot original gates successfully; focused boundary tests reject late dispatch, unsubstantiated overrun, changed latency and clock. No original bytes changed. |
| 2. Unpinned original reference/provenance | ADDRESSED | Both approved raw digests are checked before source/comparison work. Coin original input SHA, derivation method, unchanged incumbent rows and row bindings are verified. Both exact originals pass; independently serialized substitute copies fail the approved-immutable-reference check. |
| 3. Incomplete baseline evidence equality | ADDRESSED | Six groups now cover financial/audit fees, fills/funding, daily, ownership, operating and remaining original fields. The baseline gate requires every group; unity controls also require full equality and freeze requires their pass. Independent original status/cycle mutations change fingerprints; focused tests cover fees, clock, client payload, ownership, allocation status and fill size. Retained Spot historical prefix, Spot filled core0 synthetic prefix, and Coin historical prefix match all six groups exactly. |
| 4. Sibling-dependent CI test | ADDRESSED | Outage test uses a local synthetic795-start fixture with six outage starts. Exact FIX_HEAD archive without Coin/Star siblings passes all21 assessment tests. |
| 5. Lost sizing and Coin decision gap | ADDRESSED | Compact decimal quantity summaries retain actual Spot quote/quantity/price fields and Coin desired/accepted sizes, with semantic links. Coin recorded trigger/decision prices now contribute to gap summaries. The regression distinguishes1000/100 from999999/1 sizing and verifies the100→120 gap and actual fill size. No adapter calls are added. |

The invalid-base contract is also **ADDRESSED**. All ten direction obligations remain inventoried. Independently invalid candidates are explicitly inapplicable with no invented profile/performance; otherwise-valid candidates remain pending when their contemporaneous baseline is invalid. Every valid candidate requires an actual calibrated account and each valid baseline a unity control. Missing profiles now produce a controlled error. Explicit rejected/inapplicable inventories may close a report while invalid measured accounts keep `all_measured_accounts_valid` and `rules_freeze_ready` false. The controller confirmed that when all candidates are independently invalid, closing that rejected inventory is intended; invalid baselines cannot exempt otherwise-valid candidates.

Reviewer-run verification:

- `python -m unittest tests.test_alpha_assessment tests.test_complete_assessment tests.test_alpha_spot`:49 tests passed,1.731s.
- Isolated `git archive b5f7dbf...` checkout, `python -m unittest tests.test_alpha_assessment`:21 tests passed,0.173s; no sibling repositories.
- Independent read-only original schema/gate checks: approved Spot SHA `cf075b86ba5df590e078a7c626c53cb20937be955cfb6ad8d41eae19b78645e8` and Coin SHA `15dd7bfc242d52bf692663179cd1e3867418f8b55a4cad0894d253a8b296f00a`, all four cases and all six self-evidence groups pass for each. Raw substitutes fail. Session status/cycle mutations are detected.
- Independent reading of three retained old/new prefix pairs: all six evidence groups equal; both Spot pairs also pass timing checks. No new prefix replay was run.
- `git diff ad0102c... b5f7dbf... --check`:pass.

During review the controller committed progress documentation as `8ca002522fbdce531dcfbbb783ff4d152a7fd66c`. Verified there is no difference from FIX_HEAD in research/runtime/tests; the scoped source judgment remains fixed to b5f7dbf. The controller separately reports192 full-suite tests and compile pass; those are controller evidence, not a reviewer-run remote CI result.

Limits: original self-comparison and retained prefixes establish schema/evidence compatibility and these fixes, not equality of unrun full new accounts. Full financial matrices, calibrated reruns, selected combinations/sensitivities, full-scale memory and final financial review remain controller-stage work. Archive proof checks use the producer's recorded verified flag and digest; this review did not reconstruct historical SQLite archives. No new concern requiring expansion beyond the scoped fix review was established.
