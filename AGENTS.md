# Coinquant engineering rules

Repository: geniusgrok/coinquant. Use the personal / geniusgrok GitHub connection.

## Current mandate

Current state (2026-09-29): one manually triggered Binance BTCUSDT USDT-settled linear perpetual system, one model (SX60+DFII10), one Binance adapter and one configuration. One manual start runs repeated reconcile/decide/execute cycles until its configured deadline or interruption. Production and offline replay share `session.run` and `Lifecycle`. The primary risk is 7.5 (`coinquant.campaign.PRIMARY_RISK`, reselected by protocol R3 on meter M8 after the O1 audit had lowered it to 6) and the macro overlay 3.6. The default model opens no shorts. Default CLI operation is read-only. The owner authorized controlled Demo and dedicated small live trial entrypoints; this engineering task does not authorize the agent to place orders, alter accounts or transfer funds. Trial access does not establish routine production qualification.

The acceptance identity is `research/spec.json`. The economic meter is `research.rebuild` (meter M8: reads take 200 ms of simulated time) on the frozen 795-session schedule `research/session_schedule.json`, verified by its recorded SHA-256. The owner accepted the measured mark/trade divergence bound for the 29 missing official mark minutes on 2020-01-19 (`path_complete=false`). The historical P7 (153.86% / 44.73%) was measured on source `a6892b3` (meter M7 let the local request weight decide the outcome, protocol O0; M8 removes that dependence). Protocol M10 remeasured the registered scenarios on the current source (`evidence/remeasure-20260929-m10/`, digest `6504a24b…`): risk 7.5 is CNY 1,893,613 / 118.24% CAGR / 44.51% MDD, so the CAGR target is not met. The same R3 rule still selects 7.5, and `PRIMARY_RISK` is unchanged. Fee +50%, exit slippage x2 and 10% depth finish above that base (126.17% / 121.92% / 128.57%); a 20% session skip finishes at 95.69% with MDD 45.39%; the absence sequence and the 21-day block match the base. The full-window value is not monotone in risk (6 / 6.5 / 7 / 7.5: CNY 1.70M / 2.02M / 2.21M / 1.89M) or in read latency at risk 6 (100 / 200 / 400 ms: CNY 2.54M / 1.70M / 0.88M). These account outcomes match historical M9 (`ae7b3fd8…`); the only recorded difference is 20 fewer trailing observation timeouts (688 rather than 708) after a sub-millisecond virtual wait advances at least one millisecond. Economic qualification remains `NOT_MET`. The R3 figure of 131.26% describes only `evidence/robustness-20260929/m8/`. Single-parameter neighbours of the signal constants fell to 40–102% CAGR on M7 and were not remeasured. See `evidence/remeasure-20260929-m10/RESULT.md`. Native unresolved items and acceptance steps are in `evidence/bounded-session-20260926/RESULT.md`.

Economic targets remain cost-net CAGR >= 150% and continuous full-account MDD < 50%, from 2020-01-01T00:00:00Z through 2026-09-20T00:00:00Z exclusive. Start with CNY 10,000 and no additions; include contract history, costs, funding, liquidation, CNY/USDT valuation and the session decision/execution timing. Keep the session schedule frozen before any new measurement. Do not move the window, lower targets, fabricate data, or describe proxy results as production qualification. Names and repository metadata must not determine economic inputs.

Strategy, risk, dependencies and architecture may be replaced when evidence supports the change. The repository keeps only the current version: the retired Bybit/inverse code, the sparse-invocation specification and draws, and historical candidate research were removed on 2026-09-28 and remain in Git history (`3e9a696` and earlier).

## Development baseline

Main is the canonical development/integration baseline, not certification of production safety or profitability. Read the real remote HEAD before writes. Use normal fast-forward or PR merge operations and respect GitHub protection. Do not force push, overwrite parallel work, or delete historical research branches. New work starts from current main; short-lived branches may isolate changes and then normally merge back.

Select the best complete, comparable, audited account within the risk and safety constraints as the single default; report remaining distance to the 150% goal rather than making that goal a promotion gate. Development-only, interrupted, mismatched or unsafe accounts cannot supersede a completed result. Controlled trial writes require explicit environment, UID and capital limit; small live trials additionally require reviewed Demo closure from matching execution code. Do not authorize the agent to trade or alter accounts. Qualification remains NOT_QUALIFIED until its actual evidence passes. Keep default selection and production enablement separate.

## Execution safety

Default read-only. Live execution requires explicit current authorization and a matching configured account. Engineering tasks do not authorize trading, transfers, credentials or account-setting changes. Reconcile positions, ordinary and conditional orders, and fills before deciding. Unknown responses are neither failure nor success: persist intent and query stable identity before retry. An unavailable account query never means an empty account.

Use one-way isolated positions with exchange leverage fixed at 20, not necessarily 20x account exposure. Filled exposure needs native full-position TP/SL including partial fills. Protection must survive process exit. Do not leave entry remainders able to reopen unprotected exposure after a stop. Keep valid protection during amendments. Unknown funds, orders or protection stop new exposure; only explicitly authorized risk reduction is allowed. Do not invent offline client actions or substitute a background daemon for the manually started session.

The Python package is coinquant, the Binance credential variables are COINQUANT_BINANCE_KEY and COINQUANT_BINANCE_SECRET, and client IDs use cq-. Preserve the configured account state directory and reconcile durable intents before any action; never treat a new empty directory as proof that the account is flat.

## Engineering and verification

Understand real call paths. Reuse shared account, sizing, campaign and execution components. Keep the production path small; avoid obsolete strategy/adapter compatibility and unrelated refactors. Apply available PonyTail when relevant; absence of the skill is not a reason to invent its use or block independent work. No mandatory TDD, coverage target or redundant approval process.

Use risk-driven minimum necessary validation for funds, orders, idempotency, protection, causality and session execution. Reuse economic evidence only when source/config/input identities still apply. Historical source digests identify their recorded measurement, not the current working tree. Missing native checks remain unverified. Neither accounting identity nor unit tests prove economic or live-trading qualification.

Keep one lightweight CI workflow, one Python environment and timeout-minutes: 10. No real-account secrets, scheduled trading, optimization or full historical research in CI. Normal CI has contents: read. Remove temporary publishing tools before integration.

## Preservation and recovery

Keep current code, configuration, reports and the complete originals of the current economic results; superseded material lives in Git history, not the working tree. Prefer native Git and file-backed/programmatic transfers, then authorized connectors. Do not route full archives/Base64/huge JSON through model context. Use verified parts when needed, with fixed source versions and length/hash checks; verify remote bytes, Git objects, tree, commit and target ref. Inspect remote state before retrying an unknown write.

Use PROJECT_STATE.md as the current recovery entry and HANDOFF_PROMPT.md for continuation; do not create duplicate progress systems. Historical source snapshots are not current code and must not overwrite main. A merge, PR or checkpoint does not complete the 150%/<50% objective.
