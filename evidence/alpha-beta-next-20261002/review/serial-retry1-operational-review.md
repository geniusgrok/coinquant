# Serial retry1 operational review — PASS for the known-session queue

Verified queue SHA256 `30ac30a3045311aebe73263f67b4fc9ea43e84aab889c3efb76996c32ea17692` is **byte-for-byte approved v1 after exactly three replacements**:

1. Coin singles input becomes `perp-singletons-retry1.json.gz`.
2. Initial process waiter becomes `/proc/32321`.
3. Sensitivity output/log/receipt labels become `sensitivity-serial-retry1-*`.

No other source, command option, candidate, scene, calibration, capital, schedule, gate or selection behavior changes. The parallel incumbent worker is absent. The main queue waits for the actual full retry process to exit and both complete singles artifacts before assessment/risk. Risk and combination stages run at most one Coin subprocess alongside Spot, join their workers before advancing, and execute each later Coin sensitivity sequentially. Thus the entire Coin process chain sharing synthetic UIDs is serialized, not merely its cache writers. The previous parallel approval remains retracted.

At05:43:28.690069UTC, independent process inspection found exactly one active Coin producer: PID32321, frozen `research.alpha_perp --restore-prints --out /workspace/scratch/alpha-beta-next/perp-singletons-retry1.json.gz`. Serial waiter PID32493 and read-only auditor PID32496 were also present. No other Coin producer was active. Frozen Coin HEAD remains `acedaa43ca94223f24e2fe11851bbef74e032a69`, with clean `research`/`coinquant` source paths. This is a snapshot and queue-flow review, not a global lock acquired by the reviewer or a promise about unrelated future launches.

Read-only audit waiter SHA256 `a06b2341a993249607fb108dc0a707c56754a5201e642d6578b1750e1c6dde47` points to the actual retry1 Coin raw. It waits for the completed unscaled-assessment receipt and requires exit0 before Coin audit. Existing audits are reused only if `report.raw_sha256` exactly equals the current input bytes; mismatch fails. Existing independent failures are retained as failures, not changed to passes. The 48-row index describes inventory, not unconditional financial acceptance; final acceptance must inspect every retained completion/check/error status. The auditor starts no account replay and does not share the account execution lock.

New exclusive retry paths preserve failed full/probe logs and partial progress. No old partial result is promoted, no locked state/HOME/synthetic UID is altered, and no economic tuning is introduced. Registry `serial-retry1-registration.json` is consistent with the inspected process and queue. Independent proof: `serial-retry1-operational-review-proof.json`.

Reviewer launched no replay and changed no product/cache/lock/process. Operational review passes; complete financial matrix, risk, combination, sensitivity and adoption acceptance remain pending.
