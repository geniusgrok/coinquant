# BTC 后续研究入口

默认操作沿用 README 的有限手动会话和只读/owner trial 门禁。此工程不启动真实账户。

replacement-spec.json 固定三族机制、控制、成熟要求和退出条件；replacement_routes.py 提供三个信息/成本谓词及经济幅度函数。已有公开回执采集与资格解析继续使用 research.persistent_data / research.nine_data；它们有限、手动且绑定首次真实接收时间。缺失的强平/有符号现货流和定期合约数据必须取得合格原始回执再进入上下文，不能填0代替未知。

运行一次只读筛选：python -m research.replacement_routes --packet <JSON研究上下文> --out <新的结果文件>。根字段 decision_ms 是当前研究决策时间；可选 absorption / option-risk / expiry-basis 输入字段见各函数。所有价格与流量单位必须一致（BTC/USDT）；源摘要、可用时间、完成窗口、深度/保证金等是必需条件。输出来源注明 caller-supplied，不能当作原生证明。

本轮已用实际缺失输入运行并保存 WAIT 结果，不必再跑相同输入。未来重开条件：新真实信息事件/完成期间/合格可成交合约；先完成预登记成熟控制，再选最多一个真实账户候选。不要修改阈值、放宽到小样本、移动人工会话或重命名已失败候选。

旧 core_accounts 的 core 分支已退休，必须从其冻结历史生产源码复现，当前只允许 --policy baseline，防止把恢复后的旧默认误标为新版核心。原来源绑定前向账本继续由原批准消费者读取；新研究不能重绑、重置或回填它们。

恢复旧策略后也不自动接管新版状态。Coin在任何恢复与最终清理前拒绝异策略或缺失检查点；Spot沿用原严格rule边界。未知余额、未决订单或持仓继续需要归属核对，空目录不证明空账户。
