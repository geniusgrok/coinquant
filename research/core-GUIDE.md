> 2026-10-05：下文保留本轮历史交付记录。target-core默认已撤回；当前状态及后续路线见 replacement-RESULT.md / replacement-GUIDE.md。旧core账户复现必须使用原冻结生产源码，当前入口只允许显式 --policy baseline。

# BTC核心使用与复现

当前两个仓库分别运行一个价格目标核心：Spot现货多头/现金，Coin有资金预检的正向永续。无守护进程；手动有限会话；默认只读。CLI命令与凭据/执行门禁沿用README。工程改造授权没有启动私人账户写入。

旧持久状态必须保留，不可删除/重绑成新规则。新规则首次需要核对真实余额、原成交与订单归属，空目录不证明空仓。模型格式的旧字段服务于行情和成交账簿；当前策略以目标预测为准。新规则身份拒绝旧规则检查点；不在停机期间改原生保护。native取消–替换保护间隙仍未验证。

筛选程序：`python -m research.core_screen --cache <原market.json.gz> --features <已绑定edge-features-v1.json> --out <新文件>`。原版本负结果已存证；没有新的机制/输入/依赖问题不要为了报告或HEAD变化重跑。

实际账户程序：`python -m research.core_accounts --cache <缓存> --features <冻结特征> --out <新目录> --scratch <有足够空间的新目录>`。Coin加`--market <原官方市场目录> --prints <原打印目录>`。先冻结源码，scratch实际挂载和空间必须核对；Coin串行，不改HOME/UID/锁。`--policy`/`--case`限制故障恢复范围；不覆盖原报告。每钱包有独立虚拟资金/仓位/订单/时钟，仅行情缓存共享。这里启动固定四季度，非795完整历史。旧Spot基线为原策略源码加未变资金归属公共组件，cold-start门槛不同于新目标核心，不能把其收益当旧完整历史结果。

报告程序：`python -m research.core_report --root <原任务产物目录> --cache <同一行情缓存> --out <新报告>`，只处理已保存真实账簿，不能曲线缩放。已完成结果复用，不要重新运行程序作为格式化步骤。

本轮Spot闭合会话备份为节省磁盘仅做无损`.sqlite.gz`运输，清单在`spot-backup-transport.json.gz`。还原时先解压到清单原路径，再按raw SHA/bytes/mode核对；压缩件保留。原活动intents.sqlite与Coin账户备份未清空。Git中的结果JSON也按MANIFEST解压到选定非账户目录即可；禁止把文件传输当账户恢复授权。

前向：新来源必须建立独立规则绑定观察记录；不可用此HEAD消费、补写或重绑旧规则的source-bound diaries。旧消费者Spot f1383f1034e3f72df68bbda30793d22835e74557、Coin762d75c22d19686dbd364a6b58b59dbc23340430原样保留。缺少新公开回执或原生归属时保持pending，不发明native账户日。
