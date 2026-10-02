# Scoped independent project-calibration review

BASE `32ab1bb546bde064e641c4a2eb5ed4248e590acb` → HEAD `99fcf005d2cb15c13bb37322b65ab2863b19d65e`, analysis worktree `/workspace/btc-alpha-beta-analysis/spotquant`.

**Specification: PASS. Code quality: APPROVE.** No defect or unauthorized bypass found in this scoped three-file change.

Reviewed the brief, implementation report, entire three-file diff, and surrounding actual risk consumption/final-gate/source-equivalence paths. The implementation is small and reuses existing JSON/hash and deterministic calibration helpers.

- `load_project_calibration` derives the allowed subset exclusively from the full deterministic document and registered project names. All root fields and every legal project profile remain required; canonical JSON comparison rejects type substitutions, changed training/input identities, missing/extra profiles and trust fields. There is no caller-selected profile filter.
- Both complete unscaled matrices are consumed with unchanged28+20 expectations before project overrides are accepted. Existing global calibration validation and complete calibration-out behavior remain unchanged. A project subset cannot substitute for the global document.
- Each actual risk input receives the chosen parsed document and its exact original-byte SHA. Existing metadata/profile checks remain active. Global SHA/scope and actual per-project SHA/scope/profile inventory are separately reported; no raw metadata is rewritten or relabeled.
- Global-only fallback, mixed global/project files, two project files without global calibration, and missing-calibration failure paths are explicit and covered. The unchanged ten obligations, unity controls, baseline evidence, source/history, achieved-risk, sensitivity, final-completion, freeze and native-zero gates remain in force.
- No new source-equivalence exclusion or source override was introduced. Training calculations and selection rules are unchanged.

Independent offline verification:

1. Exact-head `git archive` into a temporary standalone checkout, with no producer siblings: `python -m unittest tests.test_alpha_assessment tests.test_complete_assessment` — **34 tests passed in0.680s**. These include27 assessor and7 complete-assessment tests, project subset mutation rejection, real synthetic risk-file hash consumption, global compatibility and pending-final rejection. No Coin producer or account State tests ran.
2. Real committed-tree `verify_execution_equivalence` using local analysis-repository history for frozen Spot8ca0025 and reviewed99fcf005 — **PASS**, digest `c2dd29733ec5bb96137a8ab27cc0e8dd604d74bf6d1e108d45a554b8923e6cf8`. Both full historical Python digests and unchanged spec/protocol were checked; only the pre-existing assessor exception applied.
3. Exact BASE..HEAD `git diff --check` — **PASS**.

No running producer checkout, producer HEAD, account/cache/private state, or market artifact was changed or accessed for testing. No replays, downloads, commits, product edits or subagents. Only this external review report was written. Root-owned PROJECT_STATE remained untouched.

This is approval of assessment plumbing, not completed economic evidence. Actual early Spot calibration must still be derived from its complete approved unscaled matrix, and the later unified assessment must verify that exact file against the deterministic subset after both matrices complete. Full account completion, baseline equality, actual risk reruns and final financial review remain controller responsibilities.
