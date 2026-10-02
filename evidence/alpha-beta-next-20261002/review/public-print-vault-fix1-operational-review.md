# Public print ZIP vault — fix1 operational review

**Operational spec: PASS. Quality: APPROVE for the scoped external ZIP-only workflow and controlled serial handoff.** The three findings from `public-print-vault-operational-review.md` are closed. No new blocking regression was found in the fixes or their direct interactions.

Exact reviewed SHA256 identities:

- `public_print_vault.py`: `65ad132f5bf48559d455d4fa8a76966da76f661b1dda1540068f81c5f422e506`.
- `run_registered_followthrough_public_vault.py`: `be02ff9432a5dc1d2d8bb3198aaf342d33fa65d04ce34ccc06361f8357d527e3`.
- Unchanged original queue pinned by the wrapper: `09e38e09eb755a79a8a6d7d20e83b8a371cf507e2f4c6e3b2315e13ddd9d37cd`.

## Finding closure

1. **Retained orphan accounting and recovery — CLOSED.** Watch startup counts all actual retained ZIP bytes, including ZIPs without published records. A new ZIP that would exceed the budget is skipped. An existing same-name orphan must match the original official checksum and bytes; verification then completes the checksum/record publication without a second link or another capacity charge. A conflicting orphan fails closed. Unique exclusively created JSON temporary names prevent a stale interrupted temporary record from blocking a later valid publication or being overwritten. The precise cap covers ZIP payload bytes; metadata and interrupted temporary records are additional small files, with the separate disk-free check preserved.

2. **Public-path and file-type boundaries — CLOSED.** Source/output/vault root resolution rejects symlink ancestors. Ordinary directory/file checks now cover the marker, records directory and records, ZIPs, sidecars, stop path, and watcher/restore/queue locks before the relevant reads or writes. Temporary fixtures confirmed rejection of internal and root symlinks and a FIFO. Unknown linked paths are not deleted or repaired. These checks address the actual cooperating producer's unlink/replace behavior; they are not a claim of resistance to an unrelated adversary concurrently swapping arbitrary filesystem entries.

3. **Whole-queue serialization — CLOSED.** The wrapper validates the public source before opening a persistent queue lock, acquires a real nonblocking exclusive flock, and holds it throughout process validation, `queue.main()`, all delegated commands and waits, and final identity verification. It rejects another Python `run_registered_followthrough*.py` controller, excludes only its own PID, and ignores shell parents that merely mention a script. The lock file is retained. Original queue, vault and wrapper byte identities are checked before execution and around delegated calls. The wrapper still forwards the exact original module, arguments and output to the original run function; only Coin calls receive the public ZIP restore and surrounding source checks.

## Verification

Eighteen fix1 checks passed using temporary mock public directories, tiny synthetic bytes with matching SHA sidecars, real temporary kernel locks, and mocked queue/process calls:

- All orphan ZIP bytes count toward the cap.
- A verified orphan resumes at the cap without relinking; an interrupted temporary publication remains preserved.
- Simulated source-name pruning followed by restore preserves original bytes and produces the receipt.
- Conflicting retained orphan bytes are rejected.
- Symlinks are rejected for records directory, marker, watcher lock, stop path, ZIP, checksum, restore lock and record file (eight checks).
- A nonregular FIFO is rejected before opening it.
- A symlink in a source root's parent path is rejected.
- The whole-queue lock remains held during exact original Coin and analysis calls; arguments retain their identity, and only Coin restores.
- Another Python predecessor is rejected; the current PID and a shell-parent mention do not cause false positives.
- A second wrapper cannot acquire an already-held kernel queue lock.
- A queue-lock symlink is rejected without modifying the foreign temporary file.

The normal capture/prune races, existing bad-sidecar rejection, watcher/restore locks and active-Coin rejection established in the original review remain supported by the unchanged relevant paths and direct source inspection. Fix1 tests did not run any financial producer. Exact reviewed file hashes were checked again before this report.

## Compatibility and limits

The frozen RollingPrints/TradePrints compatibility conclusion remains unchanged: official ZIP bytes are verified, published by replacement and consumed read-only; rolling eviction unlinks names rather than mutating retained ZIP contents. A retained hardlink survives that unlink. Restore uses the same verified original ZIP and checksum bytes at the same cache paths. Derived BIN files are neither retained nor supplied. Neither frozen source identity nor financial input identities are relabeled.

Approval requires the already specified operational handoff: retain a receipt for stopping the confirmed childless predecessor before launching the single replacement controller, and maintain the root's exclusive serial Coin schedule. The new queue gate intentionally rejects an existing Python predecessor. A process-list check plus this external lock does not reserve unrelated producers that do not participate in the lock; no second scheduler or direct Coin producer may be introduced. Restore remains prohibited while a Coin producer exists. The watcher may retain verified public ZIPs during the authorized producer run without modifying that producer's cache entries.

No actual cache, Coin State, private data, source files, Git HEAD, running producer or financial evidence was changed by this review. No network request, financial replay or account operation was performed. This approves only the reviewed operational helpers within those boundaries, not adoption, financial conclusions, final qualification or a new strategy grid. Full-history resource savings and performance remain unmeasured.
