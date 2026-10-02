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

## Strict operating-control repair and retained original attempt

The original five-account Coin risk raw `risk-perp.json.gz` SHA `3b958b2e92d8aefcf7b9f073a3916c325420a546cf7652203ce6692be5ee2446` passed independent monetary reconstruction, but the incumbent unity control failed operating equality in sessions31 and38. All five other evidence groups matched. Public print lazy acquisition can propagate a non404 HTTPError into the historical adapter's HTTP-unknown observation. Pure offline discrimination confirms that path; the original remote status and CHECKSUM-versus-ZIP failure URL were not recorded and cannot be recovered. Do not label the historical status503 from the injected probe, normalize the trace, or call the original financial review approved.

Retain the complete original five raw accounts, original `registered-risk.*`, `registered-combinations.*`, original `registered-final.*` and original `financial-audit-remaining-index.json` at their exact paths and byte identities. A zero command exit or completed monetary index does not waive the operating-control failure. Those reports document the first attempt and are not adoption inputs.

The externally reviewed `repair_coin_risk_incumbent.py` SHA `957d4b0171469351c38b1a27bdc579a368dc0408fa37c348686d24aeb1c6c5d8` waits both original serial queue and original remaining-audit processes, verifies closure of all four mandatory sensitivities, acquires the same whole-queue exclusive lock, and records an exclusive persistent one-attempt intent before restore or execution. Its scoped provenance review SHA `21a51ddb816a4610d3a28d944406fd3256029d12d6c7006d483ba4200647678f` closes the sole initial finding; initial helper/review and fix remain preserved. Pre-restore catalog correspondence states a verification requirement, not completed ZIP verification. Approved restore must subsequently verify all773 recorded original ZIP names and byte hashes, including files already linked. No active-producer cache writes, runtime hooks, source changes, new UID/HOME, account-lock bypass or second automatic attempt are permitted.

This execution's one waiting controller was launched at2026-10-02T13:06:27.760391UTC, PID72755, with a separate actual start receipt. Hard-coded predecessor PIDs are execution provenance; independent serialization review is required before adapting paths/PIDs for another machine. Controller launch alone is not a successful actual replay.

The actual replay command from frozen Coin is:

```sh
PYTHONDONTWRITEBYTECODE=1 TMPDIR=/workspace/scratch/alpha-beta-next/tmp \
python -u -m research.alpha_perp --candidate incumbent --scenario base \
  --risk-calibration /workspace/scratch/alpha-beta-next/registered-calibration.json \
  --restore-prints --out /workspace/scratch/alpha-beta-next/risk-perp-incumbent-retry1.json.gz
```

The reviewed controller owns this invocation; do not run it separately alongside the controller or any other Coin process. It keeps default CNY10000, start offset0, frozen sourceaced and the unchanged global calibration. The complete795 account is consumed by immutable analysis99 and all six evidence fingerprints must exactly equal the original unscaled incumbent before any successful derivation is written. A failure retains the real raw/receipt/log and stops without a projected report or alternate parameter trial.

Only then is `risk-perp-retained4-projection.json.gz` derived from the original five raw accounts. It narrows only `results` and `inputs.candidates` to the four original new candidates, retaining whole rows, journals, source, public input identity, conditions and full original risk profiles unchanged. Explicit parent raw/receipt hashes and whole-row hashes identify this as a lossless projection, never a newly measured producer raw. `risk-perp-repair-projection-proof.json` binds that derivation to the untouched actual incumbent retry. The one-level `risk-perp-repaired-manifest.json` contains exactly those two SHA-bound children. The original raw is not overwritten.

Immutable analysis99 reruns the exact original final command with only its risk-perp path and NEW JSON/CSV/Markdown destinations changed. A usable `registered-final-repaired.json` must have no pending work, every measured account valid, rules freeze ready, both original four-scene baseline proofs and both unity controls passed. Its actual same-stem command/log receipt, source and output hash remain mandatory.

