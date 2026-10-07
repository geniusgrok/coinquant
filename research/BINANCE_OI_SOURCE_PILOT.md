# Binance BTCUSDT futures metrics: archive qualified only as today's snapshot

**Decision:** Do not run a historical open-interest information or wallet test
from this archive. The current public files are internally checkable and cover
many calendar days, but their **current versions** rarely predate the original
manual opportunities. Only four original independent campaigns have both
needed prior-day file versions available before entry, and just one of those
ended through the original protective stop. This is a source/support failure,
not evidence that open interest has no predictive information. No threshold,
direction rule, account experiment or `main` change was made.

## Difference from earlier work and field meaning

The archived `research/search-RESULT.md` mentions an open-interest plus forced
liquidation and spot-absorption route awaiting matched sources; it did not
validate Binance's official historical metrics archive. The separate failed
CFTC gate used CME weekly participant positions, not Binance BTCUSDT USD-M
open interest. Binance's [official public-data repository](https://github.com/binance/binance-public-data)
explains next-day daily archives, sibling `.CHECKSUM` files, and that archived
files may be updated later. Its [USD-M API documentation](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data)
defines `sumOpenInterest` as total open interest, `sumOpenInterestValue` as
total value, and the statistic timestamp as the end of its interval; the live
historical API retains only the latest month. The CSV archive itself does not
provide a per-row original receipt or revision log. For BTCUSDT the quantity
field is a BTC-denominated participation measure; its USDT value is also driven
by BTC price. Neither a rise in open interest nor a long/short account ratio
identifies the direction of the next price move. The ratio fields were not
substituted for missing trade-side or liquidation evidence.

## Fixed public-calendar evidence

Before requests, five dates independent of private sessions were fixed:
2020-01-01, 2021-01-01, 2023-01-01, 2025-01-01 and 2026-09-01. The first
ZIP returned 404; the other four ZIPs and their official CHECKSUMs returned
200, and each computed SHA-256 matched its sibling sidecar. All four CSVs
contain `create_time`, `symbol`, `sum_open_interest`,
`sum_open_interest_value`, three long/short ratio fields, and a taker
buy/sell-volume ratio. The timestamp grid is five minutes on each sampled
day. The 2021 file has 576 physical rows but only 288 unique five-minute
times: every duplicate is byte-identical as a parsed record. The 2026 file
has all 288 slots but some rows out of chronological order. A consumer would
have to sort and deduplicate, and reject conflicting duplicates.

The site's own public listing points to an unauthenticated S3 bucket. A bounded
five-page listing of this **one public prefix** found 2,227 consecutive dated
ZIPs, from 2020-09-01 through 2026-10-06, each paired with a CHECKSUM; there
is no monthly metrics prefix. This is *filename coverage*, not complete
per-file row quality or proof of original availability. Raw sample files,
checksums, five listing pages, response headers and local receipt clocks are
retained outside the repository. No account or private start time was sent.

| Fixed sample | Unique five-minute slots | Current ZIP Last-Modified |
| --- | ---: | --- |
| 2021-01-01 | 288 | 2026-03-18 |
| 2023-01-01 | 288 | 2023-06-28 |
| 2025-01-01 | 288 | 2026-07-24 |
| 2026-09-01 | 288 | 2026-09-02 |

The listing shows every 2020–2022 ZIP now has Last-Modified over 30 days
after its data date; 2025 has the same property, as do 303 of 366 files in
2024. A current checksum authenticates **today's** ZIP, not its first version.
For a conservative 24-hour BTC open-interest change at an original entry,
both of the prior two public day ZIPs and sidecars must already have their
current Last-Modified earlier than that manual start. Local matching by the
original durable campaign identity yields:

| Original independent campaigns | Count |
| --- | ---: |
| All filled flat-to-flat campaigns | 50 |
| No two preceding archive days | 10 |
| Two days named in current archive | 40 |
| Both current ZIP and CHECKSUM versions predate original start | **4** |
| Protective-stop exits within those four | **1** |

The other **36** covered opportunities have at least one needed current
object version modified **after** their original start. No financial outcome
or metric value was paired with those entries. Open interest could in principle
add participation information beyond price, volume and funding, but the
available originally versioned support is inadequate even for a single cheap
stop-risk screen. Fetching only the private opportunity dates would expose
the manual timeline through external requests; fetching thousands of daily
ZIPs would not repair the version problem. Therefore no information hypothesis
was frozen or tested here.

One public read of the present `/futures/data/openInterestHist` endpoint,
without credentials or private time filters, returned **HTTP 451** with a
restricted-location response. That access denial was respected; no alternate
live API endpoint, identity, proxy or credential was tried after it. The small public archive
capture succeeded separately. Existing Deribit option-chain receipts are a
different independent source but cover only two real receipt days and have no
matured prospective interval; the previously frozen DVOL index information
test also failed. Among the reviewed independent inputs, none currently
supports a Coinquant strategy change. The original 150% CAGR reference remains
unmet, and current `main` stays unchanged.
