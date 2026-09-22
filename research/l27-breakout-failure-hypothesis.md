# L27: invalidate a failed breakout, before measuring this candidate

Control: exact L21, commit 8115385, 2020–2023 only, original sparse schedule.
Recovered full traces reveal nine old-regime intervals in which a later completed
close crossed the opposite extreme of the bar that established that regime.
Examples include September 2021, February/September 2022, and February/June 2023.
This is observable then; it is not evidence that exiting will improve returns.
April 2020 is a counterexample risk: an early failure can precede a long advance.

Change only direction-state lifecycle. Establish +/- direction at the existing
20-day breakout. Store that completed breakout day's opposite extreme. Hold the
anchor fixed while the state survives. A later completed close beyond that
anchor invalidates direction to zero unless it already establishes an opposite
20-day breakout. From zero require a new completed 20-day breakout to rearm.
No trailing stop, new window, size change, mean model, ensemble, or parameter grid.
Unlike L24, this updates market direction on failed evidence, not permission after
a stop; unlike L26, it has discrete anchored hysteresis, not channel midpoint size.

Keep L21 volatility allocation, one_campaign, fixed native protection, margin,
quantity and adverse funding assumptions. On original invocations, zero direction
closes a position, and all original exchange constraints still apply. Compare both
schedules as independent full accounts. Retain only if sparse CAGR improves with
MDD envelope below 50%; formal qualification still requires unresolved native data
and execution evidence. Report all four years, cross-year drawdown and costs.
If it fails, preserve exact source/traces and interpret failure before another rule.
2024+ remains unused. This is a hypothesis, not a correctness repair or known alpha.
