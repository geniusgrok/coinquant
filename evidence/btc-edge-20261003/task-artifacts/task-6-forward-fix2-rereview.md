# Task6a forward fix round2 scoped independent re-review

ROOT-F5: **ADDRESSED**.

ROOT-F6: **NOT FULLY ADDRESSED** — required finding T6-F6-R1 below.

SPEC: **FAIL for this scoped fix**.

QUALITY: **CHANGES REQUIRED**.

One Important/High finding remains in the deferred-init cold-start seam. F1–F4 remain closed by fix1 re-review `be77e4f57a6a7fad9073dddd3bf9d4a0e990f21a164cda73738c1ba0bb28d044`; they were not reopened. This is not a financial assessment, actual initialization or native qualification review.

## Immutable reviewed scope

Read task-6-forward-fix2-review-brief.md first, then both root rulings in task-6-forward-fix2-brief.md, the relevant original requirements, full patches and final appended report. Reviewed ROOT-F5/F6 and changes in their directly affected paths. Both modules are equivalent apart from project constants; inspected the shared changes once and both native bootstrap/readiness relationships.

- Brief SHA: `b554df126187003962f6967ab7999674411fe4cfe7f6b65083d4afd3a5e30565`.
- Report SHA: `8ea5905b5eceefe226cfd2e328b1e811946889a39188c400f2c49405956aa3ff`.
- Spot BASE `75c7d8efb07c98d21f1350d0f6186b48ed48a5a2`, HEAD `7faa66beeafbfb803bb72a36b926ee5a7a08d49d`.
- Coin BASE `e9a1117a79f391346be9af85ad3636ea8d438b4d`, HEAD `f4e82fb63742318846e51d189d03587ccc84af79`.
- Spot full package SHA: `e617d2d439ec25451bc3a87a4d9ed95d906c47c6741319e9d08cbc6bb9011bc7`.
- Coin full package SHA: `ff8618aeac6eb1a1cbbca363d9196fad6dce98ccd693da7f623ad8d1d5faca40`.
- Spot runtime/research Python digest: `56aa7fee335e5c51d5882490a1b28891569d82ffafc518c8be9386aba471a4d2`; protected byte/mode digest: `3823e451edc8f060586eda91f5ebb4d28ced548c3a67b6005460eebca9365298`.
- Coin runtime/research Python digest: `a75c0b7e132fe8a7c12a7b76b0876858a942b2fcb9648a33dbc67b9fa32f8604`; protected byte/mode digest: `2fad6792d777aaedc11c93b04e7d1b99a39c0687f383db3ff63b510656525b76`.
- Actual amended module hashes: Spot `f22b2f3999d290e8279f6cc20ecedd63982b65984c78704e024fb5d9f149fba2`; Coin `1f6becdeaafaae91ff7393c02cc1eabd51cc53f117f068f6e834376dc1a71114`.
- Shared test SHA: `403dd0fc78db0287536d241844397c48b82a83b15e8c10b624443107d2c2115a`.

Independently verified both supplied package bytes against Git's exact BASE..HEAD diff and current module/test bytes against the committed blobs. Both HEADs remain fixed and only root's PROJECT_STATE.md is dirty. Verified all75 files in the evidence index against their hashes. Index SHA `f45c5b04cb31db2712164c9f9d9f90086731140dc82cb1cf35bddbc2319d07b0`; smoke summary SHA `9585715e56b458db1c74abc8a33a14e01e033ed8ae9a88f5f29f9f6a0584fc47`.

## T6-F6-R1 — High / P1: a blocked decision falsely completes Coin cold start

**Location:** coinquant/research/edge_forward.py:1007–1020, especially the changed bootstrap predicate at1014; deferred readiness transition at1079–1092. The duplicated Coin branch in Spot's standalone module has the same implementation.

**Requirement:** ROOT-F6 requires native cold-start consumption after the warmup-only event, and missing required feature evidence must not enable a later old opportunity as a fresh entry. The warmup-only event correctly does not complete macro bootstrap; an unsuccessful macro observation must not complete it either.

**Cause:** `bootstrap` is inferred from the existence of any previous `kind == 'decision'` event. The missing relevant DFII10 branch records an ordinary blocked decision without calling `select_macro()` or establishing a macro baseline. That blocked event nevertheless makes the next call use `bootstrap=False`. A subsequent first valid DFII10 observation can therefore create and enter a macro campaign that was already eligible before initialization. The predicate proves that a decision event exists, not that canonical bootstrap completed and was persisted.

The current native call path does not do this: coinquant/linear_preview.py:10–11 preserves `market_bootstrap`, and coinquant/session.py:26–28 clears it only after `select_macro()` successfully completes and its campaign checkpoint is stored. A required DFII10 failure occurs before that clear. This comparison reads the native source and calls only pure Campaign methods; no native session/account was run.

**Independent full-append probe:** pending init, fresh fixed-origin warmup-only with flat primary history, first later completed interval with required DFII10 missing, then the next completed interval with valid retained official-shaped ALFRED form/ZIP/vintage data. Both current bar intervals remain flat primary100; current executable/mark observations are112. The latest macro observation is2019-12-30, selected vintage2020-01-01, and its actual canonical 48-hour availability precedes initialization. The existing source parser accepts these causal raw fields. Canonical `Campaign.select_macro(..., bootstrap=True)` produces `consumed`; the forward adapter instead produces `enter`, books3.49984 BTC and accepts the appended/reloaded audit.

Retained output:

```text
FIRST_DECISION {'action': 'blocked', 'reason': 'causal DFII10 raw vintage evidence required', 'opportunity': None} BTC 0
KNOWN_BEFORE_INIT True LATEST_OBSERVATION 2019-12-30 VINTAGE 2020-01-01
NATIVE_FIRST_VALID_MACRO_ACTION consumed
EVENT_KINDS ['warmup_only', 'decision', 'decision']
FIRST_VALID_MACRO_ACTION enter BTC 3.49984
APPENDED_AND_RELOADED_AUDIT True
```

