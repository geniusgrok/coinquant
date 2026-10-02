# Public print ZIP vault — operational review

Reviewed external tools:

- `public_print_vault.py`: SHA256 `0080ec7978d23d8a1fe249f0c571f09ed9b65214a44cb20b1b25652b666bb58d`.
- `run_registered_followthrough_public_vault.py`: SHA256 `10317f7d05d7388643ba12f99a221de6285ecae8bb3111b096dbf836d116eb7b`.
- The wrapper's pinned original queue independently matches `09e38e09eb755a79a8a6d7d20e83b8a371cf507e2f4c6e3b2315e13ddd9d37cd`.

**Operational spec: REQUEST CHANGES. Quality: REQUEST CHANGES. Do not launch these versions yet.** Two vault filesystem/recovery defects were reproduced exclusively in temporary mock public-data directories. A third wrapper serialization requirement is also unmet. The intended ZIP-only reuse and argument preservation are otherwise sound.

## Findings

1. **P2 — Count and reconcile retained orphan files before accepting more ZIPs.** `watch()` initializes `total` solely from published record JSON. A crash after `os.link(source, retained)` but before record publication leaves a real retained ZIP whose bytes are not counted. If its original source name has since been pruned, the next watcher skips that orphan entirely and may retain more than the configured cap. If the source name still exists, the next `os.link` raises `FileExistsError`, permanently interrupting restart at the same file.

   Temporary reproduction used a10-byte cap, one6-byte orphan ZIP in the vault without a record, and a different6-byte source ZIP. The watcher retained the second file: actual ZIP bytes12, configured cap10. A separate same-name retained-link/no-record fixture raised `FileExistsError` on restart. These fixtures model interruption between the existing non-atomic capture steps, not tampered financial inputs.

   **Correction:** inventory actual regular retained ZIP files at startup and account for all retained bytes, including unpublished/incomplete captures. Reconcile same-name orphans under the watcher lock before linking new files: a completely verified ZIP plus exact checksum can finish exclusive record publication; an unattested orphan stays counted and unrestorable until independently verified. Do not delete or overwrite producer files. Treat leftover `.pending` records explicitly so an interrupted publication can recover or fail before growing the vault. Reserve metadata space or state the precise ZIP-only byte budget; the5GiB disk reserve remains a separate check, not proof of the16GiB cap.

2. **P2 — Reject internal-directory/metadata/lock symlinks before opening them.** `require_source()` checks SOURCE and VAULT themselves, and capture/restore check ZIP and checksum leaf symlinks. It does not check `VAULT/records`, the source marker, record files, or lock paths. `records.mkdir(exist_ok=True)` accepts a directory symlink, then `record_new` writes through it outside the vault. Record enumeration/marker reads can likewise follow links outside the intended public-data tree. The “regular file” checks also only test `is_symlink`, which does not reject other nonregular file types.

   Temporary reproduction created `vault/records -> temporary_foreign_directory`. An ordinary one-pass watcher successfully published its JSON record into that foreign directory. No real/private directory was involved.

   **Correction:** validate the public roots and internal directories with `lstat`/non-symlink directory checks; require regular marker, ZIP, checksum and record files; open lock/metadata files without following symlinks. Reject unexpected entries before reading them. Keep exclusive publication and do not repair an unknown linked path by deleting it. The known producer eviction race should continue to be handled as a missing regular source file, without allowing a changed inode/type to become an external write.

3. **P2 — Reserve the whole replacement queue, not just each restore operation.** The wrapper has no whole-process lock or check for another Python followthrough controller. Its `unchanged()` checks code bytes, then `queue.main()` can enter the waiting/measurement chain while a predecessor or duplicate wrapper still exists. `vault.restore()` only checks active economic children at that instant and releases its restore lock before `original_run` starts the next child. Per-output exclusive creation can stop duplicate work later, but is not an explicit or auditable whole-queue handoff/serialization gate. This is visible directly in the complete wrapper; no concurrent economic process was launched to test it.

   **Correction:** hold one nonblocking, persistent external whole-queue orchestration lock from before predecessor/process validation until `queue.main()` exits, including its waits and all child processes. Reject other Python followthrough controllers as well as unexpected economic children; exclude only the current process through an explicit identity check, not broad command substrings. First stop and retain a receipt for the confirmed childless36010 predecessor as the root proposed. Keep output exclusivity as an additional safeguard. Do not remove/bypass native account locks or change UID/HOME.

## Frozen reader compatibility

Read actual frozen `research/rolling_prints.py` and `research/session_market.py`.

- RollingPrints downloads into `.downloading`, verifies the official SHA, atomically replaces the ZIP name, and writes the original CHECKSUM sidecar. Existing ZIPs are not rewritten in place. Its rolling eviction unlinks the ZIP and CHECKSUM names, then separately removes derived BIN files.
- TradePrints checks the ZIP against its CHECKSUM on load, records the ZIP digest in `loaded`, and either parses it read-only or uses a BIN cache keyed by that exact ZIP digest. The proposed vault does not retain, supply or change BIN data.
- Consequently a verified hardlink retained outside the cache survives original-name unlink without altering ZIP bytes. Restoring that link preserves the same official bytes/path/hash that the frozen loader verifies. It changes download/disk work, not economic rules, virtual timing, UID, source identity or measured archive hashes.

## Temporary verification

Only mock public-data files, temporary sidecars/locks and a mock queue were used. No actual cache, market ZIP, Coin State or economic process was accessed.

Passed checks:

- Normal checksum-verified capture creates the same inode in the vault while preserving source bytes; simulated source-name pruning followed by restore reconstructs exact original ZIP/checksum bytes and writes a linked receipt.
- Producer unlink before the capture link is safely skipped; unlink immediately after link still yields a fully verified retained ZIP and published record.
- Existing conflicting checksum sidecar is rejected before creating a missing target ZIP; the bad sidecar is not overwritten.
- Both watcher and restore nonblocking locks exclude a second holder in temporary paths. The expected active `research.alpha_perp` process shape rejects restoration before writes.
- Wrapper mock preserves the exact original Coin/non-Coin `queue.run` arguments and argument objects. It restores only before the Coin command, performs the intended before/after queue source checks, and delegates to the original run function. Its source pins match the actual approved queue and vault files.

The two filesystem failures described above were also reproduced and retained in the review result; the whole-queue guard finding is source inspection evidence. Temporary fixtures were removed.

## Concurrency, publication and operational limits

The watcher writes only its own retained links/sidecars/records; restore reads only published records and writes verified public cache links/sidecars. Record publication via exclusive temporary creation plus `os.link` is atomic to the directory reader, and no existing receipt is overwritten. This is not a multi-file crash transaction; finding1 addresses the resulting incomplete-capture state. Hash mismatch or receipt publication failure stops the helper with existing evidence/files retained.

The independent watcher/restore locks protect duplicate instances of their respective operations. They do **not** reserve the entire Coin measurement schedule: restore's lock is released before the original queue starts its next child, and unrelated producers do not share it. Finding3 requires the explicit whole-queue lock and predecessor/process gate before launch. Preserve the root's stated precondition: stop only the confirmed childless old waiter, launch one replacement queue, and allow no parallel Coin producer or second scheduler. Do not bypass account locks or change UID/HOME. The wrapper preserves the approved queue's sequential Coin command ordering; it does not provide authority to start a second queue.

No adoption, final financial result, native qualification or input/source relabeling is approved here. Correct and re-review the vault and update its byte pin in the wrapper before launch. Full-history resource savings/performance are not measured by these tiny filesystem checks.
