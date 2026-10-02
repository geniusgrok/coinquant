> Current proposal: fix1 HEAD `0c52c812301de3712f3637a1ce1b1241de0c40f1`, Python SHA `619570fb7baa586f28ad5de2a440d7752a536cc8f8ce7e357264612e65801537`. See [fix1 report](spot-adoption-implementation-fix1-report.md). The original round report below is retained unchanged as historical evidence.

# Conditional Spot adoption implementation report

Status: committed proposal, ready for independent spec/quality and financial-boundary review. NOT adopted. No full historical canonical replay, merge, push, live/private access, market/cache activity or producer tests were performed. Original financial workers remain authoritative and untouched.

- Worktree: `/workspace/btc-alpha-beta-adoption/spotquant`
- Branch: `codex/btc-spot-adoption-20261002`
- BASE: `99fcf005d2cb15c13bb37322b65ab2863b19d65e`
- HEAD: `7ac94e12b41b9958072c9ff080983eea1a3cbd83`
- Full measured Python source SHA-256: `7d4985f9176cd1d6a995be6c4fbcff17ffc5dad832218fae594eeb1b8b76a380`
- Identity is reconstructed from the exact Git tree using the historical producer algorithm: sorted tracked `.py` paths under `spotquant` and `research`, each encoded as path/NUL/bytes/NUL. `research.rebuild.source_identity()` matches and reports `dirty=false`.
- Only unstaged change after commit: parent-owned `PROJECT_STATE.md`, deliberately excluded. All proposal source/tests/docs are committed.

## Shared behavior

Model version5 stores fourteen timestamped completed true ranges. Each is computed against the preceding completed close before replacing that close; the first origin bar supplies none. Restore validates SHA, version/type, count, exact daily range timestamps, finite nonnegative ranges, close-history count and existing model flags. Persistent `trail=.28` remains unchanged.

`preview.decision_view` copies a folded view and applies the selected `clip(4*ATR14/close,.10,.30)` distance, then floors stops at allocated native STOP_LOSS prices with status `(TERMINAL-REJECTED)|NEW|PARTIALLY_FILLED` and the original campaign boundary `signal_ms >= floor(first_ms/DAY)*DAY-DAY`. Actual fill peaks and folded position fields are preserved; only the decision protection flag becomes `resting`. No adapter request or pre-entry wick is added. `follow.py` is byte-unchanged.

The canonical decision wrapper reuses the historical portfolio for entry/consensus rules, then copies exactly the selected through-mark ordinary reduction/grouped SELL/protection rebuild and exits-first/free-cash/whole-account-cap/quote-rounding/minimum clipping branch. The branch runs at scale1. The terminal partial-sale remainder invokes the same helper with committed positions and cached owners before rebuilding protection.

RULE is `2026-10-02-atr-stop`. Cycle entry performs read-only validation before Lifecycle construction/recovery: old/missing rules, research state/wrappers, wrong sleeves/model parameters, malformed model/range checkpoints, incomplete positions/follows/entry anchor, and incompatible pending allocations fail closed. Flat, held and pending legacy cases preserve state and send nothing. No silent flat migration or ownership reset exists. Models/positions/risk identity still commit together through canonical State.set_many.

## Replay and diagnostic scale seam

`python3 -m research.adoption_spot --scenario base|fee150|slip2|outage --out NEW.json [--risk-calibration FILE]` uses the explicit `complete_spot.measure(..., canonical=True, calibration_path=...)` seam. It constructs the same HistoricalVenue and Config and runs the real session.run/State/Model/decision/Lifecycle, monetary audit and archive verification. It does not construct Policy or enter configured, and rejects already-installed research Model/State/portfolio/follow/protection replacements. No copied exchange/meter, ResearchState, ResearchModel or stop/remainder replacement is installed.

The seam preserves all original raw row fields, including filters. Only the existing `research_identity`, `risk_calibration`, `opportunity_ledger` and `subpools` research additions are used; the canonical opportunity ledger is empty and does not pretend to reproduce research instrumentation. Adoption/source identities are also explicit top-level metadata. Existing alpha_assessment, source/forward checks and six evidence groups are byte-unchanged.

Only an offline venue receives the diagnostic profile. The existing registered calibration validator verifies the atr-stop file/profile; canonical State persists candidate, rule, exact file SHA, profile SHA/full profile, scale and fixed 2022-01-01 cutoff. Missing/changed identities reject before recovery, and the calibration file is reverified after replay. The scale is1 before the cutoff and fixed after it, acting only on new BUY allocation after the same cap calculation. Owned quantities/protection are unchanged. No public live-config option or calibrated default was introduced. The parent-reported actual scale `0.9972720085277638` was not run here.

Historical research Policy entrypoints discard the three explicit canonical context kwargs (positions/owners/allocation_scale) so their own selected-policy calculations remain independent. This new tree is still a new executable and MUST NOT be advertised as frozen8ca/analysis99 source-equivalent. The original frozen trees and raws remain necessary for financial proof.

## Verification

Final environment: Python3.12.14 (CI remains configured for3.13; CI was not run).

