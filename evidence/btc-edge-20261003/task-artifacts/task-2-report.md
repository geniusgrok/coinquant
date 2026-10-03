# Task 2 — frozen protocol and verified point-in-time public features

Status: **DONE_WITH_CONCERNS**, ready for controller independent review. Both protocols/specs, standalone readers, Spot offline builder, meaningful affected tests and real source-bound feature/coverage artifacts are complete. No new financial outcomes, native requests, accounts/orders/transfers/settings, state/docs edits by this task, or historical evidence mutation occurred. The preserved interrupted Spot implementation was reused and corrected rather than discarded. No subagents were used.

## Scope, source commits and ownership

Worktrees `/workspace/btc-alpha-beta-improve/{spotquant,coinquant}`, branch `codex/btc-alpha-beta-improve-20261003`. Read the exact task-2 brief and both AGENTS before implementation. Task1's corrected v3 diagnostic and full report were read: ordinary SMA exits account for the largest classified flat sleeve endpoints; earliest Coin ±60s divergence uses different observed marks and consequent sizing/rounding. No precise unnecessary same-observation dependency was established, so no phase fix is registered.

- spotquant: own final commit `1a229ac906dd5747dee32b5962de969e2865f7f8`; task-scoped diff parent `eab7260e8d6024a3023bfd519a99ba7076fa0d65`.
- coinquant: own final commit `7828caa1188c44d91538630e054fc52d9049b1e5`; task-scoped diff parent `f7667088aa89d26765b5be07e9c84d44858e7b32`.
- Coin implementation commit `34fcca1e0bb836c5ac2567e33ea281c02fd84a8c`, followed by whitespace-only `7828caa1188c44d91538630e054fc52d9049b1e5` removing a trailing blank line. The initial Coin staged whitespace check exposed that line; final scoped checks pass.
- Original prepared bases remain Spot `13de06c` / Coin `3bcd3f5`. Controller-only recovery/state commits intervened; they are excluded from the task-scoped diff using the actual parents above. Each task diff contains exactly its four new allowed files: research/edge_spec.json, research/edge-PROTOCOL.md, research/edge_features.py and tests/test_edge_features.py. Both trees were clean at report generation.

The task commits are local; integration/push/CI and independent review belong to the controller. No old source identity was relabeled and no financial producer ran.

## Frozen registration and behavior

Project schema kinds are `spot` / `perp`, matching existing assessment/source interfaces. Each project has its own spec/protocol and baseline (`atr-stop` / `incumbent`), while common economics, availability, risk/adoption gates, controls and portfolio registration agree exactly.

The finite Spot order is exit-confirm / stop-budget / crowding-interaction; Coin quality-budget / cost-horizon / crowding-interaction. Thresholds/scopes are fixed without parameter or subset searches. Ordinary Spot SMA exit waits until BOTH completed closes are below/equal to their own contemporaneous SMA; missing previous history preserves the original exit. All safety exits remain prior. Stop-budget limits genuine new BUY risk to .12 of whole-account marked USDT equity including existing proven owned protection risk and proposal fees/slip distance. Both crowding candidates halve new risk only for funding>.0003 AND basis>.01 AND weak completed-bar momentum; missing/stale features block new risk only, never safety exits. Coin quality affects primary new entries only, and cost-horizon permits only the registered legal-session exit / one durable primary trigger+10day extension at age>=5 and<7days. Macro receives no primary lifetime.

Registration includes all original constraints/targets, original four stresses per project, actual protected-participation25/50/75/100 plus cash, risk bands/tails/underwater/all-stress selection, complete eligible combinations, fixed CNY2500/7500,5000/5000,7500/2500 pairs and neutral5000/5000. Predeclared inventory: Spot36 unscaled accounts, Coin16, baseline+3 actual calibrated base accounts per project, incumbent ±60s base diagnostics, fixed actual budgets, applicable combination four stresses+actual calibratedbase. Controls disclose their distinct signal/protection rules and cannot be relabeled pure buy-and-hold or constant weights.

Calibration follows existing `alpha_assessment.calibrate`: min(1, baseline vol/candidate vol when candidate vol>0, max(.01, baseline beta)/max(.01,candidate beta) when candidate beta>baseline and positive). The .01 floors are only beta-ratio operands; scale0 is valid, and no outer .01 floor is added. Training is exactly7312020–2021USDTdays; scale1 before2022, actual new sizing after cutoff1640995200000 only. Own profiles bind project/baseline/spec/source/input. Risk-only MDD improvement compares the actual calibrated candidate against actual unity baseline while retaining unscaled all-stress gates. Baseline equality preserves all six financial/fills/daily/ownership/remaining_original_fields/operating groups under only previously allowed normalization. Every original annualization convention remains binding.

