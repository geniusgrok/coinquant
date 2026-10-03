# Task6a forward shadow ledger independent review

SPEC: **FAIL**.

QUALITY: **CHANGES REQUIRED**.

Four material findings, T6-F1 through T6-F4, require fixes before the actual source freeze/final export/initialization. No Critical finding or native action is asserted. The final financial measurement, actual independent proof/export and real empty-diary initialization are later root work, not missing deliverables in this code task.

## Scope and immutable evidence

Reviewed the full four-commit additions against the authoritative task-6-forward-brief.md and task-6-forward-review-brief.md, both AGENTS, edge spec/protocol contracts, current pure/runtime ownership and sizing call paths, the final Task5 proof verifier/schema and scoped approval, and retained Task6 validation receipts. The modules differ only in KIND/PACKAGE/INTERVAL, and the tests are byte-identical; reviewed shared implementation once and both runtime-specific seams.

- Spot BASE `083b5c1` through HEAD `953caac5b244f10885e7a70b8fdb6f6e62edcde0`; complete package SHA `a8f28fd0b9a8508a47f3eccdd5ede4682f7dbcfb97df12767aeebe603d629170`.
- Coin BASE `3c697e1` through HEAD `fc9b9d5230b698fd94ca95dce3092c4caf1b09ee`; complete package SHA `399d8bd138584f3cc191aeadc53692650171232521a82229cda92ef6abf0aa58`.
- Implementation report SHA `b45f873ff2ed019bb16a6b589e303a4de5cb7d0ef1f5e03a6470053d0366286c`.
- Spot module SHA `94291ba1ec95759c449c7865206edd00aa3b255b2e44c8ac55952285c0dac523`; Coin module SHA `96d35a3032d10bc3a5329fcf1287cfce159713bbbe0f8c760cc781f824f8731b`; shared test SHA `5401fa653018be2394de5305bf176f10023674ce51da422a7d3448b52e3e929a`.

HEADs and source were preserved. Both worktrees contain only root's pre-existing PROJECT_STATE.md modification. No commits, source edits, subagents, native/private requests, credentials, real accounts/orders, full producer runs, HOME/UID changes or account-lock operations occurred. Root reported the Coin lane idle. Coin's single isolated pure probe ran after Spot probes, serially.

Retained exact-commit evidence reports Spot 50 tests OK (3 skipped), Coin 27 OK (1 skipped), plus synthetic CLI audit/source receipts in task-6-final3-smoke-summary.json. These unchanged suites were not rerun. The independent probes below expose uncovered behavior; passing existing tests do not resolve it.

## Required findings

### T6-F1 — High / P1: prior unresolved protection does not prevent later exact Spot passive fills

**Evidence:** spotquant/research/edge_forward.py:689–730, especially 696–703, and 934–944. `passive_fills()` ignores existing `state['unresolved']` and uses the immediately previous event's trade anchor. `apply_observation()` invokes and applies those fills before its unresolved gating. The ordinary decision path's guard at 797–798 cannot undo them.

**Trigger and impact:** own BTC, append an observation without a complete retained protection path, then append a later contiguous print slice starting after the new anchor. The missing earlier slice remains unresolved, so it cannot establish that the position survived until the later print. Nevertheless the adapter books an exact sale time/price, removes ownership and realizes cash. Conditional-equity labeling and a sticky warning do not make that specific fill causally established.

**Independent result:** the retained synthetic probe first records `incomplete_public_protection_path` with BTC `12.71449`. A later one-print contiguous slice at public price80 then books three passive sales at `79.9120`, time `1582070409880`, leaving BTC0. `audit(result)` returns True while the earlier unresolved cause remains present. This demonstrates that algebra/replay acceptance is not independent validation of the disputed survival assumption.

**Required action:** prevent exact passive money/ownership mutations while any earlier exposure interval remains unresolved. If recovery is supported, require evidence covering the entire unresolved span from the last proven exposure anchor and reconcile its earliest applicable trigger; a later local slice must not reset that obligation. Add a regression spanning at least three observations and require no exact later fill after unresolved history. Keep bounded/conditional valuation explicit.

### T6-F2 — High / P1: Coin macro sizing omits the canonical 3% equity-to-stop budget

