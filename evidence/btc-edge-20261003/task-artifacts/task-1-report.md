# Task 1 — existing-evidence attribution

Status: **DONE_WITH_CONCERNS**. Implementation, synthetic verification and real read-only diagnostic outputs are complete. Independent review is delegated to the controller and remains pending at this report's creation. Material evidence limits remain even if that review passes.

## Scope and commits

Only `research/edge_attribution.py` and `tests/test_edge_attribution.py` were added in Spotquant. No financial producer, native client, Coin test, network download, account/order/transfer/settings operation or old-evidence write occurred. PROJECT_STATE and controller files were not edited or committed.

- `efae517e877de0c08fdacef807513805a49db914`: read-only accepted-account attribution implementation and 13 synthetic tests.
- `5e69b0cad8f2c105222f9041829de0fc13106609`: exclude the initialization valuation from elapsed flat-day counts and add its regression test. This is the final implementation head.
- Independent-review base: `0ca979e`. Both commits contain only this task's diagnostic code/tests.

CLI: `python3.13 -m research.edge_attribution --evidence evidence/alpha-beta-next-20261002 --out NEW_DIRECTORY`. The output directory is exclusively created and contains attribution.json/attribution.md; existing output rejects before input processing. Runtime helpers are imported only for pure monetary/dust predicates; no producer or account meter is invoked.

## Accepted input identities

Inputs are selected through accepted final64 and canonical-five review proofs, the reviewed canonical inventory, and the final assessment's exact source manifests and fixed sensitivity entries. Legacy path references are relocated by explicit known prefixes to retained files and SHA-verified. No glob selection, source relabeling or equality waiver is used.

- Accepted final assessment: `a35ef6727d1a3befa1c86778eadc3bb604ffff3ad2b7cb63275419dc30c9a5d6`.
- Spot canonical base raw: `dc94a7b315ee8ea11cc7215cd8ff7c02a8ab94180499b2c4ebf7fe1448682323`; measured source `0c52c812301de3712f3637a1ce1b1241de0c40f1`.
- Rich original ATR raw: `f8f2e18abbeb7f062796026c074fb7868e3b2524a52c5a5bcf89131b6e655917`; measured source `8ca002522fbdce531dcfbbb783ff4d152a7fd66c`. It contains 38,292 decisions plus 147 fill rows; canonical has an empty opportunity journal. The accepted canonical bridge is explicitly consumed; canonical and rich fills/daily/allocations/positions/cash/BTC are compared exactly before enriching reasons.
- Coin original unscaled incumbent raw: `bf1d167979f4bb3d15925f0bcaf5337bd1cc0a17523628b3af0599875dc5a7c1`.
- Coin −60s raw: `cd916dbad8055b18e982db20bcecfce838f3d6af398e7e09a60b362d74e805af`.
- Coin +60s raw: `38912a76ca423785de39d1a63aa1bcbcde4c28830c0f5e25819c91f6710c3ae6`.
- All three Coin accounts retain source `acedaa43ca94223f24e2fe11851bbef74e032a69` and the raw measured metadata. The failed risk-unity original is not substituted for the accepted original baseline.
- Prior funding/basis assessment is loaded from `evidence/complete-delivery-20261001/assessment.json` and checked against that delivery's manifest.

All 11 consumed files retain exact byte SHA bindings in the JSON. Each input is checked during reading and again before report generation; the acceptance script independently rechecks all 11 afterward. The diagnostic source records its final commit, module SHA and reused follow/preview helper SHAs.

## Spot attribution result

Actual fills are linked by native order ID to durable immutable allocations. Net BTC includes recorded BTC fees; allocation weights are applied exactly, including the last-sleeve remainder. The existing runtime cumulative partial-sell/full-group-dust predicates determine whether a tactical campaign actually closed. Partial sells do not establish flatness. Native STOP_LOSS ownership proves a stop exit; ordinary market reasons come only from an exact fill link in the rich ledger. Missing ownership or fill reasons stay unknown.

There are 147 canonical fills, including 76 actual sell fills and 124 sleeve-specific sell classifications:

| Actual sleeve exit reason | Count |
|---|---:|
| SMA | 66 |
| Stop, including recorded stop-through | 30 |
| Extended | 2 |
| Other (recorded adverse exits) | 26 |
| Unknown in accepted real Spot evidence | 0 |

Flat daily endpoint classifications, excluding the initialization endpoint, are SMA 2054, stop 1306, extended 136, other 620, never-entered 17 sleeve observations. There are 127 consolidated flat intervals. Counts are sleeve endpoints, not unique whole-account cash days or uninterrupted intraday flat days.

