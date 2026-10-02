# Financial review addendum: acquisition-error mechanism

This addendum preserves the BLOCKED verdict in coin-actual-risk-financial-review.md (SHA 378b29aeca4073ae68b7dece2c7d7865168f41e15888a4354ed9ff92654b0301). No raw, assessor, producer or equality rule changed.

Independent read-only inspection of the frozen request path and the implementation reviewer's discriminating probe supports the mechanism: with cached UID and 200 ms read latency, the first snapshot requests accountConfig, symbolConfig, then GET /fapi/v3/account. The third read is at session start +600 ms. Its reply computes the mark via _mark_state → _last_print → TradePrints.last → RollingPrints._load. A non-404 public CHECKSUM or ZIP HTTPError propagates to the native Binance request classifier, yielding the exact saved Unknown text. These three GET branches contain no synthetic order refusal. The earlier possible premiumIndex hypothesis is not the +600 ms path.

The probe intercepts all network access and uses in-memory synthetic state; it does not reproduce the original HTTP status. Its CHECKSUM503 and ZIP503 cases match both observed timestamps/messages; its404 case produces a different message, and a local-print control succeeds. I inspected its source and recorded results; I did not execute a producer, account State, or probe. The actual raw still lacks HTTP status and originating URL, so whether the historical failure was CHECKSUM or ZIP, and which non-404 status occurred, cannot be recovered. This mechanism explains why data acquisition can alter operating poll evidence without changing these accounts' monetary records; it does not establish that the original control passed.

A future repair can use the existing one-level account manifest schema without source-gate relaxation, provided the old four rows are losslessly projected with explicit parent raw/receipt/row/metadata provenance, and the replacement incumbent is a separately completed original actual795 replay that passes all six groups. The failed original five-account bundle and invalid reports remain evidence. No repair has been financially accepted here.

- `task1-public-http-probe.py` SHA `900eef6ef41bd6dd5d9bc56c8cab05b1bdcb042b1b584381a0386e4fdf4101db`
- `task1-public-http-probe.json` SHA `452015342b9fa28ceb60f892513c07064a46c12e22b88d6ef7d668ca163a5629`
- `coin-risk-incumbent-http-journal-diagnostic.json` SHA `f47b06382e91d64e790bd977ba2fef952239888a4be1ca3e25e1799462cca3b4`
