# Execution and data status

No production writes implemented or attempted by this continuation. Existing CLI
rejects --execute before credential access, then supports bounded authenticated
read-only account/intent observation when explicit credentials are supplied.
Current BinanceReadOnly has durable-intent recovery, UID check, parent/child
readback and isolated20x checks; it does not implement protected entry, native
TP/SL replacement, cancellation or isolated-margin writes. Legacy execution.py
is Bybit-specific and cannot be relabeled Binance or used as a fallback.
No authorized testnet account/credentials were supplied. No mock or offline check
is reported as testnet verification. A complete native protected write lifecycle
remains an actual acceptance blocker, independent of economic improvements.

Historical fee/filter/margin timelines, exact offset funding settlement marks,
USDT collateral valuation and native execution liquidity remain unresolved.
Minute refinement verifies native archive checksums and hourly reconstruction,
not exact tick paths or actual stop-market fills. Funding interval diagnostic
uses fixed measured inventory; its cash interval is not a strategy-return bound.
No new safety gates or acceptance thresholds were added.
