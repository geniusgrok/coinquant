# Reproduce the registered BTC alpha/beta study

Finite-session historical proxies; native cases and actual account-days are zero. This previously studied history is not clean out-of-sample evidence. Keep failed attempts and rejected candidates; partial progress is not a completed account.

## Sources and inputs

Use retained Git history and mirrored Coinquant/Spotquant/Starquant siblings. Star supplies historical public FX only. Frozen producers are Coin acedaa43ca94223f24e2fe11851bbef74e032a69 / Python a6e3f30f02208ff7e604b6181c5d8fa7000fe7e30dbc3276fbcc93ffbb0ad227 and Spot 8ca002522fbdce531dcfbbb783ff4d152a7fd66c / Python 0df8c537ee8d47db6e841778e8e37eac847e1a0c1151e379440081b9473ae026. Separately reviewed evaluation source is Spot99fcf005d2cb15c13bb37322b65ab2863b19d65e / Python427f34ca3640cfa78f51173583af1d9c82f007baae155f3a992dcffb8171ad7b, with frozen Coin/FX siblings. Preserve actual measured identities through integration.

Spec SHA2568228013f4ac41affb65162c1cabad8f51b5ef32b9607f62231a4776168a337d0; protocol4ae09ae0bc9224f8028ddcc1373dc1bbc7251a70be2945e5655f5e5fa12eb27e; FX67606315ea34c0301e0129ac8fc27056099986d9fbd58a552a07f140cdd05bb5. The only existing execution-source exclusion is Spot `research/alpha_assessment.py`; every other runtime/research Python byte matches. Full historical digests are reconstructed from Git archives first; the actual analysis executable remains separately bound.

Public official CHECKSUM-verified archives live under `/tmp/coinquant-market` and `/tmp/spotquant-market/klines`. Initial `public-archive-preflight.json` is a snapshot, not proof of later restored files. Retain consumed minute/print SHA manifests. Coin `--restore-prints` restores official daily prints into the marked bounded cache. Reproduction needs archives/network and unchanged Git history; runtime dependencies remain standard library.

The independently approved public ZIP observer is `public_print_vault.py`, SHA `65ad132f5bf48559d455d4fa8a76966da76f661b1dda1540068f81c5f422e506`. It reads only CHECKSUM-verified immutable BTC public ZIPs from the exactly marked `/workspace/.btc-third-round-prints`, retaining hardlinks and receipts outside the producer cache. It does not retain decoded BINs, access account State, change UIDs/HOME, or write into the active producer cache. Before later Coin commands, and only with no Coin producer active, it restores the same original ZIP bytes under an exclusive restore lock. The retained vault has a 16 GiB cap and 5 GiB free-space guard; checksum conflicts and unsafe paths fail closed. Preserve `public-print-vault` records, per-command `*-public-archive-restore.json` receipts and operational reviews; the large ZIP cache is reproducible public input rather than a required Git artifact. Stop the observer only after every Coin producer finishes by creating its regular `.stop` marker.

## Operating condition and retained failure

Run whole Coin processes strictly sequentially whenever synthetic UIDs overlap. Locks are under `Path.home()/.local/state/coinquant/account-locks`; separate ZIP/cache/state directories do not isolate account identity. Never remove/bypass locks, change HOME, or suppress blocked accounts. Spot can run beside Coin with at most two workers and adequate temporary space.

An attempted parallel incumbent probe interrupted the original Coin20 run at the global lock. Original progress/log, stopped probe partials, explicit approval retraction and independent empty-lock check are retained as operational evidence. None are completed monetary accounts. The complete Coin20 cohort restarted from the beginning on identical source into `perp-singletons-retry1.json.gz`. Superseded reproduction text and queues are retained for failure history, not as parallel Coin instructions.

## Full unscaled48 cases

Choose exclusive outputs and a sufficiently large task TMPDIR. Do not change producer source/HEAD while any financial command runs. From frozen Coin:

```sh
TMPDIR=/workspace/scratch/alpha-beta-next/tmp python -u -m research.alpha_perp \
  --restore-prints --out /workspace/scratch/alpha-beta-next/perp-singletons-retry1.json.gz
```