The account retains proven owned fractional dust. Each flat endpoint preserves retained sleeve BTC, actual account BTC and exact-account-zero separately. Flat means a closed active tactical campaign, not a fabricated zero balance. Future endpoint price changes are explicitly `price_change_diagnostic`; `realizable_profit` is null. No rise during cash is reported as earned profit or an executable counterfactual return.

## Coin first divergence result

Each comparison covers 121 opportunity contexts: 99 stable impulse identities and 22 macro contexts. Macro raw identity is the negative creation timestamp, so ±60s creates different actual IDs. Macro association requires a uniquely matching **entire recorded DFII10 causal context and direction**, retaining both raw IDs, all timestamps and numeric differences; if the context differs or is ambiguous, the opportunities remain unmatched. This is diagnostic association, not an account-equivalence claim.

First differences are retained per opportunity and event stage rather than flooding the report with every later poll. Exact raw differences retain numeric representation, timing and native/client IDs. Post-execution quantity_after and post-run horizon closes remain available in exact differences but cannot become a prior causal feature or precede actual sizing/fill causes. Differing poll counts limit later occurrence pairing and are disclosed.

Both shifts first diverge at the genuine impulse identity `1578038400000`, with the same prior cash/wallet `1435.035552682611506140917905` USDT and zero quantity:

| Trace | Original | −60s | +60s |
|---|---:|---:|---:|
| Decision timestamp ms | 1578074403000 | 1578074343000 | 1578074463000 |
| Recorded decision mark | 7355.7907212 | 7357.3860385 | 7361.66962866 |
| Entry estimate | 7360.20 | 7361.80 | 7367.10 |
| Desired BTC | 0.9661394791732414710641954977 | 0.9659295002052340290861870333 | 0.9652345963283913446711313410 |
| Rounded accepted BTC | 0.966 | 0.965 | 0.965 |
| Post-execution summarized quantity | 0.966 | 0.965 | 0.025 |

Thus the first recorded cause is different observations, with consequent desired sizing and rounding. The +60s partial-execution outcome is not mislabeled as an earlier decision defect. Linked write and fill rows are retained for the actual IOC results. There is no evidence here of a specific unnecessary same-opportunity dependency, and no timing fix is authorized by this diagnosis.

Per-opportunity first operational categories: −60s has 51 different-observation, 1 exit and 1 prior-equity-propagation trace; +60s has 52 different-observation and 1 exit trace. The other contexts have no operational difference identified by this pairing. These counts do not establish full operating equivalence: exact timing/identity differences and unowned rows remain explicit. First-stage counts include 50 top-up differences in each comparison, raw sizing/fill differences, and the recorded ordinary-exit difference.

Prior daily equity already differs for 119 of 121 contexts in each shift. Later mixed observation/account-state changes therefore remain causally unisolated; prior-equity propagation is separately identified when the first recorded difference is prior account state and synchronized prior equity differs. This cannot establish what fraction of the final return difference is caused by each mechanism.

50 Coin fill rows in every account lack an explicit opportunity link through a recorded write attempt and remain unknown; they are not attributed to the nearest opportunity. Many decisions/writes also have null opportunity IDs. Original/−60s/+60s blocked-row counts are 857/871/844. Session summaries explicitly containing deadline/timeout reasons are 692/689/690. This is deadline-reason coverage, not a claim that each timeout lost a trade. Raw blocked rows and linked session summaries are retained, and unavailable ownership/context remains a material limit.

## Prior funding/basis evidence

The prior delivery's exact four-stress selection rows reject all four simple filters: Spot funding/basis and Coin funding-filter/basis-filter are complete/audited but matched-constraint and improvement gates fail. All prior rows and their raw assessment source identity are retained in the new diagnostic JSON.

Prior base CAGR/continuous-proxy MDD: Spot default 47.7781%/41.4842%, funding 43.0631%/41.4850%, basis 47.7756%/41.4885%; Coin incumbent 119.2319%/44.1051%, funding-filter 115.5518%/44.0971%, basis-filter 119.1867%/44.1051%. These are the prior assessment's annualization, not relabeled current ATR economics.

Distinct remaining registered questions are trend-conditioned funding/basis interactions with causal coverage, funding-aware Coin holding horizons, new-entry risk budgets and Spot ordinary-exit confirmation. Negative simple-entry-filter evidence does not answer those different mechanisms, and it does not justify recycling rejected thresholds or searching the historical sample.

