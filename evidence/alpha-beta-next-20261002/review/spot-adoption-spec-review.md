# Conditional Spot shared-default independent review

BASE `99fcf005d2cb15c13bb37322b65ab2863b19d65e` → HEAD `7ac94e12b41b9958072c9ff080983eea1a3cbd83` in `/workspace/btc-alpha-beta-adoption/spotquant`.

**Specification: FAIL / changes required. Code quality: REQUEST CHANGES.** One confirmed material compatibility defect blocks freezing this source for the required five-account proof. This is a conditional proposal review, not an adoption or financial conclusion.

## Finding

**P1 — Canonical replay emits an incompatible research identity.** `research/complete_spot.py:206` creates `research_identity` from `adoption_spot.risk_identity`, whose fields at `research/adoption_spot.py:21` describe the diagnostic replay but omit the established account schema. Immutable analysis99 `consume` requires `components`, `spec_sha256`, `risk_scale`, `core_mode`, `core_fraction`, candidate and calibration SHA. The canonical identity currently contains only calibration_sha256, candidate, cutoff_ms, execution, profile, profile_sha256, rule and scale.

Independently generated a real three-session **synthetic** canonical row with `research.adoption_spot.measure('base', ..., limit=3)`. The unchanged assessor consumer, using matching synthetic input metadata and real committed-source verification, fails immediately with `KeyError: 'components'`. Its missing remaining identity fields would also fail after that key alone is supplied. The same shape is emitted for unscaled and calibrated accounts. The six-group test passes because evidence fingerprints intentionally exclude research_identity, so it does not establish consumer compatibility.

Emit the established atr-stop row identity (`components=['atr-stop']`, actual spec SHA, risk_scale, core_mode=None/core_fraction=0, candidate and actual calibration SHA), retaining honest adoption/runtime/profile provenance as explicit additional metadata. Do not change immutable analysis99 helpers, relax their checks, or relabel frozen source/raw evidence. Add an offline canonical-output → real consumer regression for both unscaled and file-bound calibrated forms, in addition to six-group equality. The calibrated form must retain its actual calibration raw SHA and profile.

## Other scoped boundaries inspected

- Completed ATR14 is computed from the preceding close before replacement, with a timestamped14-range checkpoint queue and version/type/chronology checks. Persistent trail remains.28; decision copies carry the adaptive trail/native floor. Follow catch-up is unchanged.
- Decision floor status/campaign boundary, actual filled-position peak, through-mark ordinary grouped reduction, protection rebuilding, exits-first BUY deferral and free-cash/whole-account-cap/rounding/minimum clipping match the selected-policy branches inspected. Partial-sale remainder uses the same helper and committed positions/cached owners.
- Cycle performs rule/checkpoint/pending-state and diagnostic-identity checks before constructing/recovering Lifecycle. Focused tests cover legacy flat/held/pending and malformed state with no recovery call and unchanged state. Authorization/live block, normal unknown/cancel/replace recovery code and adapter configuration are unchanged.
- Diagnostic scale is validated through the existing registered profile reader, bound to state/file/profile identity, fixed after the cutoff and applied only to new BUY allocation; default remains1. Canonical measurement checks file identity again on completion. No public live scale setting is introduced.
- The explicit canonical meter seam bypasses Policy/configured and uses the shared session/Model/State/decision/Lifecycle/venue/audit/archive path; hook-exclusion tests execute that boundary. Original financial/operating fields, including filters, remain present. Current tests establish local six-group equality against the research path on the new source, not frozen8ca full-history equality.
- Source/spec/forward assessor gates were not changed. No other material defect was established during this review; that statement does not replace the required full exact-source proof.

## Independent verification

- Full exact-head archive in a temporary standalone checkout: `python -m unittest discover -s tests -v` — **208 Spot tests passed in6.044s**. Log `/tmp/spot-adoption-review-tests-7ac94e12.log`.
- Actual three-session synthetic canonical output → unchanged assessor `consume`: **fails KeyError('components')**, as described above. No public history or full financial replay was used.
- `git diff 99fcf005... 7ac94e12... --check`:pass.
- Current source identity independently read: head7ac94e12, dirty=false, full Python SHA `7d4985f9176cd1d6a995be6c4fbcff17ffc5dad832218fae594eeb1b8b76a380`.

Read the implementation/boundary briefs, report, all changed source/tests/docs and surrounding actual execution paths. No implementation edits, commits, child agents, Coin State/tests, public download, cache/private account access or producer/analysis HEAD changes. Root-owned PROJECT_STATE remained untouched. Only this external review report was written.

After fixing the schema and scoped re-review, the controller still needs complete original finance, final selection and the five actual canonical accounts bound to the exact adopted source, with all six evidence groups equal through immutable analysis99 helpers. Native execution and actual account-days remain zero; failure of any bridge/selection gate requires the incumbent fallback.
