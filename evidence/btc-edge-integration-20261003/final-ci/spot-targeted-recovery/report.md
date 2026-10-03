# Final Spot CI targeted fixture recovery

The original Spot CI run `37142985145` failed three cases (350 tests, 11 skips). This packet records a targeted local recovery only; it does not claim a green CI rerun. The failed CI log is preserved at `/workspace/btc-alpha-beta-improve/task-artifacts/spotquant-final-ci-37142985145.log` (SHA256 `6e44dce68f187c6d94ba611cc3ee6d5a790f7115fe34656fb555685237b0b379`).

Repair base: `90fd8c35a65e786b75a97fc168a737b0ebca630d`. Final owned commit: `bf5ea35a6f83ebdb1f283feca5c4b9683f6e783d`. Only `tests/test_edge_spot.py` and `tests/test_session_account.py` changed (5 insertions, 3 deletions). No production defect was found in the examined failing call paths.

## Demonstrated causes and smallest corrections

1. `test_crowding_strict_actual_clock_momentum_and_missing_safety` manually constructed basis metadata whose observation was one minute after the UTC day boundary. Shared `crowding.value_at` correctly rejects that observation. Setting the test clock to the UTC completion plus the existing 60-second publication lag makes its recorded basis observation a valid completion. All existing actual-clock, strict momentum, half/full sizing, missing BUY, stale funding, and safety SELL assertions remain unchanged.
2. `test_hooks_restored_on_decision_and_measurement_failure` patched `preview.decision`, while the historical policy invokes `preview.atr_decision`. Patching that actual decision hook restores the intended injected exception. Both decision-failure and measurement-failure hook-restoration assertions remain unchanged.
3. `test_actual_bounded_sessions_enter_protect_and_independently_audit` used a historical venue with no crowding source and ran ten-second sessions at UTC midnight, before basis publication. `session._cycle` correctly passes missing entry inputs to the canonical policy, which blocks BUY. The test now supplies the existing `KnownFeatures` fixture and starts each session at publication time. Its actual entry, passive STOP_LOSS protection, error-free sessions, and independent monetary audit assertions remain unchanged.

## Authorized affected checks

Exactly the three failed test names ran together once, serially under Python 3.13.5 and `PYTHONPATH=tests:.`, with the original HOME, UID, and locks. PID 154226; exit 0; 3 tests passed, 0 failures/errors/skips. Actual argv/timestamps are in `command-start.json` and `command-finish.json`; complete output is `targeted-three.log` (SHA256 `70161c5e7eb6569035d7a57402dc2a5212426b7ccfec7ebb5e55a08dbb6cc620`). Existing SQLite ResourceWarnings are preserved in that log. No additional cases, fullsuite, CI, Coin/account calls, producers, preflights, compileall, or financial replay were run for this repair. The Spot account lane was released after completion.

## Source impact and handoff

Git tree comparison establishes that every tracked entry outside the two owned test paths has identical mode and blob ID at base and final HEAD. Program, configuration, and protocol bytes are unchanged. Program/research Python identity remains `8396c368948fe9f939c9aa3910384e2092a3ca4bb6fb0c7aae075ba7033bc585`. `source-impact.json` records the comparison, identities, exact paths, clean working tree, and original log hash. `base-to-final.diff` matches the patch exercised by the three-case run byte for byte (SHA256 `5a3d2ef8b26a024c5113748ce5d3b6143c7362604348e729cabe8f3c13d3159e`). Prior CI logs, financial packets, Git objects, and proofs were preserved. No default/main promotion, export, or init was performed. Independent narrow fixture review and integration remain with root.
