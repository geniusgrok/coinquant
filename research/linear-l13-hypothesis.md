# L13 preregistration — reinvest locked campaign profit, not a larger initial risk

Evidence: L9 holds33019/35064development hours but mean account notional0.06727x.
Simply staying invested does not solve capital participation. L8's continuous
current-equity stop-risk resizing worsened returns/cost/liquidation classifications.
L12 risk scaling is exhausted and is not new alpha.

One structural experiment: initial entry retains .006 cost-inclusive stop risk and
2x total exposure cap. At frozen manual invocations, ratchet the existing stop to
the original ten-day channel boundary. Only when the stop advances can the account
reinvest previously protected campaign profit into same-direction inventory.
The protected liquidation-free exit equity after fees/slippage must remain above
campaign starting equity*(1-.006). Use actual wallet-funded isolated margin;
do not turn unrealized PnL into fictitious wallet cash. Never reduce/re-expand
inventory just to target a fraction each invocation. Exit on hosted SL/TP or regime
reversal at invocation, with no same-trigger reversal. Between triggers, no decisions.

Added quantity floor((protected_exit_equity-campaign_floor) /
  (direction*(execution_price-adverse_stop_fill)+fee*(execution_price+adverse_stop_fill))).
Cap by2x current equity, prior-volume participation, existing notional proxy and
available wallet/margin. The existing resize accounting helper is reused for adds.
Campaign_floor is set before initial entry fees and resets only on a new campaign.
All quantities remain subject to the currently disclosed hypothetical LOT; this
cannot qualify historical Binance rules.

One run, unchanged channel periods, costs, data and468original development invocations.
Retain for further work only if CAGR and CAGR/MDD exceed paired refined L9,
MDD<50%, and no funded-stop/account-conservation invariant fails. Report liquidation
ambiguities and turnover; do not hide these behind the numeric screen.
If failed, diagnose actual add opportunities/blocked margin/entry-floor behavior;
do not relax the capital floor or enlarge the initial risk fraction.
No2024+economic inspection, no parameter sweep, no production qualification.