## Verification and artifacts

- `python -m unittest tests.test_edge_attribution -v`: initial 10/10 pass, expanded 12/12 and 13/13 pass as requirements were completed (Python3.12).
- `python3.13 -m unittest discover -s tests -v`: 222 tests pass in 6.981s; log `/workspace/btc-alpha-beta-improve/task-artifacts/task-1-tests.log`. This covered 209 existing tests and the then-current 13 attribution tests.
- Final `python3.13 -m unittest tests.test_edge_attribution -v`: **14/14 pass**, including the initialization-boundary regression added afterward.
- `git diff --check` and staged diff check: pass. Final worktree was clean after the two own-file commits.
- Final real CLI command: `python3.13 -m research.edge_attribution --evidence evidence/alpha-beta-next-20261002 --out /workspace/btc-alpha-beta-improve/task-artifacts/task-1-attribution-v2`: exit0, existing-evidence read only.
- Repeat CLI against that same output: rejects with `output already exists`, and both output hashes remain unchanged.
- Independent output acceptance script rechecks all 11 input hashes and verifies financial_producer_executed=false; receipt `/workspace/btc-alpha-beta-improve/task-artifacts/task-1-acceptance.json`.

Final artifacts:

- `/workspace/btc-alpha-beta-improve/task-artifacts/task-1-attribution-v2/attribution.json`, SHA `afc0d7ee88da72c855a699a3eb13c155dbdc89753d30531a6837fc5f3b506324`.
- `/workspace/btc-alpha-beta-improve/task-artifacts/task-1-attribution-v2/attribution.md`, SHA `247524e86057b1682e014141b8ec4f49b3c71f04218a71b7201e30549b729f33`.
- Earlier `/workspace/btc-alpha-beta-improve/task-artifacts/task-1-attribution/` is retained as superseded pre-initialization-fix diagnostic evidence. It must not be used for final flat-day counts.
- This report: `/workspace/btc-alpha-beta-improve/task-artifacts/task-1-report.md`.

Synthetic coverage includes actual stop versus SMA, extended/other reasons, partial sells versus flat, retained owned dust, missing rich fill links, missing allocations, tampered rich fills, first observational versus propagated equity differences, raw timing/numeric differences, distinct macro IDs with exact-context association, post-execution quantities versus earlier causes, unlinked Coin fills, top-up/exit/timeout categories, hash mismatch, duplicate JSON keys and output-overwrite rejection.

## Concerns and review handoff

The independent code/evidence review is pending with the controller. The diagnostic consumes accepted financial review proofs; it does not perform a new independent money audit, market replay or same-observation counterfactual. Canonical Spot lacks the journal and relies on the accepted original-ATR bridge. Coin opportunity ownership is incomplete; occurrence pairing and uniquely equal macro context cannot prove schedule invariance or establish an execution bug. Daily endpoints and proxy paths cannot establish native continuous behavior. Historical-selection contamination, original unmet targets, zero native cases/actual account days and no prospective-alpha proof remain unchanged.


## Fix round 1 — independent review I1 and M1

Status: **DONE_WITH_CONCERNS / ready for scoped re-review**. The independent `task-1-review.md` requested changes. This appendix supersedes the v2 causal-field classifications and final-artifact references above; original outputs/report sections remain retained. No financial producers, Coin tests, native requests, state/docs changes or old output replacements occurred.

Commit: `fa81bf5dca86e96bbdd265174e2e3e31370c79d0`, only `research/edge_attribution.py` and `tests/test_edge_attribution.py`. Scoped diff base: `5e69b0cad8f2c105222f9041829de0fc13106609`. Module SHA: `4f7d32f57dc44a5594d042b8dcd1ce529fd60831cab2397069c02fb98c4b369d`. Final test-file SHA: `0405b973d78df857e1a5abe2f5348c36016f9839232ab5e768b9f57904000393`.

Frozen Coin producer provenance was read directly with `git show acedaa43ca94223f24e2fe11851bbef74e032a69:research/alpha_perp.py` and its entry-plan lifecycle. The decision row is timestamped before `original_decide`; action/reason/quantity_after/constraint are appended after return, while reason/error can be appended after a RECOVERABLE failure. All five fields now have event-aware summary provenance, remain in exact raw differences and are excluded from prior operational causes. Their completion timestamps are explicitly unavailable rather than fabricated. Entry/top-up sizing constraint differences are attributed to the actual later sizing event timestamps. The category selector no longer consults post-execution decision actions to classify an earlier observation difference as an exit.

