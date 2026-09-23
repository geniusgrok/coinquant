# PIR1 development gate — 2026-09-23

## Decision

**Reject PIR1 at the development hard gate.** The candidate's annualized return rose against the paired SX60 control, but conservative maximum drawdown reached **63.933946%**, above the strict **<50%** ceiling. The protocol therefore ends this candidate here: no candidate full-window account, joint stress, or 787-call absence matrix was run.

## Paired 468-call development accounts

Both accounts used the same 2020-01-01 through 2024-01-01-exclusive window, `input_identity=9b036837f4eb462d672524f9b032adc7a9a9ba85cce071b33b268ab658747645`, 6.0 risk scale, five-minute entry proxy, sliced planned exits, 1% participation, and identical saved inputs. The protocol SHA-256 is `15860f4768446f8f422e74d50b1b6f52c5993df18c28fa916f9eb333f89d7237`.

| Account | CAGR | Conservative max drawdown | Final CNY |
|---|---:|---:|---:|
| SX60 control | 162.179152% | 37.209136% | 472,527.41 |
| PIR1 | 184.867114% | 63.933946% | 658,577.07 |

PIR1 finished **CNY 186,049.67 higher** (+39.37%) and improved CAGR by **22.687962 percentage points**. Its worst drawdown ran from the conservative peak at **2021-02-21T19:00:00Z** (51,493.93 USDT) to the conservative trough at **2021-10-12T20:00:00Z** (18,571.83 USDT).

## Signal and account checks

The causal replay generated **23** child signals. Six created child entry intents; all six received an initial fill, across 13 accepted child slices. The remaining 17 children generated no entry intent. The independent account ledger reports 35,064 closes and maximum equity error **0 USDT**. Risk audit passed with no violations. The original GAP buffer audit passed with no negative observations; there were no liquidation events.

Minute refinement validated a common input identity across **143 execution hours**. The request covers active signal hours and first calls after signal termination. Two missing daily mark archives were repaired from official monthly 1-minute mark archives; their exact hashes, request, validation, receipt, and input archives are retained in the evidence bundle.

## Scope and use

This is an in-sample research account comparison, not production qualification. Keep production default 3.6 and the `run --execute` guard unchanged. Do not infer native execution, live fill quality, or dynamic FX/USDT qualification from these proxy accounts.

## Reproducible evidence

- Frozen rule and differentiation: `PROTOCOL.md` (SHA-256 `15860f4768446f8f422e74d50b1b6f52c5993df18c28fa916f9eb333f89d7237`).
- Full call/event coverage: `coverage/summary.json`, `coverage/calls.jsonl`, `coverage/opportunities.jsonl`.
- Candidate child geometry and intent/fill joins: `development/PIR1_SIGNAL_ATTRIBUTION.json`.
- Input request, validation and source receipt: `MINUTE_REQUEST.development.json`, `MINUTE_VALIDATION.development.json`, `development-entry-minutes/PIR1_DEVELOPMENT_MINUTE_RECEIPT.json`.
- Exact raw account streams, measurement source snapshots, source inputs and preserved failed packaging attempt are in the companion Library evidence archive. `GATE.json` records source and result hashes.
