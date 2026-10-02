# Exact Spot adoption bridge tool review

Tool: `/workspace/btc-alpha-beta-next/review/verify_spot_adoption_bridge.py`

Reviewed SHA256: `044d7006f9daa9c20ad17047f02b34cb906cf8eedab3ad9c545907e02b610483`.

**Spec: REQUEST CHANGES. Quality: REQUEST CHANGES.** Two evidence-gate defects remain. This is a tool-source review, not a completed five-account equivalence audit or adoption approval. The controller was notified immediately; no actual bridge/full-account verification was run.

## Findings

1. **P2 — Reconstruct exact independent-audit coverage instead of trusting aggregate index declarations (`lines67–85`).** The unscaled index is accepted when `account_count == 48`, without counting its actual report accounts or matching them to final-report identities. The remaining index is accepted on its recorded final-report hash and aggregate booleans. Both then iterate `audit['audits']`, but neither rejects an empty list, duplicate report/account identities, missing accounts, or audit raw identities unrelated to the corresponding final account. Checks of each present audit's SHA/flags only establish local consistency, not complete coverage. In particular the unscaled index has no final-report binding at all.

   **Concrete pure reproduction:** executed the exact audit-loop AST from this tool with immutable analysis99 `require/read_json` and two tiny temporary index files. `{'account_count':48,'audits':[]}` and a remaining index with the matching mock final SHA, all required flags true, and `audits:[]` were both accepted and entered into `audit_bindings`. Zero independent reports were read.

   **Correction:** rebuild unique `(kind, stage, candidate/scenario, original_raw_sha256)` coverage from the referenced audit reports, check per-account reported-complete/check-passed status, and compare the exact set with the final report's registered48 unscaled accounts plus actual risk/combo/sensitivity inventory. Reject duplicates, missing/extra identities and stale raw hashes; derive counts rather than trust them. Preserve truthful manifest-child raw identities. Reuse the already reviewed remaining-audit inventory semantics where appropriate; no financial rerun is required to validate these identity sets.

2. **P2 — Bind the canonical command to its actual runner, checkout and output (`lines132–143`).** The gate checks only that the string `research.adoption_spot` occurs somewhere in argv. It does not require it to be the `-m` target, verify recorded `cwd`, or link the command's `--out` to the JSON whose bytes were compressed and compared. Thus this receipt does not establish that the matching account came through the canonical shared session. Immutable `a.consume` intentionally accepts research accounts too; it verifies candidate/calibration/source/financial shape but does not require the top-level or row `execution='canonical_shared_session'` markers.

   **Concrete pure reproduction:** the exact command/source/case/log assertions accepted argv `['python','-m','unrelated.runner','--note','research.adoption_spot','--scenario','base','--out','/unrelated/output.json']` and `cwd='/unrelated/checkout'`, with otherwise matching synthetic receipt hashes. No subprocess was executed.

   **Correction:** validate the explicit canonical command shape (`-m research.adoption_spot`, exactly one scenario and output, no unexpected execution/limit arguments, calibration only on the designated case), expected adoption checkout, expected label and raw-output path. Check the producer's canonical execution markers and their rule/profile identity before consuming/clearing rows. Validate that required launch bindings are actually present, rather than merely iterating arbitrary caller-provided keys. Apply analogous explicit module/cwd/final-output checks to the final assessment receipt. Keep the existing exact Git/full-Python verification and independently reviewed exact-head prerequisites; no source override is needed.

## Reviewed correct behavior

- The hard-coded immutable analysis99 identity matches the actual helper interfaces inspected. `source_identity()` uses its module ROOT; `verify_source` reconstructs committed full Python hashes. `load_project_calibration(path, global_cal, 'spot')` is the correct current API, and `risk_calibrations['spot']['raw_sha256']` is the emitted report field.
- Exactly five unique labels are required and paired with the four registered stresses plus calibrated base. Source identities for frozen references remain exact8ca; adopted Git/Python identity is reconstructed, not blindly accepted from caller arguments. Committed spec/protocol hashes are checked.
- The corrected canonical producer exposes the research identity/profile fields needed by immutable `consume`. Risk consumes all seven actual Spot base accounts with the exact project calibration; the selected calibrated base is compared to its actual frozen counterpart. Global/project calibration equality is checked with the immutable helper.
- Original selected rows are bound to final-report raw hashes and evidence fingerprints. `consume` enforces actual complete starts, original timing/archive gates, monetary schema, source and input hashes. The six fingerprint groups retain financial/audit, fills, daily, ownership, operating and remaining-original fields; the tool compares complete dictionaries without new exclusions or monetary/timestamp normalization.
- Each canonical compressed SHA is checked, decompressed bytes must equal the original command-output SHA, and the compression receipt is bound. Case inputs, log SHA, receipt hashes and review bindings are retained, subject to finding2's missing command linkage.
- Output uses exclusive creation and truthfully leaves `adoption_approved=False`, independent adoption review pending, native/account days zero, and diary execution bound to frozen research. Assessment/forward source gates are not edited or bypassed.

## Verification limits

Read the full tool and actual analysis99 APIs, fixed canonical producer metadata, command receipt producers and both audit-index schemas. Ran only the two small AST-extracted gate fixtures above with temporary synthetic files and immutable analysis99 validation helpers. No full financial artifact, private account, Coin State, market cache, producer run, download, source edit or subagent was involved. The final global study and canonical five remain pending; this review makes no performance or actual equivalence claim.

Re-review a corrected exact tool SHA before creating the official bridge proof. Bind that verifier SHA and its invocation/receipt to the retained proof provenance as well; this external verifier is not identified by either repository's Python-source digest.