I1 covering tests:

- `test_decision_constraint_summary_is_attributed_at_actual_later_sizing`: identical initial decision inputs with differing later decision-summary constraints and actual sizing constraints, covering both entry_sizing and topup_sizing. The earlier exact constraint remains visible with unknown available_at_ms; first operational divergence is the sizing event at timestamp120, not decision timestamp110.
- `test_decision_action_reason_and_error_preserve_later_summary_provenance`: all five post-execution fields differ, including a later failure summary. All remain exact evidence with populated_after provenance and no known completion timestamp; none precedes the actual entry-sizing cause.
- Existing `test_post_execution_summary_cannot_precede_actual_cause` continues to cover quantity_after separately.

M1 covering test:

- `test_write_quantity_is_requested_size_with_unknown_upstream_cause`: a sole explicit write payload.quantity difference is labeled requested_size, keeps the exact requested values, and leaves upstream_cause=unknown. Requested-size is also retained as a facet when other write fields differ.

Exact regression command before implementation:

`python3.13 -m unittest tests.test_edge_attribution.AttributionTests.test_decision_constraint_summary_is_attributed_at_actual_later_sizing tests.test_edge_attribution.AttributionTests.test_decision_action_reason_and_error_preserve_later_summary_provenance tests.test_edge_attribution.AttributionTests.test_write_quantity_is_requested_size_with_unknown_upstream_cause -v`

Result before fix: exit1, three tests executed, four reproduced failures (the constraint test has two failing entry/top-up subtests). This confirms that the covering regressions detect the reviewed behavior.

Final covering command: `python3.13 -m unittest tests.test_edge_attribution -v`. Result: exit0, **17 tests passed in0.005s**, including all existing attribution tests and the three added fix-round tests. `git diff --check` and staged diff check pass. Only the affected diagnostic suite was run; no financial or Coin test was invoked.

New real CLI command: `python3.13 -m research.edge_attribution --evidence evidence/alpha-beta-next-20261002 --out /workspace/btc-alpha-beta-improve/task-artifacts/task-1-attribution-v3`. Result: exit0. Both earlier directories are preserved. A repeat against v3 rejects output already exists and retains both v3 hashes unchanged.

Final v3 artifacts:

- `/workspace/btc-alpha-beta-improve/task-artifacts/task-1-attribution-v3/attribution.json`, SHA `02948e9026ed77bb43af02da9cbe04bbfbce564b826a7ffbe8187c5008f81b96`.
- `/workspace/btc-alpha-beta-improve/task-artifacts/task-1-attribution-v3/attribution.md`, SHA `832c1f82c9552f0cbb02add9a96e7f7f8638b5c2ae021b4ad70d6559ae6b564d`.
- `/workspace/btc-alpha-beta-improve/task-artifacts/task-1-fix1-acceptance.json`, SHA `d63f04928281a98142d4c0054565f6c7c1fa861313082e1eb5283bdf26285117`.
- `/workspace/btc-alpha-beta-improve/task-artifacts/task-1-fix1-verify.py`, SHA `f3220a8d8a9ac32e734ad94e0bf82390d84f481e40d438f9d0caa940d6f34b1d`.

Exact retained-output verification command: `python3.13 /workspace/btc-alpha-beta-improve/task-artifacts/task-1-fix1-verify.py`. Result: exit0, PASS for168decision traces, both real I1 sizing examples, real M1 requested write, all11input hashes, final output hashes and unchanged v2. The acceptance receipt additionally checked both v1 output hashes, rejected v3 overwrite and rechecked financial_producer_executed=false.

For −60s opportunity1602172800000 and +60s opportunity1687291200000, the decision-level constraint remains in exact differences with later-summary provenance and is absent from operational_fields; the corresponding entry-sizing trace includes constraint at its actual later timestamp. The reviewed +60s macro write for original ID−1700643602800 has exact requested quantity1.606→1.861, category/facet requested_size and upstream_cause=unknown.

The first whole-account observational divergence and Spot results are unchanged. Corrected per-opportunity first categories are −60s:52different_observations/1prior_equity_propagation; +60s:53different_observations. The former v2 exit labels came from consulting a post-execution action summary and are superseded; this does not prove equal exit behavior or assign unlinked exits. v3 stages retain50top-up divergences per shift and the +60s requested-size case. All ownership, proxy-path, macro-context/occurrence pairing, causal-isolation and no-native/prospective-proof limits remain.
