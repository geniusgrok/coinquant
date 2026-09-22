# L8 current-equity stop-risk allocation — frozen before measurement

Retain L7 persistent20-day channel and10-day stop, unchanged0.006risk budget,
2x effective cap,20x exchange setting,TP rule,costs,invocations and development data.
Replace frozen entry quantity with a target recomputed at each manual invocation:
current whole-account equity times0.006 divided by current mark-to-stop loss plus
entry/exit fee and spread/slippage reserves. Reduce when too large; add only when
the same budget, stop geometry, prior-hour participation and available wallet permit.
No risk/leverage parameter increase, no new signal/filter, no intra-gap rebalancing.

Adding fills changes average entry and pays actual assumed transaction costs.
Reserve isolated margin before the assumed added fill, at least20x initial margin
and enough for projected liquidation to remain beyond stop plus1%mark cushion.
Reject an unfundable addition; do not borrow unavailable isolated unrealized profit.
Reductions realize PnL/fees and release proportional margin. Original TP remains;
never add at a fill price outside TP/SL. No sign reversal within a resize operation.

This tests allocation continuity, not a claim that increasing exposure alone solves
economics. Require development CAGR above L7's4.863302406009273% AND continuous
conservative MDD no higher than L7's11.36320269446116%. Otherwise reject progression;
no adjacent risk/cap/period/cost tuning. Final frozen targets remain unchanged.
NOT_QUALIFIED:proxy rules,funding bounds,USDT=USD,unverified native lifecycle.
No2024+economic validation or parameter selection.
