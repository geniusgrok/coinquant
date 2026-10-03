# Task 4 independent review

SPEC: **FAIL — T4-R1 and T4-R2 require correction.**

QUALITY: **REQUEST_CHANGES — T4-R1 and T4-R2 are blocking; T4-R3 is nonblocking robustness feedback.**

Review scope: BASE `25cd5d0349bef669ac14824435f741dedac6ec82` through HEAD `fa77a6e51aafd68ebcd99236ce9712d7085381ed`. Implementation-report SHA-256 `7bfedc91c1b965442fbd7f1d5ca176b89d76e6ffb691a48d20159fa8060b5866`; root full review package SHA-256 `94aada33e50e7154d8f754d859d93aa5f5817c177fe9b33c82d4cbd7355d2389`. Both independently checked. Read Task4 brief including rulings, review brief, AGENTS, frozen spec/protocol, implementation, relevant original call paths, tests and raw receipts. Applied code-review-skill. Current working-tree documentation changes are parent-owned and excluded from this immutable source review.

## Findings

### T4-R1 — P1 / blocking: verified ZIP receipt can accompany different consumed binary tape

**Evidence E-R1:** `research/edge_prints.py:24–28,60–68`, invoking unchanged `research/session_market.py:360–375`. The helper checks that the sibling binary directory is neither a symlink nor inside the vault, but does not establish ownership or reject a preexisting unowned binary directory. The original loader then trusts a binary filename containing the ZIP digest; it does not verify that its packed rows were derived from that ZIP. Comparing `digest(target)` with `self.loaded[name]` checks the ZIP against another ZIP hash, not the packed rows actually consumed.

Independent temporary-fixture probe: create a valid ZIP containing price **7000.0** and its CHECKSUM using `PrintTests.archive`; before constructing `VerifiedPrints(tmp/'scratch', vault)`, create `tmp/'scratch-cache'/f'{zip.name}.{digest(zip)}.bin'` containing these signed-64-bit arrays in original binary format: count `[1]`, times `[1577836800000]`, IDs `[1]`, prices `[99900000000]`, quantities `[100000000]`. `_load(1577836800000)` accepts it and returns price **999.0**, while its receipt and `tape.loaded` report the valid ZIP hash. The task cache root did not exist when this foreign binary was installed. No original vault or shared cache was touched.

This violates the required isolated, task-owned binary cache and the claim that verified physical retrieval preserves matcher observations. It also exposes preexisting unknown files to original cache eviction. A stale, corrupt or unrelated derived binary can silently change economic execution without changing emitted source-input hashes.

**Fix F-R1:** Establish exclusive task ownership of the sibling binary cache before invoking the inherited loader; reject unknown existing directories/files without deleting them. For supported cache reuse, retain and validate provenance/integrity tying derived bytes to the verified ZIP, or regenerate only within a proven task-owned cache. Keep original vault bytes and unknown files untouched. Add the mismatched packed-price probe and an unknown-directory rejection/immutability assertion; checking only receipt hash equality is insufficient.

### T4-R2 — P2 / blocking: restore accepts an extension whose session stamp was never an actual registered session

**Evidence E-R2:** `research/edge_perp.py:211–228,247–255,325–332`. Restore checks the decision against the event's own `session_ms .. session_ms+300000`, but does not check that the asserted session belongs to the source-bound actual starts or an independently recorded session. The binding stores the actual-starts digest, yet that digest is never used to validate the event's session. Pre-recovery validation consequently accepts mismatched session evidence.

Independent probe used the real pinned FeatureBook, the actual frozen starts digest `d2cfa986b52fdf3c835c254469d3c23b4ab164b611ba42ff7fb61ebd4a2508ad`, and a causal model advanced from ORIGIN with a primary trigger six days before the first actual start. A legitimate extension at `1577836801000` in actual session `1577836800000` restored successfully. Changing only the event's `session_ms` to **1577836800999**, recomputing the checkpoint's normal integrity checksum, and restoring was also accepted. That new session stamp is absent from the frozen schedule. The existing test changes session by a whole day, which only tests interval arithmetic and misses this internally consistent mismatch.

The checksum is an integrity check, not a signature; semantic tampering validation with a recomputed checksum is already the task's established test model. This finding concerns the expressly required rejection of mismatched/out-of-session extension evidence before recovery, not an assertion that the normal producer fabricates events.

