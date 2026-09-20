# Pancakequant Project State

## Active objective

Implement the user's 2026-09-20 on-demand BTC perpetual redesign. Formal targets remain CNY 10,000 initial capital, start 2020-01-01 UTC, CAGR > 200%, account MDD < 20%, exchange leverage 20x. No live trading or account-setting changes are authorized now.

## Repository and recovery

- Repository: ychenracing/pancakequant
- Active branch: research/on-demand-btc-20260920 (reuse; do not create another candidate branch).
- Verified baseline/main: c886b7c63c6455bd7c933269e32cd35a6fb3e09a.
- Main remains unchanged until the new mandate is genuinely satisfied.
- Native Git cannot resolve github.com in this execution environment. Authorized GitHub connector reads work; preserve small changes through the connector. Large originals must use file-backed transfer, not model strings.

## Evidence so far

The main entry defaults to a live-capable old bot and loops after run; the factory dynamically selects legacy strategies. Bot imports multiple unused exchange adapters and hyperopt, and has cancel_all_orders_at_stop=True. These are source observations, not execution tests. Current AGENTS.md supersedes the old requirement to preserve the existing architecture.

No economic result, exchange integration check, full historical dataset, production adapter selection, fixed conversion rate, or verified complete research endpoint exists yet. Do not report any gate as passed. No API credentials were read and no exchange write was made.

## Immediate work

Finish tracing the old strategy/stop/adapter paths. Select one native hosted-protection mechanism using current official documentation and verify historical contract coverage independently. Build a single bounded run-once path, persistent intent reconciliation, shared strategy/risk model, conservative sparse-event replay and compact CLI. Preserve each meaningful implementation increment remotely with raw targeted-test evidence. Keep unresolved partial-fill/offline-order semantics explicit rather than inventing success.
