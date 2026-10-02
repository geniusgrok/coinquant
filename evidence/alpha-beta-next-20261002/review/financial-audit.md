# Independent financial evidence audit — provisional baseline phase

Reviewed 2026-10-02. This is a financial-evidence review, not an adoption approval. No product files, frozen HEADs, live controller outputs or caches were changed. No replay, download, account request or order was made. The separate assessment worktree was not used as evidence.

## Scope and identity

- Frozen Coin source: `acedaa43ca94223f24e2fe11851bbef74e032a69`; Python digest `a6e3f30f02208ff7e604b6181c5d8fa7000fe7e30dbc3276fbcc93ffbb0ad227`.
- Frozen Spot source: `8ca002522fbdce531dcfbbb783ff4d152a7fd66c`; Python digest `0df8c537ee8d47db6e841778e8e37eac847e1a0c1151e379440081b9473ae026`.
- Spec digest `8228013f4ac41affb65162c1cabad8f51b5ef32b9607f62231a4776168a337d0`; protocol digest `4ae09ae0bc9224f8028ddcc1373dc1bbc7251a70be2945e5655f5e5fa12eb27e`.
- Original Spot corrected consensus SHA256 `cf075b86ba5df590e078a7c626c53cb20937be955cfb6ad8d41eae19b78645e8`.
- Completed new Spot consensus compressed bundle SHA256 `8c22b10383f637ae2cf87f7c8f027a765c5fb7b0e9af58d331d14dba89fe439a`.
- Original Coin end-exclusive accounts SHA256 `15dd7bfc242d52bf692663179cd1e3867418f8b55a4cad0894d253a8b296f00a`. Only its four incumbent scenes were inspected. Its measured source and explicit derivation remain original; this is not a new Coin replay.
- FX bytes SHA256 `67606315ea34c0301e0129ac8fc27056099986d9fbd58a552a07f140cdd05bb5`.

Independent audit code: `independent_financial_audit.py`, SHA256 `647988a85f42b39590946c0c6175bb0d3eebc3ac076572068725198ed9824fd9`. Detailed numeric output: `financial-audit-baselines.json`, SHA256 `a5853b6f1838a4e63e04cda918f9622f4e23ad19b2572ad7fbbe8d938aceb9b0`. The JSON preserves individual public funding/mark ZIP hashes. The script imports no producer modules and uses Decimal precision 40 for money and NumPy matrix formulas for independent statistics.

## Baseline equality and money

All four completed new Spot scenes (`base`, `fee150`, `slip2`, `outage`) agree in **every original row field** after relational client-ID normalization and removal of the per-session SQLite archive hash only. Financial values, fills, prices, quantities, timestamps, daily curves, ownership/allocation relations, session statuses/cycles/errors and client request traces are unchanged. Each scene has 795 sessions and 141 fills. All 3,180 recorded archive-verification flags are true and have 64-character hashes. This checks recorded archive claims, not independent reopening of the underlying 3,180 backup files; separate archive-integrity review remains necessary.

Spot cash was reconstructed from actual recorded quote amounts. BTC was reconstructed from gross actual fill quantities less BTC fees; USDT fees debit cash. Daily cash, quantity, USDT marked equity and prior-date FX CNY values all reconcile. Maximum absolute discrepancies across the four scenes are 2.242e-23 USDT cash, 6e-29 BTC, 2.765e-23 USDT equity and 2.697e-22 CNY, consistent with the producer's 28-digit decimal rounding. Fees independently converted at each actual fill price agree within 1.513e-24 USDT. Base terminal cash is 7,858.0653950354 USDT plus 0.207770651817506 BTC; aggregate fees are 1,326.7429863087 USDT. Both 0.001 FX conversion charges are included, with the prior-date rate.

For each original Coin incumbent scene, the audit recomputed signed quantity, weighted-average entry and realized PNL from individual fills; commissions from actual quantity × price × the scene's commission rate; and wallet/equity/terminal CNY. Funding inventory was checked against all public funding timestamps while a reconstructed position was held. Exactly 921 funding payments per scene match quantity × public settled rate × previous completed public mark **exactly**. All income and trade times are strictly earlier than END; no terminal funding is included. All four final quantities are zero. Terminal CNY differences are at most 5.254e-21 CNY; daily quantity differences are zero and daily equity differences at most 1.143e-21 USDT.

| Original Coin scene | Actual fill records | WAC realized PNL USDT | Commission USDT | Funding paid USDT |
|---|---:|---:|---:|---:|
| base | 1,561 | 327,291.292750 | 15,290.544999 | 21,733.156123 |
| fees-x1.5 | 2,026 | 442,315.772180 | 29,369.422642 | 28,613.815552 |
| read-400ms | 1,069 | 205,621.463040 | 9,241.429397 | 13,355.300475 |
| trigger-slip | 1,795 | 389,600.453954 | 18,626.186653 | 25,716.975803 |

