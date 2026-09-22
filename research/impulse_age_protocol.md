# D3 event timing: diagnostic protocol, development only

Baseline8524245, impulse_hold risk_scale2.4, original schedules/costs/data.
Re-use frozen D3 raw accounts. Pair57events by first knowable timestamp; common
36and missed21. Attribute timing in common original R units (signal-to-midpoint),
then preserve actual size/compounding separately. No subgroup-derived timing grid.
Independent long-only/short-only accounts change allowed entry direction only;
model opportunity generation and risk budget stay unchanged. These are diagnostics,
not automatic production candidates. No2024+reading for this new hypothesis yet.

Observed paired shorts: entry delay-21.45R, exit delay-5.87R; missing9events-10.11R.
Longs: entry delay-27.48R, exit delay+31.14R. Sample16/20common; no universal decay
or side deletion conclusion follows. Per-event entry age/price displacement/stop
risk/fees/funding and missed reasons are retained in paired-events.json.

Independent development accounts: long-only sparse64.72%CAGR vs D3both66.06%;
short-only sparse1.80%, normal24.27%. No side deletion justified. Common-event next24h
net direction shorts2.35%at recognition vs0.67%at sparse entry (n16); longs2.47%vs2.35%
(n20). Selection/survivorship and small sample prevent general age-decay claim.

V1 preregistered before replay: unpriced -> realized-entry -> invalid/expired.
One further original impulse amplitude (=2 initial midpoint-stopR) above/below
signal close is the price-realization boundary. A completed4h close past it
permanently retires new entry for this opportunity; never rearms on retracement.
Also reject an execution quote already beyond it. Positions entered before that
state retain original stop/farTP/7day life, preserving trend option value; this is
not D's failed2R take-profit and not E's indefinite holding. Both directions same
state. Fixed risk_scale2.4. No age cutoff tuning. Candidate may reject winners;
only paired account replay can tell. Development only before any full follow-up.

V1 failed: sparse34.76%CAGR/30.43%MDD vsD3 66.06%/34.50%; normal three raw
streams byte-identical. Do not tune realization threshold or delete short side.
V2 distinct invalidation hypothesis: after a completed close retains one additional
shock amplitude, original signal close becomes failure boundary rather than
midpoint of the original shock. Retain new entries and existing inventory; native
stop changes ONLY at invocations, never retrospectively offline. One state shift,
no continuous trail, same7day life/farTP/risk2.4. Price can still continue after
realization, so no nearTP/entry ban. Reconcile mark already through proposed stop
at invocation by market exit, never install a retroactively filled stop.

V2 frozen after development: sparse69.46%/34.64%, normal87.73%/35.61%.
Then one full-window review (2024+already used): sparse49.65%/34.64%,
normal51.01%/35.61%. Gains concentrated in few events; no risk increase authorized
by these findings. D3 retained baseline, no production replacement.

Next information hypothesis, before calculation: completed recent4h aggressive
trade imbalance may distinguish continuing demand from price-only stale impulse.
Use existing native hourly quote volume and taker-buy quote volume, known only
at candle close. Direction*(2*buy/total-1)>0 means aligned flow; zero is economic
balance, not fitted cutoff. Development-only descriptive next24h net outcome;
no new account credited, no filter implemented without incremental evidence.
