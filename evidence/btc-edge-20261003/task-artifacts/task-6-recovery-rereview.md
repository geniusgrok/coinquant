# Task 6 recovery — independent engineering re-review

SPEC: **PASS**. QUALITY: **APPROVE** for the exact recovery implementation and identities below. Material findings: **0 Critical, 0 Important, 0 Minor**. No source change or implementation repair is requested. This is engineering approval for the one named physical recovery attempt, not financial, adoption, prospective or native acceptance.

## Scope and binding contract

Read the initial review brief, binding task-6-recovery-brief.md, original accepted task-6-controller-fix2-rereview.md, original three helpers, complete new recovery helper and tests, full recovery registration, report, lifecycle delta and complete root review package. The package is exactly the approved-original-to-new helper diff followed by the entire new test file from /dev/null; independently regenerated and compared both package and controller diff to actual files.

Root corrected its own review-output filename after manifest creation. My first manifest pass observed the brief mismatch. Root then restored its original brief bytes and retained a separate corrected task-6-recovery-final-review-brief.md plus task-6-recovery-root-brief-correction.json. I read that corrected brief and independently rechecked **all 1,277 manifest entries (13 files + 1,264 fixtures)**: no remaining size/hash mismatch. No helper, registry, original manifest, producer, or parent freeze was changed by that correction. The review output is the fixed task-6-recovery-rereview.md required by the actual helper and registration.

## Contract and evidence review

**Exact matrix and economics (helper lines 332–388, 470–504).** Parsed the complete 112,155-byte recovery registration and checked its actual SHA. All 50 original jobs remain in order, with identical original_job, cwd, labels, phase, expected-account counts and command lengths. Independently compared every argv position: the changed positions are exactly the values after --out and, where present, --prints. Each inserts recovery1/ beneath the original output root. No other economic/schedule/calibration/candidate argument changes. Counts are unscaled Spot36 + Coin1 invocation/16 accounts; risk Spot4 + Coin1 invocation/4 accounts; Coin sensitivity2; budgets Spot3 + Coin3: **50 jobs, 68 accounts**. Negative/stress/protected-participation rows are retained. Original production --risk-calibration paths remain under original assessment/. The CLI exposes no subset, UID, schedule, arbitrary-command or economic override.

**Original preservation and actual failure.** Independently verified all **58 recovery bound-file records**, the **22 exact first-attempt tree files**, and **49 required absent original raw outputs**. Matched both original phase summaries field-for-field to the first-failure record. Checked all three actual command-start argv against original registered jobs; recomputed their command-start and log hashes; checked command-finish bodies against phase results; verified owner/release hashes and true all_children_reaped. All three logs end in sqlite3.OperationalError: database or disk is full. Spot has two actual exit1/reaped children, missing raws and exactly34 pending jobs. Coin has one actual exit1/reaped child; its existing output is exactly0 bytes with SHA e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855. It is not usable gzip/JSON/account evidence. No failed raw or failed print-cache owner is reused.

Independently remeasured source_identity for both repositories: Spot HEAD74bd6e035e36531c517029077c1a9e2e5ec44516 / Pythonf2d6c3e73c2acb7b328a7a0e2678bb95ceb77d8a17a46139abfe8b357befdbf6; Coin HEAD37061a7f588f97cc16852551cab6cd2e51acb920 / Pythonba63895131db566e708a5c96cde4504beace39fa0bdd54881d039dd5b8ef4c50. Both equal the immutable original freeze and report source dirty=false. Both whole-repository status outputs show only the permitted root-owned ` M PROJECT_STATE.md`. Independently checked the exclusive parent anchor equals the actual freeze binding and the original three helper plus registry hashes equal their accepted identities. No refreeze occurred.

**Authority and guards (lines 351–410, 513–530).** Exact caller-supplied approval SHA is required, and approval must bind current registry/helper/report plus the fixed independent review path. Original registry/freeze/anchor/helper/review/failure bindings transitively remain covered. Authority checks run before reservation and through the child pre/post guard. Both frozen project identities and all registered input/vault trees/file bytes are checked before and after each child. Derived phase bindings and original conditional-registry bytes remain checked. Original authority and recovery-path symlink ancestry are refused. The missing-approval test proves no reservation or launch occurs. At review completion, actual recovery-approval.json and the actual recovery1 output root remain absent.

