# 九条 BTC 路线的操作入口

先读nine-RESULT.md与evidence/btc-nine-20261004/decisions.json。当前没有账户准入或默认采用项，已有结果正常查看无需重算。生产默认/旧ledger继续使用原不可变消费者：Spot f1383f1034e3f72df68bbda30793d22835e74557；Coin 762d75c22d19686dbd364a6b58b59dbc23340430。新HEAD不用于重绑旧账本。

## 新公开数据与信息筛选

从任一仓库手动运行一次有限收集（选择当前必要来源，总请求上限9）：

```sh
python3.13 -m research.nine_data capture \
  --family oi-deleveraging option-insurance dollar-financing etf-demand \
  --out /NEW/real-receipt-day
```

上述组合9请求。每次5秒超时、单响应2MiB、没有重试、后台任务或私有接口。链上另可选old-coin-supply，当前官方社区来源未合格；不要为了补行扩大请求矩阵。重复同UTC日不能增加独立样本；旧OI/期权历史接口/今日修订下载不能建立过去发布版本。

```sh
python3.13 -m research.nine_data evaluate \
  --history /NEW/real-receipt-day /OLDER/actual-receipt-day \
  --reuse-persistent evidence/btc-persistent-20261004/public \
  --reuse-etf evidence/btc-continuous-20261004/public \
  --at-ms ACTUAL_DECISION_UTC_MS --context causal-completed-context.json \
  --out /NEW/features.json

python3.13 -m research.nine_alpha \
  --history /NEW/real-receipt-day /OLDER/actual-receipt-day \
  --inherited evidence/btc-persistent-20261004/public \
  --etf evidence/btc-continuous-20261004/public \
  --at-ms ACTUAL_DECISION_UTC_MS --context causal-completed-context.json \
  --out /NEW/alpha-screen.json
```

context的共同字段completed_through_ms、available_ms、source_sha256和20个returns20必须来自已完成、已接收且新鲜的BTC日线。ETF另需spot_quote_turnover_by_day（UTC日ms字符串映射）与usd_usdt_basis_assumption="declared-parity-proxy"，匹配每个ETF交易日。OI的persistent_context需要completed_day_ms、available_ms、source_sha256、day_return、spot_taker_imbalance；日期必须匹配实际相邻OI接收日。chain合格数据必须证明实际完成UTXO输入年龄、old_spend_btc/total_spend_btc及block_height，活跃供应/转账量不等价。unknown不能填0。

FeatureBook从回执原字节重做来源资格绑定，不采信用户填入FEATURE_READY。alpha CLI是五族/两表达的可作用检查，始终不能独自批准账户。实际信息门槛先有至少10个独立事件、每个实际可用时期至少3个、90%覆盖；在时间先后固定两半均需成本后边际为正，并控制BTC前20日方向/RMS、Coin既有DFII10和简单减预算。不能把今天下载的旧数据当两时期证据，也不能把预测波动说成预测方向。

通过真实信息与机会门槛后，研究调用可使用nine_alpha.screen(FeatureBook,实际机会,family,expression,因果context_provider)定位真实新增风险；Spot nine_spot.measure接原complete_spot账户，Coin nine_perp.variant接原finite session/账户meter。这些是研究Python入口，尚不构成历史/前向资格；有限START/END必须先明确且恢复，原schedule不能更改。持仓预算不变，归属和保护保留，研究checkpoint与旧默认状态不互换。当前没有资格，**不启动这些账户**。

## 四层联合新增风险建议

```sh
python3.13 -m research.nine_admission \
  --input independently-confirmed-input.json \
  --rule stress-entry-cap --out /NEW/admission.json
```

输入包含now_ms、accounts两份（spot/coin）、proposal、可选context和competitor。accounts必须确认symbol=BTCUSDT、receipt_ms、owned/protected/pending、equity_usdt、gross_notional_usdt、stop_risk_usdt；真实尚未成交的已承诺entry还需reserved_notional_usdt/reserved_stop_risk_usdt。freshness60秒，pending或保护未知拒绝；不能从空目录认定实盘无仓。proposal明确kind、symbol、BUY、at_ms、gross_notional_usdt、stop_risk_usdt。状态规则另需各账户momentum20/momentum_available_ms。竞争规则的competitor必须另一账户真实可行且15秒内的独立preflight；不存在竞争时仍按普通cap4，不虚构预报。

该输出完全只读，调用者输入不能证明native账户安全；不会发单、转移资金、削减已有仓位或改账户。

## 联合有限账户与失败恢复

只有新依赖解决明确未决经济问题时才运行：

```sh
python3.13 -m research.nine_joint \
  --spot-repo /workspace/spotquant --coin-repo /workspace/coinquant \
  --spot-market /tmp/spotquant-market --coin-market /tmp/coinquant-market \
  --prints /workspace/scratch/alpha-beta-next/public-print-vault \
  --fx /workspace/starquant/data/usdcny_frankfurter.json \
  --features /workspace/btc-alpha-beta-improve/task-artifacts/edge-features-v1.json \
  --schedule /workspace/coinquant/research/session_schedule.json \
  --out /NEW/joint
```

上面是复现接口，**本轮结果已完整，无重跑理由**。最多两季度、每账户40个原开始时刻、24独立账户/1800秒；先基准提案census，无已知合法作用则不跑该候选。简单75%对照是真实新BUY减预算，不缩放曲线。

失败后另设新out，并加--reuse-completed /OLD/summary-failed.json，只生产失败/缺失case；已有raw hash及实际源身份保留。复用要求原规则、数据、window及实际依赖匹配；只允许代码明确识别的成功路径外缺ZIP处理差异。其他策略修改不会自动复用为相同生产者。并非任意恢复checkpoint；失败的在途账户没有完整checkpoint时不冒充恢复。

Coin始终一个UID12000 worker、case串行，HOME/UID/账户锁不改；软件测试等该worker结束后运行。Spot/合约钱包、时钟执行、订单、资金、SQLite状态独立。市场缓存可共享复用，资金状态不能共享。保持原raw失败和负结果、795计划、2020–2026经济目标及普通合并历史；全量软件每仓库只在最终一次，失败仅补受影响范围。
