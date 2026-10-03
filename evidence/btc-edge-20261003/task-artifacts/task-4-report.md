# Task 4 implementation report

Status: implemented, reviewed locally, clean committed, affected tests and final-source tiny finite-meter smokes passed. Independent Task4 review and full registered financial measurement remain controller work. No financial promotion/native qualification claimed.

## Scope and source

Review BASE `25cd5d0349bef669ac14824435f741dedac6ec82`.

Owned source commits:
- `860f858113c8bd3a7032cf040ff5f62d9c543668` — registered EdgeCampaign, finite-meter wrapper, exact calibration/CLI validation, verified read-only-vault cache seam, tests.
- `fa77a6e51aafd68ebcd99236ce9712d7085381ed` — count original incumbent decisions separately from feature evaluations. Final smoke source; tracked Python-source digest `4eec1f151c611ba549641aff26a2ca5f742bd628c3ee5715417b2d36627ca15e`; dirty=false.

Only research/edge_perp.py, research/edge_prints.py and tests/test_edge_perp.py were committed by this worker. Parent-owned documentation commits in the range remain parent work. `git diff BASE HEAD -- research/alpha_perp.py research/complete_perp.py research/rolling_prints.py research/edge_features.py research/edge_spec.json research/edge-PROTOCOL.md coinquant` is empty. Old economic executables, production source, spec/protocol, original evidence and vault bytes were not edited. Remote HEAD was read before writes with `git ls-remote origin HEAD`; no push/merge/native account action occurred.

| Final source file | SHA-256 |
| --- | --- |
| `research/edge_perp.py` | `876f1bb37d1217ef113726d1b6a2201f4f21013f4b158c9ad0a50dd6dc40f842` |
| `research/edge_prints.py` | `a94c542a117edb43ce3d165025abba32bce85432b190c576ff0cb634ad500e91` |
| `tests/test_edge_perp.py` | `e2de006733c785d3641c6c877d31af2c849413e30b7400735b61fbc29e46a9c0` |
| `research/edge_features.py` | `1af4444c3714b737651f736b905fef47c56732421767bf169ac661f2b1ee92d5` |
| `research/edge_spec.json` | `53296233aadc6429359dd7b664c4e03a28eb451d6bacf4318fced4ce13f7e3de` |
| `research/edge-PROTOCOL.md` | `714e0eae887fc9aac79380662c7db1e931823484fc2fe3781c80c2853bb4163b` |

Reviewed FeatureBook artifact is explicitly pinned to `bf920626cc13653b8bbeafd171650cc1a76888e15aad0c20bbd1061fb41da512`, loaded before the meter/accounts, and included in durable identity and edge envelope. The standalone feature reader remains unchanged.

## Implementation decisions

All financial accounting, finite session clocks, public adapter requests, Lifecycle sizing, protection, committed topups, audit, funding, terminal handling and output row fields remain in complete_perp / alpha_perp. This adds no adapter reads or waits.

The incumbent uses unchanged AlphaCampaign / alpha.variant with actual measured source and original alpha spec/protocol binding shape. The new full identity is a separate durable edge_identity record validated before Lifecycle initialization, settle, recovery and cleanup. All mechanisms bind candidate/components, source/spec/protocol, feature hash, calibration document/hash/profile and original schedule plus actual starts. Invalid existing checkpoints fail before recovery can write. New methods preserve original entry target/topups and original stop/take geometry.

Quality budget uses 20 completed four-hour closes and six completed intervals, immutable trigger close/prior ATR, and observed decision mark. It reduces only genuinely new primary sizing to half when full-quality conditions fail; missing required history/trigger blocks that new risk. Macro behavior/no-short rule remain original. Crowding independently uses the registered three-way conjunction; missing/stale features block only primary new risk. Combo factors multiply with unique registered components in fixed order.

Cost exit is prepared only inside the actual authorized session decision, while the finite session remains legal, for owned longs whose original action is hold. Missing funding leaves that hold intact and is recorded; original exits retain priority. Extension occurs only once for a primary owned opportunity at actual age >=5 and <7 days, strong completed-bar trend/momentum and known funding <=.0003. It changes expiry to trigger+10 days while preserving stop/take, and retains actual decision/session clocks, ownership, binding, source feature record, bars and old/new expiry. Restore rejects malformed/duplicate/mismatched/out-of-session or expired evidence; historical updates do not create extensions.

