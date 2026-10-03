# Task 5 implementation report

Implementation complete for independent SPEC/QUALITY review. No new full financial producer, new complete account outcome, native request, private account access, default change, or adoption decision was made. Root retains all actual financial invocations.

## Immutable scope and commit

Worktree `/workspace/btc-alpha-beta-improve/spotquant`; assigned review BASE `8c1be0fbfcc6a1c12d74450d29b5916bd10fa5dc`.

Own commit: `12fd6f13c2ea2bb29328a5a354153b9f044d7a2a` — Add strict source-bound BTC edge assessment and funded-account gates.

Only committed paths:

- `research/edge_assessment.py`, SHA256 `76dad3f7b5a8427d760300b18b677daececfa2888dcfaef8e8b9563ad8cd76a9`.
- `tests/test_edge_assessment.py`, SHA256 `e77ccc1b8892bff8c9aca3c58ffce0bf255a17d598e54200a97c45b5c5619b5e`.

Committed through explicit `git add` and `git commit --only` of those paths. Final `git status --short` was empty. No old source, results, frozen contracts, runtime defaults, shared account settings, or Coin source was edited. No subagent was spawned. Ponytail was applied to reuse the existing pure verification/account/statistics helpers without global SPEC patching, new dependencies, or an autonomous runner.

Clean post-commit measured assessor identity independently proved by `git archive` plus committed protocol checks:

- HEAD `12fd6f13c2ea2bb29328a5a354153b9f044d7a2a`.
- Full research/runtime Python SHA256 `01f27a14474c63659adb1f535c8448886488a221c9f8b77c446ecbff5570e143`.
- `dirty=false`.

## Implementation and interfaces

The single new assessor reuses old `verify_source`, strict JSON hashing/exclusive writer, row completeness/timing, six evidence fingerprints, canonical/account annualization, daily returns, calibration, achieved-risk statistics, original financial attribution and HAC7 regression. It does not mutate their global SPEC or weaken their validators. Added checks implement the new per-project edge source/spec/protocol and producer-envelope contracts.

Source verification proves the complete Python digest from each recorded committed tree, separately hashes the committed edge spec/protocol and original complete meter protocol, and rejects producer Python differences against the current frozen tree (only the new Spot assessment module may differ). All current accounts within a project must retain identical measured source and new edge contracts. Old approved Spot canonical and Coin alpha envelopes remain separately verified under their own original committed contracts. No source fields are rewritten.

Inputs support raw files or a one-level manifest with exact schema:

```json
{"format":"btc-edge-account-manifest-v1","files":[{"path":"relative-or-absolute-original.json.gz","sha256":"64-lowercase-hex"}]}
```

Exact original compressed child bytes are hashed; nested manifests, duplicate file paths, duplicate account identities and conflicting row/envelope identities fail. Per-file envelopes are retained in the report, including original source/inputs/conditions, Coin exact calibration document bytes and print restore receipts. Every row retains status/reasons and its raw hash. Invalid envelopes are retained as rejected-file entries. Known invalid earlier attempts should remain separately retained artifacts, never included as duplicate substitutes for a required complete identity.

The unconditional inventory is 68 accounts: Spot36, Coin16, actual calibrated8 including every losing single, offset2, original-default actual budgets6. Applicable combinations add four unscaled stresses and one actual calibrated base; selected nonbaseline candidates add their actual2500/5000/7500 accounts. Eligibility uses exact Decimal thresholds; ranking uses highest worst-stress CAGR then registered order. Combinations contain all individually eligible mechanisms in registered order, no subsets or duplicate singleton replay. Their own actual source-bound base generates their own training profile.

Approved references come from pinned original acceptance/bridge/inventory/raw hashes, not the convenience index or caller-supplied passed flags. The Spot baseline is the four canonical ATR accounts, with accepted base gzip `dc94a7b315ee8ea11cc7215cd8ff7c02a8ab94180499b2c4ebf7fe1448682323`; other raw hashes resolve from the pinned canonical inventory/bridge. Coin is original incumbent raw `bf1d167979f4bb3d15925f0bcaf5337bd1cc0a17523628b3af0599875dc5a7c1`. Six groups are compared, with detailed before/after hashes on any mismatch. Existing baseline annotation fields such as research identity, old risk annotation and subpools are additionally preserved/compared; only the named added opportunity ledger is excluded as instrumentation. Operating clocks/status/constraints/ownership are not ignored.

The new monetary checks reconstruct Spot cash/BTC/fees from fills, Coin average-cost position/realized cash/fees/funding from original income and fills, terminal CNY conversion, and every retained daily wallet/position/equity at original capture clocks. The original Coin daily capture includes exact-midnight funding but precedes next-minute same-stamp print fills; this convention was traced to the original `ResearchExchange._pay_funding`/capture order and verified against all four accepted scenarios. Terminal funding remains exclusive. Coin actual closing exposure uses its original actual mark, while BTC regression uses the synchronized Spot comparator. Continuous MDD remains the original account proxy and is checked against closing-daily MDD, never relabeled as independent continuous measurement.

