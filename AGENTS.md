# Coinquant engineering rules

Repository: geniusgrok/coinquant. Use the personal / geniusgrok GitHub connection.

## Current mandate

Current state (2026-09-29): one manually triggered Binance BTCUSDT USDT-settled linear perpetual system, one model (SX60+DFII10), one Binance adapter and one configuration. One manual start runs repeated reconcile/decide/execute cycles until its configured deadline or interruption. Production and offline replay share `session.run` and `Lifecycle`. The primary risk is 6 (`coinquant.campaign.PRIMARY_RISK`, lowered from 7.5 by the O1 overfitting audit) and the macro overlay 3.6. The default model opens no shorts. Default CLI operation is read-only. The owner authorized controlled Demo and dedicated small live trial entrypoints; this engineering task does not authorize the agent to place orders, alter accounts or transfer funds. Trial access does not establish routine production qualification.

The acceptance identity is `research/spec.json`. The economic meter is `research.rebuild` (meter M7) on the frozen 795-session schedule `research/session_schedule.json`, verified by its recorded SHA-256. The owner accepted the measured mark/trade divergence bound for the 29 missing official mark minutes on 2020-01-19 (`path_complete=false`). The historical P7 (153.86% / 44.73%) was measured on source `a6892b3` and no longer describes the current code: the same default trial measures 0.9–3.4 million CNY depending on request-weight use (protocol O0). The current default O1 (risk 6) measures 96.14% CAGR / 37.51% MDD, so the CAGR target is not met; fee, slippage and depth stresses measure 95.2–96.1% and the random 20% session skip 79.35%. Single-parameter neighbours of the signal constants fall to 40–102% CAGR, so the model constants sit on peaks. See `evidence/robustness-20260929/RESULT.md` and `evidence/rebuild-20260927/RESULT.md`. Native unresolved items and acceptance steps are in `evidence/bounded-session-20260926/RESULT.md`.

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

## Cursor Cloud specific instructions

- `.cursor/install.sh` installs CPython 3.13 as `python`, `python3`, and `python3.13` on `/usr/local/bin`. The package and the test suite use the standard library only. No pip packages and no exchange credentials are required.
- Offline check, same as CI: `python -m compileall -q coinquant research tests` then `python -m unittest discover -s tests -v`.
- `python -m coinquant status --config config.example.json` and `run` stop before any exchange request when Binance credentials are absent. That blocked result is the expected development path. Do not set live or demo keys, and do not pass `--execute`.
- Do not run `python -m research.rebuild` or `python -m research.robustness` for routine verification. Those meters need the frozen market archive, which is not in the repository.