Original row fields are retained, with opportunity_ledger as the named instrumentation addition. Top-level edge holds actual edge/source/profile identities, exact calibration document, original input/condition copies, decision coverage and print restore receipts. Original input/condition identities are not rewritten to manufacture baseline equality. Alpha decision pre-stamps remain intact; new candidate records explicitly identify completed_at_ms and after-return fields, while incumbent completion records separately identify after-return values. Actual fill timestamps and post-run extraction timestamps are distinct.

Calibration document validation follows the fixed perp schema, four required single profiles (plus a requested fixed combo profile), exact candidate/project/baseline/cutoff/spec, finite Decimal-string scale in [0,1], incumbent exactly1, training endpoint and raw base digest syntax. No source_base_sha256 alias. The independent assessor must prove those raw artifact references and reconstruct training; this runner cannot infer a digest's external raw content from the profile alone. Actual sizing uses scale1 before cutoff and profile scale afterward; committed held targets are untouched.

The CLI supports all four candidates/all four original scenarios in one strictly serialized invocation by default, one candidate/scenario, fixed comma-separated combo, project calibration, reviewed features, existing market/FX/prints inputs, CNY2500/5000/7500/10000, registered ±60000/0 offsets only with one fixed base candidate, /tmp-only limit1..795, restore-prints, and exclusive .json.gz output reservation. Incomplete rows retain complete=false and CAGR=null. Components supplied for a combo are the controller's previously eligible fixed set; this adapter performs no eligibility/subset search.

VerifiedPrints checks official CHECKSUM bytes and ZIP hash before exclusively hardlinking/copying into a separate marked task cache, then calls unchanged RollingPrints._load. Missing official input remains missing under original behavior. Existing orphan/symlink destinations and vault/cache overlap fail closed. Only task cache paths/binaries are eligible for original eviction. Each receipt's data hash is checked against actual tape.loaded; source vault is never written or evicted. No HOME/UID/account lock changes.

## Commands and results

All Coin tests and producers were strictly serialized in the reserved lane. No full financial producer ran.

1. `python3.13 -m unittest tests.test_edge_perp -v` — initial 19 tests passed; task-4-tests-first.log.
2. `python3.13 -m unittest tests.test_edge_perp tests.test_alpha_perp tests.test_complete_perp tests.test_edge_features tests.test_session tests.test_campaign -v` — 98 passed after real Lifecycle cost-exit test; task-4-tests.log.
3. Same affected command after fixed reviewed feature pin/rejection test — 99 passed in 1.858s; task-4-tests-final.log.
4. `python3.13 -m unittest tests.test_edge_perp -v` after final coverage correction — 21 passed in 0.340s; task-4-edge-tests-final.log. This final metadata-only correction was covered by the added count assertion; no production behavior changed.
5. `python3.13 -m py_compile research/edge_perp.py research/edge_prints.py tests/test_edge_perp.py`; `git diff --cached --check` — passed. Commits were path-only, with clean tree before every smoke.

Tests cover full/half factors and equality boundaries, 6/20 completed counts, immutable trigger geometry, independent/conjunctive/multiplicative rules, primary/macro/no-short scopes, missing feature original holds/exits, actual legal-session cost exit, unchanged native protection, one actual 5..7-day extension, forbidden history/expired/stopped extension, checkpoint/extension/source tampering, pre-recovery/cleanup rejection spies, cutoff/zero scales, real committed-target topup with a failing fraction-recompute spy, exact incumbent report/requests/clocks/cash/fills/checkpoint equality, actual journal completion clocks, hook restoration, strict profiles/JSON duplicates, output overwrite rejection, fixed feature pin, and verified ZIP receipt/vault immutability/overwrite refusal.

First clean-source smoke commands (retained as their own source, not relabeled):

```sh
python3.13 -m research.edge_perp --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json --scenario base --limit 1 --restore-prints --prints /tmp/coinquant-edge-task4-860f858 --out /tmp/coin-edge-task4-860f858-base.json.gz
python3.13 -m research.alpha_perp --candidate incumbent --scenario base --limit 1 --restore-prints --prints /tmp/coinquant-edge-task4-860f858 --out /tmp/coin-alpha-task4-860f858-incumbent.json.gz
```

