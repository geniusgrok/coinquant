# Completed-stage result documents — scoped financial check

Verdict: **two documentation corrections requested; numerical/evidence claims pass**. This is a metadata/document check of already reviewed completed stages, not a new financial run or global acceptance.

Reviewed immutable document bytes:

- SPOT-RESULT.md: `7b6438251333bec363dac812abf94112effa0a1b2f7a66924221f5eab82f142e`
- COIN-RESULT.md: `d63b251a8d529af7a7aa00bad0040f3524ea0ddc84dd88631d5cf53e32455a79`

## Corrections

1. SPOT-RESULT describes slip2 as “出场滑点×2”. Frozen `research/complete_spot.py` sets ordinary execution slip from `.0005` to `.001` and stop slip from `.001` to `.002`. The stress therefore also affects ordinary entry fills. Use “成交及止损滑点×2” or simply “滑点×2”; retain the correct measured numbers 54.1021%/36.5694%.
2. The literal `../spot-singletons/...`, `../risk-spot-project-early.json.gz`, `../spot-project-calibration.json`, `../spot-canonical/...` and `../perp-singletons-retry1.json.gz` raw paths resolve from this review directory to nonexistent locations under `/workspace/btc-alpha-beta-next`. Actual originals reside under `/workspace/scratch/alpha-beta-next`. Bind the real absolute paths, or explicitly state their common evidence root and use paths relative to it. The underlying SHA identities are correct.

These findings concern reporting precision and evidence navigation; they do not invalidate any earlier financial stage approval. Originals and reviewed documents were not edited by this reviewer.

## Verified claims

The seven Spot unscaled base rows match registered-unscaled.json, including selected 55.2180% CAGR/36.4122% MDD versus baseline 51.8503%/41.2073%, improvement 3.3678pp and reduction 4.7951pp, cost-stress values, core-permanent outage failure, and original NOT_MET targets. Session inventory is 795 except the registered Spot outage at 789. Actual calibrated atr-stop 55.1967%/36.3671%, fixed `.9972720085277638`, validation beta `.3370647782`/vol `.2901597435`, baseline `.3545835647`/`.2999153045`, cumulative validation USDT gain +27.72pp and HAC interval including zero all agree with the completed actual-risk audit. The gain is correctly described as cumulative, not annualized. The 265,808 ownership snapshots and 540 filled-BUY links, retained quantities and training-only 731-day rule are supported by the independent actual sizing proof.

Canonical HEAD0c52/full Python619570, actual five-case/147-fill inventory, six-group equality, distinct-source bridge, frozen-validator rejection of false source equivalence, and diagnostic-only calibrated scale match the approved source-bound financial review. The existing full offline test log confirms 209 passed; no tests were rerun here.

All twenty Coin case rows were programmatically checked against exact four-decimal percentage rounding of registered-unscaled.json. All five worst-stress CAGR entries equal the minimum of the three registered stresses. Base comparisons and the tiny single-topup MDD reduction are accurate. Incumbent is retained; all four new candidates fail the unscaled gates; all twenty original targets remain NOT_MET. Frozen campaign.py retains primary7.5/macro3.6, with no parameter optimum or new Coin combination claimed.

Coin 15,320 trades, 17,068 funding events, 795 sessions per case, zero funding/commission/position differences, maximum money residual below5.26e-21CNY and regression difference below8.89e-16 match the independent proof. END-exclusive settlement and Coin365.2425 versus daily/HAC365.25 are correctly distinguished. Global12 calibration SHA and compression scale `.7997705584944133` match; actual Coin risk results are not inferred from that document. The 16 hindsight-bounded cases, inherited29 baseline mark-minute bounds, continuous-path-not-independently-replayed qualification, prior research contamination and zero native/actual-day claims are preserved.

Every explicit SHA bullet in both result documents matches the referenced existing audit/report bytes. No new source, finance, private account, State, cache or producer operation was performed.

## Final reporting requirement

The later global result must disclose that selected unscaled Spot worst CNY day is **−15.8028863%** versus baseline **−14.4837424%**, while longest daily underwater duration remains **713 days** for both. These exact registered metrics were verified here. Their omission from a future global synthesis must not turn the CAGR/MDD improvement into an assertion that every risk dimension improved.

Final global report, actual Coin risk/sensitivity outcomes, global rules/source freeze and adoption approval remain pending. This scoped document review does not close those gates.


## Fix1 scoped re-review — PASS / APPROVE

This addendum closes both reporting findings above for exactly these new document bytes; the original findings and reviewed SHA history remain unchanged:

- SPOT-RESULT.md: `6f8f348efd8eee53d7dba22c2fbd3e64ecacd52464daabddceead0d1bd74bb27`
- COIN-RESULT.md: `9caa563c2c282c32ba19dd28071813e0a4d0decd7036ab89d74d30e80ddfd937`

The Spot scenario now says “成交及止损滑点×2”, correctly covering ordinary execution and stop slippage. Every corrected absolute original-artifact path in both documents resolves to the existing file under `/workspace/scratch/alpha-beta-next`. The portable-archive paragraph explicitly preserves original bytes/raw hashes and prohibits rewriting or relabeling original financial receipts; this wording review does not certify a future archive that has not been supplied.

The added Spot paragraph correctly states the original unscaled base tradeoff: worst CNY daily return −14.4837424% for consensus versus −15.8028863% for atr-stop, with longest daily underwater duration713 for both. These numbers were checked against the existing registered-unscaled metrics. It explicitly rejects an assertion that every risk dimension improved. The final global synthesis must preserve this disclosure.

No further material issue was found in this scoped correction. Previous financial/table checks remain applicable; no test, producer, financial rerun or source mutation was performed. Approval is for completed-stage documentation at the exact hashes above only. Final global report, remaining actual Coin risk/sensitivity evidence, rules/source freeze and global adoption remain pending.
