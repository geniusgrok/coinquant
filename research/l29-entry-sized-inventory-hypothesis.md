# L29: preserve entry-sized inventory through a campaign

Registered after L27/L28 sparse failures, before L29 measurement.
Control is L21, not either rejected direction candidate. Event attribution shows
129adds and103reductions on25entries; direction and lifecycle cannot alone explain
exposure. A constant target fraction has negative inventory feedback during a
trend (price rises can reduce BTC quantity) and volatility falls can add inventory
during a reversal. The recorded June2022 drawdown peak has short0.159BTC; the
July20exit has short0.239BTC. This observation motivates, but does not prove, the
inventory feedback hypothesis. Do not equate every reduction with a mistake.

One mechanism trial: calculate exactly L21 volatility/funded quantity at entry,
then hold that quantity until existing fixed SL/TP or original direction exit.
No intra-campaign target resizing. Same one_campaign lock, protection, capital,
margin, costs and original triggers. Entry size/risk scale is unchanged; exposure
will drift and may cause a larger drawdown, so this is not a risk-free simplification.
It differs from L13–L15 profit reinvestment (no profit floor, trailing or adds),
and L17 (entry is L21 volatility target, not fixed0.006stop risk).

Paired full2020–2023 sparse/hourly accounts. Retain only sparse CAGR above L21
with MDD<50% and no execution/account invariant failure. No adjacent sizing search.
If failed, preserve sources and quantify drift; do not add a clamp to rescue it.
2024+economics remain unused. Formal native qualification remains unresolved.
