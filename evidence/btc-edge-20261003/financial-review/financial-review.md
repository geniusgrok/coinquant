# Independent final financial review

**Financial PASS.** All 71 registered accounts and the separate five canonical Spot cases reconcile. No accounting, source, input, original-evidence, or adoption-gate mismatch remains. This accepts the evidence and registered selection; it does not meet the original economic targets or qualify native execution.

Machine proof: `/workspace/scratch/btc-alpha-beta-edge-20261003/assessment/independent-financial-review-proof.json` SHA256 `50dc293c8225027f2bfa49508cdd058f2ccc4a44ebb4976f3b41b206d048aefc`.
Full independent evidence index: `financial-proof.json` SHA256 `596f509d8a0ec0025e12dffcc5b8497fb5a3f65204f610e6c6448c99af1a879c`.

Preliminary SHA256 `b54a0324570d2b2a21ed7450b3f4a905887408ae31a115a180cc8743911aa6b3`; inventory `c3f4e9d3bee09bac4242660aafaed51e767d849dae5549343af7176c62226e74`. Exactly 46 Spot + 25 Coin accounts in 53 original raw files; pending/blocking/rejected lists are empty. The additional five canonical cases are separate source-bridge measurements.

## Independence and coverage

The standalone recompute.py reads original fills, commissions, funding/income, signed quantities, average-cost entry, daily wallet records, official market ZIPs, and prior-day FX. It independently reconstructs every closing wallet and daily equity observation, checks no external flows, and derives all report metrics, including daily/validation returns, beta, HAC7 intercept covariance, capture, calendar attribution, ES99, underwater duration and producer-specific CAGR. Original snapshots are admitted to curve encoding only after ledger reconstruction; sub-1e-8 original Decimal-ledger rounding follows the frozen monetary convention. Acceptance gates use exact original finite Decimal MDD strings, without float conversion/tolerance. Continuous MDD is the original producer’s OHLC/minute-envelope proxy, bound to all original fields; no independent continuous second-engine replay is claimed.

categories.py derives profiles, achieved risk, every adoption threshold/ranking, and all six actual independently funded portfolio sums. Only after derivation does it import review_expectations/verify_review_value to compare exact typed records; it never generates evidence by dumping expected values. The serialized final proof was verified once; financial calculations were not replayed. All complete accounts have 2,454 UTC daily closes and all registered 795 sessions, except Spot outage’s 789. Every session and write clock was checked. Sampling additionally retains first/last/every97th session and all exceptional/unknown/constraint/reason cases; journals retain every exceptional feature/sizing event plus deterministic periodic ownership records.

Independent categories: {'source_and_inputs': 124, 'original_accounting': 71, 'baseline_six_groups': 10, 'calibration_and_actual_risk': 16, 'adoption_gates': 8, 'actual_budget_aggregation': 6}. Journal events scanned: 2,949,304; Coin decision scales: 700,045; unchanged Coin committed/topup targets: 18,090; pre-cutoff daily identities: 5,848. Reused scoped software/controller/forward reviews remain distinct from this financial evidence.

## Sources and provenance

- spot: original HEAD `74bd6e035e36531c517029077c1a9e2e5ec44516`, full Python `f2d6c3e73c2acb7b328a7a0e2678bb95ceb77d8a17a46139abfe8b357befdbf6`; 53 protected archived files/modes independently match original/current execution bytes. Archive `/workspace/btc-alpha-beta-improve/task-artifacts/spotquant-reviewed-financial-source.tar.gz` SHA `c19ce4bab5e0e188b7680516475e77f831f586dda857055c69bbe26b37db0d64`.
- perp: original HEAD `37061a7f588f97cc16852551cab6cd2e51acb920`, full Python `ba63895131db566e708a5c96cde4504beace39fa0bdd54881d039dd5b8ef4c50`; 59 protected archived files/modes independently match original/current execution bytes. Archive `/workspace/btc-alpha-beta-improve/task-artifacts/coinquant-reviewed-financial-source.tar.gz` SHA `6695bd6a0fccdc9ae86924012cb035a95729ba16ee53a39215845893f931ccf7`.

Metadata-only dirty PROJECT_STATE/HANDOFF files do not relabel financial source. Both own edge spec/protocol contracts, original meter/source identities, schedule, FX, feature inputs, profile bytes, fixed budgets and offsets remain bound. Original Coin’s 20 native runtime files match accepted incumbent bytes; its forward reader remains standalone. No source/default promotion occurred in this review.