Calibration documents are strictly project-separated, exactly match producer schema, and bind each profile to its actual unscaled base raw SHA. Training is sliced before all statistics and requires precisely731 dates/USDT returns through2021. Formula and baselineunity are unchanged; no outer.01 scale floor. Actual risk receipts bind exact original document bytes/profiles, and current sources/features/inputs and original baseline six-group equality remain gates. Spot new-buy scale journals and Coin decision binding digests are checked. Future-tail changes do not influence profiles. Actual volatility/beta upper bands and risk-only fallback use actual calibrated candidate versus actual unity baseline.

Budget aggregation consumes actual independently funded accounts, rejects wrong capital/candidate/source/schedule/risk/offset/unresolved rows, and sums full synchronized actual daily CNY/USDT equity and absolute BTC notional. It retains actual per-account fees/funding/fills and rounding/min-notional-sensitive outcomes.5000/5000 remains the neutral reference; other fixed splits are sensitivities. Joint MDD is explicitly daily, not continuous joint MDD. No10000 curve is multiplied.

Daily ES99 is the signed mean loss of the worst `ceil(N*.01)` arithmetic CNY returns. Daily drawdown, underwater duration, worst day, CNY/USDT account CAGR with original per-project year conventions,2022+ metrics, BTC beta/HAC7, capture, yearly contributions and closing exposure are retained. Cash volatility0/beta0 is identifiable when BTC varies; degenerate BTC risk remains unidentifiable.

## CLI

`python -m research.edge_assessment --help` succeeded. Main options:

```text
--phase preliminary|calibration|final
--spot RAW_OR_MANIFEST --perp RAW_OR_MANIFEST
--spot-calibration ORIGINAL_JSON  (repeatable for original and combo docs)
--perp-calibration ORIGINAL_JSON  (repeatable)
--features PINNED_FEATURE_JSON
--schedule ORIGINAL_SCHEDULE --fx ORIGINAL_FX --market SPOT_MARKET_ROOT
--coin-market COIN_MARKET_ROOT --coin-prints IMMUTABLE_OFFICIAL_ZIP_VAULT
--references ACCEPTED_PRIOR_EVIDENCE_DIR
--financial-review INDEPENDENT_PROOF
--calibration-out-dir NEW_DIRECTORY
--out NEW_JSON --csv NEW_CSV --markdown NEW_MARKDOWN
```

Root confirmed Coin market default `/tmp/coinquant-market` and immutable original public ZIP vault `/workspace/scratch/alpha-beta-next/public-print-vault`. The assessor hashes actually consumed listed ZIPs and official CHECKSUM sidecars once per invocation, verifies every claimed consumed SHA and print receipt, and preserves `derived_binary_sha256`. No download occurs and temporary producer cache paths do not become original public source. The full14GB vault is not indiscriminately rehashed by this task; only the actual listed smoke input subset was read here.

Calibration outputs use `spot.json`, `perp.json`, and applicable `spot_combo.json`/`perp_combo.json`. They are exclusive, project-separated, deterministic documents; root may make one exclusive byte-identical receipt-bound copy to its preregistered `spot-calibration.json`/`perp-calibration.json` paths. Report/CSV/Markdown writes are exclusive and JSON forbids nonfinite outputs; reads reject duplicate keys, NaN/Infinity and numeric overflow such as1e999. No full assessment CLI was run against new financial accounts; the user-owned producer/financial command register remains unexecuted.

Preliminary missing/incomplete rows remain explicit pending; blocked inputs retain reasons. Final exits2 and remains blocked unless the required applicable inventory is complete/known/audited, all identities/calibrations/baselines match, and an independent review proof binds that exact completed preliminary report. Complete report qualification fields are native_cases0, actual_account_days0, native_qualificationNOT_QUALIFIED, prospective_alpha_provenfalse.

## Independent financial proof contract

Final requires a cycle-free `--financial-review` document:

```json
{
  "format":"btc-edge-financial-review-v1",
  "preliminary":{"path":"preliminary.json","sha256":"EXACT_ORIGINAL_REPORT_BYTES_SHA256"},
  "inventory_sha256":"CHECKSUM_OF_inventory_binding(preliminary)",
  "reviewer_source":{"git_head":"CLEAN_FULL_COMMIT","dirty":false,"python_sources_sha256":"FULL_DIGEST"},
  "checks":{
    "source_and_inputs":{"passed":true,"artifact":{"path":"source.json","sha256":"SHA256"}},
    "original_accounting":{"passed":true,"artifact":{"path":"accounting.json","sha256":"SHA256"}},
    "baseline_six_groups":{"passed":true,"artifact":{"path":"baseline.json","sha256":"SHA256"}},
    "calibration_and_actual_risk":{"passed":true,"artifact":{"path":"risk.json","sha256":"SHA256"}},
    "adoption_gates":{"passed":true,"artifact":{"path":"gates.json","sha256":"SHA256"}},
    "actual_budget_aggregation":{"passed":true,"artifact":{"path":"budgets.json","sha256":"SHA256"}}
  }
}
```

Exact category names are the six keys above. Minimal per-category artifact example:

