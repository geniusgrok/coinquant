# Coin incumbent repair controller — scoped provenance fix review

**Spec: PASS. Code quality: APPROVE.** The sole P2 from the initial operational review is closed. This approves the exact external controller bytes within the already authorized one-attempt workflow; it does not establish successful financial repair or adoption.

Reviewed helper SHA256: `957d4b0171469351c38b1a27bdc579a368dc0408fa37c348686d24aeb1c6c5d8`.
Preserved initial helper SHA256: `083068bd2bd20070f81237ef6be4459cd8dcddbbdfbeae1d2ffd035c4fafdbdc`.

Independently verified that the entire new helper is byte-for-byte identical to the preserved initial version after exactly one replacement: `zip_bytes_verified_by_approved_restore` becomes `zip_bytes_must_be_verified_by_approved_restore`. All functions except the catalog's returned field are AST-identical. Execution, predecessor wait, persistent queue lock, one-attempt intent, restore coverage, source/input bindings, six-group comparison, projection and final-assessment gates are unchanged.

The persisted pre-restore intent now states a verification requirement rather than claiming completed ZIP verification. A failed restore leaves that truthful requirement intact, creates no success receipt and does not permit relaunch. Successful verification continues to be evidenced by the subsequent actual restore receipt and its existing SHA binding; the operational gate has not been weakened.

Independently ran the updated pure temporary fixture after inspecting its source. All23 checks passed: the original21 plus assertions on intent semantics before restore and after an injected restore failure/relaunch refusal. The fixture extracts only eight pure assessor function ASTs and performs no frozen module import; its source-proof stub applies only to synthetic fixtures. Exact single-field byte replacement and unchanged execution/gate/projection function ASTs were separately asserted.

The original request-changes report remains preserved at `repair-coin-risk-operational-review.md`. Its full-source findings, compatibility checks and limits carry forward, with the sole provenance finding now closed. Root may proceed with the reviewed single waiting-controller workflow after its operational prerequisites; no second attempt, changed source, ignored evidence field or economic-parameter variation is approved.

No real controller entrypoint, restore, producer, account/State/cache operation, frozen import, source/Git/HOME change or network action was performed by this review. Only temporary fixtures and this report were written. Actual replay equality, repaired final, independent financial audit and any adoption decision remain subsequent evidence gates.
