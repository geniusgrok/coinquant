# Conditional Spot adoption — scoped fix1 review

FIX_BASE `7ac94e12b41b9958072c9ff080983eea1a3cbd83` → FIX_HEAD `0c52c812301de3712f3637a1ce1b1241de0c40f1`.

**Specification: PASS. Code quality: APPROVE. Original P1 identity-schema finding: ADDRESSED.** No remaining defect found in this fix or its direct regression. This closes the earlier source-review blocker; it does not establish financial equivalence or authorize adoption by itself.

`research/adoption_spot.py:risk_identity` now emits all established atr-stop account identity fields: registered components, actual spec SHA, risk_scale, core_mode/core_fraction, candidate and exact calibration SHA. Existing rule/cutoff/scale/full profile/profile digest and canonical execution provenance remain explicit. No original row field was removed, no runtime decision logic changed, and no assessor/source/forward check was relaxed.

Independently ran the exact-head archive's11 focused adoption tests in a standalone temporary checkout: **11 passed in3.152s**. Log `/tmp/spot-adoption-spec-fix1-review-tests.log`. The new regression creates actual three-session canonical session/Lifecycle outputs for both unscaled and actual-file-calibrated cases, serializes them, and invokes the real immutable99 consumer. It verifies the exact assessor file SHA and performs real committed-tree source validation in an isolated temporary Git repository; only ROOT is relocated, with no identity/profile/validity gate mocked. Both cases now pass schema checks and retain only `measurement_incomplete`, valid=false. The exact calibration file SHA and full profile are checked. Existing local six-group equality and canonical hook-exclusion tests also pass.

Additional reviewer checks:

- Exact fix diff `git diff --check`:pass.
- `research/alpha_assessment.py`, registered spec and protocol remain byte-unchanged against analysis99.
- Current source identity: exact FIX_HEAD above, dirty=false, full Python SHA `619570fb7baa586f28ad5de2a440d7752a536cc8f8ce7e357264612e65801537`.
- The implementation report records209 full-suite tests and compile pass; those are implementer evidence, not repeated reviewer checks.

Scope was the original identity finding and direct regression only. No product/source edits, commits, subagents, Coin State/tests, protected producer/analysis HEAD changes, public replay/download, cache or private account activity. Root PROJECT_STATE remained untouched. The synthetic incomplete cases prove the input contract, not completed performance. The exact five-account canonical bridge, full six-group equality against frozen actual accounts, global financial acceptance and final adoption gates remain required.
