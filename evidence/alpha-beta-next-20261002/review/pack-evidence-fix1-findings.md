# Copier review fix1 — received findings

Reviewed helper SHA256: `1ae25b7453f6852b6a4c1c90932b637c5ddce72750283d887e28fa4c1f142446`; original bytes preserved as `pack_completed_evidence_pre_fix1.py`.

The controller relayed two independent TEMP-fixture reproductions:

1. Opening MANIFEST.json before serialization leaves a partial final manifest on serialization/I/O failure, violating the incomplete-without-manifest contract. Required correction: exclusive same-directory temporary file, complete write/flush/fsync, atomic no-overwrite publication, and temporary-file cleanup on failure.
2. Five distinct canonical labels could all reference the same path/SHA. Required correction: exact unique label-to-<label>.json.gz mapping and correct calibrated/scenario metadata.

Only these copier defects are in scope. No original financial input, frozen source, Git state, producer or real output is modified or executed. Independent scoped re-review remains required.
