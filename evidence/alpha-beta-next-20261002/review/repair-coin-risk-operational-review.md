# Coin incumbent repair controller — independent operational review

**Spec: REQUEST CHANGES. Code quality: REQUEST CHANGES.** One narrow provenance finding remains in the initial fixed version. No execution-gate or strategy change is requested. The actual restore and strict six-group replay gates are present.

Reviewed SHA256 identities:

- `repair_coin_risk_incumbent.py`: `083068bd2bd20070f81237ef6be4459cd8dcddbbdfbeae1d2ffd035c4fafdbdc`.
- Proposal: `3f10028a7c8466be308d2e5bb1af4d21800d0690ad5a4cdedb27eae3f4fca78d`.
- Supplied fixture: `535212343d8ff7acdbf1aafa18d12a28decd8e2d3cdda2bc255064db79849a03`.
- Supplied fixture log: `3fbe7fd98eacbff95e5946058cf396ab57e60b8d6261ae849582894412059a07`.

## Finding

**P2 — The pre-restore attempt intent prematurely claims that ZIP bytes have been verified.** `public_catalog()` returns `zip_bytes_verified_by_approved_restore: True`. `main()` embeds that catalog in the exclusive persistent attempt intent before calling the approved restore helper. At this point only record name/hash correspondence has been checked; retained ZIP bytes have not been read by restore. If restore fails, the permanent one-attempt record still says that byte verification succeeded.

This is an evidence/provenance defect, not a missing producer gate: actual restore remains required, and its receipt must cover every required name/hash before `run()` is reached. Correct the pre-execution field to an explicit requirement or pending state, such as `zip_bytes_must_be_verified_by_approved_restore: True`. Keep the completed fact in the subsequently SHA-bound actual restore receipt. Add a narrow fixture asserting that intent creation and a failed restore never claim completed verification. Preserve the existing one-attempt and all-record gates.

## Full source conclusions

Read the complete helper and proposal, the approved vault restore implementation, the approved repaired-audit projection validator, and relevant frozen assessor/producer interfaces as source. The controller waits for the two specified predecessor PIDs, holds the original persistent nonblocking queue lock through retry/comparison/projection/new final, and rejects other recognized Python account producers and registered controllers. Its own PID is excluded. A public vault watcher and shell parent mentioning the command are not misclassified as producers.

The attempt intent is exclusive and precedes any restore or producer. Existing intent rejects relaunch, including after a failed restore. New raw/projection/proof/manifest/final paths are fixed rather than automatically renamed. Source/head/full tracked Python identities, original raw/receipt/calibration inputs and approved vault bytes are bound and repeatedly checked. Closed original final/index gates require exactly the known incumbent operating-only six-group mismatch and otherwise completed accepted monetary inventory.

The original risk command's Python executable is retained. The retry uses frozen Coin cwd, default capital10000 and start offset0, global calibration, incumbent/base only and the original TMPDIR. Source inspection confirms candidate index0/base index0 selects synthetic UID12000. No HOME/UID/account-lock override or runtime hook is introduced. Coin writes native `.json.gz` directly, preserving conventional command/output receipt compatibility.

The approved vault helper returns a receipt with `records` entries containing `name`, `sha256`, `linked` and `vault_record_sha256`. The new controller consumes the correct fields and requires every original consumed name/hash, irrespective of whether the ZIP was newly linked or already present. The required catalog comes from the pinned original risk raw, so the coverage is defined by original measured inputs rather than a configurable smaller list. The temporary tests below demonstrate the 773-entry handoff and missing-entry refusal. Public cache restoration is not itself treated as operating equality.

The new original incumbent is actually consumed by immutable99 with exact metadata, calibration and original unscaled reference before derivation. All six complete evidence groups must match; failure occurs before projection, proof, manifest or final creation. Original retained-four rows and complete journals are unchanged. Candidates narrow to four dictionary entries while all other original metadata, conditions and full five-profile risk metadata remain. Parent raw/receipt and whole-row hashes form explicit derivation. Independent rereads check gzip integrity and row/top/input hashes. A one-level manifest combines precisely the derived four with the untouched actual new incumbent.

The actual projection produced by a successful pure fixture was passed to the separately approved audit helper's `projection_check`; the schemas and canonical row checksums match. The final command copies the old argv and changes only the risk-perp input and new JSON/CSV/Markdown output destinations. Final acceptance and source/input rechecks remain inside the queue lock. The helper ends with independent financial review pending and adoption false.

## Actual independent checks

The provided fixture normally imports frozen research. To obey this review's no-frozen-import boundary, I read it and executed an in-memory variant that replaces that import with only the required exact pure function ASTs extracted from the source99 assessor: metadata, row validity, input equivalence, six-group fingerprints and their small pure helpers. External source proof is stubbed, and no frozen module initialization/import occurs. No file containing the fixture or source was edited.

All21 fixture cases passed under that restricted harness. They exercise projection/row preservation; operating/incomplete/source/profile/consume rejection before projection; exclusive writes, JSON/gzip/symlink integrity; immutable bindings; producer/controller refusal; persistent intent before restore and refusal of a second attempt; exact argv/TMPDIR; parent-shell discrimination; and catalog correspondence/conflict.

Added independent checks passed:

- Successful derived fixture matches the approved financial-audit projection validator exactly.
- Current PID, readonly public watcher and a shell parent are accepted by the process gate.
- A mocked approved-schema receipt covering all773 required records reaches the mocked producer boundary.
- The same receipt missing one record rejects before the producer boundary.

The latter orchestration tests use real temporary locks and synthetic receipts, with sources, predecessor waiting, restore and producer calls mocked. No actual restore or producer executes. The finding follows directly from the same pre-restore intent ordering and serialized catalog field, including the existing injected restore-failure fixture.

## Scope and limits

The initial reviewed bytes should not launch until the narrow provenance fix is reviewed. No real helper entrypoint, preflight, restore, financial producer, checker, account State, active cache, frozen import, Git/source/HOME mutation or network operation was performed. Only temporary fixtures and this report were written. The original failed control and audit verdict remain preserved. Passing this operational review after correction will not establish successful actual replay, repaired final, independent financial acceptance, bridge equivalence or adoption.