```json
{
  "inventory_sha256":"SAME_INVENTORY_SHA256",
  "category":"original_accounting",
  "recomputations":[{"account":"spot|atr-stop|base|1E+4|0|unscaled","raw_sha256":"ORIGINAL_RAW_SHA256","rederived_final_usdt":"REVIEWER_COMPUTED_VALUE","matches":true}]
}
```

The reviewer should retain full per-account independent recomputations appropriate to each category. `inventory_binding(report)` is the stable exported checksum target. `verify_financial_review` checks exact preliminary bytes/status/no pending/no blocking, recomputed current inventory equality (raw/source/spec/inputs/calibrations/gates/selection/baseline groups), clean committed reviewer full Python proof, and all six bound nonempty recomputation artifacts. A passed boolean alone cannot qualify. Final report binds the proof and artifacts without requiring a final hash before the final file exists. This verifier establishes artifact consistency; substantive independence/correctness remains the mandatory human/independent financial review, not a signature or self-certification. Exact assessor HEAD remains part of the binding, so preserve the frozen source across complete preliminary review and final invocation.

Stable independently callable helpers include `verify_source`, `baseline_equality`, `monetary_audit`, `audit_daily`, `original_curve`, `calibration_document`, `risk_match`, `adoption_gates`, `required_matrix`, `aggregate_pair`, `inventory_binding` and `verify_financial_review`.

## Exact verification commands/results

All commands ran in `/workspace/btc-alpha-beta-improve/spotquant` with the existing Python runtime. No Coin tests or producers ran.

1. `python -m py_compile research/edge_assessment.py` — exit0.
2. `python -m unittest discover -s tests -p 'test_edge_assessment.py' -v` — final22 tests passed in0.475s, exit0. Final retained log `task-5-focused-tests.log`, SHA256 `49b7628761b976def7e38e3f72d3ff6414ded6a8bfe15bbf0796af95f7792a53`.
3. `python -m unittest discover -s tests -v` —283 tests passed in12.296s, exit0. Log `task-5-full-tests.log`, SHA256 `85f5d156aecd744bf5a29edbcf8b709119708616a17cea630061d9539f62406e`. This followed implementation of all trust-boundary/timing checks; subsequent small edits removed unused imports, explicitly exposed closing exposure/fill count, and hardened finite calibration statistics, followed by the final focused run.
4. `git diff --cached --check` — exit0 before explicit path-only commit. `git status --short` — clean after commit.
5. `python -m research.edge_assessment --help` — exit0, no environment or financial work needed.
6. `PYTHONPATH=. python /workspace/btc-alpha-beta-improve/task-artifacts/task-5-verification.py > /workspace/btc-alpha-beta-improve/task-artifacts/task-5-verification.log 2>&1` — exit0 on clean committed source. Eight original accepted baselines passed committed-source/bridge binding, terminal accounting, all retained daily wallet reconstructions and original Coin journal clock checks. Retained smoke ingestion verified17 incomplete accounts (one Spot crowding plus16 reviewed Coin) and actual listed ZIP/CHECKSUM/derived receipts, all17 statuspending with exactly `measurement_incomplete`, zero rejected files, zero new producer invocations.

Synthetic coverage includes exact required matrix including rejected single risk rows, extra/duplicate/nested manifest rejection, strict JSON/exclusive writes, dirty/mismatched source/spec/protocol/input checks with standalone temporary Git fixture, original six groups and operating-only/annotation drift, partial/complete session clocks and outage, ES99 percentile/sign and boundary gates, strict CoinMDD, actual risk-only fallback,731 training and future-tail invariance, separate shared-name project profiles, profile schema/scale/raw bytes/unity, fixed all-components ordering/ranking, actual budget conservation/exposure/wrong capital/candidate/roles/alignment, original daily wallet reconstruction, official consumed bytes/checksums, pending versus final fail-closed, and financial proof original-byte/inventory mismatch. Imports and synthetic tests require no sibling repository, preserved artifacts, Git history, real market cache or network; only the standalone temp Git source test creates local fixture commits.

Post-commit read-only verification artifacts:

| Artifact | SHA256 |
| --- | --- |
| `task-5-verification.py` | `bc17bcdb5470d356a89f2e98f514582c1e4660372e128af84c653399bf3ff1e7` |
| `task-5-verification.json` | `c2c8d82798c60a671e8b8560bce600d1d69ace621a2ff14c92edc00234280c2b` |
| `task-5-verification.log` | `b377ee0db0724fe83357cac4ee5b8f8eb76d700195c061da844ed132e7aaadec` |

`task-5-verification.json` retains every checked original baseline raw SHA, original source and all six fingerprints, full assessor committed-source file proof, every consumed smoke original ZIP/CHECKSUM hash, and every incomplete smoke source/raw hash. Source/spec/raw identities remain original; no retained bytes were rewritten. The17 smoke rows do not establish new economic benefit or full-window eligibility.

## Self-review and material concerns

Traced both producer envelopes, calibration validators, original accounting/capture paths and approved canonical bridge before integrating. Corrected a discovered Coin daily-boundary assumption using original capture order and all four accepted baseline scenarios, rather than adding tolerance or ignoring accounting mismatch. Kept old baseline annotations separate from new unity envelopes, used actual Coin mark for exposure, rejected JSON numeric overflow, verified all original source families separately, and added official-byte/checksum verification rather than trusting metadata-only hashes. All meaningful new code is in the two owned files; no old validator was patched.

