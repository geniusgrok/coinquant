# Task2 fix round1 independent review

Scope: only the two prior findings and their immediate regressions, `17a21516045795b6d29280f5b3a47dbf2f17c588` → `4568a7f82a867a81b580a28c759eabebb72e1702`. Read the complete fix package and appended implementation report; no source edits, full-history runs or account calls.

**Spec compliance: PASS. Task quality: APPROVE.** Both prior findings are addressed; no immediate regression found.

- **Core opportunity provenance — ADDRESSED.** `research/alpha_spot.py:146-158,194-221` now reconstructs confirmed core net BTC changes, including BTC fees, and renews the trigger after an actual closure while ignoring material partial remainders. The trigger respects bootstrap and slow-core bullish boundaries. `exit_order_id`/`exit_fill_ms` identify the causal sale; repeated polls and restored Policy/checkpoint instances preserve the renewed identity. The real-session STOP/reentry tests exercise both core modes and same-day blocking. These values only enter journal attribution; order selection and persisted identity/state policy are unchanged.
- **Registered protocol hash — ADDRESSED.** `research/alpha_spot.py:548` now reads `SPEC.with_name('alpha-beta-PROTOCOL.md')`. The exact-head emitted hash independently matches `4ae09ae0bc9224f8028ddcc1373dc1bbc7251a70be2945e5655f5e5fa12eb27e`; the exact-path producer test passes.

Independent verification:21 focused tests pass (`/tmp/task2-fix1-review-focused.log`); compileall and diff-check pass. Checked implementer's171-test passing log and exact-head seven-candidate smoke. Independently compared preserved pre-fix and post-fix raw artifacts: every account's money, audit, fills, daily curves, positions, allocations, timestamped client events, pending intents and operational session fields are identical (excluding nondeterministic archive backup hashes). All seven audits pass with zero unresolved sessions. Equality/hash check output: `/tmp/task2-fix1-review-equality.log`. Existing real three-session core0 equality also passes in the focused suite. Source inspection shows no new adapter calls or simulated clock advances.

Full-window economics and adoption gates remain Task4; this approval covers the reviewed Task2 implementation and fixes.
