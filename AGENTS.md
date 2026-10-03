# Coinquant engineering rules

Repository: geniusgrok/coinquant. Use the personal / geniusgrok GitHub connection.

## Current mandate

Current state (2026-09-29): one manually triggered Binance BTCUSDT USDT-settled linear perpetual system, one model (SX60+DFII10), one Binance adapter and one configuration. One manual start runs repeated reconcile/decide/execute cycles until its configured deadline or interruption. Production and offline replay share `session.run` and `Lifecycle`. The primary risk is 7.5 (`coinquant.campaign.PRIMARY_RISK`, reselected by protocol R3 on meter M8 after the O1 audit had lowered it to 6) and the macro overlay 3.6. The default model opens no shorts. Default CLI operation is read-only. The owner authorized controlled Demo and dedicated small live trial entrypoints; this engineering task does not authorize the agent to place orders, alter accounts or transfer funds. Trial access does not establish routine production qualification.

The acceptance identity is `research/spec.json`. The economic meter is `research.rebuild` (meter M8: reads take 200 ms of simulated time) on the frozen 795-session schedule `research/session_schedule.json`, verified by its recorded SHA-256. The owner accepted the measured mark/trade divergence bound for the 29 missing official mark minutes on 2020-01-19 (`path_complete=false`). The historical P7 (153.86% / 44.73%) was measured on source `a6892b3` (meter M7 let the local request weight decide the outcome, protocol O0; M8 removes that dependence). Protocol M10 remeasured the registered scenarios on the current source (`evidence/remeasure-20260929-m10/`, digest `6504a24b…`): risk 7.5 is CNY 1,893,613 / 118.24% CAGR / 44.51% MDD, so the CAGR target is not met. The same R3 rule still selects 7.5, and `PRIMARY_RISK` is unchanged. Fee +50%, exit slippage x2 and 10% depth finish above that base (126.17% / 121.92% / 128.57%); a 20% session skip finishes at 95.69% with MDD 45.39%; the absence sequence and the 21-day block match the base. The full-window value is not monotone in risk (6 / 6.5 / 7 / 7.5: CNY 1.70M / 2.02M / 2.21M / 1.89M) or in read latency at risk 6 (100 / 200 / 400 ms: CNY 2.54M / 1.70M / 0.88M). These account outcomes match historical M9 (`ae7b3fd8…`); the only recorded difference is 20 fewer trailing observation timeouts (688 rather than 708) after a sub-millisecond virtual wait advances at least one millisecond. Economic qualification remains `NOT_MET`. The R3 figure of 131.26% describes only `evidence/robustness-20260929/m8/`. Single-parameter neighbours of the signal constants fell to 40–102% CAGR on M7 and were not remeasured. See `evidence/remeasure-20260929-m10/RESULT.md`. Native unresolved items and acceptance steps are in `evidence/bounded-session-20260926/RESULT.md`.

Economic targets remain cost-net CAGR >= 150% and continuous full-account MDD < 50%, from 2020-01-01T00:00:00Z through 2026-09-20T00:00:00Z exclusive. Start with CNY 10,000 and no additions; include contract history, costs, funding, liquidation, CNY/USDT valuation and the session decision/execution timing. Keep the session schedule frozen before any new measurement. Do not move the window, lower targets, fabricate data, or describe proxy results as production qualification. Names and repository metadata must not determine economic inputs.

Strategy, risk, dependencies and architecture may be replaced when evidence supports the change. The repository keeps only the current version: the retired Bybit/inverse code, the sparse-invocation specification and draws, and historical candidate research were removed on 2026-09-28 and remain in Git history (`3e9a696` and earlier).

## Current complete BTC edge delivery (2026-10-03)

Complete71 registered original accounts and5 separately source-bound canonical Spot accounts independently PASS; evidence/btc-edge-20261003 retains all raw/negative/failure/proof identities. Coin quality-budget/cost-horizon/crowding all reject registered paired gates; quality/cost also fail actual risk upper bands. Default SX60+DFII10/primary7.5/macro3.6/scale1 remains unchanged,119.2284% cost-net CNY CAGR/44.1051% original continuous minute/envelope proxy MDD,150%/<50% goalsNOT_MET. Original producer37061/Pythonba638 remains distinct from later metadata/mergeHEADs. Preserve protected source modes/bytes and original Git objects; no schedule/start/capital optimization. Spot adopts crowding development change only after independent71+5 proof, with zero actual historical halving events and missing-input-blocking interpretation disclosed. Runtime repos remain separate and Coin forward reader is standalone.

Current result/operation: research/edge-RESULT.md and edge-GUIDE.md. Actual forward ledgers begin cold CNY10000/BTC0/events0 at realUTC, no backfill and no prospective/native claim. Coin later mark-path uncertainty stays unresolved rather than inventing fills. Nativecases0/accountdays0/NOT_QUALIFIED. User verification policy: reuse passed unchanged scoped/financial evidence; no optional/repeated tests, one final fullCI perrepo. All Coin account producers/tests sharingUID are strictly serial; never change HOME/UID/locks. Engineering work does not authorize private accounts/orders/transfers/settings.

