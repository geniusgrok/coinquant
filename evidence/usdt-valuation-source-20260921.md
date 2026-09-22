# USDT valuation data dependency — unresolved

Production exchange support remains Binance only. USD valuation of USDT collateral
is a separate reference-data question; it must not silently assume USDT=USD for
formal complete-account acceptance.

[Kraken official historical OHLCVT archive documentation](https://support.kraken.com/articles/360047124832-downloadable-historical-ohlcvt-open-high-low-close-volume-trades-data)
was checked on 2026-09-21. The published complete archive covers markets through
2026-06-30 and is split into five large parts; quarterly increments are also listed.
It includes per-pair multiple-interval CSVs and a manifest. Missing candles represent
no trades, not an explicit zero price. This is a possible USDT/USD reference source,
not an additional trading adapter and not yet acquired or verified.

Do not download the multi-gigabyte all-market archive merely to extract one pair.
First determine whether verified range extraction or a smaller official USDT/USD
source is available. The remaining July-September window also needs a verified
source. No USDT depeg series has been incorporated in any reported experiment.
