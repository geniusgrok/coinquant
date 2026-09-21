# L6 channel persistence — native development account diagnostic

This tests holding/exit structure rather than a four-day return forecast. One
20-day price-channel model enters only when the latest completed daily close
exceeds the prior20daily highs/lows. Existing exposure remains until the opposite
10-day channel stop or a full-position take profit at20times the initial log-price stop distance; no forecast-timeout exit,
signal voting, momentum/funding filters or parameter grid. Stops can tighten only
at the original sparse invocation times. No decisions between invocations.

Initial stop is the opposite10-day channel. Account risk budget remains0.006,
effective notional cap2x, exchange leverage20x. Margin reserves additionally cover
stop distance plus a1% price cushion and conservative maintenance/exit fees; this
is safety geometry for wide stops, not the economic improvement hypothesis.
No risk/leverage escalation after measurement. Same-direction exposure is not topped up.

2020-2023development only, December2019trade warmup. Native Binance trade/mark and
funding, with independently hashed official mark gap supplements. Fixed proxy
fee0.00075 per side, MMR0.005, tick0.5, BTC lot0.0001, notional cap1million; these
are conservative research assumptions, NOT a verified historical Binance timeline.
Spread/slippage and initial conversion use the frozen specification. Prior-hour
quote volume supplies the explicit participation proxy; no future hour volume sizing.

For funding whose timestamp has a sub-hour offset, preserve the actual timestamp
in the trace. For exact-hour events use the opening mark before decisions. Offset events follow
the invocation, charge at the adverse hourly mark extreme (including possibly
already closed opening exposure) and omit
ambiguous funding credits; same-hour new entries pay positive funding conservatively.
This is an adverse interval bound, not exact settlement cashflow. USDT=USD is an
unresolved valuation assumption; any results remain NOT_QUALIFIED.

Whole-account wallet plus unrealized PnL is observed at opens, conservative high/low
equity envelopes and closes. Liquidation precedes ambiguous stop/take within an
hour. Liquidation assumes isolated bankruptcy settlement; native execution depth,
partial fills, historical feature availability and margin-transfer lifecycle are
not proven. No synthetic result can qualify production.

Record full equity/order traces and all frozen invocations. Reject this candidate
if development CAGR is not positive or MDD is20% or above; even a passing development
screen cannot meet the final goal without the strict full-window acceptance.
Do not tune channel lengths/reward/risk after measurement.2024+ remains untouched.

Correctness clarification after initial measurement: offset funding must not
alter an earlier invocation/opening liquidation check. The original hypothesis
and source remain in the first-run original archive. Channel lengths, risk,
leverage, stop/TP geometry and development gate are unchanged.
