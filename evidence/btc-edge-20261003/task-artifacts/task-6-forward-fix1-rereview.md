# Task6a forward fix round1 scoped independent re-review

T6-F1: **ADDRESSED**. T6-F2: **ADDRESSED**. T6-F3: **ADDRESSED**. T6-F4: **ADDRESSED**.

SPEC: **PASS for this scoped fix**.

QUALITY: **APPROVE for this scoped fix**. No new Critical/Important finding was found in the four fixes or their directly affected paths.

This closes the four findings from task-6-forward-review.md. It is not a new whole-component review or authorization to freeze, initialize or claim actual performance. Root's separately identified public FX endpoint/publication-contract problem remains outside this scope and is not approved by this verdict.

## Immutable scope and verification

Read the original four findings and retained independent reproducer/results, the round1 fix brief, complete FIX_BASE..HEAD patches, appended implementation report, the amended tests, current native ownership/sizing call paths and exact-commit evidence. Reviewed only T6-F1/F2/F3/F4 and fix-introduced breakage. The two amended modules still differ only in the project constants; tests are identical.

- Spot: `953caac5b244f10885e7a70b8fdb6f6e62edcde0..75c7d8efb07c98d21f1350d0f6186b48ed48a5a2`.
- Coin: `fc9b9d5230b698fd94ca95dce3092c4caf1b09ee..e9a1117a79f391346be9af85ad3636ea8d438b4d`.
- Spot complete fix package SHA: `a07a843e103f85f1181e37dcb2acf870dce3bab7e3aa7d1dab3b77606ed1c0ad`.
- Coin complete fix package SHA: `9fe07a82cfe6edc97ca830e75471afd70737ec2cb8d5a0ab562b79341c92fdb3`.
- Full appended implementation report SHA: `48f018c015eddadc210e7e97c2b1bf00bbcd6fdcb6486dab0091270360697224`.
- Spot amended module SHA: `0603b6233a0ab997ae7a5d4f5353fedf54fc1232ff06ff2d3f77fe82c2148d68`.
- Coin amended module SHA: `9d0388f34cbd41733183eeb54c7c713acb360222a48d5ba5299c328dbd7540fd`.
- Shared amended test SHA: `23ba827c1d755f97f60f7e7d2d4f3447f73b25e2bebdfd6be569fd4935aaa1ce`.

Independently compared both package bytes to Git's complete reviewed diff and both current source/test files to their exact committed blobs: all match. Only research/edge_forward.py and tests/test_edge_forward.py changed in each patch. Shared native modules and Model.restore were not changed. Both worktrees still contain only root's PROJECT_STATE.md modification.

Verified all thirteen retained evidence files against task-6-fix1-evidence-sha256.json. The unchanged original independent reproducer retains SHA `a694843536d52bc352c8c735346a6c45066f3db27ac5ee9272419a2992c1e080`. Inspected its recorded patched results and the new regressions' expected failures on exact FIX_BASE. No tests/probes/suites were rerun during this scoped re-review; no additional concrete uncertainty required a new probe. This distinguishes inspected execution evidence from fresh review-time execution.

## T6-F1 — addressed: unresolved exposure cannot receive later exact passive fills

At edge_forward.py:699–704, passive_fills now returns immediately when the existing exposure is unresolved, before inspecting later print slices or changing any model, money or ownership. The scope deliberately supplies no recovery mechanism. The subsequent ordinary decision guard continues to prevent fills, and uncertainty remains conditional/sticky.

The retained unchanged original probe now keeps BTC12.71449 unchanged, produces fills[], and audits successfully after the later local triggering print. The added regression checks actual append/reload plus wallet/BTC/fees/funding, owned quantities and installed owners, not merely the presence of a warning. Its exact-base run failed with the original three fabricated passive sales. This resolves the old-anchor reset/survival error without inventing a complete historical path.

## T6-F2 — addressed: canonical macro cap and separate target facts

At edge_forward.py:873 and 898–920, the adapter imports the existing MACRO_STOP_BUDGET constant and computes the same flat-capital macro target geometry as native_preview.entry_preview():

`min(capital * fraction / max(executable_entry, mark), capital * .03 / (executable_entry - stop))`.

That target is passed to funded_target(target_quantity=...), retaining existing funding/margin/fee/minimum constraints. Primary entries keep target_quantity=None, preserving their existing helper sizing. Neither default primary7.5/macro3.6 nor the shared helper/native preflight changes. The native import accesses a constant; no private request is invoked.

The proposed and committed records now retain original requested quantity, separately accepted quantity, sizing capital, entry/stop/take and stop budget, plus opportunity/creation/expiry. Minimum-rejected proposals retain their target without falsely committing a filled campaign. No extra same-interval or later-session topup path was added.

