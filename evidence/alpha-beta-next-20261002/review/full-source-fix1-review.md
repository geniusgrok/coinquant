# Broad source finding — scoped fix re-review

Reviewed 2026-10-02 in isolated analysis checkout `/workspace/btc-alpha-beta-analysis/spotquant`, FIX_BASE `8ca002522fbdce531dcfbbb783ff4d152a7fd66c` → FIX_HEAD `3d723fb5dd42ec38376f243d23ecb052b3212420`.

**Spec compliance: PASS. Code quality: APPROVE.** The broad review's P2 fill/opportunity handoff finding is **ADDRESSED**. The controller's narrow pre-outcome assessment-source equivalence ruling is implemented and verified. No remaining blocker or material direct regression was found in this scope. Together with the unaffected coverage in `full-source-review.md`, this closes the mandatory broad source review; completed financial evidence still requires its separate independent audit.

Read the full fix diff/package, task3 report's latest addendum, applicable AGENTS.md, the controller ruling in the existing PROJECT_STATE.md, and affected assessment/forward paths. No producer source, Git HEAD, raw artifact, strategy/default or account was modified.

## Finding closure

`research/alpha_assessment.py:371–425` constructs an exact client/write opportunity relation before fill compaction. `diagnose` now retains client ID, native order ID, resolved opportunity, link status and ambiguity candidates. Partial fills can use the same recorded client relation; a missing client can only use the unique client observed on another fill of that exact order. Repeated/unknown write observations remain observations and never become fills. Conflicting client or campaign evidence and unlinked exits remain explicitly unknown. There is no time-nearest or active-campaign inference.

Independently read the preserved real prefix `/tmp/task1-fix1-alpha-incumbent-3.json.gz` (raw SHA `83fddec3d87dd8bdba5dd0bc72f8a51a426557860d6fb2ab2b21b9716f7a55d3`) and applied the fixed assessor without replaying the account. The two BUY fills `0.002` and `0.964` now produce client `cq-2e9ee5b4d01a21dca7b7a725719665`, order2, opportunity `1578038400000`, total `0.966` BTC, and join the preserved entry-sizing opportunity. The raw measured source remains `31e8b1e2b3f286fe3f948b7e1c473328ffdfeafa`; no source relabeling occurred.

The new regressions use actual producer-shaped records and cover partial fills, repeated/unknown writes, exact-order client recovery, unlinked exits and conflicting client/opportunity relations. Existing Spot diagnosis and numeric fill summaries remain intact.

## Source-equivalence ruling

`verify_source` reconstructs each full recorded Python digest from its committed Git tree before returning per-path hashes. `verify_execution_equivalence` at lines114–132 validates both full digests first, requires exact committed spec/protocol bytes, then permits only the fixed Spot path `research/alpha_assessment.py` to differ. All other runtime/research Python paths and bytes, including additions/deletions, must match. Coin has no exclusion. No ignore-path option or source override was added; producer-to-producer `equivalent_inputs` remains unchanged.

Assessment generation proves the relation to measured Spot source and records the equivalence digest at lines798–808. Forward binding checks execution equivalence and independently verifies the entire current analysis executable against `report.analysis_source`, including the assessor. Coin forward additionally checks the Spot analysis helper tree against its measured source, so updating the advertised analysis hash cannot bypass changed shared helpers. Documentation-only HEAD differences are acceptable only with matching byte proofs. Frozen measured identities stay in their original fields.

Independently executed the real committed-tree comparison:

- Frozen Spot `8ca0025…` → analysis `3d723fb…`: only `research/alpha_assessment.py` differs among the proved Python/spec/protocol paths. Analysis full Python SHA is `f3ffe3422ea95726db95b76e8bfec485bac1d7b24ffed7fd010010fb58badbeb`; execution-equivalence SHA is `c2dd29733ec5bb96137a8ab27cc0e8dd604d74bf6d1e108d45a554b8923e6cf8`.
- Coin `acedaa4…`: no path differences; full Python SHA remains `a6e3f30f02208ff7e604b6181c5d8fa7000fe7e30dbc3276fbcc93ffbb0ad227`; equivalence SHA is `baa4266827026873dab75e8ec0814be69a93e256a103e6568578ebe1610079de`.

Temporary committed-tree tests exercise allowed assessor/document changes, wrong historical full digest, later assessor mismatch against an older final report, changed runtime/helper bytes, added/deleted helpers, spec/protocol changes, and Coin-forward attempts with changed Spot helpers. These tests passed in the reviewer run.

## Verification and limits

- Reviewer-run `PYTHONDONTWRITEBYTECODE=1 python -m unittest tests.test_alpha_assessment tests.test_complete_assessment tests.test_alpha_spot -q`: **51 passed**, 2.396s.
- Fixed BASE→HEAD `git diff --check`: passed. The entire commit changes only assessor, its tests and the forward guide.
- Analysis checkout research/runtime/tests are clean and HEAD remains `3d723fb5dd42ec38376f243d23ecb052b3212420`; the controller-owned PROJECT_STATE.md edit is untouched.
- Inspected the supplied exact-head isolated23-test result and source-proof artifact; did not repeat the isolated archive run because the full focused run already executed the committed-tree rejection fixtures.

No financial replay, new measurement, download, scan, account action, raw-artifact change, frozen-producer edit or subagent was performed. This approval does not establish full-history economics, baseline reproduction, achieved risk match, resource behavior, default eligibility or native qualification. The ongoing frozen financial runs and their later independent evidence review remain separate.
