# Stable-settlement feasibility continuation — 2026-09-21

Status: NOT_QUALIFIED; no new economic result. Main unchanged.

## Verified remote recovery

- main: c886b7c63c6455bd7c933269e32cd35a6fb3e09a
- research recovery HEAD: d67bf03bab57b13adda0c9b55847147d9ac6b54d
- separate existing OKX probe HEAD: c098178d7834b161185fa399950932bb607fee22
- 35559122193: minute acquisition and check jobs queued at inspection.
- 35559716288: OKX public boundary probe queued at inspection.

Later in this continuation the minute acquisition completed successfully. Artifact
10622037487 (729363 bytes) was downloaded, integrity checked and preserved in
`ambiguous-minutes-20260921/`. All 8 inventories and 56 referenced payloads matched;
11520 consecutive minute bars were verified. Exact baseline event thresholds are
not present in the active branch, so event ordering remains unresolved. The check
job and OKX probe remained queued at the later inspection. These are time-specific
observations, not promises about later asynchronous state. Existing native
BTCUSD archive was not downloaded again or reacquired. No .transfer restoration.
The OKX branch has stale recovery documents; do not merge that branch wholesale.
Only its public probe source was copied and repaired on the active branch.

## Official evidence actually read

1. Current public instrument endpoint:
https://www.okx.com/api/v5/public/instruments?instId=BTC-USDT-SWAP&instType=SWAP

The response identifies BTC-USDT-SWAP, SWAP, linear, USDT settlement, live,
ctVal=0.01 BTC, listTime=1573557408000 (2019-11-12T11:16:48Z), lever=100.
This supports existence before 2020; it does not prove complete historical
coverage or historical lot/tick/fee/MMR rules. Current metadata is not backfilled.

2. Official API best-practice guide:
https://www.okx.com/docs-v5/trick_en/

An accepted write is not a final order result. IOC may partially fill and then
cancel. Client IDs are checked for uniqueness among pending orders, so a stable
ID alone does not guarantee retry idempotency after a terminal order. Durable
intent plus authoritative order/fill reconciliation is still required.

3. Official change log:
https://www.okx.com/docs-v5/log_en/

The accessible log does not substantiate the previous evidence document's
July-2026 partial-fill protection assertion. Absence here is not proof the feature
does not exist. Treat automatic partial-fill protection, full-position coverage,
remaining-parent cancellation and TP/SL amendment behavior as UNVERIFIED until
an applicable official reference and authorized testnet observations resolve it.

## Access limitations observed

Local requests to www.okx.com docs and instrument endpoint returned HTTP 502;
openapi.okx.com instrument request timed out after 15 seconds. Web retrieval
could read the instrument endpoint and the two guides above, but could not read
2020 trade, mark and funding boundary queries. Search returned unrelated pages;
none was used as evidence. The queued existing hosted probe is the next concrete
native-data recovery path. No claim that unavailable data means nonexistent data.

## Actual code/validation

`research/probe_okx.py` now rejects absent/zero listing times, missing exact start
bars, internal hourly gaps, duplicate times, malformed or unconfirmed candles,
wrong-instrument funding and absent realized rates. Public redirects are refused.
It always labels even a successful boundary check NOT_QUALIFIED: boundary pages
do not establish continuous history, native rules, or execution safety.

Five probe regression tests passed locally. Five L1 signal tests passed for
causal candle availability, missing/stale data, long/short symmetry, flat prices,
scale invariance and same-candle decisions. Those ten tests do not validate
private execution or economic profitability. Production code was not modified.

## Direct continuation

1. Read actual status of both run IDs. Preserve completed artifacts byte-for-byte
   with remote readback verification before interpreting them.
2. Re-evaluate OKX output with the repaired probe rules. Existing queued job uses
   older probe code; its `passed` flag is not authoritative qualification.
3. Resolve native 2020 funding/mark coverage, dated rules and protection semantics.
4. Build native linear replay and measure preregistered L1 on development only.
5. Keep main unchanged until the user's unchanged economics and safety gates pass.
