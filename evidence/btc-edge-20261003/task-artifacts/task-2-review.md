# Independent Task 2 review

Spec verdict: **PASS**.

Task code-quality verdict: **APPROVE**.

Critical findings: 0. Important findings: 0. Minor findings: 0. Required fixes: none. No finding IDs were issued because no actionable defect was substantiated.

## Exact scope and identity

Reviewed the Task 2 brief, review brief, both AGENTS, full Task 2 report, both task-scoped diff packages, and all eight introduced files. Target commits are Spot `1a229ac906dd5747dee32b5962de969e2865f7f8` against `eab7260e8d6024a3023bfd519a99ba7076fa0d65`, and Coin `7828caa1188c44d91538630e054fc52d9049b1e5` against `f7667088aa89d26765b5be07e9c84d44858e7b32`. Each diff contains exactly the four allowed new files. Independently compared the actual Git diff bytes to each supplied package: exact match. Current controller metadata HEADs are Spot `74ea03037361650af3e075a69e7fef89df814f5e` / Coin `aa1488d4b5ada95f10e01cd94d8940f5c51422d8`; all four task files remain byte-identical to their target commits, and both trees were clean.

Applied the code-review skill. No subagents, source edits, commits, financial producers, downloads, native requests or account actions were performed. Only this requested review artifact was written.

## Specification assessment

The two machine specifications and prose protocols agree on the original BTCUSDT economics, CNY10000/no additions, exclusive historical window, finite session/poll clocks, ownership/protection/capital restrictions, stopped-client prohibition, targets, and NOT_QUALIFIED/zero-account-day status. They retain separate `spot`/`perp` identities and `atr-stop`/`incumbent` baselines.

The Spot registration preserves the required exit-confirm direction and equality: exit only after BOTH completed closes are below/equal to their own contemporaneous SMAs; missing preceding history cannot justify a delay. Stop-budget applies only to genuine new BUY, counts all proven owned protection risk and fee reserves against .12 of marked whole-account equity, and caps the original proposal. Crowding is the three-condition interaction, preserves strong momentum, and blocks missing-feature new risk without suppressing safety exits. Coin quality-budget fixes all three causal conditions and the 1/.5 multipliers with committed-target/protection preservation. Cost-horizon fixes legal session decisions, primary trigger-relative age >=5 and <7 days, one durable trigger+10-day extension, original protection and macro exit-only scope. Coin crowding is separately registered and macro-neutral. Neither protocol registers a timing fix or chooses a schedule offset.

Controls, all four project stresses, all single candidates, actual calibrated base reruns, fixed budgets, applicable full eligible combination and neutral CNY5000/5000 account pair are frozen. Both specs preserve all six baseline equality groups, including operating and remaining_original_fields. Adoption retains the original all-stress CAGR/MDD gates, base improvement, worst day, ES99, underwater and actual risk/validation return gates, with no target relaxation or subset search. Risk calibration uses only 731 training days, cutoff1640995200000, actual subsequent new-order sizing, separate project-bound profiles, and beta-operand floors only; no outer .01 scale floor or curve scaling is introduced. See both `research/edge_spec.json` and `research/edge-PROTOCOL.md`, particularly Spot spec lines210–220 and the corresponding Coin risk block.

Feature lookup selects the latest record available at the query time, applies settlement+28800000ms and exact age>=28800000ms funding expiry, preserves settlement jitter and negative rates, and applies basis boundary+60000ms with current UTC availability date and maxage. Explicit null causes and missing/stale/outside-window results are preserved. The frozen endpoint remains exclusive; future records cannot extend it. Evidence: both `research/edge_features.py:117`, `:158` and `:195`. Tests include a genuine changed/appended future tail, rather than comparing a book with itself.

## Code-quality and source assessment

The reader is small, standalone and standard-library-only, with identical reader logic in both repositories. It validates duplicate JSON keys, content hash, optional pinned file hash, registered raw digest, source hash field shapes, exact assumptions, finite Decimal strings, integer times, sorted unique observations/availability, lags, basis UTC boundaries and recomputed coverage. No runtime sibling import or adapter request exists. Binary search gives causal selection without scanning future records. Cause-bearing lookup metadata binds artifact/raw/market identities and selected observation clocks.

