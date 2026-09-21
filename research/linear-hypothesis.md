# L1 stable-settlement trend hypothesis — preregistered 2026-09-21

Status: signal implemented and unit-checked; economic result NOT_MEASURED;
qualification NOT_QUALIFIED. No production import or execution adapter changed.

## Why this experiment

The preserved inverse baseline added only 1.01917x BTC units. A settlement swap
alone cannot deliver the frozen target. L1 tests immediate participation in a
persistent move and holding continuity, rather than requiring another breakout
and repeatedly resetting the target size and take profit at each invocation.
It is a hypothesis, not evidence that the target is achievable.

## One model

`research/sparse_trend.py` computes a self-normalized trend from the latest 120
complete 4h log returns (20 days). Score is sum(returns)/sqrt(sum(returns^2)).
Conviction is max(0, 1 - 1/abs(score)); zero energy means no trade. The sign gives
long/short direction. Daily RMS is a scale estimate, not an annualized Sharpe,
probability of profit or calibrated expected return. No fitting has occurred.

The proposed first replay must enter at the next executable price at a frozen
invocation, keep same-direction quantity unchanged, and close on a flat/opposite
signal. It must not flip twice within the same invocation. A stopped position
cannot re-enter until the next frozen invocation. There is no offline parent
order in this first candidate, reducing stale-entry and remainder risk.

Keep the previous 0.006 account stop-risk ceiling and 2x effective exposure cap;
exchange leverage remains exactly 20x. Conviction scales risk downward only.
Proposed initial stop distance is two daily RMS price units, with a fixed 8R
native TP. At subsequent invocations the stop may tighten but never loosen;
TP remains anchored to the original fill. All costs enter sizing. Quantity must
respect native contract value, dated lot/tick/caps, liquidity and available cash.
If the intended stop is unsafe at initial 20x margin, skip the entry in this first
experiment; do not assume margin can be added atomically or after process exit.
Do not replace these assumptions after viewing results without recording why.

These lifecycle/risk rules are a preregistration, NOT implemented in the signal
module. Native linear accounting, liquidation and production lifecycle remain
unimplemented pending contract feasibility. Do not pass the signal module off
as a completed trading model.

## Frozen evaluation

Reuse `research/spec.json` start/end, CNY conversion convention, capital, costs,
market-independent invocation generator and absence stress. Do not alter the
inverse spec to pretend it represents native OKX history. A linear dataset must
identify its actual contract/settlement and preserve raw receipts and rules.

Develop on 2020-2023 only. First measure return, complete-account mark MDD,
fees/funding, time in position, skipped-entry reasons, holding duration and
return per exposure-day. Compare the old transplanted signal under the same
linear accounting as a diagnostic control. Do not optimize either over validation.
Only then run a locked 2024-end validation, and the full frozen account path.
If validation informs a subsequent change, explicitly record contamination.

Reject L1 if persistence does not produce net trading gains after costs in
development. Diagnose entry participation, stop churn and missed trend time
before choosing one structural successor. No risk-budget escalation or parameter
grid. Formal acceptance is unchanged: CAGR > 200%, MDD < 20%, credible native
inputs and necessary execution safety. Nothing measured here meets those gates.

## Current dependency

OKX listing/linear USDT settlement is supported by a current official instrument
response, but 2020 trade/mark/funding coverage and native partial-fill/full-position
protection remain unverified. See `evidence/linear-feasibility-20260921.md`.
No linear economics were run, and 2024-end market data was not inspected for L1.