This is a synthetic paper-rule error, not an actual account loss. It is load-bearing because replay accepts the same wrong inference and the result claims a genuine post-warmup modeled entry from a preexisting macro regime. ROOT-F6 cannot be approved solely from the successful primary fresh-cross regression.

**Required correction:** retain an explicit, source-bound and replay-reconstructed canonical bootstrap-completion fact, or an equivalent exact state transition. A missing relevant feature, unsuccessful selection, or a preview-only early return that discards its selected campaign must not silently complete bootstrap. Advance/consume/checkpoint the native cold-start state consistently until successful canonical completion; do not infer completion from event count/kind. The first successful relevant macro observation must consume its preexisting eligible regime. Preserve the genuinely irrelevant-source behavior allowed by the canonical primary path.

Cover pending init→warmup→missing relevant DFII10→first valid eligible macro through actual append/audit/reload, plus missing-book/early-return checkpoint handling and later legitimate fresh macro re-eligibility. Keep source/clock/money/atomic gates and shared runtime invariants intact. No private preflight or new session/topup engine is needed.

**Retained reproducer:** `task-artifacts/task-6-forward-fix2-coldstart-probe.py`, SHA `1d71d065db7d1821f1a0b00a2ff7b7bbb2607f66099d15a9a9d92e36a580f27c`.

**Retained output:** `task-artifacts/task-6-forward-fix2-coldstart-probe.txt`, SHA `8f8019c7a900f5c9c01c83cc97bba3b1a0f5859975eaadd615ff914c3e8a1d63`.

Run from the task root:

```sh
PYTHONPATH=/workspace/btc-alpha-beta-improve/coinquant python task-artifacts/task-6-forward-fix2-coldstart-probe.py
```

The final retained probe mocks only clock, approved-export trust and HTTP acquisition; actual raw DFII10 parsing, canonical campaign, paper sizing/accounting, append and audit run unchanged. Earlier small exploratory calculations isolated the same predicate; the retained full-append probe supersedes their evidence. All fixture raw files are temporary and automatically removed.

## ROOT-F5 assessment — addressed

The default URL is now the exact official fredgraph.csv endpoint; the graph page is separately categorized metadata. CSV acquisition records its own actual request/receipt/hash/path then acquires the exact metadata URL with a second clock/hash/path. `payload()` recursively checks the paired bytes/source and receipt clock shape; `fresh_receipts()` covers both clocks, and init/audit/append/replay/pre/post verification reaches that same nested evidence. Event envelope clocks and interval-boundary checks include nested receipts.

FredMetadata parses the retained strict JSON-LD Dataset identity/publication and recent-obs table. The code requires a unique DEXCHUS Dataset, timezone-aware publication, positive finite unique/date-ordered table values, latest CSV/table equality, nonfuture publication and at most7*DAY age inclusive, plus publication/observation bounds. It then selects the latest strictly prior UTC-date CSV value. The .001 conversion fee, USD=USDT assumption and declared weekly benchmark valuation remain explicit. The corrected publication freshness follows root's pre-financial ruling; it does not alter historical FX or financial gates.

Inspected tests cover the Sep25/Sep28/Oct3 pattern, exactly7days versus+1ms, future/no-timezone/missing/malformed/duplicate/wrong-series evidence, CSV/table disagreement, invalid publication gaps, current-date exclusion, paired mocked acquisition and nested hash/time/URL failure with persisted-byte immutability. The root static parser receipt binds the actual retained HTML/CSV latest Sep25/6.7110 and publicationSep28T15:16−05:00. Those public preflight bytes are source-readiness evidence and were not relabeled as paired forward observations. No additional F5 blocker was found in this scope.

## ROOT-F6 working portions and remaining limits

The approved export explicitly allows named initialization modes, and the CLI/API rejects history mixing or an unapproved deferred mode. Deferred creation has actual internal clocks, paired real-FX requirements, CNY10000/BTC0/zero money events and a reconstructed empty canonical engine. Audit derives readiness from the bound initialization mode and actual warmup replay rather than trusting a sealed boolean. Normal history init remains strict.

The first pending observation bootstraps complete fresh fixed-origin latest bars and records only warmup: no proposal, price/equity claim, fill, fee or funding mutation. Delayed warmup records elapsed intervals without backfilled decisions. Same-interval trading is rejected; later decisions require a new completion after both init and warmup. The existing tests meaningfully exercise these cases, raw/source/clock/atomic failure, readiness tampering and a primary fresh-cross entry. The identified macro-bootstrap-completion failure is the remaining exception.

Retained affected tests report Spot68 OK/7skipped and Coin45 OK/5skipped. Six exact-commit normal/pending/warmup SYNTHETIC CLI audits pass, with explicit reconstruction-only/source_binding_verified=false labels. Those suites and unchanged synthetic audits were not rerun. No unrelated native/evaluator/controller review was performed.

Complete-origin history and fresh acquisition remain operational requirements; existing Binance HTTP451 evidence is not bypassed. Public availability, native flatness, actual elapsed account days, continuous equity, prospective alpha and real finance selection are not established by any fixture. The actual full financial proof/export and real pending initialization remain later root work, after this blocker is corrected and reviewed.

Both repositories and all previous evidence/helper bytes were preserved. No child agent, commit, public network, full financial producer, Coin suite, native/private/account/credential operation or HOME/UID/lock change occurred. Only this new report and its independent review-probe artifacts were added persistently. Native cases0/actual account-days0/NOT_QUALIFIED remain unchanged.