Daily boundary convention matters: Coin's UTC midnight close includes funding settled at that timestamp but precedes a protective trade at that same timestamp. The next day's account contains that trade. An indiscriminate `trade.time <= close.timestamp` comparison would falsely report daily cash/quantity errors. The independent audit verified the documented boundary chronology, including these cases.

## Independent daily statistics

The common market grid contains 2,454 completed days, 2020-01-01 through 2026-09-19 inclusive. The 2022+ subset contains 1,723 days; 2020–2021 contains 731. USDT returns start from initial CNY converted into USDT after entry cost; CNY returns start from original CNY10,000 and include both conversion costs. Benchmark returns use actual daily BTCUSDT closes (first return from the first open) and, separately, prior-date FX-converted BTC. HAC uses seven Bartlett-weighted lags, n/(n−2) finite-sample correction and normal 1.96 intervals. Volatility uses sample standard deviation × sqrt(365.25); ES5 averages the worst ceil(5%×n) returns. These are descriptive estimates.

| Base account / period | USDT BTC beta | Annual USDT vol | Daily USDT ES5 loss | CNY closing MDD | USDT annual arithmetic intercept (HAC7 normal95) |
|---|---:|---:|---:|---:|---:|
| Spot full | 0.397068788 | 37.1882% | 4.4166% | 39.8257% | 27.5445% [5.8461%, 49.2428%] |
| Spot 2022+ | 0.354583565 | 29.9915% | 3.7392% | 39.8257% | 11.9556% [−10.4863%, 34.3975%] |
| Original Coin full | 0.275848202 | 64.4015% | 3.6183% | 27.8978% | 82.0793% [36.3713%, 127.7872%] |
| Original Coin 2022+ | 0.268369888 | 51.5983% | 2.8188% | 26.7407% | 53.4378% [8.2111%, 98.6645%] |

Full CNY betas are Spot 0.397315385 and Coin 0.272950848. Full USDT up/down arithmetic capture ratios are Spot 0.480349/0.416023 and Coin 0.380622/0.167016. Down-day betas are Spot 0.243318466 and Coin 0.023937426. The JSON includes all four scenes, both currencies, both periods, up/down capture and beta, daily MDD, volatility, ES, and calendar USDT log returns. Year 2026 is partial.

Reported continuous proxy MDD remains Spot 41.2073348% and original Coin 44.1050788%. This phase independently recomputed closing MDD, not every continuous proxy observation. The continuous measure is the declared Spot OHLC / Coin minute-envelope historical proxy; it is not native execution or order-book evidence. The pronounced difference between Coin closing and continuous MDD must remain visible.

## Assessment compatibility issue — action required

The immutable Coin baseline CAGR is **1.1922835553585416**, using **365.2425** days per year. A 365.25-based daily-curve CAGR is **1.1923188914655962**. The difference is 0.0000353361070546, so frozen `alpha_assessment.financial`'s shared 365.25 recomputation with a 1e-8 equality gate rejects a financially correct Coin account. This is an annualization convention mismatch, not money loss. Preserve the measured original Coin CAGR and use the project-specific annualization basis for equality; disclose the basis of descriptive metrics. Root was notified; final assessment repair is not yet reviewed here.

## Inventory and outstanding review

This phase audited **4/48 new unscaled cases**, namely completed Spot baseline scenes. Four immutable original Coin reference scenes were additionally inspected, and do not count toward the new 48. No completed new Coin baseline, other candidate, risk replay, combination, sensitivity or final assessment is approved by this document. Their unavailability to this audit phase is pending review, not a failed or skipped case.

The next review must inventory all 48 single cases including failures; ten candidate risk obligations plus the two unity baseline controls if produced; conditional compatible combination scenes; and all registered incumbent/final Coin sensitivity accounts (CNY9,900/10,100 and starts −/+60,000ms). It must check training profiles against only actual 2020–2021 daily returns, input hashes and cutoff; verify sizing from actual replay evidence rather than scaled curves; recompute achieved 2022+ volatility/beta matches; reconstruct independent core/tactical subpools from actual allocated fills; and compare final numeric/report-selection claims to those outputs. This script is ready to reuse one stable bundle at a time.

No matched-alpha, clean out-of-sample or prospective-return conclusion follows from this baseline review. The whole history has prior research contamination. Native cases remain zero, actual account-days remain zero, initial forward history remains zero until later observed public completed bars, and original targets are unchanged (Spot CAGR≥100%, continuous MDD≤30%; Coin CAGR≥150%, continuous MDD<50%). Neither baseline achieves its original return target.

## Later scoped addenda

The annualization compatibility issue above is closed by independently approved assessor fix3 at `32ab1bb546bde064e641c4a2eb5ed4248e590acb`; see `task3-fix3-financial-review.md`. No other pending full-evidence conclusion changes. The initial checker bytes are preserved verbatim as `independent_financial_audit_baselines_v1.py` with the original recorded SHA; the current checker has a later single-bundle interface documented in `financial-audit-checker-guide.md`. Original baseline numeric output and its SHA remain unchanged.
