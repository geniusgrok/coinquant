# Task6a forward shadow strategy ledger implementation report

Implementation complete for independent review. No real forward diary, accepted final financial export, public fetch, native account action, credential access, default change, daemon, producer matrix or elapsed observation was created. All retained smoke diaries are explicitly SYNTHETIC; clock/final-export/HTTP boundaries were mocked. Native cases0/actual account-days0/NOT_QUALIFIED.

Binding brief SHA-256: dbb370a1178b22d27506a72a96c478301232f42a813b33329db25b1551bbc6a8

## Exact source and owned scope

Only `research/edge_forward.py` and `tests/test_edge_forward.py` were committed in either repo. Parent PROJECT_STATE.md changes remain untouched. Earlier commits/worktrees/synthetic artifacts are retained; the final3 receipts below supersede earlier smoke receipts for the final implementation identity. No full unchanged suite ran; Coin checks/smokes were strictly sequential.

### spotquant

Final commit: `953caac5b244f10885e7a70b8fdb6f6e62edcde0`
Python source digest: `ed4cd90eceb4e3b346e94849c0b1d8edb46c39b7b51898cc19c33c29324fa634`
Protected byte/mode digest: `764e40c6158b06f64faa938780aa751c0a54239d77522c3e4565f6286a24a889`
Clean detached worktree: `/tmp/task6-complete-spotquant-kiuty5_q`
Full archived source map: `task-6-final3-spotquant.source.json`

Commits in this task:
```text
953caac5b244f10885e7a70b8fdb6f6e62edcde0 Reject forward Coin protection outside observed instrument bounds
58856bbc8e4befef1ef5bb38b3a8e472cad9792c Verify forward source binding before checkpoint restoration
b20ba954c443aad4d04452a7dd0724c5f00d556a Keep inert review packets outside forward execution identity
898c6b2e77ca0e43a49ee400f5596d7acb5080a7 Add source-bound manual forward shadow strategy ledger
```

### coinquant

Final commit: `fc9b9d5230b698fd94ca95dce3092c4caf1b09ee`
Python source digest: `5b35dd010e38594180958da4bbf355341060400c8eebe14d125d706fea06aac5`
Protected byte/mode digest: `0f60e77fae446391f21b67d32db154ee77d5813687f5e3eb90449dc53a0f6183`
Clean detached worktree: `/tmp/task6-complete-coinquant-fruvtp9a`
Full archived source map: `task-6-final3-coinquant.source.json`

Commits in this task:
```text
fc9b9d5230b698fd94ca95dce3092c4caf1b09ee Reject forward Coin protection outside observed instrument bounds
aa946bdbbae9dc597ae1f155a4472da17c4f1e39 Verify forward source binding before checkpoint restoration
13ad4eabd048c4f92015498a25eb12dbd12c7b52 Keep inert review packets outside forward execution identity
6a08602cfb62285e3ed6ceb1fcb1c8640132a96a Add standalone source-bound forward shadow strategy ledger
```

## Fixed protected-source class and metadata HEAD equivalence

`source()` archives the requested full Git commit and verifies current protected worktree bytes against the current committed archive. It rejects a dirty repository. Protected classes are fixed in code, with no caller exclusions: all local runtime package files; all research non-Markdown files and research protocol Markdown; all `.github` execution configuration; and root Python/JSON/TOML/YAML/CFG/INI/shell files or root executable files. Both content hashes and executable modes are bound. Ordinary prose, tests and inert `evidence/`/review packet files are outside the execution classes. This includes every committed runtime/research Python file, local spec/protocol and root configuration. Tests prove that new inert evidence JSON/proof scripts and ordinary research guide prose permit equivalence, while runtime/config/protocol byte changes reject.

Recorded measured-analysis identity, canonical bridge source and current runtime HEAD stay separate. `assert_equivalent()` re-archives the recorded commit, verifies its complete manifest/digests, and requires the current protected map AND modes to equal it exactly. No measured result is relabeled to a metadata HEAD. Old commits must remain locally available; a shallow checkout without a needed historical bridge commit fails closed. Standalone CI tests create their own Git fixture and need no sibling or old evidence.

## Final reviewed binding/export interface

No real Task5 final proof exists yet. Nothing hardcodes e910189 as a future measured identity. The Spot-only `export` command lazily imports the currently reviewed local `edge_assessment`, requires final/complete_reviewed/no pending/no blocking, reruns its full `verify_financial_review()` and `review_expectations()`, and freezes the complete raw final analysis, preliminary report, original independent proof, six raw category artifacts, exact typed expected records, actual exporter source, and canonical bridge review bytes. An independently approved exact raw export SHA and independent financial-review raw SHA are required by init/append. These are explicit review trust anchors, not cryptographic signatures.

Coin imports no sibling evaluator/runtime. Its standalone reader verifies the two external hash anchors, all embedded raw hashes, exact six-category coverage, each typed record/unique ID/raw binding against the frozen evaluator derivation, preliminary/final inventory equality and its recomputed checksum, local source archives, local spec/protocol bytes, and retained canonical bridge attestation. A claimed PASS or nonempty artifact alone is insufficient. The frozen expected-record derivation is trusted only through the independently reviewed export hash; Coin does not reimplement the entire financial evaluator.

