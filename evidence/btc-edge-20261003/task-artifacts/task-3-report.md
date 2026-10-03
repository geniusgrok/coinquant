# Task 3 — Spot registered mechanisms and actual execution controls

Status: **DONE_WITH_CONCERNS**. Implementation and offline verification are complete. Independent task review and complete registered financial measurements remain pending; no default or native-account changes occurred.

## Review and commit identity

Review BASE: `bdde051095453cbb32163b7a9913df208a52f0f2`.

- `ddccd6074f773e7b0aaf2d4e8a17682bccc95599` contains the initial implementation and final source/dust guards. The controller's PROJECT_STATE commit coincided with my staged implementation files and included them; controller acknowledged the shared-index sequencing. No reset/rewrite was performed.
- `6eb9474cf50f8d00de06e5e727235f31b812853d` is my path-only final correction: wholly unprotected owned dust blocks stop-budget new risk, plus regression coverage.

Owned files: `research/edge_spot.py` and `tests/test_edge_spot.py` only. Earlier source modules, incumbent defaults, input caches, frozen results, runtime account configuration and credentials were not edited. Source was clean and committed for every CLI receipt. These are development/smoke identities, not a premature full-financial source freeze.

## Implemented behavior and self-review

All three single mechanisms, registered multi-component combinations (at least two distinct components in registered order), the ATR incumbent and cash/25/50/75/100 protected participation controls use the existing finite meter/session/Lifecycle and three-sleeve allocation ownership.

`exit-confirm` wraps the existing owned-position decision only during the scoped decision call. It calculates previous SMA from that previous close's own completed window, treats equality as below, and preserves original exit when prior history is insufficient. It keeps the bearish bullish-vote flag unchanged; native/through-mark, adverse, overextended and repair behavior retains priority. Checkpoints stay original market-history models under a source/profile/mechanism-bound wrapper.

`stop-budget` bounds genuine new BUYs by 12% of current whole-account marked equity minus allocated active-stop risk for every owned sleeve. Active protection must have attributable groups, positive weights, quantity, finite stop, current campaign association and native NEW/PARTIALLY_FILLED status. Remaining native quantity subtracts actual native executed quantity. Whole-account BTC and durable position ownership must match. A proven active-stop sub-step rounding discrepancy is charged at full mark; zero stop coverage blocks even tiny closed dust. No balances or dust are discarded. Proposal loss per quote is the larger of actual proposed stop/entry distance and fill-based ATR trail distance, plus current fee150/base cash fee reserve, entry/stop slippage reserves and a one-price-tick reserve. Spending never exceeds the original canonical proposal, free cash or capital allowance; holds are not resized. The journal records budget, existing risk, entry estimate, reserves, loss per quote, resulting rounded quote and blocked cause. It is an estimate, not a bound on gaps or latency price jumps.

`crowding-interaction` calls the pinned standalone FeatureBook strictly at the actual adapter decision clock only for a genuine new BUY. Its journal retains each real lookup's value, observation, modeled availability, age, missing cause and artifact/raw/market bindings, plus completed current/five-days-ago momentum inputs and causality. Missing/future/stale/date-mismatched inputs block only new risk. Baseline and non-consuming controls do not perform feature lookups. Funding/basis are never fabricated as zero.

Protected controls use unconditional first legal entry after the actual checkpoint/new completed bar, static 28% fill-based trailing native protection, original capital and ownership/pending/cold-start gates, actual allocated net fills, actual fees and all retained dust. Each entry spends the declared fraction of then-free cash under the capital ceiling. They have different signal/protection rules from ATR: they disable SMA/adverse/overextended/crash-repair entry/exit policy while retaining protective exits. They are protected funded accounts, not pure buyhold or fixed-weight curves. A subsequent entry waits until a completed UTC day later than the actual stop fill's UTC day. An active sub-step partial fill is held; only the original follow's explicit dust flag, applied-sale proof and owned-dust view marker can permit a new campaign, still conservatively blocking quantities at or above BASE_STEP. Original follow folding and weighted cost basis remain unchanged.

Durable identity binds executable research/runtime Python bytes, exact spec, candidate/components, full risk profile/file hash and consumed feature bytes. Rule, checkpoint, missing binding, foreign profile and changed execution-source identities reject before Lifecycle recovery. Scoped Model/State/portfolio/guard/rule/static-control hooks restore on all exceptions. Serial execution only; no threads or delegation.

The project-specific risk document validates all included profiles, duplicate JSON keys, exact document/profile keys, own project/candidate names, atr-stop baseline, exact edge spec, training end2022 and cutoff1640995200000, lowercase64-hex base_bundle_sha256, finite string scale0..1, and baseline exactly scale1. Scaling affects only actual new orders at/after cutoff; earlier orders remain scale1 and held protection/target size stays unchanged. The base artifact hash is a binding; proving the referenced original raw complete account and trained formula remains the independent assessor's responsibility.