No known implementation blocker remains locally. Independent Task5 SPEC/QUALITY review is still required. Full68+ applicable financial inventory, actual deterministic calibration producer round trips, calibrated unity equality, candidate decisions/combination applicability, complete budget aggregation and final independent financial proof remain unmeasured. Synthetic tests and retained prior evidence cannot establish that future full accounts will complete/pass. The strict new daily/source/checksum checks may expose genuine failures in future accounts; preserve those failed originals and fix through the registered review process, never reroll or relax normalization. The known continuous proxy/mark/feature-availability/publication assumptions and contaminated historical evidence remain disclosed. Native cases0, actual account-days0, NOT_QUALIFIED, prospective alpha unproven.

# Task5 fix round1 — T5-R1 and T5-R2

The original independent verdict was SPEC FAIL / QUALITY CHANGES REQUIRED. Both P1 findings are addressed in the implementation below; independent scoped re-review must determine closure. This append supersedes the earlier permissive financial-artifact example and the earlier daily completeness claim. The pre-fix report, review/probes and original raw evidence remain retained unchanged.

## Scope, commits and final identity

FIX_BASE `12fd6f13c2ea2bb29328a5a354153b9f044d7a2a`.

- `0df61687f532b9762d33c43fed8dc006e41d7402`: exact financial-proof coverage/typed consistency and fail-closed missing daily ledgers, with focused regressions.
- `73a0baf5702fce5bed23205c245aab53fad951b9`: additionally bind calibration diagnostics/environment to the same cycle-free preliminary/final inventory; covered by an added tamper assertion.

Both commits used explicit `git commit --only research/edge_assessment.py tests/test_edge_assessment.py`. Root's existing PROJECT_STATE modifications remain uncommitted and untouched; final `git status --short` shows only ` M PROJECT_STATE.md`. Research/runtime source is clean. No old helper, economics, mechanism, defaults, original evidence, Coin source or Coin tests changed. No subagents, full producer, native/private request, account/credential/order/transfer/settings/HOME/UID/lock action occurred.

Final source proof:

- HEAD `73a0baf5702fce5bed23205c245aab53fad951b9`, research/runtime `dirty=false`.
- Full Python SHA256 `d1cb1aaf06dad8025b3c978a85018b9b3c12bd5cb13c3d5bf8f35038be67f13a`.
- `research/edge_assessment.py` SHA256 `d931bd9c499560fd8bf6b0e53fa428c9dc641249740505c6eb84d95ea9e6d20b`.
- `tests/test_edge_assessment.py` SHA256 `40ffc93734de86da27f37e3ab413b0c716d2615df3b95ec9eeade73545ebf23b`.

## T5-R1 — complete typed financial proof

The former nonempty dict/list check is removed. `review_expectations(report)` derives exact record identities, raw bindings and typed values for all six categories from the completed applicable inventory. `verify_financial_review` requires each exact expected record once, with `matches:true`, and recursively compares all fields/types/values. Unknown identities/raw hashes, duplicate/extra/missing records, omitted/extra fields, wrong numeric/boolean types, nonfinite values, null values, failed consistency and altered computed results reject. An arbitrary nonempty `{'case':'result'}` or the reviewer's `NOT_AN_ACCOUNT`/`matches:false` probe cannot pass.

Correct candidate rejection is explicitly valid: the artifact's consistency is true while its recomputed `eligible` value and failed adoption gates remain false as expected. Actual risk bands/gain and adoption gates are checked against completed account metrics; registered ranking, all-component combination applicability and final selected identity are rederived. Actual budget pair identities, raw hashes, capitals and each synchronized equity/notional sum are checked. No requirement that every candidate be eligible was introduced.

The cycle-free inventory now also binds each complete account's actual evidence values, full portfolio outputs, input envelopes, original calibration documents, calibration diagnostics, environment and combinations. Therefore an unchanged set of raw IDs cannot hide changed budget statistics or changed training diagnostics between the preliminary report reviewed and the current final computation. Preliminary original bytes and final current-source bindings remain checked as before.

Completed reports now retain original calibration input documents separately by project and exact byte SHA (`calibration_input_documents`), alongside deterministic documents, plus reference/actual raw SHA values in each baseline stress/unity comparison. This preserves exact original document identities and accepted reference identities for the review coverage derivation.

### Final proof schema

Outer proof schema remains exact:

```text
{
  format: "btc-edge-financial-review-v1",
  preliminary: {path: string, sha256: exact original preliminary bytes},
  inventory_sha256: checksum(inventory_binding(complete_preliminary)),
  reviewer_source: {git_head, dirty:false, python_sources_sha256},
  checks: {
    source_and_inputs: {passed:true, artifact:{path,sha256}},
    original_accounting: {passed:true, artifact:{path,sha256}},
    baseline_six_groups: {passed:true, artifact:{path,sha256}},
    calibration_and_actual_risk: {passed:true, artifact:{path,sha256}},
    adoption_gates: {passed:true, artifact:{path,sha256}},
    actual_budget_aggregation: {passed:true, artifact:{path,sha256}}
  }
}
```

