# Spot actual-risk financial review

**PASS / APPROVE for the seven-account Spot actual-risk stage only.** All seven registered profiles are complete, known and audited; no material financial or causal mismatch was found. This accepts their measured evidence, including the failed core-permanent risk match. It does not approve a default change or global financial completion.

## Immutable identities

| Artifact | SHA-256 |
|---|---|
| risk-spot-project-early.json.gz | `42de6af1d1761ccf0260f81793e7746eb56eb08817c944e282f0f8479cced87f` |
| spot-project-calibration.json | `d574693fe94480c598dc1698b008147267227385ada31df82eab9498d38e7b2b` |
| spot-early-risk-completed.json | `25e1e4bc310c541ef0cba161bb250e591a3098502d3dddf373f179e936f2af76` |
| risk-spot-project-early.command.json | `07f18d2d45a37b5c267f1281891938fc7c1d019ac6ca9a9d75ddaf0f4e6d0ce2` |
| spot-project-calibration-proof.json | `ba6309e7718ed7fe14021753002f10b42f2271160cb5f507a5e4e0e2fd4c34ce` |
| accounts-manifest.json | `5dc7be50f8ca12a42359ab0019d7e41d8bdec8d975fa81b94547afcde58e56a0` |
| financial-audit-risk-spot-project-early.json | `5ada5a0f19f401db4d1b2e0a561c39daba08fd5d8ab3bdf19dc64240849e39a7` |
| financial-audit-risk-spot-project-early.command.json | `ed1c70e2c7c98c8febc8f2f54ef176b38bf7fa732fa26a3f7500251972c0d11d` |
| financial-audit-spot-unscaled-comparison.json | `7dbcf9eff66c804a2cddbdd45703735be5e308b9e1b78eb63b5c5fa0dc266455` |
| spot-actual-risk-sizing-proof.json | `cf728ca85710ad8a23b4527b3d13692918ccd3986d2e32646bd63640b32dffed` |
| spot_risk_actual_sizing_check.py | `9b9268f10ad0265e1a4bc534f4db6505d5b5c7145ecdc239625c9b00a621be23` |
| review_spot_actual_risk.py | `6bb8562f3b0ca9b0e56e98aa040e9f10d85de1ea23b7fdbebdb0f0a10a42f51b` |

All seven base accounts reside in the same compressed raw, SHA `42de6af1d1761ccf0260f81793e7746eb56eb08817c944e282f0f8479cced87f`. Streaming decompression reproduced command-receipt original JSON SHA `cc936f896274c0537c9d6f1226caa11fae63c22c0d8eaaff8917cf922f76761c`; compression did not relabel or alter evidence. Producer command exited 0 on frozen source `8ca002522fbdce531dcfbbb783ff4d152a7fd66c`, full Python `0df8c537ee8d47db6e841778e8e37eac847e1a0c1151e379440081b9473ae026`. Real immutable assessment source is `99fcf005d2cb15c13bb37322b65ab2863b19d65e`, Python `427f34ca3640cfa78f51173583af1d9c82f007baae155f3a992dcffb8171ad7b`. Neither adopted-tree execution nor an adopted-tree assessor was used.

The unchanged analysis99 source archive, economic metadata, complete-row validity and source-equivalence checks passed. The original four baseline scenes and all 28 unscaled accounts were consumed read-only; the exact project calibration document was rederived from their 731 daily training observations only. Its seven scales and bound unscaled-manifest SHA match exactly. Each actual risk account retains the same pre-cutoff actual daily/fill ledger fingerprint as its unscaled account. Common full and validation lengths remain 2,454 and 1,723 days. No legal profile is missing.

## Actual order and ownership causality

The earlier independent audit proves cash/BTC including BTC and USDT commissions, daily equity/FX, training prefix, risk journal chronology and core pools. Its journal checks alone were insufficient for sizing causality. The separate `spot_risk_actual_sizing_check.py` closes that gap without importing a producer: it reconstructs each sleeve from actual fills and durable allocation weights; independently applies net BTC fees and sale quantities; checks all 265,808 decision ownership snapshots and final positions; recalculates every accepted BUY from desired quote, actual free-cash/cap, allocated core/tactical cash, fixed scale, cent floor and minimum; and links all 540 filled BUY orders back to the corresponding accepted budget and its decision before execution.

Maximum sleeve reconstruction error is below `4e-28 BTC` (independent Decimal40 versus recorded Decimal28). The checker uses `1e-18 BTC` tolerance, far below one venue step. Every owned quantity is explained by actual allocated net fills; no retrospective multiplication by the risk scale occurs. Scale is exactly one before 2022-01-01 and fixed thereafter. SELL quantities are unchanged by this scale calculation. Source inspection of frozen `Policy.__call__`, `Lifecycle.prepare` and allocated-fill folding confirms the causal order: scale only changes new BUY quote budgets; durable fills determine holdings. Actual daily equity is rebuilt from those holdings and cash, not a scaled return curve.