**Physical resource seam (lines 413–449, 505–536).** Each recovery project uses one active child. TMPDIR alone is changed in the inherited child environment, to recovery1/tmp/{spot,perp}. The isolated real-child test observes the exact inherited environment except TMPDIR and unchanged UID; the helper does not change HOME, account lock roots, native account identity, or virtual argv. Storage checks run while the shared project reservation is held, reject ancestry symlinks, ownership/owner mismatches, residual temp content and existing print/cache owners, and measure actual overlayfs/device/free bytes before launch. The floor is4GiB. No cleanup, forced unlock, kill, retry or account operation was added.

**Drain, receipts and cross-runner ownership (lines 75–301).** The minimal copied-core diff changes only cap1, optional child environment and the launch hook. Reservation/inherited-fd logic, deferred launch signals, draining wait, actual exit recording, output/source hashes, diagnostics, pending truth and unknown-owner refusal remain the accepted implementation. Exclusive phase receipts use recovery1 phase names and the recovery registry SHA; command receipts include untouched original_job and actual argv plus storage/provenance records. Original and recovery controllers share the original ART reservation namespace. Fresh tests confirm inherited live-child ownership blocks the other runner and its unfinished durable owner still blocks after child exit.

Read the new actual harmless-child SIGINT and SIGTERM receipts: failed phases, actual exit0/reaped child, second/third pending, launch_bookkeeping plus handled_signal errors, valid matching release hashes and output hashes. Signal-in-Popen likewise drains the actual child and preserves pending jobs. The nonzero probe retains actual exit7 with later jobs pending. No invented exit or successful storage-failure result occurs. Popen, post-guard, output-hash, command-finish, phase-finish and release failure paths are covered by the focused tests.

**Derived and conditional interfaces (lines 467–504).** The original unchanged bind-phase-inputs.py validates actual-schema synthetic all52 recovery-path raw accounts and writes a binding to the original production profile path and original registry SHA. Boolean audit rejection and audited negative eligibility remain strict. These52 synthetic files demonstrate the interface, not actual account proof. A later conditional registration must pass unchanged validate_supplement before its paths are transformed; the original all-eligible rule remains, and no speculative conditional registry/result is created. Recovery is not treated as a combination registration.

## Independent execution and limits

Independently ran `python -B /workspace/btc-alpha-beta-improve/task-artifacts/test-controller-recovery.py`: **18 tests, OK, 2.629s**, exit0. The new log is task-6-recovery-rereview-tests.log. Inspected actual newly retained signal/nonzero/reservation receipts after execution and recomputed corresponding raw and release hashes. Additional fixture file identities are retained in task-6-recovery-rereview-fixture-manifest.json. No unchanged repository/financial/native/account suite was run.

The actual first SQLITE_FULL failure supports the physical storage hypothesis. Moving temporary snapshots to overlay and reducing concurrency is a reasonable single authorized recovery; the4GiB admission check does not reserve storage or prove peak capacity. Spot1 and Coin1 can coexist; unrelated disk consumption or unexpectedly large snapshots can still produce another preserved failure. Full actual frozen input/vault byte hashing was inspected in the launch guards but was **not rerun by this scoped reviewer**; it remains required at real launch/completion boundaries. SIGKILL/machine failure remains outside graceful completion receipts, with inherited reservation and durable unknown-owner refusal retained. Synthetic binder/controller fixtures provide no monetary or native account qualification.

Only new review report/evidence/test log/fixture manifest and isolated test fixtures were written by this review. No original source/helper/registry/failure/input/vault/parent bytes, HEADs, HOME/UID, native account locks or private/network state were modified. No financial producer was invoked.

## Fixed approval interface and root next action

Root may now create the **new exclusive** task-artifacts/recovery-approval.json after checking these exact reviewed identities. Required fields are format=btc-edge-recovery-approval-v1, attempt=recovery1, approved=true; review is the actual {path,bytes,sha256} record for this fixed task-6-recovery-rereview.md; bound_files contains actual records for the recovery registry, recovery helper, implementation report and this independent review. Root must use actual final report/review hashes, then supply the actual approval SHA via --approval-sha256 on each fixed phase/kind launch. Do not substitute this report for the approval artifact. The registry already binds the original source/failure/parent evidence. A changed helper/registration/report/review requires a matching reviewed authority chain.

