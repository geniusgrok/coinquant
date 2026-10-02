# Task 1 implementation report

Status: DONE. Independent spec/quality review is the next gate; no full-window measurement or default promotion was performed.

## Source and scope

- Worktree: `/workspace/btc-alpha-beta-next/coinquant`.
- Branch: `codex/btc-alpha-beta-next-20261002`.
- BASE: `047f09156a870c9b40121e0a59c9542c7fe25e89`.
- HEAD/implementation commit: `c2a01d1c7ad09d58001ec2897a5a64d1b8284dd6` — Add frozen perpetual alpha mechanisms on shared session meter.
- Files: `research/alpha_perp.py` (444 lines), `tests/test_alpha_perp.py` (233 lines).
- No shared production, Lifecycle, exchange, existing runner, or default code changed. `git diff 58074c1e4f1b374ce5a4bdccccf474a51647be47 HEAD -- coinquant research/complete_perp.py` has no output.
- Before source writes, `git ls-remote origin HEAD` returned `58074c1e4f1b374ce5a4bdccccf474a51647be47 HEAD`.
- `git diff --check` passes. Only the root agent's pre-existing concurrent `PROJECT_STATE.md` progress edit remains unstaged; this agent did not modify or commit it. Tracked implementation/research sources are clean, and the measured source identity reports dirty=false.
- No Spot files, main checkout, credentials, native accounts, orders, transfers, settings, or subagents were accessed. Official public aggTrade archives were restored into `/tmp/task1-public-prints` using the existing checksum-verified RollingPrints implementation.

## Implementation and self-review

The new runner calls `complete_perp.measure`, its unchanged `ResearchExchange`, original finite `session.run`, and original independent cash-ledger audit. Scoped stdlib hooks are restored through ExitStack even on exceptions. No instrumentation performs extra adapter reads, waits, or clock advances. The no-op synthetic fixture asserts exact adapter-call/request/clock/cash/fill equality, and the historical prefix compares real monetary outputs.

- Fresh entry: immutable primary trigger close and prior ATR survive checkpoints. Only flat new primary longs receive the inclusive 24-hour and one-prior-ATR chase checks; owned positions and macro rules retain their ordinary behavior. In a combination, a newly created compression opportunity is also a primary opportunity and receives this entry gate.
- ATR trail: completed bars update only causal high/ATR state. The trail starts at the confirmed actual average entry price; a completed bar contributes its high only if its opening timestamp is at or after the fill-confirmation timestamp, so the overlapping entry bar cannot introduce a pre-entry high. At the actual owned-primary decision, the proposed stop is bounded below by the proven stop. Through-mark proposals use original owned reduction; legal amendments use original protection replacement. Macro geometry and stop budgets remain unchanged.
- Compression breakout: original primary opportunity generation gets priority. Only when no primary opportunity remains active is the registered breakout added. High/ATR/median inputs all precede the trigger; stop, take and 42-bar expiry follow the frozen formula.
- Single top-up: the original entry and complete original top-up preflight remain. Before send, the journal preserves the original add anchor because Lifecycle replaces its transient intent result during settlement. Only cached terminal orders linked to an owned add and independently reconciled cached native fills consume an allowance. Counting uses actual fill time's completed 4-hour bar, including recovery after unknown replies. Pending/unknown intents still use original recovery and are never resent. Original entry-session restriction and committed requested size are preserved.
- Checkpoints hash-bind candidate/components, source identity, frozen spec/protocol, risk profile/file hash, initial CNY, original schedule hash, and actual full start-list hash. Trigger and causal trail/rolling state are hashed; malformed or mismatching checkpoint state fails closed.
- Fixed risk scale applies only through new-entry sizing after `1640995200000`; before that it is 1. Existing requested campaign quantity and macro stop budget are not recomputed or relaxed.
- Causal ledger retains opportunities, decision identity/age/trigger/mark/cash, sizing desired/accepted amount and constraints, write attempts, fills/exit type, top-up blocks and every cycle failure. All fill and exit classification uses existing cached proxy records. 5/20-day completed closes are attached only after all execution and audits have finished and explicitly labeled `post_run_diagnostic_closes`; they are never decision inputs or assumed realizable fills.

Self-review found and corrected a pre-commit top-up bug: looking for original add anchors in `intents.result` after settlement does not work because Lifecycle replaces that transient result. The durable research-only anchor plus reconciled-fill check fixed this; both normal partial and lost-response tests now show exactly one initial entry and one confirmed add, with protection intact. No unresolved failing tests remain.

## CLI and Task 3 data contract

CLI: `python -m research.alpha_perp --out FILE [--limit N] [--candidate NAME] [--scenario NAME] [--risk-calibration FILE] [--combo COMPONENTS] [--initial-cny VALUE] [--start-offset-ms VALUE] [--restore-prints]`, with existing `--market`, `--prints`, `--fx` paths.

Default matrix is exactly 5 candidates x 4 registered stresses, in frozen order. Single scenarios/candidates and comma-separated registered multi-component combinations are supported; combination identity joins canonical registered order with `+`. No subset search or new parameter grid exists. Capital is restricted to 9900/10000/10100 and offsets to -60000/0/+60000 ms; sensitivity flags require one fixed candidate/combo and base. Results/progress never overwrite; any limit including 795 stays explicitly incomplete and must write under `/tmp`. `.json` and lossless `.json.gz` are supported.

Output retains `results[candidate][scenario]` and every original monetary/audit/session/daily row field; each row adds `opportunity_ledger`. The old meter's source identity remains `inputs.source` (`git_head`, `dirty`, `python_sources_sha256`). New identities are `inputs.spec_sha256`, `inputs.protocol_sha256`, `inputs.original_meter_protocol_sha256`, `inputs.measured_source`, `inputs.risk_calibration_sha256`, `inputs.risk_profiles`, `inputs.candidates`, `inputs.initial_cny`, `inputs.start_offset_ms`, `inputs.original_schedule_sha256`, `inputs.actual_starts_sha256`. Existing `market_identity`, `loaded_minute_files`, `loaded_print_files`, `fx_sha256`, and original `schedule_sha256` are preserved. Actual-start hash covers the entire shifted 795-start list, including on limited smokes. `selection` deliberately says independent complete matched-risk analysis is pending; it never reuses the retired selector or promotes a candidate.

Calibration contract accepted from root: JSON format 1, cutoff_ms=1640995200000, current spec_sha256, profiles keyed by exact canonical candidate identity. Selected profile requires finite scale in [0,1], effective_from_ms and calibration_end_ms equal cutoff, training_end_day_exclusive='2022-01-01', baseline_candidate='incumbent', and lowercase 64-hex base_bundle_sha256. The full calibration-file hash and selected profile enter output/checkpoint identity. The consumer structurally validates the supplied original bundle digest; Task 3 must independently verify the actual bundle bytes, complete accounts, and training-only derivation. It does not infer training validity from a checksum string. Missing selected profiles fail closed. Production qualification remains NOT_QUALIFIED.

## Final verification commands and results

1. `python -m compileall -q coinquant research tests` — exit 0, no output.
2. `python -m unittest tests.test_alpha_perp -v > /tmp/task1-tests.log 2>&1` — 10 tests, all pass; full output below.
3. At committed HEAD `c2a01d1c7ad09d58001ec2897a5a64d1b8284dd6`: `python -m unittest discover -s tests -v > /tmp/task1-exact-head-tests.log 2>&1` — 356 tests in 4.804s, OK. Full output appended below.
4. `git diff --check` — exit 0, no output.
5. `python -m research.alpha_perp --candidate incumbent --scenario base --limit 3 --prints /tmp/task1-public-prints --restore-prints --out /tmp/task1-alpha-incumbent-3.json > /tmp/task1-alpha-incumbent-3.log 2>&1` — exit 0, restored three public daily print archives; incomplete, audited true.
6. Timed old/new comparison: `PYTHONPATH=. python /tmp/task1-timed-smokes.py > /tmp/task1-timed-smokes.log 2>&1`. That script runs `/tmp/task1-baseline-smoke.py` (original complete_perp restricted to incumbent/base, original variant, same 3 starts and paths, unused empty crowding file) and calls alpha CLI with the same input plus output `/tmp/task1-alpha-timed-incumbent-3.json.gz`. Exact scripts are preserved in `/tmp`; their source is appended below. Exit 0.
7. `PYTHONPATH=. python /tmp/task1-compare.py` — exact equality over all 26 original non-session row fields, plus all session summary fields excluding detailed observations. No synthetic-identity normalization was needed because both used UID12000. Detailed observations intentionally include different research checkpoints and are not asserted identical. Money, trades, all daily rows, costs, funding, path/mdd, funnel and original independent audit match exactly. Equality evidence below.
8. `python -m research.alpha_perp --limit 1 --prints /tmp/task1-public-prints --out /tmp/task1-matrix-1.json.gz > /tmp/task1-matrix-1.log 2>&1` — exit 0; all 20 registered accounts incomplete, no failure, audits pass; 1035 total ledger events. This validates matrix wiring only; the first session is cold-start cash and cannot establish financial merit.
9. `python -m research.alpha_perp --combo fresh-entry,atr-trail,compression-breakout,single-topup --scenario base --limit 3 --risk-calibration /tmp/task1-risk-fixture.json --initial-cny 9900 --start-offset-ms 60000 --prints /tmp/task1-public-prints --out /tmp/task1-combo-diagnostic-3.json.gz > /tmp/task1-combo-diagnostic-3.log 2>&1` — exit 0, incomplete, audited true. Assertions verify all four components, calibration raw-byte SHA, initial9900, shifted start, and scale1 on every pre-cutoff decision. The calibration is an explicitly synthetic CLI fixture bound to the incomplete baseline file, not a trained risk estimate or matched-alpha evidence. Synthetic session tests separately cover post-cutoff scale .5.

## Historical no-op monetary evidence

```json
{
  "equal_fields": [
    "initial_cny",
    "complete",
    "final_usdt",
    "final_cny",
    "cagr",
    "mdd",
    "mdd_close",
    "mdd_envelope_at",
    "mdd_close_at",
    "position",
    "fees",
    "funding",
    "final_mark",
    "known_path",
    "unknown_from",
    "hindsight_bounded",
    "bounded_minutes",
    "funnel",
    "failure",
    "trades",
    "funding_ledger",
    "feature_coverage",
    "execution_unresolved",
    "daily",
    "daily_cny",
    "audit"
  ],
  "differences": [],
  "session_count": 3,
  "trade_count": 2,
  "daily_count": 3,
  "final_usdt": "1406.616202737891506140917905",
  "final_cny": "9785.598518713502741593659983",
  "fees": "5.3324649000",
  "funding": "0",
  "position": "0.966",
  "mdd": "0.0241472855557217370830340017",
  "audit": {
    "passed": true,
    "checks": {
      "trade_quantity_matches_position": true,
      "realized_pnl_matches_cash_ledger": true,
      "fees_match_cash_ledger": true,
      "funding_matches_cash_ledger": true,
      "no_external_cash_flows": true,
      "open_equity_matches_valued_ledger": true
    },
    "wallet_from_ledger_usdt": "1429.703087782611506140917905",
    "position_from_fills_btc": "0.966",
    "entry_from_fills_usdt": "7360.2",
    "income_totals": {
      "COMMISSION": "-5.3324649"
    }
  },
  "complete": false,
  "cagr": null,
  "ledger_rows": 147,
  "ledger_json_bytes": 53208,
  "ledger_loaded_object_bytes": 131889,
  "output_gzip_bytes": 14602,
  "output_json_bytes": 86115,
  "monetary_sha256": "1889de3d0f75ee61fce760087ff4bb8ae32ab2d85b5a67bd147a48bea11606d2",
  "old_sha256": "4b7f1e3948681649525093cd00faf71daaa940d37738993188d623e9fe89fe39",
  "new_sha256": "06f3f100d58df12d440dc57c8e8e092ceffaeb5c732404da3a4e81d0545b495c"
}
```

