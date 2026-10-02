# Completed evidence copier — scoped fix1 operational review

**Spec: REQUEST CHANGES. Code quality: REQUEST CHANGES.** The canonical-reference finding is closed. Atomic publication addresses the original partial-manifest defect, but one explicitly requested direct failure regression remains open.

Reviewed SHA256: `e8b7e9f012f2245dd462cfaf884999d257a8991e8a7c3c79ca14bee805de1be9` for `pack_completed_evidence.py`. Compared its complete diff against preserved pre-fix1 bytes, read the relayed findings, checked the changed canonical fields against the approved canonical controller, and independently reran the updated temporary fixture with one additional failure injection. The original review report remains unchanged.

## Remaining finding

**P2 — Do not report publication failure when only post-publication temporary cleanup fails.** In `publish_manifest`, the successful atomic `os.link` is followed by an unconditional `temporary.unlink` in `finally`. If unlink raises, that exception propagates through `pack` even though a complete `MANIFEST.json` has already been published. This violates the promised failure-without-manifest outcome and leaves callers with inconsistent completion status. The original finding explicitly requested avoiding this cleanup-after-publication failure mode.

**Independent reproduction:** through the complete `pack` path using synthetic evidence in temporary directories, inject `PermissionError` only for removal of its `.MANIFEST.*.tmp` after publication. Result: `pack` raises `PermissionError`; `MANIFEST.json` exists, parses successfully with format `completed-evidence-byte-copy-v1`, and one temporary hardlink remains. No financial files are involved.

**Correction:** make cleanup best effort once publication has succeeded, preserving the valid manifest and successful operation; an undeleted temporary hardlink may remain as operational residue. Before publication, preserve the original serialization/write/fsync/link error rather than masking it with a cleanup error. Do not delete a successfully published manifest to manufacture an incomplete result. Add focused checks for post-publication cleanup failure and for cleanup failure while handling an earlier publication error.

## Closed portions

- **Canonical references: CLOSED.** The exact label-to-`<label>.json.gz` mapping, five distinct required labels, expected scenario mapping and strict boolean calibration mapping match the existing controller's emitted schema. Duplicate references, incorrect scenarios and incorrect calibration flags reject before creating output.
- **Partial final manifest: corrected.** The helper now creates an exclusive same-directory temporary file, serializes the complete manifest, flushes and fsyncs it, closes it and publishes through an atomic no-overwrite hardlink. Serialization, write and fsync failures leave no final manifest; an existing final manifest is preserved. The remaining finding concerns only the subsequent cleanup/error semantics.

## Actual checks and scope

All 20 checks reported by the updated temporary fixture passed on independent execution, including the three canonical regressions, serialization/write/fsync failures, existing-manifest preservation, normal complete-copy publication, original exclusions and byte/path/self-hash preservation. The successful synthetic package contained 39 copied files. The additional full-path post-publication cleanup failure reproduced the remaining finding above.

Process detection was mocked for fixture execution. Tests used only temporary roots and synthetic evidence; bytecode creation was disabled. No real output was created and no frozen import, product test, financial producer, source/Git/State/cache/HOME mutation, account operation or active-process change occurred. Only this external review report was written. This review is limited to the two original findings and their direct regressions; it makes no adoption or financial inference.
