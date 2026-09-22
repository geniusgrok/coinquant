# L5 Bayesian change-point drift — frozen before measurement

Single generative model of daily log returns: within a latent regime, returns
are normal with unknown mean/variance and a normal-inverse-gamma posterior.
A daily change point has fixed probability1/90; reset prior mean0,kappa1,alpha3,
beta0.0032 (prior mean daily variance0.0016). Integrate all possible run lengths;
no maximum-run truncation, parameter grid, fitted thresholds, price/funding/taker
filters or ensemble. Parameters are structural assumptions, not estimated profits.

Each newly completed daily return updates run-length and sufficient-statistic
posteriors. A change-point branch generates that day's return from the reset prior;
growth branches generate it from their existing posteriors. Signal is four times
the run-length-weighted posterior mean. Take its sign only if absolute expected
four-day log return exceeds frozen round-trip fee/spread/slippage costs; otherwise
cash. No leverage or account risk change is part of this forecast screen.

Use December2019 trade signal warmup and2020-2023native Binance development only.
Same frozen sparse invocation schedule. Forward four-day open returns, actual
funding rate sums and fixed cost deductions use the same explicitly approximate
forecast accounting as L3/L4. Those overlapping observations are not trades,
account CAGR/MDD, exact funding cashflows or evidence of protection safety.

Require positive forecast/forward-return correlation AND higher mean directional
net return than constant-long control. A failure rejects progression; do not tune
hazard/prior/cost cutoff or reverse signals after observing the outcome. A pass
only warrants a separately specified executable account candidate; it does not
satisfy economic acceptance. No2024+economic validation or model fitting.
