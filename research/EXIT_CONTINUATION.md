# Ordinary exit continuation: frozen cheap screen

Registered on 2026-10-06 before computing any post-exit returns. This research
branch does not change the running strategy. The archived 795-session account
remains the only full-window baseline: 119.2284% CNY CAGR, 44.1051% path MDD
proxy, against the original 150% / <50% reference. Its producer is `47837e3`.

## Prior input gate

The independent miner fee-share direction retains the earlier frozen
`miner/screen-spec.json` (SHA-256 `f920cac6df1194fae5677bd153f91901022f7f181439f4e4a6de5d55894a0766`)
in the archived `search-artifacts.zip`. It requires explicit BTC fee/issuance
scope and UTC bucket-end semantics before any economic screen. Today's official
documentation review confirms generic definitions, but does not resolve those
two requirements or historical publication/vintage. Status stays NO_SCREEN.

## Distinct mechanism and inputs

Hypothesis: closing an owned long for an ordinary, non-protection reason may
forfeit a further seven days of BTC trend. Test every complete actual long
episode closed by a MARKET order that is not a STOP_MARKET or TAKE_PROFIT_MARKET
child. Do not select exits by profit, year, age, signal or later returns.

Use the original account `coin-full.json.gz` (SHA-256
`8277a620e75249017f5594a8f989ce335f7bb6d90814a724ff5eee6b92d3674e`)
and the archived official Binance spot daily bars `daily-composition.json`
(SHA-256 `6a35dadcbe9228d95191a2d2716bc2c2d9f01aa8be08638718325fbefb376009`;
container `search-artifacts.zip` SHA-256
`c9f9b30ab5f5a551a9a9bf5e9bd99ced3dc934b50d116eee1d9f5d59ff941cc3`).
The spot bar is a price proxy, not a perpetual executable quote.

## Frozen comparison and rejection rule

For each exit, observe the official spot open of the *next* UTC day and the open
seven calendar days later. This deliberately avoids using a day's pre-exit
high/low as post-exit knowledge. Calculate the seven-day price return and a
fee-only upper-bound return after two 0.075% taker fees. The baseline action is
cash after exit (zero BTC return); a constant half-size continuation is the
simple extra-beta control. Neither is a full independent wallet. Estimate gross
additional BTC notional-days from the actual closing quantity and first open.
Count intervening original entries, where a continuation would collide with
the one-position account, instead of assuming independent capital. Show the
whole set, chronological halves, and exits with observation shifted to the
second following UTC open. No shift may be selected as the adopted timing.

Report mean, median, 5th percentile, worst, positive fraction, fee-only total
on fixed initial notional, exposure-days, original turnover and extra turnover
assumptions. Count daily low below the original exit price as a *tail proxy*,
not an executed stop. Funding, original native stop survival, margin, FX,
compounding and substitution of later trades are not observed in this screen.

Reject this mechanism before account simulation if either chronological half
has nonpositive mean fee-only seven-day return, or if the whole-set 5th
percentile fee-only return is below -10%, or if more than half the events have
an intervening original entry. A positive screen only permits a later exact
finite-session wallet comparison with original protection, full funding/fees,
same capital and schedule, original and half-size controls, cost stress and
start offsets. It is not adoption or evidence of prospective alpha.

No parameter grid, full-history rerun, live account, deployment or new key.