Timed warm-cache old runner: 0.7465176219993737 seconds, process peak 140520 KiB. Alpha runner: 0.7385847620025743 seconds, process peak 155832 KiB. These are sequential runs in one Python process, so peak RSS is cumulative, not an isolated incremental-memory claim. Alpha journal: 147 events; 53208 serialized JSON bytes; approximately131889 bytes when recursively sizing the independently loaded journal object (shared Python objects counted once). Full output: 86115 decoded/re-serialized JSON bytes, 14602 gzip bytes. Initial public restoration time was not instrumented. No full-history memory extrapolation is claimed.

## Material limits and next gates

No full 795-session run, matched-risk calibration, economic selection, prior full-original baseline comparison, independent source review, exact-head GitHub CI, default replacement, integration, shadow forward initialization, or native qualification was performed in this Task 1 implementation scope. The parent owns those later gates. The source still carries all previous historical mark/minute/volume/FX proxy disclosures; a passing accounting audit does not prove economics or native execution. Actual account days/native cases remain zero.

Full-window baseline equality must still be established against retained original artifacts before candidate promotion. All smokes remain generated under `/tmp`, `complete=false`, `cagr=null`. The largest observed journal here covers only three sessions; full matrix memory/output growth remains unmeasured because the reused meter retains all account/session outputs and the new journals in memory. Calibration structural checks cannot certify training-data provenance; Task 3 must supply that independent proof. Entry-overlap bars are deliberately excluded from trail highs to avoid importing pre-entry highs; independent spec review should confirm this causal interpretation. No economic or repeatable-alpha claim is made.

## Focused test output

```text
test_calibration_binding_rejects_future_mismatch_nonfinite_and_scales_only_new_sizing (tests.test_alpha_perp.AlphaTests.test_calibration_binding_rejects_future_mismatch_nonfinite_and_scales_only_new_sizing) ... ok
test_checkpoint_roundtrip_identity_digest_and_provenance (tests.test_alpha_perp.AlphaTests.test_checkpoint_roundtrip_identity_digest_and_provenance) ... ok
test_compression_uses_prior_high_atr_and_median_with_original_priority (tests.test_alpha_perp.AlphaTests.test_compression_uses_prior_high_atr_and_median_with_original_priority) ... ok
test_fresh_entry_age_chase_boundaries_owned_and_macro_unchanged (tests.test_alpha_perp.AlphaTests.test_fresh_entry_age_chase_boundaries_owned_and_macro_unchanged) ... ok
test_hooks_restore_on_exception (tests.test_alpha_perp.AlphaTests.test_hooks_restore_on_exception) ... ok
test_incumbent_noop_preserves_calls_clock_cash_fills_and_requests (tests.test_alpha_perp.AlphaTests.test_incumbent_noop_preserves_calls_clock_cash_fills_and_requests) ... ok
test_real_lifecycle_trail_tightens_and_through_mark_reduces_without_macro_change (tests.test_alpha_perp.AlphaTests.test_real_lifecycle_trail_tightens_and_through_mark_reduces_without_macro_change) ... ok
test_single_topup_partial_and_unknown_fills_recover_once_and_keep_protection (tests.test_alpha_perp.AlphaTests.test_single_topup_partial_and_unknown_fills_recover_once_and_keep_protection) ... ok
test_trail_bar_state_excludes_entry_bar_and_makes_no_unattended_stop_change (tests.test_alpha_perp.AlphaTests.test_trail_bar_state_excludes_entry_bar_and_makes_no_unattended_stop_change) ... ok
test_unknown_unaccepted_topup_is_not_resent (tests.test_alpha_perp.AlphaTests.test_unknown_unaccepted_topup_is_not_resent) ... ok

----------------------------------------------------------------------
Ran 10 tests in 0.323s

OK
```

## Exact-head complete offline test output

