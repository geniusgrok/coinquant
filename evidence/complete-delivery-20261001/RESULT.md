# Complete perpetual account delivery — 2026-10-01

Frozen execution source: `995d0530889d8b609f41218b6904ff55499fd578`, Python SHA-256 `5a1497a18004fce43827c68d80673300004b0cbb505d5106c4ee29cc63c995b3`. Exclusive terminal derivation and actual-budget source: `3213cddb904b745193c5a27c06c42ec3a3ae2f93`, Python SHA-256 `782333a4bea85ac7f1a86050a28072eef2dda77b53ea8dd1b5a00cf42a69331a`.

All 28 accounts completed the exact 795 frozen real-session/Lifecycle invocations. Every cash-ledger/fill audit passed, every account is known within the registered proxy bounds, unresolved execution is zero, and all 2,454 daily records are present. Daily USDT/CNY equity, signed/gross BTC exposure, costs, fills, funding, session reports and checksummed market/print inputs are retained. These historical proxy fills are not native exchange execution proof.

## Mechanical development decision

**Retain SX60+DFII10, primary 7.5 / macro 3.6.** No replacement passes all four matched scenarios and the registered improvement rule. Base cost-net CAGR is 119.2283555%, continuous full-account MDD 44.1050788%, final CNY 1,951,753.8083. The original 150% CAGR goal remains unmet by 30.7716445 percentage points. Native qualification remains NOT_QUALIFIED and no trading/account operation was performed.

Percentages below use the explicitly exclusive economic window. MDD is continuous account envelope MDD, not daily chart drawdown.

| Candidate | Base CAGR | Fee x1.5 CAGR | 400ms CAGR | Trigger-slip CAGR | Base MDD | Adoption |
|---|---:|---:|---:|---:|---:|---|
| incumbent | 119.2284% | 128.5405% | 104.7730% | 124.9365% | 44.1051% | retained |
| tail-sizing | 121.0656% | 121.4892% | 100.8996% | 118.7038% | 41.9424% | rejected |
| no-macro | 120.7362% | 130.8055% | 105.9188% | 120.2264% | 44.2542% | rejected |
| slow-trend | 92.5071% | 94.0360% | 76.9477% | 91.1904% | 51.9246% | rejected |
| funding-filter | 115.5484% | 115.3211% | 94.8578% | 112.4670% | 44.0971% | rejected |
| basis-filter | 119.1832% | 127.9527% | 104.3711% | 118.1323% | 44.1051% | rejected |
| conditional-short | 119.7369% | 116.8548% | 102.3146% | 116.9457% | 67.2851% | rejected |

Exact per-scenario rejection predicates, audits and feature coverage are in [perp-exclusive-summary.json](perp-exclusive-summary.json). Tail sizing improves base return and drawdown, but fails the matched fee, latency and trigger-slip CAGR tolerance. No-macro is attribution-only and also fails trigger-slip matching. Slow trend exceeds 50% MDD in every scenario and loses return. Funding filtering loses more than the allowed return in every scenario. Basis filtering fails improvement and trigger-slip matching. Conditional shorts produce 65.33–67.62% MDD.

## Causality and terminal convention

Funding entry input is the latest settled rate with settlement <= decision minus 8 hours, and lag-relative age <8 hours. Basis requires the immediately previous completed daily close publication on the current UTC calendar date, availability <= decision and age <24 hours. Unpublished/missing input blocks fresh candidate longs. Funding feature queries had no missing/stale observations; basis had 48 unavailable queries in base/fee/slip and 36 in the 400ms scenario, all blocked. These counts describe actual entry queries, not all calendar days.

Original `perp-accounts.json` is immutable source995 output (55,218,104 bytes, SHA-256 `55aa8ba0d8e54d572907a5d57cc557face20a0ce6666692d526df37387585423`). Runtime intervals naturally settle start < funding <= advance-end. At the research terminal boundary, this includes four slow-trend funding debits outside the registered exclusive window.

