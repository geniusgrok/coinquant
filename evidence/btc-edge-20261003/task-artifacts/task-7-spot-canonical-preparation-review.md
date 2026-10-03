# Task 7 Spot canonical preparation — independent scoped review

SPEC: **FAIL** for code preparation because of T7-CP-R1.

QUALITY: **REQUEST CHANGES**. One Important finding; no Critical finding. This verdict concerns preparation code only. Intentionally deferred account checks, canonical measurements and independent original financial proof are pending acceptance gates, not code findings.

## T7-CP-R1 — Important — Malformed crowding responses abort the forward safety path

Location: `/workspace/btc-alpha-beta-canonical-prepare/spotquant/research/edge_forward.py:988`, called unconditionally at line1178 before passive protection processing at line1182 and the shared decision at line1199.

The newly added `crowding_from` calls `strict(raw)` outside a missing-input conversion boundary. A genuine, hash-valid funding or futures response received successfully over HTTP can contain malformed JSON, invalid UTF-8, duplicate JSON fields, or nonfinite JSON numbers. The parser raises before `ObservedFeatures` can represent that input as unavailable. `apply_observation` consequently aborts before recording passive protection or running an otherwise justified safety SELL. This violates the registered rule that unavailable crowding data blocks new BUY risk only, and disagrees with the native collector, which catches parsing failures and supplies explicit missing input.

One necessary pure mocked probe was run once, using a current, correctly hashed official funding receipt with HTTP-success body `<html>temporarily unavailable</html>`. Native `PublicFeatures` returned `None` with `invalid_public_funding:public_endpoint_JSONDecodeError`; forward `crowding_from` raised `JSONDecodeError`. This probe does not initialize State/Lifecycle, simulate an account, or access the network. The downstream consequence follows directly from the unconditional call order above; no account test was needed.

Requested correction: preserve raw bytes, clocks and their provenance validation, but convert parsing failures of the two added crowding-only categories into explicit unavailable feature records. Keep corrupt receipt/hash/endpoint failures as hard integrity errors, and keep the required Spot market-bar contract strict. A narrow affected regression should establish that malformed funding/futures input blocks a new BUY while leaving a valid safety exit and its raw replay available. No broad rerun is requested.

Probe artifacts in `task-7-spot-canonical-preparation/`:

- `review-malformed-public-probe.py`, SHA256 `bbbe502f8f33d8b9bff0baec157e1c183e46ff701586b809b432ba12d56bce45`.
- `review-malformed-public-probe.json`, SHA256 `c70c3dcb901a197729303958a0a480e619a1fef9890f5d10961de37bfb74a239`.

## Reviewed scope and binding

Read the review and implementation briefs, isolated AGENTS.md, immutable edge protocol/spec/plan, complete 18-file BASE-to-final diff, current affected call paths, new/changed tests, retained first failures and corrective receipts, five-command packet and guide. Reused the closed Task5 fix2 and Task6 forward fix3 reviews for unaffected behavior. This was not another whole-branch or financial-matrix review.

BASE `74bd6e035e36531c517029077c1a9e2e5ec44516`; reviewed final `bd9fbc04813d29015c8231cdc63ec784d4a46256`; isolated worktree `/workspace/btc-alpha-beta-canonical-prepare/spotquant` was clean. Full Git diff exactly matches `base-to-final-fix1.diff`, SHA256 `05e9ad212681ccafc1c3d243c8fd5cd7926c55ca383d75b62ea59b7ecb77db0e`. Independently obtained current source/archive equals the supplied receipt, including protected file bytes/modes, Python SHA256 `e98de40b851c0e2aa7e31344b67cc5cae86b97baaa7c9aafac00fd198fa0c3c0` and protected SHA256 `524bcd9476c6209c8ec0d9e7a18c397774928e4cdbfba625a62a86429bce4e3f`.

Verified artifact SHA256 bindings:

- Implementation report: `b4e74552e2cdb975e53829e89b59d80332e578e697be7d47551d9c5fa48d3653`.
- Source/check receipt: `fdf506cfa4ffdc778df1b924b9ec5293216c7d4bc9bbdff03630d6d632f847ae`.
- Five-command JSON packet: `7ab17011bd15acb8bce5696265640bc01ea88c8bbca66911a1d21753939d7cee`.
- Deferred checks: `f418572755717bcbcc922d65ba09efdd95e8b6b8122b2964bf8a72e5f21d7daf`.

All four indexed implementation check-log hashes matched. Initial failures were retained: wrong unfloored half-spend expectation, obsolete hypothetical protection expectation, and a manually inconsistent SMA checkpoint. Corrected focused receipts and the supplemental explicit old-ATR rejection were inspected, not rerun. They cover 13 new pure cases plus the affected existing synthetic export case across the retained runs. Account tests remained deferred. The policy-specific old ATR immutable99 acceptance test remains available in BASE and its historical accepted evidence; the historical validator itself is unchanged. Its retirement is explicit and accompanied by rejection of old calibration/forward artifacts, rather than a weakened historical validator.

## Other source conclusions

