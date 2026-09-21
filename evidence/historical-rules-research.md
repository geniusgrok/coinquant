# BTCUSD historical trading-rule evidence

Purpose: preserve dated evidence for the 2020-01-01 through 2026 research
window. This file is research evidence, not a production configuration and not
a qualified `rules.csv`. Missing historical facts remain missing; current
rules are never copied backward merely to make a replay run.

## Trading fee timeline

### Pre-March-2022 regime

A Bybit `/en/contract-rules` page preserved by current web indexing describes
the legacy derivatives fee model as:

- maker: **-0.025% rebate**
- taker: **0.075% fee**

Source:
- https://www.bybit.com/en/contract-rules

The indexed page itself does not establish the first effective date. It is
consistent with contemporaneous 2021/early-2022 descriptions, but the research
manifest must still attach an explicit dated source when available.

### March 2022 change

Multiple contemporaneous/near-contemporaneous secondary sources report a Bybit
fee change on **2022-03-18** (some social posts announced dates earlier in
March), changing standard derivatives fees from:

- maker -0.025% -> +0.01%
- taker 0.075% -> 0.06%

Sources preserving the change and pointing to the then-Bybit announcement:
- https://coinback-crypto.com/column/bybit-commission-measures/
- https://www.reddit.com/r/Bybit/comments/t9l0ai

This is useful dated evidence but is not as strong as a recovered original
Bybit announcement. Treat the exact effective timestamp as needing primary
confirmation before a `native` rules timeline is declared.

### By 2023-02-17 and current regime

Bybit's own fee comparison content states that, as of **2023-02-17**, the
entry-level perpetual/futures fee was:

- maker 0.02%
- taker 0.055%

Source:
- https://www.bybit.com/en/learn/bybit-guide/bybit-trading-fees

Current Bybit Help Center also lists VIP 0 perpetual/futures as taker 0.055%,
maker 0.02%:
- https://www.bybit.com/en/help-center/article/Trading-Fee-Structure

The exact effective date for the transition from 0.06%/0.01% to
0.055%/0.02% is still **UNVERIFIED**.

## Dated BTCUSD contract specification capture (2020-10-07)

A CCXT issue opened **2020-10-07** includes the then-current Bybit BTCUSD
market metadata returned to the client. The captured fields are:

- `tick_size = 0.5`
- `min_trading_qty = 1`
- `qty_step = 1`
- `max_trading_qty = 1,000,000`
- `min_leverage = 1`
- `max_leverage = 100`
- `maker_fee = -0.00025`
- `taker_fee = 0.00075`

Source:
- https://github.com/ccxt/ccxt/issues/7713

This is a dated third-party capture of Bybit API metadata, materially stronger
for the 2020 regime than copying current contract details backward. It still
does not prove that the same values were effective on 2020-01-01 or identify
the exact timestamps of later specification changes.

Additional CCXT verbose logs preserve direct Bybit `v2/public/symbols`
responses at several later dates with the same BTCUSD values:

- **2020-06-09**: CCXT issue #7091
- **2020-08-12**: CCXT issue #7454
- **2021-04-23**: CCXT issue #9053
- **2022-01-12**: CCXT issue #11268

Across these captures BTCUSD remains tick 0.5, quantity step/minimum 1,
single-order maximum 1,000,000, maximum leverage 100, maker -0.00025 and
taker 0.00075.

Sources:
- https://github.com/ccxt/ccxt/issues/7091
- https://github.com/ccxt/ccxt/issues/7454
- https://github.com/ccxt/ccxt/issues/9053
- https://github.com/ccxt/ccxt/issues/11268

Together with the 2020-10-07 capture, these are contemporaneous API observations
spanning 2020-06 through 2022-01. They substantially constrain that regime but
still do not establish a value for 2020-01-01 before the first captured point.

## Dated BTCUSD V5 specification capture (2024-04-26)