`bridges.json` contains project keys `spot` and `perp`. Each project object must contain:
```json
{
  "candidate": "atr-stop OR incumbent",
  "adapter": "canonical-incumbent-v1",
  "components": [],
  "scale": "1",
  "source": "EXACT source() OBJECT",
  "measured_source": "EXACT final.accounts[account_id].source",
  "account_id": "EXACT selected unscaled base account key",
  "raw_sha256": "EXACT final account original raw hash",
  "canonical_review_sha256": "INDEPENDENT UPSTREAM CANONICAL REVIEW HASH",
  "original_accepted_result_sha256": [
    "ORIGINAL ACCEPTED RESULT RAW HASHES"
  ],
  "canonical_review": {
    "path": "canonical-project.json",
    "sha256": "EXACT RAW CANONICAL ATTESTATION HASH"
  }
}
```

The retained `canonical_review.path` JSON must be `{format:"btc-edge-canonical-forward-bridge-v1",status:"independently_reviewed",project:"spot"|"perp",bridge:...}` where `bridge` exactly equals the project bridge object excluding its `canonical_review` pointer. The final reviewed export approves those exact canonical relationships and original identities. Export verifies project source against the actual clean local repo and measurement fields against the final analysis. The reader independently checks the raw attestation and exact bridge identity.

Only current canonical Spot atr-stop and Coin incumbent, components[] and default scale1, can initialize. A later financial selection of a new mechanism fails `selected rule has no verified canonical forward adapter`. Such a selection requires a subsequent reviewed canonical integration plus an explicitly matching adapter, new source bridge and final export; it cannot silently run incumbent logic. Historical edge-features-v1 is never extended. Since current supported incumbents do not consume crowding features, no forward funding/basis selection seam is fabricated for an unsupported newly selected rule.

## CLI and public observation schema

```text
python -m research.edge_forward source [--head FULL_COMMIT]
python -m research.edge_forward acquire --url OFFICIAL_PUBLIC_URL --directory RAW_DIR --out NEW_RECEIPT.json
python -m research.edge_forward export --analysis FINAL.json --review INDEPENDENT_PROOF.json --bridges BRIDGES.json --out NEW_EXPORT.json
python -m research.edge_forward init --diary NEW_DIARY.json --export EXPORT.json --export-sha APPROVED_RAW_SHA --review-sha APPROVED_REVIEW_RAW_SHA --history HISTORY_RECEIPT_ARRAY.json
python -m research.edge_forward observe --diary DIARY.json --export EXPORT.json --export-sha APPROVED_RAW_SHA --review-sha APPROVED_REVIEW_RAW_SHA --url URL [--url URL ...] [--declared-gap]
python -m research.edge_forward audit --diary DIARY.json
```

`audit` deliberately labels `scope=raw_ledger_reconstruction_only` and `source_binding_verified=false`; it validates retained raw inputs, money, proposals and checkpoints but cannot substitute for init/append source validation. Append validates source/export before any checkpoint restore.

Each receipt has category,url,actual request_ms,actual receipt_ms,sha256 and absolute retained raw path. `acquire` stamps wall clocks internally; `observe` acquires its own URLs and accepts no caller timestamps, prices or receipts. Initialization accepts only historical warmup receipts (from fixed runtime origin, contiguous through latest completed interval), then acquires actual initial FX. It creates CNY10000/BTC0/no fills at actual initialization time. History never creates forward cashflows or decisions.

Official allowlist: Spot api.binance.com/api/v3 klines(1d), depth, aggTrades and exchangeInfo; Coin fapi.binance.com/fapi/v1 klines(4h), depth, aggTrades, exchangeInfo, premiumIndex and fundingRate. Requests bind BTCUSDT, instrument type, quote/margin assets, parsed filters and official field layouts. Completed kline boundary is inclusive closeTime+1. Current running bars are ignored; future/duplicate/conflicting/missing completed history rejects. Only latest completed interval at all actual receipts/decision may append, and its end must be strictly later than initialization and last decision. Gaps require explicit declaration and all intervening causal warmup bars; they never create skipped decisions.

Coin ALFRED DFII10 acquisition retains the form bytes, actual selected-vintage POST body and returned ZIP in task-owned storage. Reader validates official columns, observed dates, declared request-time available vintages, runtime 48-hour availability rule, finite values and prior20/current macro fields. Relevant missing DFII10 blocks new risk. No HOME cache is used. FX reads official FRED DEXCHUS CSV, uses the most recent strictly prior UTC date (maximum7days old), USDT=USD declared parity and .1% conversion each way. Future contemporaneous receipts, requests older than60seconds at decision/recording and stale trades/marks reject.

Raw files are retained exclusively with SHA and URL/request/receipt metadata and rehashed on replay and before mutation. Existing output files are never overwritten during initialization/acquisition. Append uses a local nonblocking exclusive flock and fsync+atomic replacement; malformed/unknown/binding/source/input failures leave original diary bytes unchanged. Source/public hashes are checked around the operation.

## Runtime adapter, accounting and protection behavior

Spot restores actual Model checkpoints, advances completed OHLC, calls canonical preview.decision (ATR consensus), and preserves sleeve ownership/entry/peaks/allocated nonloosening modeled stop floors. It does not top up held sleeves or rebalance. SELL priority and original whole-account capital ceiling remain. Modeled market fills use observed executable-side depth, minimum/step checks, conservative deepest consumed price plus .0011 adverse reserve, .001 fee and sufficient fee cash. Fills journal proposal/opportunity interval/sleeves/quantity/price/fee; stops are explicitly modeled rather than claimed native.

