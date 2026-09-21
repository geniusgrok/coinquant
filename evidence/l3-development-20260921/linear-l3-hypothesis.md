# L3 causal forecast hypothesis — preregistered before measurement

L1/L2 failed on the development proxy. Do not tune their score thresholds or
stop distance. L3 asks a different question before spending another full replay:
does an expanding, causally trained forecast of four-day BTC returns have useful
directional information on native linear data after simple cost deductions?

One ridge regression jointly estimates an intercept, 20-day normalized momentum,
one-day normalized return, and the most recently settled funding rate normalized
by daily realized volatility. Inputs use bounded tanh transforms. Fixed ridge
penalty 10, minimum 90 matured daily labels; no parameter grid. Four-day labels
join training only after all four days have completed. No random split, no future
normalization, no peeking at unresolved labels. Missing inputs block evaluation.

Use 2020-2023 development only. The 2019-12 trade data supplies signal warmup;
there are no pre-2020 account returns. Evaluate at the original sparse invocation
times using only the most recent completed daily observation. Training observations
are daily; invocation observations are not treated as independent trials. Report
forecast correlation, direction accuracy and directional four-day return after a
fixed 15bp round-trip fee plus frozen spread/slippage and actual funding. These
are overlapping forecast diagnostics, NOT a compounded tradable account or CAGR.

Reject progression if the forecast fails to improve on a causal constant-long
control in mean cost-adjusted forward return, or forecast correlation is nonpositive.
No adjacent ridge/horizon/feature tuning after observing the result. Only a passing
forecast diagnostic warrants a fully specified executable account candidate.
This screening gate does not imply the frozen economic targets are attainable.

Keep 2024-end out of model fitting and economic evaluation. Boundary data was
examined solely for archive completeness; disclose that inspection. Native dated
rules, USDT depeg risk and entry/partial-fill protection remain unresolved, so all
results remain NOT_QUALIFIED even if the signal screen passes.
