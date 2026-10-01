# Third round: execution and project selection

Frozen before full measurement: Coinquant default risk 7.5; Starquant default
and risk 0.024. No parameter search. Same 795 finite 300-second sessions, 5-second
polling, 2020-01-01 through 2026-09-20 exclusive, CNY 10,000, no additions.
Targets remain CAGR >=150% and MDD <50%; report their shortfall independently
from selection of a development default.

The common venue uses Coinquant official trade/mark minutes, recorded official
funding and print quantity upper bounds, 200ms reads/1000ms writes, fee 0.00075,
zero additional baseline slippage and 0.001 conversion each way. FX is the
peer's fixing strictly before the current date, shared for valuation; its hash
is recorded. This changes the comparison measurement identity, never the old
M10 or continuous peer accounts. Missing official funding remains unknown;
premium/zero substitutions are excluded. The owner-accepted missing-mark bound
is recorded explicitly and is not a complete observed market path.

Coin IOC limit fills and peer market fills retain their actual behavior.
Peer protection is CONTRACT_PRICE; common valuation and liquidation use mark.
Production session.run/Lifecycle and peer runner.run_cycle remain the execution
paths. Unattended time sends no client commands. The peer uses its actual stop
cleanup between sessions; no background decisions are introduced.

First run small integration probes. Cover short, add, partial fills, lost ACK,
restart and process-stop protection through existing cases and adapter boundary
checks. Only then run full accounts. Partial outputs stay in /tmp and cannot
rank. Any unknown path, unresolved execution or invalid native mapping prevents
promotion. Full-account baseline must pass before pressure comparisons can
select a strategy. Retain default Coinquant while this gate is unresolved.

Select the complete safe default under the fixed usage contract; final runtime
retirement additionally requires native Demo closure and migration of useful
peer strategy capabilities. Neither a unit suite nor this proxy account clears
native qualification. No engineering agent performs account requests or trades.
