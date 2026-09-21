# Pancakequant current recovery state

Status: ACTIVE / NOT_QUALIFIED. Economic and production execution work is incomplete.
Communicate in Chinese. Continue existing authorization, not a new project.

## Mandate and Git

Repository ychenracing/pancakequant; branch research/on-demand-btc-20260920.
Latest verified runtime/data commit before this documentation update:
3f79f2f53c3aaaf482e5a39850a5de8470f9ce90. Actual HEAD must be queried on recovery.
Main last checked unchanged: c886b7c63c6455bd7c933269e32cd35a6fb3e09a.
Native Git read works; authorized GitHub connector handles writes. Changed bytes,
SHA256 and complete Git tree were read back and verified. Never restore .transfer
on top of newer code. Preserve meaningful work promptly on this research branch.

Only Binance BTCUSDT USDT-settled perpetual is the target production contract.
One model, one adapter/config, sparse manually/Agent-triggered run_once; no daemon.
Frozen: CNY10000, 2020-01-01 UTC through 2026-09-20 exclusive, CAGR>200%, complete
continuous account MDD<20%, exchange leverage20x, original frozen irregular schedule.
All actual costs/funding/margin/liquidation/collateral exposure count. No weakened
metrics/window, proxy relabeling or leverage escalation. No live trades, transfers,
credentials or real account-setting changes authorized. Do not merge main until
true economics and required safety acceptance pass. A checkpoint is not completion.

## Actual default CLI

python -m pancakequant and main.py now use pancakequant/binance.py, GET-only.
No Bybit construction, old config fallback or other venue selection in default CLI.
Old Bybit modules remain for historical research, not supported default trading.
research/binance_readonly.py was moved, without a compatibility shim.

config.example.json contains only account_uid and state_dir. Credentials are
PANCAKEQUANT_BINANCE_KEY/SECRET. Observation connects Binance real read-only API,
not testnet; no private account has been contacted during this task.

status checks UID, one-way/single-asset/isolated20x/no-auto-add-margin, wallet,
positions, ordinary/algo orders and recent fills with bounded double observation.
Report uses USDT accounting and distinguishes protection existence, liquidation
geometry and entry remainder risk. State directory is account/venue-bound and locked.
run additionally reads exactly120 completed native4h bars with server-time/boundary
validation, then reports blocked because no qualified model/write lifecycle exists.
--execute rejects before credentials/network. This is not completed trading support.

Stable-client-ID query follows conditional actualOrderId, even for canceled parents,
validates child identity/side, and never authorizes resubmission on missing history.
Recent fills are explicitly incomplete history. Full intent recovery, order writes,
protected partial fills, safe amendments, margin adjustment and testnet lifecycle
remain incomplete. Official closePosition TP/SL is not proof of atomic entry protection.
See evidence/binance-linear-feasibility-20260921.md, binance-api-chronology-20260921.json,
binance-intent-query-20260921.md. Preserve prior correct execution/risk semantics
when implementing the actual Binance lifecycle; no favorable metric-driven reversal.

Verification:120 full offline tests passed before CLI/market changes. Then12 affected
CLI/adapter/intent checks passed;4 affected market/CLI checks passed;5 affected
collector/market/CLI checks passed. Reuse results, do not claim a new full-suite run.
Current simple CI run35568398097 at3f79f2 last seen queued. One Python3.13 job,
10min, no secrets, no optimization; temporary acquisition/upload hooks removed.

## Native Binance data: full market coverage now verified

Official BTCUSDT onboardDate2019-09-08 precedes frozen start. Current instrument
metadata is not a historical risk/fee/filter timeline. Native monthly/daily originals
are unmodified, with exchange SHA256 checksums and ZIP CRC verification.

Complete audit:58,896 trade hours,58,896 mark hours,7,362 funding settlements.
No missing/duplicate/out-of-window hours after native supplements. Funding actual
millisecond offsets retained (3,296 nonzero,max47ms). See
 evidence/binance-native-coverage-20260921.json.

Monthly mark files lacked216h, including a24h month-end hole missed by internal
continuity checking. Six official markPriceKlines API responses restore exactly
those gaps, never replacing existing archive rows or interpolating. Raw6pages plus
URL/hash receipts: evidence/binance-mark-repair-20260921/. Missing sets and original
receipts: evidence/binance-mark-gaps-20260921.json and binance-mark-boundary-gaps-20260921.json.
Collector now validates period boundaries as well as internal hourly continuity.

Restore original archives from these durable sources; do not redownload:
- Initial75: Library libfile_2a68f05223408191b0f115aff601c93f,
  PANCAKEQUANT_BINANCE_NATIVE_PARTIAL_20260921.zip,1,637,860bytes,
  SHA2565ca1555d37fb4549b3ead4d61415d15500612aac6d01222b92f638c2ab580656.
  Receipt evidence/binance-partial-originals.json; physical inventory/audit beside it.
