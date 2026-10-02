# Repaired remaining financial audit helper — review package

Scope: new external helper and temporary fixtures only. No frozen producer/assessor/checker, old audit/index, raw or cache was changed. No actual checker or producer was executed. This is an implementation handoff for independent operational review, not an approval of the repair or final financial results.

The helper defaults to read-only preflight and requires `--execute` to launch exactly two new independent checker processes, sequentially, for the derived original four-account projection and the untouched actual incumbent retry. Both new reports, receipts and logs are exclusive files under REVIEW. It never calls a financial producer, accesses account State, downloads data, or waits for a live job. Missing complete artifacts fail immediately.

Required future invocation after root authorization and actual final completion:

```
PYTHONDONTWRITEBYTECODE=1 python /workspace/btc-alpha-beta-next/review/audit_repaired_remaining_registered.py --final-report /workspace/scratch/alpha-beta-next/registered-final-repaired.json --out /workspace/btc-alpha-beta-next/review/financial-audit-remaining-repaired-index.json --execute
```

Omit `--execute` for a read-only preflight. A prior partial actual audit attempt is never silently reused: exclusive output collisions fail, preserving its evidence.

The helper binds exact final command output/log/exit0/source99/--final, requires no pending work, all measured accounts valid, rules ready, native0 and actualdays0. It independently hashes the immutable99 assessor and unchanged492d checker. It reads the original failed5 raw SHA3b958…, global12cal ed8c…, sourceaced, and exact actual receipt. The agreed projection schema is the original bundle with only four retained result rows and matching candidates-map narrowing, plus top-level derivation. Every retained row, complete journal, other metadata including the original5 risk_profiles, and original receipt/row checksums must match. It consumes the actual retry original1 with source/calibration/default10000/offset0 and795 sessions. Immutable99 evidence_fingerprints checks all four unity controls against the original bf1d… unscaled raw without dropping fields. Final account child SHA and all six groups must bind those raw rows.

Only old Spot7 and four sensitivity audits can be reused. Raw/report/command/log/checker hashes, exact command flags and calibration/baseline/unscaled context are validated, and the exact (kind, stage, candidate/scene, rawSHA) identities must exist in both old and repaired final reports. No glob is used. The failed original5 Coin audit is never reused in the accepted inventory. Existing source99 one-level manifest schema remains unchanged. Original failed reports, old index and all raw artifacts remain bound and preserved.

The resulting compatible index retains the existing audits/account_count/allchecks/completeness/finalSHA fields, plus provenance. It must contain exactly16 remaining accounts (Spot7 + projection4 + actualinc1 + sensitivity4), reconcile with the SHA-pinned unscaled48 index to64 exact identities, and preserve failed old incumbent separately. Adoption approval and independently replayed continuous proxy flags remain false.

Validation: 9 pure fixture tests passed, including multiple rejection subcases for financial/journal/component/market metadata mutation, profile removal, false derivation hashes, originalinc leakage, invalid/fake/native final flags, empty/failed operating checks, duplicate/missing identities, command/output/log/source/context mismatch, path collisions/symlinks, and default no-execution behavior. These exercise small functions and orchestration default; they do not claim completed actual-artifact preflight or end-to-end financial audit. Actual repaired artifacts do not yet exist. A separate reviewer should inspect full operational integration before launch.

Files and hashes:
- `audit_repaired_remaining_registered.py` SHA `8366717a1758ba57998c89baa067a4ef23443ba538222ae1e259bbc00df0fdc5`
- `test_audit_repaired_remaining_registered.py` SHA `b968994010b6ecd4780d62ca086ecfa2029371c08825120d50ec23548415ae82`
- `repaired-remaining-audit-fixtures.log` SHA `0a7c59c7233c067ce4cd2c3d419ed8a59ac86af33954373430dfe5ce851e907c`
- `repaired-remaining-audit-helper.diff` SHA `900195b60e43830c03f69e8b3895d5ee9c123d2fba90c421e879fc3d1cc49d47`
- `repaired-remaining-audit-fixtures.json` SHA `da7ca12ac6a013bf428d268b5e76ed7b3dc2b7ab68f17cf176db7da1fa0f51d2`