Coin restores actual Campaign and Account checkpoints, uses linear_preview.preview and linear_sizing.funded_target, keeps original primary7.5/macro3.6/defaultscale1/no shorts, funding reserve, margin/liquidation/protection geometry and observed price/quantity bounds. A filled campaign fixes the committed target/opportunity/creation/expiry; held target is not topped up or retroactively extended. Modeled fills use .00075 fee and .0011 adverse reserve. Only observed settled funding after initialization and during existing exposure posts cashflow; signed cost=q*mark*rate means negative funding credits a long. Missing expected settlement coverage is explicit and never coerced to zero.

Every event records request, receipt, decision and recorded-at separately; proposal, simulated acceptance/rejection, full money entries, wallet/cash, BTC/entry, fees, funding, mark, current prior-date FX, net USDT/CNY PnL, skipped intervals, uncertainty and source identity. Audit independently reconstructs money/position/funding/FX, then replays actual pure decisions and checkpoint ownership/protection from retained raw history. Event/receipt ordering, raw bytes, checkpoint hashes, reconstructed ownership and deterministic proposal/fill mismatch reject.

Passive Spot protection can be modeled only when retained contiguous aggregate-trade IDs cover the prior anchor through the current latest trade and the triggering public print size can cover the allocated modeled sale. Exact print time/price/source/stop are retained and adverse cost applied; this remains a declared paper-print fill assumption. OHLC alone never selects an exact stop/take order/price. Incomplete protection path, ambiguous OHLC touch, mark-through protection or missing funding creates explicit sticky unresolved state and conditional marked equity. Coin trade prints cannot prove its mark-trigger path, so held Coin exposure becomes unresolved at a later manual observation without a reviewed complete mark-path adapter; no precise future passive Coin fill is invented. Missing executable book permits preview-only output and blocks fills.

No continuous equity curve, native execution equivalence, prospective alpha, qualification or return guarantee is asserted. native_cases0/actual_account_days0/NOT_QUALIFIED stay fixed, including initialized zero-event diaries.

## Final affected validation (exact committed worktrees)

### spotquant

```text
$ python -m unittest tests.test_edge_forward tests.test_preview tests.test_model
...s.s....s.......................................
----------------------------------------------------------------------
Ran 50 tests in 1.063s

OK (skipped=3)
```

CLI synthetic money-ledger audit:
```text
$ python -m research.edge_forward audit --diary /workspace/btc-alpha-beta-improve/task-artifacts/spotquant-task6-final3-SYNTHETIC/SYNTHETIC-diary.json
{"audit": true, "events": 2, "qualification": "NOT_QUALIFIED", "scope": "raw_ledger_reconstruction_only", "source_binding_verified": false}
```

Synthetic diary SHA: `0ae8326d0d640eb6a19447a7ab2d5e83081f443885d3afe79c91d6b117239e5f`. Fixture and all public raw bytes retained in `spotquant-task6-final3-SYNTHETIC/`. The fixture exercises real local runtime decisions/accounting but mocks final-proof trust, wall clock and HTTP acquisition; it is not a real forward observation.

### coinquant

```text
$ python -m unittest tests.test_edge_forward tests.test_campaign
....s......................
----------------------------------------------------------------------
Ran 27 tests in 0.304s

OK (skipped=1)
```

CLI synthetic money-ledger audit:
```text
$ python -m research.edge_forward audit --diary /workspace/btc-alpha-beta-improve/task-artifacts/coinquant-task6-final3-SYNTHETIC/SYNTHETIC-diary.json
{"audit": true, "events": 1, "qualification": "NOT_QUALIFIED", "scope": "raw_ledger_reconstruction_only", "source_binding_verified": false}
```

Synthetic diary SHA: `5f5a2a070346c179ea90e067c654fde6b2bafb338c690d5a10638ff75411d10e`. Fixture and all public raw bytes retained in `coinquant-task6-final3-SYNTHETIC/`. The fixture exercises real local runtime decisions/accounting but mocks final-proof trust, wall clock and HTTP acquisition; it is not a real forward observation.

Tests cover final export/source rejection and metadata equivalence; exact financial category/record coverage and MDD precision; strict duplicate/nonfinite JSON; raw provenance/tamper; actual acquisition stamps; cold start/exclusive initialization; duplicate/backfill/gap/latest interval; missing/stale book; actual proposal/fill/fee/PnL reconstruction; minimum/rounding/depth/no topups; checkpoint corruption; source/atomic rejection immutability; funding sign/no retro cashflows/missing coverage; ALFRED causality; ambiguous protective paths; exact Spot paper protective path; and Coin unplaceable protection price bounds.

## Self-review and limitations for independent review

