# L23: separate bullish participation from short exposure

Registered after L21/L22 development attribution, before this experiment.
L22's unchanged ten-day trailing rule reduces sparse CAGR42.23% to26.58%; it is
rejected for return-first selection despite reducing drawdown48.82% to45.47%.
All25campaigns stop out;236manual decisions are then blocked as already consumed.
Do not tighten more stops or tune the risk scale.

L21 closed gross PnL is +4924.7855USDT long and -467.2532USDT short, before
fees and with adverse funding1098.1475long/75.4396short. This is path-dependent
account attribution, not proof that future shorts lose or independent alpha.

L23 changes exactly one direction mechanism: the existing channel is long/flat,
not long/short. On a bearish channel invocation close longs; no short entry.
Everything else is L21 (fixed entry protection, volatility risk scale, one campaign,
funding/cost/margin logic). The asymmetry is explicitly sample-informed and must
not be called unseen. Compare both schedules development only. No signal reversal,
new lookback, leverage grid or tuned threshold. If return does not improve, reject.
Formal150%/50%remains unmet until full qualification;2024+economics untouched.

Historical L10 already rejected long-only at the old fixed stop-risk allocation.
L23 explicitly tests that interaction under the new volatility target; it is not
a claim that long-only is a previously untested direction. The repeated failure
strengthens the case against removing shorts based on cumulative gross PnL.
