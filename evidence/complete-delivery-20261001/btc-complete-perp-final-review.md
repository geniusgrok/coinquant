# Independent final review: 28 perpetual accounts, exclusive derivative, budget source

Verdict: **APPROVE the 995 original as the preserved measured account, the explicitly labeled 3213 exclusive-terminal derivative for protocol reporting, and budget implementation source 3213.** No unresolved implementation/ledger/selection finding in this reviewed scope. Actual three-budget completion remains pending and is not approved by this source review.

## Identity and scope

Original: `evidence/complete-delivery-20261001/perp-accounts.json`, 55,218,104 bytes, SHA-256 `55aa8ba0d8e54d572907a5d57cc557face20a0ce6666692d526df37387585423`. Execution source `995d0530889d8b609f41218b6904ff55499fd578`, clean recorded Python digest `5a1497a18004fce43827c68d80673300004b0cbb505d5106c4ee29cc63c995b3`. Independently reconstructed that digest from Git object bytes, verified protocol SHA, frozen schedule identity and FX bytes. The original raw was not changed.

New implementation/derivation source: `3213cddb904b745193c5a27c06c42ec3a3ae2f93`, Python digest `782333a4bea85ac7f1a86050a28072eef2dda77b53ea8dd1b5a00cf42a69331a`. Reviewed exact diff from 995: budget accounts/initial metric peak, research-only exact-END funding exclusion, explicit derivation helper, September funding restoration and focused tests. Production campaign, sizing, execution and permission paths are unchanged.

Independent raw evidence:

- `/tmp/btc-perp-independent-audit.json` and `/tmp/btc-perp-independent-audit.py`
- `/tmp/btc-perp-funding-audit.json` and `/tmp/btc-perp-funding-audit.py`
- `/tmp/btc-perp-short-review.json`
- `/tmp/btc-perp-exclusive-independent-audit.json` and matching `.py`

No account calls, network calls, repository edits or subagents were used in this review.

## Independent original-account audit

All 28 accounts passed separate reconstruction rather than trusting stored `audit.passed`:

- Exactly 795 session indices and starts match the frozen schedule. Every final cleanup is `verified`; unresolved executions are zero. All account paths complete/known, no failure. Exposure-increasing fills fall within session/cleanup envelopes, and no individual fill reverses through zero into an opposite position.
- Trade IDs and income IDs are unique. No trade is at or after exclusive END. Only the four slow-trend accounts contain one exact-END funding debit each.
- Quantity, weighted entry, realized P&L, fees at scenario-specific actual rates, cumulative wallet, funding, marked equity, CNY conversion, signed/gross exposure, and final account all reconcile independently. No external cashflow class appears.
- All accounts contain exactly 2,454 consecutive daily observations. Every daily quantity/wallet/equity/fee/funding observation was checked against reconstructed fill and cash histories. Daily stamps are closing boundaries; the source records midnight funding at that boundary while a trade timestamped at the next day's opening minute belongs to the next day. The terminal derivative removes the out-of-window last funding event explicitly.
- Independently verified **33,036 funding payments at 3,471 unique settlement timestamps** using quantity reconstructed from preceding fills, the actual official settled rate, preceding completed official mark close and `payment=-quantity*mark*rate`. All loaded mark file hashes match the original account manifest.
- Each continuous conservative mark-envelope MDD is at least the independently reconstructed daily MDD, is no smaller than its reported close-path MDD, and has a maximum timestamp strictly before END. Zero liquidation and zero missing-mark isolated forfeiture are recorded across all 28 accounts.

The independent audit does not rerun the entire minute/print continuous drawdown path. It reviews the accepted meter source, original recorded conservative envelope and its bound metadata, validates ledger/daily consistency, and confirms the terminal derivation cannot alter the maximum. Neither this audit nor the proxy meter establishes native continuous price-path observation or native protection qualification.

## Shorts were actually executed

Every conditional-short scenario has **13 distinct short episodes and 43 negative-position daily observations**; every other candidate has zero short episodes/negative days. All 52 scenario-specific first short entries were independently replayed against completed four-hour/daily model inputs: each has the original negative impulse, close below completed SMA60, five-day-declining SMA60, and a stop above first short fill.

Each scenario has six short exits outside any session envelope. Every one is a BUY flattening the existing short, matching its original stop rounded upward to the 0.1 tick; trigger-slip adds exactly the adverse 0.0015 multiplier. No opposite exposure opens before flat. These are actual proxy-exchange protection events in the raw, not merely a direction flag or imagined client decision while stopped.

Example: base short begins 2020-03-16 03:00:11.660, original impulse identity 1584014400000, stop6718.14 rounded6718.2. BUY flatten occurs outside a session at 2020-03-20 08:19 for6718.2; trigger-slip counterpart fills6728.2773. The four conditional-short conservative MDDs are about65.33–67.62%, so real short execution does not make this candidate eligible.

## Exclusive-terminal derivative

`perp-exclusive-accounts.json` (55,230,558 bytes, SHA `15dd7bfc242d52bf692663179cd1e3867418f8b55a4cad0894d253a8b296f00a`) keeps execution source995 and separately records clean derivation source3213. Every original row digest and the original full-artifact SHA match independently.

Only slow-trend's four exact-END funding debits are removed: base−2.9647344, fees−3.1271856, read400−1.68136992, trigger-slip−2.82665088 USDT. There are no END trades or other END income types. Their removal increases only terminal wallet/equity and changes cumulative funding, terminal daily observations, CAGR, funding-event count and the rederived audit. All earlier daily rows, all trades, all session execution/protection summaries, position, final mark, fees, continuous MDD values and maximum timestamps are identical to995. The other24 accounts' economic content is entirely identical.