## Feature implementation and source verification

`FeatureBook(path, expected_sha256=None).value(name, now_ms)` returns Decimal or None. The reader validates unique JSON keys, file hash if pinned, canonical content hash, registered raw identity, all six market identity hashes, exact availability assumptions, format/containers, finite decimal strings, nonnegative integer timestamps excluding booleans, strict unique sorted stamps, exact lags, UTC basis completion boundaries and recomputed frozen-window coverage. Optional `last_lookup` records selected observation/availability/age/value/missing cause and source hashes. It has no adapter requests or sibling runtime import. The complete reader logic/helper segment is identical in both repositories; Coin contains no builder dependency on Spot.

Funding observation is the unchanged actual settlement timestamp; availability=settlement+28800000ms. Latest rate with availability<=now is usable only when age<28800000ms; exact eight-hour expiry is stale with no jitter repair/tolerance. Negative rates are retained. Basis observation=raw available_ms-60000, the previous matched UTC-day completion boundary; all raw availability stamps are unchanged. Maxage1DAY plus current UTC availability date prevents carryover during daily publication gaps. Publication+60000ms is an explicit modeled assumption, not observed publication. It is daily trade-close basis, not executable instantaneous basis. Null values require an explicit cause; absent/stale/unavailable/outside-window lookups produce cause-bearing None, never fabricated zero.

Raw tails are preserved for identity. Historical lookup is restricted to [1577836800000,1789862400000); retained future rows cannot extend it. Forward data require separate observations/artifacts, never historical backfill. Completed trend/trigger histories remain in each project model; this artifact supplies only settled funding and lagged basis.

The controller's prior `research.prepare_inputs.build` reconstruction is reused, as explicitly authorized. Both reconstructed/raw byte identities were independently rehashed, then builder rechecked every registered futures archive's size/hash/CHECKSUM, official warmup trade/funding bytes, separately registered September funding hash/CHECKSUM, all111 Spot archive CHECKSUMs and aggregate Spot identity. There are180 registered futures archive rows. Full market reconstruction was not redundantly rerun. The retained original futures artifact was independently rehashed by the acceptance verifier. Exact funding observation/value pairs and basis availability/value pairs were compared against every registered raw row. No copied metadata can override the immutable registered raw digest.

- futures_market_sha256: `2a995b586a717a5346534656b8b23f3dbd008fde60afec32e68f94cd3af9f09e`.
- original_futures_artifact_sha256: `52a8fa8f71edc2b2e86ff63b2b495d0941d63c6cd8c8b25665ffe53273f06430`.
- september_funding_archive_sha256: `913cd31b8f924a06717a2fac17f3df6132c24ccded209eb3e4ae7d83e1b247f2`.
- spot_daily_sha256: `3f6151860a87e8f82f315dc59581d6b73e4debf1ef5e3b86fb2e4d1ca987954e`.
- warmup_funding_sha256: `25a949a83bc5305727fb86f0d6e3e297235a03990d6404a3f160a2ce82bd82b3`.
- warmup_trade_sha256: `62e9a9ecddccac737f99032a224f7a2a1932756cf200db34fb5c5641b72c4094`.

- Registered raw: `1d87be0b4c8cd8a7eacd4970a1a194e5f1ed0b2f3aa3710a43417aa9ab066ef2`, 387544bytes, both `/tmp/btc-complete-inputs/crowding-complete.json` and `task-artifacts/crowding-verified-before-edge.json`.
- Reader logic SHA-256: `e392863199e1870e849c9da341fce1d8ea5e9c00dbc240d1f08b2b3f3d656733`.
- Original schedule SHA-256: `c21b4fcfe3cb12fb062bb01d3c3591aa0ee8c65db9e9afde3c26b1bcdc2ac28e`.

## Real coverage and material missing-input evidence

Window duration212025600000ms (2454days). These are feature availability intervals, not account returns/execution curves.

| Feature | Raw rows | Available stamps inside window | Negative raw rows | Known duration ms | Missing duration ms | Missing intervals |
|---|---:|---:|---:|---:|---:|---:|
| funding | 7488 | 7362 | 1070 | 212025586885 | 13115 | 2276 |
| basis | 2485 | 2454 | 1841 | 211878360000 | 147240000 | 2454 |

