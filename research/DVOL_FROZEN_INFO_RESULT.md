# DVOL completed-bar information screen: closed

**Decision:** close the single frozen DVOL-minus-realized-volatility hypothesis
for Coinquant. Its conditional historical association with the original
protected-stop outcome is weak, opposite the preregistered direction overall,
and inconsistent between the two fixed calendar periods. This is neither a
proof that all option information is useless nor a native-account result.
No economic rule, wallet pair, 795-session replay or `main` change follows.

## Source and causal support

The preceding [source pilot](DVOL_SOURCE_PILOT.md) established the distinct
public BTC index and its strict historical-version limitation. Before the
expanded retrieval or outcome relation, a local task freeze fixed six **public
calendar** requests: April–December 2021, full years 2022–2025, and
January–September 2026. None contained private manual-start timestamps. Six
production public `BTC`, `1D` requests returned 2,009 daily OHLC bars total,
all with `continuation=null`. The calendar from 1 April 2021 through 30
September 2026 is contiguous, every bar passes OHLC checks, and all 32 bars
overlapping the earlier narrow pilot are unchanged. The six raw public
responses and request/receive receipts remain local. Deribit's
[endpoint documentation](https://docs.deribit.com/api-reference/market-data/public-get_volatility_index_data)
defines the candle fields and pagination. Its
[index description](https://insights.deribit.com/exchange-updates/dvol-deribit-implied-volatility-index/)
describes 30-day annualized **implied** volatility, not a bearish order-flow
signal or Binance executable price.

Only the original baseline's **50 distinct filled flat-to-flat campaigns**
were considered, once each at the first actual BUY in its real bounded manual
start. The original durable campaign map and terminal SELL identity assign
protective STOP_MARKET outcomes; later starts, top-ups and overlapping seven-day
windows add no observations. Fourteen campaigns precede the DVOL launch and
are excluded. The remaining **36** have a DVOL daily close completed strictly
before the start and no older than 24 hours, plus 31 contiguous original
Binance USD-M futures daily closes. The futures closes came from 85 retained
four-hour ZIPs, each checked against its previously qualified original content
digest; no new Binance history was fetched. Original stop-algo/order identity
confirms 10 protective stops among these 36. One of those ten fired more than
seven days after first fill while native protection remained in place; the
test retained the *actual* protected-exit label and did not invent an
unattended seven-day exit.

| Entry year | Independent campaigns | Original protective stops |
| --- | ---: | ---: |
| 2021 after launch | 4 | 2 |
| 2022 | 6 | 1 |
| 2023 | 11 | 1 |
| 2024 | 7 | 4 |
| 2025 | 5 | 0 |
| 2026 through original terminal | 3 | 2 |

The two fixed periods contain 21 campaigns/4 stops and 15 campaigns/6 stops.
Across them, original simulated cashflow signs are 13 winners/8 losers and
8 winners/7 losers. These counts exceed the frozen minimum of 30 independent
campaigns, 10 stops, 10 non-stops and three stops in each period, allowing the
one registered *information* screen. They do not establish power for strategy
adoption.

## One frozen test and result

The score is the latest completed DVOL close, in annualized volatility
percentage points, **minus** trailing 30-day realized volatility from the
original futures completed daily closes: `100 × sqrt(365) × sample_std(30
daily log returns)`. The past and forward horizons are each nominally 30 days
but are not the same payoff. Controls fixed before viewing the relationship:
the original 20-day zero-centered simple-return RMS, seven-day completed-price
log momentum, macro/primary model indicator, and 2021–2023 versus 2024–2026
period indicator. Both the score and observed stop label were linearly
residualized on those controls. The sole statistic was their **one-sided
partial Pearson correlation**, with 10,000 within-period label permutations
using fixed seed 0. The frozen positive-information screen required p ≤ 0.05
and a positive stop-minus-nonstop residual-score difference in both periods.

Observed correlation: **−0.0932**. Permutation one-sided **p = 0.7103**.
Residual-score stop-minus-nonstop differences are **+1.21** index points in
2021–2023 and **−5.45** in 2024–2026. The single registered screen fails on
both the overall statistic and period consistency. No threshold variant,
opposite-sign rescue, winner selection, funding/fee wallet or policy was tried.

## Qualification boundary

These historical DVOL bars were retrieved in 2026. Their complete UTC bar
times prevent *same-day* lookahead in this calculation, but Deribit provides
no per-bar initial-publication timestamp or immutable version chain in these
responses. The official launch date does not prove each archived old value
was then published unchanged. Consequently the negative result is a
conditional development finding; it is not strict point-in-time or forward
validation. The producer's uncalibrated IOC/depth and stop slippage also
remain unchanged. The original 150% CAGR reference remains unmet. Future
option-source work would need genuinely timestamped receipts at actual manual
starts or an independent historical version chain and a new, separately
justified hypothesis; this failed expression stays closed.
