# Return-first continuation: references and L21, registered before measurement

Formal target and original sparse schedule are unchanged: cost-net CAGR >=150%,
continuous account MDD <50%, 2020-01-01 to 2026-09-20 exclusive. Development only
2020-2023 here; no 2024+ economics. No live or testnet operations.

First reuse exact L17-B originals. Measure B1 protected constant-long and B2
unchanged 20-day persistent channel direction, each targeting at most 1x account
notional at manual invocations. B1 is a protected holding reference, not spot
buy-and-hold: stops can exit it, with reentry at the next invocation. B2 retains
L17 one-entry-per-regime; both can resize on manual invocations and retain the
existing channel stop and distant TP. Thus the attribution explicitly includes
protection and lifecycle, rather than pretending 1x can be maintained offline.

L21 replaces only B2's constant target by completed daily-return RMS over the
last 20 returns. Seven days covers the frozen maximum 151-hour absence. Target
fraction = 0.20 / (2.33 * RMS * sqrt(7) + 0.10 + 0.01 + round-trip friction).
0.20 is a prospective single-absence stress budget; 2.33 is a stress multiplier,
NOT an empirical 99% quantile or drawdown guarantee. The 10% gap reserve and 1%
seven-day funding reserve are declared scenarios, NOT historical upper bounds.
Use max(seven-day scale,21-day scale) only in a separately declared absence
stress, not as a tuned alternative. No risk, lookback or multiplier grids.

All orders obey observed quantity units, prior-hour liquidity, available wallet,
20x initial margin and funded liquidation boundary at least the gap reserve past
the protective stop. Funding reserve and close fees remain available. Adds use
weighted entry and existing full-position TP/SL. They never withdraw allocated
margin; proportional release only accompanies actual reduction. Stop tightening
does not raise the target. Each delta order, not just final position, must meet
lot/minimum/notional limits. No upward rounding. Whole-position native emergency
protection is modeled independently of discretionary minimum order checks.

B1/B2/L21 use the same account engine, independently for sparse and hourly paths.
Capture annual equity return/envelope drawdown, holding hours, actual exposure,
margin usage, fees, adverse funding, failed orders and liquidations. Account paths
never reset at year boundaries. Offset funding charges use the greater adverse
old/new exposure when a resize makes exact settlement ordering uncertain.

L18 used a short noisy return mean and set allocation only at entry; L21 uses
realized variation, not predicted mean, and updates target at invocations. L8
sized by stop-distance and could withdraw margin during adds; L21 does neither.
Existing historical-rule, USDT valuation, funding-mark and native protection
execution gaps keep all results diagnostic / NOT_QUALIFIED.

Rank credible sparse net CAGR first under <50% drawdown; do not require Sharpe
or drawdown improvements versus L17. Measure before choosing the next mechanism.
