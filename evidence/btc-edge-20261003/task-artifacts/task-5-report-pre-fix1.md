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
