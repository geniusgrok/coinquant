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
