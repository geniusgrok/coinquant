# Pancakequant engineering rules

Repository: ychenracing/pancakequant.

## Current mandate

Implement the user's PANCAKEQUANT_REDESIGN_PROMPT: one manually triggered BTC perpetual system, one quantitative model, one Binance exchange adapter, one current configuration.
The user selected Binance exclusively on 2026-09-21. Target BTCUSDT USDT-settled
linear perpetual. Retire other production adapters during migration; retained
Bybit/OKX evidence is historical research, not required exchange support. All existing code, strategy, risk, dependencies and architecture may be replaced. Do not preserve obsolete interfaces or capabilities as acceptance conditions.

The economic targets are cost-net CAGR >= 150% and continuous full-account MDD < 50%, from 2020-01-01T00:00:00Z through 2026-09-20T00:00:00Z exclusive. Research may decide hourly or at another preregistered causal frequency; formal acceptance still uses the original frozen sparse invocation sequence. Both modes share model, market, costs and account implementation, with independent account paths. Research-frequency success is not formal acceptance. Start with CNY 10,000, explicitly freeze conversion and settlement assumptions, include real contract history, costs, funding, liquidation and sparse irregular manual triggers. Do not move the window, lower targets, fabricate data or call diagnostic replay formal acceptance.

## Execution safety

Default read-only; live execution requires explicit current authorization and matching configured account. This engineering task does not authorize trading, transfers, credentials or real account-setting changes. Only BTC exposure and owned orders may be changed. Reconcile exchange positions, ordinary orders, conditional orders and fills before deciding. Unknown responses are not failures or successes: persist intent and query by stable identity before any retry. Never assume an unavailable account query means an empty account.

Use one-way isolated positions with exchange leverage fixed at 20; effective account leverage may be lower. Newly filled exposure needs native full-position TP and SL, including partial fills. Protection must survive process exit. Do not leave an entry remainder able to reopen unprotected exposure after a stop. Keep valid protection during amendments. When safety cannot be established, stop new exposure, report uncertainty, and use only authorized risk reduction. No background daemon is an acceptable substitute.

## Engineering and verification

Read current code and real call paths. Reuse only what serves this mandate. Keep the production path small and coherent; no obsolete adapter/strategy compatibility. Apply available PonyTail where relevant; do not add mandatory TDD, coverage targets, exhaustive tests or approval gates. Use targeted funds, orders, idempotency, protection, data-causality and sparse-trigger tests. Missing live/testnet checks remain unverified.

One lightweight CI workflow at most, one Python environment, timeout-minutes: 10, no secrets, scheduled trading, long optimization or full historical research. Report queued checks honestly; do not wait when independent work remains.

## Remote preservation and integration

Work on research/on-demand-btc-20260920. Main may receive the redesign only after economic targets and necessary trading-safety checks actually pass. A checkpoint is not completion.

Commit meaningful work promptly. Prefer native Git, then authorized connectors. Read the current branch before writes and preserve concurrent work. Verify remote commit, tree and file identities. Large originals must remain recoverable without transferring full archives/base64/huge JSON through model context; use file-backed transfer or deterministic verified parts.

The .transfer packet is historical recovery evidence, not current source. Its exporter is read-only. Never run a restoration that blindly overwrites later files. Preserve packet and current snapshot independently; reconcile intentionally. Keep PROJECT_STATE.md as the single current recovery entry.
