# Independent completed-bundle checker

`independent_financial_audit.py` now accepts one **already completed, immutable** raw candidate/risk/combo/sensitivity bundle. Current SHA256 `492d46ff9bbff72f1291ad77988fbf8478b35fd880c818e1d3979a6215f1897c`. It imports no producer modules, runs no account replay, uses no network and writes only its explicitly named new external output. Expected bundle SHA is mandatory and checked before and after reading; it refuses manifests and existing output paths.

Example for the stable Spot baseline:

```sh
PYTHONDONTWRITEBYTECODE=1 python /workspace/btc-alpha-beta-next/review/independent_financial_audit.py \
  --bundle /workspace/scratch/alpha-beta-next/spot-singletons/consensus.json.gz \
  --sha256 8c22b10383f637ae2cf87f7c8f027a765c5fb7b0e9af58d331d14dba89fe439a \
  --kind spot --out /workspace/btc-alpha-beta-next/review/NEW-AUDIT.json
```

For calibrated bundles add `--calibration EXACT_FILE`. Add `--baseline-audit BASELINE_V2_AUDIT.json` to independently compute training-only scale and achieved validation risk limits. Add `--unscaled-audit SAME_CANDIDATE_V2_AUDIT.json` to require equality of actual pre-cutoff economic fill/income/daily ledger fingerprints. The bundle's actual candidate, scenario, capital and source identities remain explicit. Existing failed accounts remain inventoried, with producer-completion status and independent errors separate; no invalid curve is silently promoted.

Checks include actual quote/quantity and both fee assets, daily cash/BTC/equity, prior-date FX, signed Coin WAC PNL, commission and every strictly end-exclusive public funding settlement, canonical daily full/2022+ USDT/CNY statistics, HAC7, capture/down beta, volatility, ES, MDD/calendar years, project-specific registered CAGR, and risk journal scale chronology. Coin public marks/rates are streamed from existing archives with input hashes retained. One parsed account bundle is retained at a time.

Core accounts independently assign each actual native-order fill to its immutable allocated sleeve group. Mixed core/tactical groups, duplicate/conflicting native ownership, pool borrowing, BTC/USDT fee errors and terminal conservation errors fail. Reconstructed independently compounding 20/80 initial pools are compared against recorded decision pool snapshots and final subpools. Actual core bundle validation is still pending; compact hand-calculated fixtures verified both fee assets/conservation and rejection of mixed owners, borrowing and wrong final cash. Journal same-timestamp boundaries are counted explicitly for subsequent examination if a real discrepancy arises.

The completed consensus regression passes all four scenes in `financial-audit-spot-consensus-v2-final.json`, SHA256 `f9066e622622fd281d2ba4506499cf70170f458b19a98a981a648999e1c1aead`. This adds training metrics and fingerprints without expanding the audited new-case inventory beyond 4/48. The earlier `financial-audit-spot-consensus-v2.json` is a retained preliminary checker output; use the `-final` file for training-fingerprint comparisons.

Limitations stay explicit: scale journals and prefix equality do not by themselves prove correct post-cutoff owned-position sizing. That needs actual unscaled/rerun evidence comparison. Continuous proxies are reported, not replayed; underlying archive backups are not reopened. No candidate/risk/core/combination/sensitivity account is accepted merely because checker support exists.

For immutable reproduction of the initial baseline report, `independent_financial_audit_baselines_v1.py` preserves the original exact script bytes/SHA `647988a85f42b39590946c0c6175bb0d3eebc3ac076572068725198ed9824fd9`; the original `financial-audit-baselines.json` is unchanged. No prior source/evidence identity is relabelled.

Coin schema compatibility v2.1 derives audit labels from nested `results[candidate][scenario]` and checks optional raw labels/input candidate keys for exact consistency. See `checker-coin-label-compatibility-review.md`. The previous v2 checker is preserved verbatim as `independent_financial_audit_bundle_v2.py` (SHA `94f59d806d641b9cf69496f50727a74ec8f394aee1ff9aa9c61ddce3b5ffaa9e`); all prior output identities remain unchanged.