The Spot builder binds the preverified reconstruction to the registered immutable raw digest before inspecting source metadata (`spotquant/research/edge_features.py:244`), then verifies the registered official futures archives and warmups, September funding archive and aggregate Spot archive identity (`:254`). This meets the brief's explicit authorization to reuse the controller's previously reconstructed input when its identity matches; a redundant full reconstruction is not required. Final output bytes pass the same reader validator before exclusive `xb` creation (`:314`). Existing-output rejection, checksum failures and pre-write validation are covered by meaningful affected tests.

Independently checked retained bytes and source consistency rather than relying solely on the report or copied metadata:

- Both crowding raw files match registered SHA-256 `1d87be0b4c8cd8a7eacd4970a1a194e5f1ed0b2f3aa3710a43417aa9ab066ef2`.
- Artifact file SHA-256 is `bf920626cc13653b8bbeafd171650cc1a76888e15aad0c20bbd1061fb41da512`; its canonical content hash and acceptance receipt source/coverage match.
- All 7488 funding observation/value pairs and 2485 basis availability/value pairs match the raw reconstruction exactly.
- Retained original futures artifact bytes match their recorded source hash. Futures identity canonical hash, Spot identity, September archive identity and both warmup identities agree between the registered raw and feature artifact.
- Independently summed valid intervals using the next record, exact expiry and frozen bounds: funding212025586885ms known/13115ms missing; basis211878360000ms known/147240000ms missing. These agree with the artifact and receipt.

## Verification performed

Strictly sequential affected runs:

1. Spot cwd: `python3.13 -m unittest tests.test_edge_features -v` — 22 tests PASS,0.025s.
2. Coin cwd: `python3.13 -m unittest tests.test_edge_features -v` — 17 tests PASS,0.015s. Root confirmed the serial lane clear; no other Coin producer/test ran concurrently.
3. `git diff --check PARENT TASK_HEAD` in each repo — PASS.
4. Read-only Python3.13 independent identity/coverage/boundary verification from `/workspace/btc-alpha-beta-improve`: exact Git/package comparisons; retained raw/artifact/futures/content/source/receipt checks; both reader modules loaded independently; 29952 funding and9940 basis paired probes at every raw record's availability-1/availability/expiry-1/expiry — PASS. Both standalone books gave identical values, and at in-window availability each yielded the expected raw Decimal. No verification output file was created.

The implementation's retained acceptance verifier/log additionally documents94714 boundary lookups per repository and47700 nominal scheduled probes per feature. I inspected those receipts and independently checked the artifact identities they bind; I did not rerun the receipt-producing verifier because it exclusively creates an already-existing acceptance file.

## Retained limitations, not defects

Historical public bytes do not establish actual native publication. Basis+60000ms is an explicit modeled publication assumption, and daily trade-close basis is not instantaneous executable basis. Actual downstream decisions must use and journal their actual clocks: nominal schedule probes show23 stale funding results and432 basis current-date mismatches, not universal feature coverage or execution evidence. Funding gaps remain exact rather than repaired; missing feature inputs must preserve registered new-risk blocks and safety exits.

The reader validates source hash structure and registered raw identity; it does not authenticate arbitrary supplied artifacts merely because their metadata and recomputed content hash agree. Review approval binds the verified retained artifact above. Downstream immutable consumers should pin its reviewed file SHA as documented, alongside spec/source identities. Builder/source verification and the controller's raw reconstruction establish this artifact's provenance; source hashes are not signatures.

I reused the authorized prior reconstruction and inspected the byte-verifying builder/report/receipts, without rehashing all market ZIPs or running a second full reconstruction. No financial mechanism execution, actual calibration, financial adoption or native qualification was tested by Task 2, and none is claimed. These are subsequent producer tasks, not missing Task 2 work. No cosmetic suggestions or gate changes are requested.
