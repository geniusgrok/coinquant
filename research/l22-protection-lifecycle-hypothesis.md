# L22: invocation-time protective exit, registered after L21 and before L22

L21 development sparse CAGR42.2274%, MDD envelope48.8171%, no liquidation;
hourly32.8787%/62.0488%. Sparse annual returns approximately +163.3%, +39.0%,
-8.7%, +22.5%. The 1x channel reference returned56.39% CAGR but59.33% MDD.
These do not establish a150%mechanism. Volatility allocation alone is insufficient.

Test only a protection-lifecycle interaction: retain L21 channel direction,
volatility target, seven-day risk scale, sizing and one-campaign policy. At manual
invocations tighten the full-position stop to the most recent ten completed-day
channel, never loosen it and never free margin because the stop moved. Entry
stops already use this same ten-day definition, so no new fitted window. Original
TP remains. If stopped, wait for a new 20-day direction campaign as before.

This reuses the L7 trailing rule, not an assertion that L7 was never tried. The
new test is its interaction with the newly measured invocation-time volatility
allocation and funded margin; no inverse-stop-risk upsizing or parameter sweep.
The causal question is whether earlier exit prevents the multi-year profit
roundtrip seen in L21, at the expense of prematurely leaving valid trends.
Compare both schedules on2020-2023; select on sparse net CAGR under50%envelope.
A lower return is a failed return-first candidate even if drawdown improves.
No2024+economics and no production promotion. Existing diagnostic limitations apply.
