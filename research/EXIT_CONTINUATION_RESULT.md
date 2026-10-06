# 2026-10-06 independent mechanism screen

The original economic contract remains CNY 10,000 without additions,
2020-01-01 to 2026-09-20 UTC exclusive, 795 manually started 300-second
sessions, and Coin CAGR at least 150% with path MDD below 50%. The unchanged
measured baseline is 119.2284% cost-net CAGR and 44.1051% minute-path MDD
proxy, bound to runtime `47837e3`, not this branch. Native cases and actual
account days remain zero. This study does not change main.

## Miner income composition: input gate still blocks

The already frozen fee-share expression uses daily `FeeTotNtv` and
`IssTotNtv`, compared with the preceding 30 days. Its archived 2,485-day
history is complete, but neither the previous official receipt nor the
current [Coin Metrics fee definition](https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/fees-and-revenue/fees.md)
provides an explicit BTC bucket label to availability-time binding and
historical release/vintage record. Generic fee/issuance definitions do not
prove miner selling. The original semantic gate remains NO_SCREEN; no
economic outcome was calculated from the fee-share series. The original
specification and raw receipt remain in the archived `search-artifacts.zip`.

## Ordinary exit continuation: frozen falsification failed

`EXIT_CONTINUATION.md` was committed as `f9a58cf4e9dc57205a5a0ec01c015d343ff885b9`
before this screen. The exact original account and official spot daily bar
hashes, extraction rule, seven-day horizon, fee assumption and rejection
conditions are in that frozen document. The small source-bound script and
complete aggregate output are `exit_continuation.py` and
`exit-continuation-result.json` in this branch.

| Fee-only seven-day spot-price proxy | Ordinary exits | Mean | Median | 5th percentile | Worst intraweek low |
| --- | ---: | ---: | ---: | ---: | ---: |
| Earlier chronological half | 18 | +2.6622% | +3.6748% | -17.3479% | -21.1055% |
| Later chronological half | 18 | -0.0725% | -0.5043% | -10.6508% | -18.1765% |
| All exits | 36 | +1.2949% | -0.3513% | -11.3077% | -21.1055% |
| Observation shifted one day later | 36 | +0.4762% | -0.6661% | -10.9489% | -21.0139% |

The fee-only return is spot open seven days later divided by the next UTC
day's open, after two 0.075% taker fees. It is deliberately generous: no
funding, stop survival, margin, forced liquidation, FX or collision accounting.
The first half is driven in part by 2020 (+7.2034% mean on 10 events); 2021,
2022, 2024 and 2025 annual event means are negative. Both the later-half mean
and whole-set tail breach the preregistered rejection rule. The shifted start
also weakens the apparent gain. Half-size continuation halves the signed
equal-notional gain and loss, so the full-size mean is extra BTC beta, not
independent alpha evidence.

The proposed seven-day overlay would represent about 42.896 million USDT
notional-days, 90.3% of the baseline's observed 47.508 million USDT
notional-days. Eleven of 36 windows contain an original new entry and cannot
be added to the original one-position wallet. Baseline traded 20.387 million
USDT notional, paid 15,290.54 USDT commission and 21,733.16 USDT net funding;
the screen cannot claim those amounts would be saved. The two-fee assumption
is a cost stress, not a measured candidate ledger. Historical spot OHLC and
simulated perpetual fills cannot prove executable future prices, native
protection or continuous drawdown.

Decision: reject this seven-day ordinary-exit extension before an expensive
new wallet run. Keep existing exits and safety gates. No full 795-session
replay, Demo/live account, deployment or credentials were used.

The next independent information routes in the archived failure ledger are
options/OI or on-chain data, but they lack an independently mature, causal
receipt window or complete publication semantics today. A future manual
research session can use genuinely new, qualified receipts and an unchanged
precommitted expression. Another price threshold or start-time search over the
same 795 development sessions would not repair this evidence gap.
