# Canonical Spot controller — operational review

Reviewed external `/workspace/btc-alpha-beta-next/review/run_spot_canonical_accounts.py`, SHA256 `c77e005cbdd62152cadee5123a704ee8c7654ec0d72172e853e61feb5b389c02`.

**Operational spec: REQUEST CHANGES. Quality: REQUEST CHANGES. Do not launch this controller version.** Two collection-gate defects were reproduced with fully mocked child processes. This review does not approve proposal7ac, a later fixed runtime, financial equivalence, adoption, or forward initialization.

## Findings

1. **P2 — Freeze and recheck the actual launch evidence instead of silently rebinding the final inventory.** Lines45–56 hash the review files and risk/calibration originals initially, but the completion receipt is not hash-bound at that point. Receipt/risk/reviews are not rechecked after collection. Lines109–111 independently hash current risk/receipt bytes when writing the final inventory. A replacement can therefore change the reference evidence while the resulting inventory still appears to describe the original gated run. Review bytes can change between their first hash and text validation as well. Calibration is checked before each child and the inspected producer has its own before/after calibration check, but the controller still needs a coherent immutable launch receipt and final equality check.

   **Concrete mock:** during the fifth successful mocked child, replaced the risk file, completion receipt and approved review text. The controller successfully created `canonical-inventory.json`; its risk and receipt SHAs were the replacements, while its recorded review SHA described the now-missing old text. No mutation was rejected. These were temporary mock files, never real evidence.

   **Minimal correction:** freeze the completion receipt bytes/SHA before interpreting them; freeze exact review bytes/SHA and calibration/risk hashes in an exclusive launch record; bind the reviewed controller SHA as well. Recheck against those original bindings before/after each child and immediately before final inventory publication, including after compression. Write the pinned identities into the final inventory; never substitute a later hash. On any mismatch preserve logs/raws/command/compression receipts and omit successful final completion. If risk is a manifest, preserve its exact manifest SHA and ensure its child hashes remain the referenced evidence at the later bridge check.

   The approval gate also needs to reject the same resolved review file supplied twice: line45 currently collapses both paths into one dictionary entry. The mock passed the same file as both independent reviews and was accepted. At minimum require two distinct review artifacts and explicit final approval/exact-source fields; finding `PASS` and `APPROVE` anywhere in prose is not enough to distinguish an actual verdict from quoted old results. The root's independent human review decision remains necessary; this controller does not create it.

2. **P2 — The claimed serial precondition does not cover another canonical run or duplicate controller.** Lines58–60 check only command lines containing ` -m research.alpha_spot `. An existing `research.adoption_spot` process is ignored, and there is no common controller lock. Two invocations with different output directories can both pass preflight and start overlapping canonical collections. The synchronous loop guarantees order only within one invocation.

   **Concrete mock:** `ps` returned `python -u -m research.adoption_spot --out /tmp/another-canonical.json`; the controller launched all five mocked child commands anyway. This is a demonstrated serial-gate gap, not evidence of a Spot account-lock collision. Inspected Spot State locks its own temporary directory; unlike the previous Coin collision, there is no basis here to claim shared synthetic UID alone collides across Spot directories.

   **Minimal correction:** hold a single nonblocking external canonical-collection lock for the whole collection, acquired before output creation. Reject existing Spot economic producers including canonical/legacy runner forms and retain the preflight record. Coordinate a reserved Spot execution window with the root's remaining risk/combination controllers, which do not share a new lock; check for unexpected producers again before each launch. Do not delete/bypass account locks or change frozen producers to make this work. Preserve the completion-receipt prerequisite and require the fixed exact proposal HEAD's independent reviews before acquiring permission to launch any account.

## What already works

- The inventory is exactly four unscaled scenarios (`base`, `fee150`, `slip2`, `outage`) followed by one calibrated `base`; the calibration path is supplied only to the last case. Calls are synchronous and no internal pool is introduced.
- `source()` requires the supplied exact HEAD and clean runtime/research paths before launch, before each case and after each successful child. The controller does not change Git, frozen producers or assessment/forward exclusions.
- The output directory is exclusively created. Logs, command records, compressed files, compression receipts and inventory use exclusive creation. Nonzero children or missing raw outputs stop collection while keeping earlier evidence and current logs/output.
- Gzip writes are deterministic (`mtime=0`, empty filename), and decompressed SHA must equal the original JSON SHA before deletion of the uncompressed copy. Compression receipts retain original/retained hashes and sizes. Compression failure preserves the raw and partial compressed artifact.
- `adoption_approved=False` and native/account-day zeros are explicit. The controller gathers artifacts; it does not establish row validity or six-group equivalence. A successful process exit is not financial acceptance, and the subsequent independent bridge must reject invalid/incomplete or wrong-source accounts.

## Verification and boundary

Read the entire controller, the early-risk completion receipt writer, and the canonical producer's argument/output/calibration path. The proposal's active source-schema review remains outside this operational review and must finish before launch.

Executed one temporary-directory mock with **all subprocesses and source checks mocked**, no economic import/replay, and only synthetic JSON files. It demonstrated five sequential calls, exclusive final inventory creation, acceptance of an existing canonical process, acceptance of one file for both reviews, and undetected receipt/risk/review mutation. Temporary mock artifacts were cleaned up. Controller SHA was unchanged when tested.

No source edit, financial replay, Coin State access, market/cache read, download, account operation or subagent was performed. Frozen Coin/Spot/analysis directories and real raw evidence were untouched. Re-review the corrected controller by its new exact SHA before scheduling it; this report grants no launch or adoption approval.