Bybit.Net issue #207 includes a full raw V5 inverse-instruments response with
exchange timestamp `1714136377870` and GitHub issue creation date
**2024-04-26**. BTCUSD fields in that response are:

- tickSize: **0.50**
- minOrderQty / qtyStep: **1 / 1**
- maxOrderQty: **1,943,695**
- maxMktOrderQty: **1,000,000**
- maxLeverage: **100**
- fundingInterval: **480 minutes**
- settleCoin: **BTC**

Source:
- https://github.com/JKorf/Bybit.Net/issues/207

The current 2026 official `api.manepa.jp` instrument response instead has
tickSize **0.10**, maxOrderQty **25,000,000** and maxMktOrderQty **5,000,000**.
Therefore those specification changes occurred after 2024-04-26; their exact
effective timestamps are still unverified and must not be invented.

## BTCUSD inverse margin/risk facts

Current Bybit inverse-contract documentation states:

- inverse position value = contract size / mark price;
- lowest BTCUSD example tier covers position value <= 150 BTC;
- maintenance-margin rate for that example tier is 0.5%;
- current V5 risk-limit response example for BTCUSD also shows riskLimitValue
  150 BTC and maintenanceMargin 0.5.

Sources:
- https://www.bybit.com/en/help-center/article/Maintenance-Margin-Inverse-Contract
- https://www.bybit.com/en/help-center/article/Risk-Limit-Perpetual-and-Expiry-Contracts
- https://bybit-exchange.github.io/docs/v5/market/risk-limit

Bybit explicitly states risk parameters may be adjusted over time. Therefore
these current numbers **must not** be projected backward over 2020-2026 as
historical-native facts. A dated risk-tier history remains **UNVERIFIED**.

## Funding facts and source leads

Current V5 documentation confirms public funding-history support for inverse
perpetuals:
- GET /v5/market/funding/history
- category=inverse
- fundingRate and fundingRateTimestamp are returned.

Source:
- https://bybit-exchange.github.io/docs/v5/market/history-fund-rate

Contemporaneous 2021-2022 articles point to Bybit's former BTCUSD inverse
funding-history page and state that actual funding-rate history could be
downloaded as XLSX:
- https://www.bybit.com/data/basic/inverse/funding-history?symbol=BTCUSD
- https://note.com/btcml/n/na9c5816cd0b0
- https://note.com/mtkn1/n/nba33bf1a0b26

The current Bybit page no longer exposes the historical XLSX download in
machine-readable HTML. Recovering the underlying original file/API remains an
open research task.

## Native market-data coverage already verified

Official public directory:
- https://public.bybit.com/trading/BTCUSD/

It contains BTCUSD inverse trade archives from before the 2020 formal start and
the currently indexed listing extends through **2026-08-08**.

Official static spot-index/premium-index directories include the 2020 start but
end in March 2020:
- https://public.bybit.com/spot_index/BTCUSD/
- https://public.bybit.com/premium_index/BTCUSD/

These static index/premium directories therefore cannot supply the complete
2020-2026 native mark/funding history.

Current Bybit V5 documentation does support historical inverse mark-price
klines and funding history:
- https://bybit-exchange.github.io/docs/v5/market/mark-kline
- https://bybit-exchange.github.io/docs/v5/market/history-fund-rate

The remaining blocker is obtaining and hashing the full responses from a
permitted/reachable official Bybit host, not inventing the schema.

## Still missing before a native rules.csv can be asserted

The following remain unverified across the complete formal window:

1. Exact timestamp of the 0.06% -> 0.055% taker-fee transition.
2. Full dated BTCUSD risk-tier / MMR changes.
3. Dated tick-size changes, if any.
4. Dated quantity step/minimum changes, if any.
5. Dated per-order and market-order maximum changes.
6. Any historical funding-interval changes (the commonly documented BTCUSD
   interval is eight hours, but a complete dated source timeline has not yet
   been recovered).

Until those are resolved, a diagnostic rules timeline must be labeled
`proxy`; it cannot qualify CAGR/MDD as native economic acceptance.