Both exit0: four edge accounts and one original comparison account. Original incumbent row equality holds without archive normalization after excluding opportunity_ledger. Logs task-4-smoke-edge.log/task-4-smoke-alpha.log and task-4-smoke-baseline-diffs.json (empty list).

Final clean-source smoke commands:

```sh
python3.13 -m research.edge_perp --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json --limit 1 --restore-prints --prints /tmp/coinquant-edge-task4-final --out /tmp/coin-edge-task4-fa77a6e-all.json.gz
python3.13 -m research.alpha_perp --candidate incumbent --limit 1 --restore-prints --prints /tmp/coinquant-edge-task4-final --out /tmp/coin-alpha-task4-fa77a6e-all.json.gz
```

Both exit0: 16 final edge accounts and four original incumbent stress controls, each exactly one session. Every audit passed, failure=null, cleanup=verified, execution_unresolved=0, complete=false, CAGR=null. All four incumbent original rows match exactly, excluding only opportunity_ledger; no clock/status/protection/archive normalization was used. Logs task-4-smoke-final-edge.log/task-4-smoke-final-alpha.log. Machine-readable row/source/hashes: task-4-smoke-manifest.json and task-4-smoke-verification.json.

| Raw artifact | SHA-256 | Account rows |
| --- | --- | --- |
| `/tmp/coin-edge-task4-860f858-base.json.gz` | `732e9f8852fcdf336d0053e83ecd8fc2550676f189d6db86d8b55c96bbb2d2d5` | 4 |
| `/tmp/coin-alpha-task4-860f858-incumbent.json.gz` | `a077113e4b744d8c79c0672965737e590829822ea54eaf320b012b7bb0911995` | 1 |
| `/tmp/coin-edge-task4-fa77a6e-all.json.gz` | `7eb39113c6e6cf3bb6e398953aaaa293e63e7d632956565d92fe3d337ab8a4e6` | 16 |
| `/tmp/coin-alpha-task4-fa77a6e-all.json.gz` | `c3c9810831cc5337c36ebd1982ab419c05f1e374dc281cb0ea40fd1c1b4f026d` | 4 |

Consumed public ZIP `BTCUSDT-aggTrades-2020-01-01.zip` SHA `638e72c179e4965c2a6521bb27295930d09126433efe0cc3acd4e925ada955ac`; official CHECKSUM-file SHA `54f9a3ec8d0ea0363fcd730c2eb43399fa425d2d1fd803a7261f761af78d8499`. Final restore receipt matches actual loaded_print_files exactly. All actually consumed market/FX/schedule identities remain in each original raw inputs object; final feature/source bindings and decisions are in edge. Full-vault post-check against parent's immutable snapshot is recorded in task-4-vault-after.json: all2396 files /14481648622 bytes have identical size and SHA-256, with no added or missing file. The full post-check passed.

## Self-review and limits

- Caught the misleading initial incumbent zero-decision coverage label during smoke review. Final metadata distinguishes all actual decision records from feature evaluations; earlier raw receipts are retained at 860f858.
- Controller identified that an initial self-hash check did not pin the reviewed feature artifact. Corrected before first commit/smoke, added preaccount mismatch test, and retained the final fixed SHA.
- Reviewed real session.cycle ordering: pure identity/checkpoint validation now occurs before Lifecycle settle/recovery and finish, not merely inside later advance/restore. Tests prove native write paths are not reached after tampering.
- No unresolved implementation blocker found in local review/tests. Independent spec/quality review is still required.
- One-session smoke rows are cold-start accounts with zero trades; they prove wiring, original clock/row equality, audit/cleanup and verified tape consumption, not financial mechanism benefit. Nontrivial entry/topup/cost exit/extension branches are exercised by offline synthetic tests, including real shared Lifecycle for entry/topup/exit/protection.
- Full 795-session baseline equality, actual calibrated accounts, all-stress results, combo/capital/offset outcomes and selection belong to later frozen financial measurement. None is inferred from smoke/unit tests; native account-days remain0 and qualification NOT_QUALIFIED.


# Task 4 fix round 1 of 5 — response to independent failed review

