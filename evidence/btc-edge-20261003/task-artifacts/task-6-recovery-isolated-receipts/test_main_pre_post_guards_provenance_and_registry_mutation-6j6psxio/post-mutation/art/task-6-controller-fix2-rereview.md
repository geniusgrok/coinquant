# Task 6 controller fix2 — scoped independent re-review

T6-C1 residual: **ADDRESSED**.

T6-C4: **ADDRESSED**.

SPEC: **PASS** for this scoped fix.

QUALITY: **APPROVE** for this scoped fix. No new Critical/Important finding.

## Scope and immutable identities

Reviewed only the C1 controlled-signal drain residual, C4 strict audit-pass check, and breakage introduced by their fixes. C2/C3 remain closed; no whole-controller/producer/financial review was reopened. Read the fix2 brief, prior scoped failed review and retained probe, fix2 report, complete helper diffs and new test additions.

Actual file hashes match the supplied review identity:

| Artifact | SHA256 |
| --- | --- |
| task-6-controller-fix2-report.md | `3bb4e4266f822f6b34e515922852fef2d8a54a4ab2804433739ceea2ecda6934` |
| task-6-controller-fix2-review-package-root.diff | `584f3aaa6a5b4c6d070d06aeeb43a13817baca7093e26ef6003b454d2af81caa` |
| run-registered-phase.py | `082d362d71977cec1e5f10afec47421cf8ab869c19ca0f064b5f8fba355977b1` |
| bind-phase-inputs.py | `a07d5b63db39a9e0934dc9df887ccaaa059a7cab5c4d3a4d1337727eff3c9cf2` |
| unchanged prepare-source-freeze.py | `3a78d0bb2c158cc0a5dc723ab149cb42b0f6456b416dd41fe6bd040cb876c2cf` |
| unchanged registered-financial-commands.json | `e58114f25f316d237860d2d6e6859d48614a57d69065524f6c256140c575fbfa` |
| task-6-controller-fix2-file-manifest.json | `c2aeab3c452251458e3c5d92666cb7e9bd576e41e2e155a5d3d446c06dce8d34` |

Independently read and checked all 165 manifest entries against actual file sizes and SHA256: no mismatch. The old fix1 report/review/test/probe evidence remains separately retained. Concurrent forward-only repository work does not redefine these external helper identities.

## T6-C1 closure

`finish()` now sets `draining=True` before the first blocking `process.wait()` and keeps it set through log closure, post-guard, hashes and finish receipt. The handler records SIGTERM/SIGINT and returns while draining, so it cannot raise the prior RuntimeError into wait. Actual waiting/reaping completes before post-guard and output hashing; queued signal diagnostics are recorded and retain the failed phase status. Final drain also enters this non-raising state. The previous normal launch/receipt failure and child bookkeeping paths remain in place; no child-kill, invented exit, forced unlock or retry was introduced.

Read the new real harmless-child test for both SIGTERM and SIGINT. Its signal thread waits for entry into the actual child wait, confirms the child is still alive, and sends the signal while a second existing-output job has already caused failure. The test checks controller return only after actual exit; post-guard only after child exit; pending second job; failed phase; and reservation refusal throughout the drain followed by valid known-finished release. This directly exercises the residual window identified in the previous review.

Independently inspected the retained SIGTERM and SIGINT evidence under `task-6-controller-fix2-isolated-receipts/both-signals-real-failure-drain/`, rather than relying only on the report's passed flag. Both phase receipts contain:

```text
status: failed
pending_labels: [second]
all_children_reaped: true
first child: state=exited, exit_code=0, reaped=true
errors include launch_not_started and handled_signal
```

Both retained actual output files contain `done`. Their recomputed SHA equals the actual finish receipt's `a4c3ed04a95a3da14a9d235c83d868bed7c0f45cf7f3faa751ee8f50598d2211`. Verified each retained release references its owner file's actual SHA and asserts actual all-children-reaped. The roughly0.37s completion intervals are consistent with the harmless0.35s child, unlike the prior0.10s early return. This is synthetic lifecycle evidence, not real account execution.

## T6-C4 closure

`validate_report()` now requires `isinstance(monetary_audit, dict)` and `monetary_audit.get('passed') is True`. The check remains inside the existing union of all original52 unscaled identities and every additional account present in the report. Missing/null/false/non-dictionary audit objects and `passed` values such as1 or a string cannot satisfy the identity check. The positive fixture now uses the actual boolean passed interface.

Inspected the new failure/type test for both an original and a later account, including the report with every audit explicitly false. It preserves correctly audited negative strategy results and pending future inventory: audit validity is not confused with candidate eligibility. Other source/raw/export/parent/complete/reasons checks are unchanged. No financial accounting engine was duplicated in the controller.

## Validation and limits

Read the preserved red output against pre-fix helpers: the two new tests failed as expected. Read the final output against reviewed helper bytes: **24 tests, OK, 0.993s**. The final amended suite includes the previous22 isolated checks because the shared paths changed. The new test file and evidence tree preserve earlier failed artifacts. No redundant suite or independent probe was run in this review because the exact reported failure cases are directly covered by the inspected code, tests and actual retained receipts.

No helper/worktree/source/registry change, commit, subagent, actual source freeze/parent anchor/production profile, full producer, Coin suite, native/private/account/network operation, vault scan or mutation, HOME/UID/account-lock change occurred. Only this new report was written. This scoped approval does not establish full financial inventory, independent finance acceptance, an adoption outcome or native qualification. SIGKILL/machine failure remains outside graceful receipt guarantees; inherited reservation ownership and durable unknown-owner refusal remain the existing fail-closed limit.
