# Task4 project calibration plumbing — ready for independent review

Implemented and committed in `/workspace/btc-alpha-beta-analysis/spotquant` on `codex/btc-alpha-beta-analysis-20261002`.

- BASE: `32ab1bb546bde064e641c4a2eb5ed4248e590acb`
- HEAD: `99fcf005d2cb15c13bb37322b65ab2863b19d65e`
- Commit: `Accept verified project calibration files for actual risk accounts`
- Scope: `research/alpha_assessment.py`, `tests/test_alpha_assessment.py`, `research/alpha-forward-GUIDE.md`; 173 insertions, 3 deletions. Product assessor change is 32 changed lines.
- Source directories are clean. The pre-existing/root-managed `PROJECT_STATE.md` modification remains unstaged and uncommitted. No merge or push.

## Behavior and boundary evidence

`--risk-spot-calibration FILE` and `--risk-perp-calibration FILE` select the actual calibration used by that project's risk input. Each file is parsed and hashed through existing `read_json`, preserving original bytes, gzip identity and duplicate-key rejection. After both full unscaled matrices have been consumed with the unchanged 28+20 account expectations, the override is compared with the full deterministic calibration restricted to that project's registered profiles. Canonical JSON comparison also rejects boolean/integer or float/integer substitutions that Python value equality would otherwise conflate. Every root field and legal profile must match; no caller-selected exclusions or trust flag exist.

Without an override, the project uses the existing global `--calibration` file and raw SHA. The existing global deterministic comparison is unchanged, including when project overrides are supplied. Both overrides may be supplied without a global file; any actual risk input without its legal project/global calibration fails. `--calibration-out` remains the complete unified deterministic output.

Actual risk consumption receives the selected parsed calibration and its original raw SHA. The existing consumer still enforces the risk metadata SHA and exact row/profile binding. It does not rewrite risk metadata. `report.calibration_sha256` retains the global identity, with additive `calibration_scope: full_deterministic_document` (or null when absent). Additive `risk_calibrations[kind]` records the actual file's `raw_sha256`, full/project `scope`, and complete sorted `profiles` list.

Inspection confirms unchanged training calibration functions, ten risk obligations plus two unity controls, pinned original baseline/six-group equality, source/input/history gates, sensitivity inventory, achieved-match limits, selection, all-valid/freeze/final gates and native/account-day zero meanings. There is no early-calibration product CLI or partial unified final assessment.

## Verification

- Test-first new calibration tests initially failed on the absent loader/report fields, then passed with implementation.
- `python -m unittest discover -s tests -p test_alpha_assessment.py -v`: 27 passed.
- `python -m unittest discover -s tests -p test_complete_assessment.py -v`: 7 passed.
- `python -m unittest discover -s tests -p test_alpha_spot.py -v`: 21 passed, using existing temporary synthetic Spot accounts.
- `python -m compileall -q spotquant research tests`: passed.
- `python -m unittest discover -s tests -v`: 198 passed in 3.633s. Full output: `project-calibration-tests.log` next to this report.
- `git diff --check`: passed before commit.
- Real committed-tree `verify_execution_equivalence` against frozen Spot `8ca002522fbdce531dcfbbb783ff4d152a7fd66c`: passed after commit. Both full historical Python digests were verified first; the existing sole assessor exception was reused unchanged. Exact spec/protocol identities passed.

New tests derive project documents independently with existing `calibration_document({kind: bundle}, ...)` and compare with the unified deterministic result. Both projects reject missing baseline/candidate profiles, foreign profiles, changed scales/input hashes/baseline identities/cutoffs/training dates, missing/extra profile fields, changed root spec/format/cutoff, missing root fields and manual trust flags. Gzip files retain their actual compressed hashes. Integration tests use real risk-file consumption with synthetic incomplete rows, mocked upstream fixture/source I/O, and real training derivation; they cover global-only, each mixed configuration, both overrides, overrides without a global file, missing fallback, wrong actual hash, global subset substitution and pending `--final` rejection. The resulting synthetic rejected rows retain 60 accounted cases, all ten risk obligations, false validity/freeze and native/account-day zero. CLI parsing is covered.

## Source identities

- Current full Python source SHA256: `427f34ca3640cfa78f51173583af1d9c82f007baae155f3a992dcffb8171ad7b`
- Frozen Spot full Python source SHA256: `0df8c537ee8d47db6e841778e8e37eac847e1a0c1151e379440081b9473ae026`
- Execution-equivalence SHA256: `c2dd29733ec5bb96137a8ab27cc0e8dd604d74bf6d1e108d45a554b8923e6cf8`
- Spec SHA256: `8228013f4ac41affb65162c1cabad8f51b5ef32b9607f62231a4776168a337d0`
- Protocol SHA256: `4ae09ae0bc9224f8028ddcc1373dc1bbc7251a70be2945e5655f5e5fa12eb27e`
- `research/alpha_assessment.py`: `a5bb0569f25e66b5aa660b0106d42c3ecffc7f30ebc5e2cf1b1216958ff43edf`
- `tests/test_alpha_assessment.py`: `fc20a34014ce63eac45f302cab04af877850162b33f87a06a2f3acf1c4b7b7a3`
- `research/alpha-forward-GUIDE.md`: `4d50c0598988e4f707751e3bba7ce2cd7dd95bcb0de280183592b18673b1fdd1`

Machine-readable committed proof: `project-calibration-source-proof.json` next to this report.

## Limits and review request

This verifies assessment plumbing, not completed actual risk replays or a final economic result. No full market replay, download, Coin producer, private account State, shared cache operation, frozen producer edit, source/default exception or new strategy was invoked. Offline tests use temporary synthetic fixtures; the Coin source-proof test creates a temporary Git repository only. Actual full48 assessment and comparison of the independently generated Spot calibration to the final unified subset remain controller work after both full matrices complete. Coin operations sharing simulated UID12000 must remain serialized.

Root: please perform/request the scoped independent specification and financial-boundary review of BASE..HEAD using this report. Implementation is ready for that review; it makes no early completion, economic qualification or native qualification claim.
