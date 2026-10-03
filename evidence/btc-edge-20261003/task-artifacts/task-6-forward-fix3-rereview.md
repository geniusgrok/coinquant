# Task6a forward fix round3 scoped independent re-review

T6-F6-R1: **ADDRESSED**.

SPEC: **PASS for this scoped fix**.

QUALITY: **APPROVE for this scoped fix**. No new Critical/Important finding was found in the amended bootstrap, selection-input or checkpoint paths.

This closes the remaining ROOT-F6 cold-start finding. F1–F5 remain closed under their earlier reviews; they were not reopened. Financial measurement, actual final proof/export and real paper initialization remain pending root work. This verdict does not establish financial performance or native qualification.

## Immutable scope and identities

Read task-6-forward-fix3-review-brief.md first, then the binding fix3 brief, prior R1 finding and unchanged reproducer, final appended report, complete root packages, relevant current native call paths and retained evidence. Reviewed only T6-F6-R1 and material fix-introduced regressions. Both standalone modules carry the same changes; active Spot behavior was checked for accidental changes.

- Spot BASE `7faa66beeafbfb803bb72a36b926ee5a7a08d49d`, HEAD `2e1ad327f81dff57c2680e96fcaaaf57c892f0ff`.
- Coin BASE `f4e82fb63742318846e51d189d03587ccc84af79`, HEAD `541db0a99055f11a2a7824742ce115c52ac7739f`.
- Spot complete package SHA: `2684055e9f69d8594e83e91999bca13557d114317b141f3e50ac85154e99ff90`.
- Coin complete package SHA: `56cb117d64d434faee5638bf453fe9fdae15484be7d042037a0bb9cd452391b4`.
- Final report SHA: `a83c448578d5460270d4dbd041d461c4bf80c7eede982f03f3a3baf2b4faf815`.
- Preserved original/fix1/fix2 report-prefix SHA: `8ea5905b5eceefe226cfd2e328b1e811946889a39188c400f2c49405956aa3ff`.
- Evidence-index SHA: `a74e1230ec7ebb7e3ed5fa5bfef0ae789ce750a0d09ac4ea426cfdc39846994c`.
- Smoke-summary SHA: `91b8140cb05f6593e8a0dd5e227683a95130232e3b02c22c28c52e859ea37146`.

Independently verified both root package hashes and exact equality with Git's full reviewed BASE..HEAD diff; both current module/test files match their committed blobs. Verified all73 indexed evidence files and the exact retained report prefix. Both HEADs remain fixed, with only root's PROJECT_STATE.md dirty. No source or helper bytes were changed.

Exact source receipts bind:

| Identity | Spot | Coin |
|---|---|---|
| Runtime/research Python | `f2d6c3e73c2acb7b328a7a0e2678bb95ceb77d8a17a46139abfe8b357befdbf6` | `ba63895131db566e708a5c96cde4504beace39fa0bdd54881d039dd5b8ef4c50` |
| Protected bytes/modes | `f932c103e73e1fdc0b3b3592ad75d7a0dde21396d6df43888e4c620a4af49d93` | `b0cb0b7df265767f28e4fa7511865cbbb8f3150a3f2edfa1c5caf33138a1ebc9` |
| edge_forward.py | `7fd5e8c5a7f49902f0b1c0c477f2f8670e4e66baef3e50e54846593253d6eefa` | `6209f9bb5bc6d0b87c56c42c2e130545bce6a9f5e6fc61df5e66446be8cb3410` |
| Source-receipt file | `f9c58493c429ba0c74899baa6eba9cbfbf49c655bf2cc8d3f3af1e221df26994` | `6c7ed5fa3c3bfd674989e0565110af72b7712915d316019361f2c27deaa4838c` |

Shared test SHA: `f54707a8aeefe36fa2d1a8f6d2ec8ca2d1104c5ce8651dce80ec5a03ef94382d`.

## R1 resolution and native correspondence

The Coin engine now initializes an explicit boolean `market_bootstrap=True` in both history and deferred modes. Warmup-only and blocked decisions cannot clear it. The adapter no longer infers completion from event count or kind.

The amended advance path reproduces coinquant.linear_preview.advance's repeated primary consumption while bootstrap remains pending. This matters after a missing relevant macro observation: a later still-current primary impulse cannot quietly establish ownership before the native baseline selection completes.

In coin_decide, missing relevant DFII10 or missing current mark preserves pending status. The first successful canonical Campaign.select_macro call uses the persisted flag. Its returned Campaign checkpoint and `market_bootstrap=False` are stored together before preview or downstream execution gating, matching coinquant.session.cycle's completion boundary. Exceptions prevent persisted diary replacement. A genuinely irrelevant DFII input still follows canonical macro_relevant behavior rather than becoming an unconditional data requirement.

