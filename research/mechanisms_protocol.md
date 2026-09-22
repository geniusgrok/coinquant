# Independent event mechanisms, frozen before measurement

Control L29 at d6a63ba; primary development2020–2023.2024+already used, never unseen.
A and B share the existing continuous Binance Account/funded_target/hourly mark,
funding and protective fill engine. Normal research decisions at4h candle close;
sparse decisions at unchanged original triggers. No offline local updates/entries.

A: BB(20,SMA,sample std,2) inside KC(20EMA,14mean true range,1.5), minimum3bars,
from public technical.py in jicheolha/crypto-trading-bot at
9851eadd96c44db99a26d4ca3cbabcc53b199242 (MIT; license preserved).
Use no RSI/volume filters and do not claim its redacted signal generator reproduced.
Freeze the highs/lows of the consecutive contraction before release. First later
completed4h close outside this fixed box signals continuation. Stop opposite box
edge; take profit2times entry-to-stop distance; opportunity expires7days after
release, corresponding to reference documented maximum hold. Define these missing
rules independently. A fresh contraction is a new opportunity, not a stale retry.

B: confirmed swing high/low using3bars on each side; publish pivot only at close of
third right bar. Keep it for20bars after pivot. A completed bar sweeps exactly one
known level and closes back across it: reverse away from sweep. Stop sweep extreme;
TP2R. Both-side sweep is ambiguous, no signal. No FVG/ADX/trend filters. Opportunity
expires20bars after signal. No future-confirmed pivot or future FVG is backfilled.
Concept only from king-No/fvg-trading-strategy at6d88394c96aa5430454ab2b4b1ae0337641816aa;
no license file found in pinned tree: no source copied. Likewise MS-backtesting at
ba33e8c5cbed79d56aaa14336b7a32aaa2631685 has no license file found; borrowing no code,
external injection or published return calculation from it.

Shared event semantics: signals appear only after complete bars, unique release or
sweep timestamp; stop/TP touched on a subsequent complete bar or expiration ends
the market opportunity. Never enter at a stale already-hit level. At invocations,
expired/changed opportunity closes holdings; no scheduled exit is imagined offline.
Existing native SL/TP remain active between calls. No deployed entry conditionals.
A modeled fill consumes the opportunity; no repeat on stopped event. Position size
stays fixed as L29. Initially reuse L29 volatility target ONLY as a diagnostic
control, not an optimized risk budget; no risk increase without measured signal edge.

First screen event direction returns over24h/168h forA,4h/24h forB, including frozen
roundtrip friction plus observed funding-rate cost approximation. This is not account
return and overlapping samples are not independent. Then report both full development
accounts even on failure, to diagnose lifecycle/cost/schedule loss. No parameter grid.
Reject unpromising mechanism; subsequent candidates require a distinct hypothesis.
Formal150%CAGR/<50%MDD remains unchanged. All proxy rules still NOT_QUALIFIED.
