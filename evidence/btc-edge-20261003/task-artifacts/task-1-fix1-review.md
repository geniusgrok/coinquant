# Task 1 fix round 1 scoped independent re-review

Reviewed `task-1-review.md`, `task-1-brief.md`, the fix appendix in `task-1-report.md`, and the complete supplied `5e69b0c..fa81bf5` fix diff. Final Spot head is `fa81bf5dca86e96bbdd265174e2e3e31370c79d0`. Review scope is closure of original I1/M1 and new Critical/Important regressions introduced by this fix. The controller's progress-ledger change is present in the supplied diff; the implementation commit changes only the diagnostic module and tests.

**Spec compliance verdict: PASS for the scoped fix; APPROVE.**

**Code-quality verdict: APPROVE.** No new Critical or Important regression found in the fix diff. The event-aware provenance table is small and directly matches the accepted producer's recording order. Existing evidence limits keep the task's overall status **DONE_WITH_CONCERNS**, without an outstanding review blocker.

## Original finding verdicts

### Important I1 — ADDRESSED

At `research/edge_attribution.py:235`, decision `action`, `reason`, `quantity_after`, `constraint`, and `error` are explicitly post-return/failure summaries. At lines 312–324 their exact differences remain intact, but those fields are excluded from `operational_fields` only for the appropriate event type. Each excluded difference records how it was populated and `available_at_ms: null`; no completion time is invented. Opportunity horizon closes retain their separate post-run provenance.

I inspected the frozen accepted Coin producer at `acedaa43ca94223f24e2fe11851bbef74e032a69:research/alpha_perp.py`. It timestamps and appends the decision before `original_decide`, adds action/reason/quantity/constraint after return or reason/error after a RECOVERABLE failure, records entry/top-up sizing after the preview completes using the then-current reader clock, and records writes before sending. The fix leaves sizing constraints operational at their own recorded timestamps and leaves write payloads operational at their actual write timestamps. Removing action-based decision category selection avoids using a later exit/top-up summary to label an earlier observation difference.

The synthetic regression at `tests/test_edge_attribution.py:142` has identical initial decision inputs and different later summary/sizing constraints. It covers both entry and top-up sizing, keeps the decision's exact constraint difference visible, and requires the first operational divergence at sizing time 120 rather than decision time 110. The additional test at line 160 covers all five decision summary fields and a failure summary. The existing quantity-after regression remains.

Selective v3 inspection confirms the original real examples:

| Shift / opportunity | Decision comparison time | Actual sizing comparison time | Result |
|---|---:|---:|---|
| −60s / `1602172800000` | `1602215943000` | `1602215945800` | `target → liquidity_cap` is exact/provenanced on decision and operational on sizing |
| +60s / `1687291200000` | `1687500003000` | `1687500005800` | `liquidity_cap → funding_cap` is exact/provenanced on decision and operational on sizing |

Both sides' raw times and numeric strings remain present. A selective scan of all 168 retained decision traces found none of the five summaries in operational fields. The unchanged first whole-account observation conclusion remains supported. Revised first-opportunity categories are −60s: 52 different observations / 1 prior-equity propagation; +60s: 53 different observations. The superseded v2 exit labels are explained in the appendix rather than presented as unchanged final evidence.

### Minor M1 — ADDRESSED

At `research/edge_attribution.py:266`, a sole write `payload.quantity` difference receives `requested_size`. Lines 329–335 also retain that facet when another field determines the primary category and explicitly set `upstream_cause: unknown`. This identifies the known requested order-size difference without assigning an unsupported sizing explanation.

The synthetic assertion at `tests/test_edge_attribution.py:175` changes only the requested write quantity, verifies its exact value and facet, and verifies the unknown upstream cause. The reviewed +60s macro opportunity with original ID `-1700643602800` now retains exact `1.606 → 1.861`, category/facet `requested_size`, and upstream cause unknown at actual write comparison time `1700643607800`; its later-shift raw write time is also retained as `1700643667800`.

## New findings in the fix diff

- Critical: none.
- Important: none.
- Minor: no additional finding raised. Unchanged matching/ownership/evidence limitations remain outside this fix re-review; any broader observations are deferred, nonblocking Minor scope.

## Verification and evidence boundaries

Inspected the meaningful synthetic test changes and the recorded red/green evidence: the fix report and acceptance receipt record four reproduced pre-fix failures and **17 passing attribution tests** afterward. The earlier full-suite evidence remains as assessed in the original review. I did not rerun tests, the acceptance verifier, the diagnostic producer, any financial producer, or any native request.

Independently checked final worktree/module/test identities and the new v3 JSON/Markdown and receipt hashes through read-only file inspection:

- Module SHA: `4f7d32f57dc44a5594d042b8dcd1ce529fd60831cab2397069c02fb98c4b369d`.
- Test-file SHA: `0405b973d78df857e1a5abe2f5348c36016f9839232ab5e768b9f57904000393`.
- v3 JSON SHA: `02948e9026ed77bb43af02da9cbe04bbfbce564b826a7ffbe8187c5008f81b96`.
- v3 Markdown SHA: `832c1f82c9552f0cbb02add9a96e7f7f8638b5c2ae021b4ad70d6559ae6b564d`.
- Fix acceptance receipt SHA: `d63f04928281a98142d4c0054565f6c7c1fa861313082e1eb5283bdf26285117`.

The receipt binds final source/output identities, records all 11 input hashes reverified, unchanged v1/v2 output hashes, overwrite rejection and no financial producer execution. Its retained verification script checks the two real I1 sizing examples, the real M1 write and the decision-trace count. My selective inspection agrees with those specific final-output checks. No earlier evidence was overwritten.

Opportunity occurrence pairing, incomplete ownership, unknown summary completion times, prior equity propagation, mixed observation/state causes and lack of a same-observation counterfactual remain explicit. Original unmet economics, historical contamination and zero native cases/actual account-days are unchanged. This approval closes I1/M1; it establishes no execution-dependence fix or prospective/native qualification.