- Source-bound real initialization intentionally remains unavailable until root supplies final independently reviewed financial export and canonical bridge after the full source freeze/measurement. Tests do not stand in for that proof.
- No public endpoint was exercised over the network in this task. Official schema adapters fail closed if an endpoint returns redirects, unexpected HTML/archive shape, unavailable history or stale data. ALFRED cookies/POST remain public-only and task-owned.
- Coin complete historical mark-trigger paths are not implemented. Conservative unresolved exposure suppresses subsequent modeled execution/performance rather than inventing passive fills; the last retained owned quantity and conditional equity are explicit. Spot exact aggregate-print fills still rely on declared paper liquidity/adverse-cost assumptions.
- Funding coverage currently recognizes exact scheduled8hour settlement stamps; a changed/jittered settlement schedule is not silently repaired and may require a reviewed coverage adapter. Current incumbent funding sizing does not reinterpret missing funding features as zero.
- Adapter support deliberately stops at current canonical incumbents. New selected research mechanisms and their lagged funding/basis rules require reviewed canonical adapter integration, not labels/default changes.
- `audit` is a raw ledger/strategy replay check, not a signature or source authorization. Actual mutation paths require the external reviewed hashes and archive-verified binding first. A party able to replace every local file and every external trust anchor is outside this local checksum integrity model.
- Local filesystem locking and atomic rename/fsync are used; no distributed lock or remote storage protocol is claimed. Public raw files acquired before a rejected append can remain as retained orphan observations, but old diary bytes are unchanged.
- The module reuses pure runtime rules/sizing/checkpoints, not full native Lifecycle. No account locks/HOME/credentials/settings/orders/transfers were touched.

Final smoke summary: `task-6-final3-smoke-summary.json`. Earlier smoke/worktree metadata and receipts are retained.

---

# Task6a fix round1 — T6-F1/F2/F3/F4

All four independent findings addressed in one coherent implementation wave. This section supersedes the affected implementation details above; original pre-fix report is retained in `task-6-forward-report-pre-fix1.md` and all original commits/probes/worktrees/synthetic receipts remain available. Independent scoped re-review is still required before source freeze.

Only each repository's `research/edge_forward.py` and `tests/test_edge_forward.py` were amended. Shared runtime/default modules were not changed. Root PROJECT_STATE.md edits were preserved; external controller files were untouched. No real finance/export/diary/public request/native/account/credential/HOME/lock operation occurred. Coin synthetic commands remained sequential.

## Finding-to-fix mapping

**T6-F1 — sticky unresolved survival.** `passive_fills()` now exits without any exact fill or ownership mutation whenever earlier exposure is unresolved. No recovery path is added. A later contiguous local aggregate-print slice cannot restart the proof from the most recent anchor and assume the earlier missing span was survived. The regression creates an entry, records a missing path, then supplies a later contiguous triggering print; balances, fees, funding, owned quantities and installed modeled owners remain unchanged, money[] stays empty and conditional-equity/unresolved status survives audit/reload.

**T6-F2 — canonical macro target and original commitment.** The adapter imports the pure constant `coinquant.native_preview.MACRO_STOP_BUDGET` (.03), uses flat funded sleeve capital and actual declared executable entry versus current mark, computes `min(capital*fraction/max(entry,mark), capital*.03/(entry-stop))` for macro opportunities, and passes that exact target through `funded_target(target_quantity=...)`. Primary sizing continues through the unchanged uncapped helper path. Original requested target, accepted quantity, sizing capital, executable entry, stop/take, actual stop budget and source opportunity/creation/expiry are distinct facts. No later-session topup or extra same-interval event is introduced. The regression separately covers a binding 3% cap, a volatility-limited target with mark above executable entry, unchanged primary quantity with fee/margin funding cap, depth-constrained fill, minimum rejection and commitment facts.

**T6-F3 — fill-time-aware Spot ownership.** The adapter now directly reuses native `follow.advance` for owned peak/repair/adverse/protection state and native `session._view` for a read-only decision view. Market Model checkpoints receive full completed OHLC for indicator/ATR history but no longer persist fill-owned entry/peaks/repair flags. Native follow._high_counts therefore excludes an entry-day high when the fill occurred beyond the first minute, while later bars can advance the owned peak. The mid-day/pre-entry-wick regression checks actual subsequent proposal (hold), owned peak, preserved installed stop, checkpoint/reload and a later eligible owned high. This also keeps repair ownership separate from market checkpoint validation.

**T6-F4 — valid full/partial close transitions.** Full ordinary and passive closures consume the market signal using actual native `Model.note_flat()` on the market-only checkpoint, instead of the unconditional protective `note_exit()` reset. Shared Model.restore invariants are unchanged. A genuine ordinary SMA bearish exit (above the adverse-stop threshold and with a complete non-triggering trade path) now appends, audits and reloads with no owned BTC and a valid bearish checkpoint. A duplicate-interval retry still rejects; one subsequent bullish close stays flat, then the second genuine fresh-cross close can enter. A separate partial depth-limited owner exit retains surviving ownership and validates closed/remaining market checkpoints; a later passive close starting from bearish market state also appends/audits/reloads.

## Independent regression evidence

New regression methods were run against the preserved exact FIX_BASE detached worktrees, without changing them. Expected failures are retained in `task-6-fix1-baseline-regressions-spotquant.txt` (F1/F3/F4/partial) and `task-6-fix1-baseline-regressions-coinquant.txt` (F2). These are new targeted checks, not unchanged full-suite reruns.

