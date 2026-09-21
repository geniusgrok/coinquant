# L28: finish a direction transition within one invocation

Registered after L27 sparse result32.3881%CAGR/50.2256%MDD, before L28.
L27 fails the return objective and drawdown condition; keep L21 as control.
Do not tune its failure anchor. Existing L21 has17 opposite-regime exits followed
by an unnecessary extra invocation gap (19–151hours). Some gaps help and some
hurt, so posthoc gap returns do not prove an advantage.

Change only the invocation transition: after a modeled full opposite-position
close, use the now-flat account to preflight and enter the already-known new
direction within the same invocation. Charge both orders; reuse the same funded
sizing, liquidity, quantity and protection constraints. Stops/takes/liquidation
at the open still forbid same-invocation reentry. Campaign lock remains unchanged.
No new trigger, signal, size, cost assumption or protective rule. Both schedules
share the rule with separate accounts. This is an ideal sequential-filled research
counterfactual, NOT proof that exchange close/readback/open lifecycle is implemented.

Use all2020–2023, retain sparse only if netCAGR>L21 and MDD<50%. Do not select
individual profitable transitions or add gap profits to original equity. Report
all years, costs, full trace and cross-year risk; validation2024+remains unused.
