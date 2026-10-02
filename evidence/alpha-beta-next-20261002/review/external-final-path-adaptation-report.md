# External final-report path adaptation — ready for scoped review

Only external consumer helpers were changed. No product/research source, Git/HEAD, financial producer, financial raw/receipt/index, prior approval document or repair-controller file was changed. Neither helper was run against real output. Tests import only these external modules and a small in-fixture reader/require shim; frozen research modules are not imported. No financial replay or bridge proof was performed.

## Immutable helper identities

| Helper | Preserved input SHA256 | Updated SHA256 |
|---|---|---|
| pack_completed_evidence.py | 88fceb73d43d0f1b16a176267ce9272f2856de66dcdeab1234442ebc0d8fba9e | 72260dbdaccfb4298752e4b55b9e5ef7a6a9d86feda1a697719ea3e35fbf0ab4 |
| verify_spot_adoption_bridge.py | ed4fabacf35be78b33e8763a1de20eae88798f940b8fa9ed88c504c62bf156fd | a33daded5ce53ec90d6648a20fba8ba2f9b60906d9733ccde6538bcb6382c549 |

The exact originals are retained as `pack_completed_evidence_pre_final_path.py` and `verify_spot_adoption_bridge_pre_final_path.py`. Unified changes are `pack_completed_evidence-final-path.diff` and `verify_spot_adoption_bridge-final-path.diff`, all in this review directory.

## Contract

Copier adds optional `--final-report ABS_SCRATCH_CHILD.json` and `--remaining-index ABS_REVIEW_FILE.json`; omission selects the original registered-final.json and financial-audit-remaining-index.json. Existing function calls retain these defaults. Bridge retains required `--final-report` and adds optional `--remaining-index`, defaulting to the original review index. No glob, fallback or newest-file choice occurs.

Selected final JSON must be an absolute ordinary file directly under the registered scratch root, with no symlink component or `..`. Selected remaining JSON must be an absolute ordinary nonsymlink file under the registered review root. Copier also requires that selected index be included in its archive inventory. The same-stem `.command.json` and `.run.log` bind the exact selected final path: exit integer0, source99, `--final`, exactly one `--out` equal to the supplied absolute path, output SHA and log SHA. Final full analysis identity remains source99/Python427f34/clean. The copier now pins that existing actual final source explicitly; the old copier had not independently checked it. The bridge now explicitly checks `--final` and final-log SHA, in addition to its prior immutable-source gate. These checks implement the requested negative regressions; no source equivalence or schema waiver was added.

Remaining index final SHA is exact. Registered identity coverage stays48 unscaled +12 risk +4 sensitivity, with 60 final accounts and four sensitivity accounts. Bridge audit kind/stage/raw/source checks remain intact; its exact64/remaining16 counts are explicit. The audit loop is relocated to a directly fixture-testable function without removing its checks. Copier continues the exact five canonical label/path/calibration mapping, approved docs pins, self hash, byte-copy/source hashes, partial classifications, optional figures and atomic no-overwrite publication with best-effort cleanup. `publish_manifest` is AST-identical to the reviewed input. The bridge body from project calibration validation through five-case command/gzip/row/six-group/source proof and output is byte-identical to the reviewed input.

Old failed reports, receipts and raw files remain evidence at their original paths/bytes. Selection of a repaired final does not relabel them or approve adoption. Any future repaired raw child must already be in the bounded copy inventory or be explicitly supplied with the existing required-artifact/hash flags; no arbitrary scratch recursion was introduced.

## Verification and limits

`PYTHONDONTWRITEBYTECODE=1 python review/external-final-path-tempfile-checks.py` passes. The script preserves prior copier regression cases with actual required source fields added to synthetic fixtures, and adds dual-report checks: old INVALID/new valid; legacy defaults reject old; explicit new+new-index succeeds; wrong old index, exit, receipt source/hash/out, missing --final, log pin, final source, native/days, allvalid, duplicated accounts, index final SHA, raw mutation, relative/out-of-root/nested/symlink paths reject. All checks run in TemporaryDirectory and the real process detector is stubbed only in these fixtures. The bridge boundary helpers use a fixture shim; full bridge execution and its market/Git checks were not run. The existing deeper checks are preserved for subsequent real review, not claimed newly executed.

Evidence: `external-final-path-tempfile-checks.py` and `.log`. In-memory compile, whitespace checks, unchanged manifest-function AST, and unchanged bridge calibration-to-output suffix all pass. Independent scoped review and actual repaired financial/index artifacts remain pending; stop here before real use.
