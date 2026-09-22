# L7 persistent channel state — frozen before measurement

L6's event-only entry missed opportunities when a daily breakout occurred between
manual invocations. L7 changes the exposure state, not channel parameters or risk:
keep the direction of the most recent completed20-day breakout until an opposite
completed20-day breakout. A flat account can enter that active state at its next
original manual invocation, even when the latest daily close is no longer a new
breakout. Stop-outs do not require a fresh20-day extreme before a later invocation
can re-enter; unsafe stop geometry still blocks entry. No immediate offline re-entry.

Compute state causally across completed daily bars (December2019warmup then
2020-2023development). Between invocations update observable indicator state only;
never place/reopen/amend orders except fixed native exits already modeled. One
model, no vote/filter/ensemble. Risk0.006,effectivecap2x,exchange20x,20/10channels,
log-distance TP20,margin safety geometry,costs,conservative funding valuation and
all frozen invocations are unchanged from corrected L6.

Require development CAGR above corrected L6's2.4372216259263% and conservative
continuous MDD<20% before further development. This paired gate is not the user's
final CAGR>200%/MDD<20% acceptance. NOT_QUALIFIED until actual dated rules, USDT
valuation, full-window validation and execution safety pass. No2024+economic use.
If it fails, do not tune channel periods,risk,reward or selectively reset state.