```text
test_contract_identity_and_gates (test_acceptance.AcceptanceTests.test_contract_identity_and_gates) ... ok
test_exact_target_boundaries (test_acceptance.AcceptanceTests.test_exact_target_boundaries) ... ok
test_recorded_default_and_evidence_identity (test_acceptance.AcceptanceTests.test_recorded_default_and_evidence_identity) ... ok
test_recorded_numbers_are_the_ones_in_their_evidence_files (test_acceptance.AcceptanceTests.test_recorded_numbers_are_the_ones_in_their_evidence_files) ... ok
test_calibration_binding_rejects_future_mismatch_nonfinite_and_scales_only_new_sizing (test_alpha_perp.AlphaTests.test_calibration_binding_rejects_future_mismatch_nonfinite_and_scales_only_new_sizing) ... ok
test_checkpoint_roundtrip_identity_digest_and_provenance (test_alpha_perp.AlphaTests.test_checkpoint_roundtrip_identity_digest_and_provenance) ... ok
test_compression_uses_prior_high_atr_and_median_with_original_priority (test_alpha_perp.AlphaTests.test_compression_uses_prior_high_atr_and_median_with_original_priority) ... ok
test_fresh_entry_age_chase_boundaries_owned_and_macro_unchanged (test_alpha_perp.AlphaTests.test_fresh_entry_age_chase_boundaries_owned_and_macro_unchanged) ... ok
test_hooks_restore_on_exception (test_alpha_perp.AlphaTests.test_hooks_restore_on_exception) ... ok
test_incumbent_noop_preserves_calls_clock_cash_fills_and_requests (test_alpha_perp.AlphaTests.test_incumbent_noop_preserves_calls_clock_cash_fills_and_requests) ... ok
test_real_lifecycle_trail_tightens_and_through_mark_reduces_without_macro_change (test_alpha_perp.AlphaTests.test_real_lifecycle_trail_tightens_and_through_mark_reduces_without_macro_change) ... ok
test_single_topup_partial_and_unknown_fills_recover_once_and_keep_protection (test_alpha_perp.AlphaTests.test_single_topup_partial_and_unknown_fills_recover_once_and_keep_protection) ... ok
test_trail_bar_state_excludes_entry_bar_and_makes_no_unattended_stop_change (test_alpha_perp.AlphaTests.test_trail_bar_state_excludes_entry_bar_and_makes_no_unattended_stop_change) ... ok
test_unknown_unaccepted_topup_is_not_resent (test_alpha_perp.AlphaTests.test_unknown_unaccepted_topup_is_not_resent) ... ok
test_explicit_missing_inside_retention_is_terminal_and_stays_terminal (test_audit_20260929.AbsentOrderTests.test_explicit_missing_inside_retention_is_terminal_and_stays_terminal) ... ok
test_missing_before_expiry_or_after_retention_stays_unknown (test_audit_20260929.AbsentOrderTests.test_missing_before_expiry_or_after_retention_stays_unknown) ... ok
test_same_account_in_two_directories_cannot_both_write (test_audit_20260929.AccountLockTests.test_same_account_in_two_directories_cannot_both_write) ... ok
test_close_sends_the_market_cap_then_the_remainder (test_audit_20260929.ExitSliceTests.test_close_sends_the_market_cap_then_the_remainder) ... ok
test_limit_entry_does_not_use_the_market_lot_cap (test_audit_20260929.QuantityRuleTests.test_limit_entry_does_not_use_the_market_lot_cap) ... ok
test_duplicate_client_id_and_triggering_stop_stay_unknown (test_audit_20260929.RejectCodeTests.test_duplicate_client_id_and_triggering_stop_stay_unknown) ... ok
test_lost_send_records_only_the_error_type (test_audit_20260929.RejectCodeTests.test_lost_send_records_only_the_error_type) ... ok
test_plain_parameter_rejection_is_still_terminal (test_audit_20260929.RejectCodeTests.test_plain_parameter_rejection_is_still_terminal) ... ok
test_names_and_output_roots_are_bounded (test_audit_20260929.TrialPathTests.test_names_and_output_roots_are_bounded) ... ok
test_a_fresh_gap_waits_and_an_old_gap_blocks (test_audit_20260929.WalletGapTests.test_a_fresh_gap_waits_and_an_old_gap_blocks) ... ok
test_documented_503_failures_are_terminal_and_other_503s_stay_unknown (tests.test_margin_intents.WriteClassificationTests.test_documented_503_failures_are_terminal_and_other_503s_stay_unknown) ... ok
test_documented_native_rejection_is_terminal (tests.test_margin_intents.WriteClassificationTests.test_documented_native_rejection_is_terminal) ... ok
test_expired_deadline_is_recorded_as_never_sent (tests.test_margin_intents.WriteClassificationTests.test_expired_deadline_is_recorded_as_never_sent) ... ok
test_lost_add_cannot_be_declared_rejected_from_age_and_missing_query (tests.test_margin_intents.WriteClassificationTests.test_lost_add_cannot_be_declared_rejected_from_age_and_missing_query) ... ok
test_margin_rejection_blocks_without_pending (tests.test_margin_intents.WriteClassificationTests.test_margin_rejection_blocks_without_pending) ... ok
test_missing_order_without_a_preparation_time_or_past_retention_stays_unknown (tests.test_margin_intents.WriteClassificationTests.test_missing_order_without_a_preparation_time_or_past_retention_stays_unknown) ... ok
test_numeric_margin_amount_is_parsed_exactly (tests.test_margin_intents.WriteClassificationTests.test_numeric_margin_amount_is_parsed_exactly) ... ok
test_overloaded_add_does_not_block_the_exit_of_the_existing_position (tests.test_margin_intents.WriteClassificationTests.test_overloaded_add_does_not_block_the_exit_of_the_existing_position) ... ok
test_read_rejections_remain_unknown (tests.test_margin_intents.WriteClassificationTests.test_read_rejections_remain_unknown) ... ok
test_unknown_execution_codes_and_server_errors_stay_pending (tests.test_margin_intents.WriteClassificationTests.test_unknown_execution_codes_and_server_errors_stay_pending) ... ok
test_a_live_writer_on_another_machine_blocks_the_next_open (test_audit_20260929.WriterHostTests.test_a_live_writer_on_another_machine_blocks_the_next_open) ... ok
test_execute_needs_trial_and_uid_before_credentials (test_audit_fixes.CliSmoke.test_execute_needs_trial_and_uid_before_credentials) ... blocked: write trial requires --trial and --authorize-uid
ok
test_run_defaults_to_observation_and_sends_no_write (test_audit_fixes.CliSmoke.test_run_defaults_to_observation_and_sends_no_write) ... read_only: 
ok
test_trial_options_without_execute_are_refused (test_audit_fixes.CliSmoke.test_trial_options_without_execute_are_refused) ... blocked: trial options require --execute
ok
test_cleanup_budget_never_passes_the_hard_deadline (test_audit_fixes.ExitPaths.test_cleanup_budget_never_passes_the_hard_deadline) ... ok
test_deadline_with_pending_intent_is_execution_unresolved (test_audit_fixes.ExitPaths.test_deadline_with_pending_intent_is_execution_unresolved) ... ok
test_interrupt_and_clock_failure_are_reported_with_phase (test_audit_fixes.ExitPaths.test_interrupt_and_clock_failure_are_reported_with_phase) ... ok
test_verified_session_is_not_unresolved (test_audit_fixes.ExitPaths.test_verified_session_is_not_unresolved) ... ok
test_entry_reply_lost_after_fill_is_found_by_identity_and_protected (test_audit_fixes.FirstFillToProtection.test_entry_reply_lost_after_fill_is_found_by_identity_and_protected) ... ok
test_stop_accepted_take_rejected_never_leaves_a_one_leg_position (test_audit_fixes.FirstFillToProtection.test_stop_accepted_take_rejected_never_leaves_a_one_leg_position) ... ok
test_unknown_margin_transfer_is_not_resent_and_position_stays_protected (test_audit_fixes.FirstFillToProtection.test_unknown_margin_transfer_is_not_resent_and_position_stays_protected) ... ok
test_audit_failure_does_not_stop_signal_exit (test_audit_fixes.FundsAuditGate.test_audit_failure_does_not_stop_signal_exit) ... ok
test_cache_is_bound_to_the_wallet_value_and_wallet_less_reads_do_not_settle (test_audit_fixes.FundsAuditGate.test_cache_is_bound_to_the_wallet_value_and_wallet_less_reads_do_not_settle) ... ok
test_final_income_audit_failure_is_reported_not_success (test_audit_fixes.FundsAuditGate.test_final_income_audit_failure_is_reported_not_success) ... ok
test_gap_that_income_never_explains_becomes_unexplained (test_audit_fixes.FundsAuditGate.test_gap_that_income_never_explains_becomes_unexplained) ... ok
test_unexplained_wallet_stops_top_up_but_keeps_protection (test_audit_fixes.FundsAuditGate.test_unexplained_wallet_stops_top_up_but_keeps_protection) ... ok
test_wallet_drop_without_income_never_opens_risk_and_late_income_clears_it (test_audit_fixes.FundsAuditGate.test_wallet_drop_without_income_never_opens_risk_and_late_income_clears_it) ... ok
test_outage_does_not_touch_a_primary_position_or_its_protection (test_audit_fixes.MacroFailurePolicy.test_outage_does_not_touch_a_primary_position_or_its_protection) ... ok
test_outage_on_a_flat_account_stops_new_risk_without_hiding_the_reason (test_audit_fixes.MacroFailurePolicy.test_outage_on_a_flat_account_stops_new_risk_without_hiding_the_reason) ... ok
test_sub_unit_residue_is_arithmetic_but_one_native_unit_is_a_gap (test_audit_fixes.NativePrecision.test_sub_unit_residue_is_arithmetic_but_one_native_unit_is_a_gap) ... ok
test_a_healthy_native_leg_keeps_the_block_without_reducing (test_audit_fixes.ReplacementFallback.test_a_healthy_native_leg_keeps_the_block_without_reducing) ... ok
test_unprotected_position_with_a_failing_replacement_is_reduced_not_left_open (test_audit_fixes.ReplacementFallback.test_unprotected_position_with_a_failing_replacement_is_reduced_not_left_open) ... ok
test_documented_rejection_is_terminal_and_transport_loss_is_not (test_audit_fixes.RestErrors.test_documented_rejection_is_terminal_and_transport_loss_is_not) ... ok
test_rate_limits_and_server_errors_stay_unknown_with_native_evidence (test_audit_fixes.RestErrors.test_rate_limits_and_server_errors_stay_unknown_with_native_evidence) ... ok
test_unknown_status_is_recorded_on_the_intent_and_never_terminal (test_audit_fixes.RestErrors.test_unknown_status_is_recorded_on_the_intent_and_never_terminal) ... ok
test_first_signal_interrupts_later_ones_are_ignored_and_handlers_restore (test_audit_fixes.Signals.test_first_signal_interrupts_later_ones_are_ignored_and_handlers_restore) ... ok
test_interrupt_before_the_session_is_an_explicit_unknown_report (test_audit_fixes.Signals.test_interrupt_before_the_session_is_an_explicit_unknown_report) ... unknown: Interrupted before or outside the bounded session; reconcile before any new action
ok
test_entry_records_its_sizing_capital_and_top_up_reports_current_capital (test_audit_fixes.SmallFundBoundaries.test_entry_records_its_sizing_capital_and_top_up_reports_current_capital) ... ok
test_lowered_capital_never_grows_the_position_back_to_the_old_target (test_audit_fixes.SmallFundBoundaries.test_lowered_capital_never_grows_the_position_back_to_the_old_target) ... ok
test_session_reports_exchange_leverage_apart_from_account_notional (test_audit_fixes.SmallFundBoundaries.test_session_reports_exchange_leverage_apart_from_account_notional) ... ok
test_failed_time_read_sends_no_signed_request (test_audit_fixes.StatusClock.test_failed_time_read_sends_no_signed_request) ... ok
test_main_reports_the_failure_and_exits_nonzero (test_audit_fixes.StatusClock.test_main_reports_the_failure_and_exits_nonzero) ... unknown: Binance server time unavailable; clock not aligned
ok
test_status_aligns_the_clock_before_the_first_signed_read (test_audit_fixes.StatusClock.test_status_aligns_the_clock_before_the_first_signed_read) ... ok
test_execution_blocked_before_credentials_or_network (test_binance_cli.BinanceCLI.test_execution_blocked_before_credentials_or_network) ... ok
test_incomplete_replacement_is_visible_without_pending_order (test_binance_cli.BinanceCLI.test_incomplete_replacement_is_visible_without_pending_order) ... ok
test_missing_named_credentials_blocks_before_network (test_binance_cli.BinanceCLI.test_missing_named_credentials_blocks_before_network) ... ok
test_observation_saves_bound_account_report_without_decision (test_binance_cli.BinanceCLI.test_observation_saves_bound_account_report_without_decision) ... ok
test_pending_recovery_refreshes_account_and_keeps_unknown_blocked (test_binance_cli.BinanceCLI.test_pending_recovery_refreshes_account_and_keeps_unknown_blocked) ... ok
test_unknown_configuration_fields_are_rejected (test_binance_cli.BinanceCLI.test_unknown_configuration_fields_are_rejected) ... ok
test_canceled_parent_still_queries_partially_filled_child (test_binance_intent_read.IntentRead.test_canceled_parent_still_queries_partially_filled_child) ... ok
test_missing_history_never_becomes_retry_permission (test_binance_intent_read.IntentRead.test_missing_history_never_becomes_retry_permission) ... ok
test_checkpoint_pages_without_truncation (test_binance_market.NativeMarket.test_checkpoint_pages_without_truncation) ... ok
test_completed_boundary_and_missing_or_forming_candle (test_binance_market.NativeMarket.test_completed_boundary_and_missing_or_forming_candle) ... ok
test_common_increment_and_incomplete_filters (test_binance_quantity.QuantityTests.test_common_increment_and_incomplete_filters) ... ok
test_preserves_risk_budget_and_applies_minimum_and_market_cap (test_binance_quantity.QuantityTests.test_preserves_risk_budget_and_applies_minimum_and_market_cap) ... ok
test_bounded_snapshot_does_not_turn_racing_wallet_into_stable_state (test_binance_readonly.BinanceReadTests.test_bounded_snapshot_does_not_turn_racing_wallet_into_stable_state) ... ok
test_missing_or_wrong_account_mode_blocks (test_binance_readonly.BinanceReadTests.test_missing_or_wrong_account_mode_blocks) ... ok
test_out_of_scope_request_and_redirect_blocked (test_binance_readonly.BinanceReadTests.test_out_of_scope_request_and_redirect_blocked) ... ok
test_public_get_never_sends_key_or_signature (test_binance_readonly.BinanceReadTests.test_public_get_never_sends_key_or_signature) ... ok
test_signs_exact_query_and_returns_only_uid (test_binance_readonly.BinanceReadTests.test_signs_exact_query_and_returns_only_uid) ... ok
test_unavailable_is_unknown_and_error_does_not_leak_secrets (test_binance_readonly.BinanceReadTests.test_unavailable_is_unknown_and_error_does_not_leak_secrets) ... ok
test_usdt_equity_full_protection_and_remainder_are_distinct (test_binance_readonly.BinanceReadTests.test_usdt_equity_full_protection_and_remainder_are_distinct) ... ok
test_canceled_parent_cannot_hide_working_child (test_binance_recovery.RecoveryTests.test_canceled_parent_cannot_hide_working_child) ... ok
test_late_missing_order_stays_unknown_then_original_fill_recovers (test_binance_recovery.RecoveryTests.test_late_missing_order_stays_unknown_then_original_fill_recovers) ... ok
test_old_false_rejection_reopens_without_resending_or_claiming_external_fill (test_binance_recovery.RecoveryTests.test_old_false_rejection_reopens_without_resending_or_claiming_external_fill) ... ok
test_payload_mismatch_and_unknown_intent_kind_stay_unknown (test_binance_recovery.RecoveryTests.test_payload_mismatch_and_unknown_intent_kind_stay_unknown) ... ok
test_readonly_recovers_algo_cancel_only_after_child_terminal (test_binance_recovery.RecoveryTests.test_readonly_recovers_algo_cancel_only_after_child_terminal) ... ok
test_terminal_partial_fill_and_unknown_are_independent (test_binance_recovery.RecoveryTests.test_terminal_partial_fill_and_unknown_are_independent) ... ok
test_child_still_working_stays_unknown (test_binance_replace.PartialFillReplacementTests.test_child_still_working_stays_unknown) ... ok
test_flat_after_partial_fill_cleans_up_without_reopening (test_binance_replace.PartialFillReplacementTests.test_flat_after_partial_fill_cleans_up_without_reopening) ... ok
test_old_leg_filled_keeps_healthy_new_pair_and_finishes (test_binance_replace.PartialFillReplacementTests.test_old_leg_filled_keeps_healthy_new_pair_and_finishes) ... ok
test_spent_new_leg_rotates_to_fresh_generation_without_reusing_spent_id (test_binance_replace.PartialFillReplacementTests.test_spent_new_leg_rotates_to_fresh_generation_without_reusing_spent_id) ... ok
test_unexplained_or_oversized_change_stays_unknown (test_binance_replace.PartialFillReplacementTests.test_unexplained_or_oversized_change_stays_unknown) ... ok
test_authorized_reduce_remains_available_with_unknown_owned_cancel (test_binance_replace.ReplacementTests.test_authorized_reduce_remains_available_with_unknown_owned_cancel) ... ok
test_cancel_timeout_after_acceptance_settles_by_query (test_binance_replace.ReplacementTests.test_cancel_timeout_after_acceptance_settles_by_query) ... ok
test_canceled_parent_working_child_blocks (test_binance_replace.ReplacementTests.test_canceled_parent_working_child_blocks) ... ok
test_changed_replacement_request_cannot_bypass_pending_operation (test_binance_replace.ReplacementTests.test_changed_replacement_request_cannot_bypass_pending_operation) ... ok
test_flat_after_cancel_cleanup_does_not_reopen (test_binance_replace.ReplacementTests.test_flat_after_cancel_cleanup_does_not_reopen) ... ok
test_lost_ownership_blocks_without_writes (test_binance_replace.ReplacementTests.test_lost_ownership_blocks_without_writes) ... ok
test_new_pair_before_old_cancel_and_restart_no_writes (test_binance_replace.ReplacementTests.test_new_pair_before_old_cancel_and_restart_no_writes) ... ok
test_new_rejection_retains_old_and_never_retries (test_binance_replace.ReplacementTests.test_new_rejection_retains_old_and_never_retries) ... ok
test_partial_exposure_restart_keeps_existing_protections (test_binance_replace.ReplacementTests.test_partial_exposure_restart_keeps_existing_protections) ... ok
test_price_already_through_new_stop_keeps_old_protection (test_binance_replace.ReplacementTests.test_price_already_through_new_stop_keeps_old_protection) ... ok
test_replacement_default_read_only (test_binance_replace.ReplacementTests.test_replacement_default_read_only) ... ok
test_restart_resumes_accepted_cancel_without_resend (test_binance_replace.ReplacementTests.test_restart_resumes_accepted_cancel_without_resend) ... ok
test_short_replacement_uses_buy_close_all_without_quantity (test_binance_replace.ReplacementTests.test_short_replacement_uses_buy_close_all_without_quantity) ... ok
test_unknown_cancel_is_not_repeated (test_binance_replace.ReplacementTests.test_unknown_cancel_is_not_repeated) ... ok
test_cancel_fill_race_returns_real_exposure (test_binance_safety.SafetyTests.test_cancel_fill_race_returns_real_exposure) ... ok
test_default_does_not_write (test_binance_safety.SafetyTests.test_default_does_not_write) ... ok
test_model_margin_target_readback (test_binance_safety.SafetyTests.test_model_margin_target_readback) ... ok
test_new_entry_remainder_between_legs_stops_writes (test_binance_safety.SafetyTests.test_new_entry_remainder_between_legs_stops_writes) ... ok
test_no_open_order_is_not_proof_unknown_entry_cannot_arrive (test_binance_safety.SafetyTests.test_no_open_order_is_not_proof_unknown_entry_cannot_arrive) ... ok
test_partial_exposure_close_all_and_idempotent_recovery (test_binance_safety.SafetyTests.test_partial_exposure_close_all_and_idempotent_recovery) ... ok
test_reduce_only_below_entry_min_notional_can_close (test_binance_safety.SafetyTests.test_reduce_only_below_entry_min_notional_can_close) ... ok
test_reduce_only_never_reverses (test_binance_safety.SafetyTests.test_reduce_only_never_reverses) ... ok
test_remainder_blocks_protection (test_binance_safety.SafetyTests.test_remainder_blocks_protection) ... ok
test_stop_fill_between_legs_prevents_stale_take_write (test_binance_safety.SafetyTests.test_stop_fill_between_legs_prevents_stale_take_write) ... ok
test_timeout_after_acceptance_is_queried (test_binance_safety.SafetyTests.test_timeout_after_acceptance_is_queried) ... ok
test_unknown_margin_blocks_different_epoch (test_binance_safety.SafetyTests.test_unknown_margin_blocks_different_epoch) ... ok
test_unknown_missing_never_retries (test_binance_safety.SafetyTests.test_unknown_missing_never_retries) ... ok
test_candle_weight_tracks_page_size_and_reserves_before_request (test_binance_writer.WriterTests.test_candle_weight_tracks_page_size_and_reserves_before_request) ... ok
test_default_read_only_and_unbounded_entries_rejected_before_network (test_binance_writer.WriterTests.test_default_read_only_and_unbounded_entries_rejected_before_network) ... ok
test_rate_limit_cooldown_prevents_poll_storm (test_binance_writer.WriterTests.test_rate_limit_cooldown_prevents_poll_storm) ... ok
test_signed_order_is_sent_once_without_account_setting_capability (test_binance_writer.WriterTests.test_signed_order_is_sent_once_without_account_setting_capability) ... ok
test_transport_timeout_is_unknown_and_never_retried (test_binance_writer.WriterTests.test_transport_timeout_is_unknown_and_never_retried) ... ok
test_checkpoint_of_another_version_blocks (test_campaign.CampaignTests.test_checkpoint_of_another_version_blocks) ... ok
test_consumption_and_unknown_position (test_campaign.CampaignTests.test_consumption_and_unknown_position) ... ok
test_every_prefix_survives_serialized_restart (test_campaign.CampaignTests.test_every_prefix_survives_serialized_restart) ... ok
test_interrupted_bootstrap_resumes_only_verified_page (test_campaign.CampaignTests.test_interrupted_bootstrap_resumes_only_verified_page) ... ok
test_macro_cold_start_does_not_infer_old_unseen_campaign (test_campaign.CampaignTests.test_macro_cold_start_does_not_infer_old_unseen_campaign) ... ok
test_missing_history_and_corrupt_checkpoint_block (test_campaign.CampaignTests.test_missing_history_and_corrupt_checkpoint_block) ... ok
test_promoted_macro_priority_consumption_and_restart (test_campaign.CampaignTests.test_promoted_macro_priority_consumption_and_restart) ... ok
test_read_only_resume_and_unknown_ownership (test_campaign.CampaignTests.test_read_only_resume_and_unknown_ownership) ... ok
test_closed_account_matches_fills_costs_and_full_cash_ledger (test_comparison_report.AccountAuditTests.test_closed_account_matches_fills_costs_and_full_cash_ledger) ... ok
test_missing_fill_wrong_wallet_and_external_flow_invalidate_account (test_comparison_report.AccountAuditTests.test_missing_fill_wrong_wallet_and_external_flow_invalidate_account) ... ok
test_budget_initial_peak_includes_only_conversion_cost (test_complete_perp.CompletePerpTests.test_budget_initial_peak_includes_only_conversion_cost) ... ok
test_checkpoint_daily_state_and_candidate_identity (test_complete_perp.CompletePerpTests.test_checkpoint_daily_state_and_candidate_identity) ... ok
test_conditional_short_requires_decline_and_one_way_ownership (test_complete_perp.CompletePerpTests.test_conditional_short_requires_decline_and_one_way_ownership) ... ok
test_features_ignore_future_and_expire (test_complete_perp.CompletePerpTests.test_features_ignore_future_and_expire) ... ok
test_filters_only_block_new_longs_not_hold_or_reduction (test_complete_perp.CompletePerpTests.test_filters_only_block_new_longs_not_hold_or_reduction) ... ok
test_initial_fx_precedes_metric_and_daily_boundary_uses_boundary_fx (test_complete_perp.CompletePerpTests.test_initial_fx_precedes_metric_and_daily_boundary_uses_boundary_fx) ... ok
test_public_restore_includes_september_funding_without_price_extension (test_complete_perp.CompletePerpTests.test_public_restore_includes_september_funding_without_price_extension) ... ok
test_research_terminal_excludes_only_end_funding_and_never_executes (test_complete_perp.CompletePerpTests.test_research_terminal_excludes_only_end_funding_and_never_executes) ... ok
test_slow_trend_primary_priority_owned_stop_and_break (test_complete_perp.CompletePerpTests.test_slow_trend_primary_priority_owned_stop_and_break) ... ok
test_tail_recent_shock_reduces_fraction_without_other_knobs (test_complete_perp.CompletePerpTests.test_tail_recent_shock_reduces_fraction_without_other_knobs) ... ok
test_terminal_derivation_preserves_history_and_reconstructs_cash (test_complete_perp.CompletePerpTests.test_terminal_derivation_preserves_history_and_reconstructs_cash) ... ok
test_official_sparse_vintages_are_reconstructed_only_as_of_call (test_dfii10.DFII10Tests.test_official_sparse_vintages_are_reconstructed_only_as_of_call) ... ok
test_raw_response_is_stored_atomically_verified_and_repaired (test_dfii10.RawStoreTests.test_raw_response_is_stored_atomically_verified_and_repaired) ... ok
test_changed_columns_or_non_zip_answers_are_unknown_not_a_stale_value (test_dfii10.SourceFailureTests.test_changed_columns_or_non_zip_answers_are_unknown_not_a_stale_value) ... ok
test_failure_defers_retries_and_success_is_reused_for_fifteen_minutes (test_dfii10.SourceFailureTests.test_failure_defers_retries_and_success_is_reused_for_fifteen_minutes) ... ok
test_capital_limit_must_be_a_positive_decimal_string (test_environment.EnvironmentTests.test_capital_limit_must_be_a_positive_decimal_string) ... ok
test_controlled_demo_writes_use_the_same_session_and_adapter (test_environment.EnvironmentTests.test_controlled_demo_writes_use_the_same_session_and_adapter) ... ok
test_demo_execute_without_trial_flags_stays_blocked_before_credentials (test_environment.EnvironmentTests.test_demo_execute_without_trial_flags_stays_blocked_before_credentials) ... ok
test_demo_reads_only_demo_hosts (test_environment.EnvironmentTests.test_demo_reads_only_demo_hosts) ... ok
test_demo_uses_its_own_credentials_and_state_scope (test_environment.EnvironmentTests.test_demo_uses_its_own_credentials_and_state_scope) ... ok
test_live_state_directory_refuses_a_demo_configuration (test_environment.EnvironmentTests.test_live_state_directory_refuses_a_demo_configuration) ... ok
test_live_trial_needs_reviewed_matching_demo_evidence (test_environment.EnvironmentTests.test_live_trial_needs_reviewed_matching_demo_evidence) ... ok
test_session_refuses_an_adapter_for_another_environment_or_limit (test_environment.EnvironmentTests.test_session_refuses_an_adapter_for_another_environment_or_limit) ... ok
test_an_absent_add_is_retired_only_while_the_position_is_unchanged (test_full_review.AbsentOrderRetirement.test_an_absent_add_is_retired_only_while_the_position_is_unchanged) ... ok
test_an_absent_entry_needs_a_flat_account (test_full_review.AbsentOrderRetirement.test_an_absent_entry_needs_a_flat_account) ... ok
test_an_absent_reduction_is_retired_even_with_a_position_and_never_reduces_more (test_full_review.AbsentOrderRetirement.test_an_absent_reduction_is_retired_even_with_a_position_and_never_reduces_more) ... ok
test_a_write_without_time_to_read_the_answer_is_never_sent (test_full_review.AdapterEdges.test_a_write_without_time_to_read_the_answer_is_never_sent) ... ok
test_algo_cancel_reply_with_string_code_200_is_accepted (test_full_review.AdapterEdges.test_algo_cancel_reply_with_string_code_200_is_accepted) ... ok
test_order_cancel_and_reduction_shapes_are_restricted_to_owned_market_reductions (test_full_review.AdapterEdges.test_order_cancel_and_reduction_shapes_are_restricted_to_owned_market_reductions) ... ok
test_slow_time_sample_does_not_set_the_offset_and_rate_limit_cools_down (test_full_review.AdapterEdges.test_slow_time_sample_does_not_set_the_offset_and_rate_limit_cools_down) ... ok
test_truncated_or_malformed_http_is_unknown_never_a_raw_exception (test_full_review.AdapterEdges.test_truncated_or_malformed_http_is_unknown_never_a_raw_exception) ... ok
test_failed_clock_sample_at_cleanup_does_not_skip_verification (test_full_review.CleanupBudgets.test_failed_clock_sample_at_cleanup_does_not_skip_verification) ... ok
test_recovery_fallback_reductions_reserve_their_own_observation_budget (test_full_review.CleanupBudgets.test_recovery_fallback_reductions_reserve_their_own_observation_budget) ... ok
test_signal_landing_inside_the_final_cleanup_is_retried_once (test_full_review.CleanupBudgets.test_signal_landing_inside_the_final_cleanup_is_retried_once) ... ok
test_relative_state_directory_is_refused (test_full_review.ConfigPath.test_relative_state_directory_is_refused) ... ok
test_interrupted_cold_start_still_consumes_the_macro_state (test_macro_input.MacroInputTests.test_interrupted_cold_start_still_consumes_the_macro_state) ... ok
test_macro_position_keeps_protection_without_dfii10 (test_macro_input.MacroInputTests.test_macro_position_keeps_protection_without_dfii10) ... ok
test_primary_exit_does_not_wait_for_dfii10 (test_macro_input.MacroInputTests.test_primary_exit_does_not_wait_for_dfii10) ... ok
test_missing_time_zone_data_fails_with_an_actionable_error (test_macro_input.SourceBudgetTests.test_missing_time_zone_data_fails_with_an_actionable_error) ... ok
test_reads_share_the_budget_and_failures_are_not_repeated_each_poll (test_macro_input.SourceBudgetTests.test_reads_share_the_budget_and_failures_are_not_repeated_each_poll) ... ok
test_a_distant_earlier_transfer_does_not_make_history_ambiguous (test_margin_intents.MarginIntentTests.test_a_distant_earlier_transfer_does_not_make_history_ambiguous) ... ok
test_a_margin_row_without_preparation_time_is_bounded_by_its_last_update (test_margin_intents.MarginIntentTests.test_a_margin_row_without_preparation_time_is_bounded_by_its_last_update) ... ok
test_absent_history_never_proves_the_transfer_failed (test_margin_intents.MarginIntentTests.test_absent_history_never_proves_the_transfer_failed) ... ok
test_acknowledged_transfer_survives_a_failed_readback (test_margin_intents.MarginIntentTests.test_acknowledged_transfer_survives_a_failed_readback) ... ok
test_ambiguous_history_stays_unknown (test_margin_intents.MarginIntentTests.test_ambiguous_history_stays_unknown) ... ok
test_amount_is_rounded_up_to_native_settlement_precision (test_margin_intents.MarginIntentTests.test_amount_is_rounded_up_to_native_settlement_precision) ... ok
test_an_earlier_equal_add_is_never_attributed_to_a_lost_one (test_margin_intents.MarginIntentTests.test_an_earlier_equal_add_is_never_attributed_to_a_lost_one) ... ok
test_lost_answer_is_settled_from_margin_history_only (test_margin_intents.MarginIntentTests.test_lost_answer_is_settled_from_margin_history_only) ... ok
test_documented_503_failures_are_terminal_and_other_503s_stay_unknown (test_margin_intents.WriteClassificationTests.test_documented_503_failures_are_terminal_and_other_503s_stay_unknown) ... ok
test_documented_native_rejection_is_terminal (test_margin_intents.WriteClassificationTests.test_documented_native_rejection_is_terminal) ... ok
test_expired_deadline_is_recorded_as_never_sent (test_margin_intents.WriteClassificationTests.test_expired_deadline_is_recorded_as_never_sent) ... ok
test_lost_add_cannot_be_declared_rejected_from_age_and_missing_query (test_margin_intents.WriteClassificationTests.test_lost_add_cannot_be_declared_rejected_from_age_and_missing_query) ... ok
test_margin_rejection_blocks_without_pending (test_margin_intents.WriteClassificationTests.test_margin_rejection_blocks_without_pending) ... ok
test_missing_order_without_a_preparation_time_or_past_retention_stays_unknown (test_margin_intents.WriteClassificationTests.test_missing_order_without_a_preparation_time_or_past_retention_stays_unknown) ... ok
test_numeric_margin_amount_is_parsed_exactly (test_margin_intents.WriteClassificationTests.test_numeric_margin_amount_is_parsed_exactly) ... ok
test_overloaded_add_does_not_block_the_exit_of_the_existing_position (test_margin_intents.WriteClassificationTests.test_overloaded_add_does_not_block_the_exit_of_the_existing_position) ... ok
test_read_rejections_remain_unknown (test_margin_intents.WriteClassificationTests.test_read_rejections_remain_unknown) ... ok
test_unknown_execution_codes_and_server_errors_stay_pending (test_margin_intents.WriteClassificationTests.test_unknown_execution_codes_and_server_errors_stay_pending) ... ok
test_flat_cash_drawdown_between_session_starts_is_recorded (test_meter_review.FlatValuationTests.test_flat_cash_drawdown_between_session_starts_is_recorded) ... ok
test_hold_across_a_missing_rate_loses_the_known_path (test_meter_review.FundingCoverageTests.test_hold_across_a_missing_rate_loses_the_known_path) ... ok
test_uncovered_settlement_time_is_a_gap_anywhere (test_meter_review.FundingCoverageTests.test_uncovered_settlement_time_is_a_gap_anywhere) ... ok
test_position_held_through_the_boundary_pays_it (test_meter_review.FundingOrderTests.test_position_held_through_the_boundary_pays_it) ... ok
test_stop_inside_the_minute_is_not_charged_the_boundary_settlement (test_meter_review.FundingOrderTests.test_stop_inside_the_minute_is_not_charged_the_boundary_settlement) ... ok
test_complete_run_writes_the_official_name (test_meter_review.TrialHygieneTests.test_complete_run_writes_the_official_name) ... ok
test_partial_run_never_writes_the_official_name (test_meter_review.TrialHygieneTests.test_partial_run_never_writes_the_official_name) ... ok
test_research_knobs_are_restored (test_meter_review.TrialHygieneTests.test_research_knobs_are_restored) ... ok
test_capital_limit_sizes_from_the_trial_capital_only (test_native_preview.NativePreviewTests.test_capital_limit_sizes_from_the_trial_capital_only) ... ok
test_liquidation_uses_supplied_closing_fee (test_native_preview.NativePreviewTests.test_liquidation_uses_supplied_closing_fee) ... ok
test_macro_parent_quantity_respects_three_percent_stop_budget (test_native_preview.NativePreviewTests.test_macro_parent_quantity_respects_three_percent_stop_budget) ... ok
test_native_inputs_use_identical_funding_function_without_consumption (test_native_preview.NativePreviewTests.test_native_inputs_use_identical_funding_function_without_consumption) ... ok
test_top_up_keeps_whole_position_inside_the_stop_budget (test_native_preview.NativePreviewTests.test_top_up_keeps_whole_position_inside_the_stop_budget) ... ok
test_unknown_collateral_book_or_account_blocks (test_native_preview.NativePreviewTests.test_unknown_collateral_book_or_account_blocks) ... ok
test_downward_impulse_is_symmetric (test_opportunities.OpportunityTests.test_downward_impulse_is_symmetric) ... ok
test_impulse_uses_prior_volatility_and_midpoint_stop (test_opportunities.OpportunityTests.test_impulse_uses_prior_volatility_and_midpoint_stop) ... ok
test_missing_bar_fails_closed (test_opportunities.OpportunityTests.test_missing_bar_fails_closed) ... ok
test_prefix_cannot_depend_on_future_or_rewrite_objects (test_opportunities.OpportunityTests.test_prefix_cannot_depend_on_future_or_rewrite_objects) ... ok
test_stop_and_expiry_retire_the_campaign (test_opportunities.OpportunityTests.test_stop_and_expiry_retire_the_campaign) ... ok
test_definitive_absence_reconciles_flat_but_legacy_absence_does_not (test_ownership.AbsentEntryOwnership.test_definitive_absence_reconciles_flat_but_legacy_absence_does_not) ... ok
test_late_fill_after_definitive_absence_fails_closed (test_ownership.AbsentEntryOwnership.test_late_fill_after_definitive_absence_fails_closed) ... ok
test_cumulative_fill_cannot_regress (test_ownership.OwnershipTests.test_cumulative_fill_cannot_regress) ... ok
test_external_fill_or_position_mismatch_never_guesses_owner (test_ownership.OwnershipTests.test_external_fill_or_position_mismatch_never_guesses_owner) ... ok
test_history_older_than_three_months_is_not_inferred (test_ownership.OwnershipTests.test_history_older_than_three_months_is_not_inferred) ... ok
test_late_partial_fill_binds_once_and_exposes_unprotected_remainder (test_ownership.OwnershipTests.test_late_partial_fill_binds_once_and_exposes_unprotected_remainder) ... ok
test_lost_journal_cannot_assign_an_existing_position (test_ownership.OwnershipTests.test_lost_journal_cannot_assign_an_existing_position) ... ok
test_protective_fill_preserves_consumption_after_flat_recovery (test_ownership.OwnershipTests.test_protective_fill_preserves_consumption_after_flat_recovery) ... ok
test_rejected_reduction_has_no_native_order_to_query (test_ownership.OwnershipTests.test_rejected_reduction_has_no_native_order_to_query) ... ok
test_mismatched_source_input_and_undeclared_risk_are_rejected (test_path_analysis.PathAnalysisTests.test_mismatched_source_input_and_undeclared_risk_are_rejected) ... ok
test_more_fees_cannot_improve_the_fixed_fill_attribution (test_path_analysis.PathAnalysisTests.test_more_fees_cannot_improve_the_fixed_fill_attribution) ... ok
test_archive_does_not_hide_unobserved_retention_gap (test_pr43.HistoryArchiveTests.test_archive_does_not_hide_unobserved_retention_gap) ... ok
test_changed_archived_fill_blocks_and_keeps_prior_coverage (test_pr43.HistoryArchiveTests.test_changed_archived_fill_blocks_and_keeps_prior_coverage) ... ok
test_nonadvancing_id_page_is_not_accepted_as_complete (test_pr43.HistoryArchiveTests.test_nonadvancing_id_page_is_not_accepted_as_complete) ... ok
test_truncated_id_history_cannot_hide_full_time_page (test_pr43.HistoryArchiveTests.test_truncated_id_history_cannot_hide_full_time_page) ... ok
test_verified_archive_recovers_old_entry_without_expired_native_order (test_pr43.HistoryArchiveTests.test_verified_archive_recovers_old_entry_without_expired_native_order) ... ok
test_income_pagination_and_duplicate_page_fail_closed (test_pr43.IncomeAuditTests.test_income_pagination_and_duplicate_page_fail_closed) ... ok
test_missing_income_coverage_is_not_filled_with_zero_cashflows (test_pr43.IncomeAuditTests.test_missing_income_coverage_is_not_filled_with_zero_cashflows) ... ok
test_native_signed_funding_fees_and_same_id_types_are_retained (test_pr43.IncomeAuditTests.test_native_signed_funding_fees_and_same_id_types_are_retained) ... ok
test_cashflow_audit_outage_blocks_entry_but_not_verified_exit (test_pr43.ReviewRegressions.test_cashflow_audit_outage_blocks_entry_but_not_verified_exit) ... ok
test_changed_owned_protection_does_not_pass_aggregate_geometry (test_pr43.ReviewRegressions.test_changed_owned_protection_does_not_pass_aggregate_geometry) ... ok
test_disconnect_during_final_wait_clears_previous_observation (test_pr43.ReviewRegressions.test_disconnect_during_final_wait_clears_previous_observation) ... ok
test_external_protection_cannot_make_cleanup_verified (test_pr43.ReviewRegressions.test_external_protection_cannot_make_cleanup_verified) ... ok
test_full_recent_window_is_a_cursor_not_complete_history (test_pr43.ReviewRegressions.test_full_recent_window_is_a_cursor_not_complete_history) ... ok
test_more_than_1000_same_millisecond_fills_reconcile_and_protect (test_pr43.ReviewRegressions.test_more_than_1000_same_millisecond_fills_reconcile_and_protect) ... ok
test_restart_finishes_interrupted_owned_protection_replacement (test_pr43.ReviewRegressions.test_restart_finishes_interrupted_owned_protection_replacement) ... ok
test_unknown_observations_are_retained_without_stale_equity (test_pr43.ReviewRegressions.test_unknown_observations_are_retained_without_stale_equity) ... ok
test_external_close_and_equal_manual_reopen_is_never_touched (test_reaudit.ReauditTests.test_external_close_and_equal_manual_reopen_is_never_touched) ... ok
test_external_reopen_is_not_adopted_on_the_trade_id_proof (test_reaudit.ReauditTests.test_external_reopen_is_not_adopted_on_the_trade_id_proof) ... ok
test_failed_protection_never_reduces_a_manual_fill_that_arrived_between_legs (test_reaudit.ReauditTests.test_failed_protection_never_reduces_a_manual_fill_that_arrived_between_legs) ... ok
test_fill_proof_after_a_week_without_trades_uses_the_flat_time_boundary (test_reaudit.ReauditTests.test_fill_proof_after_a_week_without_trades_uses_the_flat_time_boundary) ... ok
test_manual_position_after_restart_is_not_adopted_during_a_history_outage (test_reaudit.ReauditTests.test_manual_position_after_restart_is_not_adopted_during_a_history_outage) ... ok
test_owned_fill_is_protected_or_reduced_within_the_reserved_budget_under_latency (test_reaudit.ReauditTests.test_owned_fill_is_protected_or_reduced_within_the_reserved_budget_under_latency) ... ok
test_unknown_protection_does_not_block_a_later_safe_reduction (test_reaudit.ReauditTests.test_unknown_protection_does_not_block_a_later_safe_reduction) ... ok
test_interrupted_publication_leaves_no_partial_result_named_current (test_rebuild_safety.EvidenceProtection.test_interrupted_publication_leaves_no_partial_result_named_current) ... ok
test_partial_results_never_enter_the_evidence_directory (test_rebuild_safety.EvidenceProtection.test_partial_results_never_enter_the_evidence_directory) ... ok
test_refusal_happens_before_the_meter_runs (test_rebuild_safety.EvidenceProtection.test_refusal_happens_before_the_meter_runs) ... ok
test_same_name_needs_explicit_overwrite_and_keeps_the_original (test_rebuild_safety.EvidenceProtection.test_same_name_needs_explicit_overwrite_and_keeps_the_original) ... ok
test_unresolved_count_uses_the_session_report_field (test_rebuild_safety.EvidenceProtection.test_unresolved_count_uses_the_session_report_field) ... ok
test_default_state_is_unique_per_run (test_rebuild_safety.StateOwnership.test_default_state_is_unique_per_run) ... ok
test_invalid_name_with_explicit_state_removes_nothing (test_rebuild_safety.StateOwnership.test_invalid_name_with_explicit_state_removes_nothing) ... ok
test_own_stale_directory_is_replaced_but_a_live_owner_is_not (test_rebuild_safety.StateOwnership.test_own_stale_directory_is_replaced_but_a_live_owner_is_not) ... ok
test_symbolic_links_are_refused (test_rebuild_safety.StateOwnership.test_symbolic_links_are_refused) ... ok
test_unmarked_directories_are_refused_and_left_untouched (test_rebuild_safety.StateOwnership.test_unmarked_directories_are_refused_and_left_untouched) ... ok
test_history_outage_after_owned_fill_still_installs_protection (test_recovery_gaps.RecoveryGapTests.test_history_outage_after_owned_fill_still_installs_protection) ... ok
test_late_query_missing_does_not_orphan_filled_add (test_recovery_gaps.RecoveryGapTests.test_late_query_missing_does_not_orphan_filled_add) ... ok
test_protection_lost_during_margin_transfer_blocks_the_add (test_recovery_gaps.RecoveryGapTests.test_protection_lost_during_margin_transfer_blocks_the_add) ... ok
test_locally_refused_protection_is_retried_under_the_same_identity (test_rejected_intents.RejectedIntentTests.test_locally_refused_protection_is_retried_under_the_same_identity) ... ok
test_refused_cancel_is_left_to_the_target_state (test_rejected_intents.RejectedIntentTests.test_refused_cancel_is_left_to_the_target_state) ... ok
test_rejected_entry_is_never_prepared_again (test_rejected_intents.RejectedIntentTests.test_rejected_entry_is_never_prepared_again) ... ok
test_unknown_protection_is_never_resent (test_rejected_intents.RejectedIntentTests.test_unknown_protection_is_never_resent) ... ok
test_ambiguous_initial_wallet_boundary_blocks_risk (test_review_followup.ReviewFollowup.test_ambiguous_initial_wallet_boundary_blocks_risk) ... ok
test_failed_amendment_preserves_old_pair_but_does_not_block_owned_exit (test_review_followup.ReviewFollowup.test_failed_amendment_preserves_old_pair_but_does_not_block_owned_exit) ... ok
test_foreign_live_writer_refusal_does_not_change_state (test_review_followup.ReviewFollowup.test_foreign_live_writer_refusal_does_not_change_state) ... ok
test_preanchor_late_income_is_not_new_income (test_review_followup.ReviewFollowup.test_preanchor_late_income_is_not_new_income) ... ok
test_session_backup_rotates_and_failure_keeps_original (test_review_followup.ReviewFollowup.test_session_backup_rotates_and_failure_keeps_original) ... ok
test_adoption_needs_both_splits_and_a_real_margin (test_robustness.AnalysisTests.test_adoption_needs_both_splits_and_a_real_margin) ... ok
test_deflated_sharpe_falls_with_more_trials (test_robustness.AnalysisTests.test_deflated_sharpe_falls_with_more_trials) ... ok
test_growth_is_the_geometric_mean_of_block_growth (test_robustness.AnalysisTests.test_growth_is_the_geometric_mean_of_block_growth) ... ok
test_a_block_uses_only_its_frozen_sessions_and_never_the_official_name (test_robustness.BlockTests.test_a_block_uses_only_its_frozen_sessions_and_never_the_official_name) ... ok
test_a_window_outside_the_frozen_range_is_refused (test_robustness.BlockTests.test_a_window_outside_the_frozen_range_is_refused) ... ok
test_knobs_apply_and_are_restored (test_robustness.BlockTests.test_knobs_apply_and_are_restored) ... ok
test_missing_prints_fall_back_to_the_official_mark_minute (test_robustness.FinalMarkTests.test_missing_prints_fall_back_to_the_official_mark_minute) ... ok
test_atr_window_and_impulse_threshold (test_robustness.KnobTests.test_atr_window_and_impulse_threshold) ... ok
test_defaults_are_the_frozen_model (test_robustness.KnobTests.test_defaults_are_the_frozen_model) ... ok
test_life_bars (test_robustness.KnobTests.test_life_bars) ... ok
test_retrace_moves_the_stop (test_robustness.KnobTests.test_retrace_moves_the_stop) ... ok
test_a_failing_stress_vetoes_the_chosen_value_but_missing_stress_does_not (test_robustness.RiskSelectionTests.test_a_failing_stress_vetoes_the_chosen_value_but_missing_stress_does_not) ... ok
test_isolated_point_is_a_spike_and_nothing_qualifying_keeps_six (test_robustness.RiskSelectionTests.test_isolated_point_is_a_spike_and_nothing_qualifying_keeps_six) ... ok
test_plateau_and_buffer_decide (test_robustness.RiskSelectionTests.test_plateau_and_buffer_decide) ... ok
test_update_time_moves_only_when_the_account_changes (test_robustness.UpdateTimeTests.test_update_time_moves_only_when_the_account_changes) ... ok
test_cancel_timeout_does_not_get_new_identity_on_each_poll (test_session.SessionTests.test_cancel_timeout_does_not_get_new_identity_on_each_poll) ... ok
test_complete_native_tape_replays_identical_requests_and_decisions (test_session.SessionTests.test_complete_native_tape_replays_identical_requests_and_decisions) ... ok
test_config_has_one_schema_and_bounded_time (test_session.SessionTests.test_config_has_one_schema_and_bounded_time) ... ok
test_deadline_during_preflight_prevents_new_entry (test_session.SessionTests.test_deadline_during_preflight_prevents_new_entry) ... ok
test_disconnection_never_infers_flat_or_successful_cleanup (test_session.SessionTests.test_disconnection_never_infers_flat_or_successful_cleanup) ... ok
test_external_fill_prevents_strategy_or_cleanup_position_changes (test_session.SessionTests.test_external_fill_prevents_strategy_or_cleanup_position_changes) ... ok
test_failed_protection_attempts_reduce_only_and_reports_unknown (test_session.SessionTests.test_failed_protection_attempts_reduce_only_and_reports_unknown) ... ok
test_finite_long_entry_hold_and_offline_protection (test_session.SessionTests.test_finite_long_entry_hold_and_offline_protection) ... ok
test_keyboard_interrupt_finishes_owned_protection (test_session.SessionTests.test_keyboard_interrupt_finishes_owned_protection) ... ok
test_later_session_never_tops_up_an_earlier_entry (test_session.SessionTests.test_later_session_never_tops_up_an_earlier_entry) ... ok
test_lost_active_stop_readback_resumes_missing_take_after_restart (test_session.SessionTests.test_lost_active_stop_readback_resumes_missing_take_after_restart) ... ok
test_macro_entry_restart_and_false_state_reduce_same_owned_position (test_session.SessionTests.test_macro_entry_restart_and_false_state_reduce_same_owned_position) ... ok
test_margin_transfer_past_the_deadline_sends_no_add (test_session.SessionTests.test_margin_transfer_past_the_deadline_sends_no_add) ... ok
test_negative_impulse_does_not_enter_in_promoted_long_only_model (test_session.SessionTests.test_negative_impulse_does_not_enter_in_promoted_long_only_model) ... ok
test_partial_fill_protects_actual_size_then_tops_up_under_same_protection (test_session.SessionTests.test_partial_fill_protects_actual_size_then_tops_up_under_same_protection) ... ok
test_protection_amendment_keeps_old_until_new_pair_confirmed (test_session.SessionTests.test_protection_amendment_keeps_old_until_new_pair_confirmed) ... ok
test_read_only_runs_repeatedly_without_orders (test_session.SessionTests.test_read_only_runs_repeatedly_without_orders) ... ok
test_real_transport_and_budget_complete_entry_protection_and_cleanup (test_session.SessionTests.test_real_transport_and_budget_complete_entry_protection_and_cleanup) ... ok
test_restart_retains_position_and_does_not_reenter (test_session.SessionTests.test_restart_retains_position_and_does_not_reenter) ... ok
test_retired_protection_history_can_expire_without_blocking_position (test_session.SessionTests.test_retired_protection_history_can_expire_without_blocking_position) ... ok
test_signal_expiry_closes_without_same_cycle_reversal (test_session.SessionTests.test_signal_expiry_closes_without_same_cycle_reversal) ... ok
test_stale_mark_time_cannot_mix_previous_exit_with_new_entry (test_session.SessionTests.test_stale_mark_time_cannot_mix_previous_exit_with_new_entry) ... ok
test_terminal_partial_exit_reduces_only_remaining_on_next_cycle (test_session.SessionTests.test_terminal_partial_exit_reduces_only_remaining_on_next_cycle) ... ok
test_timeout_after_fill_recovers_without_duplicate (test_session.SessionTests.test_timeout_after_fill_recovers_without_duplicate) ... ok
test_unavailable_cashflow_audit_blocks_top_up_before_it_is_sent (test_session.SessionTests.test_unavailable_cashflow_audit_blocks_top_up_before_it_is_sent) ... ok
test_unknown_entry_never_resends_even_after_restart (test_session.SessionTests.test_unknown_entry_never_resends_even_after_restart) ... ok
test_unsent_exit_can_shrink_after_native_protection_reduction (test_session.SessionTests.test_unsent_exit_can_shrink_after_native_protection_reduction) ... ok
test_verified_flat_finalizes_abandoned_replacement_journal (test_session.SessionTests.test_verified_flat_finalizes_abandoned_replacement_journal) ... ok
test_zero_fill_retries_archive_terminal_entries (test_session.SessionTests.test_zero_fill_retries_archive_terminal_entries) ... ok
test_intraminute_high_before_a_fall_is_a_peak (test_session_history.EnvelopePeakTests.test_intraminute_high_before_a_fall_is_a_peak) ... ok
test_missing_mark_minute_forfeits_the_isolated_wallet_or_flags_hindsight (test_session_history.EnvelopePeakTests.test_missing_mark_minute_forfeits_the_isolated_wallet_or_flags_hindsight) ... ok
test_fill_after_funding_settlement_pays_no_funding (test_session_history.IntraminuteEventTests.test_fill_after_funding_settlement_pays_no_funding) ... ok
test_funding_without_its_official_mark_is_unknown_not_the_entry_price (test_session_history.IntraminuteEventTests.test_funding_without_its_official_mark_is_unknown_not_the_entry_price) ... ok
test_overlapping_replacement_stops_fire_the_more_protective_leg (test_session_history.IntraminuteEventTests.test_overlapping_replacement_stops_fire_the_more_protective_leg) ... ok
test_print_path_drawdown_does_not_depend_on_polling_steps (test_session_history.IntraminuteEventTests.test_print_path_drawdown_does_not_depend_on_polling_steps) ... ok
test_print_path_peak_counts_before_the_stop (test_session_history.IntraminuteEventTests.test_print_path_peak_counts_before_the_stop) ... ok
test_protection_that_would_trigger_immediately_and_bad_margin_are_refused_natively (test_session_history.IntraminuteEventTests.test_protection_that_would_trigger_immediately_and_bad_margin_are_refused_natively) ... ok
test_stop_found_while_settling_an_add_drops_the_rest (test_session_history.IntraminuteEventTests.test_stop_found_while_settling_an_add_drops_the_rest) ... ok
test_stop_inside_the_minute_precedes_a_later_client_close (test_session_history.IntraminuteEventTests.test_stop_inside_the_minute_precedes_a_later_client_close) ... ok
test_unordered_official_minute_applies_the_adverse_stop_before_a_close (test_session_history.IntraminuteEventTests.test_unordered_official_minute_applies_the_adverse_stop_before_a_close) ... ok
test_cold_start_consumes_the_already_active_impulse (test_session_history.SessionHistoryTests.test_cold_start_consumes_the_already_active_impulse) ... ok
test_exchange_stop_between_sessions_is_not_a_client_order (test_session_history.SessionHistoryTests.test_exchange_stop_between_sessions_is_not_a_client_order) ... ok
test_ioc_fill_is_booked_at_its_print_and_answered_after_the_window (test_session_history.SessionHistoryTests.test_ioc_fill_is_booked_at_its_print_and_answered_after_the_window) ... ok
test_missing_prints_block_observation_before_any_order (test_session_history.SessionHistoryTests.test_missing_prints_block_observation_before_any_order) ... ok
test_schedule_module_does_not_hand_future_starts_to_the_exchange (test_session_history.SessionHistoryTests.test_schedule_module_does_not_hand_future_starts_to_the_exchange) ... ok
test_trade_print_window_fills_at_the_limit (test_session_history.SessionHistoryTests.test_trade_print_window_fills_at_the_limit) ... ok
test_unresolved_ioc_retries_without_a_fill (test_session_history.SessionHistoryTests.test_unresolved_ioc_retries_without_a_fill) ... ok
test_warmup_hours_make_aligned_four_hour_bars (test_session_history.SessionHistoryTests.test_warmup_hours_make_aligned_four_hour_bars) ... ok
test_crossed_long_liquidation_price_is_not_a_positive_buffer (test_snapshot_export.SnapshotExportTests.test_crossed_long_liquidation_price_is_not_a_positive_buffer) ... ok
test_flat_account_has_no_liquidation_buffer_or_extra_collateral (test_snapshot_export.SnapshotExportTests.test_flat_account_has_no_liquidation_buffer_or_extra_collateral) ... ok
test_reversed_collection_clock_is_unknown (test_snapshot_export.SnapshotExportTests.test_reversed_collection_clock_is_unknown) ... ok
test_short_export_includes_unrealized_pnl_once (test_snapshot_export.SnapshotExportTests.test_short_export_includes_unrealized_pnl_once) ... ok
test_uid_stale_mark_and_slow_collection_are_unknown (test_snapshot_export.SnapshotExportTests.test_uid_stale_mark_and_slow_collection_are_unknown) ... ok
test_contract_stop_does_not_use_mark_trigger_and_survives_stopped_process (test_star_session.SharedPeerTests.test_contract_stop_does_not_use_mark_trigger_and_survives_stopped_process) ... ok
test_peer_transport_preserves_market_and_contract_price_shapes (test_star_session.SharedPeerTests.test_peer_transport_preserves_market_and_contract_price_shapes) ... ok
test_short_partial_market_fill_and_add_keep_cash_identity (test_star_session.SharedPeerTests.test_short_partial_market_fill_and_add_keep_cash_identity) ... ok
test_atomic_report (test_state.StateTests.test_atomic_report) ... ok
test_crash_recovery_does_not_duplicate_or_overwrite_intents (test_state.StateTests.test_crash_recovery_does_not_duplicate_or_overwrite_intents) ... ok
test_deterministic_id_scope (test_state.StateTests.test_deterministic_id_scope) ... ok
test_exclusion_survives_database_commits (test_state.StateTests.test_exclusion_survives_database_commits) ... ok
test_state_directory_keeps_its_identity (test_state.StateTests.test_state_directory_keeps_its_identity) ... ok
test_damaged_database_blocks_instead_of_starting_empty (test_state.StateUpgradeAndRetention.test_damaged_database_blocks_instead_of_starting_empty) ... ok
test_fresh_directory_needs_no_backup_and_newer_state_blocks (test_state.StateUpgradeAndRetention.test_fresh_directory_needs_no_backup_and_newer_state_blocks) ... ok
test_legacy_directory_is_backed_up_once_before_it_is_versioned (test_state.StateUpgradeAndRetention.test_legacy_directory_is_backed_up_once_before_it_is_versioned) ... ok
test_old_observations_move_to_an_archive_before_deletion (test_state.StateUpgradeAndRetention.test_old_observations_move_to_an_archive_before_deletion) ... ok
test_entry_budget_uses_the_venue_clock (test_virtual_clock.VirtualClockTests.test_entry_budget_uses_the_venue_clock) ... ok
test_injected_monotonic_is_not_the_wall_clock (test_virtual_clock.VirtualClockTests.test_injected_monotonic_is_not_the_wall_clock) ... ok
test_positive_submillisecond_wait_advances_virtual_venues (test_virtual_clock.VirtualClockTests.test_positive_submillisecond_wait_advances_virtual_venues) ... ok
test_rate_limit_cooldown_stays_on_the_injected_clock (test_virtual_clock.VirtualClockTests.test_rate_limit_cooldown_stays_on_the_injected_clock) ... ok

----------------------------------------------------------------------
Ran 356 tests in 4.804s

OK
```

