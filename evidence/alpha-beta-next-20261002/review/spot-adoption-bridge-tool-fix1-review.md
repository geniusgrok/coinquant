# Exact Spot bridge tool fix1 — scoped re-review

Tool: `/workspace/btc-alpha-beta-next/review/verify_spot_adoption_bridge.py`

Reviewed SHA256: `ed4fabacf35be78b33e8763a1de20eae88798f940b8fa9ed88c504c62bf156fd`.

**Spec: PASS. Quality: APPROVE.** Both prior findings are **ADDRESSED**; no material direct regression found. This approves the corrected proof tool for its stated evidence-verification scope. It does not establish that the pending real five-account proof passes, approve default adoption, or change native qualification.

## Closure

**1. Independent-audit coverage — ADDRESSED.** The verifier reconstructs expected identities from every final-report account and sensitivity, distinguishes registered unscaled, risk, combination and sensitivity stages, and rejects duplicate expected identities. It independently reconstructs actual `(kind, stage, candidate/scenario, original_raw_sha256)` identities from the SHA-verified audit reports, checks each account's independent/producer audit and completion flags/errors, rejects duplicates, checks each current original raw SHA and exact measured source, derives each index's actual count, and requires exact expected/actual set equality. An asserted48 count or aggregate flag can no longer conceal an empty, missing, repeated or stale audit inventory.

Read the actual audit producer schemas and remaining-index producer: `kind`, `source`, `raw_path`, account `independent_checks_passed`, `reported_complete`, `producer_audit_passed`, `errors`, and remaining-entry `kind/stage` are emitted under those names. Manifest-child raw identities remain consistent with final-report per-account raw bindings. The source comparison remains against the frozen measured project identity; it does not relabel audited accounts as canonical runtime measurements.

**2. Canonical shared-path provenance — ADDRESSED.** Canonical argv must equal the explicit `sys.executable -u -m research.adoption_spot --scenario SCENARIO --out LABEL.json` command, with the exact calibration argument only on the calibrated case. Recorded cwd must equal the canonical adoption checkout, and the bound log SHA must match. Top-level source, canonical execution marker, selected candidate, fixed rule, calibration hash and row execution marker are required before immutable analysis99 consumption. `consume` still checks the actual candidate/profile/input/source/validity schema and complete six-group evidence; no source override or normalization was introduced.

The inspected canonical producer emits the required fixed rule and execution fields. The original lossless compression and command-output hash proof remains intact. The verifier now binds its own exact file SHA in the result and rechecks it immediately before exclusive proof publication.

## Independent focused verification

Executed the exact relevant AST blocks from the reviewed tool with immutable analysis99 validation helpers and tiny temporary synthetic files. No economic helper, producer replay or full raw artifact was executed/loaded.

- Accepted exact48 registered synthetic unscaled identities plus representative actual risk, combination and sensitivity identities.
- Rejected empty indices, missing accounts even with consistent declared counts, duplicate audit identities, a stale final raw identity, wrong audit source, failed per-account checks hidden behind true aggregate flags, and incorrect declared count.
- Accepted both exact unscaled and calibrated command forms.
- Rejected a module token placed under an unrelated runner, wrong cwd, wrong output path, and an unregistered `--limit` argument.
- Rejected both noncanonical top-level and row execution markers.

All15 recorded check groups passed. Temporary fixtures were removed. The tool remained at the exact SHA above. The prior review's analysis99 API/schema, input/calibration, lossless evidence and six-group comparison inspection remains applicable; this was a scoped fix review, not a repetition of the whole financial audit.

## Limits

The real canonical five, final global report and full audit indices were not yet consumed by this reviewer. A later actual proof must still pass all gates, retain its invocation/source/evidence hashes, and receive independent adoption review. The root remains responsible for supplying the independently reviewed exact canonical source and approval artifacts; this tool emits `adoption_approved=False` and review-pending status. Frozen research remains the separate diary execution identity through immutable analysis99.

No source change, financial replay, private/account operation, Coin State access, market/cache read, download or subagent was performed. Immutable analysis99 and all frozen producer/source gates were left untouched.