The book adapter now parses available current mark and DFII10 selection evidence before returning for missing execution evidence. Thus valid macro selection with missing depth consumes and persists the existing regime even though the event is preview-only. Later depth cannot resurrect the same regime. Missing mark cannot complete selection using an old completed close. No private/native preflight was introduced.

The strict boolean checks cover both initial and terminal engines as well as the transition entry points. Missing/null/integer/string replacements reject; Python's bool/int equality cannot admit0/1. Audit reconstructs initial true from code, replays real advance/select calls against retained raw evidence, and compares the full resulting engine. Sealed false completion, removed events or a substituted Campaign checkpoint cannot stand in for that transition. This is a source-bound Coin schema change; earlier diaries are not migrated or relabeled.

## Independent reproduced result

Ran the original unchanged full-append probe once during this re-review against the final Coin HEAD:

```sh
PYTHONPATH=/workspace/btc-alpha-beta-improve/coinquant python task-artifacts/task-6-forward-fix2-coldstart-probe.py
```

The probe retains its original SHA `1d71d065db7d1821f1a0b00a2ff7b7bbb2607f66099d15a9a9d92e36a580f27c`. Actual raw ALFRED parsing, Campaign selection, paper accounting, append and reload audit run unchanged. Only the clock, approved-export trust and HTTP acquisition boundaries are mocked. No actual public/native/account operation occurs.

Observed:

```text
FIRST_DECISION {'action': 'blocked', 'reason': 'causal DFII10 raw vintage evidence required', 'opportunity': None} BTC 0
KNOWN_BEFORE_INIT True LATEST_OBSERVATION 2019-12-30 VINTAGE 2020-01-01
NATIVE_FIRST_VALID_MACRO_ACTION consumed
EVENT_KINDS ['warmup_only', 'decision', 'decision']
FIRST_VALID_MACRO_ACTION consumed BTC 0
APPENDED_AND_RELOADED_AUDIT True
```

The old source entered3.49984 BTC at this exact boundary. The current source now agrees with canonical first-valid macro consumption and preserves zero exposure. Fresh independent output is retained as task-artifacts/task-6-forward-fix3-independent-probe.txt, SHA `b9bfa36a949ed750e0c8d8800b1223224db50a00f6690ca5c49f835b1afc3d3f`; it matches the implementer's retained exact-commit green output byte-for-byte. Temporary raw fixture files were automatically removed.

## Regression evidence and fix-new assessment

Inspected the four new meaningful Coin regressions and their recorded passing run. They cover normal and deferred histories, repeated relevant-data failures, first valid pre-initialization macro consumption, later actual ineligible→eligible entry, missing-mark persistence, valid selection with missing depth followed by complete-book non-reentry, repeated primary consumption while pending, later genuine primary reset/fresh entry without irrelevant DFII, raw-form rejection, strict flag/checkpoint/event tampering and immutable failed append.

The existing Coin sizing/fill fixtures now establish a genuine synthetic successful baseline selection via retained ALFRED bytes and actual append before testing later entry. They do not fake completion with an event placeholder. Their scheduling-anchor adjustment leaves the diary initialization time and baseline event intact. The primary accepted quantity, monetary assertions, F2 macro budget and requested-versus-realized target checks remain covered; no weakening of the economic constraint was found.

Recorded affected validation:

- Spot72 tests OK,11 skipped; log SHA `cae74113736e14da0996039261359dfbfda3709e1b88a497ab3a5f64c69ab804`.
- Coin49 tests OK,5 skipped; log SHA `a47f267ebb3ecc4de6cc70bcb9894861c48932db93e39ef6bb3ff87a865af32b`.
- Six exact-commit normal/pending/warmup SYNTHETIC CLI audits pass. Coin pending/warmup stay bootstrap true and BTC0; its normal fixture records a successful baseline before a later fresh entry. Each audit labels raw reconstruction only and source_binding_verified=false; clean committed source is separately archived.

These suites and six smoke audits were inspected, not rerun. The one independent R1 probe above was the only review-time behavioral execution. No broader review, producer or unchanged test-suite repetition occurred. No material new regression was identified in the changed selection-input ordering, bootstrap state or source-bound replay seams.

## Limits and preservation

Only this report and the new independent probe-output file were added persistently. No source/helper modification, commit, child agent, public network, native/private/account/credential operation, Coin account suite, full financial producer, source freeze, actual export/diary, HOME/UID or lock change occurred. Root's dirty progress documents and all prior evidence remain untouched.

The approval closes R1 and the scoped F6 residual; it does not substitute for root's registered full financial matrix, independent final financial proof, canonical export or actual source-bound initialization. Mocked synthetic zero-event/warmup states are not genuine observations or real account days. Current adapter restrictions, complete fresh history requirements, public-access uncertainty, sticky unresolved protection and Coin mark-path limits remain disclosed. Native cases0/actual account-days0/NOT_QUALIFIED and the absence of prospective/native performance proof are unchanged.
