# Original-entry attribution, without an entry-rule change

Read-only reconstruction of the already published 795-session historical **simulation**. The original 50 flat-to-flat BTCUSDT perpetual position intervals, original 300-second manual starts, source-bound financial ledger, final session reports and ten required original Binance UM four-hour ZIPs were reused. Each ZIP matched the historical producer's recorded content digest before parsing. No account, order, market path or strategy state was changed; no session or wallet was replayed. Run `entry_path_reconstruct.py` with the archived `coin-full.json.gz`, `reports.jsonl`, `qualified-market-metadata.json` and those ten original four-hour files to reproduce aggregate counts; optional detail output has only ordinal campaign numbers, no account or order identifiers.

## Identity and timing

All 50 first fills map to an original BUY client identity, its actual manual start and the report's entry timing. The exact opportunity identity is proved for **46**: 34 same-session `hold` previews, eight later `hold` previews tied to the same original entry, and four unique primary signals whose original 42 completed four-hour candidates reproduce the accepted take price and eventual model stop. The same geometry procedure matches both known primary examples in the downloaded months and finds no match for three known macro examples. The remaining **four** have no surviving held preview and no primary match in their complete original seven-day candidate windows: macro **type** is supported, but the exact negative macro epoch is not. The public archive has only the terminal model checkpoint, not the four intervening durable states. The order-send offset seen on other macro entries is insufficient proof that these four macro epochs began at that same call; they stay unresolved.

| Path fact | Result |
| --- | ---: |
| Original primary / macro position intervals | 30 / 20 |
| Primary first fill at least four hours after its own signal | 29 / 30 |
| Primary signal-to-first-fill age, median and range | 47.5 h; 1.0–143.0 h |
| Request-to-first-fill in the historical simulator | 1.000–1.782 s |
| Exit by ordinary manual order / native simulated stop / native simulated take | 36 / 12 / 2 |
| Primary intervals with a later manual start before exit | 24 / 30 |
| Their first later start before the original seven-day expiry | 19 / 24 |

The single roughly one-hour-old primary first fill later lost money, but its protected position closed before another manual session. For all other 29 primary fills, adding a blanket four-hour wait to the existing session would be redundant. A delay that skips this one historical loser is not a stable discriminator or a paired-wallet benefit, and it might miss winners on other manual-start paths. A later start or calendar time before expiry alone does not prove the original opportunity remained active. The model's original seven-day expiry is checked when an actual session updates completed bars; 23/30 primary exits occurred after that calendar instant, consistent with offline native protection and irregular starts. This is not grounds to extend the seven-day ordinary exit again.

The 50 interval income subtotals reconcile **exactly** to the original simulated wallet delta. Nine intervals shorter than 24 hours were all net losers, totaling about **47.9k USDT** of loss as already identified in the review. About **92%** of that loss was realized price P/L; commission and funding explain the remainder. Eight ended by the simulated native stop before another manual start; the ninth had one later start but no proved still-active opportunity. These are outcomes, never entry labels. Removing fees alone cannot recover the price losses. The old no-macro account already failed its slip stress; this grouping does not override that failure.

Large winning intervals also had nontrivial ages and costs. The three highest net winners had primary ages about **20, 43 and 21 hours**; the two largest losing primary intervals had ages about **1 and 59 hours**. Among 46 intervals with exact model geometry, original stop distance from first fill ranges **0.78–22.47%** (median **5.92%**); both tight and wider stops appear among winners and losers. No stop-width threshold was frozen before seeing these outcomes, so choosing one now would be outcome selection. The original stop, actual first fill and the first requested native stop are kept distinct: 33 intervals sent two stop requests before the next BUY, and the later report timestamp describes the replacement. It must not be interpreted as 33 unprotected fills or as native exchange proof.

## Decision

No request-to-first-fill anomaly, mistaken primary age, missing manual start, or exploitable four-hour wait was established. Four macro **timestamps** remain unproven because intermediate durable model snapshots were not archived; that is an attribution limit, not permission to fabricate identities or rerun a full wallet. The previously failed miner fee, seven-day extension, add-freeze and no-macro routes remain closed. No new entry rule, threshold, 795-session replay, native-account claim or `main` change follows from this retrospective symptom. The original 150% CAGR / <50% drawdown reference remains unchanged and unmet.
