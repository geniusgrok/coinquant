# Development research continuation — 2026-09-21

Formal goal is CAGR>=150% and complete continuous account MDD<50%, CNY10000,
2020-01-01 through2026-09-20 exclusive,20x exchange setting, original sparse
invocations. No production qualification or live/testnet account operations.

## Evidence and decisions

All results below cover2020-2023 only;2024+ economics remain uninspected.
They retain proxy dated rules, USDT=USD, constant frozen FX and adverse funding
bounds. MDD is an extrema envelope, not a tick-measured account path.

| Experiment | CAGR | MDD envelope | Liquidation classifications | Decision |
|---|---:|---:|---:|---|
| Exact L7 reproduction |4.863302%|11.363203%|2|All five outputs reproduce archived evidence|
| L9 persistent original protection, regime exit |7.399214%|8.061816%|5|Initial hourly screen rejected|
| L10 long-only persistent holding |4.220932%|17.362124%|1|Rejected; shorts' portfolio contribution cannot be inferred from standalone gross PnL|
| L11 ratchet plus reversal exit |4.863302%|11.363203%|2|Rejected; economically identical to L7|
| Paired refined L7 |4.919425%|11.162174%|0|Comparison with identical minute availability|
| Paired refined L9 |7.504923%|8.061816%|1|Retain for development; original registered progression screen passes|
| L12 risk.012 sensitivity |14.207490%|13.330471%|1|Diagnostic only; not a new alpha or production candidate|
| L12 risk.024 sensitivity |26.004991%|21.010163%|1|Diagnostic only; stop after the two registered risk levels|

Minute evidence resolves cross-minute stop/liquidation ordering on six selected
development days, not actual exchange fill guarantees. One L9 same-minute ambiguity
remains adverse. All12 official files pass SHA256, CRC,1440-minute coverage and
exact reconstruction of native hourly OHLC. Native acquisition run35574493320
succeeded; original612670-byte ZIP is durable (refined-comparison.json receipt).
Temporary acquisition workflow hooks were removed after recovery.

The refined driver without minutes reproduces original L7 order and equity bytes.
An initial refinement risk (rechecking hour-open after offset funding) was removed;
paired baseline metrics were unchanged. Both exact sources/results are preserved.

L9 is held33019 of35064development hours, but mean account notional is0.0672698x,
maximum close notional0.298063x.20x venue leverage is not20x account exposure.
The bounded allocation probes improve raw CAGR and CAGR/MDD, but do not constitute
new alpha or formal acceptance. Do not continue escalating risk levels to hit150%.

## Engineering

Authorized thresholds now have inclusive1.5 CAGR and exclusive0.5 MDD semantics;
historical evidence remains intact. Numeric acceptance is separate from provenance
and execution qualification. Legacy inverse contract metadata is explicitly scoped;
production target is Binance BTCUSDT USDT perpetual.

Binance observation now rejects conflicting isolated-margin values across account
and position endpoints and missing/duplicate/native-invalid algo identities.
Two snapshots repeating the same cross-endpoint inconsistency cannot validate it.
The default CLI remains observation-only; full write lifecycle/testnet not verified.

Validation:12 initial threshold/replay checks passed; latest14 focused acceptance,
minute evidence and Binance observer/CLI/intent tests passed. Minute reconstruction
and original-driver equivalence passed. Existing hosted check at7ac1942 succeeded.
This is not a claim of a fresh local full-suite run.

## Next concrete work and external gaps

1. Keep L9 risk.006 as the structural reference; do not promote risk probes or
   rejected L8/L10/L11. Freeze its source and traces before further changes.
2. Assess executable order sizing with dated native quantity/minimum/tick/max rules;
   hypothetical lot.0001 is not proven valid or conservative. Establish sensitivity
   bounds explicitly if exact records cannot be recovered.
3. Resolve settlement-event marks/USDT valuation/history. The existing funding API
   probe lacked early markPrice values; repeating that probe is not a solution.
4. Complete Binance durable writes, protected entry/partial fills, cancellation
   races, margin transfers and recovery with the official current API, then an
   explicitly authorized testnet account. No such account has been supplied here.
5. Do not inspect2024+ to rescue this family. Register a mechanism-level entry or
   capital-allocation hypothesis only after executable sizing/participation evidence.
   The two L12 probes are exhausted; no adjacent risk grid is authorized by them.

Economic and execution acceptance remain incomplete. Main remains at the last
verified c886b7c63c6455bd7c933269e32cd35a6fb3e09a; verify current refs on continuation.


## Continued implementation following renewed150%/50% instruction

Targets unchanged. New work tested capital reinvestment, full-account profit
retention, bounded recovery and a30-day holding-horizon information hypothesis.
All measurements remain development-only,2024+economics unused.

| New experiment | CAGR | MDD envelope | Finding |
|---|---:|---:|---|
| L13 locked-profit reinvestment |18.336817%|72.678661%|Rejected; protecting campaign starting cash did not protect accumulated gains|
| L14 account peak floor |27.742135%|47.047499%|Rejected; cash below planned45% line locked the system out from January2021; risk efficiency below L9|
| L15 recoverable risk capacity |27.661235%|49.122198%|Rejected; trading resumed but risk efficiency did not recover;11interval liquidation classifications|
| L9 current-quantity stress |6.198385%|7.728925%|37entries and27minimum-size rejections; not historical native qualification|

L16 causal log-price slope at a30-day holding horizon produced1.2101% mean net
forecast return versus2.5932% existing channel and4.5539% constant long on459same
samples. Correlation0.1145 alone does not establish incremental utility.
The45nonoverlapping samples averaged2.3330%; original progression screen failed.
This is a forecast diagnostic, not account CAGR or a tradable monthly return.

L15 fixed-inventory funding interval is731.04..739.14USDT net cost against760.38
old adverse-debits-only cost. This attribution neither replays altered account
feedback nor proves actual funding cash. Omitted credits are not the main observed
economic gap on this inventory path.

Current-rule compatibility audit:28/32L9 entries and196/210L15entry/add orders
conflict with the saved2026-09-21native lot/notional snapshot. This says nothing
about historical2020rule validity. The previous .0001research lot must not be
promoted. Shared Binance market_quantity now rounds down to both native lot
increments, caps each market order, enforces minimum notional and refuses to
round UP beyond risk budget. Research stress actually calls this implementation;
production order writes remain unimplemented and blocked.

The stress quantity corrections worsen L9CAGR7.50%->6.20%. The active structural
reference is therefore still unqualified and not a production recommendation.
Do not solve rejected small orders by secretly forcing larger risk.

15affected offline checks passed (reinvestment/floor arithmetic, known-trend screen,
shared native sizing and existing Binance observation). Earlier unaffected
checks remain applicable; no new local full-suite claim. OriginalL9research entry
was restored exactly to8207fdd after rejected experiments; rejectedL15implementation
is isolated in research/profit_reinvestment_replay.py.

Full originals/receipts: l13-l16-originals.json and quantity-stress-originals.json.
Next: use executable order units as the baseline for a distinct entry-information
hypothesis; do not keep extending profit floors, risk grids or L16slope thresholds.
Historical filters, exact settlements/valuation and protected Binance write/testnet
lifecycle remain unresolved. These results do not meet150%full-window acceptance.