The original unchanged independent reproducer `task-6-forward-review-probe.py` was also rerun against the amended source, Spot then Coin. Result files are `task-6-fix1-review-probe-spotquant.txt` and `task-6-fix1-review-probe-coinquant.txt`:
```text
T6-F1: unresolved remains; BTC12.71449 ->12.71449; fills[]; audit True.
T6-F3: entry offset130000ms; native high_counts False; peak112.133211 ->112.133211.
T6-F4: modeled ordinary sale12.71449 BTC; unresolved[]; audit True.
T6-F2: requested3.499840370143678081389611096 BTC; accepted3.49984 BTC;
       entry112.133211; stop99.9; loss-to-stop42.81428118624 USDT;
       canonical 3% budget42.81428571428571428571428574 USDT;
       loss/budget0.9999998942398398398398398392 (pre-fix16.16047991288...).
```

These probes remain synthetic. The Coin macro probe isolates the pure post-bootstrap sizing seam and does not claim a full provenance/audit fixture, real macro receipt or performance result.

## Exact final source / affected tests / clean synthetic CLI smoke

### spotquant

FIX_BASE: `953caac5b244f10885e7a70b8fdb6f6e62edcde0`
Final commit: `75c7d8efb07c98d21f1350d0f6186b48ed48a5a2`
Runtime/research Python digest: `19753a68ebd2623d1541a0b4bc3227c9baefffbc8599b7290871fb7cdd0ae05f`
Protected bytes/modes digest: `b967e8c3b7e15260e114fc7b2007c216e6569a4bff7362a633443eb53ddcaf7d`
Clean retained exact-commit worktree: `/tmp/task6-fix1-spotquant-cbxh9w5f`

- `research/edge_forward.py` SHA-256 `0603b6233a0ab997ae7a5d4f5353fedf54fc1232ff06ff2d3f77fe82c2148d68`
- `tests/test_edge_forward.py` SHA-256 `23ba827c1d755f97f60f7e7d2d4f3447f73b25e2bebdfd6be569fd4935aaa1ce`

Full source manifest: `task-6-fix1-spotquant.source.json`.

```text
$ python -m unittest tests.test_edge_forward tests.test_preview tests.test_model
....s..s.sss..s...s.......................................
----------------------------------------------------------------------
Ran 58 tests in 2.205s

OK (skipped=7)
```

```text
$ python -m research.edge_forward audit --diary /workspace/btc-alpha-beta-improve/task-artifacts/spotquant-task6-fix1-SYNTHETIC/SYNTHETIC-diary.json
{"audit": true, "events": 2, "qualification": "NOT_QUALIFIED", "scope": "raw_ledger_reconstruction_only", "source_binding_verified": false}
```

Synthetic diary SHA-256 `78c43129d431046bd47c4a51a41ce58af6133201aa20293d74a7232ada06dbb2`; retained fixture/raw receipts in `spotquant-task6-fix1-SYNTHETIC/`.

### coinquant

FIX_BASE: `fc9b9d5230b698fd94ca95dce3092c4caf1b09ee`
Final commit: `e9a1117a79f391346be9af85ad3636ea8d438b4d`
Runtime/research Python digest: `c8304fca0bb6426ea7e8a086d7012c028757d0f328089b2a9122e98fbd4889af`
Protected bytes/modes digest: `073148f56888265ae54927866bdd09c53ae1717cc1f49700e7a69497da0beace`
Clean retained exact-commit worktree: `/tmp/task6-fix1-coinquant-b1f3qr6u`

- `research/edge_forward.py` SHA-256 `9d0388f34cbd41733183eeb54c7c713acb360222a48d5ba5299c328dbd7540fd`
- `tests/test_edge_forward.py` SHA-256 `23ba827c1d755f97f60f7e7d2d4f3447f73b25e2bebdfd6be569fd4935aaa1ce`

Full source manifest: `task-6-fix1-coinquant.source.json`.

```text
$ python -m unittest tests.test_edge_forward tests.test_campaign
...s.ss......s.s...................
----------------------------------------------------------------------
Ran 35 tests in 0.315s

OK (skipped=5)
```

```text
$ python -m research.edge_forward audit --diary /workspace/btc-alpha-beta-improve/task-artifacts/coinquant-task6-fix1-SYNTHETIC/SYNTHETIC-diary.json
{"audit": true, "events": 1, "qualification": "NOT_QUALIFIED", "scope": "raw_ledger_reconstruction_only", "source_binding_verified": false}
```

Synthetic diary SHA-256 `98b1102cc0cd0a76525c8a04d363d2a482cf8b8d4b10f0a7519591183430a04e`; retained fixture/raw receipts in `coinquant-task6-fix1-SYNTHETIC/`.

The exact-commit smoke helper is unchanged `task-6-synthetic-smoke.py`. It mocks clock, reviewed-export trust and HTTP acquisition while exercising actual local pure runtime decisions, paper accounting and the CLI raw-ledger audit. Source is captured separately from the actual clean committed archive. There are zero real public observations/account-days/native cases. Summary: `task-6-fix1-smoke-summary.json`.

## Schema/interface notes and preserved limitations

