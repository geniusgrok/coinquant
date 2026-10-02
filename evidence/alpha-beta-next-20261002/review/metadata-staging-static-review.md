# Task4 metadata staging — independent static review

**Initial static verdict: corrections requested for three specific statements (all three subsequently closed; see fix review below).** This is a review of external drafts, frozen source behavior and completed stage evidence only. It is not financial completion, runtime adoption, integration or publication approval. STATUS.md correctly prohibits applying the staged documents before repaired final64, independent finance, actual5 bridge and a separate adoption decision pass.

## Reviewed draft SHA256 bindings

| Draft | SHA256 |
|---|---|
| metadata-staging/STATUS.md | `55e11cb5f7420c689ed9eb9f76dfc0c263782a382b011fd2a957da5e7b2dd99f` |
| metadata-staging/spot-README.md | `a1cc32ee1ce7223d2bb62664d6b472ab0eeb2425364171480c3dee64999d27d8` |
| metadata-staging/spot-AGENTS.md | `7cdb85109021e84bcf49d23125fb148824929ab3ff8a2233f7a060d4ae186923` |
| metadata-staging/spot-adoption-GUIDE.md | `44eb956e90c6cf76d8bb69570991ff120a119e40279684c8cd59efbf9e29a807` |
| metadata-staging/coin-README.md | `5e6cc94b33b5c915aa0240f4eb1b14715c60835846efd1cefbf390b1ff10a70f` |
| metadata-staging/coin-AGENTS.md | `8f9dd84fdba3988ca89f628adc9ce472f9bf705f3b44d27b5155e4711a680ca4` |
| FINAL-RESULT.md | `5e725bfde8b47d54346de297f3ab7c6b0be142b2cac899fcd40426810d2c779a` |
| REPRODUCE-registered.md | `d21c58c15338082122aa8466950d5352f7a5ffef909e930b7c3e1f0b6ff08075` |

## Concrete corrections

1. **P2 — Describe the final canonical BUY cash gate, not the intermediate portfolio pool.** `spot-README.md:69` says the capital ceiling constrains a buy pool containing free cash plus expected exit proceeds. That describes the intermediate portfolio calculation, but canonical `spotquant/preview.py:decision` subsequently removes all BUYs whenever a SELL exists and clips surviving BUYs to current `snapshot['usdt_free']` and the remaining ceiling after valuing all current BTC. Readers should not infer that anticipated same-cycle exit proceeds can fund a BUY.

   Suggested replacement for this part of the table: “最终买单按当前真实可用USDT与扣除全部现有BTC估值后的剩余账户额度取小；当轮有SELL时不发BUY，退出成交经下一轮核对后才可用于新入场。共识提升仍受这些上限约束；资金上限不是亏损上限。” The existing later statements about exits-first behavior remain accurate.

2. **P2 — Distinguish final verification's120-second budget from the total bounded tail.** `coin-README.md:120` says normal ending/Ctrl-C uses at most120 seconds of cleanup. Its own earlier line71 correctly states the360-second absolute grace bound. Frozen `coinquant/lifecycle.py` defines protection120 + reduction120 + final verification120, with `ABSOLUTE_GRACE` as their sum; `session.py` enforces the hard end while starting final verification with `FINISH_SECONDS`.

   Replace the global “最多120秒收尾” wording with “最终核验预算120秒；必要的保护、失败减仓及最终核验续期受会话截止后360秒的统一硬上限约束”。 Preserve the existing no-new-entry, unresolved-reporting and interruption limitations. The120-second stage is not a promise that the whole process has exited within120 seconds.

3. **P2 — Keep the historical HTTP root cause qualified.** `coin-AGENTS.md:21` says the operating equality failed “because public print acquisition errors altered two snapshots.” The preserved root-cause report and financial addendum establish a source-consistent acquisition mechanism and matching synthetic discrimination, while explicitly saying the original journal did not retain the remote status or source URL/CHECKSUM-versus-ZIP identity. Avoid turning that supported mechanism into an unqualified historical network attribution.

   Suggested wording: “The unity control's operating evidence differs in two sessions. Frozen-source analysis and an offline discriminating probe support public-print acquisition HTTP errors as the source-consistent mechanism; the original remote status and acquisition URL were not recorded.” Continue to preserve all five matching groups, the original BLOCKED verdict and the strict six-group repair requirement. FINAL-RESULT.md and REPRODUCE-registered.md already use appropriately qualified wording.

These are draft corrections only. No controller, source or financial operation needs to be interrupted to address them.

## Static consistency confirmed