Each artifact has **exactly** `inventory_sha256`, `category` and `recomputations`; the latter is a list. Every list entry has **exactly**:

```json
{
  "id":"perp:base",
  "raw_bindings":{"reference":"EXACT_ACCEPTED_ORIGINAL_SHA256","perp|incumbent|base|1E+4|0|unscaled":"EXACT_CURRENT_RAW_SHA256"},
  "values":{
    "reference_groups":{"financial":"SHA256","fills":"SHA256","daily":"SHA256","ownership":"SHA256","operating":"SHA256","remaining_original_fields":"SHA256"},
    "actual_groups":{"financial":"SAME_SHA256","fills":"SAME_SHA256","daily":"SAME_SHA256","ownership":"SAME_SHA256","operating":"SAME_SHA256","remaining_original_fields":"SAME_SHA256"}
  },
  "matches":true
}
```

This is the `baseline_six_groups` record shape; replace symbolic strings with actual hashes. Both group maps require the six exact keys and matching actual hashes. The artifact needs every required record, not just this illustrative example. The old example containing `account/raw_sha256/matches` alone is intentionally no longer admissible.

`task-5-fix1-proof-schema-examples.json` provides concrete synthetic examples for every distinct record shape, including separate source-account/source-file, profile/actual-risk and gates/ranking records. They are explicitly labeled synthetic, incomplete subsets and cannot qualify as an actual review. `review_expectations(report)` is the authoritative auditable schema/coverage comparison contract; reviewers must independently recompute its values from originals rather than present generated expected values as independent work.

### Exact six-category coverage and values

Let N be the complete applicable account count and R the number of distinct original raw files. Without combinations/nonbaseline selection N=68; R depends on whether producer files bundle several accounts.

| Category | Exact record IDs / required coverage | Values compared |
| --- | --- | --- |
| `source_and_inputs` | `account:<account_id>` for every N account; `raw:<original_path>` for every R original file | Account project/candidate/scenario/capital/offset/calibrated/components/source/file. Raw project/source/spec/protocol/FX/schedule/market/feature identities, exact original-envelope checksum and checksum of the full actual input-byte hash map, including consumed files. Every row binds its original raw SHA. |
| `original_accounting` | One `<account_id>` for every N account, including controls, negative candidates, calibrated, offsets, budgets and applicable combos | Initial/terminal CNY/USDT, fees/funding/fills, original continuous proxy MDD and CNY/USDT CAGR; all daily CNY/USDT metrics; full daily curve checksum/count; independently derived ledger reconstruction checksum. Curve coverage must equal every registered date and all selected monetary fields are finite. |
| `baseline_six_groups` | `<kind>:<scenario>` for four stresses per project, plus `<kind>:actual_unity`: exactly10 records | Exact accepted-reference/current raw SHAs and both complete six-group maps. Actual unity references its current unscaled baseline raw. Source report comparison must itself be passed with no differences. |
| `calibration_and_actual_risk` | `profile:<document_label>:<candidate>` for every profile in each original project and applicable combo document; `actual:<account_id>` for every actual risk account | Profile exact schema/scale/cutoff/base raw, all matching exact document-byte SHAs,731 training days, candidate/baseline training statistics and source. Actual records bind document/profile, actual candidate/unscaled base/unity raws, validation beta/volatility/total USDT return and actual continuous MDD. Original four singles per project are always present, even when rejected. Combo documents separately audit all included profile bindings and their own combo profile. |
| `adoption_gates` | `<kind>:<candidate>` for all six singles plus each applicable combo; `<kind>:ranking` per project | Complete eligible/rejected result, every gate, rejection reasons, worst-stress CAGR and actual-risk result. Actual bands/gain and paired gates are checked against accounts. Ranking records retain registered order, ranked eligible singles, best single, all eligible components and final selected identity. Correct negative outcomes remain valid. |
| `actual_budget_aggregation` | `current_default:2500/7500`, `current_default:5000/5000`, `current_default:7500/2500`, plus the same three `selected:` records if either selected candidate differs | Exact constituent account IDs/raw SHAs, actual budgets/CNY10000/no flows, complete daily equity/exposure checksum/count, daily CNY/USDT metrics, beta, explicitly identified or unidentifiable correlation, closing gross exposure, actual per-account fees/funding/fill counts. Each day's equity and absolute notional sums must equal actual accounts. |

Account IDs retain the existing normalization, e.g. `spot|atr-stop|base|1E+4|0|risk`. All fields are exact typed comparisons with no silently accepted null/unknown consistency or numeric tolerance in the proof layer. Legitimately unidentifiable portfolio correlation is represented as `{identifiable:false}`; otherwise `{identifiable:true,value:<finite normalized decimal string>}`. It is never a null consistency result. Monetary ledger tolerances and original financial formulas themselves are unchanged.

The complete68-account synthetic positive roundtrip has counts136 source records (68 individual synthetic raw files),68 accounting,10 baseline,16 calibration/actual risk,8 gates/ranking and3 budget aggregation records. All six mechanism decisions are correctly rejected; the review verifies their consistent negative outcomes. This is a pure proof/coverage test with source verification isolated by a mock, not a synthetic claim of real completed financial evidence. Real final still requires the actual fresh `assess` path to verify original source/raw/input/account completeness plus independent reviewer source.

