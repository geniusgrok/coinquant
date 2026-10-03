# Task 1 independent review

Reviewed requirements in `task-1-brief.md` and `research/edge-PLAN.md`, implementation/report evidence, and the complete `0ca979e..5e69b0c` diff. Diagnostic source: `5e69b0cad8f2c105222f9041829de0fc13106609`; module SHA `f5924d156e34ef1ad8b8008a2092c8ec804b15f2eb550318bd02fb38e151f222`. Selectively inspected final `task-1-attribution-v2/attribution.json`, without loading its full contents into the review context. No code edits, producers, native requests, or test reruns occurred.

**Spec compliance verdict: REQUEST CHANGES.** Most requirements are satisfied, but one later sizing result can still be treated as a prior causal field. Resolve Important I1 before using the attribution as the completed causal diagnosis.

**Code-quality verdict: REQUEST CHANGES.** The module is reasonably direct and uses existing runtime ownership/dust predicates. The causal-field boundary is incomplete; the existing regression proves only `quantity_after`, leaving I1 uncovered. Minor M1 is nonblocking.

## Findings

### Critical

None found.

### Important I1 — decision constraint is backdated from later sizing

**Source evidence:** `spotquant/research/edge_attribution.py:235` excludes only `quantity_after` and `post_run_diagnostic_closes`; lines 302–304 treat all other differences as operational at the row's `at_ms`. The accepted journal producer in `coinquant/research/alpha_perp.py:269` timestamps the decision before calling `original_decide`, then at lines 279–281 appends `constraint=engine.entry_constraint` after that call returns. `coinquant/coinquant/lifecycle.py:512` obtains the entry preview and line 513 sets that constraint. The sizing journal has its own later clock (`coinquant/research/alpha_perp.py:320–327`). Thus a differing decision-level constraint is a later sizing summary, not a feature available at the initial decision timestamp.

**Observed final-output evidence:** For −60s opportunity `1602172800000`, decision comparison time `1602215943000` includes operational `constraint: target -> liquidity_cap`, although the corresponding entry-sizing comparison occurs at `1602215945800`. For +60s opportunity `1687291200000`, the decision at `1687500003000` includes `liquidity_cap -> funding_cap`, with sizing at `1687500005800`. Seven −60s and four +60s decision-stage differences include this field. These particular rows also differ in observations, so the reported first whole-account observation divergence remains supported; the field chronology and potential first-cause selection are still incorrect. With equal initial observations and differing later constraints, this code would select the decision summary before the actual sizing cause.

**Required fix:** Keep decision-level `constraint` in exact raw differences but exclude it from prior operational causes, using event-aware field provenance. Attribute constraint differences at the recorded entry/top-up sizing stage. Add a synthetic regression with identical initial decision inputs, different decision summary constraints, and later differing sizing constraints; assert the first operational divergence is the sizing event and the earlier exact difference remains visible. Regenerate a new diagnostic directory and update report/hash evidence without overwriting originals.

### Minor M1 — explicit write quantity differences lose the sizing category

**Source evidence:** `spotquant/research/edge_attribution.py:248–258` recognizes sizing only for `entry_sizing`; a write's `payload.quantity` alone falls through to `other_or_unknown`. The final +60s trace for macro context with original ID `-1700643602800` has a BUY IOC write quantity `1.606 -> 1.861`, at comparison time `1700643607800`, classified `other_or_unknown`.

**Impact and recommended fix:** This does not change the first account-level cause, and the quantities are retained. However, the known requested order-size difference is unnecessarily reported as unknown. Recognize the write quantity as a sizing facet (without claiming its upstream cause), and cover it with a small synthetic assertion.

## Requirements and verification assessment

- Accepted inputs are resolved through the final review, canonical inventory/bridge and exact sensitivity hashes, not globs. Raw files are SHA-checked before/after reading and before output generation; source metadata remains distinct. The canonical/rich Spot bridge requires exact equality in fills, daily, allocations, positions, cash and BTC. No first-timestamp normalization or numeric equality waiver appears.
- Spot uses actual durable native-order allocations, net BTC fees and runtime cumulative-sell/full-group-dust predicates. Partial sales remain active unless the actual residual satisfies those predicates. Retained owned dust and exact account zero are separate. Missing owners/reasons remain unknown; initialization is excluded. Daily endpoints are explicitly limited, and interval price changes have `realizable_profit: null`.
- Coin fills inherit opportunity ownership only through explicit write-client links. Unowned fills/observations remain disclosed. Macro association requires unique exact full recorded DFII10 context/direction, preserves both raw IDs, and is diagnostic rather than an account-equivalence bridge. Occurrence pairing and differing poll counts are disclosed; timing sensitivity alone is not labeled a bug. Earlier equity and mixed-state/observation limitations remain explicit.
- Prior funding/basis negatives retain their prior assessment identity, rather than being relabeled as current ATR performance. Remaining mechanism questions are distinct. BTC-only economics, finite sessions, original target failures, historical contamination and zero native qualification remain unchanged. No runtime producer/account changes are introduced. The full diff includes the controller's progress-ledger commit; task-owned commits contain only the diagnostic module/tests.
- Recorded verification: Python 3.13 full Spot suite **222 passed** before the initialization amendment; final task suite **14 passed** after it. The retained test log confirms the 222-test run. Tests meaningfully cover partial sales, stop/SMA attribution, ownership, tampering, exact values/timing, macro identity, propagated equity and exclusive outputs. The final initialization amendment has a focused regression. I did not rerun these already evidenced checks. The reported read-only CLI and acceptance receipt bind final outputs and all 11 inputs. Neither the suite nor receipt catches I1 because the post-execution regression at `tests/test_edge_attribution.py:133–140` changes only `quantity_after`.

The evidence supports the existing first-account price-observation conclusion and the stated availability limits. It does not yet support treating every emitted operational field as causally available at its comparison timestamp.
