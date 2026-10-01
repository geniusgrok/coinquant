# BTC complete delivery — registered 2026-10-01

User authorization: implement the entire engineering delivery and every proposed
alpha/beta research direction, including lower priority funding/basis and shorts.
Account requests, credentials, orders and transfers remain owner-operated.

## Fixed experiment

2020-01-01T00:00:00Z to 2026-09-20T00:00:00Z, right endpoint excluded;
CNY 10,000, no deposits. BTCUSDT only. Common previous-date Frankfurter fixing,
conversion 0.001 each way. Keep original results under their original identities.
New measures correct initial FX assignment before the first metric cash point.
795 primary starts from session_schedule.json, 300s sessions and 5s polls.
Offline exchange protection may trigger while stopped; no client decisions then.
The historical venue remains a proxy, never proof of native fills or future alpha.

Coin candidates, fixed before measurement:
1. existing SX60+DFII10, primary 7.5/macro 3.6;
2. tail sizing: existing sizing denominator uses max(20-day RMS, 5-day RMS),
   with no other sizing/stop/margin changes;
3. no-macro diagnostic, not eligible as an independently searched model;
4. slow trend replaces macro: flat, no executable primary long, close above
   completed 60-day SMA and SMA above its value 5 days earlier; 10-day low stop,
   macro risk 3.6, ordinary next-session decisions; original primary priority;
5. funding filter: new longs blocked if latest settled rate (lagged 8h) >0.0003;
6. basis filter: new longs blocked if previous completed daily futures/spot
   close premium >0.01; incomplete or unpublished input blocks new candidate risk;
7. conditional short: original negative impulse only while below completed
   60-day SMA and that SMA is declining over 5 completed days. Single one-way
   position, no opposite entry until flat; primary sizing unchanged. Compare
   cash over the same intervals and retained long baseline.

Each candidate runs base, fees x1.5, read latency 400ms, and trigger slippage
0.0015. These are separate perturbations, not a tuning grid. Full baseline and
cash audit precede selection. Unknown/incomplete accounts cannot promote.
Eligible improvement: all matched scenarios satisfy MDD<0.50, CAGR no lower
than matched incumbent minus 0.01, base CAGR at least incumbent plus 0.01 OR
base MDD at least 0.01 lower with CAGR loss <=0.03. No-macro is attribution only.
Tie: highest worst-case CAGR, then smallest change. Original 150% target
reported independently; no native enablement from economic selection.

Spot candidates use its actual session/Lifecycle: existing P4; consensus cash
allocation; persistent downside reduction/recovery; same funding and basis
entry filters. Precise fixed rules live in Spot's matching protocol. Spot stays
long/cash without leverage; original 100%/MDD<=30% targets remain.

## All-scope analysis and delivery

Same-date USDT and CNY daily curves, gross/net BTC exposure, fees/funding,
up/down BTC capture, descriptive beta and residual return with uncertainty,
annual distribution, underwater duration and tail losses. Regression is not
prospective alpha proof. Compare passive BTC/cash controls and fixed initial
spot/perp capital splits 0/25/50/75/100% to spot, no transfers/rebalancing;
rescale outputs only if linearity is demonstrated, otherwise replay budgets.
Daily combined drawdown is labelled daily, never continuous full-account MDD.

Star mismatch: first-decision/fill divergence and one-factor schedule/cost
diagnostics on recorded sources; continuous and finite accounts remain distinct.
No forced retirement from the finite-session loss.

Engineering: durable spot incremental fills with overlap/identity checks,
immutable session archive and SQLite backup, read-only restore verification,
source-bound native evidence validator, operation guide, offline tests, independent
review and corresponding-head CI. Integrate final reviewed PRs normally.
Native closure and 30 actual calendar days remain missing until owner operation.
