# Copier /proc cwd fix — scoped operational review

**Specification: PASS. Code quality: APPROVE.** No material finding in this exact fix. The reported environment-guard defect is addressed without weakening the existing relevant-process gate.

Reviewed helper: `pack_completed_evidence.py`, SHA256 **`8ea9f39b233ccedd6d578aa46d64ef0a0d7af03bf8df2c07007d530997c99857`**. Preserved original: `pack_completed_evidence_pre_proc_cwd_fix.py`, SHA256 `72260dbdaccfb4298752e4b55b9e5ef7a6a9d86feda1a697719ea3e35fbf0ab4`.

The failed actual receipt records exit1 and no manifest. Its log shows PermissionError at the original unconditional `/proc/200/cwd` resolution. Source inspection confirms this is the first `stopped()` call, before inventory/copy/output creation. The controller identified that process as unrelated dockerd; this review did not inspect live /proc.

At `pack_completed_evidence.py:95`, `stopped()` now reads comm and resolves cwd only if comm identifies Python. It still reads every non-current, non-zombie process's argv and applies the unchanged relevant-process regex, including shell launchers. Unreadable Python cwd, argv, comm or stat still raises; no PermissionError catch, UID/HOME exemption, account-lock bypass or blanket process exclusion was added. Existing current-process, zombie and vanished-process handling remains unchanged. Relevant Python with inaccessible cwd fails closed even before the final blocked-PID check.

Independent verification:

- Recomputed both exact helper hashes and verified the complete byte change is precisely the supplied three-line replacement for the old two-line condition.
- Compared ASTs of all top-level code except `stopped()`: exact equality. Copying, fingerprint/inventory, manifest publication, financial/source checks, final-path handling, required-artifact pins and all three process-guard call sites are unchanged. In-memory compilation passed.
- Executed22 independent synthetic checks using only the AST-extracted `require` and `stopped` functions with fake /proc records and pure paths. No module import or real /proc access occurred. All22 passed: inaccessible non-Python cwd is never consulted; all nine existing regex categories block non-Python shell launchers; local Python and Python argv pointing into an evidence root block; inaccessible Python/relevant-Python cwd and unreadable argv/comm/stat fail closed; unrelated readable Python passes; current/zombie/vanished cases retain their behavior; enumeration continues past unrelated dockerd to a later relevant shell.
- Read the implementer's nine-case fixture and log as supporting evidence; reviewer outcomes are independently recorded in `pack-proc-cwd-fix-operational-review-proof.json`, SHA256 `3e69216468b69f6842e788b5a6633429d8ca32f86a5c1473d6363ca35ad55ba5`.

No actual pack, live process enumeration, financial/runtime import, financial test, source/HEAD edit, State/account lock access, cache access or process change was performed. Only this review and its proof were created. No child agents were used. A later actual attempt must pin the new helper SHA above; the failed attempt's original command/receipt/log retain their original identity.

This approval closes only the reported copier process-inspection defect. It neither creates nor verifies a package and does not extend financial/adoption approval. Earlier code,64-account,canonical5,adoption and documentation reviews are unchanged by this exact helper-only fix.