This measures five candidates×four stresses in one chronological tape pass. From frozen Spot, use retained `run_spot_registered.py`, that checkout, a new spot-singletons directory, `--expected-head 8ca002522fbdce531dcfbbb783ff4d152a7fd66c`, and the task TMPDIR. It measures seven candidates×four stresses in candidate-sized/two-worker batches, preserves exact JSON as deterministic lossless gzip, verifies roundtrip SHA, and writes accounts-manifest.json binding each original compressed file. Primary cases have795 starts except the registered Spot outage789.

Approved originals under each project's evidence/complete-delivery-20261001 are Spot spot-consensus-corrected.json SHA cf075b86ba5df590e078a7c626c53cb20937be955cfb6ad8d41eae19b78645e8 and Coin perp-exclusive-accounts.json SHA15dd7bfc242d52bf692663179cd1e3867418f8b55a4cad0894d253a8b296f00a. The older failed spot-accounts-final.json is excluded. Baseline equality checks all four scenes across financial/fills/daily/ownership/operating/remaining-original groups. Prices, quantities, cash, status and times stay exact; synthetic client spelling normalizes relationally and archive hashes only after individual proof verification.

## Actual risk calibration

After all28 Spot scenes and original Spot controller exit, `run_spot_early_risk.py` checks exact inventory, pinned baseline4 and execution-source proof. Existing calibration helper derives spot-project-calibration.json from731 actual2020–2021 USDT daily returns, then replays all legal Spot base profiles including its unity baseline. Invalid bases retain absent profiles/explicit inapplicable obligations. No partial unified final assessment is emitted.

After full48 and Coin producer exit, `run_registered_followthrough_project_calibration.py` checks both original baselines and writes full deterministic registered-calibration.json. The actual earlier Spot bundle is consumed with `--risk-spot-calibration spot-project-calibration.json`; final unified assessment independently requires exact equality with the deterministic full document's complete legal Spot subset. Coin risk uses the full document after original Coin exit. Original calibration raw SHA remains bound to each actual risk bundle; never relabel project hashes as global hashes.

Reviewed queue SHA09e38e09eb755a79a8a6d7d20e83b8a371cf507e2f4c6e3b2315e13ddd9d37cd. Hard-coded PIDs describe this execution. For reproduction, update only paths/exclusive outputs/waiters for actually launched processes before launch, record the new script SHA and independently verify serialization. Do not reuse stale PIDs or alter economic parameters/sources. Commands record cwd, source HEAD, actual UTC start, wall time, exit/log/output SHA.

The active execution uses independently approved `run_registered_followthrough_public_vault.py`, SHA `be02ff9432a5dc1d2d8bb3198aaf342d33fa65d04ce34ccc06361f8357d527e3`, wrapping that unchanged original queue. Its persistent whole-queue lock rejects duplicate controllers; it rechecks both helper hashes and restores verified public ZIPs immediately before each original Coin command. Module, argv, executable, cwd, economic parameters, source, account identity and outputs remain those of the original queue. The predecessor was stopped only after independent PID/PPID inspection proved it had no children and no economic commands/outputs; `followthrough-project-calibration-stop-receipt.json` and `public-vault-controller-start.json` bind the handoff. Original logs and stopped queues remain evidence. This public input reuse does not permit parallel Coin producers.

All ten new risk obligations and two legal unity controls remain inventoried. Fixed731-day training scales affect only new sizing from2022; no retrospective resizing, scaled/spliced curves. Achieved1723-day2022+ volatility must be ≤baseline×1.05 and BTC beta≤baseline+0.02 for the matched label. Failed matches receive no matched-alpha classification.

## Combinations and sensitivity

Unscaled four-scene paired constraints identify eligible singletons. The only combination contains all compatible individually eligible components; cores are exclusive under fixed rank/tie rules. Zero components is inapplicable; one reuses its existing account; two or more require the exact proposed combination's actual four stresses. No subset search. Rejected combination retains best eligible singleton. Risk matching is a separate descriptive classification.

