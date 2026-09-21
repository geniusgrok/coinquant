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
