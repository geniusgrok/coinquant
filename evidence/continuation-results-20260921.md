# Native refinement and L1 development results

## Verified measurements

| Measurement | CAGR | MDD | Liquidations | Scope |
|---|---:|---:|---:|---|
| Reproduced inverse baseline | 43.920748% | 77.051193% | 8 | full frozen window, proxy rules |
| Native minute refinement | 44.121475% | 77.049869% | 2 | same window/schedule/model, proxy rules |
| L1 linear-account hypothesis | 0.583756% | 1.355090% | 2 | 2020-2023 only, cross-venue proxy |

L1 is not comparable to the full-window rows as a return ranking. All remain
NOT_QUALIFIED. No new native linear economic qualification exists.

## Native event resolution

The preserved full native archive was restored from its existing evidence Git
branch, size/SHA256 verified; no Bybit history was reacquired. A read-only observer
reproduced the old baseline numbers exactly and captured all eight pre-exit
positions. Six stops trigger and fully execute before liquidation under the
frozen 1% minute-volume capacity assumption. 2021-11-03 and 2024-12-05 remain
ambiguous within one minute and retain conservative liquidation outcomes.

`research/refined_replay.py` validates every refined day's inventory and payload
hashes, requires 1440 consecutive native minutes, and verifies each reconstructed
hour exactly matches the original trade/mark OHLC and volume. It feeds minute
execution ticks on the eight complete days, hourly ticks elsewhere. No synthetic
interpolation or stop-first assumption is used. Four-hour signal OHLC remains
unchanged. Native depth resolution changes on refined days and is not concealed.

The shared replay now uses each verified tick's duration, normalizes previous
volume at its own resolution, and counts signal aggregation duration. Additional
continuity guards were added after the measured run; their behavior was checked
with synthetic mixed-resolution and gap tests. The exact pre-guard measured
replay source is retained and SHA256 checked against the result identity.
Do not describe the result as a new run of any later source revision.

Full refined run: 537 fills, 795 decisions/invocations, longest gap 151h.
Invocation file SHA256 remains
2c385775cf9cc33af2ec99f68314ae76c38fd16e5bf28f449eef9731f983f8b8.
This resolves the event-state gap from the preceding checkpoint. It does not
resolve the economics: BTC collateral beta still dominates whole-account MDD.

## L1 diagnosis

468 development invocations; 306 no-direction decisions; 127 unsafe initial
stops; 10 entries; 1973 hours with exposure. Development CNY ends at 10235.56.
A low drawdown obtained by barely participating is not a successful alpha model.
L1 is rejected for progression to validation. No 2024-end L1 prices were inspected
or tuned. The signal/linear-account source used by this measurement is preserved
inside the original archive before subsequent experiments.

The diagnostic intentionally uses Bybit inverse market/funding as a proxy input
to hypothetical USDT linear accounting, conservative fee/MMR/precision assumptions,
and USDT=USD. It does not claim native OKX history, depeg risk coverage, historical
linear rules or verified atomic exchange protection.

## Validation and full originals

- 11 existing replay tests passed.
- 5 existing native-parent replay tests passed.
- 2 mixed-resolution/continuity tests passed after correcting the synthetic
  fixture's repeating-decimal volume split; native prices/volumes were not changed.
- 5 linear funds/margin/partial-close/liquidation tests passed.
- Runtime execution/adapter/model are unchanged; no live or testnet writes.

Complete original equity/order traces, identities and measured source are stored
in the 21,825,726-byte artifact identified by `native-refinement-originals.json`.
It is a complete archive, not a summary replacing original files.
