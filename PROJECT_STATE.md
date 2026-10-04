# PROJECT_STATE

Updated: 2026-10-04T06:09:48.620300+00:00

## 持续 alpha/beta 六路线交付已完成

全部六条路线及预登记的失败替代分支已实施、归档并正常合并到 main。Spotquant PR #13、Coinquant PR #62 已合并；实际远端合并提交分别为 57ed91cfb4a5b53897dcd94f6f1811cb20831e82、aae3621e524460dc99f08339be27d10f55a72a65，合并树与接受的 PR 源码树一致。原 main 和本轮活动工作树均正常快进；本记录所在提交仅更新文档及整合回执。

Spot 的弱流信息通过廉价筛选，继硬否决失败后实际检验新 BUY *.75 与统一降预算对照。两个固定季度候选实际调整事件均为 0，结论 SCREEN_REJECTED / ACCOUNT_SUPPORT_MISSING，未采用。新增 5 个独立冷资金账户共 144 会话、28.5466 秒，另复用 1 个原基线；30 项资金/归档一致性检查通过。风险权衡拒绝 Spot 持仓减仓；Coin 支持不足；继续检查入场尾部准备金，Spot 0 / Coin 2 次，仍不足。五次有限公共请求保留原始响应和真实时间，但历史发布身份未证明，DATA_NOT_QUALIFIED。执行费用线性、没有证据支持新执行机制；三个真实资金配对复用，5000/5000 日收盘 MDD 24.6339%、最大日收盘总名义敞口/权益 5.8863，联合连续 MDD 未验证。

完整本机 workflow 最终各运行一次：Spot 364 项、11 跳过，Coin 462 项、5 跳过，compile 和 unittest 均通过。测试提交分别为 9c2de7275dc6f41550f9ce0a078eee1ea8eb6060、11184b3d014971778c95ae89f32c0ea3eedc5e8c；之后仅文档/证据变化。远端 [skip ci] 是跳过，不是 CI 通过。没有待执行的测试、测量或整合任务。

接受结果 continuous-results-risk-fix1.json 修正晚售 dust 错误延长大部分已售币风险的问题；原错误结果保留，未受影响路线和全部账户结果原样复用。诊断 producer Spot59b6e41 / Coinfaa4156、实际账户 producer Spotd7d1f2614f8cc0f53c5bc6c77f347ca478203e2f 保持原身份，不能重标为当前 HEAD。报告与操作说明见 research/continuous-RESULT.md、continuous-GUIDE.md，整合/测试回执在 evidence/btc-continuous-20261004；旧 flow 证据保持。

没有证明提高收益的新默认策略，收益天花板也未被证明。后续只有新时间区间、合格的新信息或不同机制才重开；每个信息家族最多两种有经济含义的表达，不降低阈值或反复搜索已看过的历史。原 Spot56.5981% / 36.4122%、Coin119.2284% / 44.1051% 指标和原目标保持，goals NOT_MET，native NOT_QUALIFIED，实际前瞻账户日 0。

约束保持：BTC only，两独立现货/合约运行时，manual300/5；本轮795重放0、14GB库重扫0、私人请求/订单0。工程授权不包含私人账户、订单、转账、设置；不重置/重绑旧纸面账本，不改 HOME/UID/锁。旧消费者 Spotf1383f1034e3f72df68bbda30793d22835e74557 / Coin762d75c22d19686dbd364a6b58b59dbc23340430 不变；新的公共历史响应不是前瞻交易观察。
