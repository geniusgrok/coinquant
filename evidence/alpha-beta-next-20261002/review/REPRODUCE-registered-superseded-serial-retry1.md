# Corrected operating condition

The attempted parallel sensitivity queue was RETRACTED after both processes collided on the global Coin account lock for synthetic UID12000. Separate print/state directories do not isolate `Path.home()/.local/state/coinquant/account-locks`. Preserve the original failure logs/progress and the retraction/lock-check proof. Run entire Coin processes strictly sequentially whenever their synthetic account identities overlap; do not delete/bypass safety locks, change HOME, or treat interrupted progress as complete results.

The full Coin20 matrix was restarted on the SAME frozen source into `perp-singletons-retry1.json.gz`; old files remain untouched. Current actual orchestration is `run_registered_followthrough_serial_retry1.py`, SHA30ac30a3045311aebe73263f67b4fc9ea43e84aab889c3efb76996c32ea17692: exact original serial queue with only the new full-output path, known retry PID32321 waiter and new exclusive `sensitivity-serial-retry1-*` labels. All economic case tuples, virtual timing, source identities and checks are unchanged. Historical v1/v2 and their receipts remain retained as operational evidence, not recommended parallel instructions. Fresh reproduction must use its own actual producer PID, new paths, and strict serialization. The historical reference guide below describes the unchanged financial protocol; superseded parallel statements do not authorize overlapping Coin processes.

# Reproduce the registered BTC alpha/beta study

This guide describes the immutable historical measurement commands. It is not a status ledger or native execution authorization. Final measured artifacts, selection, rejections, review and source manifests belong in the completed delivery report. Use PROJECT_STATE.md and HANDOFF_PROMPT.md for task recovery.

The registered account window is 2020-01-01 through 2026-09-20 UTC exclusive, CNY10,000 without additions, BTCUSDT only. Original795 starts,300-second sessions/5-second polls, prior-date FX and .001 conversion each way stay unchanged. Spot is long/cash; Coin retains one-way isolated funded protection. Only installed venue protection acts while stopped. Spot OHLC and Coin minute/volume/mark-gap bounds remain historical proxies. Native cases and actual account-days are zero. Do not substitute a daily signal backtest, omit failed cases or choose a different schedule/capital from the diagnostic probes.

## Exact sources and layouts

Historical producers are Coin `acedaa43ca94223f24e2fe11851bbef74e032a69` / Python `a6e3f30f02208ff7e604b6181c5d8fa7000fe7e30dbc3276fbcc93ffbb0ad227` and Spot `8ca002522fbdce531dcfbbb783ff4d152a7fd66c` / Python `0df8c537ee8d47db6e841778e8e37eac847e1a0c1151e379440081b9473ae026`. The evaluation-only corrected assessor is Spot `32ab1bb546bde064e641c4a2eb5ed4248e590acb` / Python `03704225d82b4a70f7a7c22228cde80f18286961c08981506d058087b8f7fefd`. Preserve those historical identities even if integration changes current HEAD.

Use detached worktrees from retained Git history and a mirrored sibling layout: `coinquant/`, `spotquant/`, `starquant/`. Star supplies only the frozen public historical FX file `data/usdcny_frankfurter.json` (SHA `67606315ea34c0301e0129ac8fc27056099986d9fbd58a552a07f140cdd05bb5`); it is not a third trading runtime. Run the assessor in a separate Spot evaluation worktree with siblings pointing to the frozen Coin and FX sources. Runtime/research Python must be clean committed source. Never edit producer Python, registered spec/protocol or producer HEAD while a queue runs.

Spec SHA `8228013f4ac41affb65162c1cabad8f51b5ef32b9607f62231a4776168a337d0`; protocol SHA `4ae09ae0bc9224f8028ddcc1373dc1bbc7251a70be2945e5655f5e5fa12eb27e`. The source proof excludes only Spot `research/alpha_assessment.py` from execution equivalence, while the complete assessment executable independently binds the final report. There is no runtime/source override.

Use existing official public archives at `/tmp/coinquant-market` and `/tmp/spotquant-market/klines`. Official adjacent CHECKSUM bytes verify each archive; `public-archive-preflight.json` records the initial local snapshot. Coin `--restore-prints` restores and SHA-verifies official daily prints on demand in the task-owned bounded `/workspace/.btc-third-round-prints` cache. All Coin commands using the same cache must be serial. The reviewed parallel queue uses a distinct task-owned incumbent-sensitivity-prints ZIP/bin cache for its four sequential mandatory incumbent probes; official basename/content identities and simulated timing stay unchanged. Retain consumed-file SHA manifests even after rolling cache eviction. This does not authenticate native fills or order-book liquidity.

## Full registered singles

Choose new exclusive output paths and a task-owned TMPDIR on a filesystem with enough space; never overwrite old artifacts. The standard-library runtime needs no package installation. From frozen Coin:

```sh
TMPDIR=/workspace/scratch/alpha-beta-next/tmp python -u -m research.alpha_perp \
  --restore-prints --out /workspace/scratch/alpha-beta-next/perp-singletons.json.gz
```

This measures five fixed candidates × four stresses in the same chronological tape pass. From frozen Spot, measure each of the seven registered candidates in all four stresses, using the retained `run_spot_registered.py` wrapper and its exact expected HEAD:

```sh
python -u /path/to/run_spot_registered.py \
  --repo /workspace/btc-alpha-beta-next/spotquant \
  --output /workspace/scratch/alpha-beta-next/spot-singletons \
  --expected-head 8ca002522fbdce531dcfbbb783ff4d152a7fd66c \
  --tmpdir /workspace/scratch/alpha-beta-next/tmp
```