Automatic validation is an artifact consistency/coverage gate, not a signature and not a replacement for substantive independent financial review.

## T5-R2 — fail closed on missing daily evidence

`audit_daily` now merges every expected UTC closing boundary with the original retained snapshot clocks and advances the actual original fills/income across that timeline. At a missing boundary it permits carry only when both actual and last verified positions remain exactly flat, actual cash remains the verified cash and no fill/income event has occurred since that verified snapshot. Missing held exposure, missing realized cash changes, or intervening unreflected events reject. An already verified post-trade flat snapshot may begin a later eventless carry. No mark interpolation, cash fiction, curve scaling or protection/status waiver is introduced.

Existing Spot actual snapshot clocks and Coin exact-midnight funding-before-next-minute-same-stamp-fill ordering are preserved. The strengthened guard runs before unchanged `canonical`, so its former stale-cash fallback cannot conceal missing evidence. The old canonical/statistics helpers remain untouched.

Regressions cover terminal-only evidence after a held day; an intraday roundtrip already flat but with changed cash; genuinely eventless flat carry; a verified post-trade flat snapshot followed by eventless carry; and Coin exact-midnight funding/same-stamp fills with rejection when the held closing snapshot is removed. The accepted Spot baseline's original raw was also read, copied only in memory, and reduced to the terminal snapshot: the new guard rejected it. Original bytes were untouched.

## Focused tests and final-source verification

Only tests covering amended code were rerun; the unchanged283-test full suite was not rerun.

1. `python -m unittest discover -s tests -p 'test_edge_assessment.py' -v > /workspace/btc-alpha-beta-improve/task-artifacts/task-5-fix1-tests-final.log 2>&1` — **28 tests passed in28.691s**, exit0. Includes the complete positive proof roundtrip; one-record omission in each of six categories; duplicate/unknown identity; failed consistency; wrong raw SHA; null/type/nonfinite mismatch; wrong budget curve hash; reversed correct rejection; original preliminary-byte, input, portfolio and calibration-diagnostics binding changes; and the missing-daily regressions. Prior interim passing and development failure logs remain separately retained.
2. `git diff --check` — exit0. Both path-only commits succeeded and root PROJECT_STATE edits remain preserved.
3. `python -m research.edge_assessment --help > /workspace/btc-alpha-beta-improve/task-artifacts/task-5-fix1-cli-help.log` — exit0 on the first clean fix commit; help/interface source did not change in the final binding-only follow-up.
4. `PYTHONPATH=. python /workspace/btc-alpha-beta-improve/task-artifacts/task-5-fix1-final-verification.py > /workspace/btc-alpha-beta-improve/task-artifacts/task-5-fix1-final-verification.log 2>&1` — exit0 on final clean research source73a0baf. **All eight retained accepted baselines pass** source/bridge/raw binding, terminal accounting and strengthened every-boundary daily reconstruction. Original Coin session journal checks pass. **All17 retained smoke rows remain pending**, exactly `measurement_incomplete`, with no rejected file; actually consumed ZIP/CHECKSUM and original derived receipt bindings still match. **Zero new financial producers**. The read-only accepted-Spot terminal-only mutation rejects with a concrete missing-snapshot reason, retained in the machine receipt.

Final verification source was73a0baf/full Pythond1cb1aaf…; the earlier0df6168 fix verification receipt is retained under its original name and is not relabeled.

| Artifact | SHA256 |
| --- | --- |
| `task-5-fix1-tests-final.log` | `dd9ba78662026fb34506a273eb9de4a0c8c34e39b12b5b93fd315752a68d6f60` |
| `task-5-fix1-final-verification.py` | `e9ecf0ce09950c29ed7a9af584bddb2eec0f5db78918681f0a25eb30dbd50ddf` |
| `task-5-fix1-final-verification.json` | `6a8bb8673e5c6634add3a70f15c4faffec1ec532c73b2bcc58d348864bbf1548` |
| `task-5-fix1-proof-schema-examples.json` | `9bb77ad185a40663e5871ef87a765dc2ea6baa6c576ad5e264aa9e63069f4fc3` |

## Fix self-review and remaining limits

Checked the new proof contract against the completed source-bound account inventory, not merely artifact existence: source/account coverage, exact raw identities, actual calibration documents and731 statistics, actual unity groups, negative candidate outcomes, registered ranking and every actual budget pair all have explicit expected records. A final self-review additionally bound calibration diagnostics/environment to prevent a same-raw-inventory label from concealing changed reported statistics. Checked daily missing-boundary behavior before invoking canonical and retained the original venue's event ordering instead of widening timing or numeric tolerances.

No known local blocker remains for T5-R1/T5-R2. Their closure still requires root's scoped independent SPEC/QUALITY re-review. The actual full68+ inventory, new economic results, future actual profile roundtrip, independently produced final financial proof, adoption/default decisions and native qualification remain unmeasured. The positive synthetic proof test does not substitute for that work. Native cases0, actual account-days0, NOT_QUALIFIED and prospective_alpha_provenfalse remain unchanged.