- Next199: Library libfile_ff11258400548191a698659cad84933c,
  binance-native-remainder.zip,3,349,763bytes,
  SHA2565885db22836f20fcb3582df1faf8495b3fd3c38392cd6445445bd3277a80388c.
  Run35566270075/artifact10623839632,117 hosted tests passed;4semantic data failures.
  Receipt evidence/binance-remainder-result-20260921.json.
- Four gapped originals: Library libfile_9caad5300ce881919da75dd17c284395,
  binance-mark-gaps.zip,83,138bytes,
  SHA256fa8f5344769b188a562fb231fcb444321232777f2cc0b86355726887dd41ccc5.
  Run35567111349/artifact10624731223; failure is accurate semantic rejection.
- Sep funding tail57events and December2019 trade744h/funding93events are saved
  in evidence/binance-boundary-20260921/. Warmup mark beginsDec23, not fabricated.

Full market coverage is not native qualification. Dated fees/risk/filter rules,
USDT valuation and funding settlement-mark accounting remain unresolved.
A new official funding API probe returned the earliest1,000 native funding events
but all1,000 markPrice values were empty. Do not fetch all remaining pages hoping
to solve early mark valuation. Raw original is Library
libfile_ed7f7d619fb88191844e84635e1d4ee7, binance-funding-mark-probe.zip;
receipt evidence/binance-funding-mark-probe-20260921.json. Never relabel hourly
close as exact settlement mark. A conservative interval valuation would require
explicit bounds and limitations, not an exact cashflow claim.

## Economic candidates: all rejected, no validation tuning

- Original inverse result: almost all USD growth was BTC collateral beta;
  BTC-unit CAGR0.283%, multiple1.01917. Attribution evidence preserved.
- L1/L2 hypothetical linear on Bybit market proxy: development CAGR0.583756% /
  -1.096052%, MDD1.355090% /15.974647%; L2 has297entries,244stops,5liquidations.
  Rejected; do not tune neighboring stops/scores or escalate risk.
- L3 expanding causal four-day ridge on native Binance development:437overlapping
  observations,correlation-0.0161721,mean directional net-0.434740% vs long+0.0884211%.
  Failed preregistered gate. Exact code/hypothesis/identities/observations in
  evidence/l3-development-20260921/. No adjacent ridge/horizon/feature tuning.
- L4 native taker-flow continuation, preregistered at a6712e6263be0bfbb91e89a92350870cb8af7603:
  466observations,correlation0.0259375,mean net-0.332363% vs long+0.0672466%.
  Failed gate; no sign reversal/lookback/threshold tuning. Exact originals in
  evidence/l4-development-20260921/.

L3/L4 are overlapping forecast diagnostics, not trades, account CAGR or MDD.
Funding rates summed as approximate return; fixed proxy costs explicitly disclosed.
Development2020-2023 only;2024-end was inspected solely for data integrity, not
model selection/economic validation. No current alpha has earned full qualification.

## Continue

Native market collection is no longer a blocker. Build the Binance account replay
with explicit honest funding/rule/collateral treatment, and a causally specified
structural alpha candidate rather than more adjacent L1-L4 tuning. Complete real
Binance protection/recovery lifecycle, preserving no naked re-entry and unknown-write
semantics. An actual testnet lifecycle remains unverified without an authorized
account; do not silently contact live accounts. Keep main unchanged until gates pass.

## Bybit baseline, refinement and rejected directions (retain evidence)

Native BTCUSD original is already durable on evidence/native-btcusd-20260920 at
230f9d60361bfec144d066c5684b5c3b96f996bb, path
evidence/native-btcusd-history-6f5ba384.zip, 4,679,317 bytes, SHA256
717841c3267f5de40d0c0b103aeff3c067054eb7752ccf5b8cc1bcad11228159.
83 shards, 59,400 hourly rows, 7,425 funding rows; no integrity errors. Do not
reacquire complete Bybit history. Conservative historical rules remain proxy:
evidence/historical-rules-research.md and proxy-rules-conservative.*.

Exact old baseline reproduced: CAGR 43.920748%, MDD 77.051193%, 8 liquidations,
537 fills, 795 invocations, max gap 151h. Absence stress remains failed. Original
reports: evidence/proxy-diagnostic-20260921.*. H3, H4, M1, risk escalation and
stop-first upper bound already failed; see structural-research/candidates evidence.
Do not resurrect them as economic candidates.

