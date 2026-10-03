# Task 6 — one named physical recovery implementation

DONE for implementation and isolated verification; independent recovery review remains required before any real recovery launch. No financial, adoption, prospective or native acceptance is claimed.

## Result and immutable identities

The new helper copies the approved lifecycle core and adds one-child concurrency, a child environment argument, and a before-launch storage/fresh-path hook. The original three helpers, 50-job registry, parent freeze, exclusive anchor, sources and failed attempt remain untouched. No runtime source-string rewriting or production caller monkeypatching is used.

Original parent freeze: `b15129a0984d3a6f2bc1be1e1bfc700f9cd30a2023d257efcd608a408efac1c9`. Original registry: `e58114f25f316d237860d2d6e6859d48614a57d69065524f6c256140c575fbfa`. New recovery registry: `d7bc23958cedc74626d9f082a18c52b18f2417e974931cac18ea618559a6d23b`. New helper: `cdc8538d01b46963c12b8810b468cafd754b58303a69495cfb32f4e62d497185`.

Actual measured Spot identity remains HEAD `74bd6e035e36531c517029077c1a9e2e5ec44516`, Python `f2d6c3e73c2acb7b328a7a0e2678bb95ceb77d8a17a46139abfe8b357befdbf6`; Coin remains HEAD `37061a7f588f97cc16852551cab6cd2e51acb920`, Python `ba63895131db566e708a5c96cde4504beace39fa0bdd54881d039dd5b8ef4c50`. Both source identities match the actual original freeze. Both whole-repository status outputs contain only root-owned ` M PROJECT_STATE.md`; the optional clean-whole-repo assertion first failed on that known documentation state and is explicitly retained in `task-6-recovery-first-verification-observation.json`. No refreeze or source repair followed.

## Registration and first failure

Exactly 50 original commands are registered in original order: 36 Spot + one 16-account Coin unscaled invocation, four Spot + one 4-account Coin risk invocation, two Coin offsets, and six baseline budget invocations. This is 68 account identities: 52 unscaled, 8 risk, 2 sensitivity, 6 budgets. Every original negative/stress case remains. There are no subset, candidate, capital, source, UID, limit or schedule CLI overrides.

The only argv substitutions are exact `--out` and `--prints` path values: insert `recovery1/` below `/workspace/scratch/btc-alpha-beta-edge-20261003`. Every receipt carries `original_job` plus actual command. Original `--risk-calibration` paths remain under the original `assessment/`; the unchanged original binder and original registry SHA remain authoritative for derived profiles.

The registration binds 58 files, including exact original raw/log/start/finish/progress/phase/release/diagnostic evidence, original helpers/review/anchor/freeze, the recovery helper/tests/diffs/final test log, and all preserved failed print-cache files. It also fixes 22 existing files across first-attempt unscaled/print-cache trees and records 49 absent original output paths. First-attempt inventory changes or appearance of an originally absent raw fail closed.

The original Coin file is exactly ZERO BYTES with SHA `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`. It contains no valid gzip header, JSON or usable account raw. The only progress claim is the recorded 28/795 sessions and actual failure logs. Spot has two exit1 children with no raw and 34 never-started jobs. Both original phases have actual all-children-reaped/release evidence. All retained evidence stays in place; no failed raw can enter the recovery raw set.

## Small core delta and lifecycle guarantees

Exact minimal lifecycle diff: `task-6-recovery-core.diff`. Exact complete approved-original to new-helper diff: `task-6-recovery-controller.diff`. The core changes only its optional environment/launch-hook signature, Spot cap2→cap1, the prelaunch hook call, and explicit `env` passed to Popen. Reservation acquisition/release, launch critical section, deferred signals, actual process wait, finish hashing, fallback diagnostics, pending jobs and durable unknown-owner handling are copied unchanged.

The same `ART/controller-reservations/{spot,perp}` files coordinate original, conditional and recovery runners. Inherited child descriptors retain flock ownership when a parent exits. Unknown owners are never cleared. No kill, invented exit, retry, source reset, account-lock change or cleanup code exists. A phase receipt directory is exclusive and named `recovery1-PHASE-RECOVERY_REGISTRY_SHA`; failed or completed phases cannot rerun.