The full financial reviewer must later independently check both failed-attempt and complete recovery receipts/raws under the same measured sources, including complete audited real profiles and required conditional inventory. This engineering approval does not pre-accept those outcomes.

## Inspected and tested artifact identities

Paths below are relative to /workspace/btc-alpha-beta-improve/task-artifacts. The evidence JSON retains absolute paths, actual source measurements and count checks. The original file manifest retains every inspected original fixture identity; the separate review fixture manifest retains additional test artifacts.

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| run-registered-recovery.py | 27862 | `cdc8538d01b46963c12b8810b468cafd754b58303a69495cfb32f4e62d497185` |
| test-controller-recovery.py | 25523 | `7ef32ced9536cf4380a4417341ebe305231849be09b56d242b6ef0d51a51e661` |
| registered-financial-recovery1.json | 112155 | `d7bc23958cedc74626d9f082a18c52b18f2417e974931cac18ea618559a6d23b` |
| task-6-recovery-report.md | 21490 | `94cbc5a3cf6c1a4fc69a9edbf37fd83d8b89de67d6de95a586d574f72e8604b5` |
| task-6-recovery-review-package-root.diff | 47068 | `ce82b0208413beb1ff86c44f939d03c9f68221c6d9ec9112828ad817b02ef9d3` |
| task-6-recovery-controller.diff | 21102 | `96e4fbe898ba3fa3e73b585f80bc8d0386422213c9fe09c96a8cd5788ef8dddf` |
| task-6-recovery-core.diff | 2053 | `30688cc6488d611747bc948ef6624b425a6a6ffb71bb794464c204dff006325e` |
| task-6-recovery-file-manifest.json | 442328 | `60caa33eae409b54045e52cc699ca8751e0c8c4d17a30fceb4f38d60288e40d3` |
| prepare-source-freeze.py | 7759 | `3a78d0bb2c158cc0a5dc723ab149cb42b0f6456b416dd41fe6bd040cb876c2cf` |
| run-registered-phase.py | 19301 | `082d362d71977cec1e5f10afec47421cf8ab869c19ca0f064b5f8fba355977b1` |
| bind-phase-inputs.py | 13263 | `a07d5b63db39a9e0934dc9df887ccaaa059a7cab5c4d3a4d1337727eff3c9cf2` |
| registered-financial-commands.json | 42592 | `e58114f25f316d237860d2d6e6859d48614a57d69065524f6c256140c575fbfa` |
| reviewed-source-freeze.json | 1202697 | `b15129a0984d3a6f2bc1be1e1bfc700f9cd30a2023d257efcd608a408efac1c9` |
| controller-parent-freeze.json | 193 | `318e381353a83cb56f0c1206f81e2cb3990b54c5a2939003475ecde4979ad7e9` |
| first-financial-attempt-storage-failure.json | 12545 | `d2fc82347f44dc278b5700e0e144e247479fc78f787d1cf96ba10754ec288e40` |
| task-6-controller-fix2-rereview.md | 5816 | `d7e8bc06d247e3c077d8208dc79a52e48db56340fce3be75443d3d25d7b563e3` |
| task-6-recovery-tests-final.log | 2884 | `b4df9a48c62b83bb7a684d88899dc7948b8644cdfe259ad892513473bade5bbe` |
| task-6-recovery-rereview-evidence.json | 4913 | `3f6ad879f6477db5312732491710c686bf6fe144d00f9f4b9e3f90f7d1915725` |
| task-6-recovery-rereview-tests.log | 2884 | `b713654c84f1afe8915973d848dc60a6ca02095f93f48bdd3d5da342a1bd5828` |
| task-6-recovery-rereview-fixture-manifest.json | 166271 | `2694a7d49d43356638288e74367526798a8cd76d722bcb1c5e6606fc06a5434a` |
| task-6-recovery-final-review-brief.md | 3015 | `db813adb8dcaa4a496f637f1eac5c1b65e30015956039d9e34efc5c035a017d2` |
| task-6-recovery-root-brief-correction.json | 986 | `1637e0435090993803998123b58945cc807932ed15fdce4e521e3b168d6bdde0` |