## Initial historical smoke output

```text
restored BTCUSDT-aggTrades-2020-01-01.zip
{"session": 0, "date": "2020-01-01T00:00:00Z", "failures": {}}
restored BTCUSDT-aggTrades-2020-01-02.zip
restored BTCUSDT-aggTrades-2020-01-03.zip
{"finished": "incumbent/base", "complete": false, "audit": true, "cagr": null, "mdd": "0.0241472855557217370830340017"}
```

## Timed no-op output

```text
{"session": 0, "date": "2020-01-01T00:00:00Z", "failures": {}}
{"finished": "incumbent/base", "complete": false, "audit": true, "cagr": null, "mdd": "0.0241472855557217370830340017"}
{"case": "old-incumbent-3", "elapsed_seconds": 0.7465176219993737, "maxrss_kib": 140520}
{"session": 0, "date": "2020-01-01T00:00:00Z", "failures": {}}
{"finished": "incumbent/base", "complete": false, "audit": true, "cagr": null, "mdd": "0.0241472855557217370830340017"}
{"case": "alpha-incumbent-3", "elapsed_seconds": 0.7385847620025743, "maxrss_kib": 155832, "exit_code": 0}
```

## Matrix smoke output

```text
{"session": 0, "date": "2020-01-01T00:00:00Z", "failures": {}}
{"finished": "incumbent/base", "complete": false, "audit": true, "cagr": null, "mdd": "0.0019990000000000000000000004"}
{"finished": "incumbent/fees-x1.5", "complete": false, "audit": true, "cagr": null, "mdd": "0.0019990000000000000000000004"}
{"finished": "incumbent/read-400ms", "complete": false, "audit": true, "cagr": null, "mdd": "0.0019990000000000000000000004"}
{"finished": "incumbent/trigger-slip", "complete": false, "audit": true, "cagr": null, "mdd": "0.0019990000000000000000000004"}
{"finished": "fresh-entry/base", "complete": false, "audit": true, "cagr": null, "mdd": "0.0019990000000000000000000004"}
{"finished": "fresh-entry/fees-x1.5", "complete": false, "audit": true, "cagr": null, "mdd": "0.0019990000000000000000000004"}
{"finished": "fresh-entry/read-400ms", "complete": false, "audit": true, "cagr": null, "mdd": "0.0019990000000000000000000004"}
{"finished": "fresh-entry/trigger-slip", "complete": false, "audit": true, "cagr": null, "mdd": "0.0019990000000000000000000004"}
{"finished": "atr-trail/base", "complete": false, "audit": true, "cagr": null, "mdd": "0.0019990000000000000000000004"}
{"finished": "atr-trail/fees-x1.5", "complete": false, "audit": true, "cagr": null, "mdd": "0.0019990000000000000000000004"}
{"finished": "atr-trail/read-400ms", "complete": false, "audit": true, "cagr": null, "mdd": "0.0019990000000000000000000004"}
{"finished": "atr-trail/trigger-slip", "complete": false, "audit": true, "cagr": null, "mdd": "0.0019990000000000000000000004"}
{"finished": "compression-breakout/base", "complete": false, "audit": true, "cagr": null, "mdd": "0.0019990000000000000000000004"}
{"finished": "compression-breakout/fees-x1.5", "complete": false, "audit": true, "cagr": null, "mdd": "0.0019990000000000000000000004"}
{"finished": "compression-breakout/read-400ms", "complete": false, "audit": true, "cagr": null, "mdd": "0.0019990000000000000000000004"}
{"finished": "compression-breakout/trigger-slip", "complete": false, "audit": true, "cagr": null, "mdd": "0.0019990000000000000000000004"}
{"finished": "single-topup/base", "complete": false, "audit": true, "cagr": null, "mdd": "0.0019990000000000000000000004"}
{"finished": "single-topup/fees-x1.5", "complete": false, "audit": true, "cagr": null, "mdd": "0.0019990000000000000000000004"}
{"finished": "single-topup/read-400ms", "complete": false, "audit": true, "cagr": null, "mdd": "0.0019990000000000000000000004"}
{"finished": "single-topup/trigger-slip", "complete": false, "audit": true, "cagr": null, "mdd": "0.0019990000000000000000000004"}
```