Recovery authority checks run before reservation/launch and before/after every child. They bind current registry/helper/original helper/review/first-failure bytes, original parent anchor/freeze and current approval evidence. Both projects’ source identities AND all frozen input/vault trees/files are guarded before/after every child. Phase-input original export/production/raw byte links and any original conditional registry remain checked. Directory ancestry symlinks are refused for bound files and recovery destinations.

## Storage behavior

The child environment is the inherited environment with only `TMPDIR=/workspace/scratch/btc-alpha-beta-edge-20261003/recovery1/tmp/{spot,perp}` added/replaced. HOME, UIDs, native account-lock locations and all virtual schedule arguments remain inherited. Command provenance includes UID, HOME, the sole environment override, filesystem/device, available bytes, threshold and measurement time.

The launch hook runs under the shared project reservation. It refuses symlink ancestry, wrong ownership, an unknown TMPDIR owner, residual temp entries, existing print directories and existing sibling `-cache` binary owners. It checks actual `stat -f` filesystem type `overlayfs`, device equality with `/workspace`, and at least 4 GiB available before every child. No actual recovery root/TMPDIR was created during implementation. Isolated fixture equivalents were created only below this task’s artifact directory. The original producers retain their normal TemporaryDirectory cleanup behavior.

The 4 GiB floor is a conservative admission check, not a storage reservation or a proof of future peak space. Spot1/Coin1 may coexist; unrelated filesystem use or unexpectedly large snapshots can still exhaust space. If that happens the same failed/drained state is retained with no automatic retry. Full frozen Coin/vault verification hashes roughly 14.8 GB at each boundary; this deliberately retains the brief’s byte checks and can add run time.

## Conditional phases and calibration

No speculative conditional registry or result is created. A later `--supplemental-registry` must be an ORIGINAL-format conditional registration with exact caller SHA; the original unchanged `bind-phase-inputs.py.validate_supplement` validates the complete all-eligible combination/selection and original raw/report/source bindings BEFORE path transformation. Recovery is never presented as a combination registration. `--phase-input` continues to bind the original registry SHA (or validated original conditional registry SHA), not the physical recovery registry SHA.

## Fresh review and launch gate

Real `recovery-approval.json` is absent, and real recovery output root is absent. This implementation did not launch financial commands. The root agent must first obtain the independent scoped report at `task-6-recovery-rereview.md`, then create the approval exclusively with this schema:

```json
{"format":"btc-edge-recovery-approval-v1","attempt":"recovery1","approved":true,"review":{"path":"ABSOLUTE_REVIEW_PATH","bytes":0,"sha256":"ACTUAL_HASH"},"bound_files":["ACTUAL {path,bytes,sha256} records for registered-financial-recovery1.json, run-registered-recovery.py, task-6-recovery-report.md, and task-6-recovery-rereview.md"]}
```

The example is a schema explanation, not an actual approval artifact. Use actual file lengths/hashes and an array of records, then hash the final approval bytes. Root-authorized launch form after review:

```text
python task-artifacts/run-registered-recovery.py --phase unscaled --kind spot --approval-sha256 ACTUAL_APPROVAL_SHA
python task-artifacts/run-registered-recovery.py --phase unscaled --kind perp --approval-sha256 ACTUAL_APPROVAL_SHA
```

Subsequent original phases use the same gate and exact phase/project selection; risk additionally requires the actual original `--phase-input`. The recovery registry binds the original approved controller review; the post-review approval binds recovery registry, helper, report and fresh review without creating a circular hash dependency. The exact approval hash is caller-supplied review authority and checked at every boundary.

## Verification

Command: `python /workspace/btc-alpha-beta-improve/task-artifacts/test-controller-recovery.py` → **18 tests, OK, 2.601s** (`task-6-recovery-tests-final.log`). These are isolated controller, filesystem and actual harmless-child tests; no financial producer, account suite, full Coin suite or network request ran. Earlier red/green/expanded/integration outputs and all fixtures remain retained. The initial original-cap concurrency probe failed as intended with “overlapping project children”; final cap1 passes for both projects.

Coverage includes exact50/no-dropped-negative argv and account counts; parent/original registry/helpers/failure/recovery helper/registry/approval/report/review tamper; source and input metadata/inventory tamper; actual inherited-child blocking shared with the original controller; original nonzero exit, Popen failure, post-Popen bookkeeping failure, SIGINT/SIGTERM during actual blocking wait, signal during Popen, post-guard/hash/finish/phase/release failures; exact pending/exit/release truth; existing output/progress/print binary refusal; child TMPDIR propagation with byte-for-byte inherited environment and same UID; overlay/free-space/owner/residue checks; absent approval denial; and main pre/post guards with a registry mutation after actual harmless launch.

