# Task 6 controller fix 1 — DONE, pending independent scoped re-review

The external controller wave addresses T6-C1, T6-C2 and T6-C3. No actual financial job, producer test suite, account operation, public fetch, source freeze, source commit/archive, profile creation in production, vault hash sweep or vault mutation was performed. All executed children were harmless temporary Python processes. The original review, helper copies and 50-job registry remain unchanged. This is controller preparation, not financial acceptance.

## Corrections

**T6-C1.** The common runner now owns complete launch, active-child and completion bookkeeping. Failure stops new launches and drains/reaps all tracked children; log handles close; actual exits, before/after guard errors, missing outputs, hash failures, and receipt-write failures are distinct. A `launch_requested` receipt never claims that Popen succeeded. Successful Popen is tracked before later receipt writes. A failure before Popen leaves the job pending and writes an exclusive `not_started` receipt without an invented exit code. Job finish receipts include actual exit/reap state and hashes/errors. The phase result retains pending labels and all completion diagnostics, including `finish_receipt_saved:false` when necessary. Independent exclusive diagnostic files under the task-owned diagnostic tree retain failures if output receipt destinations fail. SIGTERM/SIGINT during launch are deferred until the actual child is registered, then the controller drains it; repeated handled signals cannot interrupt that drain. Errors during reservation-release bookkeeping have a final failed diagnostic result as well.

**T6-C2.** Initial freeze reads the existing `immutable-public-vault-snapshot-v1` list using its actual `{path,size,sha256}` fields. It checks the entire actual inventory and original bytes, then includes every Coin vault object and metadata file in Coin bound files and an exact all-file tree. This includes the original raw ZIPs and official CHECKSUMs, and prevents simultaneous ZIP/CHECKSUM replacement from escaping the guard. This vault tree is Coin-only: Spot checks do not repeatedly hash Coin print data. The freeze also binds the new phase helper. The future initial freeze creates an exclusive `task-artifacts/controller-parent-freeze.json` anchor for its actual path/SHA/size; subsequent phases and bindings must use that same parent, with no refreeze. Parent and registry bytes, producer/evaluator source identities and actual project inputs are rechecked before/after each job.

`bind-phase-inputs.py` binds an existing actual source-bound `research.edge_assessment` report, its ORIGINAL export identified by `report.command --calibration-out-dir`, and the exact registered production profile path. Production bytes must equal the original export bytes, not merely equivalent JSON. It uses the reviewed assessor's actual `validate_profile_document`, `required_matrix`, `account_id`, spec/protocol constants and account/source fields. The original 52 unscaled accounts must all be complete, audited and raw-byte/source-bound; blocking/rejected/incomplete accounts reject. Pending later risk/combination/budget accounts may remain. The binding also retains all report-account raw files. A combo profile requires a new binding to the actual separate original `kind_combo.json` export. Original parent, report, export, production profile and raw byte SHAs are checked before binding is written, and then before/after each risk job. The binding records actual creation UTC, project, phase, parent SHA and actual registry SHA. No nonexistent future calibration was invented.

**T6-C3.** Every runner instance uses the same fixed task-owned `controller-reservations/{spot,perp}/reservation.lock` path. One runner per project is allowed, with internal Spot concurrency 2 and Coin concurrency 1. The flock descriptor is passed to each real child. It is closed, never explicitly unlocked, after drain, so parent exit cannot release the child's inherited ownership. Immutable owner/release records preserve known-finished evidence. Owner records with missing, incomplete or mismatched release evidence fail closed even after OS locks disappear; nothing auto-deletes reservations. This touches no account locks, HOME, UID or settings. The unexpected-parent-exit test explicitly observed a live inherited lock and then unknown-owner refusal after the child exited.

## Interfaces retained for future root work

The root must finish reviewed source commits/archives before the original freeze, supply actual clean source and originals, and later supply actual assessor report/export/profile paths. This helper requires committed source; it does not commit or archive repositories itself. No such action occurred in this correction.

Initial freeze interface remains `prepare-source-freeze.py --review PATH [--review PATH ...] --out PATH`. It now also exclusively writes the one parent anchor. Risk-phase binding interface:

