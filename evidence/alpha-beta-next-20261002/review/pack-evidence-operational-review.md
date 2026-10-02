# Completed evidence copier — operational review

**Spec: REQUEST CHANGES. Code quality: REQUEST CHANGES.** Two narrowly reproduced findings block approval of this version. Product code, strategy results and the previously reviewed helpers are outside this review.

Reviewed `pack_completed_evidence.py` SHA256: `1ae25b7453f6852b6a4c1c90932b637c5ddce72750283d887e28fa4c1f142446`. The SHA was independently checked before source review and again after temporary verification.

## Findings

1. **P2 — Publish the completion manifest atomically after successful writing (lines 286–288).** The copier directly creates `MANIFEST.json` and then streams JSON into it. A write/close failure, disk exhaustion or interruption during publication leaves a partial manifest in an incomplete package. This contradicts the explicit contract that a post-copy error leaves an incomplete directory without a manifest. Exclusive open prevents replacement but does not make publication atomic.

   **Temporary reproduction:** patch only the final JSON writer to write `{"format":` and raise `OSError`. The exception propagates, but `MANIFEST.json` exists and contains that incomplete prefix. Source fixtures and copied evidence remain intact.

   **Correction:** write the complete manifest into a unique exclusively created temporary file in the new output directory, finish/close it successfully, and publish the final name with an atomic operation that cannot overwrite an existing destination. Preserve incomplete files under a name that cannot be mistaken for the completion manifest. Test a failure during write and before publication, plus successful publication and destination collision. If publication uses a hardlink, avoid turning cleanup failure after successful publication into a reported incomplete-package failure.

2. **P2 — Reject duplicate canonical file references (lines 173–179).** Validation requires five distinct labels but never requires five distinct canonical paths. Every label can point to the same single path and SHA, and the copier publishes a completed manifest. Thus the claimed separately bound canonical five can consist of one repeatedly referenced file, despite the duplicate-rejection and exact-five requirements.

   **Temporary reproduction:** keep the five required labels, replace the last four path/SHA pairs with the first entry's pair, and call the complete pack function with otherwise valid synthetic 64-account evidence. It accepts the inventory and writes the manifest; the number of unique canonical references is one.

   **Correction:** enforce five unique canonical child paths. Prefer the already approved controller's exact label-to-`<label>.json.gz` mapping, which also rejects a swapped or mislabeled reference without inspecting financial semantics. Continue verifying each file against its declared SHA. The copier need not infer adoption or reproduce the independently reviewed bridge's semantic proof.

## Source assessment

The implementation otherwise preserves the intended operational boundary. It copies bytes exclusively into a new output directory outside evidence roots, keeps original absolute paths and relative archive paths, hashes source and destination before/after copying and again before manifest publication, detects inventory changes, and binds the copied helper to the executing helper. It excludes the manifest from its own file list. Explicit required-artifact pins must exactly match the caller's supplied required paths; pinned result documents are also checked.

The final-account and audit join reconstructs 48 registered unscaled identities, 12 registered risk identities, and four sensitivity identities including raw SHA, then requires exact equality with independently audited identities and counts. It checks final readiness and pending flags, zero native/account-day claims, bound final/log receipts, current raw hashes and audit completion flags. This is an evidence-binding check, not a replacement for the financial audit or independent bridge review.

Inventory preserves scratch child-directory paths, the three named incomplete snapshots with their nonmonetary classification, vault records/log and optional figures. Other progress files and named cache/ZIP/BIN/State paths are excluded. Selected files must be ordinary files below the size limit, without symlink ancestors or escaping paths. Closed-process checks bracket inventory and copying. They do not reserve the entire process namespace against unrelated later launches; the root's already required fully stopped, exclusive operational window remains necessary.

## Actual verification

Read the complete copier source before inspecting its provided fixture implementation/log. Then executed that fixture in memory with added independent cases, using `PYTHONDONTWRITEBYTECODE=1`; all fixture roots were temporary directories. Financial/controller process detection was mocked for pack tests, so no real process was stopped or economic workload launched.

The supplied checks passed: active-process rejection through a mocked gate, missing final, pending final, incorrect final binding, symlink, size-limit and overwrite rejection; a complete synthetic 64-account plus five-canonical copy; byte and relative-path preservation; exclusions; helper self-hash; the three incomplete snapshots; figures and provenance. Added reviewed-pin mismatch and duplicate JSON-key checks passed. Both findings above were reproduced through the complete pack path, not merely inferred from source.

The original supplied log reports 39 copied files and the exact reviewed helper SHA; the independently rerun successful fixture also copied 39 files. Fixture gzip/PNG data are deliberately synthetic bytes: these tests exercise preservation and bindings, not archive parsing or financial validity. No claim is made that real final evidence exists or has passed these gates.

No real evidence package was created. No frozen runtime, source, Git HEAD, State, cache, HOME, active producer, controller, auditor or observer was modified. No financial tests, funds producers or network operations were run. Only this external review report was written. Correct and re-review the two findings before using the helper on closed real evidence.