## Combo/calibration/capital/start smoke output

```text
{"session": 0, "date": "2020-01-01T00:01:00Z", "failures": {}}
{"finished": "fresh-entry+atr-trail+compression-breakout+single-topup/base", "complete": false, "audit": true, "cagr": null, "mdd": "0.0019989999999999999999999997"}
```

## Old-meter smoke script

```text
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from decimal import Decimal as D
from research import complete_perp as meter
feature = Path('/tmp/task1-no-features.json')
feature.write_text(json.dumps({'source': 'unused incumbent fixture', 'funding': [], 'basis': []}))
args = SimpleNamespace(market=Path('/tmp/coinquant-market'), prints=Path('/tmp/task1-public-prints'),
 fx=Path('/workspace/starquant/data/usdcny_frankfurter.json'), crowding=feature,
 out=Path('/tmp/task1-old-incumbent-3.json'), restore_prints=True, limit=3,
 initial_cny=D(10000), portfolio_budgets=False, portfolio_selected=None)
with patch.object(meter, 'CANDIDATES', ('incumbent',)), patch.object(meter, 'SCENARIOS', {'base': {}}), \
     patch.object(meter, 'select', lambda rows: {'selection_pending': True}):
 result = meter.measure(args)
with args.out.open('x') as f:
 json.dump(result,f,default=str,allow_nan=False)
```