Finally replay incumbent and final selected Coin at four base-only tuples: CNY9900/offset0, CNY10100/offset0, CNY10000/offset−60000ms and CNY10000/offset+60000ms. Deduplicate only if incumbent remains selected. All Coin risk/combo/sensitivity processes are sequential. These diagnose robustness, not optimal capital/schedule. `--final` rejects pending work; honest rejected/inapplicable inventory can close while invalid accounts still block rule freeze.

## Independent verification and interpretation

Independent checker reconstructs fills/cash/BTC/both fee assets, Coin weighted entry/funding, daily returns and allocated core/tactical pools. It separately recomputes OLS/HAC7/capture/ES/training scales and prefix ledger identity. Preserve original input/checker/source SHA, command and limitations. Derived audits cannot substitute for original raw accounts or prove native fills.

Selection/goals use original row CAGR over exact registered dates: Spot365.25-day year, Coin365.2425. Shared descriptive daily CAGR/volatility/regression annualization use365.25, separately labelled. USDT terminal metrics are final_usdt; CNY are final_cny. Report continuous proxy alongside closing MDD, costs/funding, FX, BTC beta/capture/ES, calendar concentration and partial2026. HAC intervals do not correct research selection. Post-event price diagnostics are not attainable missed profit.

Measurement queues do not adopt defaults. Runtime adoption requires independently reviewed minimal shared changes and complete canonical monetary/execution proof; otherwise keep incumbent. Public forward diaries initialize all cash at actual UTC only after complete review/rules freeze, with zero observations/account-days. Append only later observed latest completed public bars with original receipts/SHA; no backfill, invented days/fills or qualification claims. Private account operations remain outside this delivery.

## Separate canonical Spot runtime and adoption bridge

The minimal shared runtime proposal is Spot `0c52c812301de3712f3637a1ce1b1241de0c40f1`, Python `619570fb7baa586f28ad5de2a440d7752a536cc8f8ce7e357264612e65801537`, based on immutable analysis99. `research.adoption_spot` invokes the shared Model/session/Lifecycle/HistoricalVenue path without AlphaPolicy/configured research hooks. The default adaptive stop uses 4 completed ATR14/close clipped to 10–30%, preserves proven protection floors, and keeps default sizing scale 1. Actual diagnostic calibration affects only new post-cutoff BUY sizing. Persistent Model v5 state guards reject old or malformed checkpoints before recovery; no checkpoint is discarded or repaired implicitly. Existing execution-source equality correctly rejects this changed runtime.

`run_spot_canonical_accounts.py`, SHA `89697d4d22904f5d93db40e19acf89781c1fd7653a4b7115536a749d98266915`, collected exactly five complete accounts serially: base, fee150, slip2, outage and file-calibrated base. Original command/compression receipts and `spot-canonical/canonical-inventory.json` retain every measured identity. The independent `spot-canonical-five-financial-review.md` and proof `c1803ecb6c66a1f6397415ce2b033f569ebca46e6df42419bee87ea45f351b8d` verify all six groups against the original atr-stop four stresses and actual calibrated risk row, and separately reconstruct funds/statistics. This is exact-five equivalence, not global completion or adoption approval.

Only after a valid complete `registered-final.json` and exact independent global audit coverage may the approved `verify_spot_adoption_bridge.py` SHA `ed4fabacf35be78b33e8763a1de20eae88798f940b8fa9ed88c504c62bf156fd` run. Supply `--inventory spot-canonical/canonical-inventory.json`, the exact proposal `--expected-head` and `--expected-python-sha256` above, `--final-report registered-final.json`, and a new exclusive `--out`. It binds the final selection, all original audit coverage, full global/project calibration identity, exact-five receipts, source Git archives, six-group fingerprints and changed-path hashes. It emits equivalence evidence with adoption unapproved; independent final review and a separate explicit adoption decision are still required. No generic checker/forward source override is permitted.

If forward diaries bind immutable analysis99, label them as research-source diaries and separately identify any adopted runtime. New runtime proof does not silently relax the old forward source gate. Historical raw measured HEADs remain unchanged after later documentation/integration commits.
