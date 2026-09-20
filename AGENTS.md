# Pancakequant Repository Instructions

## Current task and authority

Build a personal, manually triggered BTC perpetual system. A run reconciles the real account, obtains complete fresh market data, computes one reproducible strategy target, executes only when explicitly authorized, verifies exchange-hosted full-position take profit and stop loss, saves recovery state, reports, and exits. No daemon or unattended scheduler.

The user's 2026-09-20 redesign mandate supersedes old architecture and acceptance constraints. All code, strategy, risk, configuration, dependencies, tests, and structure may be replaced or removed. Retain existing implementations only when they serve this mandate. Preserve LICENSE, attribution, trading records, and evidence; Git holds obsolete implementations, not parallel production entrypoints.

## Hard boundaries

- One BTC perpetual contract, one production exchange adapter, one core decision model and one current configuration example.
- Default one-way isolated margin, exchange leverage exactly 20. Effective account exposure need not be 20x. Never silently change a real account's settings.
- This task authorizes engineering, research, necessary checks, commits and remote preservation, NOT live orders, fund transfers, credential changes or real account configuration changes.
- Read-only is the default even when API keys exist. An explicit execution flag and a matching authorized account are required for future execution.
- Exchange state is authoritative. Reconcile ordinary and conditional orders, positions, balances and fills before decisions, including repeated runs on the same candle.
- Stable client IDs, durable intents and reconciliation precede any retry after an unknown result. Unknown is not failed, flat, cancelled or filled.
- Every increase needs native full-position TP/SL including actual partial fills. Leave an entry resting offline only after its partial-fill and residual-order/exit linkage is verified. Otherwise cancel and confirm the unprotected remainder, and report the unsupported capability.
- Do not remove valid exchange protection at shutdown. Repair protection before adding risk. Reduce/close only within authorization; report network uncertainty honestly.
- Check liquidation, margin, fees, funding, quantity/price precision, liquidity and exchange limits. Do not hide insolvency or use martingale to manufacture returns.

## Economic acceptance

Initial capital is CNY 10,000, not USDT 10,000. Formal continuous-account window starts 2020-01-01T00:00:00Z and ends at a locked, genuinely available complete 2026 endpoint. Freeze currency conversion, contract, data, costs and market-independent sparse irregular invocation schedule before candidate comparisons.

Only economic gates: whole-window CAGR > 200% and mark-to-market account MDD < 20%. Do not relax either gate or replace its definition. Include intrarun and between-invocation loss, funding, transaction costs, historical margin/liquidation and capacity. Native hosted exits may execute between invocations; strategy decisions may not. Separate development from chronological validation. Proxy data, current-rule approximations and incomplete coverage are not formal qualification.

Engineering checks, economic qualification, testnet checks and live performance are separate facts. A failing or unmeasured candidate remains on the research branch, not main. Merge only after current economic and necessary safety requirements are evidenced and repository rules permit it.

## Engineering and preservation

Trace actual call paths before editing. Prefer the simplest sufficient integrated implementation; no compatibility layers, unused adapters, strategy menus or parameter-search platform. Use available PonyTail when applicable; other skills must not add unrequested approval or forced TDD gates.

Use risk-driven targeted checks; no coverage targets or automatic full-history reruns. Keep default-not-live, unknown-write recovery, idempotency, partial-fill protection, reduce-only, protection continuity and sparse replay checks. At most one short single-Python workflow with timeout-minutes: 10; no real keys, scheduled trading or full-history optimization in CI.

Commit and push meaningful changes and raw evidence promptly to the existing research branch. Prefer native Git; if unavailable use the authorized connector without exposing credentials. No giant strings, base64 archives or model-mediated large-file transfers. Verify remote ref, tree and content identity after writes. Keep PROJECT_STATE.md current with evidence, blockers and the most direct recovery action. Check for parallel changes before branch updates or integration. A checkpoint is not completion.
