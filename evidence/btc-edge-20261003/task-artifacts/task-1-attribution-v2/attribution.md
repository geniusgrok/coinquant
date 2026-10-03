# Existing-evidence attribution

Read-only accepted evidence. Price opportunity is not earned profit. Native cases/account days: 0/0.

## Spot

Exit sleeve counts: {"sma": 66, "stop": 30, "other": 26, "extended": 2}
Flat sleeve-day counts: {"never-entered": 17, "sma": 2054, "stop": 1306, "other": 620, "extended": 136}

Flat denotes closed campaigns with proven retained dust; daily endpoints do not prove intraday flatness.

## Coin

-60000ms first divergence counts: {"different_observations": 51, "exit": 1, "prior_equity_propagation": 1}
First account operational divergence: {"event": "decision", "occurrence": 0, "comparison_at_ms": 1578074343000, "left": {"ledger_index": 85, "raw": {"event": "decision", "at_ms": 1578074403000, "bar_ms": 1578067200000, "opportunity": 1578038400000, "age_ms": 36003000, "trigger": {"identity": 1578038400000, "close": "7198.02", "prior_atr": "72.67142857142857142857142857", "direction": 1, "kind": "impulse"}, "decision_mark": "7355.7907212", "quantity_before": "0", "idle_cash_usdt": "1435.035552682611506140917905", "wallet_usdt": "1435.035552682611506140917905", "desired_stop": null, "risk_scale": "1", "action": "enter", "reason": "enter", "quantity_after": "0.966", "constraint": "target"}}, "right": {"ledger_index": 88, "raw": {"event": "decision", "at_ms": 1578074343000, "bar_ms": 1578067200000, "opportunity": 1578038400000, "age_ms": 35943000, "trigger": {"identity": 1578038400000, "close": "7198.02", "prior_atr": "72.67142857142857142857142857", "direction": 1, "kind": "impulse"}, "decision_mark": "7357.3860385", "quantity_before": "0", "idle_cash_usdt": "1435.035552682611506140917905", "wallet_usdt": "1435.035552682611506140917905", "desired_stop": null, "risk_scale": "1", "action": "enter", "reason": "enter", "quantity_after": "0.965", "constraint": "target"}}, "exact_differences": {"age_ms": {"left": 36003000, "right": 35943000}, "at_ms": {"left": 1578074403000, "right": 1578074343000}, "decision_mark": {"left": "7355.7907212", "right": "7357.3860385"}, "quantity_after": {"left": "0.966", "right": "0.965"}}, "timing_or_identifier_fields": ["age_ms", "at_ms"], "post_execution_or_future_diagnostic_fields": ["quantity_after"], "operational_fields": ["decision_mark"], "category": "different_observations", "facets": ["different_observations"]}

60000ms first divergence counts: {"different_observations": 52, "exit": 1}
First account operational divergence: {"event": "decision", "occurrence": 0, "comparison_at_ms": 1578074403000, "left": {"ledger_index": 85, "raw": {"event": "decision", "at_ms": 1578074403000, "bar_ms": 1578067200000, "opportunity": 1578038400000, "age_ms": 36003000, "trigger": {"identity": 1578038400000, "close": "7198.02", "prior_atr": "72.67142857142857142857142857", "direction": 1, "kind": "impulse"}, "decision_mark": "7355.7907212", "quantity_before": "0", "idle_cash_usdt": "1435.035552682611506140917905", "wallet_usdt": "1435.035552682611506140917905", "desired_stop": null, "risk_scale": "1", "action": "enter", "reason": "enter", "quantity_after": "0.966", "constraint": "target"}}, "right": {"ledger_index": 82, "raw": {"event": "decision", "at_ms": 1578074463000, "bar_ms": 1578067200000, "opportunity": 1578038400000, "age_ms": 36063000, "trigger": {"identity": 1578038400000, "close": "7198.02", "prior_atr": "72.67142857142857142857142857", "direction": 1, "kind": "impulse"}, "decision_mark": "7361.66962866", "quantity_before": "0", "idle_cash_usdt": "1435.035552682611506140917905", "wallet_usdt": "1435.035552682611506140917905", "desired_stop": null, "risk_scale": "1", "action": "enter", "reason": "enter", "quantity_after": "0.025", "constraint": "target"}}, "exact_differences": {"age_ms": {"left": 36003000, "right": 36063000}, "at_ms": {"left": 1578074403000, "right": 1578074463000}, "decision_mark": {"left": "7355.7907212", "right": "7361.66962866"}, "quantity_after": {"left": "0.966", "right": "0.025"}}, "timing_or_identifier_fields": ["age_ms", "at_ms"], "post_execution_or_future_diagnostic_fields": ["quantity_after"], "operational_fields": ["decision_mark"], "category": "different_observations", "facets": ["different_observations"]}