- Spot position objects now also carry native follow fields `entry_open_ms`, `repair`, `repair_peak`, `adverse`, `through` and `protection`. Market Model checkpoints remain the canonical validated market shape and no longer contain owned fill state. This is an explicit source-bound adapter correction; no migration or relabeling of old diaries is offered.
- Coin entry proposals add `sizing` with `requested_quantity`, `accepted_quantity`, `sizing_capital_usdt`, `entry_estimate`, `stop`, `take` and nullable `stop_budget_usdt`. `committed_target.quantity` now denotes the original requested target (matching `requested_quantity`), while `accepted_quantity` separately records the realized initial fill. Commitment also retains original opportunity/created_ms/expires. Minimum-rejected entries retain their proposal target without committing a filled campaign.
- Export/proof/observation/clock/locking/checksum format and strict source gates were not weakened or redefined. Changed source cannot append to an old source binding; all previous synthetic diaries remain paired with their original retained executable commits. No real diary exists to migrate.
- Sticky unresolved exposure has no recovery implementation. Coin mark-trigger paths remain conservatively unresolved between manual observations, so this still is not a qualified multi-campaign forward performance record. No full native Lifecycle/session-topup equivalence is claimed.
- Macro stop budget is the canonical entry-price-to-stop distance cap; fees, adverse execution price assumptions and funding remain separately explicit. Final financial export/independent canonical review/source freeze remain later root work.
- Current supported adapters remain canonical Spot atr-stop/Coin incumbent at scale1; new selected mechanisms still need a reviewed canonical bridge/adapter. Native0/accountdays0/NOT_QUALIFIED remain fixed.

Evidence receipt hashes: `task-6-fix1-evidence-sha256.json`.


# Fix round 2 — ROOT-F5 paired FRED publication and ROOT-F6 deferred warmup

Status: implementer DONE; pending independent scoped review. Original report and fix1 prefix preserved byte-for-byte, SHA-256 `48f018c015eddadc210e7e97c2b1bf00bbcd6fdcb6486dab0091270360697224`. Authoritative amended brief SHA-256 `b554df126187003962f6967ab7999674411fe4cfe7f6b65083d4afd3a5e30565`. F1–F4 remain covered and unchanged in intent. Scope was only each repository's `research/edge_forward.py` and `tests/test_edge_forward.py`; root's dirty PROJECT_STATE.md was preserved. No network, actual financial run/export/diary, account/native operation, shared runtime/default changes, controller change or source freeze was performed. Coin checks and smokes ran serially.

## ROOT-F5 implementation and timing ruling

Default acquisition is now the exact official CSV URL `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXCHUS`. The exact `https://fred.stlouisfed.org/graph/?id=DEXCHUS` endpoint is metadata only. CSV acquisition additionally fetches that page, retaining two distinct actual request/receipt clock pairs, paths and SHA-256 digests. Redirects remain rejected. CSV receipt has a nested `metadata` receipt categorized `fx_metadata`; `payload`, freshness checks, initialization, pre/post append verification and replay audit validate both raw bodies and both source/timing records.

A stdlib HTMLParser extracts the single strict JSON-LD Dataset with alternateName DEXCHUS, timezone-aware dateModified and the official recent-obs table. The latest table date/value must exactly match the latest nonmissing positive CSV value. Publication must be no later than actual metadata receipt or decision, and at most 7*DAY milliseconds old inclusive. Its local publication date must be at/after the latest observation date with a gap <=7 days; publication UTC cannot precede that observation's UTC midnight. Duplicate/conflicting/nonfinite/future observations or missing/malformed publication evidence reject. Valuation still selects the latest observation strictly before the UTC call date, assumes USD=USDT and charges .001 conversion each way. FX output explicitly says `weekly published benchmark; not an executable FX quote`.

The root's retained real HTML and CSV were parsed locally without network. Both report latest `2026-09-25 / 6.7110`; Dataset publication is `2026-09-28T15:16:00-05:00`. HTML SHA-256 `9e58d644559addff0945b011c42f86a8c8db1805e9090aa4b22bc13c1b480853`; CSV SHA-256 `bb24b533a9df099f45ef11f97ba62a010fad703cc7b52cc296363d3bcddc2515`. Receipt `task-6-fix2-root-raw-parser.json` records static parser agreement only. Those separately acquired root preflight receipts are not relabeled as an eligible paired forward observation.

The retained synthetic boundary probe runs unchanged against each clean fix1 and fix2 commit. Fix1 uses the wrong graph endpoint, rejects the Sep25/Sep28/Oct3 pattern as `stale prior-date FX`, and has no deferred initialization interface. Fix2 uses the CSV endpoint, accepts the current publication and exposes the deferred mode. Exact probe/raw/results: `task-6-fix2-boundary-probe.py`, `task-6-fix2-{spotquant,coinquant}-{red,green}.txt` and corresponding `-raw/` directories. Unit regressions additionally exercise publication exactly seven days old versus +1ms, prior-date selection despite current-date publication, future/noTZ/absent/duplicate/wrong-series fields, latest date/value mismatch, observation/publication gaps, nested hash/clock/URL tampering, actual paired fetch with mocked HTTP and atomic init/append rejection.

## ROOT-F6 initialization, transition and reconstruction schema

The public init CLI now requires exactly one of `--history PATH` or `--defer-market-warmup`. Both require unchanged strict approved export/independent proof/canonical adapter/source verification. Exports and returned source bindings carry `initialization_modes`, whose nonempty unique values must be drawn from `history` and `deferred_market_warmup`; the selected mode must be bound. There is no fallback from failed history initialization.

