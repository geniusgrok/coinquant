# Conditional Spot adoption boundary — read-only preparation

This is a design for **only if `atr-stop` remains the final mechanically selected Spot account** after all registered cases, risk obligations, combinations, controls, sensitivities and independent financial review finish. The provisional four-scene result does not select it. A different final singleton or combination needs a corresponding boundary review. No implementation, tests, replay, cache access, download or account action was performed here.

Read the Task4 brief/protocol/plan and existing adoption ruling, frozen Spot model/preview/session/follow/execution and alpha_spot hooks, and assessment/forward source at `99fcf005d2cb15c13bb37322b65ab2863b19d65e` (analysis99). Original producer sources remain Spot8ca/Coinaced. Selection uses the registered unscaled accounts; calibrated results remain a separate risk diagnosis and equivalence obligation, not permission to choose a new default risk multiplier.

## Minimal shared implementation boundary

Do this later in a separate adoption checkout, with clean committed source frozen before canonical replays. Default native/live authorization stays unchanged.

| Path | Required conditional change |
|---|---|
| `spotquant/model.py` | Retain14 completed true ranges plus the preceding close through checkpoint/restore. Compute each range before replacing the previous close, using `max(high-low, abs(high-prev_close), abs(low-prev_close))`; no range for the first origin bar. ATR is unavailable until14 ranges exist. Hash-bind and validate the new queue and bump checkpoint version. Do **not** replace persistent `trail=.28` with the changing ATR value: the measured research policy adjusts decision views, not historical model/follow state. |
| `spotquant/preview.py` | Add one small shared decision-view helper implementing the exact measured `Policy.adjust_stop` semantics, and carry the selected post-portfolio behavior described below. Keep existing consensus and signal logic. A transient stop-floor attribute handled by `Model.stop_price`, or an equivalent small view helper, can replace the research instance lambda; it must not enter the price-only checkpoint. |
| `spotquant/session.py` | Supply the already folded positions and cached allocated owners to that helper when building decision views. Consume ATR from completed model state, never another adapter call. Change RULE/recorded stop description and enforce early rule/checkpoint rejection. Commit new ATR state atomically with the existing model/position transaction. |
| `spotquant/execution.py` | At the terminal partial-sale remainder path around lines214–219, rebuild the view with the **same** shared ATR/floor helper before `_protection`. Use committed position/owners there, matching the research remainder hook; leave recovery, identity, cancel/replace and dispatch logic otherwise intact. |
| `spotquant/follow.py` | Prefer no behavior change. Its completed-history pass continues updating actual-fill peaks, repair and adverse flags. Do not apply evolving ATR stops retrospectively to catch-up lows or manufacture historical exits. Its existing position `protection` flag is overridden to `resting` on the decision view exactly as in the measured policy; actual venue fills remain authoritative. |
| `research/adoption_replay.py`, `research/adoption_bridge.py` (proposed narrow tools) | A canonical-session replay adapter and exact evidence bridge verifier, frozen and independently reviewed before use. No candidate grid, copied strategy, engine monkeypatch or generic ignore list. |
| Existing focused tests and current README/AGENTS/PROJECT_STATE/HANDOFF | Verify safety/identity/equivalence boundaries and document the selected default and remaining qualifications. Preserve registered spec/protocol and historical reports. |

The view helper must copy the measured behavior exactly: distance `clip(4*ATR14/completed_close,.10,.30)`; floor from that sleeve's allocated STOP_LOSS owners with status in `(TERMINAL-REJECTED) ∪ {NEW, PARTIALLY_FILLED}` and the existing `signal_ms >= floor(first_ms/DAY)*DAY-DAY` boundary; stop `max(proven_floor, actual_peak*(1-distance))`; no pre-fill high and no ownership inference. Entry preview uses completed close; actual filled positions and repair use their original actual-fill peaks. Use the same ownership snapshot as the research path, including dust, and retain unknown-data failures.

**Moving only the ATR formula is insufficient.** Preserve these selected-path effects from `alpha_spot.Policy.__call__`:

1. A proposed held protection at/above the actual decision mark changes that sleeve to an ordinary exit, aggregates the original tactical sell quantities with the same floor/minimum rule, and rebuilds grouped protections. No fictitious stop fill.
2. Final BUYs defer to any SELL and are capped, in existing order, by free cash and remaining whole-account capital at the decision mark, with original quote rounding/minimum and sleeve advisory quantities. This branch executes for `atr-stop` even at scale1; the original consensus portfolio alone is not equivalent.
3. The fixed calibration scale is applied only to new BUY allocation at actual decision time after the cutoff, after the same cap calculation. Do not resize owned quantities or replace the selected unscaled default by its diagnostic calibrated variant.

For the calibrated canonical replay, expose the shared allocation function's scale as a narrow research input, default1. The replay adapter may inject only the verified fixed scale/cutoff using the same passive venue time and record passive attribution. It must still execute the canonical model, decision helper, session and Lifecycle; it must not reinstall `alpha_spot.Policy`, its model/State replacement, or its stop/remainder hooks. No runtime import of the research module or calibration file is necessary.

## Checkpoint boundary

