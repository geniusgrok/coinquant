# Coinquant研究使用与恢复

2026-10-05（Asia/Shanghai）。当前状态从PROJECT_STATE.md恢复；结果见improvement-RESULT.md，接续依赖见improvement-roadmap.json。本指南不另存任务进度。

当前默认未采用研究候选，仍只读；工程授权不包括私有账户、订单、转账、设置、状态迁移／reset或旧forwardconsumer重绑。研究仅用独立冷资金历史venue，实际shared session＋Lifecycle，固定原资金、FX、200ms读取／1000ms写入与冻结时刻表。

Coin候选：research.downside_budget.configured支持downside-semivar／downside-tail4；research.return_core.Forecast＋configured支持positive／low-turnover，缺成熟资金费标签等待，已有消费机会不得在持续正预测下恢复。Spot候选：research.participation.configured支持trend-reentry／optional-crowding-half；可选拥挤数据缺失半预算不豁免资金／价格／保护缺失。research.improvement_accounts只用于明确新依赖下的独立账户研究；本轮已有结果直接复用，不照抄旧命令再跑。

恢复证据：Spot evidence/btc-improvement-20261005/research-artifacts.zip及两仓archive.json，优先读取有限钱包inventory、assessment摘要和full-budget-result。保留6个无效首次集成钱包，勿改接受标记。有效有限Coin92739ca、Spot7c37b1e与全历史6532476分别绑定来源。

全历史半方差仅405／795、902.63秒，不完整且无安全venue检查点。禁止用partial finalCNY年化或把剩余390次会话直接接在新冷venue上；禁止自动重跑完整历史。先在小样本量上定位真实瓶颈、核对scratch挂载及资源，并证明checkpoint能恢复资金、持仓、订单、时钟和市场matcher，再决定是否值得新完整候选测量。现存state不可丢弃，HOME／UID／账户锁不可绕过，Coin同UID工作严格串行。

后续若只有文档、归档或分支变化，复用现有测量／软件证据。新资金、订单、因果性改动做必要针对性检查；一次完整交付全量软件集中最后一次，失败只补受影响部分。收益／参与／风险之一的实质改善可继续比较，仍需如实记录代价、薄样本及未达原门槛，不事后改PASS。

