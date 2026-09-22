# L15 preregistration — recoverable drawdown capacity

L14 produced CAGR27.74%,MDD47.05%,but permanently stopped opening trades after a
January2021 exit left cash below55% of peak. It fails its CAGR/MDD progression screen.
The trace demonstrates an endogenous lockout: flat cash cannot regain a fixed peak
floor without trading. Do not present this as successful low-risk trading.

Explicit research-plan amendment: L14 anticipated leaving the reinvestment family.
The observed permanent recovery lockout motivates exactly one further recoverability
hypothesis, not another floor/risk parameter grid. L14 remains rejected under its
original criteria. No user acceptance is changed.

Keep entry risk.006, exposure cap2x, planned45% drawdown and final50% ceiling.
For new entries, available loss budget is min(.006*equity,equity-.5*observed_peak).
Permit recovery only while positive capacity remains; zero/negative capacity blocks.
At invocations, floor=max(campaign_floor,.5*peak,min(.55*peak,.994*current_equity)).
Actual hosted stop NEVER loosens. This allows a new low-risk campaign below the45%
planning line without demanding an already-impossible stop above current equity.
Reinvestment spends only gains protected above this floor, as before.
No permanent state toggle or historical-reset of account equity/peak is introduced.
The50% historical ceiling is still strict; gap/interval ambiguity can fail it.

One run on identical development data. Retain only if CAGR and CAGR/MDD improve on
L9 and MDD<50%. Inspect chronological trade availability and all post-lockout trades,
fees and liquidations. If failed, no further recovery-floor levels; keep original
reference and move to executable-entry information rather than additional guards.
No2024+economic use; no optimistic exit-order substitution.