The unchanged original production binder was exercised end-to-end against an actual-schema synthetic report containing all52 recovery-path raws, producing a binding to the original assessment profile location and original registry SHA. Its strict boolean audit rejection, audited negative eligibility, exact raw/source/export links, and original all-eligible conditional validator were retained. Synthetic fixtures are not financial evidence. A test-only main adapter replaces production argv with harmless Python after asserting original selected argv; no production helper mutation or caller monkeypatch is used in deployed orchestration.

Read-only final registration validation checked all58 bound files, all22 preserved first-attempt tree paths, all49 absent originals and exact50 transformation. Actual current source identities were measured and compared to the original freeze. Full actual frozen input/vault hashing is performed by launch guards, not redundantly claimed as completed during this isolated implementation.

## Requirements mapping

| Requirement | Implementation / evidence |
| --- | --- |
| One named recovery; immutable original50 and parent | Fixed constants, validate_registration; verification JSON and exact registry hashes |
| Preserve failed raw/log/status/release and no usable empty Coin raw | 58 bindings,22 tree paths,49 absent outputs; first_failure classification and diagnostic binding |
| Exact path-only complete matrix, unchanged risk paths | transformed_job; full equality to all50 original jobs; mapping below; original-binder test |
| Spot1/Coin1 and overlay TMPDIR only | run_jobs cap1; child env; storage_guard; actual subprocess and filesystem tests |
| No rerun/subsets/fresh binary owner | Fixed phase filtering/exclusive receipt directory/output/progress checks; fresh_paths checks prints and -cache |
| Shared ownership and unknown-child refusal | Copied Reservation at original ART root; real inherited-child probe |
| C1 graceful signal/bookkeeping/failure drain | Unchanged core; SIGINT/SIGTERM/Popen-window/post-bookkeeping tests with actual exits |
| C2 original parent/input/source/helper binding | Fixed original parent SHA + exclusive anchor; both full guards before/after child |
| C3 conditional all-eligible rules | Unchanged original validate_supplement before transformation; conditional negative tests |
| C4 strict audited complete52 before profiles | Unchanged original binder; actual interface52raw tests incl bool rejection |
| Current recovery helper/registration/fresh review approval | Registry current helper hash; exact approval SHA + helper/registry/report/review bindings at every boundary |
| Authoritative provenance and pending/release records | Original job + actual argv, freeze/registry/failure/approval hashes, measured space and existing lifecycle receipts |
| All fixtures preserved; no full financial/native/network work | 1264 isolated fixture files in manifest; 0 financial invocations; absent actual recovery output root |

## Complete output and print mapping

`R` is exactly `/workspace/scratch/btc-alpha-beta-edge-20261003`. Each row maps `R/<original relative output>` to `R/recovery1/<same relative output>`. For listed print paths the identical prefix insertion applies. Full original and actual argv are preserved together in the immutable recovery registration.

