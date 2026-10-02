# Copier /proc cwd permission fix — ready for scoped review

Input SHA256 `72260dbdaccfb4298752e4b55b9e5ef7a6a9d86feda1a697719ea3e35fbf0ab4` is preserved exactly as `pack_completed_evidence_pre_proc_cwd_fix.py`.

Updated `pack_completed_evidence.py` SHA256: **`8ea9f39b233ccedd6d578aa46d64ef0a0d7af03bf8df2c07007d530997c99857`**.

The controller reported that the approved copier stopped before output creation on PermissionError reading `/proc/200/cwd`; its metadata identified an unrelated non-Python dockerd. This fix changes only `stopped()` reading order: read comm, identify Python, and resolve cwd only for Python processes. Every non-zombie/non-current process still has its argv checked with the unchanged relevant-process regex, so non-Python shell launchers remain blocked. No permission exception catch, UID bypass, source alias or process exclusion was added. Inaccessible Python or unreadable process metadata still fails closed. Existing vanished-process and zombie/current-process behavior is unchanged.

Pure mocked checks: **9 pass**, in `pack-proc-cwd-pure-checks.py` / `.log`. They cover inaccessible non-Python dockerd without any cwd lookup; relevant shell rejection without cwd lookup; local Python rejection; inaccessible unrelated/relevant Python fail-closed behavior; unreadable command failure; zombie/current-process skips; and unchanged unrelated readable Python acceptance. The fixture never enumerates real /proc, calls pack(), imports frozen modules or touches financial evidence.

`pack-proc-cwd-fix.diff` contains the complete three-line replacement for the original two-line cwd/Python condition. In-memory compilation/whitespace checks pass; AST comparison confirms all top-level code outside `stopped()` remains identical, including final-path/source/audit gates, manifest publication and copy behavior.

No bridge/helper-review/financial raw/receipt/source/HEAD/Git/cache/account files or processes were changed. No actual pack was attempted. The controller's initial failed receipt/log outside evidence roots remain untouched; this report does not claim that a new package exists. Independent scoped review is required before the controller's next actual attempt.
