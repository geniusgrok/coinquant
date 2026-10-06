# Falling mark before a long add: insufficient support

Research only. The original hypothesis and support gate were recorded locally before its counts were computed; this redacted publication was prepared afterward. The public branch's commit order alone is not evidence of preregistration. The incumbent SX60 + DFII10 strategy, seven-day lifetime and manual sessions remain unchanged.

## Frozen question

Could an existing protected long avoid wasting risk by skipping only a new add when its last two completed *perpetual mark* observations declined? At the original BUY time, require two earlier daily account marks with positive held quantity and price, separated by no more than 48 hours, with the latest no older than 24 hours. Missing or stale marks do not qualify. Count distinct signaled campaigns in 2020–2022 and 2023–2026. The pre-result gate required at least ten across both eras and at least three in each. This checks support, not profitability.

This add-only question differs from the previously rejected short/cash replacements, price-state opportunity generation, initial-entry quality budget, position reduction after a downside shock and a frequency-only single-top-up rule. It does not propose more shorting, leverage, trades or unattended action.

## Result and sampling check

| Original simulated perpetual account | 2020–2022 | 2023–2026 | Total |
| --- | ---: | ---: | ---: |
| BUY order groups while already long | 18 | 112 | 130 |
| Two qualified prior marks, declining | 2 | 0 | 2 |
| Two qualified prior marks, nondeclining | 1 | 4 | 5 |
| Missing two positive held daily marks | 15 | 108 | 123 |
| Distinct signaled campaigns | 1 | 0 | 1 |

The gate failed. Both declining adds belong to the same early simulated campaign; there is no late-period intervention. This is **insufficient support**, not evidence of better returns or of a predictive signal. No threshold change, return attribution, wallet replay or 795-session rerun was made.

The full account records 302 daily marks with an open long. The separate archived session reports contain 104 positive held-mark observations, but **zero** of the 130 top-ups have two fresh, completed report marks before the add under the same age bounds. Thus the published report archive does not supply a missing eligible pair for this rule. This check does not assert that all historical market marks were absent: the raw minute market files used by the old producer are not in this repository. Reconstructing them or substituting spot OHLC would be a new data exercise, not a correction to this screen.

## Public provenance and reproduction

The input is the repository's already published [historical backtest archive](https://github.com/geniusgrok/coinquant/tree/archive/backtest-main-20261006/backtest-source). Its [registration](https://github.com/geniusgrok/coinquant/blob/archive/backtest-main-20261006/backtest-source/coin-registration.json) says `live_or_private_account_access: false`; the archived account itself says `no_live_account: true`, `native_verified: false` and its ledger audit passed. The published [simulator](https://github.com/geniusgrok/coinquant/blob/archive/backtest-main-20261006/backtest-source/coin-tooling/research/session_exchange.py) assigns order numbers with an internal sequence; these are simulated identities. Local input bytes were checked equal to the already archived account and report files. No real-account data, credentials, exchange account identifiers or new raw account copies are included here. The original [baseline summary](https://github.com/geniusgrok/coinquant/blob/main/BACKTEST.md) remains 119.23% cost-net CNY CAGR and 44.11% minute-path drawdown *proxy*, short of the original 150% CAGR reference; native account days remain zero.

To reproduce the aggregate counts, check out the archive branch separately and run `python research/long_add_downstate.py <coin-full.json.gz> <reports.jsonl>` from this research branch with the archive's `backtest-source/coin-full.json.gz` and `backtest-source/private/coin/reports.jsonl`. The script reads only those published historical simulation files and prints aggregate counts, never order/account identifiers, balances, hashes or trade rows. It does not access an exchange or place orders.

Spot's [shared raw-block qualification result](https://github.com/geniusgrok/spotquant/blob/c1f713a1df7a8ad104a785e8a495105cd19cfca5/research/20261006-spot-alpha-screen/BLOCK-SOURCE-RESULT.md) proves the native satoshi units and actual receipt of one current BTC block. It does **not** qualify the old daily fee series at historical decision times; coinbase payout above subsidy is only a lower bound on claimed fees, not total fees or miner selling. Therefore the historical miner fee-share substitute has **no economic screen and no Coin account experiment**. Coin reuses this source conclusion only; the strategies and accounts remain independent. Existing options, OI and cross-venue flow observations also lack enough distinct mature periods or synchronized executable context for a new Coin wallet decision. No new strategy enters `main` without independent information, actual legal interventions and cost-net wallet, drawdown, tail, funding, protection and manual-start evidence.