| Label | Phase | Kind | Accounts | Original output relative to R | Original prints relative to R |
| --- | --- | --- | ---: | --- | --- |
| spot-atr-stop-base | unscaled | spot | 1 | unscaled/spot-atr-stop-base.json.gz | — |
| spot-atr-stop-fee150 | unscaled | spot | 1 | unscaled/spot-atr-stop-fee150.json.gz | — |
| spot-atr-stop-slip2 | unscaled | spot | 1 | unscaled/spot-atr-stop-slip2.json.gz | — |
| spot-atr-stop-outage | unscaled | spot | 1 | unscaled/spot-atr-stop-outage.json.gz | — |
| spot-exit-confirm-base | unscaled | spot | 1 | unscaled/spot-exit-confirm-base.json.gz | — |
| spot-exit-confirm-fee150 | unscaled | spot | 1 | unscaled/spot-exit-confirm-fee150.json.gz | — |
| spot-exit-confirm-slip2 | unscaled | spot | 1 | unscaled/spot-exit-confirm-slip2.json.gz | — |
| spot-exit-confirm-outage | unscaled | spot | 1 | unscaled/spot-exit-confirm-outage.json.gz | — |
| spot-stop-budget-base | unscaled | spot | 1 | unscaled/spot-stop-budget-base.json.gz | — |
| spot-stop-budget-fee150 | unscaled | spot | 1 | unscaled/spot-stop-budget-fee150.json.gz | — |
| spot-stop-budget-slip2 | unscaled | spot | 1 | unscaled/spot-stop-budget-slip2.json.gz | — |
| spot-stop-budget-outage | unscaled | spot | 1 | unscaled/spot-stop-budget-outage.json.gz | — |
| spot-crowding-interaction-base | unscaled | spot | 1 | unscaled/spot-crowding-interaction-base.json.gz | — |
| spot-crowding-interaction-fee150 | unscaled | spot | 1 | unscaled/spot-crowding-interaction-fee150.json.gz | — |
| spot-crowding-interaction-slip2 | unscaled | spot | 1 | unscaled/spot-crowding-interaction-slip2.json.gz | — |
| spot-crowding-interaction-outage | unscaled | spot | 1 | unscaled/spot-crowding-interaction-outage.json.gz | — |
| spot-cash-base | unscaled | spot | 1 | unscaled/spot-cash-base.json.gz | — |
| spot-cash-fee150 | unscaled | spot | 1 | unscaled/spot-cash-fee150.json.gz | — |
| spot-cash-slip2 | unscaled | spot | 1 | unscaled/spot-cash-slip2.json.gz | — |
| spot-cash-outage | unscaled | spot | 1 | unscaled/spot-cash-outage.json.gz | — |
| spot-protected-participation-25-base | unscaled | spot | 1 | unscaled/spot-protected-participation-25-base.json.gz | — |
| spot-protected-participation-25-fee150 | unscaled | spot | 1 | unscaled/spot-protected-participation-25-fee150.json.gz | — |
| spot-protected-participation-25-slip2 | unscaled | spot | 1 | unscaled/spot-protected-participation-25-slip2.json.gz | — |
| spot-protected-participation-25-outage | unscaled | spot | 1 | unscaled/spot-protected-participation-25-outage.json.gz | — |
| spot-protected-participation-50-base | unscaled | spot | 1 | unscaled/spot-protected-participation-50-base.json.gz | — |
| spot-protected-participation-50-fee150 | unscaled | spot | 1 | unscaled/spot-protected-participation-50-fee150.json.gz | — |
| spot-protected-participation-50-slip2 | unscaled | spot | 1 | unscaled/spot-protected-participation-50-slip2.json.gz | — |
| spot-protected-participation-50-outage | unscaled | spot | 1 | unscaled/spot-protected-participation-50-outage.json.gz | — |
| spot-protected-participation-75-base | unscaled | spot | 1 | unscaled/spot-protected-participation-75-base.json.gz | — |
| spot-protected-participation-75-fee150 | unscaled | spot | 1 | unscaled/spot-protected-participation-75-fee150.json.gz | — |
| spot-protected-participation-75-slip2 | unscaled | spot | 1 | unscaled/spot-protected-participation-75-slip2.json.gz | — |
| spot-protected-participation-75-outage | unscaled | spot | 1 | unscaled/spot-protected-participation-75-outage.json.gz | — |
| spot-protected-participation-100-base | unscaled | spot | 1 | unscaled/spot-protected-participation-100-base.json.gz | — |
| spot-protected-participation-100-fee150 | unscaled | spot | 1 | unscaled/spot-protected-participation-100-fee150.json.gz | — |
| spot-protected-participation-100-slip2 | unscaled | spot | 1 | unscaled/spot-protected-participation-100-slip2.json.gz | — |
| spot-protected-participation-100-outage | unscaled | spot | 1 | unscaled/spot-protected-participation-100-outage.json.gz | — |
| perp-registered-16 | unscaled | perp | 16 | unscaled/perp-registered-16.json.gz | print-cache/perp-registered-16 |
| spot-risk-atr-stop | risk | spot | 1 | risk/spot-risk-atr-stop.json.gz | — |
| spot-risk-exit-confirm | risk | spot | 1 | risk/spot-risk-exit-confirm.json.gz | — |
| spot-risk-stop-budget | risk | spot | 1 | risk/spot-risk-stop-budget.json.gz | — |
| spot-risk-crowding-interaction | risk | spot | 1 | risk/spot-risk-crowding-interaction.json.gz | — |
| perp-risk-registered-4 | risk | perp | 4 | risk/perp-risk-registered-4.json.gz | print-cache/perp-risk-registered-4 |
| perp-incumbent-offset--60000 | sensitivity | perp | 1 | sensitivity/perp-incumbent-offset--60000.json.gz | print-cache/perp-incumbent-offset--60000 |
| perp-incumbent-offset-60000 | sensitivity | perp | 1 | sensitivity/perp-incumbent-offset-60000.json.gz | print-cache/perp-incumbent-offset-60000 |
| spot-baseline-budget-2500 | budgets | spot | 1 | budgets/spot-baseline-budget-2500.json.gz | — |
| spot-baseline-budget-5000 | budgets | spot | 1 | budgets/spot-baseline-budget-5000.json.gz | — |
| spot-baseline-budget-7500 | budgets | spot | 1 | budgets/spot-baseline-budget-7500.json.gz | — |
| perp-baseline-budget-2500 | budgets | perp | 1 | budgets/perp-baseline-budget-2500.json.gz | print-cache/perp-baseline-budget-2500 |
| perp-baseline-budget-5000 | budgets | perp | 1 | budgets/perp-baseline-budget-5000.json.gz | print-cache/perp-baseline-budget-5000 |
| perp-baseline-budget-7500 | budgets | perp | 1 | budgets/perp-baseline-budget-7500.json.gz | print-cache/perp-baseline-budget-7500 |