# Task5 fix round2/5 — T5-R3 exact original gate precision

## Scope, commits and immutable source

Responds only to T5-R3/P2 in `task-5-fix1-rereview.md` under `task-5-fix2-brief.md`; FIX_BASE `73a0baf5702fce5bed23205c245aab53fad951b9`. T5-R1/T5-R2 were independently marked ADDRESSED and their coverage/daily guards remain in place. This appendix supersedes the fix1 use of float display MDD in proof gate recomputation. Earlier report and evidence files remain intact; root preserved `task-5-report-pre-fix2.md`.

Own path-only commits:

- `ddfd1b7126fe4a2866878f1b3a772c5c3868dbc3` — retain exact original gate inputs and use them in primary decisions and independent-proof comparisons, with precision/schema regressions.
- `e910189daae036cc3978173934c472862405bc8a` — remove an unnecessary newly introduced schema MDD range condition. Finite adverse MDD remains evidence; only the unchanged registered gates decide economic acceptance. Added this preservation assertion to the schema test and reran the covering suite.

Only `research/edge_assessment.py` and `tests/test_edge_assessment.py` changed. Root's uncommitted `PROJECT_STATE.md` remains preserved; no other tracked work was committed. Final source HEAD is `e910189daae036cc3978173934c472862405bc8a`, source `dirty:false`, full Python digest `6b27af92cd09be94fb1a92c20bf98ffad3f1a4cc3c7bd03796782aabb7cc2269`. Final file hashes:

- `research/edge_assessment.py`: `0ccc7fd901f16f2018d34328aa772b0804361fb354148c03bc97d8b5b709bae3`.
- `tests/test_edge_assessment.py`: `98472ca19afd0edd39981beb5634023ad06fd31f034024b6954d301f883caf4b`.

## Exact input contract and six-category coverage

Every complete account now retains `gate_inputs` before original rows are stripped from report serialization. The exact shape is:

```json
{
  "raw_sha256": "EXACT_ORIGINAL_RAW_SHA256",
  "values": {
    "cagr": 0.1,
    "mdd": "0.30000000000000001",
    "worst_day": -0.02,
    "es99": 0.03,
    "underwater": 50
  }
}
```

`raw_sha256` must equal the account's verified original-file digest and be a valid SHA256. Both objects have exactly the shown fields. `mdd` is the original finite Decimal string, never a float conversion; `cagr`, `worst_day`, `es99` are finite JSON numbers (bool excluded); `underwater` is a nonnegative integer. The values come from original row CAGR/MDD and already derived daily worst-day/ES99/underwater statistics. While the original row is retained, the helper also checks retained values equal the original inputs. Without the row it requires the complete retained binding. Both primary decision and proof gate paths call this one helper, including the actual calibrated candidate/control MDD fallback. No economic gate, threshold, tolerance, ranking, old helper, source mechanism or daily timing/funding rule changed.

The whole account evidence checksum already participates in `inventory_binding`, so exact gate inputs are bound to the complete inventory and immutable preliminary bytes. Final assessment rereads the actual source/spec/raw/input/calibration evidence and regenerates these values before matching the independent proof. A reviewer must independently compare the precise strings and other gate inputs to their original raw files; a self-generated expectation artifact does not constitute independent review.

The outer proof/artifact/record schema remains the fix1 schema. The category names and exact coverage are unchanged:

| Category | Coverage | Fix2 schema change |
| --- | --- | --- |
| `source_and_inputs` | Every account plus every distinct original raw file | None; current complete inventory now binds retained gate inputs through account evidence hashes. |
| `original_accounting` | Every applicable account | `values.gate_inputs` has the exact object above; `values.money.continuous_proxy_mdd` is now the original exact string. |
| `baseline_six_groups` | Four stress cases and actual unity per project, ten records | None. |
| `calibration_and_actual_risk` | Every project/applicable combo profile plus every actual calibrated account | Actual record `values.validation.continuous_proxy_mdd` is now the original exact string. |
| `adoption_gates` | All singles/applicable combinations plus both project rankings | Candidate record `values.gate_inputs` maps each of its eight stress and two actual calibrated account IDs to the exact bound object. Existing `values.result` is recomputed with those same values. Ranking shape unchanged. |
| `actual_budget_aggregation` | Three fixed current-default budget pairs plus three selected pairs when applicable | None. |

`task-5-fix2-proof-schema-examples.json` gives minimal concrete synthetic records for every distinct shape in these six categories and an explicit high-precision gate-input example. It is labeled incomplete illustrative evidence and is not an actual review artifact. Complete all-baseline selection fixture coverage remains 136 source, 68 accounting, 10 baseline, 16 calibration/actual-risk, 8 gates/rankings and 3 budget records; every mechanism is correctly rejected. Full actual coverage still follows the applicable inventory including combinations/selected budget cases, rather than those example counts.

## Covering verification and exact outputs