The shared predicate uses strict funding>.0003 and basis>.01, close<=close[-6], settlement+8h availability, exact age>=8h expiry, and basis completion+60s/current UTC availability date. It preserves negative funding, equality behavior and missing historical FeatureBook semantics. Native raw parsing checks finite nonboolean values, actual settlement timestamps and matched completed UTC daily closes; running bars and predicted premium data do not supply the predicate. HTTP451 is missing input, with no access bypass. Forward HTTP-error receipts retain actual bytes/status/clocks. T7-CP-R1 concerns the distinct successful-HTTP parsing failure path.

Canonical preview calls the unchanged ATR sizing body once, then applies the interaction once to BUY orders and rounds down. Original free-pool/capital limits, fees, SELL priority and installed protection floors remain shared. Held active quantities and confirmed closed dust receive the same no-top-up distinction as the measured policy. Historical edge Policy calls `atr_decision` plus the same predicate, preventing double application. No retroactive shrink or stop loosening was introduced in the inspected path.

The truthful new rule is checked before Lifecycle construction/recovery, and incompatible edge/alpha identities and diagnostic profiles reject. Model version5, durable unknown-response ownership/recovery and state retention are preserved. The historical canonical seam injects the pinned FeatureBook into the venue and uses shared State/Model/session/Lifecycle; it rejects research decision hooks. Unity-risk profile validation accepts numeric1.0 without admitting a changed canonical default scale.

Forward observation raw inputs are bound through existing payload hashes/clocks and sealed event replay. The new adapter and five-case bridge separate original measured source from current executable/archive source and require independent pinned canonical review. Existing full financial proof verification remains required. No change was made to FRED CSV/metadata pairing, first-fresh warmup, no-backfill/later-interval gates, Coin primary consumption before early returns, strict boolean market_bootstrap, or native macro-selection completion. Standalone Coin source remains untouched; no new material compatibility issue was identified in the Spot exporter.

## Five future commands

Inspected both `five-canonical-commands-fix1.sh` and JSON argv. They contain exactly base, fee150, slip2, outage and unity-risk-base using `research.adoption_spot`, the pinned feature file, and the registered original Spot calibration only in the fifth case. All five expected current source maps equal the independently obtained reviewed archive. The commands are prepared, not executed, and will need their current-source expectations rebound after a material fix.

Independently hashed all five original raw files and matched their exact registered account IDs and packet SHA anchors:

| Case | Original raw SHA256 |
|---|---|
| base | `4c937ecf80f60d957486a752562c8ab8dfee4c06fa2e5b38b135cfb24ec38872` |
| fee150 | `142c328c958f7459df93b1b4032ba61a66a9a550241937646adee212ba7647d0` |
| slip2 | `29d80444fc598545a209be1cc8d840a30d264307f45700a81cac7974c877b42e` |
| outage | `b5cb4e69c1b2970c8e8df0e7c8bb17e04093303c2a27c019cb9d5ea534fd471b` |
| unity-risk-base | `32b2068dc7c043cbdc8de01ad805f4571c336c8eb42d0e18fd4acc9342d7d600` |

Feature SHA `bf920626cc13653b8bbeafd171650cc1a76888e15aad0c20bbd1061fb41da512`, calibration SHA `7dc82577afa57db44f2c0d25e976826862e9cfbc6713d61baec4656ae55691f4`, and preliminary SHA `2e6ea2aeee64ef8ad3aa37841799576a1b02c9c17a6cdaccf5e6d739111005f9` match actual bytes. The preliminary selects Spot crowding and has blocking=[]/rejected_files=[]; that is preparation evidence, not final financial acceptance.

## Remaining acceptance gates

1. Close T7-CP-R1 with scoped affected evidence and independent fix review, then bind the final preparation source and command packet. Original measured source identities remain frozen.
2. Once root releases the account lane, complete the nine exact tests in `deferred-affected-checks.json`: canonical/research six-group equality; no research hooks; profile cutoff/mismatch/owned sizing; retained ATR baseline equality/budget; cold-start native entry; partial entry/restart/stop amendment; unknown-query recovery; forward fill/fee/checkpoint conservation; forward minimum/rounding/depth/no-top-up sizing. These unrun checks are a declared limitation, not a separate defect.
3. Complete all registered original financial accounts and substantive independent original financial review/final proof, including remaining actual risk and fixed-budget evidence and unchanged registered adoption gates. This review does not perform or substitute for that work.
4. Run only the prepared five actual canonical accounts on the final bound source and compare financial, fills, daily, ownership, remaining_original_fields and operating groups against the frozen originals under existing normalization. Require complete sessions, actual money audits, verified archives, no unresolved execution and independent source-bound canonical review. No unexplained mismatch may be waived.
5. Before promotion/export/init, obtain the complete pinned final proof and canonical bridge, preserve both source identities and archive modes, then carry out root's authorized integration and single final-delivery validation/whole-branch review. Actual future initialization still needs genuine fresh permitted public observations and FRED pairing; HTTP451 may leave it market-pending. No fabricated observations, backfill, elapsed account-days or native qualification may be substituted.

Only this report and the two minimal probe artifacts were written. No source edit/commit, financial producer, account/Lifecycle test, fullsuite, public preflight, CI, child agent, lock/HOME/UID change, export, initialization or independent financial attestation occurred.
