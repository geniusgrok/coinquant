# Native historical input contract

There is no bundled real historical dataset and no qualified economic result.
All timestamps below are UTC milliseconds. Funding/fee/risk records must identify
their real source. Hash identity does not prove source authenticity. Do not relabel
synthetic or proxy data as native because a metric looks favorable.

The single `data/manifest.json` identifies Bybit BTCUSD InversePerpetual, BTC settlement.
Required keys are `venue`, `symbol`, `contract_type`, `settlement_coin`, `provenance`
(`native`, `proxy`, or `synthetic`), `bar_interval_ms` (60000), `start`, `end`,
`warmup_start`, and `files`. Dates are explicit UTC ISO strings. Start/end must
match research/spec.json. Warmup must supply complete aligned 4-hour bars sufficient
for the configured indicators before the formal start; warmup earns no return.

`files` maps each of `bars`, `funding`, `rules` to an ordered list. Each list entry
has `path` (inside the manifest directory), `bytes`, `sha256`, and `source` (native
URL or other precise provenance). Original CSV or gzip-compressed CSV bytes are
verified before reading. Multiple parts must concatenate in timestamp order,
without gaps or overlapping rows. Preserve original downloads and conversion
scripts separately; a normalized CSV is not a substitute for source originals.

## Minute bars

Exact columns:

```text
time,open,high,low,close,volume,mark_open,mark_high,mark_low,mark_close
```

Trade OHLC and mark OHLC must refer to the same native BTCUSD contract and minute.
Volume is USD contracts, not BTC. Every minute from warmup_start through the last
minute before end is required. A trade-price series cannot substitute for mark
prices, and spot/other-platform prices cannot be silently spliced in.

## Funding

Exact columns:

```text
time,rate,mark
```

Rate is a signed decimal fraction, not a percentage string. Mark is the native
funding reference price. Include every scheduled event in the formal interval.
Missing events are not zero-cost events. Schedule changes belong in dated rules.

## Dated trading, cost and margin rules

Exact columns:

```text
time,launch_ms,funding_interval_ms,tick,step,minimum,maximum,market_maximum,risk_limit_btc,maintenance_rate,taker_fee,liquidation_fee
```

Each row is effective from time until the next row. Provide a row effective at or
before warmup_start. `risk_limit_btc` is the base-tier inverse-contract limit in
BTC. Rates are normalized decimal fractions; retain the original API/notice and
its documented units. The replay constrains exposure to this base tier rather
than pretending larger positions can use its margin forever. Both ordinary and
market-close size caps apply. Fees and liquidation costs cannot be omitted.
Historical rules cannot be inferred by copying the current exchange response over
2020-2026. A current-rule approximation must remain labeled as such in evidence.

## Invocation and account assumptions

research/spec.json is frozen before any economic observations in this current
Bybit path. It specifies a SHA-256-generated irregular series of 19/31/47/73/109/151
hour intervals, independent of prices and returns. The baseline contains 795
invocations over the locked upper-bound window, with a mean gap about 74.12 hours
and a maximum gap of 151 hours. The separately declared absence test skips a
21-day period after the 50th trigger; its resulting longest gap is 697 hours.
These are research assumptions, not a promise of identical results for arbitrary
manual timing. Do not select a more profitable trigger sequence after observing
returns.

Development is 2020-2023; 2024 through the fixed endpoint is reserved chronological
validation. No real data from either interval has been measured in this work.
When validation is examined for tuning, record that it is no longer unseen.

CNY conversion uses fixed USD/CNY 6.9762 from the PBOC 2019-12-31 central parity:
https://www.pbc.gov.cn/zhengcehuobisi/125207/125217/125925/3952151/index.html
Initial BTC is valued using the initial native mark, with a separately disclosed
modeled 10bp conversion cost; this is not an observed spot execution.

## Outputs and limitations

The replay writes identity.json, invocations.csv, equity.csv.gz, orders.csv.gz and
result.json. Identity binds all source-file hashes, current configuration, frozen
specification and exact input manifest. Equity contains BTC/USD/constant-FX CNY,
including unrealized P&L and collateral risk. A partial failure writes a failed
result and leaves original partial outputs; it never resets the account or marks
a shortened interval passed.

The current execution model uses prior-minute volume for a depth proxy, a frozen
spread/slippage assumption, participation-limited fills, funding, dated margin
rules and conservative liquidation/stop precedence. Intraminute account extremes
form a conservative drawdown envelope; actual tick-path replay and native hosted
exit behavior have not been independently qualified. Output is not formal
acceptance merely because the two numerical thresholds happen to pass.

`research/probe.py --output <new-directory>` is a bounded PUBLIC-only schema and
endpoint probe. It retrieves a small number of native responses and optionally one
historical trade file, preserving bytes and hashes. It is not a full history
collector, and it does not use account keys or bypass a venue's access restrictions.
