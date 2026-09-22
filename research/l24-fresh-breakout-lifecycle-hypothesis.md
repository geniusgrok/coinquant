# L24: rearm a stopped campaign only after a fresh completed breakout

Registered after L22/L23, before L24 measurements. L23 long/flat fails:
sparse24.7980%CAGR/53.2072%MDD versusL21 42.2274%/48.8171%. Removing shorts
worsens2022return from-8.67% to-33.11%. Closed-trade direction attribution is
not an additive counterfactual; short exposure can protect the account even when
its cumulative realized gross PnL is negative. RejectL23, preserve both directions.

L22 exits all25campaigns then blocks236of468sparse decisions until the direction
fully reverses. L24 tests that overly long lockout, NOT arbitrary stale reentry:
retain L22's original20-day direction,10-day trailing protection and L21volatility
allocation. A stopped/flat campaign rearms only when a later completed daily
close crosses the existing previous20-day high/low in the current direction.
Breakouts while still holding do not accumulate future entry permissions. No
new window, reversal, threshold, risk scaling or model ensemble. Sparse entry is
still only at the next original invocation; hourly is a separate account.

This differs from L9 entering every invocation on a stale persistent regime and
from L17 forbidding all reentries until opposite-direction breakout. Campaign
permission is account lifecycle state; direction and volatility remain market-only.
Evaluate both schedules on2020-2023, and classify missed participation vs whipsaw
cost. Reject if it cannot improve sparse netCAGR under50%diagnostic envelope.
No2024+economics; no native execution qualification claim.