The helper refuses terminal trades, other terminal cashflows, nondebits, events after END or missing/pre-END drawdown proof. Since the changed event is a debit after all execution, removing it cannot change earlier fills/protection or increase an already earlier maximum drawdown. All28 derived accounts independently pass the full cash/daily audit again, with zero income events at/after END.

## Frozen selection

Independently recalculated the protocol inequalities with Decimal thresholds. No candidate qualifies; selection remains **incumbent**, and no-macro remains attribution-only. No production or native promotion occurs. Incumbent base remains about119.23% CAGR /44.11% conservative continuous MDD. Tail sizing improves base drawdown but fails matched stressed-return retention; conditional shorts fail the MDD bound. Economic150% target remains unmet; failure of improvement candidates does not justify changing the preregistered rules.

## Budget implementation and 10,000 equivalence

Budgets2500/5000/7500 create independent incumbent/base exchange and state instances with correctly budget-sized initial wallets and initial metric peaks. CAGR denominators use each account's own initial CNY. Each account goes through actual session/Lifecycle and its own cash audit; outcomes are not scaled from10000. Exact-END funding suppression is confined to research finalization, with no production change.

Independently compared `/tmp/perp-equivalence-old.json` (172,303 bytes, SHA `81c21f9f60808fbcd89f8a6575324be4d09c3dd29a13b43773a58a6ca5e60dbe`) and `/tmp/perp-equivalence-new.json` (172,975 bytes, SHA `df945e07a4dde2d670601b38e89c781df15412a87326ba064d45a70cce076adb`). All28 account dictionaries are exactly equal after removing new explicit `initial_cny=10000`; all conditions, selection and nonsource input identities are equal. Each case completed three actual sessions, including two incumbent/base fills. The comparison script verifies its saved995 module bytes against Git and that shared core code is unchanged before using old identity. This is a concrete three-session equivalence proof, not a claim of new-source full-window execution.

September restoration adds the official September funding monthly object and checksum independently of the price-month list. Price input remains frozen at September19 daily archives; no September20 price extension is introduced. Missing required funding files fail closed; existing loaded market inputs in the10k equivalence are identical.

Ran `python -m unittest tests.test_complete_perp`: **11 passed**. Integration reports its broader346-test pass separately. Actual completed three-budget raw, finance/ownership/daily audits, final documentation and corresponding-head CI still need their own completion checks.

## Final actual-budget and delivery review: APPROVED

Final reviewed integration head: `bfadeaeee62dd28bf69c1a8872bd901acf9fadf2` (PR56). This head adds only retained evidence/documentation after already reviewed runtime source3213. No repository files were changed by the reviewer.

Independently verified actual `portfolio-perp-accounts.json`: **5,872,835 bytes**, SHA `eddf564178aad45efd9a3aac20e02fc757a0196008f4c083963621ac43a1bd8a`. Recorded clean execution source3213 and its Python digest were reconstructed from Git bytes. Source/protocol/FX/schedule/crowding/market identities match the earlier exclusive account; every used minute/print file digest agrees with the original manifest.

All three actual accounts pass independent reconstruction from their own starting capital: exact795 session indices/starts and verified cleanup; zero unresolved executions or failed/unknown paths; fill identity/direction/weighted entry/realized P&L; scenario commissions and funding; wallet and marked USDT/CNY equity for each of2,454 consecutive daily records; signed/gross exposure; final flat quantity; zero terminal or external cashflows. This check does not reuse the implementation's audit result as the test oracle.

Additionally verified **2,763 actual funding payments** directly from pre-settlement fill-derived position, official settlement rate and preceding official mark close, plus **906 held-day closing marks** (302 per account) against official historical minutes. Loaded mark hashes agree with raw inputs. Recomputed each CAGR from its own initial capital. Daily MDD is below each reported conservative continuous MDD; no short exposure, liquidation or missing-mark isolated forfeiture appears.

| Initial CNY | Final CNY | CAGR | Continuous envelope MDD | Fills |
|---:|---:|---:|---:|---:|
| 2500 | 1,013,388.529125648 | 144.4211402% | 44.0900078% | 932 |
| 5000 | 1,642,401.474402754 | 136.8896634% | 44.1082534% | 1367 |
| 7500 | 2,154,872.144727825 | 132.2156361% | 44.1049269% | 1751 |

The differing trade paths/fill counts and nonproportional terminal wealth confirm these are actual capital-dependent replay outputs, not scaled10000 curves. They retain incumbent/base labels and do not replace the registered10000 selection criterion.

Final manifest: all **10** retained JSON payloads independently match byte counts and SHA-256, including untouched995 original, explicit exclusive derivative, crowding, both small default-equivalence originals and budget raws/summaries. The manifest excludes itself and progress files. Summary values agree with full raw. Archived old/new equivalence files retain the previously independently verified hashes.

`RESULT.md` numeric claims, feature-coverage counts, candidate rejection explanation and terminal correction match the raw. It distinguishes real-session proxy execution from native qualification, base-only joint controls from unverified combined pressure/continuous drawdown, historical attribution from prospective alpha, and smaller-capital sensitivity from the original economic target. No claim exceeds this evidence. `git diff --check 3213cdd..bfadeae` passed.

Additional independent audit artifacts: `/tmp/btc-perp-budgets-independent-audit.json` + `.py`, and `/tmp/btc-perp-budgets-market-audit.json` + `.py`.

**Final spec + quality verdict: APPROVE for normal PR integration; no remaining material review finding.** Corresponding-head CI success for run36942570634/headbfadeae was supplied by integration; this read-only local review did not make a remote CI query. Native qualification remains NOT_QUALIFIED and the original10000CNY150% target remains unmet. No further budget rerun is needed for this review.
