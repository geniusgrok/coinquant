# Coin actual five-account risk financial review — BLOCKED

Verdict: **NOT APPROVED**. The actual five-account run completed, and the independent financial and sizing checks passed, but the mandatory incumbent unity control failed exact operating evidence equality. No clock, status, reason, cycle, trace or other field is excluded to obtain a pass. Global acceptance, final sensitivity review, source bridge and adoption remain pending.

## Immutable evidence

| Evidence | SHA-256 |
|---|---|
| `/workspace/scratch/alpha-beta-next/risk-perp.json.gz` | `3b958b2e92d8aefcf7b9f073a3916c325420a546cf7652203ce6692be5ee2446` |
| `/workspace/scratch/alpha-beta-next/risk-perp.command.json` | `6177756a15cc19007ea7c14db7acdf84a02967512555c71d4272e26d495196d9` |
| `/workspace/scratch/alpha-beta-next/registered-risk.json` | `6854ef5fcfebb9e746c7a586f2122c7360d21ed2a40d573c73b8f6b8fee2bcfd` |
| `/workspace/scratch/alpha-beta-next/registered-risk.command.json` | `152415cb310de6ec4eb9e6433c7cc4ce4a4ab70f40c0f0201b3e0ffd192ac0d5` |
| `/workspace/scratch/alpha-beta-next/registered-calibration.json` | `ed8c99295e71386a7cef300f7d101ea941e5a7a0147bc9038012d6cc58e23821` |
| `/workspace/scratch/alpha-beta-next/spot-project-calibration.json` | `d574693fe94480c598dc1698b008147267227385ada31df82eab9498d38e7b2b` |
| `/workspace/btc-alpha-beta-next/review/financial-audit-risk-perp.json` | `e857608457e91996d07d40863eab71e2220c4bad6accd1158c668995cd6fdc47` |
| `/workspace/btc-alpha-beta-next/review/financial-audit-risk-perp.command.json` | `d6a562d3f8abef7bfffad2c28a046e06898cdacf5356aad81a64542e48de576e` |
| `/workspace/btc-alpha-beta-next/review/coin-actual-risk-strict-first-attempt.log` | `f2f5ba7f47b1fa92f3b6d63a6819e01b9ef1f969d9ffb1ecb24873875eab5ec3` |
| `/workspace/btc-alpha-beta-next/review/coin-actual-risk-unity-operating-differences.json` | `998bd08ff4c583306ee1004f23e891664d9e7f0883b224dd96ab5133eaf8b65b` |
| `/workspace/btc-alpha-beta-next/review/coin-risk-incumbent-http-journal-diagnostic.json` | `f47b06382e91d64e790bd977ba2fef952239888a4be1ca3e25e1799462cca3b4` |
| `/workspace/btc-alpha-beta-next/review/coin-actual-risk-financial-diagnostic-blocked.json` | `cb77d177ae7581f8869c33d2d66d0aedf37ba7233b48f36944e5ad4f3ce46a99` |
| `/workspace/btc-alpha-beta-next/review/diagnose_coin_actual_risk_financial_blocked.py` | `2f3f6e05b7b16432564336020c2a8507ca6f3f4939f8624b2c1c9ba23070d097` |

Producer receipt exit 0 binds the actual raw, source acedaa43ca94223f24e2fe11851bbef74e032a69, start 10:18:01.579383 UTC and elapsed 6669.076929884002 seconds. Immutable analysis99 consumes these measured originals. Exact source, public market, FX, schedule, calibration and verification-context bindings are retained in the diagnostic proof; source identities were not overridden. Original unscaled20 remains bf1d167979f4bb3d15925f0bcaf5337bd1cc0a17523628b3af0599875dc5a7c1.

## Blocking exact comparison

Fresh-entry, atr-trail and single-topup unity profiles match all six original groups exactly. Incumbent matches financial, fills, daily, ownership and remaining-original-fields groups, but its operating hash changes from `3628c041d33b67da9e38cbeeefc39c8f16b6c529f368600c73f9e19f0643e36e` to `92528adb91eff3d6602d43d7926974ab970d9b98d48d7e6e37296380b9718614`. The exact diff contains ten changed/missing leaves, all in sessions 31 and 38; all other operating fields match.

