# Frequency isolation (development only)

Same L9 and current-quantity scenario. B reproduces all six archived economic/count fields exactly. No2024+ economics. NOT_QUALIFIED.

|Schedule|CAGR|MDD envelope|Entries|Fees USDT|Mean close exposure|
|---|---:|---:|---:|---:|---:|
|A hourly|4.3539153053%|16.4253401119%|72|65.8070|0.088215|
|B sparse|6.1983853673%|7.7289245630%|37|10.1077|0.066962|

Every computed entry sizing attempt binds on the fixed0.006risk budget. Entry quantities are rounded down by shared market_quantity; no forced upsizing. Hourly scheduling is not an upper bound and worsens this model.

A has45stop exits,4liquidation classifications and19regime exits; B has18,1,16. Gross closed PnL A402.713USDT versus B432.171USDT before fees/funding/open-position effects. A72entries versus B37: repeated stale-regime entry is a testable lifecycle mechanism, not evidence that arbitrary risk escalation works.

Regime age at entry is reported, NOT pure decision delay: it includes same-regime reentries. Current2026quantity filters are a scenario, not dated historical rules; funding is adverse valuation and credits omitted; MDD is a conservative extrema envelope.

Formal target remains sparse full-window cost-net CAGR>=150% and continuous MDD<50% plus provenance/execution safety. These measurements do not qualify. Next registered mechanism will test stale-regime reentry rather than change risk allocation.
