# Frequency redesign and mechanism research

All account measurements cover2020-2023development only.2024+economics unused. Formal unchanged: CNY10000;2020-01-01to2026-09-20exclusive; original sparse schedule; cost-net CAGR>=150%, continuous full-account MDD<50%; Binance BTCUSDT isolated one-way,20xvenue setting. Every result remains NOT_QUALIFIED.

## Shared account A/B

|Model|Schedule|CAGR|MDD envelope|Entries|Fees USDT|Mean close exposure|
|---|---|---:|---:|---:|---:|---:|
|L9 current-quantity scenario|hourly A|4.353915%|16.425340%|72|65.807046|0.088215x|
|L9 current-quantity scenario|sparse B|6.198385%|7.728925%|37|10.107736|0.066962x|
|L17 one campaign per regime|hourly A|6.504207%|7.081099%|25|3.163982|0.054306x|
|L17 one campaign per regime|sparse B|6.702496%|7.728925%|24|3.799842|0.051715x|
|L18 causal net-edge allocation|hourly A|5.350785%|24.448635%|18|8.157109|0.098956x|
|L18 causal net-edge allocation|sparse B|4.203168%|18.093756%|17|7.599530|0.096586x|

L9B exactly reproduced six archived economic/count fields before the new trials. All computed entry sizes bind the old0.6%risk budget. Higher frequency is not an upper bound: stale-regime entries raise turnover. L17 reduces this leakage, with Bfees down62.41%, but does not create remotely sufficient return. L18 replaces a fixed risk fraction with shrunk causal net-edge/second-moment sizing, not a risk grid; Bexposure rises but returns worsen. Do not tune its Kelly constants or risk ceiling.

Gross closed L9PnL: A402.713USDT vs B432.171USDT before fees/funding/open-position effects. Regime age at entry includes reentries and must NOT be called pure decision delay. Counts of minimum-size rejections are decision attempts, not independent missed opportunities.

## Further distinct information trials

L19 funding crowding:456nonoverlapping sparse intervals,360active. Mean unit-inventory net return -0.332203%, compared with long+0.015253% and channel+0.035319% on identical samples. Reject the preregistered contrarian mechanism; no post-hoc sign reversal.

L20 nonlinear conditional memory: same L3features, four-day labels and costs, replacing only global linear fitting with nearest-matured-state conditional means.437overlapping forecasts, correlation-0.036276; directional mean net-0.627223% vs long+0.088421%. Reject; no neighbor-count/feature/horizon search. These are forecast diagnostics, not CAGR/MDD.

L19first implementation incorrectly omitted exact-exit-boundary funding and used interval extrema at exact settlement boundaries. Corrected before any promotion; first and corrected sources/results remain in originals. Final code's two boundary tests pass and final/corrected outputs match exactly.

## Evidence strength and engineering

Future perturbation changes trade/mark data and funding after2023-07-01. Prior orders, decisions and equity match exactly for both schedules (six prefix checks). All468sparse timestamps have identical market-only channel/edge state in A and B, while accounts remain independent. L18unchanged economic fields reproduce exactly after source-identity instrumentation. Minute originals rebuild native hours; preserved source hashes identify each measured implementation. Historical result candidate fields in L17/L18initial files still sayL9; lifecycle/allocation fields and measured_driver.py identify their exact semantics. Current driver emits corrected candidate labels without rewriting old evidence.

34distinct targeted offline tests passed across Binance observation/recovery/CLI, durable state, quantity, schedule, edge allocation, funding boundaries and forecast causality. This is cumulative targeted verification, not a new full-suite run. Binance default CLI now recovers terminal native intents and refreshes account state; active children, missing history and inconsistent quantities remain unknown. No writes/testnet/live account calls occurred.

## Remaining decisions and hard gaps

L17is a useful lifecycle research candidate, not a qualified production model. L9remains the default reproducible structural reference; explicit --lifecycle one_campaign runsL17; --allocation edge reproduces rejectedL18. No production promotion.

Current experiments do not support a credible150%candidate. Scheduler changes, stale-entry repair, historical-edge allocation, funding crowding and nonlinear reuse of the same price information have now been measured. These results do NOT prove no BTCstrategy can meet the target. Further work needs a specific new economic mechanism or independently sourced information, not relabeling an exhausted neighbor search. Keep the150%/50%target unchanged.

Native qualification still lacks dated filters/fees/margin rules, exact funding settlement marks, USDTvaluation and verified protected entry/margin/protection lifecycle. The testnet account required for native lifecycle verification is absent. Official endpoint descriptions do not prove atomic protection. Continue safe engineering/data acquisition when it closes a specific documented gap; never use real funds to substitute for that evidence.

Raw2024+data may only be checked for integrity until a candidate is frozen. No unseen validation was consumed to rescue these trials. Full originals and exact code are linked by receipt; main is unchanged.