**Evidence:** coinquant/research/edge_forward.py:879–898 calls `entry_fraction()` and `funded_target()` without a macro-specific `target_quantity`. The current canonical call path in coinquant/native_preview.py:103–112 sets `MACRO_STOP_BUDGET=.03`, computes `min(capital*fraction/max(price,mark), capital*.03/(price-stop))`, and passes that target to the same pure funded-target helper. Margin/liquidation preflight is an additional constraint; it does not implement the macro loss budget.

**Trigger and impact:** a fresh eligible DFII10 macro campaign can model a position much larger than the accepted incumbent permits. Default macro risk3.6 and scale1 do not preserve the rule if its loss cap is absent. This is a strategy/risk divergence even though all entries are paper entries and correctly fee-funded.

**Independent result:** a pure post-bootstrap macro sizing probe with initial wallet `1427.142857142857142857142858`, executable modeled entry `112.133211`, stop99.9 and negative macro identity opens `56.55910` BTC. Entry-to-stop loss is `691.89940427010`; the current canonical 3% budget is `42.81428571428571428571428574` — **16.16048 times the budget**. No network/native account was constructed. This probe isolates the decision/sizing seam; its DFII10 row and second-event marker are synthetic and are not a complete provenance/audit fixture.

**Required action:** share or reproduce the current canonical pure macro target cap before funded sizing, with the same entry-capital and executable-price geometry. Retain requested/committed target separately from realized accepted quantity and any applicable stop budget. Currently `committed_target['quantity']` stores the accepted `account.q` (56.55910 in the probe), while the sizing result's requested target is80.5944658604; those are different facts. Cover primary versus macro entry and cap-binding cases. Do not obtain private native preflight data to fix this public-only ledger.

### T6-F3 — Important / P2: Spot ownership peak incorporates a possibly pre-fill daily high

**Evidence:** spotquant/research/edge_forward.py:562–567 seeds `Model.position_peak` from owned state, feeds each full completed daily high to `Model.update()`, then copies the resulting peak back into ownership. `Model.update()` unconditionally maximizes position_peak with that high. The actual ownership path in spotquant/follow.py:28–31 and 60–63 includes a daily high only for a bar opening after first_ms or an entry within its first minute. The runtime session obtains owned peaks from that follow state.

**Trigger and impact:** enter more than one minute after the daily open, then observe that entry day's completed bar. Its high may precede the actual modeled entry. Importing it as an owned peak tightens the ATR stop or forces a through-mark exit using a price the position never experienced. A subsequent complete post-entry print path does not establish when the whole-day OHLC high occurred.

**Independent result:** entry at day offset130000ms has owned peak `112.133211`; canonical `_high_counts(entry_day, first_ms)` is False. Advancing the forward adapter with entry-day high200 changes owned peak to200. This is a direct causal difference from the bound current runtime.

**Required action:** preserve the canonical fill-time-aware owned peak/follow rules separately from causal indicator warmup. Use exact post-entry path evidence if explicitly supported; otherwise exclude the ambiguous entry-day high as the current runtime does. Add a mid-day entry/pre-entry wick regression that checks the subsequent decision/stop as well as checkpoint ownership.

### T6-F4 — High / P1: a valid Spot ordinary exit creates an unrestorable checkpoint

**Evidence:** spotquant/research/edge_forward.py:839–844 calls `model.note_exit()` after a full modeled sale and immediately persists that checkpoint. `note_exit()` sets `need_reset=True`; the current Model.restore() at spotquant/model.py:425–427 rejects `need_reset=True` when the completed model is bearish. `observe()` then calls audit at edge_forward.py:1008, before replacement.

**Trigger and impact:** a valid ordinary SMA exit with a complete protection path and no stop trigger is modeled, but the proposed new state cannot restore/audit. Every identical retry fails before append; the original diary remains intact and retains the owned position. This prevents a normal safety/strategy exit from being recorded, rather than merely changing a descriptive field.

**Independent result:** retain broad historical ATR so all three allocated stops are78.49; enter at112.133211; supply the next completed close100 and a complete non-triggering print slice at100. The transition has `unresolved=[]` and one ordinary sell of12.71449 BTC. `audit(result)` raises `Blocked: model checkpoint does not match this origin`. The retained reproducer constructs valid causal fixture bars and an isolated deterministic transition; it does not bypass the sale decision or Model.restore.

**Required action:** represent actual exit ownership and same-interval/fresh-cross consumption using a checkpoint-valid transition, preserving canonical cold-start and no-reentry semantics. Do not relax Model.restore's shared invariant merely to admit the incompatible forward state. Verify an ordinary bearish full exit through append/audit/reload, plus partial ownership and a subsequent genuine fresh-cross decision. Check the analogous passive-exit checkpoint mutation for the same invariant.