Change RULE and model checkpoint version; validate ATR queue length/values/chronology alongside existing flags. Reject old static-stop checkpoints, old research wrappers, wrong rule/components/scale identity, and incomplete/malformed new state. Do not silently rebootstrap, synthesize14 ranges from closes, discard positions or create a new directory as proof of a flat account.

A guard only in `_load_models` is too late for a no-write migration boundary: `cycle` calls `Lifecycle.recover()` first, and `_load_models` presently auto-adopts a different rule when recorded positions are flat. Add a read-only identity guard at cycle entry **before recovery can issue writes**, covering saved models/rule and incompatible durable pending state, including flat accounts. Keep the old state and installed protection intact; any later migration/recovery under its old engine is a separate controlled procedure. Fresh all-cash replay initialization still follows the normal cold-start gate.

Later focused checks should cover legacy flat/held/pending rejection with no writes; checkpoint round-trip and failed-cycle atomicity; completed ATR/future-bar independence; exact installed-stop floor; actual-fill peak; through-mark reduction; partial-sale remainder; unknown/cancel-replace recovery; and unchanged default read-only/live block. These checks were not run in this preparation.

## Canonical replay and acceptance

After final selection and source review, replay **five full actual accounts** on the adopted shared path: `base`, `fee150`, `slip2`, `outage` at unscaled1, plus `base` with the selected candidate's exact actual calibration file/profile. Use the original10k capital, prior FX/.001 conversions, market hashes, original795 starts (789 for outage),300-second sessions,5-second polls and existing HistoricalVenue/archive/money audit. Preserve original consumed/calibration hashes and new adopted-source identities. Keep overlapping synthetic-account jobs serial and wait for the frozen financial chain to finish; separate directories do not prove lock isolation.

The existing `complete_spot.measure` installs `Policy/configured` over `session.portfolio`, and `alpha_spot.measure` additionally installs strategy/remainder hooks. Calling either unchanged on the adopted tree does not establish canonical-default equivalence. The replay adapter must reuse the actual venue, account meter/audit and session runner while explicitly bypassing those decision replacements. A tiny reviewed seam in the new replay adapter is preferable to a duplicate engine. Freeze and hash any measurement seam itself before running.

Compare each adopted account against its corresponding **frozen actual research account** using analysis99's six evidence groups: financial/audit, fills, daily, ownership, operating, remaining-original fields. Require all groups equal and each new account complete/known/audited with independent archive proofs. Retain relational synthetic-client normalization and the existing verified archive-hash treatment only. Do not normalize timestamps, prices, quantity, cash, fees, deadlines, cycles, statuses, allocations or unexplained fields. Research/checkpoint/source identity differences belong in explicit metadata/provenance, not a catch-all excluded-fields rule. Any new unmatched field or fingerprint difference blocks adoption until explained and independently reviewed; do not waive it based on close CAGR/MDD.

## Separate analysis and adoption provenance

Analysis99's full Python identity includes the old Spot runtime. Its existing `verify_execution_equivalence` allows only the assessor path to differ, and `forward_binding` also requires the complete current analysis executable to match `report.analysis_source`. **Those gates correctly reject an adopted runtime.** Do not enlarge that exclusion, relabel the original raw source, or advertise adopted-source financial measurements as analysis99 measurements.

Keep the historical final report immutable with its own raw SHA and truthful analysis99 identity. Create a separate SHA-bound adoption bridge containing:

- final report SHA, final selection and original baseline proof; analysis99 full source identity;
- frozen selected producer commit/full Python digest, exact adopted commit/full Python digest, spec/protocol hashes and reviewed changed-path before/after hash inventory;
- all five original/adopted raw account SHAs, actual calibration-file/profile SHA and market/FX/schedule identities;
- all six equality-group results per account, validity/archive results, verifier source/hash and independent source/evidence review references.

Reconstruct both complete source digests from Git trees; the exact changed-path inventory is an audit record, **not** an allowlist that accepts arbitrary future edits. The five-account proof authorizes that one adopted source identity only. A later documentation commit/merge may use exact full Python-byte equivalence; further Python changes need another reviewed bridge. Preserve every prior raw and report.

Use a separate explicit adoption-forward entrypoint that validates the final report plus this bridge and the exact current adopted source before initializing an all-cash diary. Record `historical_analysis_source=analysis99`, original measured source, adopted execution source, bridge SHA and bridge-verifier source separately. If the verifier imports analysis99 helpers, verify their complete immutable source in its dedicated checkout; do not falsely require the adopted executable's full tree to equal analysis99 or implicitly load whichever checkout is current. Keep the existing non-adoption forward gate intact. Initialization remains actual-current-UTC, zero observations/account-days/native cases; only later observed completed public bars may append.

## Safer fallback

If final eligibility, complete canonical equality, early state rejection or exact source/bridge/forward proof cannot be completed, retain the incumbent consensus default. Report `atr-stop` (if finally selected) as an eligible **research-only** candidate with adoption/equivalence incomplete. Preserve its results and rejection/blocker evidence; do not weaken source checks or use its proxy performance as native qualification. A qualifying research diary can remain bound to the frozen research engine through analysis99's existing strict interface, explicitly without an adopted-runtime claim; otherwise leave forward initialization pending. Native cases and actual account-days remain zero.
