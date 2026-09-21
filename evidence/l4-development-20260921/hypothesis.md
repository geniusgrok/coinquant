# L4: signed taker-flow continuation — frozen before measurement

L3 is rejected. L4 tests a different observable mechanism: net aggressive buying
or selling may reveal sustained demand across sparse invocations. It uses only
Binance native trade kline volume and taker-buy volume, no fitted coefficients,
price momentum, funding feature, ensemble or threshold grid.

At each original frozen 2020–2023 invocation, sum the previous 24 completed hourly
bars' quote volume V and taker-buy quote volume B. Signal is (2B-V)/V. Direction
is its sign. Fixed horizon is four days for comparison with the prior screen;
no positions are claimed to exist between observations. Deduct the same frozen
cost assumptions and actual funding-rate sum approximation as L3. Exclude
observations whose forward endpoint is outside development. No validation data
is loaded. Require positive signal/return correlation and mean directional net
above the same constant-long control. Failure rejects this hypothesis without
sign reversal, adjacent lookback tuning or threshold search.

This is an overlapping forecast diagnostic, not executable account economics.
Even a pass requires a separately frozen full lifecycle candidate, continuous
account replay, actual funding cashflows, dated native rules and USDT valuation.
Status remains NOT_QUALIFIED. Archive checksums and exact inputs are inherited
from the already verified L3 development input identity; all are rechecked.
