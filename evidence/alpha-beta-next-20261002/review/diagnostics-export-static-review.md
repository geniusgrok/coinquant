# Registered diagnostics CSV — static review

**Spec: REQUEST CHANGES. Code quality: REQUEST CHANGES.** One actual source-schema incompatibility prevents the intended64-row export.

Reviewed helper SHA256: `730d55a6ea5f3c75a47efbbd610db938c588b763c6e08a09d2be144da5f75c4a` (`export_registered_diagnostics.py`). No real export or financial checker was run.

## P2 — Spot risk metadata has no risk_profiles dictionary

`append()` reads `report['inputs']['risk_' + kind]['metadata']['risk_profiles'][candidate]` for every risk account. This exists for Coin, but the frozen Spot producer writes calibration SHA at the top level and profile details inside individual raw rows. Its top-level metadata has no `risk_profiles`. Immutable99 `metadata()` copies that top-level object, while `consume()` preserves only that metadata and analyzed accounts. Therefore every real Spot risk row reaches `KeyError: 'risk_profiles'` before CSV creation.

Neither alternative report field supplies the missing reported scale: `risk_calibrations.spot.profiles` contains candidate names only, and `training` contains candidate/baseline statistics rather than the scale string. Do not recompute a scale from those statistics or invent a metadata field.

**Correction:** accept the exact actual Spot project-calibration document as an explicit input, verify its raw SHA against `report['risk_calibrations']['spot']['raw_sha256']` and the risk metadata calibration SHA, and copy each `profiles[candidate]['scale']` value directly. Using explicit bound calibration documents for both kinds is also consistent, provided Coin's recorded profile agrees. Bind the actual calibration path/SHA in export provenance. Preserve blank baseline match/gain fields and reported-value-only semantics.

## Other static conclusions

The financial summary, validation regression beta, validation USDT annualized volatility, daily-closing MDD, fees/funding, registered CAGR/MDD and sensitivity capital/offset field paths match immutable99. The two unity baselines are excluded from `report.risk` by design, so their match/gain cells correctly remain blank; the ten candidate risk rows have reported match/gain diagnostics. Unscaled and sensitivity rows correctly have no actual-risk calibration cells.

The exporter checks60 main accounts plus4 sensitivity entries and64 distinct emitted identity strings. It does not independently reconstruct the registered candidate/scenario matrix or financial acceptance; it relies on the externally accepted final, as its scope states. CSV return/MDD/volatility/gain values remain fractions, beta dimensionless, scales ratios and fees/funding USDT. No metric is recomputed. Distinct Coin registered CAGR365.2425 versus shared daily/Spot365.25 annualization is accurately disclosed.

Exclusive output/provenance creation and unsafe output-path refusal prevent normal replacement. The source assessment is reread before provenance publication, and provenance records assessment/CSV/tool hashes. A failed export can leave CSV bytes without provenance; such output is incomplete and must not be delivered as accepted evidence. Tool/source hashes do not by themselves establish financial or adoption approval.

## Checks actually performed

Read the complete exporter and the relevant frozen `alpha_assessment` and Spot producer field-construction source without importing frozen modules. A synthetic temporary fixture with the actual Spot metadata shape reproduced `KeyError('risk_profiles')` through `main()` with no output created. A separate existing-output fixture rejected overwrite and preserved the original bytes. The synthetic inventory merely supplies enough declared entries to reach the field access; it is not a financial/registered-matrix proof.

No real assessment export, monetary raw load, frozen import, producer/checker/test execution, source/Git/State/cache/HOME mutation, account/network operation or active-process change occurred. Only the external helper import, temporary fixtures and this review report were used. Actual CSV values and full64 identity reconciliation still require final evidence review after the repaired final and independent financial gates pass.
