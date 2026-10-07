# Source gap for the two unpaired entry-shock quarters

This is a read-only source inventory for the **unchanged**, frozen `entry-shock-defer` rule. No ZIP body, account, session replay or new candidate was downloaded or run. The original archived producer is `c6223a5d1bd6ae46fd192668335cee31630ff33e`; its `session_market.py` reads daily Binance USD-M `aggTrades` ZIPs through `TradePrints`, and loads monthly one-minute trade/mark candles on demand. The completed quarter pairs and their source qualification remain in `HELD_SHOCK_SOURCE_QUALIFICATION.md` and `ENTRY_SHOCK_DEFER_PAIR_RESULT.md`.

## What is retained

The local recovered market corpus previously had 192 qualified ZIPs: 80 original monthly 4h futures bars, 81 monthly funding files, 19 September 2026 daily 4h files, and 12 one-minute trade/mark months for **2020Q1 and 2021Q2**. Of the previously authorized 110 restored ZIPs, the **81 funding and 19 daily 4h** files can be reused by the original global loader. Its other ten restored minute files cover the earlier two quarters and cannot stand in for later dates. The previously restored 182 daily `aggTrades` ZIPs also cover only 2020Q1 and 2021Q2. Two separate, original-SHA-matched monthly **mark** ZIPs for 2020Q3 and 2023Q1 were retained locally; this check copied them and their archived checksum texts into the recovered market root, then verified both destination hashes. No target-quarter one-minute **trade** ZIP or daily `aggTrades` ZIP body was found under the active market directories, `/workspace/cold/coinquant/evidence`, `/tmp`, or the archived research Git tree. The old public-print vault contains small receipt JSON files, not ZIP bodies.

The original qualification manifest retains **12 target minute** and **57 target daily print** entries with exact ZIP SHA-256, byte size and official `.CHECKSUM` text. All 69 archived sidecar texts agree with their corresponding original content hashes. The original offline wallet's `loaded_print_files` has the same 57 daily print digests. These are strong future byte-identity checks, but a hash/receipt cannot recreate a missing ZIP.

## Current official availability and compressed size

On 2026-10-07, read-only Binance S3 object listings were checked for **every public day** in the two fixed quarters, and for all twelve target monthly one-minute objects. Each required ZIP and its `.CHECKSUM` object was listed. For all 69 files previously loaded by the original producer, today's listed byte size matches the archived original size. An S3 ETag or listed size is not a substitute for downloading and checking the official SHA-256; no new ZIP is called source-qualified here.

| Fixed public range | Daily `aggTrades` ZIPs | Listed compressed bytes |
| --- | ---: | ---: |
| 2020-07-01 through 2020-09-30 | 92 | 505,679,984 |
| 2023-01-01 through 2023-03-31 | 90 | 1,587,605,804 |
| **Both quarters** | **182** | **2,093,285,788** |

The six monthly one-minute **trade** ZIPs and six monthly one-minute **mark** ZIPs total 17,693,551 compressed bytes. The already retained, hash-matched 2020-08 and 2023-02 mark files account for 2,113,214 bytes. Thus the *new* missing minute set is exactly **six trade months plus four mark months**, 15,580,337 bytes. The total missing ZIP payload is **2,108,866,125 bytes (2.109 GB decimal, 1.964 GiB)**, plus 192 tiny `.CHECKSUM` texts. Current free workspace space is sufficient for these compressed bodies, but a loader may need additional parsed/runtime space.

Official object patterns (replace `YYYY-MM-DD` with every day in the two ranges and `YYYY-MM` with each month):

- `https://data.binance.vision/data/futures/um/daily/aggTrades/BTCUSDT/BTCUSDT-aggTrades-YYYY-MM-DD.zip`
- `https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-YYYY-MM.zip`
- `https://data.binance.vision/data/futures/um/monthly/markPriceKlines/BTCUSDT/1m/BTCUSDT-1m-YYYY-MM.zip`

The exact **four missing mark months** are 2020-07, 2020-09, 2023-01 and 2023-03. Append `.CHECKSUM` to each missing ZIP URL. The official [Binance public-data format and paths](https://github.com/binance/binance-public-data/blob/master/README.md) and its [public S3 object index](https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?list-type=2&prefix=data/futures/um/daily/aggTrades/BTCUSDT/BTCUSDT-aggTrades-2020-07) support this inventory; the other five month prefixes use the same fixed pattern. The archive-side check is in `backtest-source/data/qualified-market-metadata.json` at the producer commit.

## Why the request cannot be narrowed for the frozen pair

The already archived 57 print days were loaded by the **original** account. The deferred wallet can enter later, stop on another day, and change subsequent available capital and primary fills. The frozen comparison is the complete independent 2020Q3 and 2023Q1 quarter wallets, including later winners, costs, path drawdown and tail. Requesting only the original used days would both miss candidate-dependent days and transmit a selection derived from private manual-start history. The daily print parser does not accept a monthly `aggTrades` replacement. The safe fixed, public date cover is therefore both full quarters; the on-demand minute market requires their six calendar months. No arbitrary all-history market collection or repeat 795-session replay is needed.

**Initial decision boundary:** the existing receipts and two mark ZIPs could not close either paired wallet. The prior approval for 110 other ZIPs did not cover these **182 daily print ZIPs, 10 monthly minute ZIPs and their checksum texts**. The conditional mark arithmetic in `ENTRY_SHOCK_LATER_PATH_RESULT.md` remained diagnostic, not a final economic rejection or an adoption result.

**Subsequent fixed-scope recovery:** after a separate continuation decision for exactly the two complete public quarters, the official ZIPs and checksum texts were retrieved without login or private-date selection. The local `entry-shock-fixed-quarter-manifest.json` records all **194** required public objects, their paths, bytes and validated SHA-256: **192 newly restored bodies**, two reused original mark bodies, **69** matches to the original archived SHA-256 and size, and zero incomplete parts. New ZIP bytes total **2,108,866,125**, exactly the listed estimate. This closes the historical *source* gap for the frozen offline proxy only. The completed same-source wallet results and economic decision are in `ENTRY_SHOCK_REMAINING_PAIR_RESULT.md`. No account, `main`, threshold, 795 replay or native execution was changed.