## Timed smoke script

```text
import json, resource, runpy, time
from research.alpha_perp import main
start = time.monotonic()
runpy.run_path('/tmp/task1-baseline-smoke.py', run_name='__main__')
print(json.dumps({'case':'old-incumbent-3','elapsed_seconds':time.monotonic()-start,'maxrss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}),flush=True)
start = time.monotonic()
code = main(['--candidate','incumbent','--scenario','base','--limit','3','--prints','/tmp/task1-public-prints','--restore-prints','--out','/tmp/task1-alpha-timed-incumbent-3.json.gz'])
print(json.dumps({'case':'alpha-incumbent-3','elapsed_seconds':time.monotonic()-start,'maxrss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'exit_code':code}),flush=True)
```

## Equality script

```text
import gzip, hashlib, json, sys
from pathlib import Path
old=json.loads(Path('/tmp/task1-old-incumbent-3.json').read_text())
with gzip.open('/tmp/task1-alpha-timed-incumbent-3.json.gz','rt') as f:new=json.load(f)
a=old['results']['incumbent']['base'];b=new['results']['incumbent']['base']
fields=[k for k in a if k!='sessions']
differences=[k for k in fields if a[k]!=b[k]]
assert not differences,differences
assert len(a['sessions'])==len(b['sessions'])==3
assert all({k:v for k,v in x.items() if k!='observations'}=={k:v for k,v in y.items() if k!='observations'} for x,y in zip(a['sessions'],b['sessions']))
ledger=b['opportunity_ledger'];seen=set()
def size(o):
 if id(o) in seen:return 0
 seen.add(id(o));n=sys.getsizeof(o)
 if isinstance(o,dict):n+=sum(size(k)+size(v) for k,v in o.items())
 elif isinstance(o,(list,tuple)):n+=sum(map(size,o))
 return n
summary={'equal_fields':fields,'differences':differences,'session_count':3,'trade_count':len(a['trades']),
 'daily_count':len(a['daily']),'final_usdt':a['final_usdt'],'final_cny':a['final_cny'],
 'fees':a['fees'],'funding':a['funding'],'position':a['position'],'mdd':a['mdd'],
 'audit':a['audit'],'complete':b['complete'],'cagr':b['cagr'],
 'ledger_rows':len(ledger),'ledger_json_bytes':len(json.dumps(ledger).encode()),'ledger_loaded_object_bytes':size(ledger),
 'output_gzip_bytes':Path('/tmp/task1-alpha-timed-incumbent-3.json.gz').stat().st_size,
 'output_json_bytes':len(json.dumps(new).encode()),
 'monetary_sha256':hashlib.sha256(json.dumps({k:a[k] for k in fields},sort_keys=True).encode()).hexdigest(),
 'old_sha256':hashlib.sha256(Path('/tmp/task1-old-incumbent-3.json').read_bytes()).hexdigest(),
 'new_sha256':hashlib.sha256(Path('/tmp/task1-alpha-timed-incumbent-3.json.gz').read_bytes()).hexdigest()}
Path('/tmp/task1-noop-equality.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
```

