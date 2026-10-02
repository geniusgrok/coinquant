# Diagnostics exporter — scoped calibration fix review

**Spec: PASS. Code quality: APPROVE.** The Spot metadata incompatibility is closed for helper SHA256 `921496bd345a166a434b1077ce810fb7d31c012fe7b09e8ae13960e349258dc3`.

Compared the complete diff against preserved initial helper SHA `730d55a6ea5f3c75a47efbbd610db938c588b763c6e08a09d2be144da5f75c4a`. The initial finding/report remains unchanged. The fix requires explicit Spot and Coin calibration files, verifies each exact raw SHA against the accepted final report before creating CSV, copies the reported profile scale directly, rechecks both original calibration byte strings before provenance publication, and records both calibration SHAs. It no longer requires nonexistent Spot `metadata.risk_profiles`. No metric or scale is recalculated.

Independently executed an isolated synthetic fixture with48 unscaled rows,12 actual-risk rows and4 registered sensitivity identities. Spot risk metadata deliberately omitted `risk_profiles`; its bound calibration contained7 profiles, while the Coin calibration contained the complete global12. Checks passed:

- All64 emitted identities are unique and all12 actual-risk scales preserve their exact input strings.
- Two baseline-control match/gain fields remain blank; the ten candidate risk match fields are populated, including false outcomes.
- Registered CAGR, fees, beta, volatility and fraction units preserve reported values; unscaled/sensitivity calibration fields remain blank.
- Assessment/calibration input bytes remain unchanged, and provenance's calibration and CSV hashes match.
- Wrong Spot or global calibration SHA rejects before CSV creation.
- Existing output rejects without changing its bytes.
- Calibration byte mutation after CSV writing rejects and publishes no provenance.

Approval covers this reporting fix only. A CSV left after a failed post-write check lacks provenance and remains incomplete. The exporter still relies on the independently accepted final for financial validity and registered inventory semantics; it does not replace the final64 audit, actual CSV-value review, source bridge or adoption decision.

No frozen module import, real assessment export, monetary raw load, producer/checker/test execution, source/Git/State/cache/HOME mutation, account/network action or active-process operation occurred. Only external-helper import, temporary synthetic fixtures and this report were used.
