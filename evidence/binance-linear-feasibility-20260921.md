# Binance BTCUSDT linear feasibility — NOT_QUALIFIED

Official current exchangeInfo identifies PERPETUAL, USDT margin/quote, onboardDate
1567965300000 (2019-09-08 UTC). This verifies a pre-2020 listing, not dated rules.
Current filters must not be backfilled across history.

Official public archive January 2020 trade/mark/funding and September 19 2026
trade/mark boundary ZIPs are available with matching exchange SHA256 checksums.
September funding tail has 57 real API settlements. Millisecond offsets in funding
are preserved; rounding them without event-order treatment would be incorrect.
December 2019 archive URLs return 404; investigate the official API warmup path.

[Official API trade documentation](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade)
was read on 2026-09-21. Conditional STOP_MARKET/TAKE_PROFIT_MARKET can close the
current entire position, using MARK_PRICE; quantity and reduceOnly must be omitted
when closePosition is true. One-way mode uses BOTH. clientAlgoId uniqueness applies
to open orders, so durable intent and terminal-order reconciliation remain needed.
The separate query response exposes actualOrderId and algoStatus.

These facts do NOT establish atomic entry protection, safe pre-arming while flat,
partial-fill protection, sibling cancellation or unknown-result recovery. They need
explicit lifecycle proof and authorized testnet checks. No production adapter is
selected. No private endpoint has been called. A FOK entry would remove remainder
risk only after its terminal state is established; it cannot by itself prove atomic
TP/SL protection. Historical costs, risk tiers and stablecoin collateral risk remain
unqualified. Native public history acquisition is an evidence task, not acceptance.

## Binance-only execution, verified read surface

The user selected Binance exclusively. The research read transport now signs the
exact Binance query string, restricts hosts and endpoint paths, rejects redirects,
scrubs transport errors and exposes no write method. Five focused tests passed.
No private request was sent; test credentials are synthetic. It is not yet the
production run_once adapter.

[Official Spot account schema](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/account)
contains uid on GET /api/v3/account. The wallet account-info and futures account
schemas examined do not expose this UID; do not invent a futures UID field.
Only the UID is retained by the identity probe.

[Official futures account schema](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/account)
provides accountConfig for one-way/single-asset checks and symbolConfig for
isolated mode, leverage and automatic margin. The probe requires isolated 20x
with automatic margin off; it never changes account settings. Historical filters
and fees are still separate from current account observations.
