# Task 6 controller fix round 2 — DONE, pending scoped re-review

This wave changes only the external runner's handled-signal drain and phase helper's audit-pass check. T6-C2 source/vault/profile binding and T6-C3 reservation design remain unchanged. No financial producer, real source freeze/parent anchor, production profile, source commit, vault/market scan or mutation, native/private/account operation, network fetch, account lock/HOME/UID change, or subagent was used.

## T6-C1 residual

`finish()` enters non-raising signal handling before its first blocking `process.wait()` and stays there through log close, post-guard, output hashing and finish receipt. SIGTERM/SIGINT received during this interval are retained as actual handled-signal events and persisted in phase diagnostics after the wait completes. The final drain also records these signals instead of ignoring them. Original launch/receipt failures remain in the same failed phase result. Actual children finish naturally; the controller never kills them, invents exit codes, or releases ownership before actual reaping.

The new real harmless-process test reproduces the reviewer's sequence separately for SIGTERM and SIGINT: first Python child sleeps 0.35 seconds and writes `done`; second output already exists; a thread waits until the controller enters the real child wait, then sends the signal while the child is confirmed alive. Assertions establish that the controller returns only after actual exit, records `state:exited`, `exit_code:0`, `reaped:true`, and the complete `done` output SHA; the phase remains failed, the second job remains pending, and the post-guard runs only after child exit. A different-phase reservation is refused during drain; the known finished owner then releases normally and permits a subsequent reservation. Original inherited-descriptor/unknown-owner tests also pass.

## T6-C4

`validate_report()` now requires both `isinstance(monetary_audit, dict)` and `monetary_audit.get('passed') is True` for every original unscaled account and every additional existing report account. The amended positive fixture uses the actual `{"passed": true}` interface.

New tests use the actual assessor's 52-account identity/interface with synthetic raw files, rejecting absent audit, null, booleans used as the audit object, numbers, strings, lists, empty dictionaries, missing `passed`, and `passed` values false/null/0/1/string/list/dictionary. Boundaries are tested for an original account and an additional report account. All-explicit-failed-audit reports reject. Complete correctly audited accounts remain accepted when strategy eligibility is false and later-account inventory remains pending. No financial recomputation was duplicated in the controller.

## Exact checks and retained evidence

Two test commands were executed, from `/workspace/btc-alpha-beta-improve`.

First, the two new tests against the preserved pre-correction helper bytes demonstrated the existing failures (exit 1). Harmless children were explicitly waited during test cleanup, leaving no active child behind:

```text
PYTHONDONTWRITEBYTECODE=1 python task-artifacts/test-controller-fix2.py ControllerTests.test_first_handled_signals_during_failed_wait_reap_real_children ControllerTests.test_audit_requires_actual_boolean_pass_for_original_and_later_accounts > task-artifacts/task-6-controller-fix2-red-tests.txt 2>&1
```

After the two minimal helper corrections, one full amended covering command ran against the final helper bytes (exit 0):

```text
CONTROLLER_TEST_EXAMPLES=task-artifacts/task-6-controller-fix2-isolated-receipts PYTHONDONTWRITEBYTECODE=1 python task-artifacts/test-controller-fix2.py > task-artifacts/task-6-controller-fix2-tests-final.txt 2>&1
```

Exact final output tail:

```text
----------------------------------------------------------------------
Ran 24 tests in 0.993s

OK
```

The full output retains all test names. The 22 prior isolated checks are included because these shared failure/phase paths changed; no producer or market suite was run. `test-controller-fix2.py` is the authoritative amended suite; the original fix1 test source/report/results/manifests and independent failed probes remain untouched.

New evidence lives only in `task-6-controller-fix2-isolated-receipts/`. `both-signals-real-failure-drain/SIGTERM/` and `SIGINT/` retain the actual isolated original outputs, start/finish/not-started receipts, phase diagnostics and owner/release records. Copied evidence excludes reservation lock files. The temporary paths identify synthetic test evidence, not actual production/financial inputs. New positive export/report fixtures contain strict passed:true audits. `task-6-controller-fix2-verification.json` summarizes actual signal results and final/unchanged file identities.

## Before/final identities

| Helper | Before SHA256 | Final SHA256 |
|---|---|---|
| run-registered-phase.py | 628d549a8e485e5fe9db8384613db46dc828a035a7e1fc60cde1b9dbcd791bd7 | 082d362d71977cec1e5f10afec47421cf8ab869c19ca0f064b5f8fba355977b1 |
| bind-phase-inputs.py | 3169ffc501ec2a82ec4eaf02d20f877e01d1e243e59512462676c3d9f16e7e12 | a07d5b63db39a9e0934dc9df887ccaaa059a7cab5c4d3a4d1337727eff3c9cf2 |
| test-controller-fix2.py | new amended copy; original fix1 retained | 283e23c54634942392fe8bcdf69f12c90f667114cf07d30d89e1f1d12cabbb18 |

Unchanged freeze helper: `3a78d0bb2c158cc0a5dc723ab149cb42b0f6456b416dd41fe6bd040cb876c2cf`.

Unchanged original registry: `e58114f25f316d237860d2d6e6859d48614a57d69065524f6c256140c575fbfa`.

Preserved fix1 report: `5eff803f0e82865dac23bc128be1f88f3b18fe17f4d97c2f95e74abd33218375`; scoped failed rereview: `754d926819272a1e8ce3b8e9307a6c198bdcace43687f614b096d9c9b95eae72`.

Complete amended/new deliverables and every retained evidence-file byte count/SHA are listed in `task-6-controller-fix2-file-manifest.json`: the two changed helpers; new `test-controller-fix2.py`; this report; red/final full outputs; verification JSON; and every file in the new isolated-receipts tree. The manifest itself is the only additional deliverable. The root-owned fix2 brief and pre-fix2 copies were only read.

## Concerns and limits

No known unresolved concern from these amended checks; ready for independent scoped T6-C1/T6-C4 plus fix-new re-review. SIGKILL/machine failure remains outside graceful receipt generation; inherited lifetime ownership and durable unknown-owner refusal are preserved. This controller preparation does not establish actual financial acceptance or authorize a real queue.
