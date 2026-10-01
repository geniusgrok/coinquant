# F1: recorded execution-path attribution — 2026-10-01

Registered in `research/redesign-PROTOCOL.md`. The reusable CLI is
`python -m research.path_analysis BASE.json CHANGED.json --varying fee --out NEW.json`.
It checks source, schedule, window, valuation, declared knobs and input hashes,
reconciles the fee ledger, and refuses to overwrite its inputs or prior output.
The five analyses retain the M10 original artifact SHA-256 values and the
analysis source SHA-256. They are analyses of recorded accounts, not new
full-window economic measurements.

| Change | First differing fill | Differing fields |
| --- | ---: | --- |
| Fee +50% | 17 | Quantity: 0.258 -> 0.252 BTC, same time and price |
| Exit slip x2 | 3 | Price |
| Depth participation 10% | 77 | Quantity: 4.418 -> 3.708 BTC |
| Risk 6, reads 100 ms | 1 | Time and quantity |
| Risk 6, reads 400 ms | 1 | Time, quantity and price |

At fixed baseline fills, fee +50% costs **7,644.14 USDT more**. The recorded
changed account ends **76,658.97 USDT higher**; the remaining **84,303.11 USDT**
is the combined effect of all ensuing path changes. This residual does not
identify one causal mechanism and is not standalone trading profit. Extra
fees cannot improve the fixed-fill calculation. Sizing, minimum-order and
stop-budget decisions subsequently differ between the complete accounts.

Current-source execution probes restored three official aggTrades files
matching M10 hashes and replayed 2020-01-01 through 2020-01-04 at 200 and
400 ms (three frozen sessions each, simulated UIDs 1 and 2). Both reproduce
the corresponding two-fill M10 prefixes exactly. `probes.json` records the
input/source identity and raw scratch report hashes. The short-window
returns are deliberately not presented as economic qualification.

Decision: no proven production implementation defect was found in these
divergences, so no speculative timing or risk change is promoted. The
remaining full-window sensitivity is unresolved; latency affects entry time
and liquidity, and one delay cannot be treated as a stable expected return.
No fresh complete six-year replay was run: only three of the original 768
print archives were restored. Historical M10 mark-gap and execution-model
limitations remain. Economic qualification is `NOT_MET`; native qualification
is `NOT_QUALIFIED`.

325 offline tests pass. The tool makes future execution revisions traceable
and rejects mixed experiments. Event-by-event causal tracing is still needed
before attributing the residual to a particular production decision.

For eventual two-project use: Spotquant is the spot destination. Coinquant
and Starquant remain perpetual alternatives. Coinquant is an execution-base
candidate because session and replay share Lifecycle; Starquant's useful
short, trend and pyramid behavior requires explicit migration and remeasurement.
Finite manual sessions and continuous operation are different strategies.
Choose one operation schedule and one account executor before any migration;
native recovery/protection proof is still missing for both alternatives.