Fix BASE `fa77a6e51aafd68ebcd99236ce9712d7085381ed`; source commit `49248555feb0ef588db33c5900956720e1be5b31` (only the same three owned paths). Parent documentation commits precede this source commit. Source/tree clean before both fresh smoke runs. Final tracked Python digest `faec069a4dace9a547db44d87fcd4b3f575ebdd077bb5e55fd978053cb214772`. Independent acceptance remains pending; this section does not replace the retained failed review.

The complete original report bytes are retained as `task-4-report-before-fix1.md`, SHA `7bfedc91c1b965442fbd7f1d5ca176b89d76e6ffb691a48d20159fa8060b5866`, and remain the exact prefix above. `task-4-review.md` remains SHA `72b0fd814bad1d497e08dbdcc560d1a507afbfa48d241f6f75f3208bb7f16455`, and its independent checks remain SHA `884a2a68cbfff9e6ab75cbddf5a2a04b5de2a7fc08a0a6389f0fffe0ec87f99b`. Prior raw artifacts, logs, hashes and source labels were not overwritten. Preservation identities are in `task-4-fix1-preserved-hashes.json`.

## Findings and corrections

**T4-R1 / P1:** Verified against the original loader: a foreign sibling binary file really could be consumed merely because its name contained the correct ZIP hash. Fixed by requiring a freshly and exclusively created binary directory for every VerifiedPrints invocation (`mkdir(exist_ok=False)`). Every preexisting directory/file, including a directory bearing a forged or prior ownership manifest, is rejected without modification. The controller confirmed registered invocations use distinct cache paths, so cross-invocation binary reuse is intentionally unsupported.

The initial binary inventory is empty and provenance stays in process memory. Unchanged RollingPrints generates packed bytes from the verified ZIP; only that generated filename is registered, with ZIP and actual binary hashes. Before another disk load/eviction, exact file inventory, regular-file status and binary hash are checked. Unknown files and altered packed data fail without deletion or overwrite. Receipts now separately retain derived_binary_sha256. Same-day in-memory reuse consumes already parsed arrays, not changed disk bytes. No unpinned persistent manifest can establish trusted derivation. Missing official days retain original missing behavior; owned inventory follows original eviction even when a missing day causes eviction.

New tests reproduce the exact 7000-ZIP/999-binary probe, assert preexisting root/foreign bytes remain untouched, reject forged owner files/reopening a prior directory, detect in-process binary changes and unknown files, verify actual7000 parsed prices and binary receipt hashes, and exercise missing-day eviction while preserving every fixture vault byte.

**T4-R2 / P2:** Verified that the original interval-only check admitted a semantically recomputed session+999ms. Fixed by reconstructing the pinned frozen schedule through the original loader reference, applying only a registered integer offset -60000/0/+60000, verifying original_schedule_sha256 and actual_starts_sha256 against the account binding, and deriving exact eligible session deadlines from frozen300 seconds. Extension preparation now requires membership; extension records include session_deadline_ms. Restore requires registered membership, exact deadline, actual decision within that interval, and every original source/ownership/geometry condition. This pure validation remains before Lifecycle initialization/settle/recovery/finish. No adapter calls or waits were added.

New tests accept valid original, minus60s and plus60s sessions, then change the session by999ms (also changing its claimed deadline), recompute checkpoint integrity and prove rejection before settle/finish with spies and zero native writes. Separate binding-digest mismatch tests reject altered original or actual schedule identity.

**T4-R3 / P3, nonblocking:** Added the same current completed-bar interval required by restore before extension persistence. A minus60s actual registered session can cross the boundary, but stale preboundary completed history now leaves original hold/protection/expiry intact until ordinary advancement supplies current history. The small round-trip test proves no extension/state write and successful restore. This was addressed with the related provenance fix, without adding a separate acceptance loop.

## Verification, commands and identities

Serial affected tests only; no concurrent Coin test/producer or full financial producer, HOME/UID change, lock bypass, native account request, vault mutation or original executable edit.

