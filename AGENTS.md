# Coinquant engineering rules

Repository: geniusgrok/coinquant. Use the personal / geniusgrok GitHub connection.

## Current mandate

Current engineering mandate (2026-09-26): finish the non-economic bounded-session implementation. One manual start runs repeated reconcile/decide/execute cycles until its configured deadline or interruption. Production code and offline API-tape replay share `session.run` and `Lifecycle`. Legacy inverse/Bybit implementations live under `research/legacy`, never the production import path. Default risk remains 3.6; the current session uses the same price-rule geometry in both directions, without claiming any economic promotion. `run --execute` remains blocked pending actual native qualification and economic acceptance; this task does not authorize live/Testnet orders.

The old frozen sparse schedule is preserved for historical comparability. It does not certify the new session timing. No economic account is rerun or relabeled as current in this engineering task. Native unresolved items and concrete acceptance steps are in `evidence/bounded-session-20260926/RESULT.md`.

Maintain one manually triggered BTC perpetual system, one quantitative model, one Binance exchange adapter, and one current configuration. Binance BTCUSDT USDT-settled linear perpetual is the only target market. Strategy, risk, dependencies and architecture may be replaced when evidence supports the change. Retained Bybit/OKX evidence is historical research, not a production support requirement.

Economic targets remain cost-net CAGR >= 150% and continuous full-account MDD < 50%, from 2020-01-01T00:00:00Z through 2026-09-20T00:00:00Z exclusive. Start with CNY 10,000 and no additions; include contract history, costs, funding, liquidation, CNY/USDT valuation and the frozen sparse invocation sequence. Research-frequency success does not substitute for sparse acceptance. Do not move the window, lower targets, fabricate data, or describe proxy results as production qualification.

The frozen market-independent draws are in research/invocation_draws.json; research/spec.json binds their SHA-256. Keep the complete normal and absence-stress invocation sequences fixed. Names and repository metadata must not determine economic inputs.

## Development baseline

Main is the canonical development/integration baseline, not certification of production safety or profitability. Read the real remote HEAD before writes. Use normal fast-forward or PR merge operations and respect GitHub protection. Do not force push, overwrite parallel work, or delete historical research branches. New work starts from current main; short-lived branches may isolate changes and then normally merge back.

SX60 remains a research candidate. Do not silently replace the 3.6 reference/default paths, enable execute, relax trading safety, or authorize real/Testnet orders or account changes. Qualification remains NOT_QUALIFIED until its actual evidence passes. Keep engineering integration, research candidate selection, and production enablement separate.

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