The provenance supplement binds 5,333 actual files and 11 controller phase receipts, including both original failed phases and all durable releases. Initial SQLITE_FULL output/exit evidence remains failed and retained. Exactly one pre-outcome resource recovery switched task TMPDIR to overlay storage and cap1/project, with UID/HOME and locks unchanged. First preparation/helper hashes are historical: later separately reviewed fixes are bound by the actual freeze; preserved pre-controller-fix1 files match the old preparation hashes. No controller tests were repeated.

The first post-risk assessment failed only because the -60s original account consumed the additional 2026-08-01 official aggTrades archive. The raw account was preserved. The assessment-only union retains 1,596 original read-only hardlinks plus the exact original consumed ZIP/CHECKSUM pair, retrieved HTTP200 from official URLs and matching its older raw receipt. ZIP SHA `6bfdb219726ab774c25ae782e4e8f4a5e4dbc69b807f1b7c200e71586d69b6fb`; CHECKSUM `1283c92250f64ee7db709a8e1952f682fad1ec3131e9ec6d9690aaa52a6ecec0`. Correction report SHA `9445a934a22a36e5803544259aa900debdd97e03a2da5318ebaef804c1a8b162`. Final evaluation must use the same union path. This restored verification input, not prices, source or financial accounts.

All approved first-failure reviews and scoped corrections remain retained, including source archive mode verification, controller C1–C4/resource-recovery, canonical malformed payload R1, and the single corrected partial-entry fixture. This review ran no producers, unit/fullsuite tests, network requests, native/account/private actions, public preflights, initialization or export.

## Actual economics and selection

| Project / base account | CNY CAGR | Original continuous proxy MDD | Worst CNY day | ES99 loss | Underwater days | Fees USDT | Funding paid USDT |
|---|---:|---:|---:|---:|---:|---:|---:|
| spot atr-stop | 55.218033% | 36.412249% | -15.802886% | 7.188503% | 713 | 1521.505057 | 0.000000 |
| spot crowding-interaction | 56.598116% | 36.412249% | -15.802886% | 7.133672% | 713 | 1108.006338 | 0.000000 |
| perp incumbent | 119.228356% | 44.105079% | -21.221423% | 10.849811% | 319 | 15290.544999 | 21733.156123 |

| Candidate | Eligible | Rejected gates | Validation beta / vol | Validation cumulative USDT return gain |
|---|---|---|---|---:|
| spot exit-confirm | False | base:cagr, base:mdd, fee150:cagr, fee150:mdd, slip2:cagr, outage:cagr, outage:mdd, base_improvement, es99, actual_validation | 0.169576 / 18.929791% | -1.058092 |
| spot stop-budget | False | base:cagr, fee150:cagr, slip2:cagr, outage:cagr, base_improvement, underwater, actual_validation | 0.000106 / 0.006071% | -1.434241 |
| spot crowding-interaction | True | none | 0.300300 / 27.350670% | 0.149169 |
| perp quality-budget | False | base:cagr, fees-x1.5:cagr, read-400ms:cagr, trigger-slip:cagr, base_improvement, actual_risk_bands | 0.267272 / 54.455273% | 3.269783 |
| perp cost-horizon | False | fees-x1.5:cagr, read-400ms:cagr, trigger-slip:cagr, base_improvement, actual_risk_bands | 0.290854 / 59.415752% | 1.384425 |
| perp crowding-interaction | False | base_improvement, actual_validation | 0.268223 / 51.564559% | -0.112399 |

Training independently uses exactly 731 2020–2021 USDT observations, slicing before statistics. Spot scales are ATR1, exit-confirm0.914338712559913, stop-budget1, crowding1; Coin’s four profiles are1. The raw base hashes and own-project schema match actual consumed profile bytes. Risk changes only new order sizing from 2022-01-01; held targets remain unchanged and no curve is multiplied. Scale0 is permitted by the frozen finite guards; it was not a fitted actual scale and no optional boundary test was run. The 1.05 volatility/+0.02 beta conditions are upper bands, not risk equality. Both Coin quality-budget and cost-horizon fail actual risk bands despite positive validation gain.

Selection is Spot crowding-interaction and Coin incumbent. Only Spot crowding passes all gates; no ALL-components combination is applicable. The pre-outcome selection ruling ranks eligible singles by worst-stress CAGR/registered order, then a complete eligible ALL-components combination may supersede the best single even with lower worst-stress CAGR. No global single-plus-combination maximum is claimed. All losing cases remain legitimate completed financial results.