- Frozen adoption source uses Model v5 with fourteen timestamped completed true ranges, arithmetic ATR14, no range for the first origin bar, and a copied decision view with distance `clip(4*ATR14/completed_close,.10,.30)`. Stored Model/follow catch-up remains28%. Allocated native stop floors are bounded to the current campaign; actual owned-position peaks and the partial-sale remainder helper are reused. Through-mark protection creates ordinary reductions, SELLs precede new BUYs and existing positions are not topped up merely to reach consensus exposure.
- State guards precede Lifecycle recovery and reject incompatible rules/checkpoints/research state and malformed durable allocations. The drafts retain preservation/reconciliation instructions rather than suggesting deletion, empty-directory migration or new account identity. Offline calibration remains a file-bound fixed new-BUY scale; default scale1 and owner/native safety gates remain separate.
- The staged documents distinguish the canonical shared-session meter from historical equal-allocation/rebuild accounts and preserve the old joint portfolio's consensus-era label. Historical M10/P3/P4 figures are not substituted for the new measured account. Historical source labels should continue to be read with their dated sections and recorded digests, not as the post-integration tree.
- Completed SPOT-RESULT, COIN-RESULT, actual Spot risk review, diagnostic/BLOCKED Coin risk review and canonical-five financial review support the cited base/stress figures, target failures, adverse worst-day tradeoff, actual risk scales and validation beta/volatility bands. The drafts distinguish cumulative USDT return percentage-point differences from annual CAGR and CNY results. HAC7 intervals are descriptive, include zero for the stated Spot case and do not correct selection/research contamination. Continuous OHLC/minute/envelope MDD is not presented as an independently replayed second-engine path.
- Coin's original monetary pass is not substituted for the failed operating-control verdict. The reproduction guide retains original failed raw/report/index paths, one-attempt intent, approved restore, native-gzip actual incumbent retry, complete795/six-group gate before retained-four projection, unchanged profiles/rows, one-level manifest and separately named repaired final/index. The approved repair/audit/bridge/copier helper paths and SHA values match the reviewed versions. The three cited operational-review SHA values were independently rehashed and matched.
- The actual native-zero binding proof and empty acceptance artifacts support the stated exit2, empty account UID, absent owner capital/evidence, `ready_for_owner_native_review=false`, `native_execution_verified=false`, qualification NOT_QUALIFIED and zero actual observation days/cases. The proof distinguishes Spot0c52 template-tool provenance from each target execution package (Spot0c52 and Coinaced); this is correctly kept separate from full runtime/research Python digests. No empty template is described as native verification.
- Forward initialization remains future, actual-UTC, all-cash/zero-observation research-source evidence. Nothing in these drafts authorizes backfill, elapsed-day credit, private account access or a generic forward/source override. Byte-preserving packaging retains original internal paths and needs external Git/public inputs for full reproduction.

## Outstanding evidence and review

The top STATUS and FINAL-RESULT draft notice remain essential. Present-tense completed/adopted prose inside staged target documents is prospective publication text; it must not be applied, circulated as a completed result or stripped of its gating context now. Fill the actual repaired-final SHA and four sensitivity results only from completed bound evidence. Independently review the resulting final64 finance, actual source bridge, separate decision, forward/native evidence, archive manifest and final whole-branch integration before publication. This static review does not discharge those gates.

No draft edit, frozen import, test/producer/checker execution, network request, State/cache/HOME change, Git/HEAD action or active-process operation was performed. Only source, compact completed reports/native artifacts and this external review report were read/written as appropriate. No full financial raw was loaded and no new financial result was calculated.


## Scoped wording fix review — all three findings closed

**Current static verdict: PASS / APPROVE for draft consistency only.** Reread the three corrected passages against the cited frozen source and completed root-cause evidence. Spot now explicitly defers all BUYs when SELL exists and limits BUYs to current free cash/remaining whole-account capital; Coin distinguishes the120-second final verification budget from the360-second hard tail; the HTTP explanation now states source-consistent propagation and the unavailable historical remote attribution. Each requested correction is satisfied.

Corrected draft SHA256 bindings:

| Corrected draft | SHA256 |
|---|---|
| metadata-staging/spot-README.md | `b30a842ab2aff10a2b8766c7f223bd2c2e00a1f26916f54d40be3270836b8220` |
| metadata-staging/coin-README.md | `bf44551d6da4487b1481f7db22b77fd9dbe89046c52548cf52594a70d868a69e` |
| metadata-staging/coin-AGENTS.md | `9115c574db144f54535725a8d14e369d083dd9b7cc18d5f5da51e3ab66ceb4d6` |

FINAL-RESULT.md remains `5e725bfde8b47d54346de297f3ab7c6b0be142b2cac899fcd40426810d2c779a`; REPRODUCE-registered.md remains `d21c58c15338082122aa8466950d5352f7a5ffef909e930b7c3e1f0b6ff08075`. Their pending final-SHA/sensitivity/decision status is unchanged. Initial hashes and findings above are preserved as review history. The future application, final financial/evidence/whole-branch review and adoption gates remain mandatory; this static PASS does not authorize applying or publishing the staged text. No draft or frozen source was edited by this reviewer.
