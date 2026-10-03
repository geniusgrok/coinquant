# Task 5 fix2 scoped independent re-review

T5-R3: **ADDRESSED**.

SPEC: **PASS** for this scoped fix.

QUALITY: **APPROVE** for this scoped fix. No new Critical/Important finding.

## Scope and immutable evidence

Reviewed only T5-R3 and breakage introduced by `73a0baf5702fce5bed23205c245aab53fad951b9..e910189daae036cc3978173934c472862405bc8a`, including both own commits `ddfd1b7126fe4a2866878f1b3a772c5c3868dbc3` and `e910189daae036cc3978173934c472862405bc8a`. Only the assessor and its test file changed. T5-R1/T5-R2 were already ADDRESSED; this was not another whole-task review.

Read the fix2 rereview brief, fix brief, prior T5-R3 finding, complete fix diff and appended report. Actual hashes match root's bindings:

- Fix package: `79ce99f9eb2bbae37a6eee213e0ae2fba2f83cdf8b1e52af417365a88511ad04`.
- Implementation report: `35c2eca20941e0e995182b00c0b3a1df7f53f157197bd2a1d871f1ac2605e8af`.
- Final covering log: `752362161bf48ab982c4370ccf86ebf25ec89fedd34249ffa64fcd16389d6237`; recorded 31 tests, OK, 40.007s.
- Final-source receipt: `afa10eacfc1be44d29b198fda23f4eebed6271621778244b4ae099f8cb5f23cb`.
- Updated schema examples: `c93bc579fbac00abdaa01dc4f201c737166215d7ad08f51fa90d9c14712d41b6`.

Spot HEAD is `e910189daae036cc3978173934c472862405bc8a`; Coin remains `e9c2b4c5c962c3fa1dc62a25826745ad18d79f2b`. No source/HEAD change, commit, subagent, Coin test, full producer, native/private/account action, or HOME/UID/lock change occurred during this re-review. Only this report was written persistently; probe proof files used an automatically removed temporary directory. Unchanged test suites and the retained baseline/smoke verifier were not rerun.

## T5-R3 resolution

The new `gate_inputs` is retained for every complete account before raw rows are stripped. It contains the exact original-file SHA and six explicit gate values; MDD remains the original finite Decimal string. `gate_values()` validates its exact fields/types, rejects bool-as-numeric/nonfinite/wrong raw binding, and compares against original row/statistics whenever the row is available. The final fresh assessment reconstructs the binding from each original input, rather than trusting a preliminary report supplied by the reviewer.

Both the main `decisions_for()` and `review_expectations()` now call this same helper for every unscaled stress and for the actual calibrated candidate/unity MDD fallback. No adoption comparison still substitutes `metrics['continuous_mdd_from_account']` for the exact value. The descriptive float metric can remain in ordinary output without affecting these gates. The account evidence checksum already binds the full retained input; accounting, actual-risk and adoption proof records now expose exact MDD/input values for independent raw comparison.

The patch does not change financial thresholds, introduce a tolerance, round the main gates, or weaken typed-proof coverage and missing-daily guards. Removal of the interim extra schema range restriction avoids adding an economic gate to a structural validator; the existing registered validation/gates remain authoritative.

## Independent precision probe

Ran one minimal pure computation using `complete_review_fixture()` only as a synthetic 68-account data constructor, not as a test-suite invocation or actual financial inventory. Set Spot baseline MDD to `"0.31"`, exit-confirm base MDD to `"0.30000000000000001"`, and kept the corresponding display floats `.31` and `.3`. Recomputed the primary decisions through `decisions_for()`, then generated expected category records with `review_expectations()`.

Wrote the complete synthetic preliminary and all six proof categories to a temporary directory, binding exact bytes and inventory. The independent reviewer-source check used the real current clean committed source and was **not mocked**. As in all synthetic contract probes, matching generated expectations proves the automatic consistency interface, not substantive independence or real account performance.

Observed:

```text
EXACT_NEGATIVE False False
PROOF_MDD 0.30000000000000001
FULL_SIX_CATEGORY_PROOF_ACCEPTED True
ROUNDED_SUBSTITUTION_REJECTED review recomputation mismatch
```

The first two booleans are `base_improvement` and `eligible`: both remain correctly false. For the final line, only the proof's precise MDD was changed to `"0.3"` and its artifact hash recomputed; the validator still rejected the mismatch. This directly resolves the previous false rejection while preserving exact proof comparison.

The added covering tests separately exercise both projects' actual calibrated `.31` versus `.30` equality and `.30000000000000001` just-fail boundaries, and Coin strict `.49999999999999999` / `.50` / `.50000000000000001` cases. Their primary decisions and proof expectations use the same exact values. Existing proof coverage and missing-daily tests remain in the recorded passing 31-test run. The final-source receipt retains eight accepted baseline checks, 17 solely incomplete pending smoke accounts, zero new producers, exact original gate identities, and rejection of the original terminal-only snapshot counterexample.

## Limits

No additional scoped Critical/Important issue was found. This approval closes T5-R3 and does not claim the actual complete 68+ inventory, real calibration reruns, substantive independent financial review, adoption outcome, or native qualification. Those remain root's later work. Existing BTC/economics/session/FX/cost/funding/ownership/no-topup/no-short constraints, original goals, historical proxy/contamination disclosures, native cases0/actual account-days0/NOT_QUALIFIED remain unchanged.
