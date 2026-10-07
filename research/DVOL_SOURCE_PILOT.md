# DVOL public-source pilot: conditional only

**Decision:** Deribit BTC DVOL is a distinct, reachable options-implied
volatility source with plausible *completed-bar* alignment to Coinquant's
irregular manual starts. It is **not yet a point-in-time-qualified historical
strategy input**, an entry veto, a bearish indicator, or evidence of improved
returns. No wallet or strategy test was run; `main` stays unchanged.

The archived `research/search-RESULT.md` (before the main cleanup commit
`47837e3`) covers only two receipt days of option-chain snapshots and other
source candidates. The current research branch and archived failure ledger do
not contain a DVOL index pilot. Deribit's
[`get_volatility_index_data`](https://docs.deribit.com/api-reference/market-data/public-get_volatility_index_data)
returns public BTC OHLC rows `[timestamp_ms, open, high, low, close]` with
`continuation` for pagination. It differs from
[`get_historical_volatility`](https://docs.deribit.com/api-reference/market-data/public-get_historical_volatility),
which describes volatility calculated from past prices. Deribit's
[launch page](https://insights.deribit.com/exchange-updates/deribit-launches-volatility-index/)
displays **31 March 2021** and describes DVOL as 30-day annualized implied
volatility from options. The site's machine publication/update metadata is
later; neither it nor today's endpoint proves the exact first publication of
each old bar. Deribit's [methodology page](https://insights.deribit.com/exchange-updates/dvol-deribit-implied-volatility-index/)
says the calculation parameters can change and carries a later update date.
DVOL measures expected *magnitude* of moves, including upside; a high value
does not by itself predict a decline in Binance BTCUSDT perpetuals.

## Fixed public-calendar probe

Before the saved requests, five BTC `1D` windows were fixed independently of
private starts: 1–8 April 2020, 1–8 April 2021, 1–8 January 2023,
1–8 January 2025, and 1–8 September 2026 (UTC, inclusive endpoint). A
single initial unsaved 2021 availability probe preceded this freeze; it was not
used for selection. The five saved production public GETs returned HTTP 200,
`testnet=false`, and `continuation=null`. Raw response bytes, request/receive
times, HTTP Date and SHA-256 receipts remain in the local task directory;
neither private manual times nor account/order identities were sent to Deribit
or published.

| Fixed window | Daily bars | Original manual starts in window | Starts with a sampled bar completed strictly before start |
| --- | ---: | ---: | ---: |
| 2020-04-01..08 | 0 | 3 | 0 |
| 2021-04-01..08 | 8 | 4 | 3 |
| 2023-01-01..08 | 8 | 2 | 2 |
| 2025-01-01..08 | 8 | 3 | 2 |
| 2026-09-01..08 | 8 | 4 | 3 |

The 32 returned bars have one-day-spaced UTC timestamps, positive and
internally consistent OHLC, no duplicates or gaps **inside these four sampled
postlaunch windows**. A bar is used only if `bar_start + 24h < manual_start`;
same-day developing bars are excluded. In the ten locally matched starts,
completed-bar age was 2–19 hours. The three postlaunch starts without a match
occur before the first sampled bar closes; this small query does not test
whether an earlier bar existed. The 2020 empty response is consistent with the
later launch and is never backfilled as 2020 information. All five sample
responses ended without continuation; the endpoint's documented continuation
must be followed and gaps checked in any later, justified wider query.

The HTTP Date headers describe **2026 receipt**, with no per-bar original
receipt, ETag or Last-Modified version. Thus today's historical bars cannot
prove their exact values were available at the old manual starts or that bars
were never corrected. The launch announcement supports existence of the index
after launch, while the sampled completed-bar clock only prevents same-day
lookahead under an assumed unchanged archive. Historical development may use
these bars only with that explicit qualification; strict prospective input
requires receipts collected at real future manual starts or an independent
contemporaneous version chain. This pilot does not establish whole-period
coverage, release latency, stale-bar behavior or a trading edge.

## One possible information question, pending qualification

If source timing and enough independent opportunities become qualified, test
whether the **completed DVOL minus contemporaneous, unit-matched realized
volatility** carries information about the original seven-day protected-stop
outcome *after controlling for the existing RMS and momentum state*. Count all
eligible manual opportunities and the winners a rule could miss; do not choose
a DVOL threshold from these historical outcomes. This is an information
hypothesis, not a signed direction or a proposed risk rule. Any later economic
candidate would still need the original fees/funding, protected wallet path,
irregular manual starts, native cost limits and replacement checks. No signal
formula, account, Demo or live adapter was changed here.