**Fix F-R2:** Bind extension provenance to the actual eligible session start and deadline, and check that session against the already source-bound actual schedule (including the registered offset), or equivalent independently retained actual-session evidence, in the pure pre-recovery validator. Do not introduce adapter calls or waits. Add a rejection-before-recovery spy for a changed session stamp that still contains the decision, alongside acceptance for valid original and offset sessions.

### T4-R3 — P3 / nonblocking: decision preparation can write a checkpoint that its own restore rejects after a bar boundary

**Evidence E-R3:** `research/edge_perp.py:145–175` lacks the causal-bar window check enforced by restore at line 218. With `EdgeTests.aged()` under cost-horizon, call `prepare_decision(engine_at(model.last+BAR+1000), snapshot)` using a legal synthetic session and unchanged strong history. It persists an extension; immediate `EdgeCampaign.restore(model.checkpoint())` raises `Blocked('invalid edge checkpoint')`. Observed `bar_ms=1576180800000`, decision `1576195201000`.

**Scope qualification:** independently inspected all 795 frozen starts: none of their unshifted 300-second sessions crosses a four-hour boundary; non-boundary starts are at least one hour away. A minus-60-second run can straddle a boundary, but the frozen protocol registers Coin offset diagnostics for incumbent, which has no extension. The CLI additionally permits a fixed cost-horizon base offset; that broader supported invocation could expose this defect. This probe does not establish a failure in the frozen required financial matrix and does not independently block Task4 acceptance.

**Fix F-R3:** Apply the same causal current-bar precondition before persisting an extension, leaving the original hold/protection unchanged until a normal later decision has current history. A small round-trip boundary test is sufficient; no extra reads or broad redesign are needed.

## Independently verified evidence and accepted implementation aspects

Machine-readable independent checks: `/workspace/btc-alpha-beta-improve/task-artifacts/task-4-review-independent-checks.json`.

- Rehashed and decompressed all four smoke artifacts against the implementation manifest: earlier 4+1 accounts and final 16+4 accounts; all hashes match.
- Compared every original incumbent row field for all four final scenarios, excluding only the explicitly named `opportunity_ledger`: exact equality, with no archive, clock, status or protection normalization.
- Inspected all 20 final rows directly: exactly one session, audit passed, failure null, cleanup verified, no unresolved execution, incomplete and CAGR null. Actual consumed print SHA map equals the restore receipts. These clean empty-cache receipts do not exercise R1.
- Original alpha_perp, complete_perp, rolling_prints, edge_features, edge spec/protocol and production `coinquant` sources have no BASE-to-HEAD diff. Shared finite session and Lifecycle still own accounting, writes, protection, committed topups and terminal handling.
- Source review supports exact 20-close mean, six-interval momentum, immutable trigger ATR/close and decision mark, strict crowding three-way conjunction, missing-feature behavior, no shorts, original macro sizing scope, multiplicative combo reductions and scale cutoff. Original exits retain priority; cost exit requires owned-long hold and legal actual decision. Extension writes are confined to decision preparation, not historical updates; original stop/take geometry remains intact.
- Durable account binding and checkpoint restore occur before Lifecycle initialization/settle/recovery/cleanup. Hook restoration uses ExitStack. Profile schema and project/candidate/spec/cutoff/scale validation are fail-closed, and committed topup target comes from the unchanged Lifecycle state. R2 narrows the remaining defect in extension provenance.
- Actual decision preinputs and after-return values have distinct provenance; actual trade timestamps and extraction timestamps are separate. Unknown client links remain unknown. No new adapter reads or waits found in instrumentation.
- Reviewed the retained logs showing 99 affected tests and the later 21 edge tests passed. Did not rerun unchanged suites. Existing tests meaningfully cover real Lifecycle entry/topup/exit/protection, baseline equality and recovery ordering, but miss R1/R2. Only small isolated in-memory/temporary-cache probes ran in the reserved serial lane; no native access, financial producer, source edit, HOME/UID change or lock bypass occurred.

## Requirements deliberately not established in Task4

Full 795-session all-six baseline equality, complete stress outcomes, deterministic trained-profile/raw-artifact reconstruction, actual calibrated accounts, eligible combo membership, capital/start diagnostics, adoption and financial targets remain later tasks. The runner validates the declared raw SHA syntax; the independent assessor must verify its contents and training derivation. The one-session smoke does not establish nontrivial financial benefit. Native execution and actual account-days remain unverified/zero. The implementation's full-vault unchanged report was inspected; this review did not redundantly rehash all 14 GB. No new financial or native qualification claim is made.
