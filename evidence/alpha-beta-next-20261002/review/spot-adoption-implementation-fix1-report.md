# Conditional Spot adoption implementation — fix1

Status: committed correction for the single P1 identity-schema finding in the independent spec/quality and financial-boundary reviews. Ready for scoped re-review; not adopted and no full historical replay performed.

- Proposal original BASE: `99fcf005d2cb15c13bb37322b65ab2863b19d65e`
- Fix1 BASE: `7ac94e12b41b9958072c9ff080983eea1a3cbd83`
- Fix1 HEAD: `0c52c812301de3712f3637a1ce1b1241de0c40f1`
- Full measured Python SHA-256: `619570fb7baa586f28ad5de2a440d7752a536cc8f8ce7e357264612e65801537`
- Branch/worktree: `codex/btc-spot-adoption-20261002`, `/workspace/btc-alpha-beta-adoption/spotquant`
- Exact Git-tree reconstruction using the historical sorted tracked spotquant/research `.py` path/NUL/bytes/NUL algorithm matches `source_identity()`, `dirty=false`.
- Only remaining working-tree modification: root-owned PROJECT_STATE.md, excluded from this commit.

## Corrected contract

`research.adoption_spot.risk_identity` now includes the established selected-account fields: candidate=`atr-stop`, components=`['atr-stop']`, the actual spec-file SHA, risk_scale equal to the validated fixed scale, core_mode=None, core_fraction=`'0'`, and the actual calibration SHA (None for unscaled). Existing canonical execution, rule, cutoff, scale, full profile and profile-SHA provenance remains explicit; complete_spot emits it through the existing research_identity addition and top-level adoption metadata. No original financial/operating row fields were removed or normalized.

No assessor, source verification, execution equivalence, forward gate, specification or protocol changes. The extra identity fields also remain bound by the existing exact diagnostic state identity; incompatible reruns still fail closed. This source is intentionally distinct from the previously reviewed proposal and frozen producers.

The guide now permits strictly serial canonical accounts after original Spot producers finish and this source is reviewed/frozen. At most one canonical process may run; disjoint Coin producers may coexist. Global financial selection and acceptance still precede adoption. No canonical full process was launched here.

## Regression and checks

New regression `test_canonical_unscaled_and_file_calibrated_rows_enter_immutable99_consumer` generates actual three-session canonical session/Lifecycle outputs for BOTH unscaled and file-bound calibrated profiles. It independently confirms the consumer module's exact immutable analysis99 SHA `a5bb0569f25e66b5aa660b0106d42c3ecffc7f30ebc5e2cf1b1216958ff43edf`. It then calls its real consume function on serialized canonical output, using matching synthetic input metadata and an exact committed temporary source snapshot.

Only ROOT is relocated to that isolated test Git repository. No metadata/source/identity/profile/validity gate is stubbed or bypassed; verify_source performs its real Git-archive digest check. The calibration case binds the exact fixture file SHA and full validated profile. Both cases assert the only rejection is measurement_incomplete and valid remains false, so synthetic partial accounts are never represented as financial acceptance. Existing local six-group equality test remains intact.

Before the producer fix, both subcases reproduced `KeyError('components')` at unchanged consume line621. After the correction:

- Focused `python3 -m unittest discover -s tests -p test_adoption_spot.py`: **11 passed**, 2.983 seconds.
- `python3 -m compileall -q spotquant research tests`: passed.
- Full `python3 -m unittest discover -s tests -v`: **209 passed**, 7.829 seconds, Python3.12.14.
- `git diff --check`: passed.
- Full test log `/tmp/spot-adoption-fix1-full.log`, SHA-256 `9b86322453c375b978ba2847f5c1bc4fd1fcc5e68ec35dddd461254be7fc2b16`.
- No full public market replay, downloads, active cache operations, private account use, Coin State/tests, subagents, producer edits, push or merge.

## Focused immutable change inventory

| Path | Fix1 BASE SHA-256 | Fix1 HEAD SHA-256 |
|---|---|---|
| `research/adoption-GUIDE.md` | `fb34817eb2014184db5fe1c4e68c897293ba469f2c70f75b18317c2401dab60e` | `a52152a90499da4078b4eba4ff4fd967a2e7ee7bb843a92bd2fbaa789a7ee7cf` |
| `research/adoption_spot.py` | `9f8cbfc91cb77d76021cdfa1dbd237d520bd28b4d0c67ccb992538fdc12cabce` | `cabc1f01b5d0c32fe3a8be6cee54f7b1bd1d14cc5dbf015758b2a16e54c4c555` |
| `tests/test_adoption_spot.py` | `28abc7715b5e148fe36b8c336f68530d13ed398471dac116ae3abde07eb3e5df` | `2d94f3d73c48d765a6b8bce461427153d5797609bbae9d8c612544158ad60aef` |

All other proposal files, including research/alpha_assessment.py and runtime model/session/decision/remainder implementation, are unchanged from fix1 BASE. The original implementation report retains the earlier full inventory as historical context.

## Pending

Independent scoped spec/quality and financial-boundary re-review; then coordinator-controlled source freeze and the five complete canonical accounts on exact reviewed inputs. The external immutable-analysis99 bridge must still establish all six groups equal against original frozen accounts, complete/known/audited archives and exact source/input/calibration provenance. Remaining global finance, mechanical selection and final adoption gates are unchanged. No financial equivalence, prospective alpha, native execution or real account-day claim follows from this schema correction.
