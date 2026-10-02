# Coin unscaled20 financial review — waiting for completed evidence

Status at 2026-10-02 09:34 UTC: **pending, no Coin20 stage acceptance**. The completed retry raw, successful registered-unscaled receipt and independent Coin audit are not yet present. This is a readiness note, not a final financial review. Failed original full/probe runs and operational approval retraction remain historical evidence; no partial progress is substituted for completed accounts.

Read-only Git/archive checks confirm frozen producer HEAD `acedaa43ca94223f24e2fe11851bbef74e032a69`, full Python SHA `a6e3f30f02208ff7e604b6181c5d8fa7000fe7e30dbc3276fbcc93ffbb0ad227`, and analysis HEAD `99fcf005d2cb15c13bb37322b65ab2863b19d65e`, full Python SHA `427f34ca3640cfa78f51173583af1d9c82f007baae155f3a992dcffb8171ad7b`. Runtime/research directories are clean.

Focused invariant review confirms:

- Recorded normal commission proxy is 0.00075 of actual notional; fees-x1.5 uses 0.001125. Liquidation/insurance income, if any, must remain distinct and be reconciled when actual rows arrive.
- Funding settlement uses held quantity, public funding rate and previous completed one-minute official mark. `complete_perp.Exchange._pay_funding` passes END−1 to settlement at the terminal boundary and marks closing equity at END without paying the next interval's funding.
- Producer registered Coin CAGR uses YEAR_MS 31,556,952,000 (365.2425 days); analysis daily statistics, volatility and arithmetic regression use 365.25. Continuous proxy MDD is not independently replayed by the audit.
- Immutable calibration slices daily curves before 2022-01-01 before computing any statistics. Full common training count is 731; actual scales will be recomputed from completed evidence. Registered validation risk bands remain baseline vol×1.05 and beta+0.02.
- Approved orchestration waits for all complete singles and PID32321 exit, then runs full unscaled assessment/calibration and every legal actual profile plus baseline unity. Financial acceptance remains separate from source review and producer progress.

Required inputs before final review: `/workspace/scratch/alpha-beta-next/perp-singletons-retry1.json.gz`, `/workspace/scratch/alpha-beta-next/registered-unscaled.command.json` with exit 0 and matching output SHA, and `/workspace/btc-alpha-beta-next/review/financial-audit-perp-singletons.json` with its receipt/context. Final review will cover exact20 inventory, original incumbent4/six-group proof, actual fills/WAC/fees/public funding/timing, common daily statistics/HAC, past-only calibration and registered mechanical selection. No producer, account, cache, source or State operation was performed for this note.
