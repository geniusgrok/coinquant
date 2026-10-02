# Remaining audit queue review — CHANGES REQUIRED

Reviewed external queue SHA256 `b9dabb63236db0a0c16a8f965ddb0afe964cb1a6b0a6b49b88861bed6f3d1c3c` against unchanged independent checker SHA256 `492d46ff9bbff72f1291ad77988fbf8478b35fd880c818e1d3979a6215f1897c`. Do not treat the current queue's final index as a complete independent audit of the final assessment. Two material provenance/completeness gaps require a narrow external-queue fix before launch.

## Finding1 — completed assessment and audited raws are not linked end to end

`command_receipt` checks only `exit_code==0`; it never checks the report file's actual bytes against `receipt.output_sha256`. Coin risk and combination paths are read from report inputs, but their current bytes are never compared with the report's recorded `raw_sha256`. Sensitivity paths are extracted from the command list without reconciling their SHA/identity set against `final.sensitivity`. `final.pending==[]` alone does not prove that the independent queue inspected every corresponding case.

The checker does bind each newly audited raw to its currently calculated SHA and frozen producer source. That is useful, but it does not prove those bytes are the exact artifact assessed in the final report. A changed/replaced path or mismatched receipt could cause the independent index to describe a different account while still showing checks passed. The index records only counts per artifact, so duplicate/missing case identities are not detected. One-level manifest traversal also accepts the same child twice.

Pure fixtures demonstrated that a completed-command receipt with an intentionally incorrect output SHA is accepted, and a manifest containing the same SHA-valid child twice invokes the audit twice. No actual evidence was changed.

Required closure: verify each consumed assessment's current bytes against its completed receipt; verify risk/combo root raw or manifest SHA against the corresponding report input; reconcile exact sensitivity identities/raw hashes with final report entries; and reconcile the actual audited case-identity set, including duplicates/missing/extra cases, with the final assessment's actual risk/combination/sensitivity inventory. Preserve explicit inapplicable/rejected obligations rather than inventing expected accounts. Verify manifest roots as well as children and retain their binding in the index. These checks can fail closed without touching original artifacts.

## Finding2 — same-raw audit reuse silently skips required calibration/comparison context

The existing-output branch of `audit_one` checks only `report.raw_sha256`. It skips checker identity verification, the audit command receipt and all requested calibration/baseline/unscaled context. Therefore a previously generated same-raw audit that did not perform training-scale recomputation or pre-cutoff ledger equality can be reused as though this queue supplied and verified those inputs.

A pure fixture created an existing same-raw audit with no comparison evidence and passed three nonexistent paths as `calibration`, `baseline` and `unscaled`. The queue reused the report and appended `all_checks_passed:true` without reading or rejecting any of those paths. This directly defeats the promised additional risk checks on the reuse path. It does not require changing a raw financial file.

Required closure: bind each audit execution/reuse to the checker SHA and exact required input context, including calibration SHA and the baseline/unscaled audit SHAs and kind. On reuse, verify the original audit receipt/output hash and matching context plus the required risk result fields; otherwise reject or schedule a new exclusive audit artifact without overwriting the older result. Preserve previously failed audits and their false flags. Sensitivity/combo audits should continue to omit training-prefix equality intentionally.

## Checked behavior that is otherwise correct

The early Spot path waits for its derived unscaled audit collection and completed-risk receipt, verifies the actual early raw/calibration hashes, and passes baseline/unscaled references only for risk. Coin risk waits for completed registered-risk assessment and the actual unscaled Coin audit. Applicable combination inputs and predeclared final sensitivity command paths are used without starting new financial replays. Checker subprocess failure retains the log/receipt and stops the queue; checker-internal failed account checks remain false in the index. The index explicitly states `adoption_approval:false` and `continuous_proxy_independently_replayed:false`.

The unmodified checker independently reconstructs money/statistics, validates frozen raw producer metadata, recomputes the actual731-day scale when given the baseline audit, and requires the actual pre-cutoff ledger fingerprint when given the unscaled audit. No new issue was found in this queue's choice to supply those comparisons only to risk accounts. The findings concern whether the queue proves that those specific checks actually ran for the exact final-report artifact set.

## Verification and scope

Independent pure-function regression: `review_remaining_audit_queue.py`; proof: `remaining-audit-queue-review-proof.json`. It imported the external queue without calling `main`, substituted temporary external fixture paths, and replaced the audit callback for duplicate-manifest testing. All three observed gaps reproduce. Checker/producer subprocesses0; account replays0; State invocations0; downloads0; product/cache/source/HEAD mutations0. Only external review/proof/temporary fixture files were written.

No remaining-risk/combo/sensitivity account or full-matrix result is accepted by this review. Await corrected queue for scoped re-review.