**Material interpretation limit:** Across registered Spot decision journals, 689 crowding proposals retained the original quote and 200 were blocked for missing causal features; no triple-condition halving event occurred. The observed historical gain therefore comes from unavailable-input entry blocking on these measured paths and does not establish profitability of the halving branch. The reviewed shared predicate and five measured source comparisons establish implementation/equivalence; synthetic branch tests are separately retained. Missing features affect new BUY only; exits/protection are preserved by the reviewed code and bridge.

| Selected base account | Full-window BTC beta | Annualized residual intercept | HAC7 descriptive normal95 interval | Up / down arithmetic capture |
|---|---:|---:|---|---|
| spot crowding-interaction | 0.368539 | 31.673214% | [11.127205%, 52.219224%] | 0.442677 / 0.365403 |
| perp incumbent | 0.275848 | 82.079264% | [36.371319%, 127.787209%] | 0.380622 / 0.167016 |

These intercepts and intervals are descriptive and selection-contaminated. They do not establish clean out-of-sample or prospective alpha. The validation-period results and full-window results are separately retained in every independent account checkpoint.

## Actual two-account budgets

| Selection | Spot/Coin CNY | Daily CAGR | Daily joint MDD | Worst CNY day | BTC beta | Return correlation |
|---|---|---:|---:|---:|---:|---:|
| current_default | 2500/7500 | 123.216197% | 24.812878% | -20.338976% | 0.292277 | 0.386629 |
| current_default | 5000/5000 | 115.485112% | 24.633856% | -19.620584% | 0.306728 | 0.389976 |
| current_default | 7500/2500 | 102.823307% | 25.799495% | -17.848760% | 0.329699 | 0.396510 |
| selected | 2500/7500 | 123.152656% | 24.812878% | -20.338976% | 0.292123 | 0.371057 |
| selected | 5000/5000 | 115.329327% | 24.633856% | -19.620584% | 0.306338 | 0.373072 |
| selected | 7500/2500 | 102.940617% | 25.799495% | -17.848760% | 0.325909 | 0.384152 |

Each row sums two genuine separately funded accounts with CNY10000 total, zero transfers/additions/rebalancing, and its own fees, minimum notionals, rounding and realized paths. Selected Spot’s additional three accounts were conditionally registered with 54 exact bindings and actually completed. 5000/5000 is the fixed neutral reference. The other splits are robustness evidence, not allocation recommendations or a selected historical optimum. Daily joint MDD is not independent continuous joint MDD.

## Separate canonical acceptance and remaining binding

All five canonical Spot cases (base, fee150, slip2, outage, unity-risk-base) independently reconcile in financial/fills/daily/ownership/operating/remaining_original_fields groups. Case proof SHA `44bd6e504f7e33b3e702f9bfe28a8084f643f9dcf4ce1e94c1e376658939f8a0`. New source is HEAD `609606d9c0e0ad8d3c3038b329c9c4ab6d1b9629` / Python `b81f1bfee086e875cbf8ff22a67b2cfdff419130a7918a6ce8754b2e9e2936c5`, distinct from original74bd/Pythonf2d6. The five-account template preserves both identities and command receipts. See spot-canonical-five-financial-review.md and spot-canonical-bridge-template.json; Coin’s unchanged runtime proof/template is separate.

Final report bytes and later metadata/current-source HEAD are not yet available. The same reviewer may bind those final identities to these already-completed calculations and protected byte maps, without rerunning the 71 or five cases. This report itself authorizes no source edits, native execution, export or initialization.

## Preserved review-calculation corrections

The first account script rejected legitimate resting protective allocations, then a null flat sleeve; each initial script/log remains and only incomplete portions resumed, reusing all completed checkpoints. The first canonical attempt used an incorrect archive subdirectory before any case calculation; the path was corrected to the actual bound archive. Supplement failures retained a null suffix-filter handling error and a historical preparation path mismatch; the latter was resolved to preserved pre-fix helper bytes, not by relaxing source hashes. These were review-script assumptions, not producer/account mismatches. Passing account/canonical calculations and six categories were not rerun.

Both original targets remain **NOT_MET**: Spot56.598116% CAGR/36.412249% proxy MDD falls short of100%/30%; Coin119.228356% CAGR falls short of150% (44.105079% proxy MDD remains below50%). Native cases0, actual account-days0, prospective_alpha_proven=false, native qualification **NOT_QUALIFIED**. Continuous OHLC and minute-envelope paths, 29 missing official mark minutes, prior-day FX/USD-par conventions, missing-feature assumptions, confirmed-stop replacement gaps and unresolved native protection remain disclosed.
