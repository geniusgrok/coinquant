# Coinquant engineering rules

Repository: geniusgrok/coinquant. Use the personal / geniusgrok GitHub connection.

## Current mandate

Current mandate (2026-09-27): the best completed, comparable, safety-valid research account is the development default even when the 150% economic goal remains unmet. The currently selected historical candidate is SX60 with the DFII10 flat-account long overlay. Integrate its model into the one bounded-session path; do not relabel the historical sparse-call proxy as a measurement of current session timing. One manual start runs repeated reconcile/decide/execute cycles until its configured deadline or interruption. Production code and offline API-tape replay share `session.run` and `Lifecycle`. Legacy inverse/Bybit implementations live under `research/legacy`, never the production import path. `run --execute` remains blocked pending actual native qualification and current-session economic acceptance; this task does not authorize live/Testnet orders.

Update (2026-09-28, owner decisions): the default is now measured on the current session timing by `research.rebuild` (meter M5, frozen 795-session schedule in `research/session_schedule.json`). The owner accepted the measured mark/trade divergence bound for the 29 missing official mark minutes on 2020-01-19 (`path_complete=false`) and the primary risk 7.5 selected under that basis: P5 153.87% CAGR / 44.73% MDD; fee, slippage and depth stresses 147.97–149.27%; random 20% session skip 101.06%. The default model opens no shorts. `run --execute` remains blocked and qualification remains NOT_QUALIFIED. See `evidence/rebuild-20260927/RESULT.md`.

Current acceptance identity is research/spec.json (Binance bounded sessions). Frozen historical assumptions remain byte-identical in research/legacy/spec.json; coinquant.research.spec() loads only that historical benchmark. The old frozen sparse schedule is preserved for historical comparability. It does not certify the new session timing. Historical sparse-call accounts are never relabeled as current-session results. Native unresolved items and concrete acceptance steps are in `evidence/bounded-session-20260926/RESULT.md`.

Maintain one manually triggered BTC perpetual system, one quantitative model, one Binance exchange adapter, and one current configuration. Binance BTCUSDT USDT-settled linear perpetual is the only target market. Strategy, risk, dependencies and architecture may be replaced when evidence supports the change. Retained Bybit/OKX evidence is historical research, not a production support requirement.

Economic targets remain cost-net CAGR >= 150% and continuous full-account MDD < 50%, from 2020-01-01T00:00:00Z through 2026-09-20T00:00:00Z exclusive. Start with CNY 10,000 and no additions; include contract history, costs, funding, liquidation, CNY/USDT valuation and the current session decision/execution timing. Freeze the session-start schedule before a new measurement; historical sparse invocation results remain comparisons only. Do not move the window, lower targets, fabricate data, or describe proxy results as production qualification.

The frozen market-independent draws are in research/invocation_draws.json; research/legacy/spec.json binds their SHA-256. Keep the complete normal and absence-stress invocation sequences fixed. Names and repository metadata must not determine economic inputs.

## Development baseline

Main is the canonical development/integration baseline, not certification of production safety or profitability. Read the real remote HEAD before writes. Use normal fast-forward or PR merge operations and respect GitHub protection. Do not force push, overwrite parallel work, or delete historical research branches. New work starts from current main; short-lived branches may isolate changes and then normally merge back.

Historical (2026-09-27): the formal sparse-call DFII10 account (108.228852% CAGR, 39.779796% MDD) outranked its paired SX60 account (102.626204%, 39.885115%) under the user's promotion rule; current-session measurements now rank candidates. Select the best complete, comparable, audited account within the risk and safety constraints as the single default; report remaining distance to the 150% goal, rather than making that goal a promotion gate. Development-only, interrupted, mismatched or unsafe accounts cannot supersede a completed result. Do not enable execute, relax trading safety, or authorize real/Testnet orders or account changes. Qualification remains NOT_QUALIFIED until its actual evidence passes. Keep default selection and production enablement separate.

## Execution safety

Default read-only. Live execution requires explicit current authorization and a matching configured account. Engineering tasks do not authorize trading, transfers, credentials or account-setting changes. Reconcile positions, ordinary and conditional orders, and fills before deciding. Unknown responses are neither failure nor success: persist intent and query stable identity before retry. An unavailable account query never means an empty account.

Use one-way isolated positions with exchange leverage fixed at 20, not necessarily 20x account exposure. Filled exposure needs native full-position TP/SL including partial fills. Protection must survive process exit. Do not leave entry remainders able to reopen unprotected exposure after a stop. Keep valid protection during amendments. Unknown funds, orders or protection stop new exposure; only explicitly authorized risk reduction is allowed. Do not invent offline client actions or substitute a background daemon for run_once.

The Python package is coinquant, the Binance credential variables are COINQUANT_BINANCE_KEY and COINQUANT_BINANCE_SECRET, and client IDs use cq-. Preserve the configured account state directory and reconcile durable intents before any action; never treat a new empty directory as proof that the account is flat.

## Engineering and verification

Understand real call paths. Reuse shared account, sizing, campaign and execution components. Keep the production path small; avoid obsolete strategy/adapter compatibility and unrelated refactors. Apply available PonyTail when relevant; absence of the skill is not a reason to invent its use or block independent work. No mandatory TDD, coverage target or redundant approval process.

Use risk-driven minimum necessary validation for funds, orders, idempotency, protection, causality and sparse execution. Reuse economic evidence only when source/config/input identities still apply. Historical source digests identify their recorded measurement, not the current working tree. Missing native checks remain unverified. Neither accounting identity nor unit tests prove economic or live-trading qualification.

Keep one lightweight CI workflow, one Python environment and timeout-minutes: 10. No real-account secrets, scheduled trading, optimization or full historical research in CI. Normal CI has contents: read. Remove temporary publishing tools before integration.

## Preservation and recovery

Preserve meaningful code, configuration, reports and complete economic originals. Prefer native Git and file-backed/programmatic transfers, then authorized connectors. Do not route full archives/Base64/huge JSON through model context. Use verified parts when needed, with fixed source versions and length/hash checks; verify remote bytes, Git objects, tree, commit and target ref. Inspect remote state before retrying an unknown write.

Use PROJECT_STATE.md as the current recovery entry and HANDOFF_PROMPT.md for continuation; do not create duplicate progress systems. Historical source snapshots are not current code and must not overwrite main. A merge, PR or checkpoint does not complete the 150%/<50% objective.
