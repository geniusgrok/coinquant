# Project calibration financial-boundary review — PASS / APPROVE

Reviewed BASE `32ab1bb546bde064e641c4a2eb5ed4248e590acb` → HEAD `99fcf005d2cb15c13bb37322b65ab2863b19d65e` in the separate analysis worktree. Current full Python source SHA256 is `427f34ca3640cfa78f51173583af1d9c82f007baae155f3a992dcffb8171ad7b`. No material financial-boundary finding remains in this change. Approval covers calibration input plumbing and the scoped external orchestration below; it does not accept pending risk accounts or economic selection.

## Cutoff and deterministic project subset

The product change adds `load_project_calibration` and modifies only `assess`/`main` among existing functions. Independent AST comparison found all37 other existing functions unchanged, including calibration, risk statistics, canonical/raw consumption, baseline evidence, source proof, selection and risk inventory. Full unscaled consumption still requires exactly28 Spot plus20 Coin cases before the project-file comparison. The global calibration output remains the deterministic complete document; it has12 profiles when all12 bases are valid, and otherwise retains the existing explicit legal-profile/invalid-obligation treatment.

The project document must equal the full deterministic document restricted only to that project's registered profile names. Every root field and profile field remains covered, including cutoff, spec, scale, baseline identity, training end and original unscaled bundle/manifest SHA. Canonical JSON comparison rejects extra/missing fields and `True`/`1` or `1.0`/`1` substitutions. It offers no caller-controlled profile omission, trust flag or source override. Losing but valid base candidates still require their legal profiles and actual reruns; ranking outcomes cannot remove them.

Independent calculation used actual completed immutable consensus and trend-reentry daily paths, one bundle at a time. Exactly731 daily observations belong to2020–2021; the1,723 remaining days are excluded. NumPy recomputation gave:

| Actual training metric | Consensus | Trend reentry |
|---|---:|---:|
| Annual USDT volatility | 0.5007698764175386 | 0.5098268772324465 |
| BTC beta | 0.43731788190389737 | 0.44949810253302946 |

The independently calculated fixed scale is `0.9729026205883993`; the assessor returns `0.9729026205884008`, a difference below2e-15. Actual consensus self-calibration returns exactly`1.0`. Replacing **every** post-cutoff candidate equity and benchmark return with a nonnumeric sentinel leaves the entire training result unchanged, demonstrating those values are not read into training statistics. No production calibration document was created by this review.

Pure status/document fixtures additionally verify that invalid candidate bases have no invented profiles while their six Spot obligations remain inventoried; a valid candidate with an invalid baseline remains pending and receives no legal profile or unity pass. Missing valid profiles, added invalid profiles, changed bound raw hashes and root type mutations reject. These fixtures are not measured financial accounts.

## Raw calibration identity and final gates

`read_json` retains the actual supplied bytes' SHA, rejects duplicate keys/nonfinite JSON, and verifies the file remains unchanged during reading. Project validation returns that actual SHA, including gzip/whitespace differences. `consume` receives the chosen project/global document and its actual SHA, retains the original risk metadata and requires exact metadata/profile correspondence. The global hash is never substituted for an early project-file hash.

Without an override, existing global-only flow remains intact. Any supplied global file must still equal the full deterministic document, even when project overrides are present. The report separately labels the global calibration identity and each consumed project's actual hash/scope/profile list. Supplying a risk bundle without its legal matching calibration rejects.

The original baseline byte pins and six equality groups, source-execution equivalence, ten new-candidate risk obligations, two baseline unity controls, achieved2022+ volatility/beta limits, sensitivities, original selection/targets, `--final` pending-work rejection, all-valid/freeze conditions and native/account-day-zero meanings remain intact. Completed but invalid/rejected evidence does not become a validity or adoption claim. Independent committed-tree source equivalence against frozen Spot8ca passes with the sole assessor exception, digest `c2dd29733ec5bb96137a8ab27cc0e8dd604d74bf6d1e108d45a554b8923e6cf8`.

## External orchestration reviewed

- `run_spot_early_risk.py`: SHA256 `a21b00a2f77881d092dbd3ce8d3e2d1c1516ad00147dc3c867300ba8930ed26c`.
- `run_registered_followthrough_project_calibration.py`: SHA256 `09e38e09eb755a79a8a6d7d20e83b8a371cf507e2f4c6e3b2315e13ddd9d37cd`.

The early helper waits for the full Spot manifest **and original Spot controller21624 to exit**, then consumes the exact28-scene set, proves source equivalence and verifies all four pinned original baseline scenes before deriving the Spot-only training file. It launches actual legal Spot base risk accounts from frozen8ca, with no Coin producer call. Its completion receipt is written only after the actual risk command(s), compression and SHA checks return; no null path is represented as completed risk evidence in the final assessor when legal profiles remain pending.

The final queue still waits for Coin32321 to exit and both full matrices, derives the full deterministic global document, and verifies the early Spot calibration/raw-result receipt hashes. It supplies `--risk-spot-calibration` with the actual early file while Coin uses the global file. The full assessor independently verifies the Spot file is the exact final deterministic subset. No Spot rerun is silently duplicated by the main queue; it joins the early result before later combination stages.

All Coin producer operations remain **whole-process serial**: existing Coin20 → Coin risk → applicable Coin combination → each Coin sensitivity. No separate Coin worker is introduced by the early helper. This review explicitly inspected the lock distinction missed in the withdrawn parallel-Coin approval: Spot's frozen State uses its per-temporary-directory execution lock; it does not invoke Coin's shared HOME account lock. Actual Spot workers retain the already-used process-isolated two-worker mechanism and each measurement creates its own temporary state directory. No locks are bypassed, identities changed or HOME altered.

Root must perform the stated normal stop/receipt of old waiting queue32493 before starting the new main queue once; full producers are not stopped. This is known-session orchestration, not a general concurrency guarantee. The earlier parallel Coin approval remains withdrawn.

## Verification and limits

Five targeted **pure fixture** tests independently rerun and pass in0.111s: project subset exactness, project/global actual-SHA integration, CLI routing, training/future independence and exact risk-file/profile binding. These tests invoke no Coin producer or private account State. `git diff --check` passes. Additional independent actual-prefix/status/source proof is recorded in `project-calibration-financial-review-proof.json`; executable review is `review_project_calibration_financial.py`.

Reviewer account replays0, private State invocations0, downloads0, product/cache/source/HEAD mutations0. All temporary fixture and final review output writes are external. Actual seven Spot reruns, subsequent complete48 assessment, actual risk matching/sizing, core invariants, combinations and sensitivities still require completed-evidence review. Whole historical results remain research-contaminated, not clean prospective evidence; native cases and actual account-days stay zero.
