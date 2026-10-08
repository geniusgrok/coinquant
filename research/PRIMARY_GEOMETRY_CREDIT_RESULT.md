# Primary geometry and credit source review

Research only. This branch contains a concise technical record; it does not change trading code, defaults, account state or model behavior.

## Original evidence and scope

Use the original published historical simulation and its source binding, not another producer with the same manual-session table. Original runtime: `47837e391be4130104967d794e9701068a0bcc5a`; archive: [c6223a5](https://github.com/geniusgrok/coinquant/tree/c6223a5d1bd6ae46fd192668335cee31630ff33e/backtest-source). The current runtime base is `f3fe9b8be32fbe8cce324b35c57a06fc929a4958`.

The original order/payload/fill witnesses and chronological income ledger recover 28 primary first positive-fill IOC orders and their preceding flat capital. Original runtime/tooling bytes, report binding, source arithmetic and qualified market inputs were checked. The full original preflight mark, book, read clock and State database remain unavailable. A different producer's journal cannot fill those gaps.

These are first **positive-fill** orders, including terminal EXPIRED partial fills. They are not a causal selector for the first attempted order. Earlier zero-fill attempts retain unknown signal identities where the original evidence lacks them.

## One frozen geometry expression

Let `C` be original sizing capital, `F` the same-time original RMS fraction, `P0` the original signal's completed close, `S` its native rounded stop, `P` the executable IOC limit, and `fee` the original source fee. The original zero-extra-stop-slip scenario is a research proxy.

```
loss(P, S) = P - S + fee * (P + S)
B = C * F * loss(P0, S) / P0
q_new = native_LIMIT_floor(min(original_funded_IOC_quantity, B / loss(P, S)))
```

This references signal geometry; it does not assume execution at `P0`. It adds no loss percentage, age/ATR cutoff, short, leverage increase, new entry or changed stop/take/lifetime. A later executable implementation would have to enforce the rule before every initial attempt and share a persistent budget with all same-identity topups.

The diagnostic changes 20 submitted quantities. Only seven caps shorten the original first-order fill prefix, with support in both chronological periods; the other 13 remain above the original partial-fill quantity. No whole order is suppressed by minimum filters. In the original matcher, a smaller legal order selects the same print prefix and truncates its last segment under the same complete arrival state.

Reducing quantity preserves the fixed flat-entry funding calculation only if allocated margin is recomputed consistently and original filters remain valid. It does not establish ownership readback, protection installation, window-end survival or a changed wallet path.

## Minimal falsification and result

The rule and controls were frozen before the new outcome calculation. Equal submitted quantity/notional does not imply equal filled quantity/notional for IOC partial fills. Two uniform controls use only initial dose: earlier-period calibration held fixed later, and a full-sample retrospective initial-fill-gross matching benchmark. The latter is not deployable or out-of-sample evidence. Native quantity plateaus and matching residuals are retained in the local receipts.

Only the initial IOC lot is attributed on the original path. Later original BUYs enlarge the original-position denominator without adding to this lot. SELLs allocate the lot pro rata using original quantity before selling; funding allocates at its original income-ledger position. Commission events match original trades in sequence. REALIZED_PNL audits source average cost and is not added twice.

All original trade/commission, funding denominator and final lot-quantity checks passed. The geometry choice forfeits substantially more positive contribution while saving less negative contribution than the near-equal initial-gross uniform benchmark. The later period saves no negative contribution. The planned stop-loss scenario is smaller, but initial gross matching does not match holding-time exposure or beta.

**Close this particular expression without threshold rescue or a full wallet replay.** This result does not reject every risk budget. It supplies no candidate wallet CAGR, portfolio drawdown, native stop-slippage calibration, future alpha or adoption evidence. The original depth, fixed maintenance-margin and zero-stop-slippage proxies remain limitations.

The deterministic reconstruction, pre-output freezes, complete local attribution scripts and receipts are retained separately. This technical record deliberately publishes no account/order identifiers, exact manual timeline, asset ledger, private hashes or raw data. No original pack is duplicated here.

## Independent credit source qualification

NFCICREDIT is a possible independent credit-condition input to distinguish macro easing from credit stress. Existing bounded candidate directories contained no prior NFCICREDIT experiment. No action or signal threshold was selected.

Official [Chicago Fed definition](https://www.chicagofed.org/research/data/nfci/about), [release/revision description](https://www.chicagofed.org/research/data/nfci/current-data), [ALFRED series](https://alfred.stlouisfed.org/series?seid=NFCICREDIT) and [vintage help](https://alfred.stlouisfed.org/help/downloaddata) were consulted. The index is revised; today's historical series cannot substitute for a historical vintage. Current weekly scheduling alone cannot prove every historical publication and exception.

Bounded official download and date-specific page requests, an independent connected search channel and browser navigation yielded no historical original or qualified old value. The browser call hung and was interrupted; this was a channel failure, not an approval rejection or proof that the archive is absent.

**Source qualification remains blocked.** Required next evidence is two genuine old vintages with effective vintage identity, old-value/absence/revision comparison and publication/exception clock proof. No credit opportunity coverage, return test, final-value substitution, account access, new credential, paid source or larger collection followed.
