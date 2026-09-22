# L26: continuous channel position instead of latched binary direction

Registered before measurement, after L25 failed (sparse1.5108%CAGR/48.2131%MDD).
L25 does not invalidate every causal price mechanism, but it rules out the tested
200-day mean replacement; no adjacent horizon grid follows.

The existing channel remains fully long or short until an opposite20-day breakout.
Its frictionless2023gain31.9%versusBTC155.9% motivates replacing that persistent
binary state, not adding a new filter. Use the SAME20completed prior-day high/low
range and latest completed close. Position score = clip((2*close-high-low)/(high-low),
-1,1). Direction is sign(score); volatility target fraction is multiplied by
abs(score). A zero-width range gives zero target. Thus midpoint exposure is zero
and breakout exposure reaches the existing volatility target; there is no new
lookback, risk multiplier, fitted coefficient or leverage escalation.

This is one unified target-position mechanism, explicitly changing direction and
conviction together. It is not a clean direction-only attribution and will not
be described as one. Preserve L21 fixed protection, ten-day entry stop, funded
resizing, one campaign per sign regime and original sparse invocations. Sign
crossings create new campaigns, zero target closes at the next invocation.

Both account schedules on2020-2023; costs and whipsaw can overwhelm any benefit.
L18's noisy historical return mean/Kelly estimate is not reused. No2024+economics,
no neighboring midpoint/band/lookback search. Rank net sparse CAGR under50%envelope.
