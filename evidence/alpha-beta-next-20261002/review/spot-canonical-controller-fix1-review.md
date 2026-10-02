# Canonical Spot controller fix1 — scoped operational re-review

Controller: `/workspace/btc-alpha-beta-next/review/run_spot_canonical_accounts.py`

Reviewed SHA256: `89697d4d22904f5d93db40e19acf89781c1fd7653a4b7115536a749d98266915`.

**Operational spec: PASS. Quality: APPROVE.** Both previous operational findings are **ADDRESSED**; no material direct regression found. This approval applies only to the reviewed one-shot collection controller. It does not approve proposal7ac or any future runtime HEAD, financial equivalence, adoption or forward initialization. Launch still requires the separately reviewed fixed exact HEAD and completed Spot risk evidence supplied by the coordinator.

## Finding closure

1. **Immutable launch evidence — ADDRESSED.** The controller pins review files, completion receipt, calibration, reference risk artifact and its own bytes. `unchanged()` rechecks every original binding plus exact clean runtime/research HEAD before collection, before/after each successful child and before final inventory publication. Final inventory retains the original receipt/calibration/risk identities instead of silently rebinding to later bytes. Per-case command records retain launch bindings. Resolved review paths and review byte hashes must both be distinct.

   Independently mocked a replacement of each of the five evidence categories during the fifth child. Each was rejected after that child; no final inventory was written, and the fifth raw output and command receipt remained available. Duplicate review paths and duplicate contents were separately rejected before launch.

2. **Whole-collection serialization — ADDRESSED.** `main()` holds a persistent external `fcntl.LOCK_EX | LOCK_NB` lock over the entire `collect()` call. The sidecar is not deleted or bypassed. Launch preflight rejects active `alpha_spot`, `adoption_spot`, `complete_spot` and `rebuild` module invocations. The synchronous five-child loop is retained.

   Used a real kernel flock only on a temporary mock sidecar: a duplicate invocation failed before `collect`; a separate descriptor could not acquire the lock while `collect` ran; the sidecar remained afterward. Mock process lists for all four supported producer forms each failed before creating the output directory.

## Direct regression checks

All economic subprocesses and source checks were mocked; no strategy/meter/account execution occurred.

- Successful collection issued exactly `base`, `fee150`, `slip2`, `outage`, calibrated `base`, serially; only the last received `--risk-calibration`.
- Final inventory contained exactly five artifacts with the expected flags and pinned receipt SHA; `adoption_approved` remained false.
- Every compressed artifact's recorded SHA matched, and each gzip decompressed to the exact synthetic original bytes.
- A nonzero first child stopped collection with raw output and command record preserved, and no final inventory.
- All five launch-evidence mutations, both duplicate-review cases and all four active-producer cases rejected as described above.
- The tested controller's SHA remained the reviewed SHA. Temporary mock files were removed; the real external controller and all producer/source/raw files were untouched.

The coordinator remains responsible for the content and independence of the two approval reports and for reserving the Spot execution window against other schedulers that do not use this new controller lock. The controller checks active producers at launch; it is not a global lock imposed on unrelated tools. Its output remains evidence collection, not a declaration that all produced accounts are valid or equivalent. Subsequent independent row/source/archive and six-group bridge checks remain mandatory.

No source edit, financial replay, Coin State access, market/cache read, download, account operation or subagent was performed.