- `python3.13 -m unittest tests.test_edge_perp -v` after the implementation changes:21 existing tests passed; `task-4-fix1-existing-tests.log`.
- Same command after new review probes:25 passed; `task-4-fix1-edge-tests.log`.
- `python3.13 -m unittest tests.test_edge_perp tests.test_alpha_perp tests.test_complete_perp tests.test_edge_features tests.test_session tests.test_campaign -v`: **104 passed in1.897s**, including26 edge tests and missing-day eviction regression; `task-4-fix1-tests-final.log`.
- `git diff --check` and staged diff check passed. Own-path commit made after the final tests. Root then held source HEAD fixed through smoke measurement.

| Final source | SHA-256 |
| --- | --- |
| `research/edge_perp.py` | `8d14dbf93f4a8fc511b4952e2b312de8b33fbf6406d2ba8681d4ab3e230ed3e0` |
| `research/edge_prints.py` | `65e07bfe4fc0a966f6e1acb584b830bcb99a53719f1d1e7a38bf94fd4bc24e62` |
| `tests/test_edge_perp.py` | `d3c8de1334eebf386c9ebdf24626854984ef68b904a72042e7f4216324315c5a` |

Fresh exclusive smoke commands, strictly sequential, both exit0:

```sh
python3.13 -m research.edge_perp --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json --limit 1 --restore-prints --prints /tmp/coinquant-edge-task4-fix1-4924855 --out /tmp/coin-edge-task4-fix1-4924855-all.json.gz
python3.13 -m research.alpha_perp --candidate incumbent --limit 1 --restore-prints --prints /tmp/coinquant-edge-task4-fix1-4924855 --out /tmp/coin-alpha-task4-fix1-4924855-all.json.gz
```

The original Alpha comparison reads the already verified generated cache; it does not instantiate a second VerifiedPrints or grant cross-invocation manifest trust. New edge invocations require a distinct cache path, as the controller's command registry already provides.

All16 edge and4 original control accounts: one session each, audit passed, failure=null, cleanup=verified, execution_unresolved=0, complete=false, CAGR=null. All4 incumbent scenario rows equal original Alpha row fields exactly after excluding only opportunity_ledger; no archive/clock/protection normalization. These cold-start smoke accounts have zero trades and establish no financial benefit.

| New raw artifact | SHA-256 | Rows |
| --- | --- | --- |
| `/tmp/coin-edge-task4-fix1-4924855-all.json.gz` | `ca517d03bab2271d6b192d808e96c9ccad4d894505efbc77796827b51141c8c8` | 16 |
| `/tmp/coin-alpha-task4-fix1-4924855-all.json.gz` | `50109be2dd046770c6225d22a9133577971fbac50814ffb7264baf71d98055ad` | 4 |

Machine-readable raw/source/row checks are `task-4-fix1-smoke-manifest.json` and `task-4-fix1-smoke-verification.json`; logs are `task-4-fix1-smoke-edge.log` and `task-4-fix1-smoke-alpha.log`. Consumed public ZIP SHA remains `638e72c179e4965c2a6521bb27295930d09126433efe0cc3acd4e925ada955ac`; generated binary SHA is `2ab81ec332ee0b5c7dd0389dd712fbe0a55e7997258357fd0bf57c5ad148505a`. Both match actual final files, and ZIP hash matches original tape.loaded. Full vault rehash in `task-4-fix1-vault-after.json`: all2396 files /14481648622 bytes equal original size/hash, no added/missing files.

Diff package against FIX_BASE is `task-4-fix1-review-package.diff`. Artifact hashes are separately retained in `task-4-fix1-artifact-hashes.json`. Original code/spec/protocol/input files remain unchanged.

## Fix self-review and remaining limits

Checked the call order and trust boundary, not just reported strings: unowned binaries are refused before the inherited loader; source-bound session validation is performed before native recovery; expiry preparation and restore use the same completed-bar precondition. Found and covered an adjacent missing-day eviction case while maintaining the in-process binary inventory. Rejected persistent self-authored manifests as trust because they can merely restate foreign bytes; fresh exclusive derivation is simpler and matches the controller's actual invocation registry.

No local unresolved blocker remains for T4-R1/R2/R3. Existing directories are deliberately not adopted or automatically cleared; the caller must provide the registered fresh per-invocation cache path. Independent re-review must determine acceptance. Full795-session financial equality, mechanism outcomes, actual calibrated accounts and adoption remain later work. Native qualification/account-days remain NOT_QUALIFIED/0.