After that success, the externally reviewed `audit_repaired_remaining_registered.py` SHA `8366717a1758ba57998c89baa067a4ef23443ba538222ae1e259bbc00df0fdc5` validates the repaired final/projection/raw contexts and runs exactly two new independent checker audits serially: the retained four and the actual incumbent. It reuses only the unchanged Spot7 and four sensitivity audits with exact raw, receipt, log, checker, calibration, baseline and unscaled bindings. The new `financial-audit-remaining-repaired-index.json` must cover exactly16 identities and the new finalSHA, reconciled with the untouched unscaled48 index. Its operational review SHA `bfa54c92c407db9d7e046ea134fef394b2f5710968f5a96d440dc181ef0b5582` approves the helper, not the unperformed actual audit or adoption. Root uses its default read-only preflight before `--execute`:

```sh
PYTHONDONTWRITEBYTECODE=1 python /workspace/btc-alpha-beta-next/review/audit_repaired_remaining_registered.py \
  --final-report /workspace/scratch/alpha-beta-next/registered-final-repaired.json \
  --out /workspace/btc-alpha-beta-next/review/financial-audit-remaining-repaired-index.json --execute
```

Actual full64 financial review and actual five-account source bridge must pass independently before a separate adoption decision. Keep failed first-attempt reviews and indices distinct from the successful new index.

## Separate canonical Spot runtime and adoption bridge

The minimal shared runtime proposal is Spot `0c52c812301de3712f3637a1ce1b1241de0c40f1`, Python `619570fb7baa586f28ad5de2a440d7752a536cc8f8ce7e357264612e65801537`, based on immutable analysis99. `research.adoption_spot` invokes the shared Model/session/Lifecycle/HistoricalVenue path without AlphaPolicy/configured research hooks. The default adaptive stop uses 4 completed ATR14/close clipped to 10–30%, preserves proven protection floors, and keeps default sizing scale 1. Actual diagnostic calibration affects only new post-cutoff BUY sizing. Persistent Model v5 state guards reject old or malformed checkpoints before recovery; no checkpoint is discarded or repaired implicitly. Existing execution-source equality correctly rejects this changed runtime.

`run_spot_canonical_accounts.py`, SHA `89697d4d22904f5d93db40e19acf89781c1fd7653a4b7115536a749d98266915`, collected exactly five complete accounts serially: base, fee150, slip2, outage and file-calibrated base. Original command/compression receipts and `spot-canonical/canonical-inventory.json` retain every measured identity. The independent `spot-canonical-five-financial-review.md` and proof `c1803ecb6c66a1f6397415ce2b033f569ebca46e6df42419bee87ea45f351b8d` verify all six groups against the original atr-stop four stresses and actual calibrated risk row, and separately reconstruct funds/statistics. This is exact-five equivalence, not global completion or adoption approval.

Only after a valid complete `registered-final-repaired.json` and exact independent global audit coverage may the approved `verify_spot_adoption_bridge.py` SHA `a33daded5ce53ec90d6648a20fba8ba2f9b60906d9733ccde6538bcb6382c549` run. Supply absolute `--inventory /workspace/scratch/alpha-beta-next/spot-canonical/canonical-inventory.json`, the exact proposal `--expected-head` and `--expected-python-sha256` above, `--final-report /workspace/scratch/alpha-beta-next/registered-final-repaired.json`, `--remaining-index /workspace/btc-alpha-beta-next/review/financial-audit-remaining-repaired-index.json`, and a new exclusive `--out`. It binds the final selection, all original audit coverage, full global/project calibration identity, exact-five receipts, source Git archives, six-group fingerprints and changed-path hashes. It emits equivalence evidence with adoption unapproved; independent final review and a separate explicit adoption decision are still required. No generic checker/forward source override is permitted.

If forward diaries bind immutable analysis99, label them as research-source diaries and separately identify any adopted runtime. New runtime proof does not silently relax the old forward source gate. Historical raw measured HEADs remain unchanged after later documentation/integration commits.