`perp-exclusive-accounts.json` is separately derived (55,230,558 bytes, SHA-256 `15dd7bfc242d52bf692663179cd1e3867418f8b55a4cad0894d253a8b296f00a`). It removes only exact-END slow-trend debits of 2.9647344 / 3.1271856 / 1.68136992 / 2.82665088 USDT. All trades precede END, no stop/order follows the settlement, every maximum drawdown predates END, and removing these debits increases terminal wealth without changing the historical maximum. All 28 independent derived audits pass; the selection remains incumbent. The other 24 financial rows are unchanged. Added candidate/scenario/initial-CNY metadata binds each row to its canonical original-row SHA. The original execution source remains995; derivation source3213 is explicit.

Budget source3213 excludes only terminal research funding while preserving ordinary settlement intervals and closing valuation. Production funding behavior, protection, strategy, risk and price fallback stay unchanged.

## Verification and reproduction

346 offline tests passed (4.366s); independent review approved the variants, terminal derivation, funding formula checks and default-equivalence proof. [perp-budget-equivalence.json](perp-budget-equivalence.json) records 28 cases x3 real sessions: all 5,086 nonidentity/default fields match old995 exactly, including two incumbent replay fills. The two small original comparison outputs are archived for independent verification. This is a short deterministic equivalence check, not a relabelled full economic run.

Full replay:
```sh
python -m research.complete_perp --crowding evidence/complete-delivery-20261001/crowding-complete.json --restore-prints --out /path/to/new-perp-accounts.json
```

Explicit terminal derivation:
```sh
python -m research.exclusive_terminal --accounts evidence/complete-delivery-20261001/perp-accounts.json --out /path/to/new-exclusive-accounts.json
```

Independent budget replay (actual CNY 2,500 / 5,000 / 7,500, no transfers or curve scaling):
```sh
python -m research.complete_perp --crowding evidence/complete-delivery-20261001/crowding-complete.json --restore-prints --portfolio-budgets --out /path/to/new-portfolio-perp-accounts.json
```

Keep original inputs/schedule/FX and use new exclusive output paths. `--initial-cny` defaults to 10,000 and initializes wallet, initial metric peak, CAGR and audit from that capital. Budget results are directly indexed by capital, with explicit incumbent/base labels. No selected-budget replay is needed because all substitutes are rejected. Optional selected-budget support keeps separate `selected_results` and candidate metadata when future registered selection requires it.

All three actual-budget accounts completed795 sessions. Their independent own-capital cash audits, exactfrozen starts, matching market/FX/crowding/protocol/schedule inputs, complete2454 daily records and302 actually marked held closing days passed. Each is flat at END with all execution/cashflow times strictly before END; unresolved count is zero. See [portfolio-perp-summary.json](portfolio-perp-summary.json). Unified cross-account attribution, daily controls and independent fixed-capital combinations are published in [Spotquant ALPHA_BETA.md](https://github.com/geniusgrok/spotquant/blob/main/evidence/complete-delivery-20261001/ALPHA_BETA.md), with source/candidate-matched endpoint and budget checks. CAGR alone does not establish prospective alpha.


## Actual independent budget results

Budget source3213 remained frozen throughout command93244, which exited0. Fullraw is5,872,835 bytes, SHA-256 `eddf564178aad45efd9a3aac20e02fc757a0196008f4c083963621ac43a1bd8a`. No money transferred across accounts and no curve rescaling occurred.

| Initial CNY | Final CNY | Net CAGR | Continuous MDD | Fills |
|---:|---:|---:|---:|---:|
| 2500 | 1,013,388.5291 | 144.42114% | 44.09001% | 932 |
| 5000 | 1,642,401.4744 | 136.88966% | 44.10825% | 1367 |
| 7500 | 2,154,872.1447 | 132.21564% | 44.10493% | 1751 |

The smaller-capital paths are not proportional to the10,000CNY path. Minimum quantities, finite fill/sizing cycles and quantity limits make actual account outcomes depend on capital; even the7,500CNY terminal wealth exceeds the10,000CNY terminal wealth. These are fixed registered capital-allocation controls. They neither replace the10,000CNY selection criterion nor establish alpha. Matching candidate names and actual capital amounts are mandatory when constructing joint curves.
