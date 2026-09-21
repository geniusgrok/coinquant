# 最新追加：D3完整稀疏47.93% CAGR /34.50%MDD，仍未达标

先读evidence/impulse-risk-20260921/REPORT.md、candidate-register.json、verification.json、
originals.json，再读下文A–E及L29历史。D3是D2相同模型的固定2.4风险预算配置，
完整窗期末人民币138,871.75；正常4h50.10%/35.58%。收益与回撤优于L29代理基线，
仍远低于150%。没有追加本金或提高交易所20x设置。不是正式资格。
F小时识别开发稀疏4.64%/33.78%，拒绝继续周期/阈值搜索，未看全窗。
2024+又用于D3时间顺序复核并启发F，没有独立未见区间。生产仍只读，无账户写入。
D3复现：research.measure_mechanisms --mechanism impulse_hold --risk-scale 2.4；
需--native/--output，完整窗显式--full-window。所有新逐笔和权益原件及实测源码已保留。
下一条可执行步骤：检查D3完整归因的单位风险收益不足，定义不同收益来源再开发检验；
同时按EXECUTION_STATUS继续原生生命周期与历史经济证据。无依据放大/搜索不继续。

---
# 当前状态：独立机制A/B/C失败，D2保留诊断，正式未达标

ACTIVE / NOT_QUALIFIED。研究分支research/on-demand-btc-20260920；禁止合并main。
本轮从远端d6a63ba恢复，main核验c886b7c；没有覆盖历史/并行工作。
首先完整阅读evidence/mechanisms-20260921/REPORT.md、candidate-register.json、
verification.json、sources.json、EXECUTION_STATUS.md及originals.json。
所有正式窗口、人民币10,000、CAGR>=150%、完整MDD<50%、20x和原稀疏序列保持不变。

本轮A/B/C开发区无成本后优势，拒绝放大；D冲击延续的7天信号有诊断优势，D2取消近端
止盈后开发33.86%/18.22%，稀疏27.78%/16.62%。D2完整窗4h21.58%/18.22%、
稀疏20.48%/16.62%、期末¥34,964.35，仍不达标且收益低于L29。
E去时间退出开发37%附近但稀疏回撤30.39%，不推进全窗。
2024+本轮又用于D2时间顺序复核并启发E；不能恢复unseen身份。
L29原始比较基线保留；三条开发轨迹与原件逐字节一致。没有改动既有费用/滑点/
保护/强平保守顺序以美化候选。

恢复本轮原始包以及originals.json引用的上一轮原始包/依赖。实测source版本A/B/C/D/D2/E
分别保留并按result.source_hashes核验；不要用最终源文件谎称早先运行的逐字节版本。
常用开发命令：python -m research.measure_mechanisms --native NATIVE_ROOT --output NEW_DIR
--mechanism squeeze|sweep|shock|impulse|impulse_hold|persistent_impulse。
一次只运行单一模型；这些研究选择不是生产多模型配置。
全窗显式调用persistent_hold_replay.run(...full_window=True...)并复用
research/mechanism-minute-days.json。只有D2本轮看了全窗。完整再现命令见原始包logs/reproduction。

Binance新增安全操作模块及离线生命周期测试，默认不授权，生产CLI仍只读。
没有新建风险的网络writer；沒有已授权testnet可验证。不能拿mock替代原生证明。
下一步：读取详细归因后提出有证据的新机制/持有结构，避免重复A/B/C失败和E尾部退化；
同时补真实历史经济规则、FX/USDT估值及原生执行证据。本任务未完成。

---
以下为上轮保留基线与原件恢复说明（不是本轮最新状态）：

# Current state — L29 improvement preserved, formal qualification failed

ACTIVE / NOT_QUALIFIED. Branch research/on-demand-btc-20260920; do not merge main.
Formal CNY10000,2020-01-01..2026-09-20exclusive, netCAGR>=150%, continuousMDD<50%,
original sparse triggers, isolated20x Binance BTCUSDT. No account writes authorized
or performed. Main last checked c886b7c63c6455bd7c933269e32cd35a6fb3e09a.

## Current research and validation

Read evidence/return-capture-20260921/REPORT.md, verification.json, originals.json.
L29 preserves L21 entry volatility size without intra-campaign resizing. Original
six-day-minute development:71.2820%CAGR/42.4310%MDD; L21:42.2274%/48.8171%.
Frozen before holdout at0eaf76753fd2b9387a56b15391db5b7bb8e89e22.
2024+HAS NOW BEEN USED for validation/failure analysis. No unseen claim remains.
Full continuous final24-day-minute comparison:
L21 CAGR0.2007671113511038, MDD0.5783639800266933205292557952, CNY34187.67525877459802610382740.
L29 CAGR0.3576612871420546, MDD0.5479327086513183762218691119, CNY78019.33606695087255024475611.
Both NOT_QUALIFIED. L27 anchored invalidation/L28 same-run reversal rejected.
All original and failed raw paths preserved; no post-validation strategy retuning.

## Recovery

Restore new originals.json archive and its prior140850994-byte dependency.
Verify lengths/SHA256/manifests. Never overwrite newer remote source automatically.
From repo root, use research.persistent_hold_replay with root/minutes=NATIVE_ROOT,
warmup=evidence/binance-boundary-20260921,repairs=evidence/binance-mark-repair-20260921,
quantity-rules=evidence/binance-boundary-20260921/current-instrument.json,
--schedule sparse --allocation volatility --lifecycle one_campaign
--reference entry_inventory --full-window; repeat --extra-minute-day for each
raw exit-minute-days.json value. Retain L21 exact control with --reference channel.
Driver default still historical; do not mistake defaults for L29 selection.

## Evidence

8targeted tests and minute reconstruction test passed;3invalid-input checks.
L21 legacy control traces byte-identical. L29six causal prefixes and468shared
market states match. Expanded-data development/full prefix identical:
{"decisions": 468, "orders": 2588, "equity": 144340}.795full sparse calls;zero liquidation classifications.
42exit-day archives independently checksum verified;24unique minute-refined days.
This is not a full tick path/native historical economics qualification.

## Remaining work

Economic target is unmet. Do not rescue with arbitrary parameter/risk grids,
repeat rejected mechanisms, lower150%/50%, or add phantom exact-funding credits.
A new causal hypothesis must establish incremental information before another
model change; report holdout reuse honestly. Existing funding interval and
full-year failure decomposition are in the evidence. L29simplification is valuable
but not proven sufficient. Do not revert it blindly to L17 or promote to live.
Native dated fee/filter/margin rules, USDT valuation, exact funding marks remain.
Binance production stays read-only; full protected execution and authorized
testnet validation remain unimplemented/unverified. LegacyBybit cannot substitute.
No credentials or authorized testnet account were supplied. No live fallback.

Native Git write credentials unavailable. Connector checkpoint writes/readback
verified13files/complete tree. New final receipt records final evidence identity.
Always recheck actual remote HEAD and parallel work before the next write.