Minute task 35559122193 artifact 10622037487 is already recovered and saved.
8 complete native days, 11,520 minute rows, exact hashes/CRC/hour reconstruction.
Original 729,363 bytes, SHA256
7cf97ac730953674d7da9f503eddf0d16470b7fd3fa885d5ab16b4ace098580f,
durable 23 parts under evidence/ambiguous-minutes-20260921/.
Six stops resolve earlier than liquidation; two same-minute ambiguities remain.
Full refined replay: CAGR 44.121475%, MDD 77.049869%, final CNY 116538.70,
2 liquidations, 537 fills, 795 invocations, identical schedule hash. It confirms
ordering is not the main economic failure. See native-minute-ordering and
native-refined-baseline JSON and continuation-results-20260921.md.

OKX is no longer a production candidate. Run 35559716288 completed with failure:
both official hosts returned empty 2020 mark/funding, while trade and end pages
worked. All 15 raw/report files are under evidence/okx-boundary-probe-20260921/.
Original ZIP SHA256 fddc78d56d85f7b6fb382a6d3a85923c0da6a7e2a1fd9bb53c4ba0661de75c15.

## Other durable full originals

- evidence/native-refinement-originals.json: full baseline/refinement traces,
  exact measured sources and L1. ZIP 21,825,726 bytes, SHA256
  9985156a6c37bf733de49b0f162a0fddc9994a685a24b614f1062488d13105cd,
  Library libfile_4d0b56787e048191b3754decb32b983c.
- evidence/l2-boundary-originals.json: full L2 traces/exact source, OKX ZIP and
  Binance boundary ZIPs. 1,349,536 bytes, SHA256
  2d26c0a3b15827ce73297999e7a6562291c4b6853c26168dbbfd37f303525314,
  Library libfile_ba354742cd748191a65d34dd04515224.

Original refined replay preceded a later continuity guard; exact measured source is
inside its evidence archive. Do not mislabel a reused result as a fresh run of later
code. Preserve new meaningful evidence promptly, verify remote identities and keep
working on the same research branch. No task-completion claim is justified yet.


L5 preregistered at59a73abc4fa33d5443614b4313ad44cfc2321acb then measured and rejected: online Bayesian change-point drift,467development observations,364active,correlation-0.00601996,mean net-0.197441% vs constant-long+0.0710532%. Forecast diagnostics only,NOT_QUALIFIED,no2024+validation. Exact source/hypothesis/observations/result in evidence/l5-development-20260921/. No adjacent hazard/prior/cost-threshold tuning or signal reversal. The one targeted posterior-update/symmetry check passed.

L6 native channel-persistence account diagnostic measured. Corrected latest development CAGR2.43722%,conservative continuous MDD6.47025%,final CNY11011.13,22entries,21stops,1liquidation,468original invocations. It passes the preregistered positive-return/sub20%development screen but is nowhere near final CAGR>200%; NOT_QUALIFIED,2024+unused. Corrected funding ordering removes future within-hour mark influence on earlier opening checks; exact-hour funding uses opening mark. Entry/exit events and allinvocations match the initial run. Full old/corrected sources and traces are durable; receipts under evidence/l6-development-20260921/ and evidence/l6-corrected-development-20260921/. Initial attribution:22closedtrades,10winners,mean562.36holding hours,mean unweighted signed underlying trade return9.93%; these are not leveraged account returns. No channel/reward/risk/leverage parameters changed in correctness repair.

L7 persistent channel state measured: development CAGR4.86330%,conservative MDD11.36320%,72entries,2liquidations,468invocations; paired progression gate passed, final economic target still far away. Exact full originals Library libfile_5b982c646b348191a1e0d2c571db6002; receipt/result in evidence/l7-development-20260921/. L8 now preregistered in research/linear-l8-hypothesis.md: current-equity stop-risk reallocation at manual triggers, unchanged0.006risk/2xcap/20xsetting/channels/costs. research/native_channel_replay.py contains L8; older exact sources remain archived. Three targeted resize-accounting/state checks passed. Measure L8 once, preserve result; no2024+validation.

L8 measured and rejected: development CAGR3.59120%,conservative MDD12.43447%,72entries,215adds,160reductions,17liquidations,468invocations. Fees51.298USDT versus L7's28.867USDT. Failed both paired objectives; no risk/cap/channel tuning. Full originals Library libfile_dbe5691260688191b5c954a260ed9479,receipt in evidence/l8-development-20260921/. L7 is the better current development baseline,not a qualified production candidate. Active research/native_channel_replay.py contains rejected L8 for reproducibility; exact L7 source is at6152f426b2e6746cfa0db9c18941307e257aa9cf and in its original archive. None of L6-L8 used2024+economic validation.

Rule qualification clarification: the reused hypothetical BTC lot0.0001 and fixed rule constants are NOT established conservative bounds on historical Binance execution. Only market inputs are native. Fee/funding/mark-envelope stress assumptions do not make unverified quantity/minimum/risk rules native or uniformly conservative. Do not promote any of these development figures as production-feasible economics. Close historical rules/USDT/execution gaps before formal validation; do not silently backfill current instrument rules.
