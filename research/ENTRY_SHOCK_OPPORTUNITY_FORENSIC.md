# Entry-shock continuous pair: opportunity and cost attribution

**Decision remains reject.** This is a read-only attribution of the one completed
795-session simulated baseline and frozen entry-deferral wallet, not another run
or a native-account observation. Both receipts passed the producer's financial
audit. The script below independently rebuilds every flat-to-flat inventory and
cashflow from fills, order IDs and durable `settled_entry_campaigns` in each
wallet's SQLite. It assigns sells and funding to the owned campaign, matches
campaigns **only by durable opportunity identity**, verifies all positions flat
and reproduces both terminal wallets to decimal precision. Order IDs, exact
manual starts, individual campaign amounts and private files stay local.

| Matched opportunity group | Baseline → candidate campaigns | BUY print change | SELL print change | Filled add-order change | Fee change | Funding paid change | Net campaign cashflow change |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Removed macro opportunities | 2 → 0 | −11 | −2 | 0 | −27.95 USDT | −2.24 USDT | +894.01 USDT |
| Same 48 opportunities | 48 → 48 | +115 | 0 | +10 | +764.23 USDT | +1,081.98 USDT | +7,161.63 USDT |
| **Complete wallets** | **50 → 48** | **+104** | **−2** | **+10** | **+736.28 USDT** | **+1,079.75 USDT** | **+8,055.64 USDT** |

The complete-wallet trade count therefore rises **1,561 → 1,663**, or +102
prints. This is not 102 new entry decisions. Of the +104 net BUY prints, **+99
are from add orders** and +5 from opening orders. Filled opening orders fall
50 → 48, one per distinct campaign in each wallet; filled add orders rise
130 → 140. All 30 original primary opportunities are present in both paths;
their BUY print count alone rises **+102** and their filled add orders **+9**.
The macro group contributes +2 BUY and −2 SELL prints, hence zero net fills.
Only two shared opportunities enter in a different manual session. All 48
shared exits fall in the same interval between manual starts in the two paths;
14 baseline and 12 candidate exits occur outside the 300-second start window,
so these intervals are not called active sessions. Exit time and quantity can
still differ. No duplicate opening of an owned opportunity,
foreign-position overlap, unreconciled intent, or commission/funding double
charge was found. The original baseline itself has one filled opening order and
one closing order per campaign, with 130 legitimate filled add orders.

The added costs come from path-dependent quantity. The candidate has **22 fewer
funding events** but pays **1,079.75 USDT more** funding; fee and turnover each
rise 4.8153% because the same taker rate applies to more notional. The primary
group supplies +667.55 USDT of the fee increase and +1,010.37 USDT of the
funding increase. The two removed macro losers save only 30.19 USDT of fees
plus funding. This is the candidate's sizing and add-on cost, not evidence that
current `main` misattributes fills or duplicates orders.

## Why 2023 and 2024 annual returns weaken

Grouping by original campaign **entry year**, without pairing trades by nearby
time, the 11 opportunities entering in 2023 gain +4,839.53 USDT net under the
candidate, while the seven entering in 2024 lose −1,375.12 USDT net. The 2023
group's gross exit-minus-entry cashflow improves +5,661.52 USDT but spends
+364.35 USDT more fees and +457.64 USDT more funding. The 2024 group's gross
cashflow worsens −883.79 USDT and adds +156.85 USDT fees and +334.48 USDT
funding. Five of those seven opportunities worsen, two improve. The original
2024 model entries and exits remain present; two more filled add orders and
larger quantities on several losses account for the adverse cohort result.

The two paths are separately compounded wallets, so cohort net cashflows do
not equal calendar-year percentage returns. At year-end 2022, candidate CNY
equity was **6.4078%** above baseline; that lead shrank to **5.1650%** at
year-end 2023 and **2.6370%** at year-end 2024. Thus 2023 has a larger absolute
simulated profit in the candidate but a lower own-wallet growth rate
(431.0301% → 424.8279%) from its higher starting base. The 2024 own-wallet
growth rate also falls (64.6453% → 60.6875%) as the relative lead contracts
further. A 2023 position carried across the year boundary, so an entry-year
cohort cannot be relabeled as a calendar-year settled cashflow.

This closes the frozen candidate's economic case: +0.8907 percentage points
full-path CAGR but higher MDD/ES5, costs, and maintenance, below the archived
replacement rules and the original 150% CAGR reference. The exact attribution
supports **candidate design cost and wallet feedback**, not a new proven
execution bug in `main`. No strategy code or risk setting changes.

## Reproduce and next evidence gate

Run `python research/entry_shock_opportunity_forensic.py --root <local-pair-directory>`
against the already archived pair. That directory contains
`session_schedule.json`, each wallet's `receipts/027-2026Q3.json`,
`scratch/reports.jsonl`, and `scratch/state/intents.sqlite`. The script reads
SQLite in `mode=ro`, checks 795 matching manual starts, zero unresolved or
pending intents, order/inventory identity, funding/fee totals and terminal
wallet closure. It prints only aggregate counts and cashflow differences.

The next executable **independent** question is whether newly timestamped
source receipts at actual future manual starts can identify enough untouched
opportunities before a rule is frozen. The existing option receipts cover only
two days, matched liquidation/open-interest and spot-flow receipts lack
qualification, and synchronous executable dated-basis quotes are absent; none
can currently support a candidate. A native IOC/stop cost question would need
separately authorized Demo observations. Reusing this failed gate with a new
threshold, reducing primary adds without independent information, or replaying
795 accounts cannot settle either question. Current `main` remains unchanged.
