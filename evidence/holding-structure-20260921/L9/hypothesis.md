# L9 preregistration: align holding exit with persistent regime

Before L9 results: exact L7 replay reproduced all five logical outputs. Long trades
43, gross +425.3936 USDT; short trades29, gross -15.4716 USDT. L7 had69 stops,
2 liquidations and1 take. Frozen .006 risk,20x exchange and2x cap remain unchanged
for this paired structural experiment; no parameter search or validation data.

Hypothesis: ten-day stop ratcheting exits positions inside the persistent
20-day regime; retaining original hosted SL/TP and closing on opposite regime
at the next frozen invocation may improve captured trend return per unit risk.
All regime updates use completed daily bars. No writes between invocations.
An opposite regime closes the existing position at adverse market cost, without
same-invocation reversal; next invocation may enter. Initial SL/TP unchanged.

Bounded experiment: exactly one L9 implementation, compared to exact L7.
Retain for further investigation only if development CAGR improves, CAGR/MDD
improves, drawdown remains below50%, and liquidation count does not increase.
These are research selection criteria, not formal qualification. No2024+inspection.
If rejected: inspect direction-specific participation and stop/reentry losses,
then investigate a separately registered holding structure, not adjacent periods.
Proxy rules, USDT=USD, adverse funding and hourly ordering remain limitations.