The wrapper bounds memory to four candidate scenes/two isolated workers, preserves original JSON bytes through deterministic lossless gzip, checks roundtrip SHA, and writes a one-level account manifest. Its output manifest retains each contributing original compressed raw SHA; do not assemble a new bundle with relabelled source. Partial smoke/progress files are not complete economic evidence. Spot outage has789 starts; all other primary cases have795.

## Calibration, combinations and robustness

From corrected evaluation Spot, consume all48 cases and the exact approved baseline originals:

```sh
python -m research.alpha_assessment \
  --spot /workspace/scratch/alpha-beta-next/spot-singletons/accounts-manifest.json \
  --perp /workspace/scratch/alpha-beta-next/perp-singletons.json.gz \
  --baseline-spot /workspace/btc-alpha-beta-next/spotquant/evidence/complete-delivery-20261001/spot-consensus-corrected.json \
  --baseline-perp /workspace/btc-alpha-beta-next/coinquant/evidence/complete-delivery-20261001/perp-exclusive-accounts.json \
  --out /workspace/scratch/alpha-beta-next/registered-unscaled.json \
  --calibration-out /workspace/scratch/alpha-beta-next/registered-calibration.json
```

Immutable baseline SHA pins are Spot `cf075b86ba5df590e078a7c626c53cb20937be955cfb6ad8d41eae19b78645e8` and Coin `15dd7bfc242d52bf692663179cd1e3867418f8b55a4cad0894d253a8b296f00a`. The earlier failed Spot `spot-accounts-final.json` is not this baseline. Every scene compares financial/fill/daily/ownership/operating/remaining-original evidence; synthetic client-ID spelling normalizes relationally and archive bytes normalize only after recorded proof checks. Actual prices, quantities, times, cash, status and clocks do not normalize. Any baseline mismatch stops the queue.

Calibration uses actual2020–2021 USDT daily returns only. Fixed scales apply to new sizing from2022; owned committed positions are not retrospectively resized. Profiles bind original raw/manifest bytes, spec and cutoff. Actual reruns are required for all ten legal new-candidate risk obligations plus both baseline unity controls; invalid unscaled bases retain explicit rejected/inapplicable obligations and no fabricated profiles. If every profile is legal, run frozen Spot/Coin with `--scenario base --risk-calibration /path/registered-calibration.json` (Spot `--workers 2`; Coin `--restore-prints`). Otherwise run each legal candidate separately and retain an explicit manifest. No risk claim can come from rescaled/spliced equity curves. Achieved2022+ vol/beta limits are separately checked.

Selection is deterministic on the unscaled four paired stress scenes. All independently eligible compatible components form the only permitted combination; two core modes are exclusive under the frozen rank/tie rule. Zero components means not applicable; one reuses its existing measured singleton. Two or more require new actual all-four-stress `--combo comma,separated,components` commands on each frozen producer. A rejected combination retains the best eligible singleton. No subset grid is allowed.

After exact combination selection, independently replay incumbent and final selected Coin candidate at each fixed tuple `(CNY9900,offset0)`, `(CNY10100,offset0)`, `(CNY10000,offset−60000ms)`, `(CNY10000,offset+60000ms)`, base only. Use `--candidate NAME` (or exact `--combo` for a selected combination), `--scenario base --initial-cny VALUE --start-offset-ms VALUE --restore-prints`. Deduplicate only if incumbent is the final selected candidate. These are robustness diagnostics, not optimal capital/schedule choices.

`run_registered_followthrough.py` retains the exact one-shot command queue used for this delivery, including expected heads, immutable baseline gates, profile inventory, conditional combos, fixed probes and final `--final` assessment. Its original fixed `/proc/21612` waiter identifies this session's original Coin producer; for a fresh reproduction, wait for the actually launched producer and its exit rather than reusing that numeric PID. Review/update only orchestration paths/waiter before launch and record the new controller SHA. Do not change economic parameters, measurements, sources or output identities. Every subprocess command/cwd/start/wall/exit/log/output SHA is separately recorded. The queue stops on unknown command failure, source change or baseline mismatch and preserves prior evidence; it performs no adoption or forward/account action.

## Interpretation and forward evidence

Keep raw account CAGR for goals/selection: Coin365.2425-day original convention; Spot365.25-day convention, both exact registered interval. Shared descriptive daily CAGR/sample annual volatility/regression arithmetic annualization use365.25 and are labelled separately. USDT terminal metrics use `final_usdt`, CNY use `final_cny`. Report closing MDD beside the declared continuous proxy MDD, costs/funding, calendar2026 partial, concentration, CNY FX and USDT BTC regressions/capture/ES. HAC7 intervals are descriptive and do not correct the research selection. Post-event5/20-day price diagnostics are not attainable missed profit or inputs to actual decisions. This previously studied history is not clean OOS or prospective alpha proof.

After independent full financial/source review and source-bound final report, `alpha-forward-GUIDE.md` describes all-cash initialization at actual UTC with zero observations/days. Append only later observed latest completed public bars with preserved receipts/SHA, never backfill or fake elapsed account days. A diary is public observation evidence, not strategy fills or native trading qualification. Default adoption requires separate reviewed executable equivalence; the measurement queue does not adopt automatically.

For this execution, sleeping v1 was stopped before any economic command and replaced by the scoped-reviewed `run_registered_followthrough_parallel_sensitivity.py` (SHA82ab032036359d064c60f172a978d78fac577ca07007e7539d888f2c69f01128). Its only change is the timing/cache location of the four preregistered incumbent probes, which run serially in their own empty marked ZIP/bin root while main matrix work continues. Main/risk/combo/final-selected Coin work remains serial in the original root. Retained stop/registration/operational review and individual command receipts document the change. No sensitivity tuple, economic parameter, source, rule, selection, virtual latency or gate changes; the completed incumbent Future is consumed once, including dedup when incumbent remains selected.