```text
python task-artifacts/bind-phase-inputs.py --freeze ORIGINAL_FREEZE --report ACTUAL_ASSESSOR_REPORT --export ORIGINAL_EXPORT_DIRECTORY/spot.json --production-profile ACTUAL_REGISTERED_SPOT_PROFILE --kind spot --phase risk --export-label spot --out EXCLUSIVE_PHASE_BINDING
```

For Coin, use `--kind perp --export-label perp` and the exact registered Coin path. For a later all-eligible combo risk phase use its own original `spot_combo.json`/`perp_combo.json`, export label, new phase binding, and the explicit supplemental registry path/SHA. There is no copy/rewrite/export-generation action in this helper.

Runner interface is `run-registered-phase.py --kind spot|perp --phase PHASE --freeze ORIGINAL_FREEZE [--phase-input EXCLUSIVE_PHASE_BINDING]`. Every risk argv must match the production path in the binding. The original registry's SHA and original four phase names remain enforced.

Conditional jobs use the same runner/core with `--supplemental-registry ROOT_REGISTERED_JSON --supplemental-sha256 ACTUAL_SHA`. The supplemental format is `btc-edge-conditional-registration-v1` with `parent_freeze_sha256`, original `parent_registry_sha256`, bound `assessment_report`, its original raw-account `bound_files`, `project_kind`, `phase`, `condition`, `role` and exact `jobs`. Conditions are only `all-eligible-combination` (role `unscaled` or `risk`) and `selected-budgets`. The controller checks original research interpreter/module prefix, allowed argv options, project/repository/features, new outputs inside the task output tree, exact ALL-eligible ordered components, and the complete four stress / one risk / three budget inventory. Selection follows the actual assessor's complete individual/combo decisions; partial combinations, subsets, custom entrypoints, limits and alternate capital sets reject. The original 50-job registry is never amended. Root's independent financial reviewer still validates actual applicability and exact commands.

Small schema overview (field names are actual; full synthetically valid examples are retained below):

```json
{
  "format": "btc-edge-phase-input-binding-v1",
  "created_utc": "2026-10-03T04:00:00+00:00",
  "parent_freeze_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "project_kind": "spot",
  "phase": "risk",
  "registry_sha256": "e58114f25f316d237860d2d6e6859d48614a57d69065524f6c256140c575fbfa",
  "analysis_source": {"dirty": false},
  "export_label": "spot",
  "assessor_report": {"path": "/temporary/report.json", "sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "bytes": 123},
  "original_export": {"path": "/temporary/exports/spot.json", "sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc", "bytes": 456},
  "production_profile": {"path": "/temporary/spot-calibration.json", "sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc", "bytes": 456},
  "bound_files": []
}
```

The abbreviated overview above is not a usable binding: runtime additionally requires all original entries and the parent in `bound_files`. Full test-created schema examples, including the actual complete fields and files, are retained under `task-6-controller-fix1-isolated-receipts/derived-binding-synthetic-schema/binding.json` and `task-6-controller-fix1-isolated-receipts/conditional-registry-synthetic-schema/supplemental-registry.json`. Their referenced `/tmp/controller-isolated-*` paths were deliberately temporary; these are synthetic test evidence, not future production inputs or financial acceptance. `launch-failure-drain/` retains actual isolated exclusive start/finish/not-started/diagnostic and owner/release examples. Task-owned lock descriptors/files themselves are not copied into examples.

## Validation

Final amended covering command, run from `/workspace/btc-alpha-beta-improve`:

```text
CONTROLLER_TEST_EXAMPLES=task-artifacts/task-6-controller-fix1-isolated-receipts PYTHONDONTWRITEBYTECODE=1 python task-artifacts/test-controller-fix1.py > task-artifacts/task-6-controller-fix1-tests-complete-retained.txt 2>&1
```