## Zero native evidence, charts and byte-preserving archive

The separately source-bound empty native templates are `spot-native-atr-stop-zero-template.json` and `perp-native-incumbent-zero-template.json`. `native-zero-source-binding-proof.json` distinguishes the Spot0c52 template-tool source from the Spot0c52 and Coinaced target execution-package bytes. Actual empty acceptance checks exit2: owner review is not ready and native verification is false. They contain no owner UID/capital/native cases and do not authorize account access. Native cases and actual account-days remain0; templates are not completed native checks.

Research forward initialization must run from immutable analysis99 after the repaired final and independent reviews pass. Bind `--analysis /workspace/scratch/alpha-beta-next/registered-final-repaired.json`, `--kind spot` or `perp`, and a new exclusive `--forward-init` path. The diary uses actual initialization time, CNY10000 cash/BTC0 and no observations. Its execution identity remains research source99/aced, separately from any adopted Spot runtime; do not relax the source gate or backfill completed history. A calendar wait is not an actual account-day.

Charts must use the valid repaired final directly and preserve standalone PNG/SVG plus actual report hash provenance. Passive controls have daily-closing drawdown only and are not finite-session/continuous-drawdown peers. The previous `complete-delivery-20261001` joint allocation accounts used old consensus plus Coin, not the new ATR runtime, and must remain labelled historical.

The separately reviewed `export_registered_diagnostics.py` SHA `921496bd345a166a434b1077ce810fb7d31c012fe7b09e8ae13960e349258dc3` exports all64 identities without recomputing metrics. Its scoped calibration-fix review is `diagnostics-export-calibration-fix-static-review.md`; the original rejected helper and review remain preserved. Supply the actual Spot project and Coin global calibration files: Spot producer metadata does not contain risk profiles. The exporter requires their byte hashes to match the final report, copies their exact scale strings, and rechecks input bytes before publishing provenance. All return, drawdown, volatility and cumulative return-difference columns use fractions, not percentages; risk matching is an upper band, not exact equality. Run only after the repaired final and independent financial review pass, using a new output path:

```sh
PYTHONDONTWRITEBYTECODE=1 python /workspace/btc-alpha-beta-next/review/export_registered_diagnostics.py \
  --assessment /workspace/scratch/alpha-beta-next/registered-final-repaired.json \
  --spot-calibration /workspace/scratch/alpha-beta-next/spot-project-calibration.json \
  --perp-calibration /workspace/scratch/alpha-beta-next/registered-calibration.json \
  --out /workspace/scratch/alpha-beta-next/registered-diagnostics.csv
```

Retain `registered-diagnostics.provenance.json` with the CSV and independently compare its64 rows to the actual accepted report and calibration files. A CSV lacking provenance is incomplete. Exporter review does not approve financial results, prospective alpha or adoption.

The reviewed byte copier `pack_completed_evidence.py` SHA `8ea9f39b233ccedd6d578aa46d64ef0a0d7af03bf8df2c07007d530997c99857` accepts explicit NEW `--final-report` and `--remaining-index` paths above. Use a new absolute output directory outside scratch/review, and explicit reviewed bridge/adoption/zero-event-diary artifacts plus their individual `--required-sha256 ABSOLUTE_PATH=SHA256` bindings. Its operational review is `final-path-adaptation-operational-review.md`, SHA `08693b27ff1f79b9272c43a1cf815252cf5fd655d9425e4ddebbbddd358a481e`. All producers, controllers, independent audit processes and ZIP observer must have exited before and throughout copying. The copier preserves original bytes, maps absolute paths to archive paths, verifies64 audit identities and the unique canonical five, and atomically publishes a no-overwrite `MANIFEST.json` excluding itself. It does not infer adoption from supplied artifact filenames. Retain both original failed and repaired evidence, helper/fix/retraction history, selected small partial snapshots and native-zero results; exclude account State, credentials, market ZIP/BIN cache, decoded inputs and huge completed progress copies. Full reproduction still needs original Git history and official public inputs.


