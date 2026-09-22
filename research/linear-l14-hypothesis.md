# L14 preregistration — full-account profit retention

L13 development CAGR18.34%, conservative MDD72.68%,193profit adds,11interval
liquidation classifications. Reject. Preserving only campaign-start capital is
insufficient to protect accumulated account gains. Initial entry risk is unchanged;
do not increase it or relax any rule to rescue this result.

One integrated correction: at each frozen invocation retain the tighter of campaign
entry floor and55% of the observed full-account equity peak (45% planned drawdown,
5percentage-point reserve beneath the user's50% ceiling). Use this floor both to
tighten native-stop geometry and limit funded profit reinvestment. The45% level is
set once, not searched. If safe stop cannot exist below/above current mark, close
at adverse market cost instead of inventing a valid stop. If already flat below
the floor, block a new position. Tick rounding must strengthen protection.

This uses only past observed extrema and current open. No between-invocation
decisions or real-time trailing assumption. A rising peak between manual runs and
price gaps can still exceed the intended floor: never call it a hard guarantee.
Fees/slippage included in stop-equity computation; margin transfers funded from
wallet. Other L13 settings unchanged, no adjacent risk/period search.

One development run. Retain only if CAGR and CAGR/MDD exceed refined L9 and MDD<50%.
All cash/protection invariants required. Disclose unresolved intrabar ordering.
If rejected, use trade/peak attribution to determine whether entry information
rather than allocation is the bottleneck; stop this profit-reinvestment family.
No2024+economic data used.
