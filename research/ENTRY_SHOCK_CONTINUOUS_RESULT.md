# Entry shock: complete continuous account result

**Decision: reject the frozen entry deferral for the current strategy.** The
single authorized baseline/candidate pair completed all 795 original irregular
manual sessions and the original terminal valuation. This remains a development
simulation under the archived perpetual exchange model, not prospective alpha
or native execution acceptance. The rule, original seven-day expiry, position
sizing, fees, funding, protection, and session clock were unchanged during the
pair. No parameter rescue or second full pair was run.

The fresh baseline exactly reproduced the archived complete original wallet on
25 financial/path fields: terminal equity, drawdown, 1,561 trades, 2,532 income
entries, 2,455 daily equity points, fees, funding, the financial audit, and all
773 loaded print and 210 loaded minute file hashes. The candidate used exactly
the **same** loaded minute and print file path/hash sets; the first 26 session
reports were identical, and the first changed decision was session ordinal 27.
Only two original executed sessions became nonexecuted, while two other sessions
executed only in the candidate. Both terminal receipts passed the native-shaped
order/ownership and financial audits with a fully known simulated path;
`native_verified` remains false.

| Complete account measure | Baseline | Frozen deferral |
| --- | ---: | ---: |
| CNY CAGR | 119.2319% | 120.1226% |
| Path proxy MDD | 44.1051% | 44.1062% |
| Worst 5% daily CNY loss, mean | 3.7489% | 3.7530% |
| Trades | 1,561 | 1,663 |
| Days with gross BTC exposure | 302 | 295 |
| Mean daily gross notional/equity | 0.2754× | 0.2783× |
| Maximum daily gross notional/equity | 7.6804× | 7.6795× |

Terminal CNY wealth is **2.7616%** higher, equivalent to **+0.8907 percentage
points CAGR** on this exact path. Path MDD is **0.0012 points worse** and CNY
daily loss ES5 is **0.0041 points worse**. Turnover and fees each rise **4.8153%**,
funding paid rises **4.9682%**, and there are **102 more fills**. Fewer held
calendar days therefore did not reduce total cost or average effective
exposure. The tiny MDD and ES5 changes are descriptive model outputs, not
measurable native tail precision.

Own-wallet calendar-year CNY returns show why the four selected quarter results
do not generalize. The final 2026 row is partial through the original terminal
date; these rows are not independently restarted accounts.

| Year | Baseline | Deferral |
| --- | ---: | ---: |
| 2020 | 1185.6430% | 1225.8709% |
| 2021 | 46.6081% | 51.2799% |
| 2022 | -17.4854% | -17.4913% |
| 2023 | 431.0301% | 424.8279% |
| 2024 | 64.6453% | 60.6875% |
| 2025 | 16.7885% | 16.7802% |
| 2026 partial | 23.1449% | 23.3032% |

The original replacement contract requires either at least **1.10× baseline
CAGR with no higher MDD**, or at least **0.95× baseline CAGR and at most 0.80×
baseline MDD** with reduced risk budget. This candidate fails both routes:
the first requires about 131.16% CAGR and MDD no higher than 44.1051%; the
second requires MDD at most about 35.28%. It also remains well below the
original **150% CAGR / below-50% MDD** reference. A doubled-cost or slippage
wallet cannot rescue the failed nominal gate, so none was run. No change is
prepared for `main`.

## Input and execution limits

The fixed public calendar supplied 2,454 Binance USD-M daily print ZIPs,
41.584 GiB verified, with 36.054 GiB newly transferred; 50 archived daily
minute overlays and 160 archived monthly minute ZIPs retained their original
SHA identities. The extra public download breadth did not add files to the
original minute loader's selection. That loader reads its exact retained month
set first and applies retained daily overlays only when values agree. New
candidate print access would use the precommitted official daily file and
checksum; in the actual final pair, even the loaded print days matched the
baseline exactly. This proves reproducibility of the archived model's source
bytes, not the first-publication time of every historical object.

The original producer still uses its uncalibrated print/depth, IOC and stop
slippage proxies. This pair cannot establish executable capacity, an upper
bound on drawdown, or protection behavior in a native exchange account. It also
uses only the original irregular manual start sequence. Four previously saved
independent quarter starts remain useful local checks, but do not prove
robustness to arbitrary future user launch times. The added gate and durable
research identity increase maintenance and recovery surface while missing the
economic acceptance routes.

The read-only aggregate check is
`python research/entry_shock_continuous_result.py --original <archived-receipt.gz> --baseline <fresh-baseline-receipt.json> --candidate <candidate-receipt.json>`.
It requires complete audited local receipts and journals, checks the original
baseline reproduction and exact paired input versions, and prints only
aggregate ratios/counts. Private receipts, exact manual timestamps, order
identifiers, and raw account balances remain local. Public technical research
stays on this branch; current `main` remains the simple existing strategy.