- `python3 -m compileall -q spotquant research tests`: passed.
- `python3 -m unittest discover -s tests -v`: **208 tests passed**, 5.727 seconds.
- Final test log: `/tmp/spot-adoption-tests-final.log`, SHA-256 `658a6aff428a8e8bb0f2b5205190cee4d2648a5af92cc1b86c11a225b76baf6c`.
- `git diff --check`: passed before commit.
- Dedicated tests: completed ATR warmup/gaps/future independence/queue chronology, checkpoint roundtrip and malformed identity, early legacy flat/held/pending and malformed-new-state rejection with unchanged SQLite/no recovery, installed-floor status/campaign boundaries, actual-fill decision peak, through-mark SELL and BUY deferral, file/profile cutoff/identity/new-sizing, and canonical meter engine-hook exclusion.
- Existing full suite retains failed-cycle model/position atomicity, partial fills, retained dust, terminal partial-sale remainder, lost acknowledgements, unknown identities, cancel/replace/prepared-sale recovery, external balances, read-only and live-block checks. Updated old numeric stop expectations only where the new shared default intentionally differs; old flat-checkpoint expectation now requires rejection. Incomplete old synthetic fixtures gained realistic marks, model state and native allocation fields.
- Three-session synthetic canonical account matched the selected atr-stop research path on this new tree in **all six unmodified evidence fingerprint groups**. Both sides used actual finite sessions/audits/verified archives. This is a local mechanism/schema regression, not the required frozen8ca financial proof.

## Changed paths and immutable inventory

| Path | BASE SHA-256 | HEAD SHA-256 |
|---|---|---|
| `AGENTS.md` | `458c3706c437036b87258c3ff93e07f3e9c15d51664ceb823e11fcb6e090cd4c` | `654b16c56ff08591f3f0be28901acc318b00c29b36572124f1be035bfa13cfdb` |
| `README.md` | `f56a2168e9a31b8e8c10e431a141fea07b6d22d342918d67902b4a33db49e60e` | `a9a66b1c029326b359e8a79ca40f5d44931cda277543dafd86e82d89361a4591` |
| `research/adoption-GUIDE.md` | `new` | `fb34817eb2014184db5fe1c4e68c897293ba469f2c70f75b18317c2401dab60e` |
| `research/adoption_spot.py` | `new` | `9f8cbfc91cb77d76021cdfa1dbd237d520bd28b4d0c67ccb992538fdc12cabce` |
| `research/alpha_spot.py` | `2de030fab8bae1f0e2665d5d8201347ff823237c1712bb14b7f38afeaaed4e9c` | `dcce52f3e6d133354403a8f6837b687c5b7098c086865d198eeafffdce5bd50b` |
| `research/complete_spot.py` | `a4864b43388c3e86426a9b455bb65aabdf008ffd16aebaab9184d93639c0eeb6` | `5956fac2766b3cec5299df00cbb34216cb52e49de1ee6290a659e87dcd754e55` |
| `spotquant/execution.py` | `14fe31c35f5822072f07708bdec8f6cf1e0f15bedc12c7c19d30f7702f64af8f` | `07ec228071afb7364024a82313972791348216df5218c4f0cfb64a85fbb4dcbf` |
| `spotquant/model.py` | `1029d764ae79b590e925ded1b2b0023d1852c4bd977a14511f1a04c302764602` | `a02da7dd9674155ee577ecd3cc176cfe9d934a4a5d4b65aa6b9a7ab14e2ff57f` |
| `spotquant/preview.py` | `a1e0226b331c6d0fcf77af50ce7c097a010439e1db1949e831e3e2b65cc97996` | `fe22ed3ef27722f237ab101d32949116f55e88b4877f87952013abe9f27770bf` |
| `spotquant/session.py` | `c003b9b14a42558ac8ea351a5df12a2dc65c9a745f51e3978a91759b8aab12e2` | `aea8107ddbc318ba623988c3448c4df1a5bc39db147f05f3818995912630e0b6` |
| `tests/test_adoption_spot.py` | `new` | `28abc7715b5e148fe36b8c336f68530d13ed398471dac116ae3abde07eb3e5df` |
| `tests/test_grouped_close.py` | `c857ef364301c6b0345b5ff6caada297793c28256180236cfc58ffca9046bd80` | `2a3c8657be3f3ad56ddb5226d78386076b29af5228d327637038cabbdaf8de99` |
| `tests/test_p4_execution.py` | `c55f567287db08d8769b987ab204914c8336ccd3aea2da9e7574d8fabd3feb3f` | `d8da25ec9ab085f3e58b834057c5f220f95659ca8aeea66176b0f69b2f486337` |
| `tests/test_session.py` | `fe7e1b8020333fc3f76ba72b30da405cf072156929c30627ccf56818e7ef4187` | `9ea79e24121da7076cdc1a93eee4d74d2ddfe5051c64f8593a7391ec359905e6` |

`research/alpha_assessment.py`, `research/alpha_beta_spec.json`, both original protocols, all original evidence and `spotquant/follow.py` are unchanged. No dependency or configuration-schema change.

## Remaining gates and limitations

Independent spec/quality review and financial boundary review are pending. Actual7 risk/full Coin finance and final mechanical selection remain the coordinator's active work. After those complete and reviewed source is frozen, run the four unscaled actual canonical stresses plus the exact selected calibrated base serially. Require complete/known/audited/archive-valid accounts, all six exact groups equal, and an external bridge binding immutable analysis99, frozen producers, original/adopted raw SHAs, exact Git/full-Python/spec/protocol/market/FX/schedule/calibration identities and reviewed changed paths. This commit authorizes no equivalence claim for another Python tree.

No extra adoption-forward framework or source-check bypass was added, per the implementation brief. A diary may remain honestly bound to the frozen research implementation through analysis99. Native execution remains unverified, account-days remain zero, live writes remain blocked and owner Demo gates remain unchanged. Confirmed-cancel protection gaps remain. On any failed selection/proof, retain the incumbent and classify the candidate research-only.