## Review fix round 1 — supersedes the two attribution limitations in the independent review

Status: DONE, ready for independent re-review. FIX_BASE `c2a01d1c7ad09d58001ec2897a5a64d1b8284dd6`; FIX_HEAD `31e8b1e2b3f286fe3f948b7e1c473328ffdfeafa` (Fix causal failure chronology and immutable macro attribution). Only research/alpha_perp.py and tests/test_alpha_perp.py were committed; root's PROJECT_STATE.md edit remains untouched. The fixes change attribution/checkpoint metadata only; four mechanisms, execution math, defaults and production sources are unchanged.

Finding 1 fixed: cycle wrapper events are authoritative and carry actual failure time plus session/cycle-sequence/phase identity. The bounded session report's cycle summaries are not appended again. Other phases use a separately named session_phase_summary event, stamped at report completion and explicitly labeled timestamp_basis=session_report_completed; they are never backdated to session start or presented as precise failure times. Identical reasons on genuinely different cycles remain separate. A real finite-session fixture fails on cycles1/3, recovers in between, and verifies single events, actual chronology and correct retention of non-cycle phase summaries.

Finding 2 fixed: newly created macro opportunities emit one opportunity event with immutable created_at_ms, original decision_mark and a deep copy of the already-observed DFII10 row. Macro provenance is hash-bound, restored and validated with the campaign checkpoint. Repeated polls, changed later observations/marks and a later session cannot rewrite or re-emit its creation. Decision age uses actual decision time minus recorded creation time; ordinary macro creation time equals the absolute negative identity. If the original model establishes an epoch before legal geometry exists, actual opportunity creation is the later successful creation call; trading identity/math are untouched. Macro creation events receive the same post-run5/20-day diagnostics. Since creation can be intrabar, diagnostics use the last completed4h close at the horizon, with both horizon_ms and actual completed at_ms reported. A separate test asserts these prices are accessed only after execution returns. No adapter request or clock advance is added.