Exit 0, **22 tests passed**. Exact complete output is retained in that file. Coverage includes existing output, Popen failure with another active child, launched/finish/phase receipt failures, output hash failure, before/after guard errors, pending preservation, actual harmless success/nonzero exits, SIGTERM during Popen bookkeeping, project reservation conflicts between different phases, known-finished release, unknown ownership, inherited ownership after parent exit, vault ZIP/CHECKSUM/metadata mutation/addition/removal, original/production profile mutation/removal, complete audited unscaled-account requirements, project/spec/raw/source mismatch, original-export binding/exclusivity/byte equality, actual runner parent-anchor/freeze/report/profile/binding rechecks and conditional-registry rejection. Source/market guards that are replaced by synthetic fixtures are explicitly isolated controller tests, not market/source/financial acceptance.

Parser-only checks (each exit 0; output retained in the corresponding file):

```text
PYTHONDONTWRITEBYTECODE=1 python task-artifacts/prepare-source-freeze.py --help > task-artifacts/task-6-controller-fix1-freeze-help.txt
PYTHONDONTWRITEBYTECODE=1 python task-artifacts/bind-phase-inputs.py --help > task-artifacts/task-6-controller-fix1-bind-help.txt
PYTHONDONTWRITEBYTECODE=1 python task-artifacts/run-registered-phase.py --help > task-artifacts/task-6-controller-fix1-runner-help.txt
```

Earlier successful amended-check outputs are retained separately (`tests-first`, `tests-second`, `tests-final`, `tests-final-retained`, `tests-signal-final`, `tests-complete`); they are not claimed as the final helper identities. Original controller failed review and pre-fix copies remain intact. Only the amended controller checks ran, not original unchanged producer or market suites.

## Limits and concerns

No known unresolved implementation concern from these isolated checks; independent scoped re-review is still required. SIGKILL/machine failure cannot create graceful completion receipts: inherited ownership and durable unknown-owner refusal intentionally prevent a later controller from proceeding. An unknown owner has no automatic unlock/recovery interface. If every task-owned diagnostic destination is unwritable, the controller returns failure and prints errors but cannot promise persisted receipts. Linux/POSIX flock and pass_fds are required. The financial validity/authenticity of root-supplied assessment results remains subject to the planned independent financial review; these guards enforce retained source/schema/raw-byte and execution identities.

The exclusive parent anchor is new future runtime behavior. If freeze creation succeeds but its anchor write fails or leaves incomplete evidence, it fails closed; do not regenerate or delete evidence to bypass it. The actual vault must still match the preserved preflight when the first real freeze is attempted. No controller reservation, parent anchor, actual freeze or real financial output was created under the production controller tree in this task.

## Helper identities and complete amended-file list

| File | Before SHA256 | Final SHA256 |
|---|---|---|
| prepare-source-freeze.py | 742f6b895cf18e691a64d1819099e6cdf15eda26babb04e4ef0fcd2fbb417af8 | 3a78d0bb2c158cc0a5dc723ab149cb42b0f6456b416dd41fe6bd040cb876c2cf |
| run-registered-phase.py | 57ce768b53b4277031d82f344506c7d4f3b8db569f350762f52cfa0944756a2a | 628d549a8e485e5fe9db8384613db46dc828a035a7e1fc60cde1b9dbcd791bd7 |
| bind-phase-inputs.py | new | 3169ffc501ec2a82ec4eaf02d20f877e01d1e243e59512462676c3d9f16e7e12 |
| test-controller-fix1.py | new | d6356ee83433a07d6eb98ede285b2cb9492eb63c08bc75df157c5b881728a4cb |

Unchanged original registry SHA256: `e58114f25f316d237860d2d6e6859d48614a57d69065524f6c256140c575fbfa`. Original review SHA256: `59c7fbfe0dee244874331bd50feee5a9b6d1c1554d61ee1aa424a4611805b57b`.

Complete amended/new deliverable list (every retained example file, size and SHA) is in `task-6-controller-fix1-file-manifest.json`. It contains the four implementation/test files, this report, the exact check/help outputs above, and every file in the isolated-receipts tree. This manifest itself is the only additional new deliverable; no other source files were edited. Disposable controller-only bytecode generated during parser/import checks was removed.