The diary adds `initialization_mode`, boolean `market_ready`, nullable `market_ready_at_ms`, and `market_ready_reason`. Deferred initialization has the actual internal initialization clock, CNY10000 converted using the validated paired FX, zero BTC/fees/funding, no events, empty canonical engine (Coin wallet seeded), null last interval, false readiness, and reason `fresh_public_market_pending`. History is forbidden in this mode. History mode retains full fixed-origin/latest-completed bootstrap and starts ready. Initialization itself now audits the full result before exclusive creation; audit also rejects reversed initialization/record clocks.

First pending observe requires fresh retained contiguous public bars from the canonical fixed origin through the current completed interval. It bootstraps/consumes existing native signals, records one `kind: warmup_only` event with actual request/receipt/decision/record clocks, gap count, raw receipts and current source; `proposal` is null and `simulated`/`money` are empty. Wallet/BTC/fees/funding are identical to initialization. No mark, equity, retrospective decision or performance result is invented. Readiness becomes true at that actual decision time. A later ordinary `kind: decision` requires a genuinely new completed interval after initialization AND warmup time, plus existing fresh input/native-cross rules. Coin's first actual decision still bootstraps macro selection; warmup-only events do not consume that separate source boundary.

Audit derives initial engine/readiness from mode and original FX/history bytes, derives the warmup transition by replaying raw bars and canonical bootstrap, reconstructs chronology and money independently, and compares the full event and checkpoint. Sealed readiness booleans, removed warmup events, forged money/proposal/initial engine or changed raw bytes cannot bypass this. Regressions cover cash-only pending init, history mixing/export-mode rejection, both native cold starts, same-interval rejection, subsequent native fresh-cross entry, delayed first warmup with an explicit three-interval gap/no past trades, raw/source/clock failures and pre-replace atomic failure.

Formats retain source-bound v1 identifiers but require the new fields; no migration or reuse of old bindings/diaries is offered. Earlier synthetic fixtures must be replayed only on their retained earlier executable commits. The original 68-account financial registration, historical contracts, candidates and gate thresholds were not changed.

## Exact committed source, checks and synthetic CLI evidence

Affected checks ran after final changes, before committing the exact tested owned paths. No unchanged full suite ran. Each retained detached worktree is clean and fixed at the final commit. The smoke fixture mocks clock, final-reviewed export trust and HTTP acquisition, and exercises the actual local canonical pure adapter and raw-ledger audit. It is NOT an approved final finance export or real diary. Each repo retains normal modeled decisions, zero-event pending initialization and the warmup-only state, including every nested raw metadata receipt. All six public CLI audits return audit true, qualification NOT_QUALIFIED, scope raw_ledger_reconstruction_only and source_binding_verified false. Native cases, actual observations and actual account-days remain zero.

### spotquant

FIX_BASE `75c7d8efb07c98d21f1350d0f6186b48ed48a5a2`; final HEAD `7faa66beeafbfb803bb72a36b926ee5a7a08d49d`.
Runtime/research Python digest `56aa7fee335e5c51d5882490a1b28891569d82ffafc518c8be9386aba471a4d2`.
Protected bytes/modes digest `3823e451edc8f060586eda91f5ebb4d28ced548c3a67b6005460eebca9365298`.
Retained clean exact-commit worktree `/tmp/task6-fix2-spotquant-_g6dy_sp`.

- research/edge_forward.py SHA-256 `f22b2f3999d290e8279f6cc20ecedd63982b65984c78704e024fb5d9f149fba2`
- tests/test_edge_forward.py SHA-256 `403dd0fc78db0287536d241844397c48b82a83b15e8c10b624443107d2c2115a`

Full source manifest: `task-6-fix2-spotquant.source.json`.

```text
$ cd /workspace/btc-alpha-beta-improve/spotquant
$ python -m unittest tests.test_edge_forward tests.test_preview tests.test_model
....s......s......sss...s...s.......................................
----------------------------------------------------------------------
Ran 68 tests in 3.045s

OK (skipped=7)
```

Exact-commit smoke commands (cwd `/tmp/task6-fix2-spotquant-_g6dy_sp`):

```text
python -m research.edge_forward source
python /workspace/btc-alpha-beta-improve/task-artifacts/task-6-fix2-synthetic-smoke.py /workspace/btc-alpha-beta-improve/task-artifacts/spotquant-task6-fix2-SYNTHETIC
python -m research.edge_forward init --help
```

normal diary SHA-256 `a5bd921b2278c7274f9b446103fabf6f6cf86d067f4833818c7ab57eabf009ae`; events 2; market_ready true.

```text
$ python -m research.edge_forward audit --diary /workspace/btc-alpha-beta-improve/task-artifacts/spotquant-task6-fix2-SYNTHETIC/normal/SYNTHETIC-diary.json
{"audit": true, "events": 2, "qualification": "NOT_QUALIFIED", "scope": "raw_ledger_reconstruction_only", "source_binding_verified": false}
```

pending diary SHA-256 `84c7efa9805be5a2b995b3d678ac51f17d4aac7ae1d9d83c544e1e726d13d47f`; events 0; market_ready false.

```text
$ python -m research.edge_forward audit --diary /workspace/btc-alpha-beta-improve/task-artifacts/spotquant-task6-fix2-SYNTHETIC/pending/SYNTHETIC-diary.json
{"audit": true, "events": 0, "qualification": "NOT_QUALIFIED", "scope": "raw_ledger_reconstruction_only", "source_binding_verified": false}
```

