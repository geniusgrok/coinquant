# Task 4 fix round 1 independent re-review

SPEC: **PASS for Task4 implementation scope.**

QUALITY: **APPROVE.**

| Original finding | Verdict | Remaining severity |
| --- | --- | --- |
| T4-R1 — foreign derived binary tape | **ADDRESSED** | None |
| T4-R2 — unregistered extension session provenance | **ADDRESSED** | None |
| T4-R3 — crossed-bar extension checkpoint | **ADDRESSED** | None |

No new important breakage found in the fix diff. No additional deferred minors are raised.

## Scope and identities

Scoped to FIX_BASE `fa77a6e51aafd68ebcd99236ce9712d7085381ed` through HEAD `49248555feb0ef588db33c5900956720e1be5b31`. Independently verified supplied report SHA-256 `4a78e0300c895e9cf40ae9cdca17ca31f8fd94456fd64e3db9183d1b1c5a1f19` and root fix package SHA-256 `19bb1be8d0f7a4e165b8c304bf46a48d31c738a14d80c09648d2c0eb23752382`. Read the original brief and immutable failed review, appended implementation response, full fix diff, changed tests and relevant unchanged loader/recovery paths. The original failed review remains unchanged at SHA-256 `72b0fd814bad1d497e08dbdcc560d1a507afbfa48d241f6f75f3208bb7f16455`.

Only `research/edge_perp.py`, `research/edge_prints.py`, `tests/test_edge_perp.py` and parent-owned PROJECT_STATE documentation differ in this fix range. All three reviewed source hashes match the appended report. No original production/economic executable, feature reader, spec or protocol changes are present.

## Closure evidence

**T4-R1 / E-R1-F1:** `research/edge_prints.py:25–57,70–104` requires exclusive creation of a fresh binary directory. It rejects every existing directory before accepting derived data, regardless of a claimed persistent owner manifest. This matches the controller's explicit ruling that each financial invocation uses a distinct cache path and prior binary reuse is unnecessary. Within the invocation, the helper checks exact file inventory and hashes before disk reuse or eviction; newly derived hashes come from the unchanged parser reading the verified ZIP. Receipts separately identify the actual derived binary. Original missing-day eviction updates the in-process inventory, and same-day reuse reads the already parsed arrays.

Independent temporary-fixture probe repeated the original 7000-ZIP/999-binary setup: construction now raises FileExistsError; the foreign binary remains byte-identical and the raw-cache root remains absent. A different fresh directory produces price7000 and a matching derived-binary receipt. Replacing that generated binary with the 999 packed data then forces rejection before disk reuse, retaining the changed bytes rather than deleting or overwriting them. Source inspection confirms unknown file inventory is likewise rejected before the inherited loader; the new tests cover unknown files, forged owners, directory reuse and missing-day eviction. No untrusted persistent manifest can establish derivation.

**T4-R2 / E-R2-F1:** `research/edge_perp.py:67–76,178–191,229–245,255–276` reconstructs the original loader's pinned frozen starts, validates original and actual schedule digests and the exact registered offset, derives300-second deadlines, and checks extension session membership and exact deadline both during preparation and restore. The captured original schedule-loader reference avoids applying offsets twice through the meter's temporary schedule hook. Restore remains inside the pure constructor validation, before original Lifecycle initialization and therefore before settle/recovery/cleanup.

Independent probes used the actual pinned FeatureBook SHA `bf920626cc13653b8bbeafd171650cc1a76888e15aad0c20bbd1061fb41da512` and actual schedule. For each offset -60000/0/+60000, a valid extension checkpoint round-tripped unchanged. Changing both session and deadline by999ms, while retaining internal interval consistency and recomputing checkpoint integrity, raised Blocked before a sentinel for original Lifecycle initialization could run. Separately changing the deadline by1ms also failed restore. The new implementation tests additionally exercise settle/finish spies, zero native writes and wrong schedule bindings.

**T4-R3 / E-R3-F1:** `research/edge_perp.py:181` now enforces the same current-bar interval before persistence that restore already requires. Independent probe naturally advanced a model from ORIGIN through a trigger and strong subsequent bars, stopping at the prior completed bar; it did not mutate clock fields to manufacture the state. An actual minus60s registered session with a decision just after the next bar boundary created no extension, made no state write, retained the original opportunity, and left a checkpoint that restored unchanged. The ordinary later update remains responsible for refreshing history.

## Verification and limits

Independent machine-readable receipt: `/workspace/btc-alpha-beta-improve/task-artifacts/task-4-fix1-rereview-checks.json`.

- Rehashed both fresh raw smoke files: edge `ca517d03bab2271d6b192d808e96c9ccad4d894505efbc77796827b51141c8c8`, Alpha control `50109be2dd046770c6225d22a9133577971fbac50814ffb7264baf71d98055ad`.
- Decompressed and directly checked all20 final rows: one session each, audits passed, failure null, cleanup verified, no unresolved session execution, incomplete and CAGR null.
- All four incumbent original rows exactly equal their original Alpha controls after excluding only the already registered opportunity_ledger addition. No clock/status/protection/archive normalization used.
- Actual loaded ZIP hashes equal restore receipts, and the actual generated binary file matches its recorded hash `2ab81ec332ee0b5c7dd0389dd712fbe0a55e7997258357fd0bf57c5ad148505a`.
- Read the final104-test successful log and inspected the added regression cases. Did not rerun unchanged suites or financial producers. Independent work consisted only of small serial in-memory/temporary-fixture probes and raw read-only checks; no native access, source edits, commits, HOME/UID changes or lock bypass.

Acceptance closes the original Task4 implementation findings. It does not establish full795-session equality, financial improvement, actual trained-risk performance, adoption, native execution or qualification; those remain the already registered later tasks. The20 tiny smoke accounts remain incomplete cold-start evidence. Existing binary directories are intentionally refused; fresh per-invocation cache paths are an accepted operating requirement. No full-vault rehash was repeated during this scoped review.
