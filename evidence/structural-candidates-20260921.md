# Structural candidate diagnostics — 2026-09-21

These are diagnostic replays on the same frozen 2020-01-01 through 2026-09-20
schedule, native Bybit BTCUSD market/funding history, and conservative proxy
historical rules. They are **NOT_QUALIFIED** and do not replace native-rule
qualification.

| Candidate | CAGR | MDD | Liquidations | Final CNY | Decision |
|---|---:|---:|---:|---:|---|
| Current baseline | 43.92% | 77.05% | 8 | ¥115,452 | baseline |
| M1 buffered isolated margin | 43.51% | 77.25% | 9 | ¥113,239 | reject |
| H4 collateral-neutralized bearish alpha | 35.02% | 76.59% | 13 | ¥75,196 | reject |
| stop-first upper-bound diagnostic | 44.16% | 77.05% | 0 | ¥116,762 | diagnostic only |

M1 tested a coherent margin-state change rather than a leverage increase:
immediate positions could allocate more already-owned BTC as isolated margin so
liquidation sat another stop-risk distance beyond the native stop. Offline FOK
entries deliberately remained safe using initial 20x margin alone, because no
process is present to add margin after an offline fill. The result was worse.

H4 tested the stronger inverse-contract hedge hypothesis. On bearish manual
invocations it targeted enough BTCUSD short exposure to neutralize BTC
collateral delta plus the existing bearish alpha and evaluated stop risk on the
complete account. It reduced MDD only marginally and materially hurt return,
while liquidations increased. Reject this structure.

The stop-first run is not an acceptance result. It is an upper-bound diagnostic
that removes all eight hourly liquidation outcomes when the 60m bar opened
above stop and stop was above liquidation. Even under that favorable ordering,
MDD stayed at 77.05%. Therefore stop/liquidation ambiguity needs evidence repair
but cannot explain the economic failure.

The next structural path is to evaluate a stable-settlement BTC linear
perpetual rather than continue tuning the BTC-settled inverse contract. OKX
BTCUSDT perpetual launched before the formal 2020 start and, since July 2026,
attached TP/SL is created on partial fills with remaining parent quantity
cancelled. Before switching production, official 2020-boundary trade/mark/funding
history must be proven accessible and the same frozen economic protocol rerun.