The baseline calls unchanged `complete_spot.measure(...canonical=True)` with no legacy calibration file. The new unity edge profile is validated separately and bound in the edge envelope. Original canonical row candidate/research/risk identities remain unchanged. The synthetic no-op test compares direct `adoption_spot.measure` against the edge baseline using every existing six-group `evidence_fingerprints` group. New metadata uses the top-level edge envelope and only the established row additions `research_identity`, `opportunity_ledger`, `risk_calibration` for mechanisms/controls.

## Tests and results

- `python -m compileall -q spotquant research tests`: exit0.
- `python -m unittest discover -s tests -v`: final **261 tests passed in11.446s**, exit0; log `task-3-tests-final.log`.
- `python -m unittest discover -s tests -p 'test_edge_spot.py' -v`: final **13 tests passed in5.227s**, exit0; log `task-3-edge-tests-final.log`.
- `git diff --check`: exit0 before final commit; final worktree clean.

The focused tests cover contemporaneous previous SMA/equality/missing history; ordinary delay retaining bearish consensus vote; adverse/extended/native/through-close/repair priority; aggregate allocated risk, fee stress, ownership/protection malformation and dust; min-notional/quote rounding; actual-clock future/stale FeatureBook input, weak versus strong completed momentum, missing-feature safety exits; scale0 and exact before/at cutoff; held/dust/active sub-step no-topup guards; actual cash and both25/100 controls with real entry/stop/reentry fills, fees, current native stops and next-day wait; unbound/profile/rule/checkpoint/source mismatch spies proving recovery was not called and SQLite/sent bytes unchanged; hook restoration after injected decision/meter failures; baseline six original groups and actual CNY2500 capital path. Registered combos reject singleton/duplicate/unregistered parts.

No Coin account jobs, native calls or full-window financial matrices were run.

## Final clean-source CLI smoke

Ten isolated sequential one-candidate commands below completed with exit0. Seven base cases use only the first2 original starts; three ATR stress cases use only the first1 original start. They retain the original schedule and clocks. All outputs are explicitly `complete=false`, `cagr=null`; all original fields are present, monetary audit passes, no pending intents or unresolved sessions remain, and all session archives are integrity verified with retained raw archive hashes. The two protected controls each produce one actual historical fee-bearing BUY and owned installed protection. Mechanisms and baseline remain flat in these earliest2 sessions: **zero real crowding lookups in these tiny CLI smokes**, disclosed rather than claiming full decision feature coverage; future/stale/actual-clock mechanism branches are covered by the focused tests. Real stop/reentry behavior is established by the actual finite synthetic-control tests.

`task-3-smoke-final-manifest.json` retains exact commands, outputs, SHA256s and per-command logs; `task-3-smoke-final-verification.json` retains assertions/counts. Re-running the baseline command against its existing output rejected with exit2 and the exact prior bytes unchanged (`task-3-overwrite-final-check.log`). Earlier ddccd60 partial receipts and their initial manifests/logs remain preserved, explicitly incomplete, and are not relabeled as final-source receipts.

Final source/input bindings:

```json
{
  "source": {
    "git_head": "6eb9474cf50f8d00de06e5e727235f31b812853d",
    "dirty": false,
    "python_sources_sha256": "59faadcdda379ec8d0d79bb35adcfe97abbe875a0b85339da62ea3bb748e19cb"
  },
  "spec_sha256": "af23d8afdce40c7cfc60387cc70e0332739a017c7b9a5460b9a5dbe9444b409f",
  "protocol_sha256": "c20446129708ef998ce9ab403ec6a14760b008cc00ad0ad49ea3488c2dc897bd",
  "feature_sha256": "bf920626cc13653b8bbeafd171650cc1a76888e15aad0c20bbd1061fb41da512",
  "market_sha256": "3f6151860a87e8f82f315dc59581d6b73e4debf1ef5e3b86fb2e4d1ca987954e",
  "schedule_sha256": "c21b4fcfe3cb12fb062bb01d3c3591aa0ee8c65db9e9afde3c26b1bcdc2ac28e",
  "fx_sha256": "67606315ea34c0301e0129ac8fc27056099986d9fbd58a552a07f140cdd05bb5"
}
```

Original baseline row research identity (preserved; distinct from new edge envelope):

```json
{
  "execution": "canonical_shared_session",
  "candidate": "atr-stop",
  "components": [
    "atr-stop"
  ],
  "spec_sha256": "8228013f4ac41affb65162c1cabad8f51b5ef32b9607f62231a4776168a337d0",
  "risk_scale": "1",
  "core_mode": null,
  "core_fraction": "0",
  "rule": "2026-10-02-atr-stop",
  "cutoff_ms": 1640995200000,
  "scale": "1",
  "calibration_sha256": null,
  "profile": {
    "scale": "1",
    "sha256": null
  },
  "profile_sha256": "0176f4e1ab75a42afd7236214416c80b211a184493cd68b8ba2ca2dfe29ef836"
}
```

