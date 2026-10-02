# Broad alpha/beta source review

Reviewed 2026-10-02. Coin BASE `58074c1e4f1b374ce5a4bdccccf474a51647be47` → HEAD `acedaa43ca94223f24e2fe11851bbef74e032a69`; Spot BASE `4f25316ad253546ca566173f6cff09703c1bffd8` → HEAD `8ca002522fbdce531dcfbbb783ff4d152a7fd66c`.

**Spec verdict: REQUEST CHANGES for one causal-assessment handoff defect.** The reviewed mechanism, accounting, calibration, selection and forward-interface implementations otherwise conform to the registered scope and pre-outcome rulings.

**Code-quality verdict: REQUEST CHANGES for the same P2 reporting defect.** No new money-conservation, execution-safety or financial-path defect was established. This is not approval of financial results, default adoption or native qualification.

## Finding

**P2 — Preserve Coin fill-to-opportunity links when compacting the journal.** `spotquant/research/alpha_assessment.py:366–375` assigns a fill's opportunity from `event.opportunity` or `event.signal_ms`. Coin's actual producer supplies neither: `coinquant/research/alpha_perp.py:429–435` records `client_order_id`, and its earlier write event at lines304–306 contains the corresponding `identity` and `opportunity`. The assessor ignores that relation and omits the client ID from its output. Consequently every Coin fill-size record has `opportunity:null`; it cannot be joined to the desired/accepted sizing records by the preserved compact fields. An order ID identifies the fill group but is absent from the sizing records.

This is a concrete producer-to-consumer gap in the registered actual opportunity/desired/accepted/fill attribution, not a loss of the numeric fill amounts. It was not exercised by the earlier isolated sizing regression, which constructs a Coin fill without an opportunity and asserts only its amount.

Read-only reproduction used the already retained `/tmp/task1-fix1-alpha-incumbent-3.json.gz`, not a new replay. Its entry sizing reports opportunity `1578038400000`, desired `0.9661394791732414710641954977` BTC and accepted `0.966` BTC. Its write event maps client `cq-2e9ee5b4d01a21dca7b7a725719665` to that same opportunity. The two actual BUY fills for order2 preserve that client ID and quantities `0.002` and `0.964`. Current `diagnose(..., [], 'perp')` emits:

```json
{"identity":{"opportunity":null,"order_id":2,"side":"BUY","exit_type":null},"observations":2,"values":{"qty":{"n":2,"sum":"0.966","min":"0.002","max":"0.964"}}}
```

Minimal correction: resolve the existing Coin client-ID/write-event opportunity relation during assessment before compacting fills, preserve relational identity, and fail closed or explicitly mark ambiguity rather than infer an ownership link by timestamp. Add a regression consuming producer-shaped journal events, including multiple/partial fills and repeated/unknown write observations. Unattributed exits must remain explicitly unknown unless their relation is proved; do not invent a campaign assignment.

**Preservation impact:** the running producer already retains the necessary entry link in raw journals. Preserve raw accounts and frozen source identities. This finding does not establish a reason to discard or rerun monetary accounts, and it does not require changing an active producer. A later separately identified assessment-only fix can consume preserved raw artifacts. The controller was notified immediately before this report; no source/HEAD modification was made by this reviewer.

## Broad review coverage

Read both AGENTS.md files, mirrored spec/protocol/plan, the active PROJECT_STATE rulings, all three implementation reports and approved fix reviews, complete new source modules, full-diff scope, and relevant original Campaign/session/Lifecycle/ownership/preview/model/meter surroundings. Prior closed findings were not re-opened absent new evidence; the finding above is a newly reproduced producer/consumer interaction.

- **Coin mechanisms:** prior-only breakout high/ATR/median inputs and original opportunity priority; immutable primary/macro provenance; fresh-entry boundaries restricted to new primary exposure; completed-bar primary trailing state, proven-stop floor and normal through-mark reduction; original entry-session, committed-size, protection, fresh sizing and pending-intent gates for confirmed top-ups. Scoped hooks restore on exit and preserve the existing dispatch/cleanup coordinator.
- **Spot mechanisms and pooled money:** actual-fill reentry allowance and exit eligibility, later completed closes/reclaim/reset gates; target adds restricted to owned bullish tactical sleeves with original exits/capital/free-cash constraints; completed ATR inputs, repair behavior, monotone confirmed stops and partial-exit remainder protection; separate core/tactical allocated fill ledgers including BTC/USDT fees and dust; independent cash pools and unmerged core protection. The declared core bootstrap clarification is reflected in the source. Combined components retain tactical/core separation, exit priority and global cash/capital bounds.
- **Calibration/sizing interface:** scale is1 before the cutoff; calibration statistics slice2020–2021 before calculation; profile/spec/raw-input hashes and fixed effective boundary are checked; consumer assessment recomputes the complete deterministic calibration; new sizing changes while owned positions and committed Coin requests are not retroactively resized. Actual post-cutoff volatility/beta and validation returns are reported separately, with failed/unidentifiable risk match unable to claim matched alpha.
- **Evidence/selection:** exact matrices and outage starts; original dispatch timing; immutable approved original baseline hashes, ancestry and all six evidence groups; required actual unity controls; fixed compatible combination and core exclusion/tie rule; four matching stresses and original ranking; required incumbent/final Coin capital/start sensitivity tuples; rejected accounts remain inventoried and prevent rule freeze even when registered work can close. The pre-outcome ruling that selection uses paired unscaled stresses while risk accounts provide separate attribution is consistently implemented.
- **Final freeze/forward interface:** pending work, failed baseline proof, invalid measured accounts and failed unity controls block freeze. Current Python/spec/protocol equivalence and analysis identity are bound. Initialization is all cash at actual receipt time; appends accept only later, latest completed public bars, preserve gaps, and use integrity checking plus locked atomic replacement. This is an observation diary, not simulated fills or actual account days.
- **Boundaries:** runtime/default files are unchanged by these source diffs; original public data/proxy assumptions and zero native/account-day claims remain explicit. No expanded strategy grid or new account authority is introduced.

## Reviewer verification

- Coin: `PYTHONDONTWRITEBYTECODE=1 python -m unittest tests.test_alpha_perp -q` — **13 passed**.
- Spot: `PYTHONDONTWRITEBYTECODE=1 python -m unittest tests.test_alpha_spot tests.test_alpha_assessment tests.test_complete_assessment -q` — **49 passed**.
- Both complete fixed BASE→HEAD `git diff --check` calls passed.
- Recomputed current tracked research/runtime Python digests match the frozen manifest exactly: Coin `a6e3f30f02208ff7e604b6181c5d8fa7000fe7e30dbc3276fbcc93ffbb0ad227`, Spot `0df8c537ee8d47db6e841778e8e37eac847e1a0c1151e379440081b9473ae026`.
- Both HEADs remain the requested immutable commits. Both spec copies are byte-identical with SHA `8228013f4ac41affb65162c1cabad8f51b5ef32b9607f62231a4776168a337d0`; protocol copies are byte-identical with SHA `4ae09ae0bc9224f8028ddcc1373dc1bbc7251a70be2945e5655f5e5fa12eb27e`.
- Only controller-owned PROJECT_STATE.md changes were visible in worktree status at verification; this reviewer did not modify them.

No financial replay, full-history measurement, download, new scan, account operation, source edit, Git mutation or subagent was performed. Existing full-suite and exact-head CI results were supplied by the controller, not rerun or independently fetched here. Full-history resource behavior remains unmeasured by this review. The independent completed financial audit, exact full-baseline equality, all actual risk accounts, eligible combinations and final sensitivities remain separate gates.
