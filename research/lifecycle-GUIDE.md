# BTC 本轮复现与后续
先读 lifecycle-RESULT.md、lifecycle-spec.json、benefit-harm-policy.md 和 PROJECT_STATE.md。旧指标与producer不改标为新代码结果。研究状态具有独立生命周期身份；默认消费者在恢复前拒绝它，不能迁移/重置生产状态或从新HEAD读旧forward日记。

已接受screen和原件复用，不自动重新执行下面的命令。只有对应实际依赖变化或需定位失败时，从归档的冻结原始source运行到新输出，原输出不得覆盖：
```sh
python3.13 -m research.lifecycle_screen --help
python3.13 -m research.lifecycle_giveback_screen --help
```
前两机制无入围钱包，B与A原始筛选各一次。现货初始安装回执恢复只影响A，B不重跑。screen是已实现归属现金/日线机会的开发归因，不是独立重放账户、风险匹配或prospective alpha。

两仓 lifecycle.configured(policy,bars,binding,journal) 只允许显式offline venue，并复用各自原会话/资金/订单/保护流程。新因果输入应以实际hash绑定；日线close使用完成边界+建模60秒，完整持仓日不包括买入日的未知价格。当前配置两种表达debt-half/debt-two-loss；unsupported不启动钱包。持仓回吐是owned初始已安装stop所定义R的零订单提案。

Coin financing_risk.evaluate(packet,state,expression=half|flat) 是研究提案0orders/0account_entrants。next_state由调用者在任何另行授权动作前持久保存；不存在账户认证。必须提供dated native维护档位/mark/逐仓抵押/确认归属/真实已结资金费；历史模拟固定.005不得替代。新unknown不能释放上限，同比分配抵押不能冒充强平距离改善；仅确认平仓释放约束。Spot余额不能作Coin抵押。

公开跨场入口：information_next --plan … --out … 从原始成交与level2_batch/level2_50簿编译固定共同窗口；information_capture --help 为有限手动公开采集，不启动daemon/交易，不用私有认证。要执行新采集须先登记未解决决策、真实依赖变化、固定窗口及容量预算；原失败和已合格窗口不自动重采，不能事后移动窗口/修改1秒新鲜度或用lasttrade代替报价。现有合格负需求观测只是一条feature，成熟0；先取得独立日期、非重叠的实际后续结果并与单场/价格及简单预算对照，才有钱包采用意义。

Spot现货真实持有/cash基准入口在 spot_hold_control；四个已接受参考钱包复用。它们是无止损的一次买入持有/现金，与原策略会话时钟不同，不通过强可比账户适配器；不能用于默认策略保护资格。归档说明、原源SHAs、记录与软件日志见 evidence/btc-lifecycle-20261005/archive.json。

全量软件本轮最终各一次；新资金/订单/因果性问题仅必要针对性补测。无新795、大库扫描、HOME/UID/锁绕过或旧状态删除。只有未来有采用价值的候选和未解决连续路径问题，才登记重型测量预算；当前没有该理由。
