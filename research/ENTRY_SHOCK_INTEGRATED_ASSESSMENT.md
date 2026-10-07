# Entry-shock deferral: integrated selected-window assessment

This follows the four completed fixed baseline/deferral pairs and the separately committed `ENTRY_SHOCK_INTEGRATED_STRESS_FREEZE.md`. It preserves every earlier result: 2020Q1/2021Q2 met their narrow mechanical and local economic screens; 2020Q3/2023Q1 failed the subsequently registered **no adverse quarter wealth or ES5** screen. That latter screen is a conservative research guideline, **not** a user instruction that each window must win. The user's original material-benefit objective and the unchanged Coin 150% CAGR / <50% drawdown reference remain separate. The archived `research/replacement-spec.json` is a stronger, pre-existing *default replacement research policy*: its return route requires continuous cost-net CNY CAGR at least 1.10× baseline without increasing continuous MDD; its risk route requires at least 0.95× baseline CAGR and at most 0.80× baseline MDD. It also requires stress and cross-era evidence. Those thresholds are research admission rules, not literal user per-quarter commands; no independent quarter comparison can be relabelled a pass of that policy or of native execution.

## Same initial CNY capital, four independent quarters

Each wallet began cold with **10,000 CNY** and the exact original manual-start sequence for its quarter. USDT ingress differs with point-in-time FX, so the comparable local return difference is the CNY percentage-point change. These are **four separate accounts**, not a continuous wealth curve, annual CAGR or out-of-sample sample.

| Quarter | Baseline → defer CNY net return | Change | Baseline → defer path MDD | Baseline → defer daily USDT ES5 loss | Local final USDT difference |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2020Q1 | 68.6967% → 74.2351% | **+5.5384 pp** | 40.5516% → 40.5516% | 8.4392% → 8.4392% | +78.09 |
| 2020Q3 | 101.2484% → 101.6261% | **+0.3777 pp** | 15.1889% → 15.1889% | 1.5159% → 1.5260% | +5.55 |
| 2021Q2 | −4.5576% → −1.6243% | **+2.9333 pp** | 5.9623% → 3.0721% | 0.5963% → 0.0000% | +45.47 |
| 2023Q1 | 211.2163% → 210.8488% | **−0.3675 pp** | 25.0191% → 25.0191% | 7.0667% → 7.3820% | −5.35 |

| Quarter | Fee change, USDT | Funding paid change, USDT | Turnover change, USDT | Held-time change |
| --- | ---: | ---: | ---: | ---: |
| 2020Q1 | −3.86 | −0.59 | −5,143 | −4.09 h |
| 2020Q3 | +0.05 | −0.37 | +65 | −38.00 h |
| 2021Q2 | −1.34 | −0.09 | −1,790 | −5.05 h |
| 2023Q1 | +2.67 | −0.72 | +3,561 | −119.99 h |

For a **descriptive equal-capital score only**, the four return changes add to +8.4818 percentage points, or +2.1205 points per independent 10,000-CNY quarter. The first two completed pairs contribute **95.7% of positive** return changes. Omitting the strongest quarter leaves +2.9435 points across the other three, while the two later-reentry quarters nearly cancel at about +0.0102 points. The worst selected-quarter MDD remains 40.5516% and worst sampled daily ES5 remains 8.4392% in both columns, but 2020Q3 and 2023Q1 individually worsen ES5. This is a potentially useful *conditional* local beta mechanism, with concentrated early benefits and no demonstrated continuous-path or current-era robustness. It cannot be converted into the 119.23% historical CAGR or the 150% target.

## Why delayed sizing expanded, and what it costs

The archived original producer's macro entry preview explicitly caps `quantity × (entry price − stop price)` at **3% of sizing capital**, before fees, funding or any stop gap. It also checks available wallet, exchange notional cap, 20×-eligible margin and visible IOC capacity. Current `main` retains that 3% macro geometry; its optional user-configured total stop budget can include fees and adverse slip but is not a default strategy dose. In the paired 2023Q1 wallets, pre-entry cash was the same, and modeled stop-price loss was **2.990% versus 2.985% of that cash**. Delaying entry while retaining the same stop narrowed the per-BTC distance, so the original formula increased units **2.42×**. Actual entry notional rose from roughly **0.48× to 1.11× wallet cash**, still below the venue/margin ceiling. The same relationship appears in 2020Q3 at about 3% modeled stop-price loss. This is an intended consequence of the original loss-to-stop sizing rule, **not** a quantity reconciliation defect, a new leverage setting, or a proven all-in loss bound. More units raise commission and exposure to a given per-BTC stop gap. No risk preference, threshold or account configuration is changed here.

The first two windows avoid their shocked macro trades rather than buy later. In 2020Q3 the rule buys again after about 38 hours, yielding only +5.55 USDT and a slight ES5 increase; roughly **0.98%** additional adverse price on its changed macro BUY or SELL would erase that wallet gain under fixed quantity and path. In 2023Q1 it buys again after about 120 hours and hits the same modeled stop. Its macro net falls 1.88 USDT; the subsequent primary winner still enters but with slightly less quantity and contributes 3.47 USDT less. About **0.17%** better candidate macro execution would be needed merely to equal its baseline final cash, holding the rest fixed. These are arithmetic sensitivities, not executable bid/depth, stop-gap bounds or calibration.

## One registered fee stress, then stop

The frozen `fees-x1.5` scenario was run **only** for the most cost-sensitive 2023Q1 pair, using the same original producer, sourced quarter, 26 actual manual starts and separate audited cold wallets. This spent the spec's two-wallet stress allowance. Both results are complete, with identical input digests, zero pending intents, and `native_verified=false`.

| 2023Q1 fee scenario | Baseline CNY return | Defer CNY return | Defer minus baseline final USDT | Daily USDT ES5 loss, baseline → defer | Path MDD |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original fee | 211.2163% | 210.8488% | −5.35 | 7.0667% → 7.3820% | 25.0191% both |
| 1.5× fee | 208.1539% | 207.6317% | **−7.60** | 7.0717% → 7.3970% | 25.0666% both |

The fee-stressed deferred macro still buys over twice the baseline units; its incremental fee cost grows from **2.67 to 4.01 USDT** versus its matching baseline. Thus the adverse local cost/tail interaction persists and strengthens. This is **not** the archived doubled-fee-and-slippage adoption stress, not an estimate of native stop gaps, and not a stress result for the other three quarters. It does not turn the descriptive four-quarter score into a continuous stress pass.

**Integrated decision:** do not call the mechanism worthless from one −5.35-USDT window: the selected equal-capital quarters show positive local net effect, and conditional entry deferral is distinct from the earlier failed blanket no-macro rule. Equally, do not call the local no-adverse-window screen a user hard rule or overwrite its registered failure. The benefits are concentrated in two early selected windows, later periods do not add material net benefit, one worsens wealth, both later periods worsen sampled ES5, and the original stop-distance sizing can increase quote/stop-gap sensitivity. Historical simulation still lacks real executable depth and native stop slippage, and no continuous full-path adoption metric was run. Keep the frozen candidate and all results on the research branch; **do not merge a strategy change into `main`** or start a parameter/795 rescue. The next qualifying evidence would have to address unselected forward manual starts and executable native costs, or a separately justified continuous-path question without changing the rule or inventing an unattended schedule.
