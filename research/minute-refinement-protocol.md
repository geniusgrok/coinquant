# Paired minute refinement, before refined L9 results

Six preregistered development dates only,12 official daily archives with exchange
SHA256 and exact reconstruction of all144 hourly trade/mark candles per kind.
No strategy/size/stop changes. L7 and L9 both receive identical minute availability.
Resolve cross-minute event order; keep same-minute liquidation-first ambiguity.
Only frozen original invocations may change model decisions.
Funding remains the disclosed adverse hourly bound; do not call it actual cashflow.

Initial L7 refinement identified a potential implementation hazard: do not repeat
hour-open checks after applying an offset funding bound using later hour extrema.
Hour-open checks already execute before decisions/funding in the original driver.
Subsequent minute-open checks are allowed; first-minute repeats are omitted.
Preserve initial result/source, then rerun corrected L7 before paired L9.
Do not interpret changes from revised observation resolution as new strategy alpha.

Compare refined L9 to refined L7 for CAGR and CAGR/MDD; MDD<50% and <=2 liquidation
classifications retain original L9 screen. Report baseline liquidations separately.
Numeric progression is not qualification;2024+ remains economically uninspected.
