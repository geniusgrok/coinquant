# Pancakequant project state

## Effective mandate

Implement the attached 2026-09-20 redesign on research/on-demand-btc-20260920. Main was verified at c886b7c63c6455bd7c933269e32cd35a6fb3e09a and must not receive an unqualified candidate. CNY 10,000 initial capital; formal start 2020-01-01 UTC; CAGR > 200%, complete-account MDD < 20%; fixed exchange leverage 20. This task does not authorize live trading or real account changes.

## Reconciled branch state

The current production implementation is the Bybit BTCUSD inverse path in pancakequant/types.py, model.py, config.py, rest.py, decode.py, bybit.py, state.py and execution.py. Parallel commits removed the old framework and added the .transfer historical recovery packet and read-only exporter. AGENTS.md at bb448a439bac1d520a39ced0e763879b462c8e14 was read and retained. The .transfer packet contains a different unqualified implementation; preserve it as recovery evidence, never restore it over current source or mix both adapters into production.

Preserved current execution tests: commit 2b9aae59e10e8bd1f35239df64cc4af1c4b55e85. Native write-through file operations on the research branch are working. Native Git DNS is unavailable in this container. Before every integration read the current remote ref; no force rewinds or local-snapshot replacement.

## Actual verification

24 local offline tests passed for the current Bybit model, durable state and execution lifecycle. These cover default read-only, account binding, unknown response reconciliation, deterministic IDs after local state loss, partial fills with cancellation of remaining entry, native-protector readback requirements, same-candle protection repair and best-effort reduce-only recovery. They are synthetic/fake-venue tests, not live or testnet validation. Initial old-framework CI failed on removed dependency imports. Current check/export run 35516362361 was queued when inspected; no CI success is claimed.

The first complete source archive at a3c2e3127c02e9abbf38e55f7a12c30f51907670 was downloaded using the connector and its ZIP/tar hashes verified. Subsequent current-source byte readback is still pending. A later .transfer recovery artifact is being obtained without passing the archive through model context.

## Remaining implementation and evidence

A local three-command CLI, strict historical data manifest reader, frozen invocation specification and sparse replay have been written in the active workspace and are undergoing tests and remote preservation. They are not yet the branch's runnable release. Keep this entry current after they are committed; do not infer completion from this description.

Still missing: complete native 2020-2026 BTCUSD price/mark/funding/historical-rule evidence, full economic measurement, chronological independent validation, real native API safety verification, verified offline resting-entry parent/residual cancellation linkage, and end-to-end durable margin/ordinary-entry amendment integration. Adapter methods alone do not prove those features are delivered.

No formal CAGR/MDD result exists. No financial target has been relaxed. BTC collateral itself changes fiat value even while the derivative is flat; this must remain in whole-account replay and reporting. Do not present the 0.6% incremental BTC stop budget as a fiat drawdown guarantee.

## Direct recovery

Read this file and AGENTS.md from the current branch, obtain the current-source artifact without applying the historical packet, verify file identity, then finish the current CLI/data/replay integration and targeted safety checks. Preserve raw logs and code promptly. Continue independent engineering if native data or API checks are blocked, but keep economic status NOT_MEASURED and leave main unchanged.