warmup diary SHA-256 `3af9866e778f07d418c81e5c0579e6cadea83b93476d70013ecc81f8b6cf1431`; events 1; market_ready true.

```text
$ python -m research.edge_forward audit --diary /workspace/btc-alpha-beta-improve/task-artifacts/spotquant-task6-fix2-SYNTHETIC/warmup/SYNTHETIC-diary.json
{"audit": true, "events": 1, "qualification": "NOT_QUALIFIED", "scope": "raw_ledger_reconstruction_only", "source_binding_verified": false}
```

### coinquant

FIX_BASE `e9a1117a79f391346be9af85ad3636ea8d438b4d`; final HEAD `f4e82fb63742318846e51d189d03587ccc84af79`.
Runtime/research Python digest `a75c0b7e132fe8a7c12a7b76b0876858a942b2fcb9648a33dbc67b9fa32f8604`.
Protected bytes/modes digest `2fad6792d777aaedc11c93b04e7d1b99a39c0687f383db3ff63b510656525b76`.
Retained clean exact-commit worktree `/tmp/task6-fix2-coinquant-711wkgp7`.

- research/edge_forward.py SHA-256 `1f6becdeaafaae91ff7393c02cc1eabd51cc53f117f068f6e834376dc1a71114`
- tests/test_edge_forward.py SHA-256 `403dd0fc78db0287536d241844397c48b82a83b15e8c10b624443107d2c2115a`

Full source manifest: `task-6-fix2-coinquant.source.json`.

```text
$ cd /workspace/btc-alpha-beta-improve/coinquant
$ python -m unittest tests.test_edge_forward tests.test_campaign
...s.s....s...........s..s...................
----------------------------------------------------------------------
Ran 45 tests in 0.481s

OK (skipped=5)
```

Exact-commit smoke commands (cwd `/tmp/task6-fix2-coinquant-711wkgp7`):

```text
python -m research.edge_forward source
python /workspace/btc-alpha-beta-improve/task-artifacts/task-6-fix2-synthetic-smoke.py /workspace/btc-alpha-beta-improve/task-artifacts/coinquant-task6-fix2-SYNTHETIC
python -m research.edge_forward init --help
```

normal diary SHA-256 `7a3a629cf06d0e3b6e10763d1796b02393c41de723a747bf0c46053d3192c174`; events 1; market_ready true.

```text
$ python -m research.edge_forward audit --diary /workspace/btc-alpha-beta-improve/task-artifacts/coinquant-task6-fix2-SYNTHETIC/normal/SYNTHETIC-diary.json
{"audit": true, "events": 1, "qualification": "NOT_QUALIFIED", "scope": "raw_ledger_reconstruction_only", "source_binding_verified": false}
```

pending diary SHA-256 `7fb5c5cf29520f7a93117b6121ea3aae96dcaff6e3abcc71a09a66802bafcba8`; events 0; market_ready false.

```text
$ python -m research.edge_forward audit --diary /workspace/btc-alpha-beta-improve/task-artifacts/coinquant-task6-fix2-SYNTHETIC/pending/SYNTHETIC-diary.json
{"audit": true, "events": 0, "qualification": "NOT_QUALIFIED", "scope": "raw_ledger_reconstruction_only", "source_binding_verified": false}
```

warmup diary SHA-256 `21bcf783f2c869ebf8c573b4bfac26dc94c727ff35bd950c5d616a92c423e00a`; events 1; market_ready true.

```text
$ python -m research.edge_forward audit --diary /workspace/btc-alpha-beta-improve/task-artifacts/coinquant-task6-fix2-SYNTHETIC/warmup/SYNTHETIC-diary.json
{"audit": true, "events": 1, "qualification": "NOT_QUALIFIED", "scope": "raw_ledger_reconstruction_only", "source_binding_verified": false}
```

## Self-review and remaining limits

Self-review checked both raw payload layers, exact publication boundaries, bootstrap signal consumption, source validation before/after transition, full replay equality, same-interval exclusion, unchanged money on warmup, and retained F1–F4 regressions. Final `git diff --check` passed. Only owned files were committed; root documentation changes remain uncommitted and intact.

FRED page structure is deliberately strict: a publication/table schema change or stale/missing/mismatched data blocks new initialization/risk until reviewed. The actual root Binance HTTP451 situation is not bypassed or converted into invented bars; pending initialization does not imply accessible future observations. Once accessible, complete fresh origin history must fit existing receipt freshness requirements. Warmup consumes a first opportunity and requires another new completed interval before any paper decision.

Current adapters remain canonical Spot atr-stop and Coin incumbent at scale1, with strict rejection of unsupported future selected research mechanisms. An eventual promoted mechanism still needs root's matching reviewed canonical integration/adapter. Sticky unresolved protection and Coin between-observation mark-path ambiguity retain the earlier disclosed limits; no native Lifecycle equivalence or prospective performance qualification follows. No real final export, finance selection, source freeze or diary has been created by this task.

Artifact index: `task-6-fix2-smoke-summary.json`, `task-6-fix2-worktrees.json`, per-repo source/check/probe/smoke/CLI logs and three SYNTHETIC fixture directories each. Evidence hashes: `task-6-fix2-evidence-sha256.json`. All earlier source, worktrees, fixtures, probes and report prefixes remain preserved.