Concrete post-cutoff records:

- ATR-stop scale `0.9972720085277638`: at `1644498002000`, desired BUY `11775.57` becomes `11743.44` USDT.
- Core-permanent scale `0.8338190387997291`: existing core `0.04359625286066249980792370706 BTC` remains at the first post-cutoff decision. A later core BUY at `1643061601800` changes `1631.51` to `1360.38` USDT.
- Core-slow scale `0.9584097975933019`: tactical BUY at `1644498002000` changes `9183.84` to `8801.88` USDT.

Both core modes retain the registered initial 20% cash pool and real independently compounding pool ledgers; the scale does not reset either pool or borrow between them. Across their recorded pool snapshots maximum cash discrepancy is below `6.4e-24 USDT`, BTC discrepancy below `2.4e-28 BTC`, and terminal total cash discrepancy below `1.7e-23 USDT`. BTC/USDT fees are charged to the actual order owner. Pool conservation passes. Consensus scale 1 is an actual rerun and matches the original unscaled base in every one of the six evidence groups.

## Validation outcomes

Validation is 2022-01-01 through 2026-09-19, using USDT daily returns. Registered bands are annual volatility ≤ `0.31491106970231053` and beta ≤ `0.3745835647337812`, derived from actual consensus validation volatility ×1.05 and beta +0.02. Gain is the difference in cumulative validation USDT returns, in percentage points, not annual CAGR, regression alpha or CNY gain.

| Profile | Fixed scale | Beta | Annual vol | Risk bands | Return gain (pp) | Annual descriptive alpha 95% interval |
|---|---:|---:|---:|---|---:|---|
| consensus | 1.0 | 0.354584 | 29.9915% | PASS | +0.0000 | [-10.4863%, 34.3975%] |
| trend-reentry | 0.9729026205883997 | 0.348201 | 29.4415% | PASS | -0.9328 | [-10.1401%, 33.8575%] |
| target-participation | 0.9103288241320875 | 0.342712 | 28.7787% | PASS | +11.4774 | [-8.1752%, 34.1562%] |
| atr-close | 1.0 | 0.358327 | 30.1210% | PASS | +1.8596 | [-10.3714%, 34.5376%] |
| atr-stop | 0.9972720085277638 | 0.337065 | 29.0160% | PASS | +27.7237 | [-6.2358%, 35.5419%] |
| core-permanent | 0.8338190387997291 | 0.393244 | 27.1776% | FAIL (beta) | -11.3025 | [-8.2635%, 26.3621%] |
| core-slow | 0.9584097975933019 | 0.351812 | 28.8885% | PASS | +0.9969 | [-9.4076%, 33.0016%] |

Trend-reentry has no positive matched return gain. Target-participation, atr-close, atr-stop and core-slow have positive conditional historical matched-return evidence under the registered rule. Core-permanent fails the beta band despite passing volatility and therefore cannot be called risk matched. These diagnostics do not override separate unscaled stress/selection gates or select a different winner.

The intervals are OLS daily intercept intervals against BTC/USDT, with fixed seven-lag Newey-West covariance, Bartlett weights, n/(n−2) correction, normal ±1.96 and arithmetic annualization ×365.25. They are descriptive, unadjusted for prior selection/research, and are not confidence intervals for return gain. Every interval contains zero. Independent matrix OLS/HAC7 and immutable scalar assessor results agree within `3.3306690738754696e-16`. CNY statistics use the same actual common daily path and prior-date FX; they do not substitute for the registered USDT match test.

Selected atr-stop actual calibrated base has full-account CNY CAGR `55.1966828%` and reported continuous proxy MDD `36.3670854%`. Original targets remain unchanged and unmet: Spot CAGR at least 100% and MDD at most 30%. A positive validation diagnostic is not target achievement or prospective alpha proof.

## Limits and remaining gates

This review reads immutable completed outputs and existing public inputs; it did not run a financial producer, download data, edit product/frozen sources or caches, access a private account or Coin State, or spawn subagents. Full daily ledger/statistics and actual allocated-fill sizing were independently checked. The continuous intraday OHLC proxy was **not independently replayed**. Archive claims/hashes were checked through the strict row gates; archived backup contents were not reopened here. Public daily proxies are not native execution evidence. Native verification and actual account-days remain zero, and all studied history remains research contaminated.

Global Coin, applicable combination and sensitivity evidence, unified full-matrix final assessment, exact five-account adopted-source bridge, and final adoption review remain pending. This Spot-stage approval does not weaken those gates.