No unnecessary dependency is established. Raw timestamps/values and per-opportunity stage traces are in JSON.

## Prior funding/basis

All four prior simple filters were ineligible; negative evidence is retained.

- Trend-conditioned funding/basis interactions require a separately registered causal test.
- Coin holding-horizon funding awareness is distinct from a simple entry filter.
- Risk budgets and Spot ordinary-exit confirmation are distinct mechanisms; old filters do not answer them.
- Reusing a previously rejected simple filter or tuning thresholds to this history is not justified.

## Input byte bindings

- `9453b031924322612da3445e305e0499dce87eda20eb604def14ff7aa54241de` /workspace/btc-alpha-beta-improve/spotquant/evidence/alpha-beta-next-20261002/review/final64-financial-review-proof.json
- `a35ef6727d1a3befa1c86778eadc3bb604ffff3ad2b7cb63275419dc30c9a5d6` /workspace/btc-alpha-beta-improve/spotquant/evidence/alpha-beta-next-20261002/scratch/registered-final-repaired.json
- `c1803ecb6c66a1f6397415ce2b033f569ebca46e6df42419bee87ea45f351b8d` /workspace/btc-alpha-beta-improve/spotquant/evidence/alpha-beta-next-20261002/review/spot-canonical-five-financial-proof.json
- `db23143dffbd6d8c5711789fee8b3ac92454d7712bcad14644cd244197701b32` /workspace/btc-alpha-beta-improve/spotquant/evidence/alpha-beta-next-20261002/scratch/spot-canonical/canonical-inventory.json
- `dc94a7b315ee8ea11cc7215cd8ff7c02a8ab94180499b2c4ebf7fe1448682323` /workspace/btc-alpha-beta-improve/spotquant/evidence/alpha-beta-next-20261002/scratch/spot-canonical/base.json.gz
- `f8f2e18abbeb7f062796026c074fb7868e3b2524a52c5a5bcf89131b6e655917` /workspace/btc-alpha-beta-improve/spotquant/evidence/alpha-beta-next-20261002/scratch/spot-singletons/atr-stop.json.gz
- `bf1d167979f4bb3d15925f0bcaf5337bd1cc0a17523628b3af0599875dc5a7c1` /workspace/btc-alpha-beta-improve/spotquant/evidence/alpha-beta-next-20261002/scratch/perp-singletons-retry1.json.gz
- `cd916dbad8055b18e982db20bcecfce838f3d6af398e7e09a60b362d74e805af` /workspace/btc-alpha-beta-improve/spotquant/evidence/alpha-beta-next-20261002/scratch/sensitivity-serial-retry1-incumbent-10000--60000.json.gz
- `38912a76ca423785de39d1a63aa1bcbcde4c28830c0f5e25819c91f6710c3ae6` /workspace/btc-alpha-beta-improve/spotquant/evidence/alpha-beta-next-20261002/scratch/sensitivity-serial-retry1-incumbent-10000-60000.json.gz
- `220508d338b57744a88ca1f2704263da97f6eb3c9601d1ad71aac2de1068f0d1` /workspace/btc-alpha-beta-improve/spotquant/evidence/complete-delivery-20261001/manifest.json
- `a1cc9e0990c61713fa216221add48e28aa57e5c4675d9295ededb6ba541624bf` /workspace/btc-alpha-beta-improve/spotquant/evidence/complete-delivery-20261001/assessment.json

## Limits

- Accepted financial reviews are consumed, not re-executed or independently reconstructed here.
- Historical proxy evidence is contaminated by prior research; no prospective alpha or native qualification.
- Flat is a closed tactical campaign; retained owned dust is not exact account zero.
- Daily endpoints do not prove uninterrupted intraday flatness.
- The initialization valuation is excluded from elapsed daily endpoint counts.
- Future endpoint price changes are opportunity diagnostics, never earned or realizable profit.
- Missing ownership poisons affected sleeve attribution; missing exit reasons remain unknown.
- Exact comparisons retain all raw timestamps, identifiers and numeric values.
- Event occurrences align within actual opportunities; differing poll counts limit later pairing.
- Macro contexts pair only uniquely identical full recorded DFII10 context/direction; distinct creation IDs remain distinct.
- Recorded decision quantity_after can summarize later execution; sizing/fill traces retain their timestamps.
- Post-execution quantity_after and post-run horizon closes stay in exact differences but cannot identify a prior cause.
- First account divergence means first among explicitly opportunity-owned rows; unowned observations remain separate.
- A timing or price observation change is not by itself a bug.
- Earlier equity differences can propagate; mixed observation/state changes are not causally isolated.
- Unlinked fills and blocked observations have unknown opportunity ownership.
- No counterfactual same-observation execution was produced; no dependency fix is justified here.