1. `python -m unittest tests.test_edge_assessment -v > /workspace/btc-alpha-beta-improve/task-artifacts/task-5-fix2-tests.log 2>&1` — **31 tests, OK, 40.506s**, exit0 on first fix2 commit contents. After the schema-range self-review adjustment, final covering command `python -m unittest tests.test_edge_assessment -v > /workspace/btc-alpha-beta-improve/task-artifacts/task-5-fix2-tests-final.log 2>&1` — **31 tests, OK, 40.007s**, exit0. The original unchanged 283-test full suite was not repeated.
2. `git diff --check` — exit0. `git commit --only research/edge_assessment.py tests/test_edge_assessment.py ...` created each own commit without including root's state edits; final `git status --short` shows only ` M PROJECT_STATE.md`.
3. Schema examples were generated with the complete synthetic test fixture and `review_expectations` via an offline Python heredoc, then written exclusively to the new fix2 example file. No actual financial account producer or source check was invoked by this synthetic example generation.
4. `PYTHONPATH=. python /workspace/btc-alpha-beta-improve/task-artifacts/task-5-fix2-final-verification.py > /workspace/btc-alpha-beta-improve/task-artifacts/task-5-fix2-final-verification.log 2>&1` — exit0 on final clean source. Output: **8 retained accepted baselines, 17 retained incomplete smoke accounts, 0 new producers**; verification digest `afa10eacfc1be44d29b198fda23f4eebed6271621778244b4ae099f8cb5f23cb`. Original eight MDD strings/CAGR numeric types are explicitly checked and recorded, with original raw identities. Source/raw bridge and six-group fingerprints, monetary/daily reconstruction, Coin session chronology and consumed public input validation still pass. All 17 smoke accounts remain `pending` solely for `measurement_incomplete`; no accepted evidence is relabeled.

The actual regression boundary is tested end-to-end: baseline `"0.31"`, candidate `"0.30000000000000001"`, equal CAGR, candidate float display `.3`. Primary `base_improvement:false` and `eligible:false` are preserved; all six complete typed proof categories are written, preliminary/inventory hashes bound, and the correct negative proof roundtrip accepts. A newly hashed proof substituting rounded `"0.3"` for the original exact value rejects. Independent source verification is mocked only in this offline synthetic proof test; it is not an assertion of real financial completion.

Additional tests compare primary decisions with proof expectations for both projects' actual calibrated fallback: `.31` baseline versus `.30` candidate passes exact `.01` improvement; `.30000000000000001` fails. Coin unscaled strict MDD accepts `.49999999999999999`, rejects `.50` and `.50000000000000001`, even though all three can display as `.5`. Schema guards cover missing/extra fields, missing/wrong raw binding, wrong binding type, float MDD, nonfinite inputs, bool-as-number, noninteger underwater and drift from an original retained row. Finite adverse MDD `"1.01"` is retained as an input so existing gates alone determine its rejection.

All earlier covering R1/R2 tests also pass: missing/duplicate/foreign/failed/null/type/raw/value proof records, changed preliminary/inventory/portfolio/calibration evidence, missing held and unreflected-cash daily snapshots, legitimate eventless flat carry, verified intraday flat carry and original midnight funding/fill order. Read-only terminal-only mutation of the accepted original Spot account still rejects with the existing missing-snapshot error; its original bytes are unchanged.

| Artifact | SHA256 |
| --- | --- |
| `task-5-fix2-brief.md` | `b7b9621f47bcbe790ea8774e9fa841d66942e1ab560487bd101b5067f303cdce` |
| `task-5-fix1-rereview.md` | `d212d2ff21c23b6d66aad8024edb77e2e38e10f92d281cee22a064507d1ae866` |
| `task-5-fix2-tests.log` | `eb605c53abcd288a50197b8e89252999ba9bbc198a9a3012bb736a21360427b3` |
| `task-5-fix2-tests-final.log` | `752362161bf48ab982c4370ccf86ebf25ec89fedd34249ffa64fcd16389d6237` |
| `task-5-fix2-final-verification.py` | `dacbebea73b517e4fdbbbad83560933128130a24b3e00a7d6c88316ca9283050` |
| `task-5-fix2-final-verification.json` | `afa10eacfc1be44d29b198fda23f4eebed6271621778244b4ae099f8cb5f23cb` |
| `task-5-fix2-final-verification.log` | `d6550ec10082eda2818b405bcfa787b71696015ae2bab0da6be9ef13b1da60e1` |
| `task-5-fix2-proof-schema-examples.json` | `c93bc579fbac00abdaa01dc4f201c737166215d7ad08f51fa90d9c14712d41b6` |

## Self-review and remaining limits

Checked every `gate_values` and `continuous_mdd_from_account` call site: economic gates and proof recomputation now share the original exact string; the float metric remains only descriptive output. The actual fallback follows the same contract, not a separate rounded path. Exact input schema and inventory/proof binding preserve finite types and full raw precision without changing financial acceptance boundaries. R1/R2 implementations are untouched.

No known local blocker remains for T5-R3; closure requires root's scoped independent review against this final source. Real full-window 68+ accounts, actual calibration/profile replay, independent financial proof, adoption outcomes and future qualification remain unmeasured. No subagents, Coin test suite, full financial producer, native/private/account operation, HOME/UID/lock modification, original raw mutation or economic/spec/default change occurred. Native cases0, actual account-days0, NOT_QUALIFIED and prospective_alpha_provenfalse remain unchanged.