- Command: `/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python -m research.edge_spot --candidate atr-stop --scenario base --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json --limit 2 --out /tmp/spot-edge-task3-final-atr-stop-base-1790988715073070248.json.gz`
  - Output SHA256: `f76d0bde763b6211e967dfc79c3a0d4bf0e1e4a0e301f426418ff0407bc93e70`; exit0.
- Command: `/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python -m research.edge_spot --candidate exit-confirm --scenario base --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json --limit 2 --out /tmp/spot-edge-task3-final-exit-confirm-base-1790988715073070248.json.gz`
  - Output SHA256: `145ba6e32637c8a23312a19cffe79a76d7dffbb4bdb16f3e9ea3b8aabc9abba3`; exit0.
- Command: `/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python -m research.edge_spot --candidate stop-budget --scenario base --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json --limit 2 --out /tmp/spot-edge-task3-final-stop-budget-base-1790988715073070248.json.gz`
  - Output SHA256: `ffef1a7b4ed20df228dc31c96a04ca7086be427fc2a91a1f6d7e7586575e54b2`; exit0.
- Command: `/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python -m research.edge_spot --candidate crowding-interaction --scenario base --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json --limit 2 --out /tmp/spot-edge-task3-final-crowding-interaction-base-1790988715073070248.json.gz`
  - Output SHA256: `ab9ca66a50eda6f0bf6c69af94d2dbd85cb3744e150cfdd8717fb5a55479ccf3`; exit0.
- Command: `/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python -m research.edge_spot --candidate cash --scenario base --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json --limit 2 --out /tmp/spot-edge-task3-final-cash-base-1790988715073070248.json.gz`
  - Output SHA256: `98a799ba777b642c7411a2d7d76a53d65ab6ae0a31f2a966f5be51e77c58cd98`; exit0.
- Command: `/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python -m research.edge_spot --candidate protected-participation-25 --scenario base --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json --limit 2 --out /tmp/spot-edge-task3-final-protected-participation-25-base-1790988715073070248.json.gz`
  - Output SHA256: `ed497a7f996bb41cf052ba3160a0d80d38809375294a267f42bf581c9a79dcf9`; exit0.
- Command: `/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python -m research.edge_spot --candidate protected-participation-100 --scenario base --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json --limit 2 --out /tmp/spot-edge-task3-final-protected-participation-100-base-1790988715073070248.json.gz`
  - Output SHA256: `8293d01ee936d90a6ef48ee930a154d4ceda554a52ba15e4c3b3198edbefc1d8`; exit0.
- Command: `/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python -m research.edge_spot --candidate atr-stop --scenario fee150 --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json --limit 1 --out /tmp/spot-edge-task3-final-atr-stop-fee150-1790988715073070248.json.gz --initial-cny 2500`
  - Output SHA256: `395592daf8261d2c82f2a90127c222dbc4d079bd66b8bbb68eadd4ff75e14591`; exit0.
- Command: `/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python -m research.edge_spot --candidate atr-stop --scenario slip2 --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json --limit 1 --out /tmp/spot-edge-task3-final-atr-stop-slip2-1790988715073070248.json.gz`
  - Output SHA256: `d236acd5097e9fa760f52e6ea772c4aabc04f9e86fa63dae1f70a40c59ea0b3b`; exit0.
- Command: `/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python -m research.edge_spot --candidate atr-stop --scenario outage --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json --limit 1 --out /tmp/spot-edge-task3-final-atr-stop-outage-1790988715073070248.json.gz`
  - Output SHA256: `ac9c05c508a8406041f4925a5827822bb0f61cdd1441b4d79b687b437019953f`; exit0.

## Material concerns and limits

1. This implementation has not passed the independent Task3 review yet; no financial/default/native qualification follows from tests or partial receipts.
2. Stop-budget may correctly refuse future new risk after actual stopping leaves unprotected owned dust. It must not silently erase/rescale that dust to evade the registered missing-protection block.
3. Verified funding/basis records have genuine stale/current-date missing intervals. Full execution can remain known when the registered rule blocks a BUY, but all-session known-feature coverage cannot be claimed. The tiny CLI mechanism cases contain no entry opportunity and hence no consumed lookup counts.
4. Current OHLC high-before-low and modeled publication/slippage remain proxies. Stops can gap; protection submission and confirmed cancel/replace retain the original non-atomic limitations. Native qualification remains NOT_QUALIFIED, actual account-days0.
5. Hooks are process-local and require serial accounts or separate isolated processes; there is deliberately no new orchestration/threading framework. Profile source-raw completeness/training provenance is assessed downstream from the bound base_bundle_sha256.

File SHA256 `research/edge_spot.py`: `0173f8cf23c52e2220362640172f8e7b34ac637637c8dfb002b0a1142a90193f`.

File SHA256 `tests/test_edge_spot.py`: `8d86ada32674160030c8b804ee12f73805c8f1c769f3249e5429ca75d5a3ce8c`.
