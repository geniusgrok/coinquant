# L19: funding crowding information, registered before outcomes

L18 historical channel-edge allocation failed to improve sufficient net account return. Do not adjust its Kelly constants or risk ceiling. Test a different causal input already present in native evidence: funding crowding, not another price indicator.

At each original sparse development invocation, compare the most recently settled funding rate (strictly earlier than decision time) with the median of the previous90settlements excluding that latest one. Crowded high relative funding predicts downside; depressed funding predicts upside. Exact ties mean flat.90settlements is a30-day baseline, specified once. No sign reversal or horizon/threshold tuning after results.

Hold forecast to the next frozen invocation, using hourly trade opens and fixed nonzero round-trip fee/spread/slippage. Compute actual funding-rate cash approximation at each settlement as direction*settlement-hour mark HIGH/entry price times rate for debits, LOW for credits. This is a nonoverlapping unit-inventory forecast diagnostic, not an account, leveraged return or native qualification. Unresolved offset marks are labeled; no fabricated exact cashflow. Controls: constant long and causal channel direction on exactly the same intervals. Inputs all2020-2023;2024+untouched.

Proceed to account replay only if positive mean net return and improved mean versus same-sample constant long OR channel. This is a mechanism-development screen, not formal acceptance. Otherwise preserve evidence and reject this funding hypothesis; do not reverse its sign post hoc.
