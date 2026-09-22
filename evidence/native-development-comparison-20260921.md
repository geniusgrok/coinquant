# Native-market account development comparison

All cases use2020-2023,468identical frozen invocations,native Binance trade/mark/funding,
fixed0.006risk budget,2xnotional cap and20xexchange setting. All are NOT_QUALIFIED.
Rules/lot/minimum/liquidity are hypothetical,USDT=USD; funding is an adverse interval
valuation, not actual marked settlement cashflow. MDD is the conservative continuous
hourly account envelope. No2024+economic validation used.

| Candidate | CAGR | MDD envelope | Entries | Liquidations | Paired decision |
|---|---:|---:|---:|---:|---|
| L6 corrected event-only channel |2.4372%|6.4703%|22|1|Positive development screen passed|
| L7 persistent channel state |4.8633%|11.3632%|72|2|Improves return,under20%development MDD|
| L8 current-equity resizing |3.5912%|12.4345%|72|17|Rejected:lower return,higher drawdown|

L8 adds215and reduces160times,with fees51.298USDT versus28.867USDT for L7.
The frozen final CAGR>200% and continuous MDD<20% have NOT been achieved.
L7's local improvement is not full-window acceptance or evidence of future returns.
Do not tune neighboring risk/channel/reward parameters against these results.

A funding chronology correctness fix separated exact-hour opening settlement from
sub-hour offsets; it changed L6 final CNY11010.0849 to11011.1333, with identical
entry/exit events and all468invocations. Both exact runs/sources remain preserved.
See the l6-development,l6-corrected-development,l7-development,l8-development
original receipts for full equity and order traces, source and input identities.