## Other requirement assessments and declared limitations

**Final source/proof binding:** structurally satisfactory within the documented external-hash trust model. The Spot exporter calls the final full `verify_financial_review()` and `review_expectations()`, freezes original final/preliminary/proof/category bytes and typed expectations, and the standalone Coin reader checks external export/review anchors, exact six-category/record coverage, raw hashes, inventory equality, local contracts and archive source equivalence. No real final proof exists yet and none was represented by these tests. The independently approved export SHA is essential: frozen expected records are not independently derived by Coin, and checksums are not signatures.

**Current source versus measured HEAD:** fixed protected classes bind runtime package, research executable/data/protocol files, root executable/configuration files and .github content plus modes. Recorded, canonical and current identities stay separate and are archive-proved. Inert evidence metadata and ordinary Markdown changes may be equivalent; actual protected changes reject. Current dirty PROJECT_STATE files mean real source-bound init is unavailable until normal integration produces clean committed source, as intended. Historical commits must remain available. There is no caller-configured protected-path exclusion.

**Observation boundaries and monetary integrity:** the public CLI obtains wall-clock receipt/decision times itself, retains raw bytes, validates endpoint/symbol/interval and parsed schemas, checks latest completed inclusive-close+1 intervals and explicit gaps, and excludes warmup from decisions/fills. Decimal algebra independently reconstructs wallet/BTC/fees/funding/equity before replaying shared transitions. Exclusive creation, nonblocking local file lock and durable atomic append are present; source/export/public inputs are rechecked before replacement. `audit` correctly labels its scope as raw reconstruction and explicitly disclaims source authorization. The uncovered causal/state bugs show the limits of deterministic replay of the same transition logic.

**Coin mark-trigger uncertainty:** accepted as a conservative, disclosed implementation limitation for this task. Without a complete reviewed mark path, every later observation after a Coin entry becomes unresolved and further modeled execution is blocked. The brief explicitly permits unresolved protective exposure and suppressed performance qualification; no exact continuous trajectory is invented. Consequently this is not yet a usable multi-campaign Coin forward-performance record. The limitation does not excuse F2 or change the strategy cap on the first entry.

**Coin held target/topups:** current native Lifecycle.top_up() is restricted to the entry's own manual session and its original requested target. The forward interface permits only one new event per completed4h interval, so absence of later-session topups is not independently a reason to extend an expired opportunity or create duplicate-interval fills. It must explicitly remain a discrete observation adapter, not full session/Lifecycle equivalence. Retaining realized quantity under the name committed_target is insufficient to describe the original target; F2's fix must preserve that distinction. No new topup/session engine is prescribed by this review.

**Supported selection:** limiting initialization to current canonical Spot atr-stop/Coin incumbent, components[] and scale1, is consistent with the brief's requirement to wait for a verified bridge when a later selected mechanism has not been integrated. It may leave initialization blocked after future financial selection until a new reviewed adapter/bridge exists; that is an honest limitation, not authorization to run incumbent logic under a different label. Funding/basis feature lags for unsupported future mechanisms are not silently substituted. Signed observed settled Coin funding and causal ALFRED parsing have explicit handling; exact8h coverage remains a declared limitation for changed/jittered future schedules.

All output remains DECLARED_MODELED_FILLS_ONLY, native_cases0, actual_account_days0 and NOT_QUALIFIED. Synthetic proof/clock/HTTP boundaries are not real public observation or financial performance evidence. No live public endpoint schema availability, continuous equity, native execution equivalence, prospective alpha or future return was verified.

## Retained independent probe evidence

Reproducer: `task-artifacts/task-6-forward-review-probe.py`.

Outputs: `task-artifacts/task-6-forward-review-probe-spot.txt` and `task-artifacts/task-6-forward-review-probe-coin.txt`.

Run from `/workspace/btc-alpha-beta-improve` with the exact preserved HEADs:

```sh
PYTHONPATH=/workspace/btc-alpha-beta-improve/spotquant python task-artifacts/task-6-forward-review-probe.py spot
PYTHONPATH=/workspace/btc-alpha-beta-improve/coinquant python task-artifacts/task-6-forward-review-probe.py perp
```

These are the four small probes described above, not unchanged suite reruns. Temporary synthetic fixture files are automatically removed. All persistent review additions are outside the repositories.
