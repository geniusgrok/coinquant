# Coin actual-risk operating mismatch: read-only root-cause investigation

Frozen Coin HEAD: acedaa43ca94223f24e2fe11851bbef74e032a69. No product source/cache changes, no State/locks, no Coin producer/tests, no account access, and no network requests. Only this external diagnostic and an in-memory stub were created. Full risk bundles were not reread; financial agent's compact extraction and existing run log were reused.

## Finding

The precise source-consistent failure path is the first session snapshot's **third GET /fapi/v3/account**, after accountConfig (+200ms) and symbolConfig (+400ms), reaching +600ms. UID is already cached after earlier sessions. Both accounts are flat at these boundaries (session31 prior quantity0 and subsequent flat; session38 prior protective SELL then subsequent quantity0/consumed). Therefore flat `_advance` simply advances time and returns. Acquisition is in `_reply → _answer('/fapi/v3/account') → _mark_state → _last_print → TradePrints.last → RollingPrints._load`. It is not the holding `_advance → _scan` branch, and not the later premiumIndex GET.

Required first-choice public archive dates are 2020-03-29 and 2020-04-20. For each, RollingPrints first requests:

`https://data.binance.vision/data/futures/um/daily/aggTrades/BTCUSDT/BTCUSDT-aggTrades-<date>.zip.CHECKSUM`

and then the corresponding `.zip`. Non404 HTTPError from either request escapes RollingPrints and is caught by inherited Binance._request's HTTP handler, which loses downloader provenance and labels it `Binance HTTP outcome unresolved; query stable identity after cooldown`. The exact three synthetic GET branches contain no native rejection/_refuse path; the public downloader is the source-consistent HTTP acquisition site. The run log subsequently says each named ZIP was restored, consistent with a transient first attempt followed by normal later recovery.

The original journal retains neither request URL nor HTTP status/native code. **Actual remote status and CHECKSUM-versus-ZIP cannot be reconstructed**, and injected503 is a discriminant, not a claim that the historical status was503. No operating equality is inferred from this causal explanation: original risk incumbent still fails strict six-group equality and its immutable raw receipt remains unchanged.

## Probe evidence

`PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 python /workspace/btc-alpha-beta-next/review/task1-public-http-probe.py > /workspace/btc-alpha-beta-next/review/task1-public-http-probe.json`

The actual frozen snapshot/request/transport/answer/mark/print-loader methods run on in-memory synthetic objects; RollingPrints.__init__ and SessionExchange.__init__ are not called. Virtual path objects prohibit filesystem operations; opener/urlopen are intercepted. Each date independently checks CHECKSUM503, ZIP503 and CHECKSUM404, plus a local-print success control. The503 probes exactly match +600ms and the observed reason;404 instead yields `no trade print at or before the request`; local prints produce a successful flat snapshot without any downloader call.

```json
[
  {
    "session_start_ms": 1585486800000,
    "injected_stage": "checksum",
    "injected_http_status": 503,
    "failure_at_ms": 1585486800600,
    "reason": "Binance HTTP outcome unresolved; query stable identity after cooldown"
  },
  {
    "session_start_ms": 1585486800000,
    "injected_stage": "zip",
    "injected_http_status": 503,
    "failure_at_ms": 1585486800600,
    "reason": "Binance HTTP outcome unresolved; query stable identity after cooldown"
  },
  {
    "session_start_ms": 1585486800000,
    "injected_stage": "checksum",
    "injected_http_status": 404,
    "failure_at_ms": 1585486800600,
    "reason": "no trade print at or before the request"
  },
  {
    "session_start_ms": 1587355200000,
    "injected_stage": "checksum",
    "injected_http_status": 503,
    "failure_at_ms": 1587355200600,
    "reason": "Binance HTTP outcome unresolved; query stable identity after cooldown"
  },
  {
    "session_start_ms": 1587355200000,
    "injected_stage": "zip",
    "injected_http_status": 503,
    "failure_at_ms": 1587355200600,
    "reason": "Binance HTTP outcome unresolved; query stable identity after cooldown"
  },
  {
    "session_start_ms": 1587355200000,
    "injected_stage": "checksum",
    "injected_http_status": 404,
    "failure_at_ms": 1587355200600,
    "reason": "no trade print at or before the request"
  }
]
```

## Operational proposal and limits

Keep all frozen source, strict six-group gates, calibration and existing receipts. After the active queue/audit complete, use the reviewed public-vault helper only between jobs to restore checksum-verified original ZIPs. Run one explicitly registered retry with original runtime arguments into a new exclusive artifact; compare all six groups and fail closed on any mismatch, without repeated selection, field exclusions, clock normalization, trajectory replacement or money rescaling. Public restoration is not itself a proof of deterministic coverage: RollingPrints retains only three recently used dates, so a later revisit can redownload a pruned day. The actual replay and strict comparator remain authoritative. Root has now specifically authorized implementation (not launch) of an external one-incumbent retry plus lossless retained-four-account projection/manifest and corrected assessment. That scoped helper is a separate operational repair, not a rewrite of failed evidence.

- `task1-public-http-probe.py` SHA256 `900eef6ef41bd6dd5d9bc56c8cab05b1bdcb042b1b584381a0386e4fdf4101db`
- `task1-public-http-probe.json` SHA256 `452015342b9fa28ceb60f892513c07064a46c12e22b88d6ef7d668ca163a5629`
- `coin-risk-incumbent-http-journal-diagnostic.json` SHA256 `f47b06382e91d64e790bd977ba2fef952239888a4be1ca3e25e1799462cca3b4`
- `coin-actual-risk-unity-operating-differences.json` SHA256 `998bd08ff4c583306ee1004f23e891664d9e7f0883b224dd96ab5133eaf8b65b`
