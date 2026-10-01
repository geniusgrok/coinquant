# BTC perpetual comparison and execution traces — 2026-10-01

`comparison.json` freezes Coinquant default, Starquant default and Starquant
half-risk. Nine unresolved dimensions block ranking: operation schedule,
mark valuation, fills, fees, slippage, request latency, funding, FX/conversion
and missing-input handling. Common reference: the frozen 795 finite manual
sessions. Both repositories' old returns stay under their original identities;
this report is a comparison protocol, not newly aligned full-window accounts.
The 150% CAGR / MDD <50% goal and default configuration are unchanged.

Five diagnostic request/cycle traces in `traces/` reproduce every corresponding
M10 fill prefix exactly: risk 6 at 100/200/400 ms through January 3, and risk
7.5 at original/1.5x fee through January 14. Fourteen official daily trade
archives were restored and checked. Compressed JSONL holds request timing,
rounded orders, stable client IDs, pre/post wallet and position, model preview
and cycle results; `summary.json` records source/input/trace identities.

`first-order-divergence.json` shows the first differing IOC requested quantity:
1.675 vs 1.671 BTC at the same instant/price/ID, with wallet 2764.150082 vs
2758.304888 USDT. This precedes the 17th fill's 0.258 vs 0.252 BTC difference.
Thus the fee effect first changes the wallet and requested size, before later
liquidity/timing decisions. It does not attribute the complete six-year residual
to one mechanism or establish expected returns. No production defect was proved
and no production timing/risk change is made.

`local-checks.json` records six named existing cases actually passing: partial
entry protection, lost ACK, unknown entry after restart, protection replacement,
disconnect and venue protection after a stopped session. Native qualification
remains NOT_QUALIFIED; these are offline cases, not exchange protocol proof.

```sh
python -m research.perp_comparison --star ../starquant/reports/btc_account_first_round.json --out evidence/comparison-NEW.json
python -m research.local_checks --out evidence/local-checks-NEW.json
python -m research.execution_trace --out evidence/traces-NEW
```

Trace inputs need the existing market restore command and Jan 1–14 aggTrades
under `/tmp/coinquant-prints`. Replays are diagnostic subwindows, never economic
qualification. Next acceptance is genuine alignment and owner-run native Demo
proof; no claim that Coinquant is already the winning perpetual executor.