Verification at FIX_HEAD:

- `python -m unittest tests.test_alpha_perp -v > /tmp/task1-fix1-focused.log 2>&1` — 13 tests in0.436s, OK. New coverage includes recovery/deadline dedup/chronology, repeated-poll/checkpoint macro provenance and post-execution diagnostic timing.
- `python -m compileall -q coinquant research tests && python -m unittest discover -s tests -v > /tmp/task1-fix1-exact-head-tests.log 2>&1` — compile exit0; 359 tests in4.925s, OK.
- `git diff --check` — exit0, no output.
- `PYTHONPATH=. python /tmp/task1-fix1-baseline-smoke.py > /tmp/task1-fix1-old-smoke.log 2>&1` — original unchanged complete_perp runner, incumbent/base, fresh three-session account, same frozen market/FX/starts/prints as before; incomplete and audited true. Script differs from the previous saved baseline script only in output filename.
- `python -m research.alpha_perp --candidate incumbent --scenario base --limit 3 --prints /tmp/task1-public-prints --out /tmp/task1-fix1-alpha-incumbent-3.json.gz > /tmp/task1-fix1-alpha-smoke.log 2>&1` — fresh alpha three-session account at clean FIX_HEAD; incomplete and audited true.
- `PYTHONPATH=. python /tmp/task1-fix1-compare.py` — all26 original non-session fields and all session summaries exactly equal. Monetary digest is unchanged from pre-fix evidence. All14 cycle failures have distinct session/cycle/phase identities and actual post-start times. No session_error duplicates remain; the final ledger is sorted by actual event timestamps. Full assertions and evidence are preserved in the script and `/tmp/task1-fix1-noop-equality.json`.

```json
{
  "head": "31e8b1e2b3f286fe3f948b7e1c473328ffdfeafa",
  "dirty": false,
  "equal_fields": 26,
  "session_summaries_equal": true,
  "complete": false,
  "audit": true,
  "trade_count": 2,
  "daily_count": 3,
  "final_cny": "9785.598518713502741593659983",
  "final_usdt": "1406.616202737891506140917905",
  "monetary_sha256": "1889de3d0f75ee61fce760087ff4bb8ae32ab2d85b5a67bd147a48bea11606d2",
  "old_sha256": "d150f2c8a2d23c81d30b1ddedf43191ca9fd0d434e8addc7742ff43116f3ccb0",
  "new_sha256": "83fddec3d87dd8bdba5dd0bc72f8a51a426557860d6fb2ab2b21b9716f7a55d3",
  "events": {
    "opportunity": 2,
    "cycle_blocked": 14,
    "decision": 91,
    "entry_sizing": 1,
    "write_attempt": 4,
    "fill": 2,
    "topup_sizing": 21
  },
  "failure_identities_unique": true,
  "chronology_sorted": true,
  "failures_not_backdated": true,
  "source_delta_does_not_change_money": true
}
```

Artifact paths: `/tmp/task1-fix1-old-incumbent-3.json`, `/tmp/task1-fix1-alpha-incumbent-3.json.gz`, `/tmp/task1-fix1-noop-equality.json`, the exact-head/focused logs and saved comparison script named above. The new smoke contains two fills and three daily rows and remains complete=false/cagr=null. No full histories, real account operations, calibration claims or subagents. No unresolved implementation concern identified in this fix round; independent re-review and later economic gates remain outstanding as planned.