## New artifact hashes

All files below are new external task artifacts. The file manifest records each retained test fixture individually. The report’s own final hash is supplied in the handoff and must be included in the root-created approval; a file cannot contain its own stable hash.

| File | Bytes | SHA256 |
| --- | ---: | --- |
| run-registered-recovery.py | 27862 | `cdc8538d01b46963c12b8810b468cafd754b58303a69495cfb32f4e62d497185` |
| test-controller-recovery.py | 25523 | `7ef32ced9536cf4380a4417341ebe305231849be09b56d242b6ef0d51a51e661` |
| registered-financial-recovery1.json | 112155 | `d7bc23958cedc74626d9f082a18c52b18f2417e974931cac18ea618559a6d23b` |
| task-6-recovery-core.diff | 2053 | `30688cc6488d611747bc948ef6624b425a6a6ffb71bb794464c204dff006325e` |
| task-6-recovery-controller.diff | 21102 | `96e4fbe898ba3fa3e73b585f80bc8d0386422213c9fe09c96a8cd5788ef8dddf` |
| task-6-recovery-tests-red.log | 856 | `8e9d9b77ce52c1e5631aecab4fbf2c42ea1b66362037b1580a9129119759070c` |
| task-6-recovery-tests-first-green.log | 183 | `12c9b568d7c15782b531d3c22aa99caa6c3c3d8028b759b3513400caca8e323e` |
| task-6-recovery-tests-expanded.log | 2245 | `4e7d0a78247d80e05ad1d8cefa46749fc1e34f1457ee8fabe391bf42eb417e26` |
| task-6-recovery-tests-integration.log | 2598 | `be4512f09ec47c7e6dae516510fe5c0eaff129e43d32ef0801c8fb6d27aac293` |
| task-6-recovery-tests-final.log | 2884 | `b4df9a48c62b83bb7a684d88899dc7948b8644cdfe259ad892513473bade5bbe` |
| task-6-recovery-file-manifest.json | 442328 | `60caa33eae409b54045e52cc699ca8751e0c8c4d17a30fceb4f38d60288e40d3` |
| task-6-recovery-verification.json | 2664 | `dbcbec4fb5bb7e7c98526db46a19a5bb31c13c74f7011ea98de5a110769778e1` |
| task-6-recovery-first-verification-observation.json | 318 | `9e47fbdffeeaa4e2cb290412c6843115c7cb02ae5cbdafcaae94409a3be24285` |

## Limits and review handoff

The implementation is ready for fresh independent scoped review; no approval was manufactured. Graceful SIGINT/SIGTERM are covered; SIGKILL/machine failure remains fail closed through inherited flock and durable unknown-owner refusal. Storage admission does not reserve future bytes. A new failure would remain preserved and require a separate explicit ruling, never an automatic recovery2. Root-owned documentation dirtiness does not alter the measured source identity. Original financial acceptance, full finite-session results, prospective validation and native qualification remain outstanding.