The original patched probe's loss-to-stop is42.81428118624 against the42.81428571428571428571428574 budget, versus the old691.89940427010. Its requested3.499840370143678081389611096 and accepted3.49984 are retained separately. Additional tests cover a cap-binding macro, higher mark than executable entry, volatility-limited target, unchanged primary accepted74.45505, funding/fees, shallow depth and minimum rejection. The exact-base macro regression failed the actual monetary cap assertion. These comparisons address the required geometry rather than asserting merely that a new field exists.

## T6-F3 — addressed: market history and owned follow state are separate

At edge_forward.py:557–574, completed OHLC still advances the market Model for indicator/ATR history, while existing owned positions advance through canonical spotquant.follow.advance(). That native function applies _high_counts against first_ms. At789–800, session._view() overlays the actual owned entry/peak/repair/adverse state only for the pure decision. Entry creation supplies the native follow fields; fill state no longer contaminates market checkpoints.

The unchanged original mid-day probe now retains peak112.133211 after the ambiguous entry-day high200. The added regression goes further: the ensuing proposal holds, booked money stays empty, the allocated stop does not tighten, audit/reload succeeds, and a later bar opening after entry correctly increases owned peak to114. The exact-base version instead sold the full position on the pre-entry wick. This demonstrates both exclusion of ambiguous entry-day highs and preservation of legitimate later owned highs. The patch reuses the current canonical helper rather than weakening its timing rule.

## T6-F4 — addressed: ordinary/partial/passive closure preserves valid checkpoints

At edge_forward.py:733–738 and 850–857, completed ownership exits use Model.note_flat() on the market-only checkpoint. For an already bearish market it preserves the valid no-reset state; for a still-bullish fresh regime it consumes the signal until a reset. The implementation no longer persists a decision view with fill-owned state or calls unconditional note_exit() on bearish market state. Shared Model.restore invariants remain unchanged.

The original synthetic ordinary sale12.71449 now audits successfully. The new ordinary-SMA regression uses a close above the adverse-stop threshold and a complete non-triggering path, then verifies append, reload, bearish checkpoint restoration, duplicate-interval rejection and one-bullish-close flat/two-close fresh entry behavior. The partial-depth regression closes some ownership while retaining the remainder, verifies each checkpoint, then executes and reloads a later passive close from bearish market state. Both relevant exact-base regressions failed with the original checkpoint error. The final recorded covering run passes these paths.

## Retained validation and limits

Inspected exact-source affected test receipts:

- Spot58 tests, OK,7 skipped; log SHA `44f84b73e3bee7eb58e1944b40017e0f31df6976b3821770f57742183c7ffd57`.
- Coin35 tests, OK,5 skipped; log SHA `11a492a1452440bc3343616af828b6634dba086fc59e5a904bc1e68aa9534226`.
- Original-probe patched output hashes: Spot `188f9f88da99a2ee140973a6f9da395123677a78dd8e1ac2cb29c7828f5919f4`; Coin `41f0854d9281a7455c1c8b0d2e62a759e6a65e56e3d44fd595506657c58211fa`.
- Exact-source smoke summary SHA `7710bf21cf8c05c79eef6a72431ddee7e5663621780ededcd5e1065c03772769`.
- Clean source receipt hashes: Spot `38ac9c1be24da93874820d80b0b8ddb150e864304d351e2d6fc63419df6a5cc1`; Coin `3d38669a88e6f635f43933777f7cb0fdc77c5c89ba1ab6afdb6e8e0ccb10779b`.

The retained synthetic CLI audits pass for Spot2events/Coin1event and explicitly identify raw reconstruction, not source authorization. Exact committed source is separately archived. Synthetic fixture clock/export/HTTP mocks do not establish genuine public observation, actual elapsed account days or performance. The Coin macro probe remains an isolated sizing fixture, not a full public-provenance ledger.

No source/helper bytes, commits, original artifacts, native/private/public requests, credentials, accounts, producers, HOME/UID settings or locks were changed by this re-review. Only this report was added persistently. No child agent was used.

Source-first export binding, protected classes, typed financial proof, clocks, raw input validation and atomic persistence are unchanged by the scoped patch. Source changes require new approved binding; no migration/relabeling of the pre-fix synthetic diaries is implied. Root still owns the separate real FRED acquisition/publication fix, final financial proof/export and actual empty initialization. Sticky exposure uncertainty and the absent Coin complete mark-path adapter remain declared limits. Native cases0/actual account-days0/NOT_QUALIFIED and the lack of continuous/prospective/native performance proof are unchanged.