Both raw series have zero null rows. Raw funding begins1575158400000 and ends1790784000002; raw basis observation boundaries begin1575244800000 and end1789862400000. Tail records outside the frozen window stay retained. Funding settlement jitter modulo8h ranges0–47ms and its complete histogram is in the artifact/acceptance receipt. Funding gaps total13115ms across2276intervals; daily basis publication/current-date gaps total147240000ms across2454intervals.

Real scheduled-clock coverage probes read the original795starts and60nominal five-second polls per300-second session (47700probes per feature): funding47677known /23stale; basis47268known /432current-date mismatch. These are nominal clock probes, NOT actual adapter decision timestamps or executable account evidence. Candidate new-risk decisions during a gap must block safely and journal their actual-clock causes; no repair/tolerance or safety-exit suppression is permitted. Safe, cause-known missing-feature blocks are distinguishable from unknown/unverifiable fills. Coverage therefore cannot be described as known at every scheduled poll, and prospective candidate financial performance remains unmeasured.

## Exact commands and verification

Commands executed from the named project cwd unless an absolute script path is shown. Only affected offline checks were run for this task. Coin tests were reserved/coordinated and strictly serial; HOME/UID/locks were unchanged.

1. Spot cwd: `python3.13 -m unittest tests.test_edge_features -v > /workspace/btc-alpha-beta-improve/task-artifacts/task-2-spot-tests.log 2>&1` — final22tests PASS,0.018s. Seventeen shared temporal/input/spec tests plus five Spot builder/checksum/output tests.
2. Coin cwd: `python3.13 -m unittest tests.test_edge_features -v > /workspace/btc-alpha-beta-improve/task-artifacts/task-2-coin-tests.log 2>&1` — final17tests PASS,0.012s. The later Coin EOF cleanup is whitespace-only; no logic changed after these checks.
3. Spot cwd: `python3.13 -m research.edge_features --build --crowding /tmp/btc-complete-inputs/crowding-complete.json --verified-crowding /workspace/btc-alpha-beta-improve/task-artifacts/crowding-verified-before-edge.json --perp-repo /workspace/btc-alpha-beta-improve/coinquant --perp-market /tmp/coinquant-market --spot-market /tmp/spotquant-market/klines --out /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json > /workspace/btc-alpha-beta-improve/task-artifacts/task-2-build.log` — exit0,7488funding/2485basis, immutable1,049,039byte artifact.
4. `python3.13 /workspace/btc-alpha-beta-improve/task-artifacts/task-2-verify.py > /workspace/btc-alpha-beta-improve/task-artifacts/task-2-verify.log` — exit0/PASS. Independent all-row raw identity comparison, original futures hash, identical reader logic and independently executed standalone readers, every availability/expiry/day/window boundary plus nominal frozen-session probes, and immutable-output rejection.47,357unique timestamps ×2features =94,714boundary lookups per repository have identical decisions/metadata digest `19b6257a0447ea4b194bb534457b33bf4acad8acf6859176f8d01a83f5a5cd72`.
5. The verifier invokes existing-output rejection from Spot: `python3.13 -m research.edge_features --build --crowding /tmp/btc-complete-inputs/crowding-complete.json --out /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json` — exit2 before archive processing; bytes/SHA unchanged.
6. `git diff --check` and `git diff --cached --check` on each own patch; final `git diff --check PARENT TASK_HEAD` scoped comparisons pass. Initial Coin staged EOF whitespace warning was fixed in its second own commit. Final own diffs contain exactly the four allowed new files. Common spec dictionaries match after excluding the explicitly project-specific candidate/account/stress/target fields.

The first synthetic run had two fixture-construction errors: its coverage helper compared a malformed string timestamp before invoking the reader. The fixture was corrected to recompute only its content hash for malformed timestamps; the final tests reach and prove reader rejection. No malformed data were accepted and no financial/old evidence was changed.

Tests cover before/at availability, exact expiry, unmodified settlement jitter gaps, negative funding, absent/null/current-date/stale basis, invalid timestamp/lag/UTCboundary/order/duplicates/JSON/container/value/hash/format/source records, future-tail perturbation invariance, journal source/cause metadata, window exclusion, project-bound finite registration, changed registered raw rejection, required CHECKSUMs, exclusive output creation and pre-write artifact validation. Standalone parity and real source checks add acceptance coverage beyond fixtures. The controller's209Spot/359Coin pre-task baseline suite results were reused as historical environment context only; they were not rerun or attributed to these task commits.

