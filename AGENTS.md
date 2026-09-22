# Coinquant engineering rules

Repository: geniusgrok/coinquant.

## Repository migration: 2026-09-23 (Asia/Tokyo)

The user migrated this project from ychenracing/pancakequant to geniusgrok/coinquant. Use the personal GitHub connection (geniusgrok) for current repository work. The source repository is preserved and must not be modified for coinquant tasks. Original branches, tags, commits and research evidence retain their identities. The Python package and PANCAKEQUANT environment-variable names remain unchanged; this migration does not change strategy, configuration, trading permissions or economic qualification.

## Current mandate

Maintain one manually triggered BTC perpetual system, one quantitative model, one Binance exchange adapter, and one current configuration. Binance BTCUSDT USDT-settled linear perpetual is the only target market. All existing strategy, risk, dependencies and architecture may be replaced when evidence supports the change. Retained Bybit/OKX evidence is historical research, not a production support requirement.

Economic targets remain cost-net CAGR >= 150% and continuous full-account MDD < 50%, from 2020-01-01T00:00:00Z through 2026-09-20T00:00:00Z exclusive. Start with CNY 10,000 and no additions; include contract history, costs, funding, liquidation, CNY/USDT valuation and the original frozen sparse invocation sequence. Research-frequency success does not substitute for sparse acceptance. Do not move the window, lower targets, fabricate data, or describe proxy results as production qualification.

## Development integration authorization: 2026-09-22

The user explicitly requested merging the research work into main and basing subsequent development on main. This replaces the old requirement to reach the economic targets before any main integration. Main is now the canonical development/integration baseline, not a certification that the model is safe or profitable in production.

Restore and verify the previously Library-only sustainable-capital/planned-exit implementation before claiming that main contains it. Preserve all existing evidence, failed results and original identities. Read the real remote HEAD before writes; use normal fast-forward or PR merge operations and respect GitHub protection. Do not force push, overwrite parallel work, or delete the historical research branch. New work starts from current main; short-lived branches may be used for isolated changes, then normally merged back.

This authorization does not promote SX60 to a live default, change the existing 3.6 reference/default paths, enable execute, relax trading safety, or authorize any real/Testnet order or account modification. Economic qualification remains NOT_QUALIFIED until its evidence actually passes. Keep development integration, research candidate selection, and production enablement separate.

## Execution safety

Default read-only. Live execution requires explicit current authorization and a matching configured account. This engineering task does not authorize trading, transfers, credentials or real account-setting changes. Reconcile positions, ordinary and conditional orders, and fills before deciding. Unknown responses are neither failure nor success: persist intent and query stable identity before any retry. An unavailable account query never means an empty account.

The intended execution uses one-way isolated positions with exchange leverage fixed at 20, not necessarily 20x account exposure. Filled exposure needs native full-position TP/SL including partial fills. Protection must survive process exit. Do not leave entry remainders able to reopen unprotected exposure after a stop. Keep valid protection during amendments. Unknown funds, orders or protection stop new exposure; only explicitly authorized risk reduction is allowed. Do not invent offline client actions or substitute a background daemon for run_once.

## Engineering and verification

Understand real call paths. Reuse shared account, sizing, campaign and execution components. Keep the production path small; avoid obsolete strategy/adapter compatibility and unrelated refactors. Apply available PonyTail when relevant; absence of the skill is not a reason to invent its use or block independent work. No mandatory TDD, coverage target or redundant approval process.

Use risk-driven, minimum necessary validation for funds, orders, idempotency, protection, causality and sparse execution. Reuse evidence only when source/config/input identities still apply. A code publication/merge need not repeat unchanged economic accounts. Missing native checks remain unverified. Neither accounting identity nor unit tests prove economic or live-trading qualification.

Keep one lightweight CI workflow, one Python environment, timeout-minutes: 10; no real-account secrets, scheduled trading, optimization or full historical research in CI. One-time exact-source recovery may write only the authorized research branch, check fixed before/after hashes and offline tests, then remove its publisher and restore contents: read in the same commit. Do not leave temporary acquisition/publishing steps on main.

## Preservation and recovery

Preserve meaningful code, configuration, reports and recovery state promptly. Prefer native Git and file-backed/programmatic transfers, then authorized connectors. Large originals must remain fully recoverable without full archives/Base64/huge JSON in model context. Use deterministic patches or verified parts when necessary, with fixed source versions and length/hash checks; verify remote bytes, Git objects, tree, commit and target ref. Unknown writes require remote-state inspection before retry.

The old .transfer packet is historical evidence, not current source. Do not blindly restore it over newer code. Keep PROJECT_STATE.md as the current recovery entry and HANDOFF_PROMPT.md as the concise continuation entry; no duplicate progress systems. Main integration, a PR, or a checkpoint is not completion of the 150%/<50% objective.