## Previous complete BTC alpha/beta delivery (2026-10-02)

Evidence/alpha-beta-next-20261002 preserves the complete registered64-account inventory: Spot28/Coin20 unscaled cases, actualSpot7/Coin5 trained-risk controls and four prescribed incumbent capital/start sensitivities. Five additional canonical Spot shared-runtime cases establish a separate source bridge; they do not count as native trades. Spot selects consensus plus ATR-stop; Coin rejects all four new mechanisms and retains SX60+DFII10/primary7.5/macro3.6/defaultscale1. No multi-component combination applies, no capital optimum is selected and no short is introduced. Registered start-minus/plus60s CAGR136.018640%/127.114524% versus original119.228356% shows material execution-timing sensitivity; neither offset is selected and the frozen schedule is unchanged.

Coin unscaled base remains119.2284% cost-net CNY CAGR/44.1051% continuous minute/envelope proxy MDD, finalCNY1951753.808294805224630873758. Original150%/<50% goal remainsNOT_MET; nativecases0/actual accountdays0/NOT_QUALIFIED. The20-case frozen producer is acedaa43ca94223f24e2fe11851bbef74e032a69/Pythona6e3f30f02208ff7e604b6181c5d8fa7000fe7e30dbc3276fbcc93ffbb0ad227; immutable assessor99 and original input/source identities remain in raw receipts even after metadata integration.

The original risk unity control failed operating equality in two snapshots; its financial/fill/daily/ownership/remaining groups matched but the failure was not waived. The trace is consistent with the independently demonstrated public print acquisition HTTPError propagation path; historical remote status and CHECKSUM-versus-ZIP origin URL were not recorded, so exact remote response attribution is unavailable. A complete actual incumbent replay precedes strict all-six equality. Four other original risk rows are kept as an explicitly parent-bound lossless projection with every whole row, journal, source, profile and condition structurally identical; the complete original raw bytes remain retained; one-level manifest plus new repaired final/index form successful evidence. Original failedraw/reports/BLOCKEDreview are retained separately. No ignored operating clocks/status, source relabel, UID/HOME/cache/lock bypass or automatic reroll is permitted.

Actual risk matching uses the frozen7312020–2021training window and actual2022+accounts, volatility<=baseline1.05/beta<=baseline+.02; it is an upper-band diagnostic, not equality or prospective alpha. Fresh/topup satisfy risk bands but lose validation returns; ATR/compression fail risk bands. Continuous minute/envelope MDD remains a bounded historical proxy, not independently second-engine replay/native execution;29missing-mark bound and other disclosed hindsight path envelopes remain. Old joint allocation evidence uses old Spot consensus, not the newly adopted ATR runtime. Research forward diaries bind immutable researchsource99/aced and start allcash/noevents at actual UTC.

Synthetic Coin producers/tests sharing UIDs MUST run strictly serially: separate cache/state directories do not isolate Path.home account locks. Never change HOME or delete/bypass locks. Public ZIP observers may only retain verified original public bytes outside the active cache; restore between producer jobs with receipts. Freeze producer/evaluator HEADs and protected source through all financial producers and audits. Latest delivery results do not change defaultread-only or owner-controlled trial authorization.

## Shared comparison (2026-10-01)

Third-round fixed candidates completed the 795 shared historical sessions.
At Coin source 00a6849 and Star source 882b521: Coin default 119.23% CAGR /
44.11% MDD; Star default -3.68% / 51.75%; half-risk -1.27% / 38.21%.
Full cash-ledger audit passed. This is a proxy venue with a simplified peer
snapshot and a legacy initial metric FX point, not native adapter timing or
execution proof. See evidence/third-round-20261001/RESULT.md and assessment.json.
Retain Coinquant as the perpetual development runtime and Spotquant as spot;
Starquant stays research. No strategy promotion, retirement or native enablement.
Economic NOT_MET, native NOT_QUALIFIED. Historical M10 keeps its own recorded
source identity; do not label its old digest as the current tree. snapshot
exports and concurrent reports are read-only; actual account days remain zero.

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

`.cursor/install.sh` installs Python 3.13 with uv and links `python`, `python3`, and `python3.13` into `/usr/local/bin`. The package and the offline suite use the standard library only. There is no requirements file and no long-running service to start.

The CI check is:

```sh
python -m compileall -q coinquant research tests
python -m unittest discover -s tests
```

`python -m coinquant status --config <file>` is the read-only observation entry. With `COINQUANT_BINANCE_KEY` and `COINQUANT_BINANCE_SECRET` unset it stops before any exchange call. Do not set trading credentials or pass `--execute`.