- Session 31: flat actions 39→40; the old deadline and closing-settled reasons disappear, and one HTTP-unresolved reason appears. Fresh observations remain 40.
- Session 38: cycles 39→40, consumed actions 40→38, fresh observations 40→39; one HTTP-unresolved, one bounded-deadline and one closing-settled reason appear.
- Both actual HTTP blocks occur on cycle sequence 1, at session start +600 ms: 1585486800600 and 1587355200600. They are recorded as Unknown; HTTP status, native code, request path and originating URL are not persisted.

Frozen source supports the suspected acquisition failure path: RollingPrints._load propagates non-404 HTTPError from official public CHECKSUM/ZIP downloads; Binance._request catches HTTPError raised inside the historical transport and classifies it as a Binance HTTP outcome. SessionExchange uses a virtual clock, so wall-clock download delay alone does not explain these observations. The raw journal proves the HTTP classification and changed poll outcomes, but does not uniquely identify the remote status/URL. An exact historical network diagnosis is therefore unavailable from this artifact alone. This is not a basis to normalize away the control failure.

## Financial and causal checks (diagnostic, not stage acceptance)

All five actual accounts have 795 completed sessions, known paths, no terminal failure and no unresolved execution. Independent Decimal signed-position/WAC reconstruction checks realized P&L, commissions, cash, positions, public funding rates and prior completed marks with held quantities; funding is strictly before the exclusive END. Public funding, commission and quantity differences are zero; maximum absolute terminal CNY rounding residual is below 5.26e-21. Daily USD/CNY calculations and NumPy OLS/HAC comparisons differ by at most 8.89e-16.

All five 731-day training ledger fingerprints and training statistics match the original unscaled accounts. The global12 profile document equals the previously derived past-only calibration, including its exact Spot7 subset. All four unity scales remain 1.0; compression remains 0.7997705584944133. No outcome-dependent recalibration is applied.

| Actual profile | Validation beta | Annual volatility | Meets beta/vol caps | Cumulative USDT return gain vs incumbent (percentage points) |
|---|---:|---:|---|---:|
| incumbent/base | 0.268369888 | 51.598262% | True | 0.000000 |
| fresh-entry/base | 0.019064250 | 7.622345% | True | -900.568356 |
| atr-trail/base | 0.329082863 | 64.281925% | False | 410.583547 |
| compression-breakout/base | 0.356925108 | 58.408218% | False | -835.561867 |
| single-topup/base | 0.221105052 | 45.545520% | True | -145.584545 |

Caps are incumbent beta +0.02 and incumbent volatility ×1.05, on the actual 1723-day 2022+ returns. Return gain is cumulative, not annualized. Compression fails both caps despite reduced sizing; atr-trail also fails. Fresh-entry and single-topup satisfy these risk caps but have negative cumulative return gains. These are descriptive diagnostics relative to an economically identical, operationally invalid control.

Independent actual sizing reconstruction covers every recorded owned-quantity decision and all post-cutoff new-entry demands:
- incumbent/base: 29253 quantity snapshots, 62 post-cutoff entry demands, 1511 BUY fills linked to recorded IOC plans.
- fresh-entry/base: 30074 quantity snapshots, 44 post-cutoff entry demands, 79 BUY fills linked to recorded IOC plans.
- atr-trail/base: 29202 quantity snapshots, 62 post-cutoff entry demands, 700 BUY fills linked to recorded IOC plans.
- compression-breakout/base: 28831 quantity snapshots, 78 post-cutoff entry demands, 788 BUY fills linked to recorded IOC plans.
- single-topup/base: 29450 quantity snapshots, 62 post-cutoff entry demands, 626 BUY fills linked to recorded IOC plans.

The reconstruction uses completed public daily observations, fixed 7.5/3.6 budgets, native macro stop cap, actual sizing capital and accepted quantities. Maximum requested-quantity rounding residual is below 3.29e-26 BTC. Owned quantities change only through actual fills; compression scaling modifies new demand rather than retroactively scaling holdings or return curves. Fixed-scale multiplication can be clipped by the separate macro stop cap, so not every accepted quantity falls proportionally.

HAC uses lag 7, Bartlett weights and normal 95% descriptive intervals; no prospective or selection-adjusted alpha claim follows. Exact registered Coin CAGR uses 365.2425 days; common daily statistics use 365.25. Hindsight-bounded mark proxies remain disclosed; the continuous intraday path was not independently replayed. Native cases and actual account days remain zero.

The original strict checker script and failed first-attempt log are preserved. The separate diagnostic explicitly records stage_approved=false and the rejected unity control; it does not replace or repair either raw data or registered invalid assessment. Any repair requires fresh authorized actual evidence and unchanged exact gates, followed by a separately bound review.
