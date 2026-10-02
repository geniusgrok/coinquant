# RETRACTION — parallel Coin sensitivity approval was incorrect

2026-10-02. This addendum **supersedes and withdraws** the PASS/APPROVE verdict in `followthrough-parallel-sensitivity-operational-review.md` for queue SHA256 `82ab032036359d064c60f172a978d78fac577ca07007e7539d888f2c69f01128`. The prior structural/cache proof remains a record of the incomplete review, not authorization to use that concurrent queue again.

The reviewer checked archive/binary cache separation but missed the product's **global account-identity lock**, shared across all state directories and all print-cache roots. Frozen `coinquant/state.py` derives `_account_lock_path(identity)` under `Path.home()/.local/state/coinquant/account-locks` and acquires an exclusive nonblocking lock at line80. Both processes use the same synthetic scope `binance:BTCUSDT:live:12000`, whose lock file is `/home/agent/.local/state/coinquant/account-locks/213a7625d970e1d439a347a6df7ea963f72b6182d04d7522ed99a7222b4b0d7e`. The scope string is a simulator's internal identity; it does not indicate a real account operation. Separate temporary state directories and print caches cannot isolate this lock.

Observed consequence: after the concurrent queue launched at05:36:29UTC, main Coin PID21612 exited1 at session289. Its traceback explicitly shows `BlockingIOError: [Errno 11] Resource temporarily unavailable` on the global `fcntl.flock`, converted to `coinquant.types.Blocked: state unavailable or another run holds the execution lock`. The last preserved progress is session288 (`complete:false`). No complete Coin20 raw output exists and its temporary directory was cleaned. The incumbent CNY9,900 probe's retained progress is session44 (`complete:false`). Neither partial output is a complete account, measured performance result, baseline proof or selection input. No newly completed Coin account is accepted from this attempt.

Root stopped probe31869 and queue31865 with the recorded normal SIGTERM procedure. `parallel-sensitivity-stop-receipt.json` records05:39:06.597831UTC and `financial_evidence_accepted:false`. All stopped progress/logs/receipts remain immutable; no partial values are extrapolated or relabelled. Spot continues independently. No main/default/native or product source change follows from this incident; the safety lock correctly refused the concurrent account writer.

The corrected operational requirement is **serialize entire Coin producer processes that share any synthetic UID**, irrespective of print-cache separation. Restore the strictly serial queue and rerun the full Coin20 matrix into a new exclusive output path using unchanged frozen source `acedaa43ca94223f24e2fe11851bbef74e032a69` and recorded input/source hashes. Existing incomplete evidence must remain separately identified. Do not delete/bypass account locks, change HOME, alter synthetic identities, relax source binding or weaken product safeguards to obtain concurrency.

## Independent pre-restart check

At **05:40:47.464375UTC**, independent read-only inspection found:

- No active Coin replay or either follow-through queue process.
- No entry in the visible kernel `/proc/locks` table matching the device/inode of any of the39 Coin account-lock files.
- No matching account-lock descriptor among accessible live processes.
- Only stopped probe PID31869 remains as a zombie (`Z`), which retains no open descriptors or lock. PIDs21612/31865/28019 were absent.
- Descriptor enumeration of two system processes, PIDs200/251, was permission-limited; the kernel lock table independently had no matching Coin account lock. This limitation is preserved in the proof.

The snapshot supports a strictly serial restart and is not a promise about future process launches or a lock acquisition. All39 lock files remain intact; none was deleted, opened for writing, acquired or bypassed by the reviewer. Proof: `parallel-sensitivity-retraction-lock-check.json`.

## Preserved failure evidence

| Artifact under `/workspace/scratch/alpha-beta-next` | SHA256 |
|---|---|
| `perp-full.run.log` | `f085cf74e5c87a2c9502b65fec3f31d0e92313e63fa58cafc64d1a53363102c6` |
| `perp-singletons.json.progress.json` | `41bac48260ead53b7421a47390febdd3f2539725aa1ff0dcd97b11cc8b801df6` |
| `sensitivity-incumbent-9900-0.run.log` | `afbebf518225a73054cd18029c0d18b0a31c55cee1dc47ed81f144fa67d577c6` |
| `sensitivity-incumbent-9900-0.json.progress.json` | `f0f87edc4185d16dfa33c623e35595cfe077a6df8e4ce1c32ab911210a30b83b` |
| `parallel-sensitivity-stop-receipt.json` | `619cc90b0ed5b3d9aad9d2034da09a6ffc98d9be289c365e14e15be9fe6cd098` |

The missed global lock scope is a material review error. The earlier statement that no isolation issue existed is withdrawn. There is no economic acceptance or prospective/native evidence from the failed concurrent attempt. Reviewer actions for this correction were read-only inspection and external report/proof writing only: no product edits, replays, downloads, cache changes, lock changes or process actions.