## Artifact and committed-file SHA-256 inventory

All task artifacts below are external to the repositories. Every prior report/raw/cached public byte remains retained; no old evidence was replaced.

- `/workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json`: `bf920626cc13653b8bbeafd171650cc1a76888e15aad0c20bbd1061fb41da512` (1049039bytes).
- `/workspace/btc-alpha-beta-improve/task-artifacts/task-2-acceptance.json`: `f13ed01e9109075ee6f5a4adb921f3982d0c2789e74b30af65ca78c656f381a0` (371673bytes).
- `/workspace/btc-alpha-beta-improve/task-artifacts/task-2-verify.py`: `8dfb9380266485c0b17002b6a71effd0f1e3142ec2850988efc303fb658795c8` (4655bytes).
- `/workspace/btc-alpha-beta-improve/task-artifacts/task-2-spot-tests.log`: `8a63aa4edf47256b2585d5235b64fe04a15c278cb8ce861b64724ac268605789` (3515bytes).
- `/workspace/btc-alpha-beta-improve/task-artifacts/task-2-coin-tests.log`: `f52494abbda91b78f042f20263910e47d0457464a34c1cd3ae7ba77f3f980e85` (2666bytes).
- `/workspace/btc-alpha-beta-improve/task-artifacts/task-2-build.log`: `c4a39254d9824ad23aa38bcad5e009c58e88c40289b43f7bf9b2a4d9333b93f3` (152685bytes).
- `/workspace/btc-alpha-beta-improve/task-artifacts/task-2-verify.log`: `c4a38c3871b666121e772092e633e136d9382be22501bfda457a87f1150f36c8` (1414bytes).
- Feature canonical content hash excluding its own field: `89ac6c8d62e65581b78f4363ef9c12e5cc06035706620538792de392d6d55d0d`.

spotquant own final commit `1a229ac906dd5747dee32b5962de969e2865f7f8`:

- `research/edge-PROTOCOL.md`: `c20446129708ef998ce9ab403ec6a14760b008cc00ad0ad49ea3488c2dc897bd`.
- `research/edge_features.py`: `84a1a109f0262f61380185b955afaab634f42d247be92050142dabde4252c766`.
- `research/edge_spec.json`: `af23d8afdce40c7cfc60387cc70e0332739a017c7b9a5460b9a5dbe9444b409f`.
- `tests/test_edge_features.py`: `e0df84295067229d82e7f52820e7692bf4d70d483cf92c04310fd68599f045ca`.

coinquant own final commit `7828caa1188c44d91538630e054fc52d9049b1e5`:

- `research/edge-PROTOCOL.md`: `714e0eae887fc9aac79380662c7db1e931823484fc2fe3781c80c2853bb4163b`.
- `research/edge_features.py`: `1af4444c3714b737651f736b905fef47c56732421767bf169ac661f2b1ee92d5`.
- `research/edge_spec.json`: `53296233aadc6429359dd7b664c4e03a28eb451d6bacf4318fced4ce13f7e3de`.
- `tests/test_edge_features.py`: `112f3c2c8707cac60d816e11b60c220349f9f440ad8ae0ce1d322251a1b06692`.

## Self-review and concerns

Self-review compared all registered inequalities/scopes against the brief and controller corrections: exit confirmation exits on BOTH below/equal and cannot delay missing-history exits; calibration has no outer .01scale floor; project schema kind is perp; risk-only MDD is actual calibrated-vs-unity; baseline remaining group is remaining_original_fields. Checked all-stress/capital/combination inventories and separate project source binding. Verified no adapters/requests, future-known selection, timestamp repair, sibling reader import, unrelated edits or financial replay. Canonical hashes/explicit source records bind this build, and output validation occurs before exclusive file creation.

Material limits remain: official historical data plus assumed basis publication do not establish actual native publication or executable instantaneous basis; frozen coverage is not known at every scheduled poll; actual decision clocks must be journaled downstream. A recomputed content hash is integrity/provenance binding, not a signature/authenticity proof; consumers should pin the reviewed file SHA when loading this immutable artifact. The full raw reconstruction was previously performed by the controller, then independently byte/source-verified here as authorized, not independently reconstructed a second time. No financial improvement/adoption decision, original-target achievement, prospective alpha or native qualification is claimed. Historical-selection contamination and continuous-proxy limits remain. Independent controller review/integration is pending.

Status: DONE_WITH_CONCERNS; Task2 implementation and authorized verification are complete, with precise missing-input limitations retained for Tasks3–6.