## Actual completion, independent adoption and initialized diaries

The repaired final SHA is `a35ef6727d1a3befa1c86778eadc3bb604ffff3ad2b7cb63275419dc30c9a5d6`; the new16 index is `0d78b9355deb09f7597be3b756aa51c209980188536d186c3b5a72d7dcb6a44e`. Independent `final64-financial-review.md` SHA `b7ba215bdc4b9ad645f6360ea688d15692e4a96c1bb63da53cae3d2bdec6656d` accepts precisely48+12+4 identities. Source and financial adoption reviews are separately retained. The actual bridge SHA `0838fde5cd3f3645f846632f6a5e7e3c3d80ca923d3cd7de48e4292a278aa987` stays unapproved/pending internally; the separate actualUTC `adoption-decision.json` SHA `b44b7c4899021b3238c1968265d5e4b2c9338180fdb70d05dd056f48f041f8fc` authorizes only shared ATR development defaultscale1 and unchanged Coin7.5/3.6. It grants no account action or production qualification.

Both actual forward initializations completed from immutable analysis99 on2026-10-02 at17:17:58.642UTC and17:17:59.131UTC respectively. Each retains same-stem command/log, output SHA, actual start/end and source. To reproduce into new exclusive outputs from that source, run the two commands sequentially:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m research.alpha_assessment \
  --analysis /workspace/scratch/alpha-beta-next/registered-final-repaired.json \
  --kind spot --forward-init /workspace/scratch/alpha-beta-next/spot-forward-zero-init-NEW.json
PYTHONDONTWRITEBYTECODE=1 python -m research.alpha_assessment \
  --analysis /workspace/scratch/alpha-beta-next/registered-final-repaired.json \
  --kind perp --forward-init /workspace/scratch/alpha-beta-next/perp-forward-zero-init-NEW.json
```

Never overwrite the actual delivered diaries. They start allcash10000/BTC0/no observations or fills/native0/accountdays0; immutable99/aced research execution identity differs from canonicalSpot0c52. Changing an initialized source fails the original gate rather than silently upgrading it.

Actual charts use external `plot_registered_assessment.py` SHA `886c6ff4eea3a8703583cb49009c34d7fc709f17f44b774433ff7f9746bf9868`, the repaired report and standard Matplotlib. The only preview repair was figure size/margins; the first helper and preview remain outside the measured source. Both final PNGs were actually viewed through byte-identical layout-corrected previews. `registered-figures.command.json` binds actual CLI/start/end/exit0/report/helper and image byte equality; `figures/figure-provenance.json` binds PNG/SVG bytes to the accepted report. Plot axes use percentages; CSV keeps fractional metrics.

All financial producers/controllers/audits and the ZIP observer exited before final copying. The archive copier executes only after the separate final documentation, decision/diary reviews complete. Its supplied required-artifact hashes bind actual completed artifacts, not filenames or inferred approvals.


The first actual copy attempt at2026-10-02T17:30:12.689990UTC failed before creating its output: `/proc/200/cwd` was inaccessible for unrelated root-owned `dockerd`. Preserve `pack-attempt1-proc-cwd-denied.*` receipts/log and the original722 helper as `pack_completed_evidence_pre_proc_cwd_fix.py`. The scoped `pack-proc-cwd-fix-operational-review.md` independently passes22 synthetic checks and verifies all AST outside `stopped()` unchanged. The only guard change reads cwd only for Python processes; relevant argv still blocks shell launchers, and unreadable Python/metadata still fails closed. No financial rerun, process/UID/HOME/lock bypass or evidence overwrite occurred. Parent path-adaptation review08693 remains applicable to unchanged copy/source/financial/SHA/manifest gates; the scoped review binds the current8ea9 helper. The prior guide690a and documentation review0a22/5e remain retained as the preceding reviewed versions; a scoped final-guide addendum binds this guard repair without changing financial, CSV, figure or adoption claims.
